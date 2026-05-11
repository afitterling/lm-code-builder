# llm-code

A tiny, single-file CLI coding assistant that behaves like Claude Code but uses a **local model running in [LM Studio](https://lmstudio.ai)** as the backend.

You launch it from inside a project folder, type what you want, and the model uses tools to read, write, and run things directly in that folder.

> ⚠️ **Hardware requirement:** need processor M4 or above. M4 is fast!

---

## What it does

- Connects to LM Studio's OpenAI-compatible local server (`/v1/chat/completions`).
- Gives the model four tools and lets it call them in a loop until your request is done:
  - `read_file(path)` — read a file in the working directory.
  - `write_file(path, content)` — create or overwrite a file with full content.
  - `list_files(path)` — list a directory.
  - `run_bash(command)` — run a shell command (you confirm each one with `y`).
- Sandboxes all file access to the folder you launched it from — the model can't write outside it.
- Fancy console UX: arrow-key history, persistent history file (`~/.llm-code_history`), autosuggestions from history, Ctrl-R search, colourised assistant panels, tool-call traces, a "thinking…" spinner, and a status bar with model + working dir.
- `/reset` to clear chat history, `/exit` or Ctrl-D to quit.

---

## Requirements

- **Apple Silicon M4 or above** — earlier chips work but feel sluggish under tool-calling loops. M4 is noticeably fast.
- Python 3.8+
- Two pip packages:
  ```bash
  pip install prompt_toolkit rich
  ```
- [LM Studio](https://lmstudio.ai) with:
  - A model loaded that supports **OpenAI-style tool / function calling** (e.g. Qwen2.5-Coder-Instruct, Llama 3.1 Instruct, Mistral Nemo Instruct). Models without tool-calling support will just chat at you and never touch your files.
  - The **local server running** (LM Studio → "Developer" / "Local Server" tab → Start).

---

## Setup

```bash
# 1. In LM Studio: load a tool-calling model and click "Start Server".
#    Default URL is http://localhost:1234

# 2. Install the two python deps:
pip install prompt_toolkit rich

# 3. Make the script executable (optional — you can also run it via python3):
chmod +x llm-code
```

---

## Usage

```bash
cd ~/dev/my-project        # the folder you want code written into
/path/to/llm-code           # or: python3 /path/to/llm-code
```

Example session:

```
╭────────────────────────────────────────────────╮
│ llm-code  ·  a local-LLM coding agent          │
│                                                │
│ model: qwen2.5-coder-7b-instruct               │
│ dir:   /Users/alex/dev/my-project              │
│                                                │
│ commands: /reset  /exit  Ctrl-D                │
│ tips: ↑/↓ history · Ctrl-R search · …          │
╰────────────────────────────────────────────────╯

» make a python script that fetches the current bitcoin price and prints it
▸ write_file(path='btc.py', content='import urllib.request...')
    wrote 412 bytes to btc.py

╭─ assistant ────────────────────────────────────╮
│ Created btc.py. Run it with `python3 btc.py`.  │
╰────────────────────────────────────────────────╯

» _
  ── llm-code  model: qwen2.5-coder-7b-instruct  dir: …  /reset · /exit ──
```

### Built-in commands

| Command  | Effect                              |
|----------|-------------------------------------|
| `/reset` | Clear chat history (keep model).    |
| `/exit`  | Quit (also Ctrl-D).                 |

### Environment variables

| Var        | Default                       | Purpose                                            |
|------------|-------------------------------|----------------------------------------------------|
| `LM_BASE`  | `http://localhost:1234/v1`    | Base URL of the LM Studio OpenAI-compatible API.   |
| `LM_MODEL` | *(first model listed)*        | Force a specific model id instead of auto-detect.  |

Example:

```bash
LM_BASE=http://192.168.1.50:1234/v1 LM_MODEL=qwen2.5-coder-32b-instruct \
  ./llm-code
```

---

## Safety

- File I/O is restricted to the current working directory (paths that resolve outside it are rejected).
- `run_bash` **always** asks you to confirm with `y` before executing.
- There's nothing else stopping a misbehaving model from filling your folder with junk — keep it pointed at a project directory, not your home folder.

---

## Limitations

- No streaming output — assistant replies appear after the model finishes each round.
- No diff/patch tool: edits happen by rewriting the whole file. Fine for small files, wasteful for large ones.
- Quality depends entirely on the local model. A 7B coder model handles small scripts well; for serious refactors use a larger model (32B+) and expect it to be slower than Claude.
- Tool-call rounds per user turn are capped at 25 to prevent runaway loops.

---

## License

Do whatever you want with it.
