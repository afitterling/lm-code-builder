#!/usr/bin/env python3
"""lmcode — a tiny Claude Code-style CLI that uses LM Studio as the backend.

Run LM Studio, load a model that supports tool/function calling, start the
local server (default http://localhost:1234), then `python lmcode.py` from the
folder you want the assistant to work in.

Env vars:
  LM_BASE   base URL of the LM Studio OpenAI-compatible server
            (default: http://localhost:1234/v1)
  LM_MODEL  model id to use (default: first model returned by /v1/models)
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

LM_BASE = os.environ.get("LM_BASE", "http://localhost:1234/v1").rstrip("/")
LM_MODEL = os.environ.get("LM_MODEL", "")
WORKDIR = Path.cwd().resolve()
MAX_TOOL_ROUNDS = 25

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file inside the working directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content. "
                           "Pass the full file contents — there is no patch tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List entries in a directory (default '.').",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command in the working directory. "
                           "The user is prompted to confirm before it runs.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
]


def safe_path(p: str) -> Path:
    target = (WORKDIR / p).resolve()
    if target != WORKDIR and WORKDIR not in target.parents:
        raise ValueError(f"path escapes working directory: {p}")
    return target


def tool_read_file(path: str) -> str:
    return safe_path(path).read_text(encoding="utf-8", errors="replace")


def tool_write_file(path: str, content: str) -> str:
    target = safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} bytes to {path}"


def tool_list_files(path: str = ".") -> str:
    p = safe_path(path)
    if not p.is_dir():
        return f"not a directory: {path}"
    return "\n".join(
        e.name + ("/" if e.is_dir() else "") for e in sorted(p.iterdir())
    ) or "(empty)"


def tool_run_bash(command: str) -> str:
    print(f"\n  $ {command}")
    try:
        confirm = input("  run this command? [y/N] ").strip().lower()
    except EOFError:
        confirm = "n"
    if confirm != "y":
        return "user declined to run the command"
    proc = subprocess.run(
        command, shell=True, cwd=WORKDIR,
        capture_output=True, text=True, timeout=300,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if len(out) > 8000:
        out = out[:4000] + "\n…[truncated]…\n" + out[-4000:]
    return f"exit={proc.returncode}\n{out}"


TOOL_IMPL = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "list_files": tool_list_files,
    "run_bash": tool_run_bash,
}


def http_json(method: str, url: str, payload=None, timeout=600):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {body[:500]}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"cannot reach {url}: {e.reason}") from None


def detect_model() -> str:
    if LM_MODEL:
        return LM_MODEL
    data = http_json("GET", f"{LM_BASE}/models", timeout=10)
    ids = [m["id"] for m in data.get("data", [])]
    if not ids:
        sys.exit("No models loaded in LM Studio — load one in the UI first.")
    return ids[0]


SYSTEM_PROMPT = (
    f"You are a coding assistant working inside the folder {WORKDIR}.\n"
    "You have tools: read_file, write_file, list_files, run_bash.\n"
    "When the user asks for code, write it directly into files with write_file.\n"
    "write_file always overwrites, so pass the complete file content.\n"
    "Stay inside the working directory. Keep chat replies short — the real\n"
    "output is the files you create. Stop calling tools once the task is done."
)


def render_args(args: dict) -> str:
    parts = []
    for k, v in args.items():
        s = repr(v)
        if len(s) > 80:
            s = s[:77] + "...'"
        parts.append(f"{k}={s}")
    return ", ".join(parts)


def agent_turn(model: str, messages: list) -> None:
    for _ in range(MAX_TOOL_ROUNDS):
        resp = http_json("POST", f"{LM_BASE}/chat/completions", {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.2,
            "stream": False,
        })
        msg = resp["choices"][0]["message"]
        # Normalise: some servers omit content when tool_calls present.
        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": msg.get("tool_calls") or [],
        })
        if msg.get("content"):
            print(f"\n{msg['content'].strip()}\n")

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return

        for call in tool_calls:
            name = call["function"]["name"]
            raw = call["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw)
            except json.JSONDecodeError:
                args = {}
            print(f"  → {name}({render_args(args)})")
            impl = TOOL_IMPL.get(name)
            try:
                result = impl(**args) if impl else f"unknown tool: {name}"
            except Exception as e:
                result = f"ERROR: {type(e).__name__}: {e}"
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "name": name,
                "content": str(result),
            })
    print("(stopped: tool-call round limit reached)")


def main() -> None:
    try:
        model = detect_model()
    except RuntimeError as e:
        sys.exit(str(e))

    print(f"lmcode · model={model} · dir={WORKDIR}")
    print("Type your request. /reset clears history, /exit or Ctrl-D quits.\n")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    while True:
        try:
            user = input("» ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not user:
            continue
        if user in ("/exit", "/quit"):
            return
        if user == "/reset":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("(history cleared)\n")
            continue

        messages.append({"role": "user", "content": user})
        try:
            agent_turn(model, messages)
        except RuntimeError as e:
            print(f"\n[error] {e}\n")
            messages.pop()  # roll back the user message so retry is clean


if __name__ == "__main__":
    main()
