# lmcode

A tiny, single-file CLI coding assistant that behaves like Claude Code but uses a **local model running in [LM Studio](https://lmstudio.ai)** as the backend.

You launch it from inside a project folder, type what you want, and the model uses tools to read, write, and run things directly in that folder.

---

## What it does

- Connects to LM Studio's OpenAI-compatible local server (`/v1/chat/completions`).
- Gives the model four tools and lets it call them in a loop until your request is done:
  - `read_file(path)` — read a file in the working directory.
  - `write_file(path, content)` — create or overwrite a file with full content.
  - `list_files(path)` — list a directory.
  - `run_bash(command)` — run a shell command (you confirm each one with `y`).
- Sandboxes all file access to the folder you launched it from — the model can't write outside it.
- Keeps an in-memory chat history so you can iterate (`/reset` to clear, `/exit` or Ctrl-D to quit).

It's a single Python file with **no third-party dependencies** — stdlib only.

---

## Requirements

- Python 3.8+
- [LM Studio](https://lmstudio.ai) with:
  - A model loaded that supports **OpenAI-style tool / function calling** (e.g. Qwen2.5-Coder-Instruct, Llama 3.1 Instruct, Mistral Nemo Instruct). Models without tool-calling support will just chat at you and never touch your files.
  - The **local server running** (LM Studio → "Developer" / "Local Server" tab → Start).

---

## Setup

```bash
# 1. In LM Studio: load a tool-calling model and click "Start Server".
#    Default URL is http://localhost:1234

# 2. Drop lmcode.py somewhere on your PATH (optional):
chmod +x lmcode.py
```

No `pip install` needed.

---

## Usage

```bash
cd ~/dev/my-project        # the folder you want code written into
python3 /path/to/lmcode.py
```

Example session:

```
lmcode · model=qwen2.5-coder-7b-instruct · dir=/Users/alex/dev/my-project
Type your request. /reset clears history, /exit or Ctrl-D quits.

» make a python script that fetches the current bitcoin price and prints it
  → write_file(path='btc.py', content='import urllib.request...')

Created btc.py. Run it with `python3 btc.py`.

» add a --currency flag so I can pick USD/EUR/GBP
  → read_file(path='btc.py')
  → write_file(path='btc.py', content='import argparse...')

Done — `python3 btc.py --currency EUR` now works.
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
  python3 lmcode.py
```

---

## Safety

- File I/O is restricted to the current working directory (paths that resolve outside it are rejected).
- `run_bash` **always** asks you to confirm with `y` before executing.
- There's nothing else stopping a misbehaving model from filling your folder with junk — keep it pointed at a project directory, not your home folder.

---

## Limitations

- No streaming output — replies appear after the model finishes each round.
- No diff/patch tool: edits happen by rewriting the whole file. Fine for small files, wasteful for large ones.
- Quality depends entirely on the local model. A 7B coder model handles small scripts well; for serious refactors use a larger model (32B+) and expect it to be slower than Claude.
- Tool-call rounds per user turn are capped at 25 to prevent runaway loops.

---

## License

Do whatever you want with it.
