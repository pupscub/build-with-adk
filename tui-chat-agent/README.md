# TUI Chat Agent — Bhalu 🐻

A terminal chat app built with [Textual](https://textual.textualize.io/), wired to an ADK
agent with **custom function tools** and a heavy dose of personality.

The agent is *Bhalu* — Aditya's AI alter-ego. He's funny, a little edgy, and hopelessly
in love with exactly one user. Ask him anything about Aditya and he'll pull answers from
his intel tools instead of making things up.

## What this sample demonstrates

- **Custom function tools** — plain Python functions (`get_aditya_profile`,
  `get_aditya_lore`) exposed to the agent via `tools=[...]`. ADK builds the tool schema
  from the function signatures and docstrings.
- **Persona via instruction** — the entire character lives in the `instruction` prompt.
- **A custom frontend** — instead of `adk web`, this uses ADK's `Runner` +
  `InMemorySessionService` directly from a Textual TUI (`tui.py`), which is the same
  pattern you'd use to embed an agent in any app of your own.

> **Why no live LinkedIn/X scraping?** Both block anonymous requests (LinkedIn returns
> HTTP 999, X wants a login). The tools serve a curated snapshot instead, with the real
> URLs attached — a practical pattern when a data source can't be hit at runtime.

## Run it

From the repo root, make sure dependencies are installed and your `.env` has a
`GOOGLE_API_KEY`:

```bash
uv sync
cp .env.example .env  # then add your key
```

Then:

```bash
cd tui-chat-agent
uv run tui.py
```

The classic runners work too:

```bash
adk run bhalu_agent   # plain CLI chat
adk web               # ADK's dev UI
```
