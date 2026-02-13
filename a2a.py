
import asyncio
import uuid
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass

# --- 1. Identity & Discovery ---

class AgentIdentity(BaseModel):
    did: str = Field(default_factory=lambda: f"did:agent:{uuid.uuid4().hex[:8]}")
    name: str
    capabilities: List[str]
    endpoint: str = "local" # For now, we simulate local p2p

# --- 2. Protocol Messages ---

class A2AMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    sender_id: str
    type: str
    content: Dict[str, Any]

class RFP(BaseModel):
    """Request for Proposal"""
    task_description: str
    max_budget: float = 0.0

class Bid(BaseModel):
    agent_id: str
    agent_name: str
    proposed_cost: float
    estimated_time: str
    rationale: str

# --- 3. The A2A Client (The "Modem") ---

class A2AClient:
    def __init__(self, identity: AgentIdentity, peers: List[AgentIdentity]):
        self.identity = identity
        self.peers = peers
        self.inbox: asyncio.Queue = asyncio.Queue()

    async def broadcast_rfp(self, task: str) -> List[Bid]:
        """
        Broadcasts a Request for Proposal to all known peers.
        Returns a list of Bids.
        """
        print(f"📡 [A2A] Broadcasting RFP for: '{task}' to {len(self.peers)} peers...")
        
        bids = []
        # Simulate network delay and peer response
        for peer in self.peers:
            # Simple keyword matching to simulate "Intelligence" of peers
            bid = await self._simulate_peer_response(peer, task)
            if bid:
                bids.append(bid)
        
        return bids

    async def _simulate_peer_response(self, peer: AgentIdentity, task: str) -> Optional[Bid]:
        """Simulates an external agent evaluating the RFP"""
        await asyncio.sleep(0.5) # Network latency
        
        # Logic: If peer has capability matching task, they bid
        matches = any(cap.lower() in task.lower() for cap in peer.capabilities)
        
        if matches:
            return Bid(
                agent_id=peer.did,
                agent_name=peer.name,
                proposed_cost=0.05, # Mock cost
                estimated_time="30s",
                rationale=f"I specialize in {peer.capabilities[0]} and can handle this."
            )
        return None

    async def delegate_task(self, peer_id: str, task: str) -> str:
        """
        Sends the task to the specific winner agent.
        """
        peer = next((p for p in self.peers if p.did == peer_id), None)
        if not peer:
            raise ValueError(f"Peer {peer_id} not found")
            
        print(f"🤝 [A2A] Delegating task to {peer.name} ({peer.did})...")
        await asyncio.sleep(2.0) # Simulate remote execution
        
        # Mock responses based on agent type
        if "Security" in peer.name:
            return f"[{peer.name} REPORT]: scanned code. No vulnerabilities found. ISO 27001 Compliant."
        elif "Legal" in peer.name:
            return f"[{peer.name} MEMO]: The contract clause 4.2 is valid under EU AI Act."
        else:
            return f"[{peer.name} RESULT]: Task '{task}' completed successfully."
