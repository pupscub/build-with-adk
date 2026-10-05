import asyncio
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import httpx
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge import APP_NAME, USER_ID, ChatSession
from bhalu_agent.agent import root_agent
from bhalu_agent import web_search


class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def call_search(self, response=None, error=None):
        async def handler(request):
            self.assertEqual(request.headers['x-api-key'], 'test-exa-key')
            if error:
                raise error
            return response
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {'EXA_API_KEY': 'test-exa-key'}), patch.object(web_search.httpx, 'AsyncClient', return_value=client):
            return await web_search.search_web('Bhalu')

    async def test_offline_needs_no_network(self):
        with patch.dict(os.environ, {'EXA_API_KEY': ''}), patch.object(httpx, 'AsyncClient') as client:
            result = await web_search.search_web('Bhalu')
            self.assertEqual(result['status'], 'offline')
            client.assert_not_called()

    async def test_search_preserves_sources_and_handles_empty_results(self):
        result = await self.call_search(httpx.Response(200, json={'results': [
            {'title': 'Profile', 'url': 'https://example.com/profile', 'text': '  Excerpt  '},
            {'url': 'https://example.com/other', 'text': None},
        ]}))
        self.assertEqual(result['results'][0]['excerpt'], 'Excerpt')
        self.assertEqual(result['results'][0]['url'], 'https://example.com/profile')
        self.assertEqual(result['results'][1]['excerpt'], '')
        self.assertEqual(await self.call_search(httpx.Response(200, json={'results': []})), {'status': 'ok', 'results': []})

    async def test_http_and_timeout_errors_are_tool_results(self):
        for code in (401, 429, 503):
            with self.subTest(code=code):
                result = await self.call_search(httpx.Response(code))
                self.assertEqual(result['status'], 'error')
        result = await self.call_search(error=httpx.ReadTimeout('Timed out'))
        self.assertEqual(result['status'], 'error')

    async def test_malformed_payloads_do_not_crash_the_agent(self):
        for payload in (None, [], {}, {'results': None}, {'results': [None]}, {'results': [{'text': 42}]}):
            with self.subTest(payload=payload):
                result = await self.call_search(httpx.Response(200, json=payload))
                self.assertEqual(result['status'], 'error')
        result = await self.call_search(httpx.Response(200, text='<html>upstream error</html>'))
        self.assertEqual(result['status'], 'error')


class AgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_google_key_has_actionable_error(self):
        session = ChatSession()
        with patch.dict(os.environ, {'GOOGLE_API_KEY': ''}):
            with self.assertRaisesRegex(ValueError, 'GOOGLE_API_KEY'):
                await anext(session.reply('hello'))

    async def test_real_runner_cancellation_preserves_completed_history(self):
        entered = asyncio.Event()
        observed = []

        async def slow_tool() -> dict:
            """A read-only slow lookup."""
            entered.set()
            await asyncio.sleep(100)
            return {'result': 'finished'}

        class Model(BaseLlm):
            model: str = 'test-model'
            calls: int = 0

            async def generate_content_async(self, llm_request, stream=False):
                self.calls += 1
                if self.calls == 2:
                    yield LlmResponse(content=types.Content(role='model', parts=[
                        types.Part(function_call=types.FunctionCall(name='slow_tool', args={})),
                    ]))
                else:
                    observed.append(llm_request.contents)
                    yield LlmResponse(content=types.Content(role='model', parts=[types.Part(text='Hello from Bhalu')]))

        async def consume(session, text):
            return [event async for event in session.reply(text)]

        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-google-key'}), patch.object(root_agent, 'model', Model()), patch.object(root_agent, 'tools', [slow_tool]), contextlib.redirect_stdout(io.StringIO()):
            session = ChatSession()
            await session.reset()
            await consume(session, 'first completed turn')
            task = asyncio.create_task(consume(session, 'interrupt this lookup'))
            await asyncio.wait_for(entered.wait(), 3)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            result = await consume(session, 'hello after stop')
            self.assertEqual(result[-1], {'type': 'text', 'text': 'Hello from Bhalu'})
            history = observed[-1]
            self.assertEqual([part.text for content in history for part in content.parts if part.text],
                             ['first completed turn', 'Hello from Bhalu', 'hello after stop'])
            self.assertFalse(any(part.function_call for content in history for part in content.parts))

    async def test_demo_routes_both_characters_and_labels_search_as_scripted(self):
        session = ChatSession(demo=True)
        async def no_delay(_):
            return
        with patch('bridge.asyncio.sleep', no_delay):
            for prompt, expected in [('Bhalu', 'Aditya Singh'), ('Bhediya', 'Kruti Pandya'), ('both', 'One bear, one wolf'), ('roast', 'Neovim'), ('latest', 'scripted preview')]:
                with self.subTest(prompt=prompt):
                    events = [event async for event in session.reply(prompt)]
                    self.assertEqual(events[0]['type'], 'tool')
                    self.assertIn(expected, events[-1]['text'])


if __name__ == '__main__':
    unittest.main()
