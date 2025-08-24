import os
import logging
import backoff
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

log = logging.getLogger(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@backoff.on_exception(backoff.expo, (APIError, RateLimitError, APITimeoutError), max_tries=5, jitter=backoff.full_jitter)
def chat(messages: list[dict], model: str = "gpt-4o-mini", **kwargs) -> str:
    log.debug("Calling OpenAI model=%s", model)
    resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
    return resp.choices[0].message.content
