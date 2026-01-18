"""
Extraction Tools - Layer 1 (FREE).

Extract data from documents and images without verification.
These tools are free and used before paid verification.
"""

from typing import Dict, Any
from .adk_agents.document_agent import ADKDocumentAgent
from .adk_agents.image_agent import ADKImageAgent


async def extract_document_data(claim_id: str, document_path: str) -> object:
    """
    Extract data from a document (FREE - no verification).
    
    This is a free extraction tool that extracts data without verification.
    Use this before calling verify_document to save costs.
    
    Args:
        claim_id: Unique claim identifier
        document_path: Path to the document file
        
    Returns:
        {
            "success": bool,
            "extracted_data": {...},
            "confidence": float,
            "cost": 0.0  # FREE
        }
    """
    try:
        document_agent = ADKDocumentAgent()
        result = await document_agent.analyze(
            claim_id,
            [{"file_path": document_path}]
        )
        
        return {
            "success": True,
            "extracted_data": result.get("extracted_data", {}),
            "confidence": result.get("confidence", 0.0),
            "valid": result.get("valid", False),
            "cost": 0.0  # FREE extraction
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {},
            "confidence": 0.0,
            "cost": 0.0
        }


async def extract_image_data(claim_id: str, image_path: str) -> object:
    """
    Extract data from an image (FREE - no verification).
    
    This is a free extraction tool that extracts damage assessment without verification.
    Use this before calling verify_image to save costs.
    
    Args:
        claim_id: Unique claim identifier
        image_path: Path to the image file
        
    Returns:
        {
            "success": bool,
            "damage_assessment": {...},
            "confidence": float,
            "cost": 0.0  # FREE
        }
    """
    try:
        image_agent = ADKImageAgent()
        result = await image_agent.analyze(
            claim_id,
            [{"file_path": image_path}]
        )
        
        return {
            "success": True,
            "damage_assessment": result.get("damage_assessment", {}),
            "confidence": result.get("confidence", 0.0),
            "valid": result.get("valid", False),
            "cost": 0.0  # FREE extraction
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "damage_assessment": {},
            "confidence": 0.0,
            "cost": 0.0
        }
