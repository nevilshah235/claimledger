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


# Gemini AI Agent Test Fixtures

@pytest.fixture
def gemini_api_key():
    """Get Gemini API key from environment, or None if not available."""
    return os.getenv("GOOGLE_AI_API_KEY")


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client for testing."""
    from unittest.mock import MagicMock
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"document_type": "invoice", "amount": 3500.00, "date": "2024-01-15", "vendor": "Auto Repair Shop", "description": "Front bumper repair", "valid": true, "confidence": 0.85, "notes": "Mock response"}'
    
    # Mock the new API structure: client.aio.models.generate_content
    mock_aio = MagicMock()
    mock_models = MagicMock()
    mock_models.generate_content = AsyncMock(return_value=mock_response)
    mock_aio.models = mock_models
    mock_client.aio = mock_aio
    
    return mock_client


@pytest.fixture
def real_gemini_client(gemini_api_key):
    """Real Gemini client if API key is available, otherwise skip."""
    if not gemini_api_key:
        pytest.skip("GOOGLE_AI_API_KEY not set, skipping real API test")
    
    try:
        import google.genai as genai
        client = genai.Client(api_key=gemini_api_key)
        return client
    except ImportError:
        pytest.skip("google-genai not installed")
    except Exception as e:
        pytest.skip(f"Failed to initialize Gemini: {e}")


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a temporary PDF file for testing."""
    import tempfile
    
    # Create a minimal PDF file (PDF header + basic structure)
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Invoice: $3500.00) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
    
    pdf_file = tmp_path / "sample_invoice.pdf"
    pdf_file.write_bytes(pdf_content)
    return str(pdf_file)


@pytest.fixture
def sample_receipt_image(tmp_path):
    """Create a temporary receipt image file for testing."""
    try:
        from PIL import Image
        # Create a simple test image
        img = Image.new('RGB', (400, 300), color='white')
        img_path = tmp_path / "sample_receipt.jpg"
        img.save(img_path, 'JPEG')
        return str(img_path)
    except ImportError:
        # Fallback: create minimal valid JPEG file
        img_path = tmp_path / "sample_receipt.jpg"
        # Minimal JPEG header
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'
        img_path.write_bytes(jpeg_data)
        return str(img_path)


@pytest.fixture
def sample_damage_photo(tmp_path):
    """Create a temporary damage photo for testing."""
    try:
        from PIL import Image
        img = Image.new('RGB', (800, 600), color='gray')
        img_path = tmp_path / "sample_damage_photo.jpg"
        img.save(img_path, 'JPEG')
        return str(img_path)
    except ImportError:
        # Fallback: create minimal valid JPEG file
        img_path = tmp_path / "sample_damage_photo.jpg"
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'
        img_path.write_bytes(jpeg_data)
        return str(img_path)


@pytest.fixture
def sample_fire_damage_photo(tmp_path):
    """Create a temporary fire damage photo for testing."""
    try:
        from PIL import Image
        img = Image.new('RGB', (800, 600), color=(200, 100, 50))
        img_path = tmp_path / "sample_fire_damage.jpg"
        img.save(img_path, 'JPEG')
        return str(img_path)
    except ImportError:
        # Fallback: create minimal valid JPEG file
        img_path = tmp_path / "sample_fire_damage.jpg"
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'
        img_path.write_bytes(jpeg_data)
        return str(img_path)


@pytest.fixture
def sample_water_damage_photo(tmp_path):
    """Create a temporary water damage photo for testing."""
    try:
        from PIL import Image
        img = Image.new('RGB', (800, 600), color=(50, 100, 200))
        img_path = tmp_path / "sample_water_damage.jpg"
        img.save(img_path, 'JPEG')
        return str(img_path)
    except ImportError:
        # Fallback: create minimal valid JPEG file
        img_path = tmp_path / "sample_water_damage.jpg"
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'
        img_path.write_bytes(jpeg_data)
        return str(img_path)


@pytest.fixture
def test_claim_with_evidence(test_db, test_claimant, sample_pdf_file, sample_damage_photo):
    """Create a test claim with attached evidence files."""
    import uuid
    
    # Get wallet address
    wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
    
    claim = Claim(
        id=str(uuid.uuid4()),
        claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
        claim_amount=Decimal("3500.00"),
        status="SUBMITTED",
        processing_costs=Decimal("0.00")
    )
    test_db.add(claim)
    test_db.flush()
    
    # Add document evidence
    doc_evidence = Evidence(
        id=str(uuid.uuid4()),
        claim_id=claim.id,
        file_type="document",
        file_path=sample_pdf_file,
        mime_type="application/pdf"
    )
    test_db.add(doc_evidence)
    
    # Add image evidence
    img_evidence = Evidence(
        id=str(uuid.uuid4()),
        claim_id=claim.id,
        file_type="image",
        file_path=sample_damage_photo,
        mime_type="image/jpeg"
    )
    test_db.add(img_evidence)
    
    test_db.commit()
    test_db.refresh(claim)
    return claim


@pytest.fixture
def test_claim_high_confidence(test_db, test_claimant):
    """Create a test claim that should auto-approve (high confidence scenario)."""
    import uuid
    
    wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
    
    claim = Claim(
        id=str(uuid.uuid4()),
        claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
        claim_amount=Decimal("2000.00"),
        status="SUBMITTED",
        processing_costs=Decimal("0.00")
    )
    test_db.add(claim)
    test_db.commit()
    test_db.refresh(claim)
    return claim


@pytest.fixture
def test_claim_low_confidence(test_db, test_claimant):
    """Create a test claim that needs review (low confidence scenario)."""
    import uuid
    
    wallet = test_db.query(UserWallet).filter(UserWallet.user_id == test_claimant.id).first()
    
    claim = Claim(
        id=str(uuid.uuid4()),
        claimant_address=wallet.wallet_address if wallet else "0x1234567890123456789012345678901234567890",
        claim_amount=Decimal("5000.00"),
        status="SUBMITTED",
        processing_costs=Decimal("0.00")
    )
    test_db.add(claim)
    test_db.commit()
    test_db.refresh(claim)
    return claim


# Test utility functions

def create_test_pdf(tmp_path, content="Invoice: $3500.00"):
    """Helper to create test PDF files."""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(""" + content.encode() + b""") Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
    
    pdf_file = tmp_path / "test_invoice.pdf"
    pdf_file.write_bytes(pdf_content)
    return str(pdf_file)


def create_test_image(tmp_path, size=(800, 600), color='gray', filename="test_image.jpg"):
    """Helper to create test image files."""
    try:
        from PIL import Image
        
        if color == 'gray':
            img_color = (128, 128, 128)
        elif color == 'red':
            img_color = (200, 50, 50)
        elif color == 'blue':
            img_color = (50, 50, 200)
        else:
            img_color = color if isinstance(color, tuple) else (128, 128, 128)
        
        img = Image.new('RGB', size, color=img_color)
        img_path = tmp_path / filename
        img.save(img_path, 'JPEG')
        return str(img_path)
    except ImportError:
        # Fallback: create minimal valid JPEG file
        img_path = tmp_path / filename
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb'
        img_path.write_bytes(jpeg_data)
        return str(img_path)


def mock_gemini_response(text_response, json_data=None):
    """Helper to mock Gemini API responses."""
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    if json_data:
        import json
        mock_response.text = json.dumps(json_data)
    else:
        mock_response.text = text_response
    return mock_response


def assert_agent_result_structure(result, agent_type):
    """Helper to validate agent result structure."""
    assert isinstance(result, dict), f"{agent_type} result should be a dict"
    
    if agent_type == "document":
        assert "summary" in result
        assert "extracted_data" in result
        assert "valid" in result
        assert "confidence" in result
    elif agent_type == "image":
        assert "summary" in result
        assert "damage_assessment" in result
        assert "valid" in result
        assert "confidence" in result
    elif agent_type == "fraud":
        assert "fraud_score" in result
        assert "risk_level" in result
        assert "indicators" in result
        assert "confidence" in result
    elif agent_type == "reasoning":
        assert "final_confidence" in result
        assert "contradictions" in result
        assert "fraud_risk" in result
        assert "reasoning" in result
