"""Streamlit UI for the Deep Agent Todo Planner."""

import json
import os

import streamlit as st
from dotenv import load_dotenv

from agent_core import WORKSPACE, create_planner_agent, stream_planner

load_dotenv()

st.set_page_config(page_title="Deep Agent Todo Planner", page_icon="🧠", layout="wide")

STEPS = [
    ("plan", "1. Plan", "write_todos breaks the goal into phases"),
    ("tasks", "2. Tasks", "write_file creates day-by-day tasks"),
    ("store", "3. Store", "FilesystemBackend saves to workspace/"),
    ("review", "4. Review", "read_file + edit_file refine the plan"),
    ("roadmap", "5. Roadmap", "write_file produces roadmap.md"),
]

TOOL_LABELS = {
    "write_todos": "Planning",
    "write_file": "Write file",
    "read_file": "Read file",
    "edit_file": "Edit file",
    "ls": "List files",
    "glob": "Find files",
    "grep": "Search files",
}


def init_state():
    if "step_status" not in st.session_state:
        st.session_state.step_status = {k: "pending" for k, _, _ in STEPS}
    if "activity" not in st.session_state:
        st.session_state.activity = []
    if "todos" not in st.session_state:
        st.session_state.todos = []


def render_pipeline():
    cols = st.columns(len(STEPS))
    for col, (key, title, desc) in zip(cols, STEPS):
        status = st.session_state.step_status.get(key, "pending")
        icon = {"pending": "⬜", "active": "🔄", "done": "✅"}.get(status, "⬜")
        with col:
            st.markdown(f"### {icon} {title}")
            st.caption(desc)


def format_tool_detail(event: dict) -> str:
    tool = event["tool"]
    inp = event.get("input") or {}
    label = TOOL_LABELS.get(tool, tool)
    if tool == "write_todos":
        todos = inp.get("todos", [])
        lines = [f"- {t.get('content', t)}" for t in todos[:6]]
        extra = f" (+{len(todos)-6} more)" if len(todos) > 6 else ""
        return f"**{label}**{extra}\n" + "\n".join(lines)
    path = inp.get("file_path", inp.get("path", ""))
    if path:
        return f"**{label}** → `{path}`"
    return f"**{label}**"


def load_workspace_files():
    tasks_path = WORKSPACE / "tasks.json"
    roadmap_path = WORKSPACE / "roadmap.md"
    tasks = None
    if tasks_path.exists():
        try:
            tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            tasks = tasks_path.read_text(encoding="utf-8")
    roadmap = roadmap_path.read_text(encoding="utf-8") if roadmap_path.exists() else None
    return tasks, roadmap


init_state()

st.title("Deep Agent Todo Planner")
st.markdown(
    "Watch a **Deep Agent** plan, break down tasks, store files in a workspace, "
    "review, and generate a learning roadmap."
)

with st.sidebar:
    st.header("Settings")
    goal = st.text_input("Learning goal", "I want to learn Python in 30 days.")
    model = st.selectbox("Model", ["openai:gpt-4o-mini", "openai:gpt-4o"], index=0)
    run = st.button("Run Deep Agent", type="primary", use_container_width=True)
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Set OPENAI_API_KEY in .env")

st.subheader("Agent pipeline")
render_pipeline()

log_box = st.empty()
progress = st.progress(0, text="Waiting to start...")

st.subheader("Live activity")
activity_area = st.container()

tab_tasks, tab_roadmap, tab_workspace = st.tabs(["Tasks JSON", "Roadmap", "Workspace"])

if run:
    if not os.getenv("OPENAI_API_KEY"):
        st.stop()

    st.session_state.step_status = {k: "pending" for k, _, _ in STEPS}
    st.session_state.activity = []
    st.session_state.todos = []
    done_count = 0

    with st.spinner("Deep Agent working..."):
        agent = create_planner_agent(model)
        for event in stream_planner(agent, goal):
            if event["type"] == "tool":
                step = event["step"]
                if step in st.session_state.step_status:
                    st.session_state.step_status[step] = "done"
                    for k, _, _ in STEPS:
                        if st.session_state.step_status[k] == "pending":
                            st.session_state.step_status[k] = "active"
                            break
                if event["tool"] == "write_todos":
                    todos = (event.get("input") or {}).get("todos", [])
                    st.session_state.todos = todos
                st.session_state.activity.append(event)
                done_count = sum(1 for v in st.session_state.step_status.values() if v == "done")
                progress.progress(min(done_count / len(STEPS), 1.0), text=f"Step {done_count}/{len(STEPS)}")
                with activity_area:
                    for ev in reversed(st.session_state.activity[-12:]):
                        st.markdown(format_tool_detail(ev))
                        if ev.get("output") and ev["tool"] != "write_todos":
                            preview = str(ev["output"])[:300]
                            st.code(preview + ("..." if len(str(ev["output"])) > 300 else ""))
                render_pipeline()
            elif event["type"] == "message":
                log_box.success(event["content"][:500])
            elif event["type"] == "done":
                for k in st.session_state.step_status:
                    st.session_state.step_status[k] = "done"
                progress.progress(1.0, text="Complete")
                render_pipeline()

tasks, roadmap = load_workspace_files()

with tab_tasks:
    if st.session_state.todos:
        st.json(st.session_state.todos)
    elif tasks:
        if isinstance(tasks, list):
            st.dataframe(tasks, use_container_width=True)
        else:
            st.code(tasks)
    else:
        st.info("Tasks appear here after the agent writes tasks.json")

with tab_roadmap:
    if roadmap:
        st.markdown(roadmap)
    else:
        st.info("Roadmap appears here after the agent writes roadmap.md")

with tab_workspace:
    files = sorted(WORKSPACE.glob("*"))
    if files:
        for f in files:
            st.markdown(f"**{f.name}** ({f.stat().st_size} bytes)")
            st.code(f.read_text(encoding="utf-8")[:2000])
    else:
        st.info("Workspace is empty until the agent writes files")
