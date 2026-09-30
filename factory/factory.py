#!/usr/bin/env python3
"""uLLAMA factory, version 2: a task passes only when its JUDGE says so.

The loop, per task in issues.json:
  1. Ask the model (the ullama binary) for code.
  2. Copy that code to solution.py in a fresh temporary folder, together with
     the task's test file (the judge), and run the judge.
  3. If the judge fails, ask again, this time showing the model its own
     previous code and the judge's failure message (a real repair prompt).

Usage:
  python3 factory.py           run every task whose status is "pending"
  python3 factory.py --reset   set every task back to "pending"
"""
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
        print("    [model timed out]")
        return ""
    stats = p.stderr.strip().splitlines()
    if p.returncode != 0:
        print("    [ullama failed]", " | ".join(stats[-2:]))
        return ""
    if stats:
        print("    " + stats[-1])          # the "[N tok, X tok/s]" line
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


def work_on(issue):
    """Try one task up to MAX_ATTEMPTS times. Returns (status, attempts)."""
    prompt = first_prompt(issue)
    code = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print("  attempt %d/%d" % (attempt, MAX_ATTEMPTS))
        code = extract_code(ask_model(prompt))
        passed, message = run_judge(issue, code)
        if passed:
            print("    judge: PASS")
            save(issue["output"], code)
            return "resolved", attempt
        print("    judge: FAIL ->", message.splitlines()[-1] if message else "(no message)")
        prompt = repair_prompt(issue, code, message)
    save(issue["output"] + ".failed", code)
    return "failed", MAX_ATTEMPTS


def save(name, code):
    os.makedirs(OUTPUTS, exist_ok=True)
    with open(os.path.join(OUTPUTS, name), "w") as f:
        f.write(code + "\n")


def main():
    with open(ISSUES) as f:
        issues = json.load(f)
    if "--reset" in sys.argv:
        for i in issues:
            i["status"] = "pending"
        with open(ISSUES, "w") as f:
            json.dump(issues, f, indent=2)
        print("All tasks set to pending.")
        return
    todo = [i for i in issues if i["status"] == "pending"]
    if not todo:
        print("Nothing pending. Use --reset to run everything again.")
        return
    for issue in todo:
        print("\n== #%s %s ==" % (issue["id"], issue["title"]))
        start = time.time()
        issue["status"], attempts = work_on(issue)
        with open(RESULTS, "a") as f:
            f.write(json.dumps({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "id": issue["id"],
                "title": issue["title"],
                "status": issue["status"],
                "attempts": attempts,
                "seconds": round(time.time() - start, 1),
            }) + "\n")
        with open(ISSUES, "w") as f:      # save after every task
            json.dump(issues, f, indent=2)
    print("\n== Summary ==")
    for i in todo:
        print("  #%s %-28s %s" % (i["id"], i["title"], i["status"]))


if __name__ == "__main__":
    main()
