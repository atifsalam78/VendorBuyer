import os
from pathlib import Path

# Use SQLite for development
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR}/bazaarhub.db"

# For production, uncomment and configure PostgreSQL
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost/bazaarhub"