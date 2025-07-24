# backend/app/supabase.py

import os
import httpx
import logging

logger = logging.getLogger(__name__)


async def save_transcript(
    call_id: str, ts_start: float, ts_end: float, text: str
) -> None:
    """Save transcription data to Supabase if credentials exist."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        logging.info("Supabase credentials not set. Skipping save_transcript.")
        return  # Si las variables no están, la función sale sin error

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    data = {
        "call_id": call_id,
        "ts_start": ts_start,
        "ts_end": ts_end,
        "text": text,
    }

    try:
        # Modificación: Hacer la llamada HTTP asíncrona
        async with httpx.AsyncClient() as client:  # Usar AsyncClient
            resp = await client.post(
                f"{url}/rest/v1/transcripts", headers=headers, json=data, timeout=10
            )  # Añadir timeout

        resp.raise_for_status()  # Lanza un HTTPStatusError para códigos de error 4xx/5xx
        logger.info(
            "Transcript saved to Supabase for call %s: %s...",
            call_id,
            text[:50],
        )
    except httpx.RequestError as e:
        logger.exception("Supabase connection error for call %s: %s", call_id, e)
    except httpx.HTTPStatusError as e:
        logger.exception(
            "Supabase API error %s for call %s: %s",
            e.response.status_code,
            call_id,
            e.response.text,
        )
    except Exception as e:
        logger.exception(
            "An unexpected error occurred while saving to Supabase for call %s: %s",
            call_id,
            e,
        )
