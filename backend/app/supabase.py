"""Helper for storing transcripts in Supabase."""

import os
import httpx


async def save_transcript(
    call_id: str, ts_start: float, ts_end: float, text: str
) -> None:
    """Save transcription data to Supabase if credentials exist."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Supabase credentials not set. Skipping save_transcript.")
        return  # Si las variables no están, la función sale sin error

    # Cabeceras de autenticación para la API REST de Supabase
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
        # Realizamos la petición de forma asíncrona
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{url}/rest/v1/transcripts", headers=headers, json=data, timeout=10
            )

        resp.raise_for_status()
        print(f"Transcript saved to Supabase for call {call_id}: {text[:50]}...")
    except httpx.RequestError as e:
        print(f"Supabase connection error for call {call_id}: {e}")
    except httpx.HTTPStatusError as e:
        print(
            f"Supabase API error {e.response.status_code} for call {call_id}: {e.response.text}"
        )
    except Exception as e:
        print(
            f"An unexpected error occurred while saving to Supabase for call {call_id}: {e}"
        )
