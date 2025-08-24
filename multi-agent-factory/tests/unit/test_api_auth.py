import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from api.auth import create_access_token, verify_token, get_current_user
from api.main import app


@pytest.mark.security
class TestAuthentication:
    def test_create_access_token_valid_payload(self):
        """Test JWT token creation with valid payload"""
        payload = {"sub": "user123", "scopes": ["read", "write"]}
        token = create_access_token(payload)
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        payload = {"sub": "user123"}
        token = create_access_token(payload)
        decoded = verify_token(token)
        assert decoded["sub"] == "user123"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_get_current_user_unauthorized(self):
        """Test user retrieval with invalid token"""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token")
        assert exc_info.value.status_code == 401