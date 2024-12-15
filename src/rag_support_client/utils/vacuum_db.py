"""
Utility script to vacuum ChromaDB database.
"""

import logging
import sqlite3
from pathlib import Path

# Configuration
CHROMA_PERSIST_DIRECTORY = "./data/vector_store"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Setup logging
logging.basicConfig(level="INFO", format=LOG_FORMAT)
logger = logging.getLogger("vacuum_db")


def vacuum_database():
    """Vacuum ChromaDB SQLite database to optimize storage."""
    try:
        # Le fichier SQLite de ChromaDB est dans le dossier de persistance
        db_path = Path(CHROMA_PERSIST_DIRECTORY) / "chroma.sqlite3"

        if not db_path.exists():
            logger.warning(f"Database file not found at {db_path}")
            return

        # Connecter et vacuum la base SQLite
        logger.info(f"Starting vacuum of database at {db_path}")
        conn = sqlite3.connect(str(db_path))
        conn.execute("VACUUM")
        conn.close()

        logger.info("Successfully vacuumed ChromaDB database")
    except Exception as e:
        logger.error(f"Error vacuuming database: {str(e)}")
        raise


if __name__ == "__main__":
    vacuum_database()
