"""Call every board once and print how many jobs it has. Writes nothing.

    python -m app.ingest.check_sources
"""
import time

from app.ingest.fetch import get_json, make_client
from app.ingest.run import ADAPTERS, load_boards


def main() -> None:
    total = 0
    with make_client() as client:
        for position, board in enumerate(load_boards()):
            if position:
                time.sleep(1)
            adapter = ADAPTERS[board["source"]]
            try:
                count = len(adapter.items(get_json(client, adapter.url(board))))
                total += count
                print(f"ok    {board['source']:10} {board['board']:32} {count}")
            except Exception as exc:
                print(f"FAIL  {board['source']:10} {board['board']:32} {type(exc).__name__}")
    print(f"total jobs: {total}")


if __name__ == "__main__":
    main()
