import time
import logging

from dotenv import load_dotenv
from langchain.globals import set_verbose, set_debug
from langchain_groq.chat_models import ChatGroq
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent

from agent.prompts import *
from agent.states import *
from agent.tools import write_file, read_file, get_current_directory, list_files, list_file, edit_file, run_cmd, search_files

_ = load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────
# Disable LangChain's extremely verbose debug/trace logging to save tokens
set_debug(False)
set_verbose(False)

# Use a concise logger for our own agent steps
logger = logging.getLogger("agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# ── LLM with retry configuration ────────────────────────────────────
MAX_RETRIES = 5
INITIAL_BACKOFF = 4  # seconds

# Best combo found through testing:
#  - planner_llm: Llama 3.3 70B + json_schema → reliable structured output
#  - coder_llm:   GPT-OSS 120B → only model with reliable tool calling on Groq free tier
#                  max_retries=5 so the SDK auto-retries 429s inside react agent loops
planner_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    max_retries=5,
)
coder_llm = ChatGroq(
    model="openai/gpt-oss-120b",
    max_retries=5,
)


def invoke_with_retry(fn, *args, **kwargs):
    """Invoke an LLM call with exponential backoff on rate-limit (429) errors."""
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "429" in err_str or "rate_limit" in err_str or "rate limit" in err_str
            if is_rate_limit and attempt < MAX_RETRIES:
                wait = INITIAL_BACKOFF * (2 ** (attempt - 1))  # 6, 12, 24, 48…
                logger.warning(
                    f"Rate-limited (attempt {attempt}/{MAX_RETRIES}). "
                    f"Waiting {wait}s before retry…"
                )
                time.sleep(wait)
                last_exc = e
            else:
                raise
    raise last_exc  # should not reach here


# ── Agent Nodes ──────────────────────────────────────────────────────

def planner_agent(state: dict) -> dict:
    """Converts user prompt into a structured Plan."""
    user_prompt = state["user_prompt"]
    logger.info("🗺️  Planner – creating project plan…")
    resp = invoke_with_retry(
        planner_llm.with_structured_output(Plan, method="json_schema").invoke,
        planner_prompt(user_prompt),
    )
    if resp is None:
        raise ValueError("Planner did not return a valid response.")
    logger.info(f"✅ Plan created: {resp.name} ({len(resp.files)} files)")
    return {"plan": resp}


def architect_agent(state: dict) -> dict:
    """Creates TaskPlan from Plan."""
    plan: Plan = state["plan"]
    logger.info("📐 Architect – breaking plan into tasks…")
    resp = invoke_with_retry(
        planner_llm.with_structured_output(TaskPlan, method="json_schema").invoke,
        architect_prompt(plan=plan.model_dump_json()),
    )
    if resp is None:
        raise ValueError("Architect did not return a valid response.")

    resp.plan = plan
    logger.info(f"✅ TaskPlan ready: {len(resp.implementation_steps)} steps")
    return {"task_plan": resp}


def coder_agent(state: dict) -> dict:
    """LangGraph tool-using coder agent with rate-limit resilience."""
    coder_state: CoderState = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state, "status": "DONE"}

    current_task = steps[coder_state.current_step_idx]
    step_num = coder_state.current_step_idx + 1
    total = len(steps)

    logger.info(
        f"💻 Coder [{step_num}/{total}] – {current_task.filepath}: "
        f"{current_task.task_description[:80]}…"
    )

    existing_content = read_file.run(current_task.filepath)

    system_prompt = coder_system_prompt()
    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n"
        f"Existing content:\n{existing_content}\n"
        "Use write_file(path, content) to save your changes."
    )

    coder_tools = [read_file, write_file, edit_file, list_files, list_file,
                   get_current_directory, run_cmd, search_files]

    # Build a fresh react agent for each step
    react_agent = create_react_agent(coder_llm, coder_tools)

    # Retry the whole coder step on rate-limit
    invoke_with_retry(
        react_agent.invoke,
        {"messages": [{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}]},
    )

    logger.info(f"✅ Coder [{step_num}/{total}] – {current_task.filepath} done")

    # Brief cooldown between steps to stay under TPM
    if step_num < total:
        cooldown = 10  # seconds – react agent makes multiple internal LLM calls per step
        logger.info(f"⏳ Cooling down {cooldown}s to stay within rate limits…")
        time.sleep(cooldown)

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}


# ── Graph ────────────────────────────────────────────────────────────

graph = StateGraph(dict)

graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_conditional_edges(
    "coder",
    lambda s: "END" if s.get("status") == "DONE" else "coder",
    {"END": END, "coder": "coder"},
)

graph.set_entry_point("planner")
agent = graph.compile()

if __name__ == "__main__":
    result = agent.invoke(
        {"user_prompt": "Build a colourful modern todo app in html css and js"},
        {"recursion_limit": 100},
    )
    print("Final State:", result)
