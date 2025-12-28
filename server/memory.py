
import sqlite3
import json
import os
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = "brain.db"


class NeuralMemory:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Table for storing element selectors found on specific domains
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    tags TEXT,
                    selector TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()

    def add_memory(self, domain: str, tags: str, selector: str):
        """Reinforce a memory. If it exists, increment success_count."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Check for existing memory
            cursor.execute(
                """
                SELECT id, success_count FROM memories 
                WHERE domain = ? AND tags = ? AND selector = ?
            """,
                (domain, tags, selector),
            )
            row = cursor.fetchone()

            if row:
                # Reinforce
                new_count = row[1] + 1
                cursor.execute(
                    "UPDATE memories SET success_count = ?, last_used = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_count, row[0]),
                )
                logger.info(f"🧠 Reinforced memory for {domain} [{tags}] (Strength: {new_count})")
            else:
                # Create new
                cursor.execute(
                    "INSERT INTO memories (domain, tags, selector) VALUES (?, ?, ?)", (domain, tags, selector)
                )
                logger.info(f"🧠 Created new memory for {domain} [{tags}]")
            conn.commit()

    def query_memory(self, domain: str, tags_query: str) -> List[Dict[str, Any]]:
        """Retrieve memories for a domain matching tags."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Simple exact match on domain, fuzzy on tags for now
            # In a real "Neural" system, this would be a vector search
            cursor.execute(
                """
                SELECT selector, success_count, tags FROM memories 
                WHERE domain = ? 
                ORDER BY success_count DESC
            """,
                (domain,),
            )

            rows = cursor.fetchall()
            results = []
            for r in rows:
                if r[2] is None:
                    continue
                if tags_query.lower() in r[2].lower() or r[2].lower() in tags_query.lower():
                    results.append({"selector": r[0], "confidence": r[1], "tags": r[2]})

            return results

    def get_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(success_count) FROM memories")
            row = cursor.fetchone()
            return {"total_memories": row[0] or 0, "total_accumulated_experience": row[1] or 0}


# Global instance
memory = NeuralMemory()
