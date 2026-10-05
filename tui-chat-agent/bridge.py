"""JSON-lines bridge between OpenTUI and ADK. Stdout is protocol only."""

import asyncio
import contextlib
import copy
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

from bhalu_agent.privacy import nicknames_only

APP_NAME = 'bhalu_agent'
USER_ID = 'visitor'
PROTOCOL_OUTPUT = sys.stdout


def emit(event: dict) -> None:
    event = {key: nicknames_only(value) if key in ('text', 'message') and isinstance(value, str) else value
             for key, value in event.items()}
    print(json.dumps(event, ensure_ascii=False), file=PROTOCOL_OUTPUT, flush=True)


class ChatSession:
    def __init__(self, demo: bool = False):
        self.demo = demo
        self.session_id = None
        self.runner = None
        self.sessions = None

    async def reset(self):
        if self.demo:
            return
        # Keep SDK logs/prints away from the JSON protocol.
        with contextlib.redirect_stdout(sys.stderr):
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from bhalu_agent.agent import root_agent

            self.sessions = InMemorySessionService()
            self.runner = Runner(
                agent=root_agent, app_name=APP_NAME, session_service=self.sessions
            )
            session = await self.sessions.create_session(app_name=APP_NAME, user_id=USER_ID)
            self.session_id = session.id

    async def reply(self, text: str):
        if self.demo:
            async for event in self.demo_reply(text):
                yield event
            return
        if not os.getenv('GOOGLE_API_KEY'):
            raise ValueError('Add GOOGLE_API_KEY to the repo-root .env, then restart. Or try bun run demo.')
        # ADK persists tool calls before executing them. An interrupted turn must
        # not leave an unanswered tool call in the next Gemini request. These
        # tools are read-only; preserve all history/state from completed turns.
        checkpoint = copy.deepcopy(self.sessions)
        try:
            async with contextlib.aclosing(self.live_reply(text)) as stream:
                async for event in stream:
                    yield event
        except (Exception, asyncio.CancelledError):
            self.sessions = checkpoint
            self.runner.session_service = checkpoint
            raise

    async def live_reply(self, text: str):
        from google.adk.agents.run_config import RunConfig, StreamingMode
        from google.genai import types

        stream = self.runner.run_async(
            user_id=USER_ID,
            session_id=self.session_id,
            new_message=types.Content(role='user', parts=[types.Part(text=nicknames_only(text))]),
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
        # Redirect only while advancing ADK, never across a yielded protocol event.
        streamed = False
        async with contextlib.aclosing(stream):
            while True:
                try:
                    with contextlib.redirect_stdout(sys.stderr):
                        event = await anext(stream)
                except StopAsyncIteration:
                    break
                if event.error_code:
                    raise RuntimeError(event.error_message or event.error_code)
                for call in event.get_function_calls():
                    yield {'type': 'tool', 'name': call.name}
                parts = event.content.parts if event.content and event.content.parts else []
                response = ''.join(part.text or '' for part in parts if not part.thought)
                if response and event.partial:
                    streamed = True
                    yield {'type': 'delta', 'text': response}
                elif response and event.is_final_response():
                    streamed = True
                    yield {'type': 'text', 'text': response}
        if not streamed:
            yield {'type': 'text', 'text': 'The bear lost his words. Try asking that again.'}

    async def demo_reply(self, text: str):
        query = text.lower()
        if 'roast' in query:
            tool = 'get_bhalu_lore'
            answer = 'Bhalu maintains an entire Neovim config repo. The man does not open an editor; he enters a committed relationship with it. And then voice-notes the experience into his own app. Peak founder behavior, yaar.'
        elif any(word in query for word in ('both', 'story', 'together', 'bear and')):
            tool = 'get_bhediya_dossier'
            answer = 'One bear, one wolf. She named the bear; he named the wolf. She builds agents, so naturally the bear moved into her codebase. That is the lore I have. Anything more cinematic, you will have to ask the real two.'
        elif any(word in query for word in ('bhediya', 'wolf')):
            tool = 'get_bhediya_dossier'
            answer = 'Meet Bhediya, the wolf in this little universe. She is building agents with Google ADK, and this very repository is hers. The bear is merely a guest with very strong opinions.'
        elif any(word in query for word in ('latest', 'search', 'fresh')):
            tool = 'search_web'
            answer = 'This is a scripted preview, so my forest Wi-Fi is imaginary. Start live mode with your Google key and optional Exa key to search for fresh information. No invented headlines from this bear.'
        else:
            tool = 'get_bhalu_profile'
            answer = 'Bhalu is a bear, a builder, and the co-founder and CTO of Taim. He is building a personal memory layer for thoughts, voice notes, and everyday chaos. Apparently organizing his own chaos was not enough; now it is a startup.'
        yield {'type': 'tool', 'name': tool}
        for word in answer.split(' '):
            await asyncio.sleep(0.025)
            yield {'type': 'delta', 'text': word + ' '}
        yield {'type': 'text', 'text': answer}


async def serve(demo=False):
    session = ChatSession(demo)
    await session.reset()
    emit({'type': 'ready', 'configured': demo or bool(os.getenv('GOOGLE_API_KEY')),
          'search': bool(os.getenv('EXA_API_KEY')) and not demo, 'demo': demo})
    active = None

    async def answer(request):
        try:
            async for event in session.reply(request['text']):
                emit({**event, 'id': request['id']})
            emit({'type': 'done', 'id': request['id']})
        except asyncio.CancelledError:
            emit({'type': 'cancelled', 'id': request['id']})
            raise
        except Exception as exc:
            emit({'type': 'error', 'id': request['id'], 'message': str(exc)})

    async def cancel():
        if active and not active.done():
            active.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await active

    try:
        while line := await asyncio.to_thread(sys.stdin.readline):
            request = {}
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError('Expected a request object')
                if request.get('type') == 'cancel':
                    await cancel()
                elif request.get('type') == 'reset':
                    await cancel()
                    await session.reset()
                    emit({'type': 'reset'})
                elif request.get('type') == 'chat':
                    if not isinstance(request.get('text'), str) or not request['text'].strip():
                        raise ValueError('A message cannot be empty')
                    if not isinstance(request.get('id'), str):
                        raise ValueError('A message needs an id')
                    if active and not active.done():
                        raise ValueError('Wait for the current reply to finish')
                    active = asyncio.create_task(answer(request))
                else:
                    raise ValueError('Unknown request type')
            except (ValueError, TypeError) as exc:
                emit({'type': 'error', 'id': request.get('id') if isinstance(request, dict) else None,
                      'message': str(exc)})
    finally:
        await cancel()


if __name__ == '__main__':
    try:
        asyncio.run(serve('--demo' in sys.argv))
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        emit({'type': 'fatal', 'message': str(exc)})
        sys.exit(1)
