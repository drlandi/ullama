#!/usr/bin/env python3
"""uLLAMA factory, version 3: a task passes only when its JUDGE says so.

The loop, per task in issues.json:
  1. Ask the model (the ullama binary) for code.
  2. Copy that code to solution.py in a fresh temporary folder, together with
     the task's test file (the judge), and run the judge.
  3. If the judge fails, try again, using one of two strategies:
       repair : show the model its previous code and the judge's failure
       fresh  : ignore the failure and ask the original question again
                (the sampler is random, so each try is a new draw)

Usage:
  python3 factory.py                          run every "pending" task
  python3 factory.py --strategy fresh         same, but with fresh retries
  python3 factory.py --only 7                 run task 7 once (any status) and keep its code
  python3 factory.py --bench 10 --only 1      measure task 1 over 10 runs
  python3 factory.py --judge FILE --only 5    run task 5's judge on a saved file
  python3 factory.py --reset                  set every task to "pending"
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ULLAMA_BIN = os.environ.get("ULLAMA_BIN", os.path.join(HERE, "..", "src", "ullama"))
MODEL = os.environ.get(
    "ULLAMA_MODEL",
    os.path.join(HERE, "..", "models", "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"),
)
ISSUES = os.path.join(HERE, "issues.json")
OUTPUTS = os.path.join(HERE, "outputs")
RESULTS = os.path.join(HERE, "results.jsonl")

MAX_ATTEMPTS = 3
GEN_TIMEOUT = 600   # seconds the model may take for one answer
TEST_TIMEOUT = 20   # seconds the judge may run (catches infinite loops)

RULES = (
    "Reply with ONE Python code block and nothing else. "
    "Define exactly the function(s) named in the task. "
    "Do not include test code, example calls, input(), or a main guard."
)

QUIET = False       # True while benchmarking: one summary line per run


def say(*args):
    if not QUIET:
        print(*args)


def ask_model(prompt):
    """Send the whole prompt to ullama on stdin; return only the completion."""
    try:
        p = subprocess.run(
            [ULLAMA_BIN, MODEL],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=GEN_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        say("    [model timed out]")
        return ""
    stats = p.stderr.strip().splitlines()
    if p.returncode != 0:
        say("    [ullama failed]", " | ".join(stats[-2:]))
        return ""
    if stats:
        say("    " + stats[-1])          # the "[N tok, X tok/s]" line
    return p.stdout


def extract_code(text):
    """Take the first code block; tolerate a missing closing fence."""
    m = re.search(r"```(?:python)?[ \t]*\n(.*?)(?:```|\Z)", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def run_judge(issue, code):
    """Run the task's test file against the code. Returns (passed, message)."""
    if not code:
        return False, "No code was returned."
    with tempfile.TemporaryDirectory() as work:
        with open(os.path.join(work, "solution.py"), "w") as f:
            f.write(code + "\n")
        shutil.copy(os.path.join(HERE, issue["test"]), os.path.join(work, "check.py"))
        for extra in issue.get("support", []):      # helper files the judge needs (human-written)
            shutil.copy(os.path.join(HERE, extra), os.path.join(work, os.path.basename(extra)))
        try:
            r = subprocess.run(
                [sys.executable, "check.py"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=TEST_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return False, "The judge timed out (infinite loop, or far too slow)."
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def first_prompt(issue):
    return issue["prompt"] + "\n\n" + RULES


def repair_prompt(issue, code, failure):
    tail = "\n".join(failure.splitlines()[-25:])[-1500:]
    return (
        "TASK:\n" + issue["prompt"] + "\n\n"
        "PREVIOUS CODE:\n```python\n" + code + "\n```\n\n"
        "FAILURE:\n" + tail + "\n\n"
        "Fix the code so this failure goes away. " + RULES
    )


def work_on(issue, strategy="repair", trace=None):
    """Try one task up to MAX_ATTEMPTS times. Returns (status, attempts)."""
    prompt = first_prompt(issue)
    code = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        say("  attempt %d/%d" % (attempt, MAX_ATTEMPTS))
        code = extract_code(ask_model(prompt))
        if not QUIET:
            save("attempts/%s_attempt%d.py" % (issue["id"], attempt), code)
        passed, message = run_judge(issue, code)
        if trace is not None:
            trace.append((attempt, code, passed, message))
        if passed:
            say("    judge: PASS")
            if not QUIET:
                save(issue["output"], code)
            return "resolved", attempt
        say("    judge: FAIL ->", message.splitlines()[-1] if message else "(no message)")
        if strategy == "repair":
            prompt = repair_prompt(issue, code, message)
    if not QUIET:
        save(issue["output"] + ".failed", code)
    return "failed", MAX_ATTEMPTS


def save(name, code):
    path = os.path.join(OUTPUTS, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(code + "\n")


def log(entry):
    entry["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(RESULTS, "a") as f:
        f.write(json.dumps(entry) + "\n")


def failure_label(message):
    """Short label for a failure, so we can count which check fails most."""
    line = message.strip().splitlines()[-1] if message.strip() else "no message"
    prefix = "AssertionError: "
    if line.startswith(prefix):
        rest = line[len(prefix):]
        label = rest.split(": ")[0]
        if " returned " in rest:
            label += " [wrong answer]"
        elif " read " in rest and "bytes" in rest:
            label += " [too many bytes read]"
        elif " opened the file " in rest:
            label += " [opened more than once]"
        elif " left the file open" in rest:
            label += " [file left open]"
        return label
    return line[:90]


def bench(issues, runs, strategy, only):
    """Run each chosen task `runs` times and report how often it passes."""
    global QUIET
    QUIET = True
    for issue in [i for i in issues if only is None or i["id"] == only]:
        print("\n== #%s %s | strategy=%s | %d runs ==" % (issue["id"], issue["title"], strategy, runs))
        start = time.time()
        outcomes = []
        reasons = {}
        for n in range(runs):
            trace = []
            status, attempts = work_on(issue, strategy, trace)
            for k, code, passed, message in trace:
                if not passed:
                    label = failure_label(message)
                    reasons[label] = reasons.get(label, 0) + 1
                    save("bench/%s_%s_run%d_attempt%d.py" % (issue["id"], strategy, n + 1, k), code)
            outcomes.append(attempts if status == "resolved" else 0)
            result = "pass on attempt %d" % attempts if status == "resolved" else "FAIL"
            print("  run %2d/%d: %s" % (n + 1, runs, result), flush=True)
        wins = sum(1 for o in outcomes if o)
        first = outcomes.count(1)
        seconds = round(time.time() - start)
        print("  -> %d/%d runs passed (%d on the first attempt) in %d s" % (wins, runs, first, seconds))
        total = sum(reasons.values())
        print("  why attempts failed (%d failed attempts):" % total)
        for label, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print("    %3d x %s" % (count, label))
        log({"kind": "bench", "id": issue["id"], "strategy": strategy, "runs": runs,
             "passed": wins, "first_attempt": first, "seconds": seconds,
             "failure_reasons": reasons})


def main():
    ap = argparse.ArgumentParser(description="uLLAMA factory")
    ap.add_argument("--reset", action="store_true", help="set every task to pending")
    ap.add_argument("--strategy", choices=["repair", "fresh"], default="repair")
    ap.add_argument("--bench", type=int, metavar="N", help="run each task N times and report the pass rate")
    ap.add_argument("--only", type=int, metavar="ID", help="task id (for --bench and --judge)")
    ap.add_argument("--judge", metavar="FILE", help="run a task's judge on an existing code file (needs --only)")
    args = ap.parse_args()

    with open(ISSUES) as f:
        issues = json.load(f)

    if args.judge:
        issue = next((i for i in issues if i["id"] == args.only), None)
        if issue is None:
            sys.exit("--judge needs --only ID with a valid task id")
        passed, message = run_judge(issue, open(args.judge).read().strip())
        last = message.splitlines()[-1] if message else "(no message)"
        print("PASS" if passed else "FAIL: " + last)
        return

    if args.reset:
        for i in issues:
            i["status"] = "pending"
        with open(ISSUES, "w") as f:
            json.dump(issues, f, indent=2)
        print("All tasks set to pending.")
        return
    if args.bench:
        bench(issues, args.bench, args.strategy, args.only)
        return

    if args.only is not None:         # run exactly this task once; its status in issues.json is left alone
        todo = [i for i in issues if i["id"] == args.only]
    else:
        todo = [i for i in issues if i["status"] == "pending"]
    if not todo:
        print("Nothing to run. Use --reset to make every task pending, or --only ID.")
        return
    outcome = {}
    for issue in todo:
        print("\n== #%s %s ==" % (issue["id"], issue["title"]))
        start = time.time()
        status, attempts = work_on(issue, args.strategy)
        outcome[issue["id"]] = status
        log({"kind": "run", "id": issue["id"], "title": issue["title"],
             "status": status, "attempts": attempts,
             "strategy": args.strategy, "seconds": round(time.time() - start, 1)})
        if args.only is None:
            issue["status"] = status
            with open(ISSUES, "w") as f:      # save after every task
                json.dump(issues, f, indent=2)
    print("\n== Summary ==")
    for i in todo:
        print("  #%s %-28s %s" % (i["id"], i["title"], outcome[i["id"]]))


if __name__ == "__main__":
    main()
