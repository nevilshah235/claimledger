"""
ADK Tool Wrappers.

Wraps existing tool functions as ADK FunctionTool instances.
"""

from typing import Dict, Any

try:
    from google.adk.tools import FunctionTool
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    FunctionTool = None

from .tools import (
    verify_document,
    verify_image,
    verify_fraud,
    approve_claim,
)


def create_adk_tools():
    """
    Create ADK FunctionTool instances for all claim evaluation tools.
    
    Returns:
        List of FunctionTool instances
    """
    if not ADK_AVAILABLE:
        return []
    
    tools = [
        FunctionTool(
            verify_document,
            name="verify_document",
            description="Verify a document (invoice, receipt, etc.) for authenticity and extract data. Costs $0.10 USDC.",
        ),
        FunctionTool(
            verify_image,
            name="verify_image",
            description="Analyze an image (damage photos, etc.) to assess damage and validity. Costs $0.15 USDC.",
        ),
        FunctionTool(
            verify_fraud,
            name="verify_fraud",
            description="Check for fraud indicators on a claim. Costs $0.10 USDC.",
        ),
        FunctionTool(
            approve_claim,
            name="approve_claim",
            description="Approve a claim and trigger USDC settlement on Arc blockchain. Only call if confidence >= 0.85.",
        ),
    ]
    
    return tools


def get_adk_tools() -> list:
    """Get all ADK tools."""
    return create_adk_tools()
