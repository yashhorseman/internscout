"""Peak memory of the app's process after 20 searches, with or without the re-ranker.
Run inside the image; query vectors come from the benchmark cache, so no quota is used.

    python memory.py hybrid|hybrid_rerank /data/query_vectors.json
"""
import json
import sys

from app import api  # noqa: F401  (load everything the server loads)
from app.db import connect
from app.retrieval.search import search

mode, path = sys.argv[1], sys.argv[2]
vectors = list(json.load(open(path)).items())[:20]
with connect() as conn:
    for text, vector in vectors:
        assert search(conn, text, vector, {}, 10, mode)
status = dict(line.split(":", 1) for line in open("/proc/self/status"))
print(f"{mode}: peak resident memory {int(status['VmHWM'].split()[0]) / 1024:.0f} MB")
