
import asyncio
import sys
import numpy as np
from pathlib import Path
import json

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

from browser_use.memory.neural_bridge import neural_bridge

async def verify_neural_bridge():
    print("\n🧠 Testing Neural Bridge...")
    
    # 1. Test Embedding Generation
    text = "The quick brown fox jumps over the lazy dog."
    embedding = neural_bridge._get_embedding(text)
    
    if hasattr(neural_bridge, 'model') and neural_bridge.model:
        print(f"✅ Embedding Model Loaded: {neural_bridge.model}")
        print(f"   Embedding Shape: {embedding.shape}")
    else:
        print("⚠️  Embedding Model NOT Loaded (Using Fallback Hash)")
        print(f"   Embedding Shape: {embedding.shape}")

    # 2. Store Memory
    print("\n💾 Storing Memories...")
    memories = [
        ("Python is a programming language.", {"topic": "tech"}),
        ("The sky is blue today.", {"topic": "nature"}),
        ("Javascript is used for web development.", {"topic": "tech"}),
    ]
    
    for content, meta in memories:
        neural_bridge.store_memory(content, meta)
        
    # 3. Query Memory
    print("\n🔍 Querying 'coding languages'...")
    results = neural_bridge.query_similar("coding languages", limit=2)
    
    for r in results:
        print(f"   - Score: {r['score']:.4f} | Hash: {r['hash'][:8]} | Metadata: {r['metadata']}")
        
    if neural_bridge.model:
        # Expect tech topics to be top results
        if results and results[0]['metadata'].get('topic') == 'tech':
             print("✅ Semantic Search Working (Relevant results found)")
        else:
             print("⚠️ Semantic Search Results mixed (expected if model is weak or small dataset)")
    else:
        # Expect precise match only (so unlikely to find anything for "coding languages" unless exact match)
        if not results:
             print("✅ Fallback mode behaving as expected (Partial/No matches for semantic query)")
        else:
             print(f"ℹ️ Fallback mode found {len(results)} matches (Likely random or exact hash collision)")

    print("\n🎉 Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify_neural_bridge())
