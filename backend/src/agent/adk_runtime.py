"""
ADK Runtime Configuration.

Sets up ADK Runtime with SessionService, MemoryService, and ArtifactService
for claim evaluation sessions.
"""

import os
from typing import Optional

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    # Memory and Artifact services may be optional or have different names
    # We'll configure them as needed
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    Runner = None
    InMemorySessionService = None


class ADKRuntime:
    """ADK Runtime manager for claim evaluation."""
    
    def __init__(self):
        if not ADK_AVAILABLE:
            raise ImportError(
                "google-adk is not installed. Install it with: pip install google-adk"
            )
        
        # Initialize session service (in-memory for local development)
        # For production, we can use VertexAiSessionService or DatabaseSessionService
        self.session_service = InMemorySessionService()
        
        # Note: Runner is created per-agent in agent classes
        # We just provide the session service here
        # Individual agents will create runners with app_name and agent parameters
    
    def create_runner(self, app_name: str, agent) -> Runner:
        """Create an ADK runner instance for a specific agent."""
        return Runner(
            app_name=app_name,
            agent=agent,
            session_service=self.session_service,
        )
    
    def get_session_service(self) -> InMemorySessionService:
        """Get the session service instance."""
        return self.session_service


# Singleton instance
_runtime: Optional[ADKRuntime] = None


def get_adk_runtime() -> ADKRuntime:
    """Get or create the ADK runtime singleton."""
    global _runtime
    if _runtime is None:
        if not ADK_AVAILABLE:
            raise ImportError(
                "google-adk is not installed. Install it with: pip install google-adk"
            )
        _runtime = ADKRuntime()
    return _runtime
