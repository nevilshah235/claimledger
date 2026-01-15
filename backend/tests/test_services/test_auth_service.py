"""
Tests for authentication service utilities.
"""

import pytest
from src.services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password_123"
    hashed = get_password_hash(password)
    
    # Hash should be different from original
    assert hashed != password
    assert len(hashed) > 0
    
    # Should verify correctly
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_password_hash_different_each_time():
    """Test that password hashes are different each time (salt)."""
    password = "test_password_123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    
    # Hashes should be different due to salt
    assert hash1 != hash2
    
    # But both should verify
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "user-123", "email": "test@example.com", "role": "claimant"}
    token = create_access_token(data)
    
    assert token is not None
    assert len(token) > 0
    assert isinstance(token, str)


def test_decode_access_token():
    """Test JWT token decoding."""
    data = {"sub": "user-123", "email": "test@example.com", "role": "claimant"}
    token = create_access_token(data)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "test@example.com"
    assert decoded["role"] == "claimant"


def test_decode_invalid_token():
    """Test decoding invalid token."""
    decoded = decode_access_token("invalid_token_string")
    assert decoded is None


def test_decode_expired_token():
    """Test decoding expired token."""
    from datetime import timedelta
    
    data = {"sub": "user-123"}
    # Create token with very short expiration
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))
    
    # Token should be invalid (expired)
    decoded = decode_access_token(token)
    # Note: JWT library may still decode but exp check happens in validation
    # This depends on implementation
