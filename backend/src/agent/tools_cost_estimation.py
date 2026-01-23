"""
Cost Estimation Tools - Layer 2 (FREE).

Estimate repair costs and cross-check amounts.
These tools are free and used before paid verification.

Supports multi-currency: document amounts in INR/Rs/₹ are converted to USD
when comparing to the claim amount (USDC). Use INR_TO_USD_RATE env (default 83).
"""

import os
from typing import Dict, Any, Optional
from decimal import Decimal


def _inr_to_usd_rate() -> float:
    try:
        return float(os.getenv("INR_TO_USD_RATE", "83"))
    except ValueError:
        return 83.0


def _to_usd(amount: float, currency: Optional[str]) -> float:
    """Convert to USD when currency is INR/Rs/₹. Claim amounts are in USDC (USD)."""
    if amount is None or (isinstance(amount, (int, float)) and float(amount) == 0):
        return 0.0
    amount = float(amount)
    if not currency or not isinstance(currency, str):
        return amount
    c = currency.strip().upper()
    if c in ("INR", "RS", "RS.", "₹", "RUPEES", "INDIAN RUPEES"):
        return amount / _inr_to_usd_rate()
    return amount


async def estimate_repair_cost(
    claim_id: str,
    extracted_data: object = None,
    damage_assessment: object = None
) -> object:
    """
    Estimate repair cost based on extracted data (FREE).
    
    Estimates repair cost from document amounts and/or image damage assessment.
    This is a free tool used before verification to filter out obviously fake claims.
    
    Args:
        claim_id: Unique claim identifier
        extracted_data: Data extracted from document (from extract_document_data)
        damage_assessment: Damage assessment from image (from extract_image_data)
        
    Returns:
        {
            "success": bool,
            "estimated_cost": float,
            "confidence": float,
            "cost_breakdown": {...},
            "cost": 0.0  # FREE
        }
    """
    try:
        estimated_cost = 0.0
        confidence = 0.5
        cost_breakdown = {}
        
        # Use document amount if available (convert INR/Rs to USD when currency present)
        if extracted_data and isinstance(extracted_data, dict):
            ef = extracted_data.get("extracted_fields") or extracted_data
            if isinstance(ef, dict):
                doc_amount = ef.get("total_amount") or ef.get("amount") or ef.get("grand_total") or ef.get("final_total")
                doc_currency = ef.get("currency")
                if doc_amount is not None:
                    doc_amount = _to_usd(float(doc_amount), doc_currency)
                    estimated_cost = doc_amount
                    confidence = 0.8
                    cost_breakdown["document_amount"] = doc_amount
        
        # Use image damage assessment if available
        if damage_assessment:
            img_cost = damage_assessment.get("estimated_cost")
            if img_cost:
                if estimated_cost > 0:
                    # Average if both available
                    estimated_cost = (estimated_cost + float(img_cost)) / 2
                    confidence = 0.9
                else:
                    estimated_cost = float(img_cost)
                    confidence = 0.7
                cost_breakdown["image_estimate"] = img_cost
        
        return {
            "success": True,
            "estimated_cost": estimated_cost,
            "confidence": confidence,
            "cost_breakdown": cost_breakdown,
            "cost": 0.0  # FREE
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "estimated_cost": 0.0,
            "confidence": 0.0,
            "cost": 0.0
        }


async def cross_check_amounts(
    claim_id: str,
    claim_amount: float,
    extracted_total: Optional[float] = None,
    estimated_cost: Optional[float] = None,
    document_amount: Optional[float] = None,
    extracted_total_currency: Optional[str] = None,
    document_amount_currency: Optional[str] = None
) -> object:
    """
    Cross-check amounts for consistency (FREE).
    
    Compares claim amount (USDC/USD) with extracted amounts. When document amounts
    are in INR/Rs/₹, pass extracted_total_currency or document_amount_currency so
    they are converted to USD before comparison (e.g. 40000 Rs ≈ $500 at ~80–85 INR/USD).
    
    Args:
        claim_id: Unique claim identifier
        claim_amount: Original claim amount in USDC (USD)
        extracted_total: Total from extracted line items
        estimated_cost: Estimated cost from estimate_repair_cost (already in USD if from INR doc)
        document_amount: Amount from document extraction
        extracted_total_currency: Currency of extracted_total (e.g. INR, Rs, USD). If INR/Rs, converted to USD.
        document_amount_currency: Currency of document_amount (e.g. INR, Rs, USD). If INR/Rs, converted to USD.
        
    Returns:
        {
            "success": bool,
            "matches": bool,
            "difference": float,
            "difference_percent": float,
            "warnings": [str],
            "cost": 0.0  # FREE
        }
    """
    try:
        warnings = []
        matches = True
        difference = 0.0
        difference_percent = 0.0

        # Convert document amounts to USD when in INR/Rs (explicit or inferred from 50–200× ratio)
        def _infer_inr_if_ratio(amt: float, ref: float) -> Optional[str]:
            if ref and ref > 0 and amt and amt > 0:
                r = amt / ref
                if 50 <= r <= 200:  # plausible INR/USD ratio
                    return "INR"
            return None

        if extracted_total is not None and extracted_total > 0:
            c = extracted_total_currency or _infer_inr_if_ratio(float(extracted_total), claim_amount)
            extracted_total = _to_usd(float(extracted_total), c)
        if document_amount is not None and document_amount > 0:
            c = document_amount_currency or _infer_inr_if_ratio(float(document_amount), claim_amount)
            document_amount = _to_usd(float(document_amount), c)
        
        # Compare with extracted_total
        if extracted_total and extracted_total > 0:
            diff = abs(claim_amount - extracted_total)
            diff_pct = (diff / max(claim_amount, extracted_total)) * 100
            if diff_pct > 20:  # More than 20% difference
                matches = False
                difference = diff
                difference_percent = diff_pct
                warnings.append(f"Claim amount (${claim_amount:,.2f}) differs from extracted total (${extracted_total:,.2f}) by {diff_pct:.1f}%")
        
        # Compare with estimated_cost (already in USD from estimate_repair_cost)
        if estimated_cost and estimated_cost > 0:
            diff = abs(claim_amount - estimated_cost)
            diff_pct = (diff / max(claim_amount, estimated_cost)) * 100
            if diff_pct > 20:  # More than 20% difference
                matches = False
                if difference == 0:
                    difference = diff
                    difference_percent = diff_pct
                warnings.append(f"Claim amount (${claim_amount:,.2f}) differs from estimated cost (${estimated_cost:,.2f}) by {diff_pct:.1f}%")
        
        # Compare with document_amount (converted to USD if INR/Rs)
        if document_amount and document_amount > 0:
            diff = abs(claim_amount - document_amount)
            diff_pct = (diff / max(claim_amount, document_amount)) * 100
            if diff_pct > 20:  # More than 20% difference
                matches = False
                if difference == 0:
                    difference = diff
                    difference_percent = diff_pct
                warnings.append(f"Claim amount (${claim_amount:,.2f}) differs from document amount (${document_amount:,.2f}) by {diff_pct:.1f}%")
        
        return {
            "success": True,
            "matches": matches,
            "difference": difference,
            "difference_percent": difference_percent,
            "warnings": warnings,
            "cost": 0.0  # FREE
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "matches": False,
            "difference": 0.0,
            "difference_percent": 0.0,
            "warnings": [f"Error: {str(e)}"],
            "cost": 0.0
        }
