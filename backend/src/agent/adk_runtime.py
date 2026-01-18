"""
ADK Runtime Configuration.

Sets up ADK Runtime with SessionService, MemoryService, and ArtifactService
for claim evaluation sessions.
"""

import os
from typing import Optional, Any

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
        
        # Ensure GOOGLE_API_KEY is set for ADK (ADK uses GOOGLE_API_KEY, not GOOGLE_AI_API_KEY)
        # If GOOGLE_AI_API_KEY is set but GOOGLE_API_KEY is not, copy it
        google_ai_key = os.getenv("GOOGLE_AI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        
        if google_ai_key and not google_key:
            # Set GOOGLE_API_KEY from GOOGLE_AI_API_KEY for ADK compatibility
            os.environ["GOOGLE_API_KEY"] = google_ai_key
            print("   └─ Set GOOGLE_API_KEY from GOOGLE_AI_API_KEY for ADK compatibility")
        elif not google_key and not google_ai_key:
            print("   ⚠ Warning: Neither GOOGLE_API_KEY nor GOOGLE_AI_API_KEY is set. ADK agents may fail.")
        
        # Initialize session service (in-memory for local development)
        # For production, we can use VertexAiSessionService or DatabaseSessionService
        self.session_service = InMemorySessionService()
        self.app_name = "claimledger"
        
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
    
    async def get_or_create_session(self, user_id: str, session_id: str) -> Any:
        """Get existing session or create a new one if it doesn't exist."""
        try:
            # Try to create session (will succeed if new, or may raise if exists)
            # ADK's InMemorySessionService create_session should handle existing sessions
            session = await self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id
            )
            return session
        except Exception as e:
            # If creation fails (e.g., session already exists), try to get it
            try:
                # Some session services might have a get_session method
                if hasattr(self.session_service, 'get_session'):
                    session = await self.session_service.get_session(
                        app_name=self.app_name,
                        user_id=user_id,
                        session_id=session_id
                    )
                    return session
            except Exception:
                pass
            
            # If both fail, log warning but continue - runner might handle it
            # Some ADK versions might auto-create sessions
            print(f"Warning: Could not ensure session {session_id} exists: {e}")
            return None
    
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
