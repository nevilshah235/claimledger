"""
Pytest fixtures for backend tests.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from decimal import Decimal

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"

from src.database import Base, get_db
from src.models import User, UserWallet, Claim, Evidence
from src.main import app


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    # Use a file-based SQLite for testing to avoid connection issues
    # Or use :memory: with check_same_thread=False
    import tempfile
    import os
    
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    try:
        engine = create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)
            engine.dispose()
    finally:
        # Clean up temp file
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    from src.services.auth import get_password_hash
    
    user = User(
        id="test-user-id",
        email="test@example.com",
        password_hash=get_password_hash("password123"),
        role="claimant"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_claimant(test_db, test_user):
    """Create a claimant user with wallet."""
    wallet = UserWallet(
        user_id=test_user.id,
        wallet_address="0x1234567890123456789012345678901234567890",
        circle_wallet_id="test-circle-wallet-id",
        wallet_set_id="test-wallet-set-id"
    )
    test_db.add(wallet)
    test_db.commit()
    test_db.refresh(wallet)
    return test_user


@pytest.fixture
def test_insurer(test_db):
    """Create an insurer user."""
    from src.services.auth import get_password_hash
    
    insurer = User(
        id="test-insurer-id",
        email="insurer@example.com",
        password_hash=get_password_hash("password123"),
        role="insurer"
    )
    test_db.add(insurer)
    test_db.commit()
    test_db.refresh(insurer)
    return insurer


@pytest.fixture
def auth_headers(client, test_claimant):
    """Get JWT token headers for authenticated requests."""
    response = client.post(
        "/auth/login",
        json={
            "email": test_claimant.email,
            "password": "password123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def insurer_headers(client, test_insurer):
    """Get JWT token headers for insurer requests."""
    response = client.post(
        "/auth/login",
        json={
            "email": test_insurer.email,
            "password": "password123"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_claim(test_db, test_claimant):
    """Create a test claim."""
    import uuid
    # Get wallet address
    wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
    
    claim = Claim(
        id=str(uuid.uuid4()),  # Use valid UUID format
        claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
        claim_amount=Decimal("1000.00"),
        status="SUBMITTED",
        processing_costs=Decimal("0.00")
    )
    test_db.add(claim)
    test_db.commit()
    test_db.refresh(claim)
    return claim


@pytest.fixture
def mock_gateway_service():
    """Mock GatewayService for x402 tests."""
    with patch("src.services.gateway.get_gateway_service") as mock_get:
        mock_service = AsyncMock()
        mock_service.validate_receipt = AsyncMock(return_value=True)
        mock_service.create_micropayment = AsyncMock(return_value="mock_receipt_token_12345")
        mock_service.get_balance = AsyncMock(return_value=Decimal("100.00"))
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_x402_client():
    """Mock X402Client for agent tool tests."""
    with patch("src.services.x402_client.get_x402_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.verify_document = AsyncMock(return_value={
            "extracted_data": {"amount": 1000.0},
            "valid": True,
            "verification_id": "test-verification-id"
        })
        mock_client.verify_image = AsyncMock(return_value={
            "damage_assessment": {"severity": "moderate"},
            "valid": True,
            "analysis_id": "test-analysis-id"
        })
        mock_client.verify_fraud = AsyncMock(return_value={
            "fraud_score": 0.05,
            "risk_level": "LOW",
            "check_id": "test-check-id"
        })
        mock_get.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_blockchain_service():
    """Mock BlockchainService for settlement tests."""
    with patch("src.services.blockchain.get_blockchain_service") as mock_get:
        mock_service = AsyncMock()
        mock_service.approve_claim = AsyncMock(return_value="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_developer_wallets_service():
    """Mock DeveloperWalletsService for wallet creation tests."""
    with patch("src.services.developer_wallets.DeveloperWalletsService") as mock_class:
        mock_service = AsyncMock()
        mock_service.create_wallet = AsyncMock(return_value={
            "wallet_id": "test-circle-wallet-id",
            "address": "0x1234567890123456789012345678901234567890",
            "wallet_set_id": "test-wallet-set-id"
        })
        mock_service.get_wallet = AsyncMock(return_value={
            "blockchain": "ARC",
            "address": "0x1234567890123456789012345678901234567890"
        })
        mock_service.get_wallet_balance = AsyncMock(return_value={
            "balances": [{"amount": "100.00", "currency": "USDC"}]
        })
        mock_class.return_value = mock_service
        yield mock_service
