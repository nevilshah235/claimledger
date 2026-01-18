"""
Test ADK Agent - Basic agent creation for Phase 1 verification.

This is a simple test agent to verify ADK setup works correctly.
"""

import os
from typing import Optional

try:
    from google.adk.agents import LlmAgent
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    LlmAgent = None


def create_test_agent() -> Optional[LlmAgent]:
    """
    Create a simple test ADK agent to verify setup.
    
    Returns:
        LlmAgent instance if ADK is available, None otherwise
    """
    if not ADK_AVAILABLE:
        return None
    
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️  Warning: GOOGLE_AI_API_KEY or GOOGLE_API_KEY not set")
        return None
    
    try:
        # Create a simple test agent
        agent = LlmAgent(
            model=os.getenv("AGENT_MODEL", "gemini-2.0-flash"),
            name="test_agent",
            description="A simple test agent for ADK setup verification",
            instruction="You are a helpful test agent. Respond briefly to confirm you are working.",
        )
        
        return agent
    except Exception as e:
        print(f"❌ Error creating test agent: {e}")
        return None


async def test_agent_response() -> dict:
    """
    Test the agent with a simple query.
    
    Returns:
        dict with test results
    """
    agent = create_test_agent()
    
    if agent is None:
        return {
            "success": False,
            "error": "Agent creation failed - ADK not available or API key missing",
        }
    
    try:
        # Simple test query
        response = await agent.run_async("Say 'Hello, ADK is working!' in one sentence.")
        
        return {
            "success": True,
            "agent_name": agent.name,
            "response": str(response) if response else "No response",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


if __name__ == "__main__":
    import asyncio
    
    print("🧪 Testing ADK Agent Setup...")
    result = asyncio.run(test_agent_response())
    
    if result["success"]:
        print(f"✅ Test passed!")
        print(f"   Agent: {result['agent_name']}")
        print(f"   Response: {result['response']}")
    else:
        print(f"❌ Test failed: {result['error']}")
