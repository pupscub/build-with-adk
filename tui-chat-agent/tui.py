"""Bhalu Chat — a tiny Textual TUI for chatting with the bhalu_agent.

Run from this directory:

    uv run tui.py

Requires GOOGLE_API_KEY in the repo-root .env (see .env.example).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from bhalu_agent.agent import root_agent

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

APP_NAME = 'bhalu_chat'
USER_ID = 'her'


class ChatBubble(Static):
    pass


class BhaluChat(App):
    TITLE = '🐻 Bhalu'
    SUB_TITLE = 'professional simp · powered by google-adk'
    BINDINGS = [('ctrl+c', 'quit', 'Quit')]

    CSS = """
    #chat {
        padding: 1 2;
    }
    ChatBubble {
        margin-bottom: 1;
        padding: 0 1;
        max-width: 80%;
        width: auto;
    }
    .you {
        border: round $accent;
        margin-left: 20;
    }
    .bhalu {
        border: round #d2691e;
    }
    #prompt {
        dock: bottom;
        margin: 0 1 1 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._sessions = InMemorySessionService()
        self._runner = Runner(
            agent=root_agent, app_name=APP_NAME, session_service=self._sessions
        )
        self._session_id = ''

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id='chat')
        yield Input(placeholder='Say something to Bhalu…', id='prompt')
        yield Footer()

    async def on_mount(self) -> None:
        session = await self._sessions.create_session(
            app_name=APP_NAME, user_id=USER_ID
        )
        self._session_id = session.id
        if not os.getenv('GOOGLE_API_KEY'):
            self._say(
                'bhalu',
                'No GOOGLE_API_KEY found — copy .env.example to .env in the repo '
                'root and add your key. Even a lovesick bear needs credentials.',
            )
        else:
            self._say(
                'bhalu',
                'Arre, look who showed up. 🐻 Ask me anything about Aditya — '
                'I know that man embarrassingly well.',
            )
        self.query_one(Input).focus()

    def _say(self, who: str, text: str) -> ChatBubble:
        bubble = ChatBubble(escape(text), classes=who)
        chat = self.query_one('#chat', VerticalScroll)
        chat.mount(bubble)
        bubble.scroll_visible()
        return bubble

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ''
        self._say('you', text)
        self.run_worker(self._ask_bhalu(text), exclusive=True)

    async def _ask_bhalu(self, text: str) -> None:
        bubble = self._say('bhalu', '…')
        try:
            reply = await self._run_agent(text)
        except Exception as exc:  # surface API/config errors in the chat itself
            reply = f'Bhalu short-circuited: {exc}'
        bubble.update(escape(reply))
        bubble.scroll_visible()

    async def _run_agent(self, text: str) -> str:
        message = types.Content(role='user', parts=[types.Part(text=text)])
        reply = ''
        async for event in self._runner.run_async(
            user_id=USER_ID, session_id=self._session_id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                reply = ''.join(part.text or '' for part in event.content.parts)
        return reply or '…Bhalu is speechless. Cherish this rare moment.'


if __name__ == '__main__':
    BhaluChat().run()
