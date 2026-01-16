"""
Constants for API routes and configuration.
"""
import os

# Backend URL - should be set via environment variable
BACKEND_URL = os.getenv("BACKEND_URL")


class Routes:
    """
    API route constants for backend endpoints.
    Automatically builds full URLs using BACKEND_URL from environment.
    """
    
    @staticmethod
    def _build_url(endpoint: str) -> str:
        """Build full URL from endpoint path."""
        return f"{BACKEND_URL}{endpoint}"
    
    # Classroom endpoints
    classrooms = property(lambda self: Routes._build_url("/classrooms/filter"))
    
    # Add more endpoints here as needed
    # users = property(lambda self: Routes._build_url("/users"))
    # submissions = property(lambda self: Routes._build_url("/submissions"))


# Create a singleton instance for easy access
ROUTES = Routes()
