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
from .tools_extraction import (
    extract_document_data,
    extract_image_data,
)
from .tools_cost_estimation import (
    estimate_repair_cost,
    cross_check_amounts,
)
from .tools_validation import (
    validate_claim_data,
)


def create_adk_tools():
    """
    Create ADK FunctionTool instances for all claim evaluation tools.
    
    Returns:
        List of FunctionTool instances
    """
    if not ADK_AVAILABLE:
        print("⚠️  ADK not available, cannot create tools")
        return []
    
    # FunctionTool only accepts the function itself
    # It infers name from function.__name__ and description from function.__doc__
    try:
        # Layer 1: Extraction tools (FREE)
        extraction_tools = [
            FunctionTool(extract_document_data),
            FunctionTool(extract_image_data),
        ]
        
        # Layer 2: Cost estimation tools (FREE)
        cost_tools = [
            FunctionTool(estimate_repair_cost),
            FunctionTool(cross_check_amounts),
        ]
        
        # Layer 3: Validation tool (FREE)
        validation_tools = [
            FunctionTool(validate_claim_data),
        ]
        
        # Layer 4: Verification tools (free)
        verification_tools = [
            FunctionTool(verify_document),
            FunctionTool(verify_image),
            FunctionTool(verify_fraud),
        ]
        
        # Settlement tool
        settlement_tools = [
            FunctionTool(approve_claim),
        ]
        
        # Combine all tools
        tools = extraction_tools + cost_tools + validation_tools + verification_tools + settlement_tools
        tool_names = [getattr(t, 'name', None) or getattr(t, '__name__', 'unknown') for t in tools]
        print(f"   └─ Created {len(tools)} ADK tool(s): {', '.join(tool_names)}")
        return tools
    except Exception as e:
        print(f"❌ Failed to create ADK tools: {e}")
        import traceback
        traceback.print_exc()
        # Return empty list to allow agents to initialize without tools
        # This prevents the entire agent from failing to initialize
        return []


def get_adk_tools() -> list:
    """Get all ADK tools."""
    return create_adk_tools()
