
from a2a import AgentIdentity

# The "Yellow Pages" of Agents
KNOWN_PEERS = [
    AgentIdentity(
        name="SecurBot-X", 
        capabilities=["security audit", "vulnerability scan", "code review"], 
        endpoint="https://securbot.ai/api/v1/a2a"
    ),
    AgentIdentity(
        name="LegalEagle-7", 
        capabilities=["legal review", "contract analysis", "compliance check", "gdpr"], 
        endpoint="https://legaleagle.io/agent"
    ),
    AgentIdentity(
        name="CryptoKeep", 
        capabilities=["wallet check", "transaction analysis", "crypto"], 
        endpoint="wss://cryptokeep.defi/stream"
    )
]
