"""
Location-based tools for classroom distance calculations and sorting.
Uses Google Maps API for distance matrix calculations.
"""

from langchain_core.tools import tool
from typing import List, Dict, Any
import httpx
import os

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DEFAULT_CAMPUS = "Dartmouth College, Hanover, NH"


@tool
async def validate_address(address: str) -> Dict[str, Any]:
    """
    Verify that an address exists and is correctly formatted.
    Use this to check user input before calculating distances.
    
    Args:
        address: The address to validate (e.g., "Baker Library, Hanover NH")
    
    Returns:
        Dictionary with 'valid' status and the corrected/formatted address
    """
    if not GOOGLE_MAPS_API_KEY:
        return {"valid": False, "error": "Google Maps API key not configured"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": GOOGLE_MAPS_API_KEY},
                timeout=10.0
            )
            data = response.json()
        
        if data["status"] != "OK" or not data.get("results"):
            return {
                "valid": False,
                "input": address,
                "error": "Address not found. Please check spelling or add more details."
            }
        
        result = data["results"][0]
        return {
            "valid": True,
            "input": address,
            "formatted_address": result["formatted_address"],
            "location_type": result["geometry"]["location_type"]  # ROOFTOP, APPROXIMATE, etc.
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}


@tool
async def get_distance(origin: str, destination: str, mode: str = "walking") -> str:
    """
    Get travel distance and time between two locations.
    
    Args:
        origin: Starting address
        destination: Ending address  
        mode: "walking", "driving", "bicycling", or "transit"
    """
    if not GOOGLE_MAPS_API_KEY:
        return "Error: Google Maps API key not configured"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params={"origins": origin, "destinations": destination, "mode": mode, "key": GOOGLE_MAPS_API_KEY}
            )
            elem = resp.json()["rows"][0]["elements"][0]
        
        if elem["status"] != "OK":
            return f"Could not find route between locations."
        
        return f"{elem['distance']['text']} ({elem['duration']['text']} {mode})"
    except Exception as e:
        return f"Error: {e}"


@tool
async def sort_classrooms_by_distance(
    origin: str,
    classrooms: List[Dict[str, Any]],
    mode: str = "walking"
) -> str:
    """
    Sort classrooms by distance from an origin, closest first.
    
    Args:
        origin: Starting address (e.g., "Baker Library, Hanover NH")
        classrooms: List of classroom dicts with 'building', 'room', 'seatCount'
        mode: "walking", "driving", "bicycling", or "transit"
    """
    if not GOOGLE_MAPS_API_KEY:
        return "Error: Google Maps API key not configured"
    
    if not classrooms:
        return "No classrooms to sort."
    
    try:
        # Build addresses from building names
        destinations = [f"{c.get('building', 'Unknown')}, {DEFAULT_CAMPUS}" for c in classrooms]
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params={
                    "origins": origin,
                    "destinations": "|".join(destinations),
                    "mode": mode,
                    "key": GOOGLE_MAPS_API_KEY
                },
                timeout=15.0
            )
            elements = resp.json()["rows"][0]["elements"]
        
        # Pair classrooms with distances, filter failures
        results = [
            {**c, "dist": e["distance"]["value"], "dist_text": e["distance"]["text"], "time": e["duration"]["text"]}
            for c, e in zip(classrooms, elements) if e["status"] == "OK"
        ]
        results.sort(key=lambda x: x["dist"])
        
        # Format output same format as def query_classrooms_basic
        result_text = f"Found {len(results)} classrooms:\n\n"
        for c in results:
            result_text += f"- {c['building']} {c['room']}: {c['seatCount']} seats ({c['dist_text']}, {c['time']} {mode})\n"
        
        return result_text
        
    except Exception as e:
        return f"Error: {e}"
