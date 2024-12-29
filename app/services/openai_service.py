from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt
from ..config import settings
import openai
import logging

logger = logging.getLogger(__name__)

@circuit(failure_threshold=5, recovery_timeout=60)
@retry(stop=stop_after_attempt(3))
async def generate_ai_suggestion(prompt: str) -> str:
    try:
        resp = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an SEO assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise 