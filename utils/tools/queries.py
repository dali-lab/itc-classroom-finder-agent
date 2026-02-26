"""
Database query tools for classroom searches.
Handles basic and advanced classroom queries with various filters and amenities.
"""

from langchain_core.tools import tool
from typing import Optional, Tuple, Any, List
from ..db import get_db_connection


def _rows_to_dicts(classrooms) -> List[dict]:
    """Convert RealDictRow objects to plain dicts."""
    return [dict(row) for row in classrooms]


def _format_classrooms_for_llm(classroom_dicts: List[dict]) -> str:
    """Format classroom dicts into a concise text summary the LLM can reference."""
    lines = []
    for c in classroom_dicts:
        features = []
        if c.get('seminarSetup'):
            features.append('seminar')
        if c.get('lectureSetup'):
            features.append('lecture')
        if c.get('groupLearning'):
            features.append('group learning')
        if c.get('projectionSurface'):
            features.append(f"projection: {c['projectionSurface']}")
        if c.get('whiteBoard'):
            features.append('whiteboard')
        if c.get('chalkBoard'):
            features.append('chalkboard')
        if c.get('zoomRoom'):
            features.append(f"Zoom: {c['zoomRoom']}")
        if c.get('classroomCapture'):
            features.append('classroom capture')
        if c.get('ac'):
            features.append('AC')
        feat_str = ', '.join(features) if features else 'no special features listed'
        lines.append(
            f"- {c.get('building', '?')} {c.get('room', '?')}: "
            f"{c.get('seatCount', '?')} seats | {feat_str}"
        )
    return '\n'.join(lines)


@tool
def find_acronyms(text: str) -> str:
    """
    Find acronyms in the given text and expand them to full building names with location.
    ALWAYS use this tool FIRST when users mention building acronyms (HOP, FOCO, ECSC, LSC, etc.) before calling distance or address validation tools.
    This tool automatically expands acronyms to full building names suitable for address lookups.
    For example: "HOP" → "Hopkins Center, Hanover, NH" or "FOCO" → "Class of 1953 Dining Room, Hanover, NH".
    """
    import re
    acronyms = {
        'ECSC': 'Engineering Computer Science Center',
        'LSC': 'Life Science Center',
        'VAC': 'Visual Arts Center',
        'BVAC': 'Black Family Visual Arts Center',
        'BAKER': 'Baker Berry Library',
        'Berry': 'Baker Berry Library',
        'FFB': 'Baker Berry Library',
        'HOP': 'Hopkins Center',
        'FOCO': 'Class of 1953 Dining Room'
    }
    
    result = text
    for acronym, full_name in acronyms.items():
        # Case-insensitive replacement with word boundaries to match only whole words
        # \b ensures we match the acronym as a complete word, not part of another word
        pattern = re.compile(r'\b' + re.escape(acronym) + r'\b', re.IGNORECASE)
        # Expand to full name with location for better address matching
        result = pattern.sub(f"{full_name}, Hanover, NH", result)
    
    return result


@tool(response_format="content_and_artifact")
def query_classrooms_basic(
    seminar_setup: bool = False,
    lecture_setup: bool = False,
    group_learning: bool = False,
    class_size: Optional[int] = None,
    department_name: Optional[str] = None
) -> Tuple[str, Any]:
    """
    Query classrooms based on essential criteria: class style (seminar, lecture, or group learning) and class size.
    Use this tool when you have collected the basic requirements from the user.
    ALWAYS use this tool when the user asks to find or see classrooms — do not just describe them in text.
    
    Args:
        seminar_setup: Whether the classroom should support seminar-style teaching
        lecture_setup: Whether the classroom should support lecture-style teaching
        group_learning: Whether the classroom should support group learning
        class_size: The expected class size (number of students)
        department_name: The department name for context (optional)
    
    Returns:
        A tuple of (summary text, list of classroom dicts)
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
            # Any room that fits at least class_size students works — no upper bound
            conditions.append('"seatCount" >= %s')
            params.append(class_size)
        
        query = 'SELECT * FROM "Classroom"'
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY "
        # If a target size was given, prefer rooms closest to it (smallest adequate room first)
        if class_size:
            query += '"seatCount" ASC'
        else:
            query += '"building" ASC, "room" ASC'
        query += " LIMIT 9"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                classrooms = cur.fetchall()
        
        # If no results with style+size filters, retry dropping the style constraint
        if not classrooms and class_size and (seminar_setup or lecture_setup or group_learning):
            fallback_query = 'SELECT * FROM "Classroom" WHERE "seatCount" >= %s ORDER BY "seatCount" ASC LIMIT 9'
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(fallback_query, [class_size])
                    classrooms = cur.fetchall()
            if classrooms:
                classroom_dicts = _rows_to_dicts(classrooms)
                summary = _format_classrooms_for_llm(classroom_dicts)
                return (
                    f"No classrooms matched the exact style filter, but found {len(classroom_dicts)} room(s) with at least {class_size} seats. "
                    f"These are the REAL results — base your response ONLY on this data, do NOT invent or add other classrooms:\n{summary}\n"
                    "The classroom cards are shown in the UI. Tell the user no exact style match was found but here are the closest-fitting options, then offer to refine.",
                    classroom_dicts
                )

        # If still no results, retry with only the style filter (drop size)
        if not classrooms and (seminar_setup or lecture_setup or group_learning):
            style_conditions = []
            style_params = []
            if seminar_setup:
                style_conditions.append('"seminarSetup" = %s')
                style_params.append(True)
            if lecture_setup:
                style_conditions.append('"lectureSetup" = %s')
                style_params.append(True)
            if group_learning:
                style_conditions.append('"groupLearning" = %s')
                style_params.append(True)
            fallback_query = 'SELECT * FROM "Classroom" WHERE ' + ' AND '.join(style_conditions) + ' ORDER BY "seatCount" ASC LIMIT 9'
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(fallback_query, style_params)
                    classrooms = cur.fetchall()
            if classrooms:
                classroom_dicts = _rows_to_dicts(classrooms)
                summary = _format_classrooms_for_llm(classroom_dicts)
                return (
                    f"No classrooms matched all criteria, but found {len(classroom_dicts)} room(s) with the requested style. "
                    f"These are the REAL results — base your response ONLY on this data:\n{summary}\n"
                    "The classroom cards are shown in the UI. Tell the user these are the closest matches and offer to refine.",
                    classroom_dicts
                )

        if not classrooms:
            return (
                "No classrooms found even after relaxing the filters. Inform the user no results were found and ask them to try different criteria (e.g. different style or size). Do NOT route to contacts.",
                []
            )
        
        classroom_dicts = _rows_to_dicts(classrooms)
        summary = _format_classrooms_for_llm(classroom_dicts)
        result_text = (
            f"Found {len(classroom_dicts)} classroom(s) matching the criteria. "
            f"These are the REAL results — base your response ONLY on this data, do NOT invent or add other classrooms:\n{summary}\n"
            "The classroom cards are already shown to the user in the UI. "
            "Write a SHORT 1-2 sentence summary referencing these specific rooms (building + room number), then offer to refine."
        )
        return (result_text, classroom_dicts)
        
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
) -> Tuple[str, Any]:
    """
    Query classrooms with specific amenities and features.
    Use this tool when the user has specified detailed requirements beyond just class style and size.
    ALWAYS use this tool when the user asks to find or see classrooms — do not just describe them in text.
    
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
        A tuple of (summary text, list of classroom dicts)
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
            # Any room that fits at least class_size students works — no upper bound
            conditions.append('"seatCount" >= %s')
            params.append(class_size)
        
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
        query += " ORDER BY " + ('"seatCount" ASC' if class_size else '"building" ASC, "room" ASC')
        query += " LIMIT 9"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                classrooms = cur.fetchall()

        # If no results, progressively relax constraints and retry
        if not classrooms:
            # Drop amenity filters but keep style + size
            relaxed_conditions = []
            relaxed_params = []
            if seminar_setup:
                relaxed_conditions.append('"seminarSetup" = %s')
                relaxed_params.append(True)
            if lecture_setup:
                relaxed_conditions.append('"lectureSetup" = %s')
                relaxed_params.append(True)
            if group_learning:
                relaxed_conditions.append('"groupLearning" = %s')
                relaxed_params.append(True)
            if class_size:
                relaxed_conditions.append('"seatCount" >= %s')
                relaxed_params.append(class_size)
            fallback_query = 'SELECT * FROM "Classroom"'
            if relaxed_conditions:
                fallback_query += " WHERE " + " AND ".join(relaxed_conditions)
            fallback_query += " ORDER BY " + ('"seatCount" ASC' if class_size else '"building" ASC') + " LIMIT 9"
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(fallback_query, relaxed_params)
                    classrooms = cur.fetchall()
            if classrooms:
                classroom_dicts = _rows_to_dicts(classrooms)
                summary = _format_classrooms_for_llm(classroom_dicts)
                return (
                    f"No classrooms matched all amenity requirements, but found {len(classroom_dicts)} room(s) matching style/size. "
                    f"These are the REAL results — base your response ONLY on this data:\n{summary}\n"
                    "Cards are shown in the UI. Tell the user some amenity filters were relaxed and these are the best matches, then offer to refine.",
                    classroom_dicts
                )

        # If still nothing, drop size too and just match style
        if not classrooms and (seminar_setup or lecture_setup or group_learning):
            style_conditions = []
            style_params = []
            if seminar_setup:
                style_conditions.append('"seminarSetup" = %s')
                style_params.append(True)
            if lecture_setup:
                style_conditions.append('"lectureSetup" = %s')
                style_params.append(True)
            if group_learning:
                style_conditions.append('"groupLearning" = %s')
                style_params.append(True)
            fallback_query = 'SELECT * FROM "Classroom" WHERE ' + ' AND '.join(style_conditions) + ' ORDER BY "seatCount" ASC LIMIT 9'
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(fallback_query, style_params)
                    classrooms = cur.fetchall()
            if classrooms:
                classroom_dicts = _rows_to_dicts(classrooms)
                summary = _format_classrooms_for_llm(classroom_dicts)
                return (
                    f"No exact match found, but here are {len(classroom_dicts)} room(s) with the requested style. "
                    f"These are the REAL results:\n{summary}\n"
                    "Cards are shown in the UI. Tell the user these are the closest available options and offer to refine.",
                    classroom_dicts
                )

        if not classrooms:
            return (
                "No classrooms found even after relaxing all filters. Inform the user and ask them to try different criteria. Do NOT route to contacts.",
                []
            )
        
        classroom_dicts = _rows_to_dicts(classrooms)
        summary = _format_classrooms_for_llm(classroom_dicts)
        result_text = (
            f"Found {len(classroom_dicts)} classroom(s) matching all specified amenities. "
            f"These are the REAL results — base your response ONLY on this data, do NOT invent or add other classrooms:\n{summary}\n"
            "The classroom cards are already shown to the user in the UI. "
            "Write a SHORT 1-2 sentence summary referencing these specific rooms (building + room number), then offer to refine."
        )
        return (result_text, classroom_dicts)
        
    except Exception as e:
        return (f"Error querying classrooms with amenities: {str(e)}", [])
