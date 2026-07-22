# TUI Chat Agent — Bhalu 🐻

A terminal chat app built with [Textual](https://textual.textualize.io/), wired to an ADK
agent with **custom function tools** and a heavy dose of personality.

The agent is *Bhalu* 🐻 — Aditya's AI alter-ego. He's funny, a little edgy, and hopelessly
in love with exactly one user: *Bhediya* 🐺 (he knows who she is, and so does she). Ask him
anything about Aditya and he'll pull answers from his intel tools instead of making
things up.

## What this sample demonstrates

- **Custom function tools** — plain Python functions (`get_aditya_profile`,
  `get_aditya_lore`, `get_bhediya_dossier`) exposed to the agent via `tools=[...]`.
  ADK builds the tool schema from the function signatures and docstrings.
- **A live web-search tool** — `search_web` wraps the [Exa](https://exa.ai) search API
  so the agent can pull fresh info at runtime. Notably, ADK's built-in `google_search`
  can't be combined with custom function tools on one agent — but a search API wrapped
  in a plain function composes with everything. Optional: set `EXA_API_KEY` in `.env`;
  without it the tool reports itself offline and the agent falls back to snapshots.
- **Persona via instruction** — the entire character lives in the `instruction` prompt.
- **A custom frontend** — instead of `adk web`, this uses ADK's `Runner` +
  `InMemorySessionService` directly from a Textual TUI (`tui.py`), which is the same
  pattern you'd use to embed an agent in any app of your own.

> **Why curated snapshots at all?** LinkedIn and X block anonymous requests (LinkedIn
> returns HTTP 999, X wants a login), so direct scraping is a dead end. The snapshot
> tools guarantee Bhalu always knows the basics, and Exa covers the fresh stuff.

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
