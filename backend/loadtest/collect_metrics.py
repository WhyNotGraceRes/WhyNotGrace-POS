"""Samples server-side metrics (backend process CPU/RAM, aggregate Postgres
process CPU/RAM, and live pg_stat_activity connection counts) at a fixed
interval and writes them to CSV — run alongside a Locust stage, not part of
Locust itself, since Locust's own process is the load *generator* and must
not be conflated with the *server* being measured.

Usage:
    python loadtest/collect_metrics.py --port 8100 --pg-port 5544 \
        --db whynotgrace_loadtest --out loadtest/results/stage_100_metrics.csv \
        --duration 200
"""
import argparse
import csv
import subprocess
import time
from pathlib import Path

import psutil


def _find_listening_pid(port: int) -> int | None:
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return conn.pid
    return None


def _find_backend_worker_procs(port: int) -> list[psutil.Process]:
    """With uvicorn --workers N, the listening socket belongs to the master
    process while N separate child worker processes do the actual request
    handling — summing CPU/RAM from only the listener PID would badly
    undercount. Finds the master via the listening port, then includes it
    and every live child (the worker pool)."""
    master_pid = _find_listening_pid(port)
    if master_pid is None:
        return []
    try:
        master = psutil.Process(master_pid)
    except psutil.NoSuchProcess:
        return []
    return [master, *master.children(recursive=True)]


def _postgres_procs():
    return [p for p in psutil.process_iter(["name"]) if p.info["name"] and p.info["name"].lower() == "postgres.exe"]


def _pg_connection_count(pg_bin: str, pg_port: int, db: str, user: str, password: str) -> tuple[int, int]:
    """Returns (active, total) connections to `db` via psql -c, since no
    python postgres driver is guaranteed importable outside the app venv
    context at metrics-collection time; psql ships with the portable
    Postgres binaries already used throughout this project."""
    import os

    env = dict(os.environ, PGPASSWORD=password)
    query = f"SELECT state, count(*) FROM pg_stat_activity WHERE datname = '{db}' GROUP BY state;"
    try:
        result = subprocess.run(
            [str(Path(pg_bin) / "psql.exe"), "-h", "localhost", "-p", str(pg_port), "-U", user, "-d", "postgres", "-t", "-A", "-F,", "-c", query],
            env=env, capture_output=True, text=True, timeout=5,
        )
        total = 0
        active = 0
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            state, count = line.split(",")
            count = int(count)
            total += count
            if state == "active":
                active = count
        return active, total
    except Exception:
        return -1, -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True, help="Backend port to identify its process by")
    parser.add_argument(
        "--pg-bin",
        default=r"C:\Users\sanskar raut\AppData\Local\Temp\claude\C--Users-sanskar-raut-OneDrive-Desktop-gandu\da259249-6ea3-44c0-a5d7-1e63c6642b5b\scratchpad\pg\postgresql-18.4.0-x86_64-pc-windows-msvc\bin",
        help="Windows-style path (subprocess needs a native path here, not a Git-Bash /c/... path)",
    )
    parser.add_argument("--pg-port", type=int, default=5544)
    parser.add_argument("--db", default="whynotgrace_loadtest")
    parser.add_argument("--pg-user", default="whynotgrace")
    parser.add_argument("--pg-password", default="changeme_dev_password")
    parser.add_argument("--out", required=True)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--duration", type=float, default=180.0, help="Stop sampling after this many seconds")
    args = parser.parse_args()

    backend_procs = _find_backend_worker_procs(args.port)
    for p in backend_procs:
        try:
            p.cpu_percent()  # prime each process's internal counter
        except Exception:
            pass
    for p in _postgres_procs():
        try:
            p.cpu_percent()
        except Exception:
            pass

    rows = []
    start = time.time()
    while time.time() - start < args.duration:
        time.sleep(args.interval)
        ts = round(time.time() - start, 1)

        backend_cpu_total = 0.0
        backend_rss_total_mb = 0.0
        backend_proc_count = 0
        for p in backend_procs:
            try:
                if not p.is_running():
                    continue
                backend_cpu_total += p.cpu_percent()
                backend_rss_total_mb += p.memory_info().rss / (1024 * 1024)
                backend_proc_count += 1
            except Exception:
                continue
        backend_cpu = round(backend_cpu_total, 1)
        backend_rss_mb = round(backend_rss_total_mb, 1)

        pg_cpu_total = 0.0
        pg_rss_total_mb = 0.0
        pg_count = 0
        for p in _postgres_procs():
            try:
                pg_cpu_total += p.cpu_percent()
                pg_rss_total_mb += p.memory_info().rss / (1024 * 1024)
                pg_count += 1
            except Exception:
                continue

        active_conn, total_conn = _pg_connection_count(args.pg_bin, args.pg_port, args.db, args.pg_user, args.pg_password)

        row = {
            "elapsed_s": ts,
            "backend_cpu_pct_total": backend_cpu,  # summed across all worker processes; 300% = 3 cores fully busy
            "backend_rss_mb_total": backend_rss_mb,
            "backend_process_count": backend_proc_count,
            "postgres_total_cpu_pct": round(pg_cpu_total, 1),
            "postgres_total_rss_mb": round(pg_rss_total_mb, 1),
            "postgres_process_count": pg_count,
            "db_active_connections": active_conn,
            "db_total_connections": total_conn,
        }
        rows.append(row)
        print(row)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} samples to {args.out}")


if __name__ == "__main__":
    main()
