"""Voice — the listening track (Day 3, pulled forward Oct 28, 2026).

Petro's bug report, from his live sitting: he shared audio of
himself talking to Liv and a video answering one of her questions,
and Liv replied she could not listen or watch — while he was, in
his words, "expressing myself in my own words, educating Liv about
my childhood." A listener who cannot hear is a broken promise.
This module is the server half of the fix.

The shape of it: the BROWSER makes a "listening track" for every
audio and video item — a 16 kHz mono PCM WAV transcoded from the
original with Web Audio (decodeAudioData), because
muse-voice-transcribe-1.0 accepts mono PCM WAV at 16/24 kHz ONLY
and rejects the WebM/Opus every browser records by default
(WHITE-PAPER-META-INNOVATIONS.md, V-1). The server validates that
track here, hands it to the transcription model, and stores the
returned transcript on the media item as the storyteller's spoken
words.

Transcription reality (verified against the live API, Oct 28):
POST {base}/asr/transcribe, multipart/form-data with a `request`
part (JSON: model + audioEncoding "WAV") and an `audio` part.
The model follows mid-sentence language switches; it returns a
plain transcript — NO word timestamps, NO confidence, NO emotion.
Nothing here pretends otherwise.

Stdlib only.
"""
import io
import wave

# The only sample rates the model accepts (white paper V-1).
ACCEPT_RATES = (16000, 24000)
# A listening track is a copy for the model's ears, not an archive:
# 30 MB of 16 kHz mono PCM is ~16 minutes — far beyond one telling
# beat — and 15 minutes is the duration ceiling to match.
MAX_WAV_BYTES = 30 * 1024 * 1024
MAX_WAV_SECONDS = 15 * 60


def validate_listening_wav(data):
    """Check a candidate listening track.

    Returns (info, None) for a good track — info carries rate,
    channels, frames and duration — or (None, error) with a plain
    sentence for the storyteller-facing 400. Strict on purpose:
    mono, 16-bit PCM, 16 or 24 kHz, non-empty, in caps. Anything
    else would only be rejected by the model later, worse.
    """
    if not data:
        return None, "No listening copy arrived with that recording."
    if len(data) > MAX_WAV_BYTES:
        return None, ("That recording is too long to listen to "
                      "here — please share a shorter one.")
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            info = {
                "channels": wav.getnchannels(),
                "sampwidth": wav.getsampwidth(),
                "rate": wav.getframerate(),
                "frames": wav.getnframes(),
                "comptype": wav.getcomptype(),
            }
    except (wave.Error, EOFError, ValueError):
        return None, ("The listening copy of that recording could "
                      "not be read — please try again.")
    if info["comptype"] != "NONE":
        return None, ("The listening copy of that recording could "
                      "not be read — please try again.")
    if info["channels"] != 1:
        return None, ("The listening copy of that recording was "
                      "not in the form Liv can hear — please try "
                      "again.")
    if info["sampwidth"] != 2:
        return None, ("The listening copy of that recording was "
                      "not in the form Liv can hear — please try "
                      "again.")
    if info["rate"] not in ACCEPT_RATES:
        return None, ("The listening copy of that recording was "
                      "not in the form Liv can hear — please try "
                      "again.")
    if info["frames"] <= 0:
        return None, "That recording seems to hold no sound."
    info["seconds"] = info["frames"] / float(info["rate"])
    if info["seconds"] > MAX_WAV_SECONDS:
        return None, ("That recording is too long to listen to "
                      "here — please share a shorter one.")
    return info, None


def is_listening_wav(data):
    """True when these bytes already ARE a valid listening track
    (e.g. the storyteller uploaded a .wav recording directly)."""
    info, _error = validate_listening_wav(data)
    return info is not None
