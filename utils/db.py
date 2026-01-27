import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found! Please set it in environment variables."
    )


def get_db_connection():
    """Create a new database connection with RealDictCursor for dict-like row access."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
