# Deep Agent Todo Planner

An educational demo that uses [LangChain Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) and the OpenAI API to turn a learning goal into a structured plan, day-by-day tasks, and a final roadmap.

**Example input:** `I want to learn Python in 30 days.`

The agent plans, writes files to a local workspace, reviews its own output, and produces a readable roadmap — all through built-in Deep Agent harness tools.

---

## Architecture

```mermaid
flowchart TB
    subgraph UI["Presentation layer"]
        APP["app.py (Streamlit UI)"]
    end

    subgraph Core["Application layer"]
        AC["agent_core.py"]
    end

    subgraph Harness["Deep Agent harness (deepagents)"]
        CDA["create_deep_agent()"]
        TLM["TodoListMiddleware → write_todos"]
        FSM["FilesystemMiddleware → read/write/edit files"]
        LG["LangGraph runtime → stream_events()"]
    end

    subgraph Backends["Pluggable backends"]
        CB["CompositeBackend"]
        SB["StateBackend (ephemeral)"]
        FB["FilesystemBackend → ./workspace/"]
    end

    subgraph External["External services"]
        OAI["OpenAI API (gpt-4o-mini)"]
    end

    APP -->|"goal, model"| AC
    AC --> CDA
    CDA --> TLM
    CDA --> FSM
    CDA --> LG
    FSM --> CB
    CB --> SB
    CB -->|"/workspace/*"| FB
    CDA --> OAI
    LG -->|"tool call events"| APP
    FB -->|"tasks.json, roadmap.md"| APP
```

### Agent pipeline

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Agent as Deep Agent
    participant Todos as write_todos
    participant FS as Filesystem tools
    participant Disk as workspace/

    User->>UI: Enter learning goal
    UI->>Agent: stream_events(goal)

    Agent->>Todos: 1. Plan — decompose into phases
    Todos-->>UI: Live todo list

    Agent->>FS: 2. Tasks — write_file tasks.json
    FS->>Disk: Persist day-by-day tasks
    FS-->>UI: Tool call event

    Agent->>FS: 3. Review — read_file + edit_file
    FS-->>UI: Refinement events

    Agent->>FS: 4. Roadmap — write_file roadmap.md
    FS->>Disk: Persist final roadmap
    FS-->>UI: Completion

    UI->>User: Pipeline status + files
```

---

## Project structure

```
Deep Agent/
├── agent_core.py      # Agent setup, backend routing, event streaming
├── app.py             # Streamlit dashboard
├── requirements.txt
├── .env.example       # Copy to .env and add your API key
├── workspace/         # Agent output (tasks.json, roadmap.md) — gitignored
└── venv/              # Python virtual environment — gitignored
```

---

## Deep Agent concepts used

| Concept | Where | Purpose |
|---------|-------|---------|
| **Agent harness** | `create_deep_agent()` | Bundles planning, filesystem, and context tools out of the box |
| **TodoListMiddleware** | `write_todos` tool | Breaks a long goal into trackable phases |
| **FilesystemMiddleware** | `write_file`, `read_file`, `edit_file` | Creates and refines plan artifacts |
| **CompositeBackend** | `agent_core.make_backend()` | Routes `/workspace/` to disk, keeps harness internals ephemeral |
| **FilesystemBackend** | `workspace/` folder | Persists `tasks.json` and `roadmap.md` on local disk |
| **StateBackend** | Default route | In-memory storage for internal agent data |
| **Event streaming** | `stream_events(version="v3")` | Powers the live UI pipeline and activity log |
| **LangGraph runtime** | Under the hood | Multi-step tool loop with durable execution |

---

## Setup

### 1. Create a virtual environment

```powershell
cd "Deep Agent"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure OpenAI

```powershell
copy .env.example .env
```

Edit `.env` and set your key (UTF-8, one line):

```
OPENAI_API_KEY=sk-your-actual-key
```

> **Windows tip:** Save `.env` as UTF-8 in Notepad. UTF-16 encoding causes `embedded null character` errors.

### 3. Run the UI

```powershell
streamlit run app.py
```

Open the URL shown in the terminal (usually `http://localhost:8501`).

---

## What the UI shows

1. **Pipeline** — five steps (Plan → Tasks → Store → Review → Roadmap) with live status
2. **Live activity** — each harness tool call as it happens
3. **Tasks JSON** — structured day-by-day tasks from `tasks.json`
4. **Roadmap** — rendered `roadmap.md`
5. **Workspace** — raw files the agent wrote to disk

---

## Expected workspace output

After a successful run, the agent writes:

| File | Description |
|------|-------------|
| `workspace/tasks.json` | Day-by-day tasks with title, day, duration, status |
| `workspace/roadmap.md` | Overview, weekly milestones, resources, and tips |

These files are regenerated on each run and are not committed to git.

---

## Requirements

- Python 3.11+
- OpenAI API key
- Dependencies: `deepagents`, `langchain-openai`, `python-dotenv`, `streamlit`

---

## License

Educational demo — not intended for production use.
