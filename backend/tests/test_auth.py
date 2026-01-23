"""
Tests for authentication endpoints.
"""

import pytest
from fastapi import status


def test_register_claimant(client):
    """Test registering a new claimant."""
    response = client.post(
        "/auth/register",
        json={
            "email": "newclaimant@example.com",
            "password": "password123",
            "role": "claimant"
        }
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newclaimant@example.com"
    assert data["role"] == "claimant"
    assert "wallet_address" in data
    assert "access_token" in data
    assert len(data["access_token"]) > 0


def test_register_insurer(client):
    """Test registering a new insurer."""
    response = client.post(
        "/auth/register",
        json={
            "email": "newinsurer@example.com",
            "password": "password123",
            "role": "insurer"
        }
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newinsurer@example.com"
    assert data["role"] == "insurer"
    assert "wallet_address" in data
    assert "access_token" in data


def test_register_duplicate_email(client, test_user):
    """Test that duplicate email registration is rejected."""
    response = client.post(
        "/auth/register",
        json={
            "email": test_user.email,
            "password": "password123",
            "role": "claimant"
        }
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"].lower()


def test_register_invalid_role(client):
    """Test that invalid role is rejected."""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "role": "invalid_role"
        }
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "role" in response.json()["detail"].lower()


def test_login_success(client, test_user):
    """Test successful login."""
    response = client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "password123"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user.email
    assert "access_token" in data
    assert len(data["access_token"]) > 0


def test_login_invalid_credentials(client, test_user):
    """Test login with invalid password."""
    response = client.post(
        "/auth/login",
        json={
            "email": test_user.email,
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user(client, auth_headers):
    """Test getting current user info with valid token."""
    response = client.get("/auth/me", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "user_id" in data
    assert "email" in data
    assert "role" in data


def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user_no_token(client):
    """Test getting current user without token."""
    response = client.get("/auth/me")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_wallet_info(client, auth_headers, test_claimant):
    """Test getting wallet information."""
    response = client.get("/auth/wallet", headers=auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "wallet_address" in data
    assert "circle_wallet_id" in data


def test_get_wallet_info_no_wallet(client, test_db):
    """Test getting wallet info when user has no wallet."""
    from src.services.auth import get_password_hash, create_access_token
    from src.models import User
    
    # Create user without wallet
    user = User(
        id="no-wallet-user",
        email="nowallet@example.com",
        password_hash=get_password_hash("password123"),
        role="claimant"
    )
    test_db.add(user)
    test_db.commit()
    
    # Login
    login_response = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": "password123"
        }
    )
    token = login_response.json()["access_token"]
    
    # Try to get wallet
    response = client.get(
        "/auth/wallet",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
