from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Type, Union, List
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class ValidationResult(BaseModel):
    """Result of message validation"""
    
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_data: Optional[Dict[str, Any]] = None
    schema_version: str = Field(default="1.0")
    validated_at: datetime = Field(default_factory=datetime.utcnow)

class MessageValidator:
    """Centralized message validation"""
    
    def __init__(self):
        self.schemas: Dict[str, Type[BaseModel]] = {}
        self.register_default_schemas()
    
    def register_schema(self, message_type: str, schema_class: Type[BaseModel]):
        """Register a schema for a message type"""
        self.schemas[message_type] = schema_class
        logger.info(f"Registered schema for message type: {message_type}")
    
    def register_default_schemas(self):
        """Register default schemas"""
        from .task_message import TaskMessage
        from .result_message import ResultMessage
        from .base_message import BaseMessage
        
        self.register_schema("task", TaskMessage)
        self.register_schema("result", ResultMessage)
        self.register_schema("base", BaseMessage)
    
    def validate_message(self, message_data: Union[Dict[str, Any], str], message_type: str) -> ValidationResult:
        """Validate a message against its schema"""
        
        # Parse JSON if string
        if isinstance(message_data, str):
            try:
                message_data = json.loads(message_data)
            except json.JSONDecodeError as e:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Invalid JSON: {str(e)}"]
                )
        
        # Get schema
        schema_class = self.schemas.get(message_type)
        if not schema_class:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unknown message type: {message_type}"]
            )
        
        # Validate
        try:
            validated_instance = schema_class(**message_data)
            return ValidationResult(
                is_valid=True,
                validated_data=validated_instance.dict()
            )
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                errors.append(f"{field}: {error['msg']}")
            
            return ValidationResult(
                is_valid=False,
                errors=errors
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    def validate_envelope(self, envelope_data: Dict[str, Any], secret: str) -> ValidationResult:
        """Validate a signed envelope"""
        from .security import SignedEnvelope
        
        try:
            envelope = SignedEnvelope(**envelope_data)
            
            # Verify signature
            if not envelope.verify_signature(secret):
                return ValidationResult(
                    is_valid=False,
                    errors=["Invalid signature"]
                )
            
            # Validate inner message
            message_type = envelope.message.get('message_type')
            if message_type:
                inner_result = self.validate_message(envelope.message, message_type)
                if not inner_result.is_valid:
                    return ValidationResult(
                        is_valid=False,
                        errors=["Invalid inner message"] + inner_result.errors
                    )
            
            return ValidationResult(
                is_valid=True,
                validated_data=envelope.dict()
            )
            
        except ValidationError as e:
            errors = [f"{'.'.join(str(x) for x in error['loc'])}: {error['msg']}" for error in e.errors()]
            return ValidationResult(
                is_valid=False,
                errors=errors
            )

# Global validator instance
validator = MessageValidator()