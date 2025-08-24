from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone
import json
import logging
import uuid
import nats
from nats.js import JetStreamContext

from .base_message import BaseMessage, NATSHeaders
from .security import SignedEnvelope
from .validation import MessageValidator

logger = logging.getLogger(__name__)

class ProductionMessageHandler:
    """Production message handler with proper headers and tracing"""
    
    def __init__(self, nats_client: nats.NATS, secret: str, producer_id: str):
        self.nc = nats_client
        self.js: JetStreamContext = nats_client.jetstream()
        self.secret = secret
        self.producer_id = producer_id
        self.validator = MessageValidator()
    
    async def publish_message(
        self,
        message: BaseMessage,
        headers: Optional[Dict[str, str]] = None,
        reply_to: Optional[str] = None,
        traceparent: Optional[str] = None
    ) -> str:
        """Publish message with proper headers and signing"""
        
        # Create NATS headers (transport concerns)
        nats_headers = NATSHeaders(
            schema_id=message.get_schema_id(),
            reply_to=reply_to,
            traceparent=traceparent,
            producer_id=self.producer_id
        )
        
        # Add custom headers
        if headers:
            for key, value in headers.items():
                setattr(nats_headers, key.lower().replace('-', '_'), value)
        
        # Create signed envelope
        subject = self._get_subject_for_message(message)
        envelope = SignedEnvelope.create_signed(
            message=message.model_dump(),
            subject=subject,
            secret=self.secret
        )
        
        # Publish with headers
        await self.js.publish(
            subject=subject,
            payload=envelope.model_dump_json().encode('utf-8'),
            headers=nats_headers.model_dump(by_alias=True, exclude_none=True)
        )
        
        logger.info(
            f"Published message",
            extra={
                "message_type": message.message_type,
                "subject": subject,
                "correlation_id": message.correlation_id,
                "nats_msg_id": nats_headers.nats_msg_id,
                "traceparent": traceparent
            }
        )
        
        return nats_headers.nats_msg_id
    
    async def subscribe_with_validation(
        self,
        subject: str,
        handler: Callable[[BaseMessage, Dict[str, str]], Awaitable[None]],
        durable: Optional[str] = None,
        queue: Optional[str] = None
    ):
        """Subscribe with automatic validation and error handling"""
        
        async def validated_handler(msg: nats.aio.msg.Msg):
            try:
                # Extract headers
                headers = dict(msg.headers) if msg.headers else {}
                
                # Parse and validate envelope
                envelope_data = json.loads(msg.data.decode('utf-8'))
                envelope = SignedEnvelope(**envelope_data)
                
                # Verify signature with replay protection
                if not envelope.verify_signature(self.secret, max_age_seconds=300):
                    logger.error(
                        "Invalid message signature",
                        extra={
                            "subject": msg.subject,
                            "nats_msg_id": headers.get('Nats-Msg-Id'),
                            "envelope_id": str(envelope.envelope_id)
                        }
                    )
                    await msg.nak()
                    return
                
                # Validate inner message
                message_type = envelope.message.get('message_type')
                validation_result = self.validator.validate_message(envelope.message, message_type)
                
                if not validation_result.is_valid:
                    logger.error(
                        "Invalid message format",
                        extra={
                            "subject": msg.subject,
                            "errors": validation_result.errors,
                            "nats_msg_id": headers.get('Nats-Msg-Id')
                        }
                    )
                    await msg.nak()
                    return
                
                # Create message instance
                message_class = self.validator.get_message_class(message_type)
                message = message_class(**envelope.message)
                
                # Call handler with validated message and headers
                await handler(message, headers)
                await msg.ack()
                
            except Exception as e:
                logger.exception(
                    "Message handler error",
                    extra={
                        "subject": msg.subject,
                        "error": str(e),
                        "nats_msg_id": headers.get('Nats-Msg-Id') if 'headers' in locals() else None
                    }
                )
                await msg.nak()
        
        # Subscribe with proper JetStream options
        await self.js.subscribe(
            subject=subject,
            cb=validated_handler,
            durable=durable,
            queue=queue,
            manual_ack=True
        )
    
    def _get_subject_for_message(self, message: BaseMessage) -> str:
        """Get NATS subject for message (no IDs in subjects)"""
        if hasattr(message, 'get_nats_subject'):
            return message.get_nats_subject()
        return f"{message.message_type}.default"