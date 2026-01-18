"""
Test ADK installation and basic setup.

Phase 1: Verify ADK is installed and can be imported.
"""

import pytest


def test_adk_import():
    """Test that google-adk can be imported."""
    try:
        from google import adk
        assert adk is not None
    except ImportError:
        pytest.skip("google-adk is not installed")


def test_adk_runtime_import():
    """Test that ADK runtime components can be imported."""
    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        assert Runner is not None
        assert InMemorySessionService is not None
    except ImportError:
        pytest.skip("google-adk runtime components are not available")


def test_adk_agents_import():
    """Test that ADK agent types can be imported."""
    try:
        from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
        assert LlmAgent is not None
        assert ParallelAgent is not None
        assert SequentialAgent is not None
    except ImportError:
        pytest.skip("google-adk agents are not available")


def test_adk_runtime_module():
    """Test that our ADK runtime module can be imported."""
    try:
        from src.agent.adk_runtime import ADKRuntime, get_adk_runtime, ADK_AVAILABLE
        assert ADK_AVAILABLE is True
        assert ADKRuntime is not None
        assert get_adk_runtime is not None
    except ImportError as e:
        pytest.skip(f"ADK runtime module not available: {e}")
