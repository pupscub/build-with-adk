"""Curated intel about Aditya, served as ADK function tools.

LinkedIn and X both block anonymous scraping (LinkedIn answers with HTTP 999,
X with a login wall), so instead of fetching live these tools return a curated
snapshot of his public profiles. The source URLs are included so the agent can
always point people at the real thing.
"""

LINKEDIN_URL = 'https://www.linkedin.com/in/aditya2312/'
X_URL = 'https://x.com/pupscub'
GITHUB_URL = 'https://github.com/pupscub'


def get_aditya_profile() -> dict:
    """Get Aditya's professional profile: who he is, what he does, and where to find him.

    Use this whenever the user asks anything factual about Aditya — his work,
    his startup, his background, or his links.
    """
    return {
        'name': 'Aditya Singh',
        'also_answers_to': 'Bhalu (usage rights restricted to exactly one person)',
        'location': 'San Francisco',
        'role': 'Co-founder & CTO @ TAIM Inc',
        'what_he_is_building': (
            'Taim (trytaim.com) — a personal memory layer. You dump your thoughts, '
            'voice notes, and chaos into it, and it organizes your life into threads '
            'you can carry between AI systems (it even has its own MCP server).'
        ),
        'background': (
            'AI/ML engineer: RAG pipelines, LLM-detection Kaggle challenges, '
            'self-supervised transformers for audio, and an unreasonable number '
            'of side projects (43 public repos and counting).'
        ),
        'links': {
            'linkedin': LINKEDIN_URL,
            'x_twitter': X_URL,
            'github': GITHUB_URL,
        },
    }


def get_aditya_lore() -> dict:
    """Get the fun, unserious lore about Aditya — hobbies, quirks, and roastable material.

    Use this when the conversation is casual, when the user wants gossip,
    or when a joke needs ammunition.
    """
    return {
        'lore': [
            'Jumps out of planes for fun. Yes, skydiving. No, he will not stop talking about it.',
            'Maintains a whole Neovim config repo. He does not simply *use* an editor, he curates it.',
            'On a self-assigned mission to rank every Chinese, Italian, and Indian restaurant in San Francisco.',
            'Voice-notes his entire life into his own app. Peak founder behavior: being your own power user.',
            "His GitHub handle is 'pupscub'. Pup. Cub. The bear nickname was honestly inevitable.",
            'Ships everything with uv and has strong opinions about Python tooling.',
        ],
        'disclaimer': (
            'This is a snapshot, not a live feed — for the freshest chaos, '
            f'check his tweets at {X_URL} or just ask the real Aditya.'
        ),
    }
