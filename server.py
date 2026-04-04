import json
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

from agent.graph import agent

logger = logging.getLogger("server")

app = FastAPI(title="Builder Agent Server")

# Ensure directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("generated_project", exist_ok=True)

# Serve generated project at /preview/*
app.mount("/preview", StaticFiles(directory="generated_project", html=True), name="preview")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


class ChatRequest(BaseModel):
    prompt: str


@app.get("/api/chat")
async def chat(prompt: str):
    def event_generator():
        try:
            for event in agent.stream(
                {"user_prompt": prompt}, {"recursion_limit": 100}
            ):
                for node, state in event.items():
                    data = {"node": node}

                    # Capture coder state updates
                    if "coder_state" in state and state["coder_state"]:
                        cs = state["coder_state"]
                        idx = getattr(cs, "current_step_idx", 0)
                        if hasattr(cs, "task_plan") and cs.task_plan:
                            steps = cs.task_plan.implementation_steps
                            total = len(steps)
                            data["progress"] = f"{idx}/{total}"
                            # Show the step that was just completed (idx-1)
                            completed_idx = max(0, idx - 1)
                            if steps and completed_idx < len(steps):
                                data["current_task"] = steps[completed_idx].task_description
                                data["current_file"] = steps[completed_idx].filepath

                    # Capture plan
                    if "plan" in state and state["plan"]:
                        try:
                            data["plan"] = state["plan"].model_dump()
                        except Exception:
                            data["plan"] = str(state["plan"])

                    # Capture status
                    if "status" in state:
                        data["status"] = state["status"]

                    yield f"data: {json.dumps(data)}\n\n"

            yield f"data: {json.dumps({'node': 'END', 'status': 'DONE'})}\n\n"
        except Exception as e:
            logger.exception("SSE stream error")
            yield f"data: {json.dumps({'node': 'ERROR', 'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
