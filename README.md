# 🛠️ Buildify

https://buildify-v2.onrender.com

**Buildify** is an AI-powered coding assistant built using **LangGraph**. It acts as a multi-agent development team - **Planner**, **Architect**, and **Coder**, to transform your natural language requests into complete, working projects.

---

## ✨ Features

- **Multi-Agent Pipeline**: Planner → Architect → Coder workflow for structured project generation
- **Dual-Model Strategy**: Uses Llama 3.3 70B for planning/architecture and GPT-OSS 120B for coding
- **Live Web UI**: Real-time streaming logs with progress bar via Server-Sent Events (SSE)
- **Rate-Limit Resilient**: Built-in retry/backoff logic for Groq free-tier rate limits
- **Instant Preview**: View generated projects directly in the browser at `/preview`
- **Sandboxed Tools**: File I/O is restricted to the `generated_project/` directory for safety

---

## 🚀 Getting Started

### Prerequisites
1. **uv**: Install `uv` following the [Astral documentation](https://docs.astral.sh/uv/getting-started/installation/).
2. **Groq API Key**: Get a free API key from the [Groq Console](https://console.groq.com/keys).

### Installation & Setup
1. Clone the repository and navigate to the project directory.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_actual_api_key_here
   ```

### Running the Web UI (Recommended)
Start the FastAPI server:
```bash
uv run python server.py
```
Then open **http://localhost:8080** in your browser.

- **Build a project**: Type your prompt and click **Generate**
- **Preview the result**: Visit **http://localhost:8080/preview**

### Running via CLI
For terminal-based usage without the web UI:
```bash
uv run python main.py
```

---

## 🏗️ Architecture

```
User Prompt
    │
    ▼
┌──────────┐   Llama 3.3 70B    ┌────────────┐   Llama 3.3 70B    ┌──────────┐
│ Planner  │ ─────────────────► │ Architect  │ ─────────────────► │  Coder   │
│          │   (json_schema)    │            │   (json_schema)    │          │
└──────────┘                    └────────────┘                    └──────────┘
 Creates Plan                    Breaks into                      GPT-OSS 120B
 (name, files,                   implementation                   (tool calling)
  features)                      tasks per file                   writes actual code
                                                                       │
                                                                       ▼
                                                                  generated_project/
                                                                  ├── index.html
                                                                  ├── styles.css
                                                                  └── script.js
```

### Models Used (Groq Free Tier)

| Role | Model | Why |
|------|-------|-----|
| **Planner & Architect** | `llama-3.3-70b-versatile` | Reliable structured output via `json_schema` mode |
| **Coder** | `openai/gpt-oss-120b` | Only Groq model with reliable tool calling |

### Rate-Limit Handling
- **SDK-level retries** (`max_retries=5`) handle 429 errors inside the react agent's internal loop
- **Inter-step cooldown** (10s) between coder steps to stay within TPM limits
- **Exponential backoff** on outer calls for additional resilience

---

## 📁 Project Structure

```
web_builder_agent/
├── server.py              # FastAPI server with SSE streaming
├── main.py                # CLI entry point
├── .env                   # Groq API key
├── agent/
│   ├── graph.py           # LangGraph pipeline (planner → architect → coder)
│   ├── states.py          # Pydantic models (Plan, TaskPlan, CoderState)
│   ├── prompts.py         # System prompts for each agent role
│   └── tools.py           # Sandboxed file I/O and shell tools
├── static/
│   └── index.html         # Web UI frontend
└── generated_project/     # Output directory for generated projects
```

---

## 🧪 Example Prompts
- Build a modern todo list app with HTML, CSS, and JS
- Create a simple calculator web application
- Build a notes app with local storage
- Create a weather dashboard with a search bar

---

## ⚠️ Limitations
- **Groq Free Tier**: Rate-limited to ~8,000 tokens/minute for GPT-OSS 120B. Projects take 2-3 minutes to generate due to cooldown periods.
- **Static Projects Only**: Best suited for HTML/CSS/JS projects. No server-side runtime (Node, Python, etc.) for generated projects.
- **No Validation Node**: Generated code is not automatically tested for correctness.

---

## 📄 License
MIT
