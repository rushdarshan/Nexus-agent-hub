#!/usr/bin/env python3
"""Fractal Swarm prototype (MVP)

This script demonstrates a "CEO" manager that spawns sub-agents in parallel.
Default mode is `simulate` so it runs without external LLM or browser dependencies.

Usage:
  python examples/fractal_swarm/swarm_manager.py            # simulate mode (default)
  python examples/fractal_swarm/swarm_manager.py --mode real # attempt to use real Agents (requires OPENAI_API_KEY, optional browser)

"""
import argparse
import asyncio
import json
import random
import time
from typing import Any, Dict

try:
    import nest_asyncio
except Exception:
    nest_asyncio = None

# Load .env if present so OPENROUTER_API_KEY from browser-use/.env is available
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


async def flight_agent_sim(task: str) -> Dict[str, Any]:
    await asyncio.sleep(random.uniform(0.6, 1.8))
    return {"agent": "flight", "result": f"Flights found for {task}: [FL123, FL456]"}


async def hotel_agent_sim(task: str) -> Dict[str, Any]:
    await asyncio.sleep(random.uniform(0.4, 1.2))
    return {"agent": "hotel", "result": f"Hotels found for {task}: [Hotel A, Hotel B]"}


async def itinerary_agent_sim(task: str) -> Dict[str, Any]:
    await asyncio.sleep(random.uniform(0.3, 1.0))
    return {"agent": "itinerary", "result": f"Itinerary draft for {task}: Day1 sightsee, Day2 rest"}


async def run_simulated_swarm(task: str) -> Dict[str, Any]:
    # Spawn sub-agents in parallel
    agents = [flight_agent_sim(task), hotel_agent_sim(task), itinerary_agent_sim(task)]
    start = time.time()
    results = await asyncio.gather(*agents)
    elapsed = time.time() - start

    # CEO compiles results
    summary = {
        "task": task,
        "elapsed_seconds": round(elapsed, 2),
        "results": {r["agent"]: r["result"] for r in results},
    }
    return summary


async def run_real_swarm(task: str, openrouter_key: str | None = None) -> Dict[str, Any]:
    # Try to use browser_use ChatOpenAI pointed at OpenRouter (or other OpenAI-compatible base_url)
    try:
        from browser_use import ChatOpenAI

        # Read key from environment if set; ChatOpenAI supports api_key and base_url
        import os

        api_key = openrouter_key or os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

        if not api_key:
            # Fallback to simulated swarm
            return await run_simulated_swarm(task)

        # Debug: confirm we have a key (do not print the key itself)
        print(f"[swarm_manager] using OpenRouter key (masked) length={len(api_key)} base_url={base_url}")


        # Use the OpenAI-compatible async client directly to call OpenRouter
        try:
            from openai import AsyncOpenAI
        except Exception:
            # Fallback to simulation if async client isn't available
            return await run_simulated_swarm(task)

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        async def flight_agent_real(task: str):
            prompt = f"You are a knowledgeable assistant. Given the task: {task}, provide 10 Bible verses with short citations." if 'Bible' in task or 'bible' in task.lower() else f"You are a flight search assistant. Given the task: {task}, list two flight options concisely."
            resp = await client.chat.completions.create(model="openai/gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
            text = ''
            try:
                text = resp.choices[0].message.content
            except Exception:
                text = str(resp)
            return {"agent": "flight", "result": text}

        async def hotel_agent_real(task: str):
            prompt = f"If asked for Bible verses, provide them; otherwise act like a hotel search assistant for: {task}."
            resp = await client.chat.completions.create(model="openai/gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
            try:
                text = resp.choices[0].message.content
            except Exception:
                text = str(resp)
            return {"agent": "hotel", "result": text}

        async def itinerary_agent_real(task: str):
            prompt = f"If asked for Bible verses, provide them succinctly; otherwise draft a two-day itinerary for: {task}."
            resp = await client.chat.completions.create(model="openai/gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
            try:
                text = resp.choices[0].message.content
            except Exception:
                text = str(resp)
            return {"agent": "itinerary", "result": text}

        agents = [flight_agent_real(task), hotel_agent_real(task), itinerary_agent_real(task)]
        start = time.time()
        results = await asyncio.gather(*agents)
        elapsed = time.time() - start

        summary = {
            "task": task,
            "elapsed_seconds": round(elapsed, 2),
            "results": {r["agent"]: r["result"] for r in results},
        }
        return summary
    except Exception as e:
        import traceback, sys

        print("[swarm_manager] real swarm error:", type(e).__name__, e, file=sys.stderr)
        traceback.print_exc()
        return await run_simulated_swarm(task)


def run_main(mode: str, task: str, openrouter_key: str | None = None):
    async def _main():
        if mode == "simulate":
            out = await run_simulated_swarm(task)
        else:
            out = await run_real_swarm(task, openrouter_key=openrouter_key)
        print(json.dumps(out, indent=2))

    # Run safely inside nested event loops (e.g., VS Code/Jupyter)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        asyncio.run(_main())
    else:
        if nest_asyncio:
            nest_asyncio.apply()
        loop.run_until_complete(_main())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("simulate", "real"), default="simulate")
    p.add_argument("--task", default="Plan my trip to Japan", help="High-level task for CEO")
    p.add_argument("--openrouter-key", default=None, help="OpenRouter API key (optional) - used in real mode")
    args = p.parse_args()

    run_main(args.mode, args.task, openrouter_key=args.openrouter_key)
