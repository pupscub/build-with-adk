"""Curated, nickname-only character notes served as ADK function tools."""


def get_bhalu_profile() -> dict:
    """Get Bhalu's professional profile: who he is and what he does.

    Use this whenever the user asks anything factual about Bhalu — his work,
    his startup, or his background. Use only his nickname.
    """
    return {
        'name': 'Bhalu',
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
    }


def get_bhalu_lore() -> dict:
    """Get the fun, unserious lore about Bhalu — hobbies, quirks, and roastable material.

    Use this when the conversation is casual, when the user wants gossip,
    or when a joke needs ammunition.
    """
    return {
        'lore': [
            'Jumps out of planes for fun. Yes, skydiving. No, he will not stop talking about it.',
            'Maintains a whole Neovim config repo. He does not simply *use* an editor, he curates it.',
            'On a self-assigned mission to rank every Chinese, Italian, and Indian restaurant in San Francisco.',
            'Voice-notes his entire life into his own app. Peak founder behavior: being your own power user.',
            'Ships everything with uv and has strong opinions about Python tooling.',
        ],
        'disclaimer': (
            'This is a snapshot, not a live feed — for the freshest chaos, '
            'ask Bhalu himself.'
        ),
    }


def get_bhediya_dossier() -> dict:
    """Get Bhalu's dossier on Bhediya — the one person this whole agent exists for.

    Use this when the user asks who she is, what Bhalu knows about her, or why
    he calls her Bhediya.
    """
    return {
        'name': 'Bhediya',
        'codename': 'Bhediya 🐺 (his one and only wolf — she named the bear, he named the wolf)',
        'currently': (
            'Building agents with Google ADK — this very repo is hers. '
            'Bhalu lives inside her own codebase now. She has no one to blame but herself.'
        ),
        'bhalu_editorial': (
            'Objectively out of his league. He knows it. She knows it. '
            'The bear persists anyway.'
        ),
    }
