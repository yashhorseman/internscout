"""After a deploy: is it up, and does one question come back with at least one job?

    python scripts/smoke.py http://127.0.0.1:8000
"""
import sys

import httpx


def main(base: str) -> int:
    with httpx.Client(base_url=base, timeout=180) as client:
        assert client.get("/health").json() == {"ok": True}, "health check failed"
        session = client.post("/sessions").raise_for_status().json()["session_id"]
        reply = client.post(f"/sessions/{session}/messages",
                            json={"text": "software engineering internship in India"}).raise_for_status().json()
    print(f"outcome {reply['outcome']}, {len(reply['cards'])} cards")
    if not reply["cards"]:
        print("FAILED: no cards")
        return 1
    print("passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"))
