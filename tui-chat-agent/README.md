# The Den · Bhalu & Bhediya

A cozy terminal chat about a bear, a wolf, and their lore. Built with
[OpenTUI](https://opentui.com/) + React, with a Python Google ADK agent behind it.

![The Den, captured from the OpenTUI renderer](docs/preview-120.svg)

**Bhalu** is the resident bear: a builder, an enthusiastic self-roaster, and a
bear with a soft spot for **Bhediya**, the wolf. Anyone can pull up a chair and
ask about either of them. The agent uses curated tools for facts and optional Exa
search for fresh information.

The characters use only **Bhalu** and **Bhediya**. Their real names and personal
profile links are absent from the character notes and interface. The agent is
instructed not to reveal or confirm real identities, and a shared ADK output
filter replaces known names before replies reach any frontend, including names
split across streamed chunks. Search titles and excerpts use the same filter;
identifying URLs are omitted. Generated tool arguments are filtered before ADK
executes or records them.

## Try it

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and
[Bun](https://bun.sh/docs/installation) (tested with Bun 1.3.11). Python 3.10+
is supported; the repository defaults to 3.13. Use a modern terminal with true
color. The layout adapts from 60×24 to a wide view with character cards at 105×38+.

From the repository root:

```bash
uv sync --frozen
cd tui-chat-agent
bun install --frozen-lockfile
bun run demo
```

Demo mode is a **scripted preview**, visibly labeled in the app. It exercises the
same Python bridge, streamed rendering, tools display, and controls without API
calls. Try the starter prompts to meet both characters.

## Live chat

1. From the repository root, install the Python dependencies and create your
   local configuration. If `.env` already exists, edit it instead of copying
   over it.

   ```bash
   uv sync --frozen
   cp -n .env.sample .env
   ```

2. Open the repo-root `.env` in your editor and fill in these settings:

   ```dotenv
   GOOGLE_GENAI_USE_VERTEXAI=FALSE
   GOOGLE_API_KEY=paste_your_gemini_key_here
   GEMINI_MODEL=gemini-3.8-flash
   EXA_API_KEY=
   ```

   | Variable | What to enter |
   | --- | --- |
   | `GOOGLE_GENAI_USE_VERTEXAI` | Keep `FALSE` to use the Gemini Developer API. No Google Cloud project or location settings are needed for this mode. |
   | `GOOGLE_API_KEY` | Your key from [Google AI Studio](https://aistudio.google.com/apikey). Required for live replies. |
   | `GEMINI_MODEL` | Defaults to `gemini-3.8-flash`. You can set another available [Gemini model](https://ai.google.dev/gemini-api/docs/models), including the `gemini-flash-latest` alias. |
   | `EXA_API_KEY` | Optional key from the [Exa dashboard](https://dashboard.exa.ai/api-keys). Leave blank to chat using the curated character notes. |

   Put the actual key only in `.env`, which Git ignores. The committed sample
   stays empty. Restart the app after changing settings; no `source .env` step
   is needed. In OpenTUI, an already exported shell variable overrides the file,
   so clear stale overrides if the app uses an unexpected key or model.

3. Install the terminal frontend and start live chat:

   ```bash
   cd tui-chat-agent
   bun install --frozen-lockfile
   bun start
   ```

4. Try **Meet Bhalu** or **Meet Bhediya**, then send a question. `bun run demo`
   remains a scripted preview; use `bun start` for Gemini replies.

The Python bridge and standard ADK runners load the repo-root `.env`. Without a
Google key, the UI shows setup guidance. Without an Exa key, the agent can still
use its curated notes and reports live search as offline. Search errors are
returned to the agent so it can explain the limitation.

### Troubleshooting

See Google's [Gemini troubleshooting guide](https://ai.google.dev/gemini-api/docs/troubleshooting)
for API error details.

| Symptom | Next step |
| --- | --- |
| The UI asks for `GOOGLE_API_KEY` | Check that `.env` is in the repository root, paste the key after `=`, and restart. |
| Gemini rejects the key or returns 403 | Check the key and its Gemini API permissions in AI Studio. |
| Gemini returns 429 | Check your project's quota and billing in AI Studio, then retry when quota is available. |
| Gemini returns 503 / high demand | Retry after a short wait, or choose another available model with `GEMINI_MODEL` and restart. |
| Replies say this is a scripted preview | Exit and run `bun start` instead of `bun run demo`. |
| Live web search is offline | Add `EXA_API_KEY` to `.env` and restart; ordinary chat works without it. |

To test the Gemini connection directly, this command reads the same `.env`
without printing the key. Run it from the repository root:

```bash
uv run --frozen python - <<'PY'
import os
from dotenv import load_dotenv
from google import genai

load_dotenv('.env')
client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])
response = client.models.generate_content(
    model=os.getenv('GEMINI_MODEL', '').strip() or 'gemini-3.8-flash',
    contents='Say hello to Bhalu and Bhediya in one sentence.',
)
print(response.text)
PY
```

## Make yourself at home

- **Enter** sends; **Shift+Enter** or **Ctrl+J** adds a line. Multiline paste works.
- **F2–F5**, or click a starter, to fill the composer with a suggested question.
- **Esc** stops the current reply. You can draft your next message while Bhalu
  talks; Enter waits until that reply finishes, so messages cannot overlap.
- **Page Up / Page Down** or the mouse wheel scrolls the conversation. New text
  follows the bottom unless you have scrolled up.
- **Ctrl+N** or `/new` starts a fresh chat and clears this session's history.
- **F1** or `/help` shows the shortcuts. **Ctrl+C** or `/quit` exits.

Conversations live in memory and disappear when the app closes. No local chat
files are written. In live mode, messages and tool results go to Google; Exa
receives search queries when the agent uses web search. Curated notes are
snapshots, not guarantees of current facts; a search index may not have every
LinkedIn profile or X post.

## What this sample teaches

```text
OpenTUI + React  ← JSON lines →  bridge.py  →  ADK Runner
                                              ├─ get_bhalu_profile
                                              ├─ get_bhalu_lore
                                              ├─ get_bhediya_dossier
                                              └─ search_web (async HTTPX → Exa)
```

- **Custom function tools:** ADK builds schemas from Python signatures and docstrings.
- **A custom frontend:** Bun owns the terminal; one Python subprocess owns the ADK
  session. There is no HTTP server or port to configure.
- **Streaming and lifecycle:** replies and tool activity stream as typed events.
  Stopping or failing a turn restores the last completed ADK session, avoiding
  dangling function calls on the next turn. This rollback is for these read-only
  tools; it cannot undo external side effects in tools you add yourself.
- **Persona via instructions:** the character lives in `bhalu_agent/agent.py`.

The standard ADK runners also work from this directory:

```bash
uv run adk run bhalu_agent
uv run adk web
```

The ADK CLI also loads `.env` and can override exported shell variables. Configure
the repo-root file directly when using these commands.

## Verification

From the repository root:

```bash
uv run --frozen python -m unittest discover -s tui-chat-agent/tests -p 'test_*.py' -v
cd tui-chat-agent
bun run typecheck
bun test
```

Tests cover native OpenTUI rendering, keyboard controls, narrow layouts, paste,
scrolling, stream state, the real Python subprocess, Exa errors, and ADK history
after cancelling a tool call. A Gemini stream regression verifies that tool
calls followed by empty terminal chunks still produce an answer and preserve
thought signatures. Privacy checks cover names in streamed replies,
Markdown, tool arguments, and search results. All automated tests are offline;
live model quality and API credentials require a manual check. GitHub Actions
runs the suite on Python 3.10 and 3.13.

Regenerate the renderer-captured previews with `bun run preview` and
`bun run preview 60 24`. [Compact preview](docs/preview-60.svg).
