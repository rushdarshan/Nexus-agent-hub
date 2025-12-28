"""
SWARM BRAIN - Shared Memory & Coordination System
==================================================
The brain that connects all agents. Stores findings, enables learning,
and coordinates the final synthesis.
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict
from dataclasses import dataclass, asdict
import threading


@dataclass
class Finding:
    """A single piece of information discovered by an agent."""
    agent_name: str
    task: str
    finding: str
    source_url: str
    confidence: float  # 0.0 to 1.0
    timestamp: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass  
class Decision:
    """The final synthesized decision from the CEO agent."""
    question: str
    recommendation: str
    reasoning: str
    sources: List[str]
    timestamp: str
    

class SwarmBrain:
    """
    Central nervous system for the agent swarm.
    
    Capabilities:
    - Store findings from all agents
    - Query historical findings
    - Enable CEO agent to synthesize results
    - Learn from past decisions
    """
    
    def __init__(self, db_path: str = "swarm_brain.db"):
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for persistent memory."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Findings table - what agents discover
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    agent_name TEXT,
                    task TEXT,
                    finding TEXT,
                    source_url TEXT,
                    confidence REAL,
                    timestamp TEXT,
                    metadata TEXT,
                    embedding_hash TEXT
                )
            """)
            
            # Decisions table - what CEO agent concluded
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    question TEXT,
                    recommendation TEXT,
                    reasoning TEXT,
                    sources TEXT,
                    timestamp TEXT,
                    user_feedback TEXT
                )
            """)
            
            # Sessions table - group related work
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    goal TEXT,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT
                )
            """)
            
            conn.commit()
    
    def create_session(self, goal: str) -> str:
        """Start a new research session."""
        session_id = hashlib.md5(f"{goal}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sessions (id, goal, status, created_at)
                VALUES (?, ?, 'active', ?)
            """, (session_id, goal, datetime.now().isoformat()))
            conn.commit()
            
        return session_id
    
    def store_finding(self, session_id: str, finding: Finding):
        """Store a finding from an agent."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO findings 
                    (session_id, agent_name, task, finding, source_url, confidence, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    finding.agent_name,
                    finding.task,
                    finding.finding,
                    finding.source_url,
                    finding.confidence,
                    finding.timestamp,
                    json.dumps(finding.metadata) if finding.metadata else None
                ))
                conn.commit()
        
        print(f"🧠 [Brain] Stored finding from {finding.agent_name}: {finding.finding[:50]}...")
    
    def get_session_findings(self, session_id: str) -> List[Finding]:
        """Get all findings for a session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT agent_name, task, finding, source_url, confidence, timestamp, metadata
                FROM findings WHERE session_id = ?
                ORDER BY timestamp
            """, (session_id,))
            
            findings = []
            for row in cursor.fetchall():
                findings.append(Finding(
                    agent_name=row[0],
                    task=row[1],
                    finding=row[2],
                    source_url=row[3],
                    confidence=row[4],
                    timestamp=row[5],
                    metadata=json.loads(row[6]) if row[6] else None
                ))
            return findings
    
    def store_decision(self, session_id: str, decision: Decision):
        """Store the CEO's final decision."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO decisions 
                (session_id, question, recommendation, reasoning, sources, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                decision.question,
                decision.recommendation,
                decision.reasoning,
                json.dumps(decision.sources),
                decision.timestamp
            ))
            
            # Mark session as completed
            conn.execute("""
                UPDATE sessions SET status = 'completed', completed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
    
    def get_past_decisions(self, limit: int = 10) -> List[Decision]:
        """Get past decisions for learning/reference."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT question, recommendation, reasoning, sources, timestamp
                FROM decisions
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            decisions = []
            for row in cursor.fetchall():
                decisions.append(Decision(
                    question=row[0],
                    recommendation=row[1],
                    reasoning=row[2],
                    sources=json.loads(row[3]),
                    timestamp=row[4]
                ))
            return decisions
    
    def search_findings(self, query: str, limit: int = 20) -> List[Finding]:
        """Search past findings (simple text search for now)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT agent_name, task, finding, source_url, confidence, timestamp, metadata
                FROM findings
                WHERE finding LIKE ? OR task LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            
            findings = []
            for row in cursor.fetchall():
                findings.append(Finding(
                    agent_name=row[0],
                    task=row[1],
                    finding=row[2],
                    source_url=row[3],
                    confidence=row[4],
                    timestamp=row[5],
                    metadata=json.loads(row[6]) if row[6] else None
                ))
            return findings
    
    def get_context_for_ceo(self, session_id: str) -> str:
        """Generate a context summary for the CEO agent."""
        findings = self.get_session_findings(session_id)
        past_decisions = self.get_past_decisions(limit=3)
        
        context = "## Current Research Findings\n\n"
        for f in findings:
            context += f"### From {f.agent_name}\n"
            context += f"- Task: {f.task}\n"
            context += f"- Finding: {f.finding}\n"
            context += f"- Source: {f.source_url}\n"
            context += f"- Confidence: {f.confidence:.0%}\n\n"
        
        if past_decisions:
            context += "\n## Relevant Past Decisions (for learning)\n\n"
            for d in past_decisions:
                context += f"- Q: {d.question[:100]}...\n"
                context += f"  A: {d.recommendation[:100]}...\n\n"
        
        return context
    
    def export_session(self, session_id: str) -> dict:
        """Export a complete session for review."""
        findings = self.get_session_findings(session_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT goal, status, created_at, completed_at
                FROM sessions WHERE id = ?
            """, (session_id,))
            row = cursor.fetchone()
            
            cursor = conn.execute("""
                SELECT question, recommendation, reasoning, sources, timestamp
                FROM decisions WHERE session_id = ?
            """, (session_id,))
            decision_row = cursor.fetchone()
        
        return {
            "session_id": session_id,
            "goal": row[0] if row else None,
            "status": row[1] if row else None,
            "created_at": row[2] if row else None,
            "completed_at": row[3] if row else None,
            "findings": [f.to_dict() for f in findings],
            "decision": {
                "question": decision_row[0],
                "recommendation": decision_row[1],
                "reasoning": decision_row[2],
                "sources": json.loads(decision_row[3]),
                "timestamp": decision_row[4]
            } if decision_row else None
        }


# Singleton instance for global access
_brain_instance: Optional[SwarmBrain] = None

def get_brain() -> SwarmBrain:
    """Get or create the global SwarmBrain instance."""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = SwarmBrain()
    return _brain_instance


if __name__ == "__main__":
    # Test the brain
    brain = SwarmBrain("test_brain.db")
    
    session = brain.create_session("Find the best flight from NYC to Tokyo")
    print(f"Created session: {session}")
    
    brain.store_finding(session, Finding(
        agent_name="Kayak Agent",
        task="Search Kayak for NYC-Tokyo flights",
        finding="Found Delta flight at $850, departing 10am, 14h total",
        source_url="https://kayak.com/flights/nyc-tokyo",
        confidence=0.9,
        timestamp=datetime.now().isoformat()
    ))
    
    brain.store_finding(session, Finding(
        agent_name="Google Agent",
        task="Search Google Flights for NYC-Tokyo",
        finding="ANA direct flight at $780, departing 1pm, 13h total",
        source_url="https://google.com/flights",
        confidence=0.95,
        timestamp=datetime.now().isoformat()
    ))
    
    print("\n📊 Session Findings:")
    for f in brain.get_session_findings(session):
        print(f"  - {f.agent_name}: {f.finding}")
    
    print("\n🧠 CEO Context:")
    print(brain.get_context_for_ceo(session))
