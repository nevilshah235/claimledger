"""
Validation Tools - Layer 3 (FREE).

Validate claim data before paid verification.
This tool filters out obviously fake or invalid claims.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal


async def validate_claim_data(
    claim_id: str,
    claim_amount: float,
    extracted_data: Optional[object] = None,
    damage_assessment: Optional[object] = None,
    cost_analysis: Optional[object] = None,
    cross_check_result: Optional[object] = None
) -> object:
    """
    Validate claim data before verification (FREE).
    
    Performs basic validation to filter out obviously fake or invalid claims.
    This is a free tool used before paid verification to save costs.
    
    Args:
        claim_id: Unique claim identifier
        claim_amount: Original claim amount
        extracted_data: Data from extract_document_data
        damage_assessment: Data from extract_image_data
        cost_analysis: Result from estimate_repair_cost
        cross_check_result: Result from cross_check_amounts
        
    Returns:
        {
            "success": bool,
            "valid": bool,
            "validation_score": float (0.0-1.0),
            "issues": [str],
            "recommendation": str,  # "PROCEED", "REJECT", "REVIEW"
            "cost": 0.0  # FREE
        }
    """
    try:
        issues = []
        validation_score = 1.0
        
        # Check if we have any data
        has_data = bool(extracted_data or damage_assessment)
        if not has_data:
            issues.append("No extracted data available")
            validation_score = 0.0
            return {
                "success": True,
                "valid": False,
                "validation_score": validation_score,
                "issues": issues,
                "recommendation": "REJECT",
                "cost": 0.0
            }
        
        # Check amount consistency
        if cross_check_result:
            if not cross_check_result.get("matches", True):
                issues.extend(cross_check_result.get("warnings", []))
                validation_score -= 0.3
            
            if cross_check_result.get("difference_percent", 0) > 50:
                issues.append("Extreme amount mismatch (>50%)")
                validation_score -= 0.5
        
        # Check extracted data quality
        if extracted_data:
            extracted_fields = extracted_data.get("extracted_fields", {})
            if not extracted_fields:
                issues.append("No fields extracted from document")
                validation_score -= 0.2
            
            # Check for suspicious patterns
            amount = extracted_fields.get("amount")
            if amount and amount <= 0:
                issues.append("Invalid or zero amount in document")
                validation_score -= 0.3
        
        # Check damage assessment quality
        if damage_assessment:
            if not damage_assessment.get("damage_type"):
                issues.append("No damage type identified in image")
                validation_score -= 0.2
            
            estimated_cost = damage_assessment.get("estimated_cost")
            if estimated_cost and estimated_cost <= 0:
                issues.append("Invalid or zero estimated cost")
                validation_score -= 0.3
        
        # Determine recommendation
        validation_score = max(0.0, min(1.0, validation_score))
        
        if validation_score < 0.3:
            recommendation = "REJECT"
        elif validation_score < 0.7:
            recommendation = "REVIEW"
        else:
            recommendation = "PROCEED"
        
        return {
            "success": True,
            "valid": validation_score >= 0.5,
            "validation_score": validation_score,
            "issues": issues,
            "recommendation": recommendation,
            "cost": 0.0  # FREE
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "valid": False,
            "validation_score": 0.0,
            "issues": [f"Validation error: {str(e)}"],
            "recommendation": "REVIEW",
            "cost": 0.0
        }
