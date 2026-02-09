from langchain_core.tools import tool
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv
from utils.db import get_db_connection
import httpx
import os

load_dotenv()

# Environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DEFAULT_CAMPUS = "Dartmouth College, Hanover, NH"

@tool
def validate_address(address: str) -> Dict[str, Any]:
    """
    Verify that an address exists and is correctly formatted.
    Use this to check user input before calculating distances.

    IMPORTANT: Google Maps often cannot resolve short building names like "ECSC" or "Hitchcock Hall".
    Always try the full building name with "Hanover, NH 03755" appended, e.g. "Cummings Hall, Hanover, NH 03755".
    If a building still can't be found after ONE attempt, tell the user you cannot locate it and ask for a street address.
    Do NOT keep retrying with different variations.

    Args:
        address: The address to validate. Use full names with city/state, e.g. "Cummings Hall, Hanover, NH 03755"

    Returns:
        Dictionary with 'valid' status and the corrected/formatted address
    """
    if not GOOGLE_MAPS_API_KEY:
        return {"valid": False, "error": "Google Maps API key not configured"}

    try:
        response = httpx.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address, "key": GOOGLE_MAPS_API_KEY},
            timeout=10.0
        )
        data = response.json()
        print(f"[DEBUG validate_address] Query: '{address}'")
        print(f"[DEBUG validate_address] API status: {data.get('status')}")
        print(f"[DEBUG validate_address] Error message: {data.get('error_message', 'none')}")
        print(f"[DEBUG validate_address] Results count: {len(data.get('results', []))}")

        if data["status"] != "OK" or not data.get("results"):
            return {
                "valid": False,
                "input": address,
                "error": f"Address not found. API status: {data.get('status')}. {data.get('error_message', '')}"
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
def get_distance(origin: str, destination: str, mode: str = "walking") -> str:
    """
    Get travel distance and time between two locations.

    IMPORTANT: Use full addresses with city/state (e.g. "Cummings Hall, Hanover, NH 03755"),
    not abbreviations or short building names. If the result fails, ask the user for a street address
    rather than retrying with variations.

    Args:
        origin: Starting address (use full address with city/state)
        destination: Ending address (use full address with city/state)
        mode: "walking", "driving", "bicycling", or "transit"
    """
    if not GOOGLE_MAPS_API_KEY:
        return "Error: Google Maps API key not configured"

    try:
        resp = httpx.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params={"origins": origin, "destinations": destination, "mode": mode, "key": GOOGLE_MAPS_API_KEY},
            timeout=10.0
        )
        data = resp.json()

        if data.get("status") != "OK":
            return f"Could not find route. API status: {data.get('status')}. Try using a full street address."

        rows = data.get("rows", [])
        if not rows or not rows[0].get("elements"):
            return "Could not find route between these locations. Try using full street addresses instead of building names."

        elem = rows[0]["elements"][0]

        if elem["status"] != "OK":
            return f"Could not find route between locations. Status: {elem['status']}. Try using full street addresses."

        return f"{elem['distance']['text']} ({elem['duration']['text']} {mode})"
    except Exception as e:
        return f"Error: {e}"

@tool
def sort_classrooms_by_distance(
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

        resp = httpx.get(
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

def _serialize_classrooms(classrooms) -> List[Dict[str, Any]]:
    """Convert RealDictRow objects to JSON-serializable dicts."""
    result = []
    for row in classrooms:
        classroom = dict(row)
        # Convert datetime fields to ISO strings
        for key in ("createdAt", "updatedAt"):
            if key in classroom and classroom[key] is not None:
                classroom[key] = classroom[key].isoformat()
        result.append(classroom)
    return result


@tool(response_format="content_and_artifact")
def query_classrooms_basic(
    seminar_setup: bool = False,
    lecture_setup: bool = False,
    group_learning: bool = False,
    class_size: Optional[int] = None,
    department_name: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
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
        A tuple of (formatted text for the LLM, list of classroom dicts)
    """
    try:
        # Build SQL query
        conditions = []
        params = []

        # Use IS NOT FALSE to include NULL values (unknown = not excluded)
        if seminar_setup:
            conditions.append('"seminarSetup" IS NOT FALSE')
        if lecture_setup:
            conditions.append('"lectureSetup" IS NOT FALSE')
        if group_learning:
            conditions.append('"groupLearning" IS NOT FALSE')
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
            return ("No classrooms found matching the basic criteria. Try adjusting the requirements.", [])

        # Format results for LLM
        result_text = f"Found {len(classrooms)} classrooms:\n\n"
        for classroom in classrooms[:10]:  # Show top 10
            result_text += f"- {classroom['building']} {classroom['room']}: {classroom['seatCount']} seats\n"

        return (result_text, _serialize_classrooms(classrooms[:10]))

    except Exception as e:
        return (f"Error querying classrooms: {str(e)}", [])


@tool(response_format="content_and_artifact")
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
) -> Tuple[str, List[Dict[str, Any]]]:
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
        A tuple of (formatted text for the LLM, list of classroom dicts)
    """
    try:
        # Build SQL query
        conditions = []
        params = []

        # Essential criteria — use IS NOT FALSE to include NULL values
        if seminar_setup:
            conditions.append('"seminarSetup" IS NOT FALSE')
        if lecture_setup:
            conditions.append('"lectureSetup" IS NOT FALSE')
        if group_learning:
            conditions.append('"groupLearning" IS NOT FALSE')
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

        # Amenities - boolean fields (IS NOT FALSE includes NULLs)
        if classroom_capture is not None:
            conditions.append('"classroomCapture" IS NOT FALSE' if classroom_capture else '"classroomCapture" = FALSE')
        if group_learning_screens is not None:
            conditions.append('"groupLearningScreens" IS NOT FALSE' if group_learning_screens else '"groupLearningScreens" = FALSE')
        if white_board is not None:
            conditions.append('"whiteBoard" IS NOT FALSE' if white_board else '"whiteBoard" = FALSE')
        if chalk_board is not None:
            conditions.append('"chalkBoard" IS NOT FALSE' if chalk_board else '"chalkBoard" = FALSE')
        if dual_board_screen_use is not None:
            conditions.append('"dualBoardScreenUse" IS NOT FALSE' if dual_board_screen_use else '"dualBoardScreenUse" = FALSE')
        if group_learning_boards is not None:
            conditions.append('"groupLearningBoards" IS NOT FALSE' if group_learning_boards else '"groupLearningBoards" = FALSE')
        if windows is not None:
            conditions.append('"windows" IS NOT FALSE' if windows else '"windows" = FALSE')
        if ac is not None:
            conditions.append('"ac" IS NOT FALSE' if ac else '"ac" = FALSE')
        if film_screening is not None:
            conditions.append('"filmScreening" IS NOT FALSE' if film_screening else '"filmScreening" = FALSE')

        query = 'SELECT * FROM "Classroom"'
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " LIMIT 3"

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                classrooms = cur.fetchall()

        if not classrooms:
            return ("No classrooms found matching all the specified amenities. Consider relaxing some requirements.", [])

        # Format detailed results
        result_text = f"Found {len(classrooms)} classroom(s) with your amenities:\n\n"
        for classroom in classrooms:
            result_text += f"- {classroom['building']} {classroom['room']}: {classroom['seatCount']} seats\n"

        return (result_text, _serialize_classrooms(classrooms))

    except Exception as e:
        return (f"Error querying classrooms with amenities: {str(e)}", [])

tools = [validate_address, get_distance, sort_classrooms_by_distance, query_classrooms_basic, query_classrooms_with_amenities]
