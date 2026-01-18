"""
Cost Estimation Tools - Layer 2 (FREE).

Estimate repair costs and cross-check amounts.
These tools are free and used before paid verification.
"""

from typing import Dict, Any, Optional
from decimal import Decimal


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
        
        # Use document amount if available
        if extracted_data:
            doc_amount = extracted_data.get("extracted_fields", {}).get("amount")
            if doc_amount:
                estimated_cost = float(doc_amount)
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
    document_amount: Optional[float] = None
) -> object:
    """
    Cross-check amounts for consistency (FREE).
    
    Compares claim amount with extracted amounts to detect mismatches.
    This is a free tool used before verification to filter out obviously fake claims.
    
    Args:
        claim_id: Unique claim identifier
        claim_amount: Original claim amount
        extracted_total: Total from extracted line items
        estimated_cost: Estimated cost from estimate_repair_cost
        document_amount: Amount from document extraction
        
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
        
        # Compare with extracted_total
        if extracted_total and extracted_total > 0:
            diff = abs(claim_amount - extracted_total)
            diff_pct = (diff / max(claim_amount, extracted_total)) * 100
            if diff_pct > 20:  # More than 20% difference
                matches = False
                difference = diff
                difference_percent = diff_pct
                warnings.append(f"Claim amount (${claim_amount:,.2f}) differs from extracted total (${extracted_total:,.2f}) by {diff_pct:.1f}%")
        
        # Compare with estimated_cost
        if estimated_cost and estimated_cost > 0:
            diff = abs(claim_amount - estimated_cost)
            diff_pct = (diff / max(claim_amount, estimated_cost)) * 100
            if diff_pct > 20:  # More than 20% difference
                matches = False
                if difference == 0:
                    difference = diff
                    difference_percent = diff_pct
                warnings.append(f"Claim amount (${claim_amount:,.2f}) differs from estimated cost (${estimated_cost:,.2f}) by {diff_pct:.1f}%")
        
        # Compare with document_amount
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
