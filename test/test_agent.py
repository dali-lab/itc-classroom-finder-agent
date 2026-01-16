"""
Quick test script to verify the agent returns classroom data correctly.
"""
import asyncio
from utils.tools import query_classrooms_basic, get_classroom_data, clear_classroom_data

def test_basic_query():
    """Test that tools store classroom data"""
    print("Testing query_classrooms_basic...")
    
    # Clear any previous data
    clear_classroom_data()
    
    # Make a query
    result = query_classrooms_basic(
        seminar_setup=True,
        class_size=20,
        department_name="Economics"
    )
    
    print(f"\nTool returned text:\n{result}\n")
    
    # Get stored classroom data
    classrooms = get_classroom_data()
    
    if classrooms:
        print(f"✓ Successfully stored {len(classrooms)} classrooms")
        print(f"\nFirst classroom example:")
        print(f"  - Building: {classrooms[0]['building']}")
        print(f"  - Room: {classrooms[0]['room']}")
        print(f"  - Seats: {classrooms[0]['seatCount']}")
        print(f"  - Has {len(classrooms[0].keys())} fields total")
    else:
        print("✗ No classroom data was stored")
    
    return classrooms is not None

if __name__ == "__main__":
    success = test_basic_query()
    exit(0 if success else 1)
