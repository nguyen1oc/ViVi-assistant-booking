from langchain_core.tools import tool


@tool
def request_user_location(reason: str = "find_nearby_showrooms") -> dict:
    """Ask the browser client to request current GPS coordinates from the user."""
    return {
        "requires_client_geolocation": True,
        "reason": reason,
        "suggested_next_action": "request_browser_geolocation",
    }
