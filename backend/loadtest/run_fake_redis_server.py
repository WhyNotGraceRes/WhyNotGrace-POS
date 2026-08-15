"""Starts fakeredis's TcpFakeServer — a real TCP listener speaking the
Redis wire protocol, backed by an in-memory emulator (NOT genuine Redis).

Used ONLY for Phase 11 load-test verification, so the cache layer
(app/core/cache.py) can be tested against a real, separate, network-
reachable process from all 4 uvicorn worker processes at once — the same
topology a real Redis deployment would have, which an in-process fake
cannot exercise. This is explicitly disclosed everywhere the resulting
test data is reported: this proves the application's Redis client code
path, connection handling, and cross-process cache-sharing/tenant-key
correctness — it does NOT prove genuine Redis's own performance or
operational characteristics under real production load.

Usage: python loadtest/run_fake_redis_server.py [port]
"""
import sys

from fakeredis import TcpFakeServer

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 6399
    server = TcpFakeServer(("127.0.0.1", port), server_type="redis")
    print(f"fakeredis TCP server (NOT genuine Redis) listening on 127.0.0.1:{port}")
    server.serve_forever()
