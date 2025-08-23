# Build Agents with ADK

This repository contains sample agents built using the Google ADK (Agentic Development Kit).


## Requirements

- Python 3.10 or higher (see `.python-version` for the recommended version)
- [google-adk](https://pypi.org/project/google-adk/) >= 1.1.1
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
   Copy `.env.example` to `.env` and fill in the required values (e.g., `GOOGLE_API_KEY`).


## Running the Agent

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