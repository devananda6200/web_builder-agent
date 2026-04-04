# 🛠️ Web_Builder agent

**Web_builder agent** is an AI-powered coding assistant built using **LangGraph**. It acts as a multi-agent development team (Planner, Architect, and Coder) to transform your natural language requests into complete, working projects.

---

## 🚀 Getting Started

### Prerequisites
1. **uv**: Install `uv` following the [Astral documentation](https://docs.astral.sh/uv/getting-started/installation/).
2. **Groq API Key**: Get a free API key from the [Groq console](https://console.groq.com/keys).

### Installation & Setup
1. Clone the repository and navigate to the project directory.
2. Install the dependencies using `uv sync`.
3. Create a `.env` file in the root directory and add your Groq API key:
   ```env
   GROQ_API_KEY=your_actual_api_key_here
   ```

### Running the App
Start the interactive application by running:
```bash
uv run python main.py
```

### 🧪 Example Prompts
- Create a to-do list application using HTML, CSS, and JS.
- Create a simple calculator web application.
- Create a basic blog API in FastAPI with a SQLite database.

---

