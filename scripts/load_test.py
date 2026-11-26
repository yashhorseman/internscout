"""Many users at once, each sending one message after another.

    python scripts/load_test.py http://127.0.0.1:8010 --users 20 --seconds 120
"""
import argparse
import asyncio
import time

import httpx


async def user(client, deadline, times, failures):
    session = (await client.post("/sessions")).json()["session_id"]
    while time.monotonic() < deadline:
        started = time.perf_counter()
        try:
            response = await client.post(f"/sessions/{session}/messages",
                                         json={"text": "software engineer internship"})
            response.raise_for_status()
            times.append(time.perf_counter() - started)
        except Exception as exc:
            failures.append(type(exc).__name__)


async def run(base: str, users: int, seconds: int) -> None:
    times, failures = [], []
    started = time.monotonic()
    async with httpx.AsyncClient(base_url=base, timeout=60,
                                 limits=httpx.Limits(max_connections=users)) as client:
        await asyncio.gather(*(user(client, started + seconds, times, failures) for _ in range(users)))
    elapsed = time.monotonic() - started
    ordered = sorted(times)
    total = len(times) + len(failures)
    print(f"{users} users for {elapsed:.0f} s: {total} requests, {total / elapsed:.1f} per second, "
          f"errors {len(failures)} ({len(failures) / max(total, 1):.1%})")
    if ordered:
        print(f"latency p50 {ordered[len(ordered) // 2] * 1000:.0f} ms, "
              f"p95 {ordered[int(0.95 * len(ordered))] * 1000:.0f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--seconds", type=int, default=120)
    args = parser.parse_args()
    asyncio.run(run(args.base, args.users, args.seconds))
