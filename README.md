# Build Agents with ADK

This repository contains sample agents built using the Google ADK (Agentic Development Kit).

## Samples

| Folder | Agent | What it shows |
| --- | --- | --- |
| `basic-agent` | `greeting_agent` | Minimal LLM agent with just an instruction |
| `built-in-tools` | `google_search_agent` | Using ADK's built-in `google_search` tool |
| `structured-output-schema` | `email_agent` | Pydantic `output_schema` for validated JSON output |
| [`tui-chat-agent`](tui-chat-agent/) | `bhalu_agent` 🐻 | The Den: an OpenTUI chat about Bhalu & Bhediya, backed by ADK custom tools |

## Requirements

- Python 3.10 or higher (see `.python-version` for the recommended version)
- [google-adk](https://pypi.org/project/google-adk/) >= 1.39.1, < 2 (locked for Gemini streaming and tool-call support)
- [python-dotenv](https://pypi.org/project/python-dotenv/) >= 1.1.0

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/krutip7/build-with-adk.git
   cd build-with-adk
   ```
2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   ```
    OR 

   ```bash
   uv venv
   ``` 

   **Inititalize Virtual Environment:**

   ```bash
   source .venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install .
   ```

    OR 

   ```bash
   uv sync
   ```
4. **Configure environment variables:**  
   Copy the template from the repository root (preserves an existing `.env`):
   ```bash
   cp -n .env.sample .env
   ```
   Open `.env` and set `GOOGLE_API_KEY` to your Gemini API key. Keep
   `GOOGLE_GENAI_USE_VERTEXAI=FALSE` for API-key authentication. For Bhalu and
   Bhediya, `GEMINI_MODEL=gemini-3.8-flash` selects the model; `EXA_API_KEY`
   is optional and enables live web search. Leave it blank for ordinary chat.
   The existing `.env.example` template also works. Never put credentials in
   either committed template.


## Running the Agent

For **The Den**, follow the [OpenTUI sample setup](tui-chat-agent/README.md).
It uses Bun for the terminal interface and Python for the ADK agent. A scripted
demo runs without API keys.

1. **Navigate to one of the sample project**  
   For instance, to run the `email_agent` agent, we checkout the `structured-output-schema` sample.
   ```bash
   cd structured-output-schema
   ```

2. **Run the agent project**  
   
   ```bash
   # Launch in Dev UI mode:
   adk web
   ```
   OR  
   ```bash
   # Chat with the agent in CLI mode:
   adk run email_agent
   ```
