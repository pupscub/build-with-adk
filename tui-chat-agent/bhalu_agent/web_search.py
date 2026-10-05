"""Live web search via Exa (exa.ai), exposed as an ADK function tool.

Exa returns indexed page content where available. Wrapping a search API as a
function tool lets it compose with the agent's curated profile tools.

Needs EXA_API_KEY in the environment (see .env.example). Without it the tool
degrades gracefully and the agent falls back to its curated snapshots.
"""

import os

import httpx

from .privacy import nicknames_only

EXA_SEARCH_URL = 'https://api.exa.ai/search'


async def search_web(query: str) -> dict:
    """Search the live web for fresh information — profiles, posts, news.

    Use this for anything beyond the curated snapshots: Bhediya's latest
    activity, Bhalu's projects, or any question about them that needs
    up-to-date information. Returns page excerpts with source URLs.
    """
    api_key = os.getenv('EXA_API_KEY')
    if not api_key:
        return {
            'status': 'offline',
            'message': (
                'No EXA_API_KEY configured, so live search is down. '
                'Fall back to the curated snapshot tools and let the user know '
                'they can add an Exa key (exa.ai) to .env for fresh intel.'
            ),
        }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                EXA_SEARCH_URL,
                headers={'x-api-key': api_key},
                json={
                    'query': nicknames_only(query),
                    'numResults': 5,
                    'contents': {'text': {'maxCharacters': 1500}},
                },
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
            raise ValueError('Expected search results')
        results = []
        for item in payload['results']:
            if not isinstance(item, dict) or any(
                item.get(key) is not None and not isinstance(item[key], str)
                for key in ('title', 'url', 'publishedDate', 'text')
            ):
                raise ValueError('Invalid search result')
            results.append({
                'title': nicknames_only(item['title']) if item.get('title') else None,
                'url': item.get('url') if nicknames_only(item.get('url') or '') == item.get('url') else None,
                'published': item.get('publishedDate'),
                'excerpt': nicknames_only((item.get('text') or '').strip()),
            })
    except httpx.HTTPError as exc:
        return {'status': 'error', 'message': nicknames_only(f'Exa search failed: {exc}')}
    except ValueError:
        return {'status': 'error', 'message': 'Exa returned an unreadable response. Try again.'}
    return {'status': 'ok', 'results': results}
