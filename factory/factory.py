import subprocess
import sys
import os
import re
import json

# Anchor paths relative to this script's directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration
ULLAMA_BIN = os.path.join(SCRIPT_DIR, "../src/ullama")
MODEL_PATH = os.path.join(SCRIPT_DIR, "../models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf")
LIB_PATH = "/home/drlandi/tools/llama.cpp/build/bin"
MAX_ATTEMPTS = 3
ISSUES_FILE = os.path.join(SCRIPT_DIR, "issues.json")

def load_issues():
    if not os.path.exists(ISSUES_FILE):
        print(f"[!] Error: {ISSUES_FILE} not found!")
        return []
    with open(ISSUES_FILE, "r") as f:
        return json.load(f)

def save_issues(issues):
    with open(ISSUES_FILE, "w") as f:
        json.dump(issues, f, indent=2)

def ask_ullama(prompt):
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{LIB_PATH}:{env.get('LD_LIBRARY_PATH', '')}"
    
    flat_prompt = " ".join(prompt.splitlines())
    
    try:
        process = subprocess.Popen(
            [ULLAMA_BIN, MODEL_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        stdout, stderr = process.communicate(input=flat_prompt + "\n")
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', stdout)
        
        # 1. Strip out the C engine's "--- Response ---" header if present
        if "--- Response ---" in clean_output:
            clean_output = clean_output.split("--- Response ---", 1)[1]
            
        # 2. Strip out trailing telemetry stats like "[16.04 tok/s]" from the footer
        clean_output = re.sub(r'\[\d+\.\d+\s*tok/s\]', '', clean_output)
            
        return clean_output.strip()
    except Exception as e:
        print(f"[!] Error: {e}")
        return ""

def extract_code_block(text):
    # 1. Try standard python markdown block
    match = re.search(r"```python\s*(.*?)\s*(?:```|$)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # 2. Try generic markdown block
    match_generic = re.search(r"```\s*(.*?)\s*(?:```|$)", text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()
        
    # 3. Fallback: if raw text starts with backticks, strip them manually
    cleaned = text.strip()
    if cleaned.startswith("```python"):
        cleaned = cleaned[9:].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()
        
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
        
    return cleaned

def run_code(filename):
    result = subprocess.run([sys.executable, filename], capture_output=True, text=True)
    if result.returncode == 0:
        return True, result.stdout
    else:
        return False, result.stderr

def main():
    issues = load_issues()
    pending_issues = [i for i in issues if i.get("status") == "pending"]
    
    if not pending_issues:
        print("[*] No pending issues found in queue.")
        return

    outputs_dir = os.path.join(SCRIPT_DIR, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    resolved_count = 0
    
    for issue in pending_issues:
        issue_id = issue["id"]
        title = issue["title"]
        prompt_text = issue["prompt"]
        target_filename = os.path.join(SCRIPT_DIR, issue["output"])
        temp_filename = os.path.join(outputs_dir, f"issue_{issue_id}_temp.py")
        
        print(f"\n==========================================")
        print(f" PROCESSING ISSUE #{issue_id}: {title}")
        print(f"==========================================")
        
        current_prompt = prompt_text
        task_success = False
        
        for attempt in range(1, MAX_ATTEMPTS + 1):
            print(f"\n--- Iteration {attempt}/{MAX_ATTEMPTS} ---")
            raw_response = ask_ullama(current_prompt)
            code_content = extract_code_block(raw_response)
            
            if not code_content:
                print("[!] Warning: Empty code received. Retrying...")
                continue
                
            with open(temp_filename, "w") as f:
                f.write(code_content)
                
            success, output = run_code(temp_filename)
            
            if success:
                print(f"\n[+] Issue #{issue_id} RESOLVED! Saved as {issue['output']}")
                print("[Output]:\n", output.strip())
                if os.path.exists(target_filename):
                    os.remove(target_filename)
                os.rename(temp_filename, target_filename)
                
                # Update issue status in queue
                issue["status"] = "resolved"
                resolved_count += 1
                task_success = True
                break
            else:
                print(f"\n[!] Failed attempt {attempt}. Error:\n{output.strip()}")
                clean_error = " ".join(output.splitlines())
                current_prompt = (
                    f"Your previous Python code failed with this error: {clean_error} "
                    f"Fix the code for this task: '{prompt_text}'. "
                    f"Provide ONLY the corrected Python code inside a markdown block."
                )
                
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        if not task_success:
            print(f"\n[X] Issue #{issue_id} FAILED all attempts.")
            issue["status"] = "failed"
            
        # Save state back to JSON immediately after each task
        save_issues(issues)
            
    print(f"\n==========================================")
    print(f" QUEUE RUN COMPLETE: {resolved_count}/{len(pending_issues)} Issues Resolved.")
    print(f"==========================================")

if __name__ == "__main__":
    main()