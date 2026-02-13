
import urllib.request
import json
import sys

BASE_URL = "http://localhost:8000"

def test_api():
    print(f"🚀 Testing Nexus Agent Hub API at {BASE_URL}...\n")

    # 1. Test Server Health (via memory stats)
    print("1️⃣  Checking Server Health...")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/memory/stats") as response:
            if response.status == 200:
                print("   ✅ Server is UP (Stats endpoint reachable)")
                print(f"   📊 Stats: {response.read().decode()}")
            else:
                print(f"   ❌ Server returned status {response.status}")
                return
    except Exception as e:
        print(f"   ❌ Could not connect to server: {e}")
        print("   👉 Make sure 'uvicorn server.api:app' is running!")
        return

    # 2. Add a Semantic Memory
    print("\n2️⃣  Testing Memory Injection (Neural Bridge)...")
    memory_content = "The Secret Key for Project X is 'BlueSky99'."
    data = json.dumps({
        "content": memory_content,
        "metadata": {"source": "test_script", "sensitivity": "high"}
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/memory/add", 
        data=data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            print("   ✅ Memory Stored Successfully")
    except Exception as e:
        print(f"   ❌ Failed to add memory: {e}")
        return

    # 3. Query the Memory
    print("\n3️⃣  Testing Memory Recall...")
    # Using a semantic query (different wording than content)
    query = "What is the secret key for Project X?"
    data = json.dumps({
        "query": query,
        "limit": 1,
        "min_score": 0.0 # Strict check might fail if no embeddings model, so allow low score to see what returns
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/memory/query", 
        data=data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"   🔍 Query: '{query}'")
            if result:
                top_match = result[0]
                print(f"   ✅ Result Found: {top_match}")
                
                # Check if it's the correct memory
                if "BlueSky99" in str(top_match):
                    print("   🎉 SUCCESS: Correct memory recalled!")
                else:
                    print("   ⚠️  Result retrieved, but content might be different (expected 'BlueSky99')")
            else:
                print("   ⚠️  No results found. (If running without 'sentence-transformers', semantic search is hash-based only)")
                print("      👉 Try querying exact text if in Fallback Mode.")
    except Exception as e:
        print(f"   ❌ Failed to query memory: {e}")

    print("\n🏁 Test Complete.")

if __name__ == "__main__":
    test_api()
