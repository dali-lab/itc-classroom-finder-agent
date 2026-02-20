"""
Tools package for the Classroom Finder Agent.
Contains specialized modules for different tool categories.
"""

from .location import validate_address, get_distance, sort_classrooms_by_distance
from .queries import query_classrooms_basic, query_classrooms_with_amenities
from .contacts import get_contact_information

# List of all tools for the agent
tools = [
    validate_address,
    get_distance,
    sort_classrooms_by_distance,
    query_classrooms_basic,
    query_classrooms_with_amenities,
    get_contact_information
]

__all__ = [
    'validate_address',
    'get_distance',
    'sort_classrooms_by_distance',
    'query_classrooms_basic',
    'query_classrooms_with_amenities',
    'get_contact_information',
    'tools'
]
