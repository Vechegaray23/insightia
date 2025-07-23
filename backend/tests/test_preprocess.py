import math
import struct
import io
import wave
import audioop

from backend.app.stt import mulaw_to_wav, preprocess_wav, INPUT_SAMPLE_RATE


def _duration(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def test_preprocess_modifies_audio_preserves_duration():
    # generate 1 second sine wave as mu-law
    sr = INPUT_SAMPLE_RATE
    pcm = b"".join(
        struct.pack("<h", int(10000 * math.sin(2 * math.pi * 440 * i / sr)))
        for i in range(sr)
    )
    mu = audioop.lin2ulaw(pcm, 2)
    wav = mulaw_to_wav(mu)
    before = _duration(wav)

    processed = preprocess_wav(wav)
    after = _duration(processed)

    assert before == after
    assert wav != processed