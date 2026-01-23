"""
Verifier HTTP client for internal (backend) calls to /verifier/*.

Evaluations are free: no x402, no payment. This client POSTs to verifier
endpoints with X-Internal-Secret for auth. The verifier records usage (amount=0)
for tracking.
"""

import os
from typing import Dict, Any, Optional
import httpx

# Base URL for self-calls (backend -> verifier). Override with API_BASE_URL.
_VERIFIER_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
_INTERNAL_SECRET = os.getenv("EVALUATION_INTERNAL_SECRET", "dev-internal-secret")

_default_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _default_client
    if _default_client is None:
        _default_client = httpx.AsyncClient(timeout=60.0)
    return _default_client


async def _post(path: str, json: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_VERIFIER_BASE}{path}"
    r = await _get_client().post(url, json=json, headers={"X-Internal-Secret": _INTERNAL_SECRET})
    r.raise_for_status()
    return r.json()


async def verify_document(claim_id: str, document_path: str) -> Dict[str, Any]:
    """Call /verifier/document. Evaluations are free (no payment)."""
    return await _post("/verifier/document", {"claim_id": claim_id, "document_path": document_path})


async def verify_image(claim_id: str, image_path: str) -> Dict[str, Any]:
    """Call /verifier/image. Evaluations are free (no payment)."""
    return await _post("/verifier/image", {"claim_id": claim_id, "image_path": image_path})


async def verify_fraud(claim_id: str) -> Dict[str, Any]:
    """Call /verifier/fraud. Evaluations are free (no payment)."""
    return await _post("/verifier/fraud", {"claim_id": claim_id})
