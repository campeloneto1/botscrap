import logging
import httpx
from typing import Optional, Any

from app.config import get_settings

logger = logging.getLogger(__name__)
env_settings = get_settings()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def generate_summary(text: str, app_settings: Any = None, max_length: int = 200) -> Optional[str]:
    """
    Generate a summary of the given text using Groq API (free tier).

    Args:
        text: The text to summarize
        app_settings: AppSettings from database (optional, falls back to .env)
        max_length: Maximum length of the summary

    Returns:
        Summary string or None if failed/disabled
    """
    # Get settings from app_settings or fallback to .env
    if app_settings:
        enable_summary = app_settings.enable_ai_summary
        api_key = app_settings.groq_api_key or env_settings.groq_api_key
    else:
        enable_summary = env_settings.enable_ai_summary
        api_key = env_settings.groq_api_key

    if not enable_summary:
        return None

    if not api_key:
        logger.warning("GROQ_API_KEY not configured, skipping summary")
        return None

    if not text or len(text) < 100:
        # Text too short, no need to summarize
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",  # Fast and free
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Você é um assistente que resume textos de posts de redes sociais. "
                                "Faça um resumo conciso e objetivo em português, "
                                f"com no máximo {max_length} caracteres. "
                                "Mantenha as informações mais importantes. "
                                "Responda APENAS com o resumo, sem introduções ou explicações."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Resuma este post:\n\n{text[:2000]}"  # Limit input
                        }
                    ],
                    "max_tokens": 150,
                    "temperature": 0.3,
                }
            )

            if response.status_code == 200:
                data = response.json()
                summary = data["choices"][0]["message"]["content"].strip()
                # Ensure summary respects max_length
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                return summary
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return None
