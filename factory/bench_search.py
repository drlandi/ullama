#!/usr/bin/env python3
"""Benchmark a search_file(path, key) solution on a real record file.

Written by a human. It does two things, in this order:
  1. CHECK   every answer against an independent oracle (abort on the first mismatch);
  2. TIME    each lookup, in two passes over the same queries.

The oracle: for a present key we know its index because we picked the index first and
read the key stored there; for an absent key we take a stored key plus 1 when the next
stored key is larger than that, so it cannot be present.

Usage:
  python3 bench_search.py SOLUTION.py DATAFILE [--queries 2000] [--seed 1] [--baseline 3] [--log]

Make a data file with:  python3 tests/recordlib.py data/records_1M.bin 1000000
The first pass is made cold by asking the kernel (posix_fadvise DONTNEED) to drop this file from the page
cache after the queries are built. That is advisory; for a stronger guarantee, also run before the benchmark:
  sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
"""
import argparse
import importlib.util
import json
import os
import random
import statistics
import struct
import time

RECORD = 24
HERE = os.path.dirname(os.path.abspath(__file__))


def load_function(path):
    spec = importlib.util.spec_from_file_location("solution_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.search_file


def key_at(f, i):
    f.seek(i * RECORD)
    return int.from_bytes(f.read(8), "big")


def make_queries(path, n, count, seed):
    """Half present keys, half absent keys, each with its known correct answer."""
    rng = random.Random(seed)
    queries = []
    with open(path, "rb") as f:
        while len(queries) < count:
            i = rng.randrange(n)
            if len(queries) % 2 == 0:
                queries.append((key_at(f, i), i))
            else:
                k = key_at(f, i) + 1
                if i + 1 >= n or key_at(f, i + 1) > k:
                    queries.append((k, -1))
    return queries


def linear_scan(path, key):
    """Slow, obviously correct baseline: read the file in 1 MB chunks."""
    index = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(RECORD * 43690)
            if not chunk:
                return -1
            for k, _payload in struct.iter_unpack(">Q16s", chunk):
                if k == key:
                    return index
                index += 1


def timed_pass(fn, path, queries):
    times = []
    for key, expected in queries:
        t = time.perf_counter_ns()
        got = fn(path, key)
        times.append(time.perf_counter_ns() - t)
        if got != expected:
            raise SystemExit("MISMATCH: search_file(%d) returned %r, expected %r" % (key, got, expected))
    return times


def summary(times):
    us = sorted(t / 1000 for t in times)
    pick = lambda q: us[min(len(us) - 1, int(q * len(us)))]
    return {"median_us": round(statistics.median(us), 1), "p95_us": round(pick(0.95), 1),
            "p99_us": round(pick(0.99), 1), "max_us": round(us[-1], 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("solution")
    ap.add_argument("datafile")
    ap.add_argument("--queries", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--baseline", type=int, default=None, help="linear-scan queries to time (default 3 if the file has <= 20M records)")
    ap.add_argument("--no-drop", action="store_true", help="do not drop the file from the page cache before the first pass")
    ap.add_argument("--log", action="store_true", help="append the result to factory/results.jsonl")
    args = ap.parse_args()

    size = os.path.getsize(args.datafile)
    if size % RECORD:
        raise SystemExit("file size %d is not a multiple of %d" % (size, RECORD))
    n = size // RECORD
    fn = load_function(args.solution)
    queries = make_queries(args.datafile, n, args.queries, args.seed)

    print("file: %s  (%d records, %.2f GB)   queries: %d (half present, half absent)" % (args.datafile, n, size / 1e9, len(queries)))
    # Building the queries read pages of the file (that is how the oracle knows the answers).
    # Ask the kernel to forget them, so the first pass starts with the file out of the page cache.
    dropped = False
    if not args.no_drop and hasattr(os, "posix_fadvise"):
        with open(args.datafile, "rb") as f:
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
        dropped = True
    print("page cache for this file dropped before the first pass: %s" % ("yes (posix_fadvise DONTNEED)" if dropped else "no"))
    first = summary(timed_pass(fn, args.datafile, queries))
    print("all %d answers verified against the oracle" % len(queries))
    warm = summary(timed_pass(fn, args.datafile, queries))
    print("  first pass : median %8.1f us   p95 %8.1f us   p99 %8.1f us   max %10.1f us" % (first["median_us"], first["p95_us"], first["p99_us"], first["max_us"]))
    print("  warm pass  : median %8.1f us   p95 %8.1f us   p99 %8.1f us   max %10.1f us" % (warm["median_us"], warm["p95_us"], warm["p99_us"], warm["max_us"]))

    base = args.baseline if args.baseline is not None else (3 if n <= 20_000_000 else 0)
    baseline_ms = None
    if base:
        ts = []
        for key, expected in queries[:base]:
            t = time.perf_counter()
            got = linear_scan(args.datafile, key)
            ts.append((time.perf_counter() - t) * 1000)
            assert got == expected, "baseline disagrees with the oracle"
        baseline_ms = round(statistics.median(ts), 1)
        print("  linear scan: median %8.1f ms  (%d queries)   ->  binary search is about %dx faster (warm median)"
              % (baseline_ms, base, baseline_ms * 1000 / warm["median_us"]))
    if args.log:
        with open(os.path.join(HERE, "results.jsonl"), "a") as f:
            f.write(json.dumps({"kind": "search_bench", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "solution": os.path.basename(args.solution), "records": n,
                                "queries": len(queries), "cache_dropped": dropped, "first": first, "warm": warm,
                                "linear_scan_ms": baseline_ms}) + "\n")


if __name__ == "__main__":
    main()
