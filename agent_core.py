"""Shared Deep Agent setup and streaming helpers."""

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend

WORKSPACE = Path(__file__).parent / "workspace"
WORKSPACE.mkdir(exist_ok=True)

SYSTEM_PROMPT = """You are a learning-plan Deep Agent. For every goal you receive:

1. PLAN - use write_todos to decompose the goal into ordered phases.
2. TASKS - write /workspace/tasks.json (day-by-day tasks with title, day, duration, status).
3. REVIEW - read tasks.json, note gaps or pacing issues, edit_file to fix them.
4. ROADMAP - write /workspace/roadmap.md (overview, weekly milestones, resources, tips).

Work step-by-step. Mark todos complete as you finish each phase. Be specific and practical."""

STEP_FOR_TOOL = {
    "write_todos": "plan",
    "write_file": "store",
    "read_file": "review",
    "edit_file": "review",
    "ls": "store",
    "glob": "store",
    "grep": "review",
}


def make_backend(_runtime):
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/workspace/": FilesystemBackend(
                root_dir=str(WORKSPACE.resolve()), virtual_mode=True
            ),
        },
    )


def create_planner_agent(model: str = "openai:gpt-4o-mini"):
    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        backend=make_backend,
    )


def classify_tool_event(tool_name: str, tool_input: dict) -> str:
    if tool_name == "write_todos":
        return "plan"
    if tool_name == "write_file":
        path = str(tool_input.get("file_path", tool_input.get("path", "")))
        if "roadmap" in path:
            return "roadmap"
        if "tasks" in path:
            return "tasks"
        return "store"
    if tool_name in ("read_file", "edit_file"):
        return "review"
    return STEP_FOR_TOOL.get(tool_name, "other")


def stream_planner(agent, goal: str):
    """Yield event dicts while the agent runs."""
    stream = agent.stream_events(
        {"messages": [{"role": "user", "content": f"Create a learning plan for: {goal}"}]},
        version="v3",
    )
    for call in stream.tool_calls:
        yield {
            "type": "tool",
            "tool": call.tool_name,
            "input": call.input,
            "step": classify_tool_event(call.tool_name, call.input or {}),
            "output": call.output,
            "error": call.error,
        }
    for msg in stream.messages:
        if hasattr(msg, "content") and msg.content:
            yield {"type": "message", "content": msg.content}
    yield {"type": "done"}
