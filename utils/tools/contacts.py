"""
Contact information routing system for the Classroom Finder Agent.
Matches user queries to appropriate Dartmouth contacts using keyword-based classification.
"""

import yaml
from typing import List, Dict, Any
from pathlib import Path
from langchain_core.tools import tool

# Load contacts configuration
config_path = Path(__file__).parent / "contacts_config.yaml"
with open(config_path, 'r') as f:
    CONTACTS_CONFIG = yaml.safe_load(f)

CONTACTS = CONTACTS_CONFIG.get('contacts', [])
ROUTING_RULES = CONTACTS_CONFIG.get('routing_rules', [])


def find_relevant_contacts(query: str, max_contacts: int = 2) -> List[Dict[str, Any]]:
    """
    Find the most relevant contacts based on the user's query.
    
    Args:
        query: The user's question or request
        max_contacts: Maximum number of contacts to return
        
    Returns:
        List of contact dictionaries with match scores
    """
    import re
    query_lower = query.lower()
    contact_scores = []
    
    for contact in CONTACTS:
        score = 0
        matched_keywords = []
        
        # Check keyword matches with word boundaries to avoid partial matches
        for keyword in contact.get('keywords', []):
            keyword_lower = keyword.lower()
            # Use word boundaries for multi-word keywords or single words
            # This prevents "av" from matching "available"
            if len(keyword_lower) <= 2:
                # For very short keywords, require exact word match
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            else:
                # For longer keywords, allow partial matches within words
                pattern = r'\b' + re.escape(keyword_lower)
            
            if re.search(pattern, query_lower):
                score += 1
                matched_keywords.append(keyword)
        
        if score > 0:
            contact_scores.append({
                'contact': contact,
                'score': score,
                'matched_keywords': matched_keywords
            })
    
    # Sort by score (descending)
    contact_scores.sort(key=lambda x: x['score'], reverse=True)
    
    # Return top matches
    return contact_scores[:max_contacts]


def format_contact_info(contact: Dict[str, Any], include_description: bool = True) -> str:
    """
    Format contact information into a readable string.
    
    Args:
        contact: Contact dictionary
        include_description: Whether to include the description
        
    Returns:
        Formatted contact information string
    """
    parts = [f"**{contact['name']}**"]
    
    if include_description and contact.get('description'):
        parts.append(f"{contact['description']}")
    
    contact_details = []
    if contact.get('email'):
        contact_details.append(f"📧 Email: {contact['email']}")
    if contact.get('phone'):
        phone_text = f"📞 Phone: {contact['phone']}"
        if contact.get('phone_tollfree'):
            phone_text += f" or {contact['phone_tollfree']} (toll-free)"
        contact_details.append(phone_text)
    if contact.get('website'):
        contact_details.append(f"🌐 Website: {contact['website']}")
    if contact.get('hours'):
        contact_details.append(f"🕒 Hours: {contact['hours']}")
    
    if contact_details:
        parts.append("\n".join(contact_details))
    
    return "\n".join(parts)


def get_contact_information_helper(query: str) -> str:
    """
    Main function to get contact information based on user query.
    This is the helper function called by the LangChain tool.
    
    Args:
        query: The user's question or request
        
    Returns:
        Formatted string with relevant contact information
    """
    matches = find_relevant_contacts(query, max_contacts=2)
    
    if not matches:
        # No matches found - provide general guidance
        return """I couldn't determine a specific contact for your question. Here are the main resources:

**For booking or scheduling questions:** Contact the Registrar's Office
📧 Email: Registrar@Dartmouth.edu
📞 Phone: 603-646-2246

**For classroom technology or equipment questions:** Contact Classroom Technology Services
📧 Email: Classroom.Technology.Services@Dartmouth.edu
📞 Phone: 603-646-2999
🌐 Website: https://services.dartmouth.edu/TDClient/1806/Portal/Requests/ServiceDet?ID=38206

**For questions about this Classroom Finder tool or general IT support:** Contact ITC Dartmouth
📧 Email: itc@dartmouth.edu
📞 Phone: 603-646-2999 or 1-855-764-2485 (toll-free)
🕒 Hours: Monday through Friday, 8:00 a.m. to 5:00 p.m. (ET)

If you'd like more specific contact information, please provide more details about your question."""
    
    # Format response
    response_parts = []
    
    if len(matches) == 1:
        # Single clear match
        match = matches[0]
        response_parts.append("For your question, you should contact:")
        response_parts.append("")
        response_parts.append(format_contact_info(match['contact']))
    else:
        # Multiple possible matches
        response_parts.append("Based on your question, here are the relevant contacts:")
        response_parts.append("")
        for i, match in enumerate(matches, 1):
            if i > 1:
                response_parts.append("")
            response_parts.append(format_contact_info(match['contact']))
    
    return "\n".join(response_parts)


@tool
def get_contact_information(query: str) -> str:
    """
    Get contact information for Dartmouth offices based on the user's question or request.
    Use this tool when the user asks questions about:
    - Booking or scheduling classrooms
    - Room availability
    - Classroom technology or equipment issues
    - Accessibility accommodations
    - Timetable editor or course planning
    - Furniture delivery or modifications
    - Parking or transportation
    - Questions beyond the scope of the Classroom Finder tool
    
    This tool helps route users to the appropriate Dartmouth office (Registrar, Technology Services, ITC, or Transportation).
    
    Args:
        query: The user's question or request that needs to be routed to a specific contact
    
    Returns:
        Formatted contact information for the relevant Dartmouth office(s)
    """
    return get_contact_information_helper(query)


def should_route_to_contact(query: str) -> bool:
    """
    Determine if a query should be routed to external contacts.
    
    Common patterns that indicate the agent cannot help directly:
    - Booking/scheduling requests
    - Availability questions
    - Administrative requests
    - Technology troubleshooting
    - Policy questions
    
    Args:
        query: The user's question
        
    Returns:
        True if the query should be routed to a contact
    """
    query_lower = query.lower()
    
    # Patterns that suggest routing needed
    routing_patterns = [
        # Booking & Scheduling
        'book', 'reserve', 'schedule', 'available', 'availability',
        'can i get', 'request',
        
        # Administrative
        'timetable', 'deadline', 'add course', 'change time',
        'exam', 'final',
        
        # Accessibility & Special Needs
        'accessibility', 'disability', 'accommodation',
        
        # Furniture & Modifications
        'furniture', 'deliver', 'add chair', 'add table', 'podium',
        
        # Technology Issues
        'not working', 'broken', 'fix', 'setup', 'training',
        'how to use zoom', 'how to set up',
        
        # Questions beyond agent scope
        'who do i contact', 'where do i', 'how do i',
    ]
    
    return any(pattern in query_lower for pattern in routing_patterns)
