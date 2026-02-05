from langchain_core.tools import tool
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

# Environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DEFAULT_CAMPUS = "Dartmouth College, Hanover, NH"

@tool
async def validate_address(address: str) -> Dict[str, Any]:
    """
    Verify that an address exists and is correctly formatted.
    Use this to check user input before calculating distances.
    
    Args:
        address: The address to validate (e.g., "Baker Libary, Hanover NH")
    
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
async def get_distance(origin:str, destination:str, mode: str = "walking") -> str:
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

@tool
def query_classrooms_basic(
    seminar_setup: bool = False,
    lecture_setup: bool = False,
    group_learning: bool = False,
    class_size: Optional[int] = None,
    department_name: Optional[str] = None
) -> str:
    """
    Query classrooms based on essential criteria: class style (seminar, lecture, or group learning) and class size.
    Use this tool when you have collected the basic requirements from the user.
    
    Args:
        seminar_setup: Whether the classroom should support seminar-style teaching
        lecture_setup: Whether the classroom should support lecture-style teaching
        group_learning: Whether the classroom should support group learning
        class_size: The expected class size (number of students)
        department_name: The department name for context (optional)
    
    Returns:
        A formatted string with classroom results
    """
    try:
        # Build SQL query
        conditions = []
        params = []
        
        if seminar_setup:
            conditions.append('"seminarSetup" = %s')
            params.append(True)
        if lecture_setup:
            conditions.append('"lectureSetup" = %s')
            params.append(True)
        if group_learning:
            conditions.append('"groupLearning" = %s')
            params.append(True)
        if class_size:
            conditions.append('"seatCount" >= %s AND "seatCount" <= %s')
            params.extend([max(1, class_size - 5), class_size + 10])
        
        query = 'SELECT * FROM "Classroom"'
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " LIMIT 50"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                classrooms = cur.fetchall()
        
        if not classrooms:
            return "No classrooms found matching the basic criteria. Try adjusting the requirements."
        
        # Format results for LLM
        result_text = f"Found {len(classrooms)} classrooms:\n\n"
        for classroom in classrooms[:10]:  # Show top 10
            result_text += f"- {classroom['building']} {classroom['room']}: {classroom['seatCount']} seats\n"
        
        return result_text
        
    except Exception as e:
        return f"Error querying classrooms: {str(e)}"


@tool
def query_classrooms_with_amenities(
    seminar_setup: bool = False,
    lecture_setup: bool = False,
    group_learning: bool = False,
    class_size: Optional[int] = None,
    department_name: Optional[str] = None,
    projection_surface: Optional[str] = None,
    computer: Optional[str] = None,
    microphone: Optional[str] = None,
    zoom_room: Optional[str] = None,
    classroom_capture: Optional[bool] = None,
    group_learning_screens: Optional[bool] = None,
    white_board: Optional[bool] = None,
    chalk_board: Optional[bool] = None,
    dual_board_screen_use: Optional[bool] = None,
    group_learning_boards: Optional[bool] = None,
    teaching_station: Optional[str] = None,
    windows: Optional[bool] = None,
    ac: Optional[bool] = None,
    floor_type: Optional[str] = None,
    furniture: Optional[str] = None,
    film_screening: Optional[bool] = None
) -> str:
    """
    Query classrooms with specific amenities and features.
    Use this tool when the user has specified detailed requirements beyond just class style and size.
    
    Args:
        seminar_setup: Supports seminar-style teaching
        lecture_setup: Supports lecture-style teaching
        group_learning: Supports group learning
        class_size: Expected class size
        department_name: Department name (optional)
        projection_surface: Type of projection surface
        computer: Type of computer available
        microphone: Type of microphone system
        zoom_room: Type of Zoom room setup
        classroom_capture: Has classroom capture system
        group_learning_screens: Has group learning screens
        white_board: Has whiteboard
        chalk_board: Has chalkboard
        dual_board_screen_use: Supports dual board/screen use
        group_learning_boards: Has group learning boards
        teaching_station: Type of teaching station
        windows: Has windows
        ac: Has air conditioning
        floor_type: Type of floor
        furniture: Type of furniture
        film_screening: Supports film screening
    
    Returns:
        A formatted string with detailed classroom results
    """
    try:
        # Build SQL query
        conditions = []
        params = []
        
        # Essential criteria
        if seminar_setup:
            conditions.append('"seminarSetup" = %s')
            params.append(True)
        if lecture_setup:
            conditions.append('"lectureSetup" = %s')
            params.append(True)
        if group_learning:
            conditions.append('"groupLearning" = %s')
            params.append(True)
        if class_size:
            conditions.append('"seatCount" >= %s AND "seatCount" <= %s')
            params.extend([max(1, class_size - 5), class_size + 10])
        
        # Amenities - string fields
        if projection_surface:
            conditions.append('"projectionSurface" = %s')
            params.append(projection_surface)
        if computer:
            conditions.append('"computer" = %s')
            params.append(computer)
        if microphone:
            conditions.append('"microphone" = %s')
            params.append(microphone)
        if zoom_room:
            conditions.append('"zoomRoom" = %s')
            params.append(zoom_room)
        if teaching_station:
            conditions.append('"teachingStation" = %s')
            params.append(teaching_station)
        if floor_type:
            conditions.append('"floorType" = %s')
            params.append(floor_type)
        if furniture:
            conditions.append('"furniture" = %s')
            params.append(furniture)
            
        # Amenities - boolean fields
        if classroom_capture is not None:
            conditions.append('"classroomCapture" = %s')
            params.append(classroom_capture)
        if group_learning_screens is not None:
            conditions.append('"groupLearningScreens" = %s')
            params.append(group_learning_screens)
        if white_board is not None:
            conditions.append('"whiteBoard" = %s')
            params.append(white_board)
        if chalk_board is not None:
            conditions.append('"chalkBoard" = %s')
            params.append(chalk_board)
        if dual_board_screen_use is not None:
            conditions.append('"dualBoardScreenUse" = %s')
            params.append(dual_board_screen_use)
        if group_learning_boards is not None:
            conditions.append('"groupLearningBoards" = %s')
            params.append(group_learning_boards)
        if windows is not None:
            conditions.append('"windows" = %s')
            params.append(windows)
        if ac is not None:
            conditions.append('"ac" = %s')
            params.append(ac)
        if film_screening is not None:
            conditions.append('"filmScreening" = %s')
            params.append(film_screening)
        
        query = 'SELECT * FROM "Classroom"'
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " LIMIT 3"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                classrooms = cur.fetchall()
        
        if not classrooms:
            return "No classrooms found matching all the specified amenities. Consider relaxing some requirements."
        
        # Format detailed results
        result_text = f"Found {len(classrooms)} classroom(s) with your amenities:\n\n"
        for classroom in classrooms:
            result_text += f"- {classroom['building']} {classroom['room']}: {classroom['seatCount']} seats\n"
        
        return result_text
        
    except Exception as e:
        return f"Error querying classrooms with amenities: {str(e)}"

tools = [validate_address, get_distance, sort_classrooms_by_distance, query_classrooms_basic, query_classrooms_with_amenities]
