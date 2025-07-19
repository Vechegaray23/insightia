import os
import httpx


def save_transcript(call_id: str, ts_start: float, ts_end: float, text: str) -> None:
    """Save transcription data to Supabase if credentials exist."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return
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
    httpx.post(f"{url}/rest/v1/transcripts", headers=headers, json=data)
