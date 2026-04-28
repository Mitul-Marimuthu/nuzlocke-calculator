"""Shared Groq client + retry-aware chat completion helper."""

import os
import time
from groq import Groq, RateLimitError

MODEL = "llama-3.3-70b-versatile"

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client

# chat with the Groq client, with exponential backoff on rate limits
def chat(messages: list, tools: list | None = None, max_retries: int = 4):
    """Call chat.completions.create with exponential backoff on rate limits."""
    client = get_client()
    kwargs = {"model": MODEL, "messages": messages}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    delay = 10
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise
