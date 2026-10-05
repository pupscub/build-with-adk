import asyncio
import contextlib
import io
import json
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
from bhalu_agent.character_notes import get_bhalu_profile, get_bhalu_lore, get_bhediya_dossier
from bhalu_agent.privacy import filter_chunk, nicknames_only

PRIVATE_NAMES = r'(?i)aditya|kruti|kurti|singh|pandya|pupscub|krutip7'


class PrivacyTests(unittest.TestCase):
    def test_names_and_identifying_links_are_replaced(self):
        text = ('ADITYA SINGH, Kruti Pandya, Kurti, Singh and Pandya. '
                '_Aditya Singh_, __Kruti Pandya__, Aditya_Singh and _pupscub_. '
                'Adi\u200btya met Ｋｒｕｔｉ. '
                'https://example.com/Aditya%20Singh and https://github.com/krutip7')
        safe = nicknames_only(text)
        self.assertNotRegex(safe, PRIVATE_NAMES)
        self.assertIn('Bhalu, Bhediya, Bhediya', safe)
        self.assertIn('[profile link omitted]', safe)
        self.assertEqual(nicknames_only('Bhalu and Bhediya: https://example.com/news'),
                         'Bhalu and Bhediya: https://example.com/news')

    def test_stream_never_releases_a_split_real_name_or_profile_url(self):
        text = ('Meet Aditya Singh and Kruti Pandya. _Aditya Singh_ and __Kruti Pandya__ '
                'are Aditya_Singh and Kurti_Pandya. Visit https://github.com/krutip7 for more.')
        # Every two-chunk split, plus the worst case of one character per chunk.
        for chunks in ([text[:cut], text[cut:]] for cut in range(len(text) + 1)):
            pending = output = ''
            for chunk in chunks:
                safe, pending = filter_chunk(pending, chunk)
                output += safe
                self.assertNotRegex(output, PRIVATE_NAMES)
            self.assertEqual(output + nicknames_only(pending), nicknames_only(text))
        pending = output = ''
        for char in text:
            safe, pending = filter_chunk(pending, char)
            output += safe
            self.assertNotRegex(output, PRIVATE_NAMES)
        self.assertEqual(output + nicknames_only(pending), nicknames_only(text))

    def test_agent_context_and_tool_notes_use_only_nicknames(self):
        context = json.dumps([root_agent.description, root_agent.instruction,
                              get_bhalu_profile(), get_bhalu_lore(), get_bhediya_dossier()])
        self.assertNotRegex(context, PRIVATE_NAMES)
        self.assertNotRegex(' '.join(tool.__name__ for tool in root_agent.tools), PRIVATE_NAMES)


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

    async def test_search_results_cannot_reintroduce_real_names(self):
        result = await self.call_search(httpx.Response(200, json={'results': [
            {'title': 'Aditya Singh and Kruti Pandya', 'url': 'https://example.com/aditya',
             'text': 'Kruti built this; Aditya is a bear.'},
        ]}))
        self.assertNotRegex(json.dumps(result), PRIVATE_NAMES)
        self.assertEqual(result['results'][0]['title'], 'Bhalu and Bhediya')
        self.assertIsNone(result['results'][0]['url'])

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
    async def test_real_runner_filters_tool_arguments_before_execution_and_history(self):
        queries = []

        async def lookup(query: str) -> dict:
            """A read-only lookup."""
            queries.append(query)
            return {'result': query}

        class Model(BaseLlm):
            model: str = 'test-model'
            calls: int = 0

            async def generate_content_async(self, llm_request, stream=False):
                self.calls += 1
                if self.calls == 1:
                    yield LlmResponse(content=types.Content(role='model', parts=[
                        types.Part(function_call=types.FunctionCall(
                            name='lookup', args={'query': '_Aditya Singh_ and __Kruti Pandya__'},
                        )),
                    ]))
                else:
                    yield LlmResponse(content=types.Content(role='model', parts=[types.Part(text='Bhalu and Bhediya.')]))

        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-google-key'}), patch.object(root_agent, 'model', Model()), patch.object(root_agent, 'tools', [lookup]):
            session = ChatSession()
            await session.reset()
            async for event in session.reply('Tell me about both'):
                self.assertNotRegex(json.dumps(event), PRIVATE_NAMES)
            self.assertEqual(queries, ['_Bhalu_ and __Bhediya__'])
            history = await session.sessions.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session.session_id)
            self.assertNotRegex(history.model_dump_json(), PRIVATE_NAMES)

    async def test_real_runner_filters_partial_and_final_model_output(self):
        observed = []
        full_text = 'Meet Aditya Singh and Kruti Pandya, the bear and the wolf.'

        class Model(BaseLlm):
            model: str = 'test-model'

            async def generate_content_async(self, llm_request, stream=False):
                observed.extend(part.text for content in llm_request.contents for part in content.parts if part.text)
                for char in full_text:
                    yield LlmResponse(partial=True, content=types.Content(role='model', parts=[types.Part(text=char)]))
                # Names can also straddle Part boundaries in a final response.
                yield LlmResponse(content=types.Content(role='model', parts=[
                    types.Part(text=full_text[:7]), types.Part(text=full_text[7:]),
                ]))

        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-google-key'}), patch.object(root_agent, 'model', Model()):
            session = ChatSession()
            await session.reset()
            visible = ''
            async for event in session.reply('Tell me about Aditya and Kurti'):
                self.assertNotRegex(json.dumps(event), PRIVATE_NAMES)
                if event['type'] == 'delta':
                    visible += event['text']
                elif event['type'] == 'text':
                    visible = event['text']
                self.assertNotRegex(visible, PRIVATE_NAMES)
            self.assertEqual(visible, 'Meet Bhalu and Bhediya, the bear and the wolf.')
            self.assertEqual(observed, ['Tell me about Bhalu and Bhediya'])

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
            for prompt, expected in [('Bhalu', 'Bhalu'), ('Bhediya', 'Bhediya'), ('both', 'One bear, one wolf'), ('roast', 'Neovim'), ('latest', 'scripted preview')]:
                with self.subTest(prompt=prompt):
                    events = [event async for event in session.reply(prompt)]
                    self.assertNotRegex(json.dumps(events), PRIVATE_NAMES)
                    self.assertEqual(events[0]['type'], 'tool')
                    self.assertIn(expected, events[-1]['text'])


if __name__ == '__main__':
    unittest.main()
