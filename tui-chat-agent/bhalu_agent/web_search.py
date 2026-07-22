"""Live web search via Exa (exa.ai), exposed as an ADK function tool.

Exa serves crawled page content through an API, which neatly sidesteps the
problem that LinkedIn and X block anonymous scraping. It also demonstrates an
ADK gotcha: the built-in google_search tool cannot be combined with custom
function tools on the same agent, but a search API wrapped in a plain function
composes with anything.

Needs EXA_API_KEY in the environment (see .env.example). Without it the tool
degrades gracefully and the agent falls back to its curated snapshots.
"""

import os

import httpx

EXA_SEARCH_URL = 'https://api.exa.ai/search'


def search_web(query: str) -> dict:
    """Search the live web for fresh information — profiles, posts, news.

    Use this for anything beyond the curated snapshots: Bhediya's latest
    activity, Aditya's recent tweets, or any question about them that needs
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
        response = httpx.post(
            EXA_SEARCH_URL,
            headers={'x-api-key': api_key},
            json={
                'query': query,
                'numResults': 5,
                'contents': {'text': {'maxCharacters': 1500}},
            },
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {'status': 'error', 'message': f'Exa search failed: {exc}'}
    return {
        'status': 'ok',
        'results': [
            {
                'title': item.get('title'),
                'url': item.get('url'),
                'published': item.get('publishedDate'),
                'excerpt': (item.get('text') or '').strip(),
            }
            for item in response.json().get('results', [])
        ],
    }
