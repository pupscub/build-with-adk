"""Keep known real identities out of model output, including streamed chunks.

The names below are a denylist, never agent context or character facts.
"""

import re
import unicodedata
from contextvars import ContextVar
from urllib.parse import unquote

from google.genai import types

_NAMES = (
    (re.compile(r'(?<![^\W_])(?:Aditya(?:[\s_]+Singh)?|Singh)(?![^\W_])', re.I), 'Bhalu'),
    (re.compile(r'(?<![^\W_])(?:(?:Kruti|Kurti)(?:[\s_]+Pandya)?|Pandya)(?![^\W_])', re.I), 'Bhediya'),
)
_HANDLES = re.compile(r'(?<![^\W_])(?:pupscub|aditya2312|krutip7)(?![^\W_])', re.I)
_URL = re.compile(r'https?://[^\s<>]+', re.I)
# Coroutine-local buffering avoids putting withheld text in ADK event/state
# payloads. The invocation id also resets the tail after a cancelled turn.
_PENDING = ContextVar('nickname_output_buffer', default=('', ''))


def nicknames_only(text: str) -> str:
    """Replace known real names and omit links/handles that expose identities."""
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Cf')

    def safe_url(match):
        decoded = unquote(match.group()).casefold()
        if any(name in decoded for name in ('aditya', 'kruti', 'kurti', 'singh', 'pandya', 'pupscub')):
            return '[profile link omitted]'
        return match.group()

    text = _URL.sub(safe_url, text)
    text = _HANDLES.sub('[private handle]', text)
    for pattern, nickname in _NAMES:
        text = pattern.sub(nickname, text)
    return text


def filter_chunk(buffer: str, chunk: str) -> tuple[str, str]:
    """Release complete words, retaining a tail so split names/URLs never flash."""
    buffer += chunk
    boundaries = list(re.finditer(r'\s+', buffer))
    if len(boundaries) < 2:
        return '', buffer
    cut = boundaries[-2].end()
    # Keep a full name or URL together if it straddles the release boundary.
    for pattern in (*[pattern for pattern, _ in _NAMES], _URL):
        for match in pattern.finditer(buffer):
            if match.start() < cut < match.end():
                cut = match.start()
    return nicknames_only(buffer[:cut]), buffer[cut:]


def _safe_arguments(value):
    """Filter generated tool arguments before ADK emits or persists them."""
    if isinstance(value, str):
        return nicknames_only(value)
    if isinstance(value, dict):
        return {key: _safe_arguments(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_arguments(item) for item in value]
    return value


def protect_model_response(callback_context, llm_response):
    """ADK callback shared by OpenTUI, adk run, and adk web."""
    response = llm_response.model_copy(deep=True)
    invocation, pending = _PENDING.get()
    if invocation != callback_context.invocation_id:
        pending = ''
    parts = response.content.parts if response.content and response.content.parts else []
    public_parts = [part for part in parts if part.text and not part.thought]
    for part in parts:
        if part.text and part.thought:
            part.text = ''
        if part.function_call and part.function_call.args:
            part.function_call.args = _safe_arguments(part.function_call.args)
    if response.partial:
        safe, pending = filter_chunk(
            pending,
            ''.join(part.text for part in public_parts),
        )
        _PENDING.set((callback_context.invocation_id, pending))
        for index, part in enumerate(public_parts):
            part.text = safe if index == 0 else ''
    else:
        _PENDING.set((callback_context.invocation_id, ''))
        safe = nicknames_only(''.join(part.text for part in public_parts))
        for index, part in enumerate(public_parts):
            part.text = safe if index == 0 else ''
        if pending and not public_parts:
            if response.content is None:
                response.content = types.Content(role='model', parts=[])
            response.content.parts = [*(response.content.parts or []), types.Part(text=nicknames_only(pending))]
    if response.error_message:
        response.error_message = nicknames_only(response.error_message)
    return response
