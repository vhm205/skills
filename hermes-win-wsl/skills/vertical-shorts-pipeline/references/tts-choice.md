# TTS Choice: Kokoro ONNX

## Why Kokoro

The pipeline uses **Kokoro TTS** via `kokoro-onnx` for local, zero-cost voiceover generation.

### What was considered

| Option | Cost | Quality | Latency | Setup |
|--------|------|---------|---------|-------|
| **Kokoro ONNX** ✅ | Free | Very good (82M params) | ~1x real-time | `pip install` + 310MB model |
| Bark (suno-ai) | Free | Good | ~10x real-time | Needs GPU for practical use |
| Coqui XTTS v2 | Free | Very good (cloning) | ~5x real-time | Needs GPU + 10-30 min voice sample |
| Edge TTS | Free | Decent | Fast | API calls to Microsoft |
| ElevenLabs API | ~$5-22/mo | Excellent (cloning) | Fast | Paid API key |
| OpenAI TTS | ~$15/1M chars | Very good | Fast | Paid API key |

### Decision: Kokoro ONNX

- **No per-request cost** — runs entirely on your CPU
- **No API key** — model is cached locally
- **Apache 2.0 license** — no usage restrictions
- **82M parameters** — lightweight enough for real-time CPU inference
- **20+ voices** — male and female, American and British accents
- **~310 MB download** — one-time; model cached at `%LOCALAPPDATA%\hermes\models\kokoro\`

### Voice cloning

Voice cloning (your second option) requires:
1. A clean voice sample (10–30 minutes of speech)
2. Significantly more GPU memory (6–12 GB VRAM typical)
3. Fine-tuning or adapter training

This is not included in v1 of the pipeline. If you record voice samples,
we can add a cloning step using:
- **Coqui XTTS v2** (open source, best quality)
- **OpenVoice** (lightweight, instant cloning)
- **RVC** (popular for real-time voice conversion)

The pipeline is designed so the TTS step can be swapped — just replace
the `generate_voiceover()` function.

## Available Kokoro voices

### American English (af_*, am_*)
- `af_heart` — warm female (default)
- `af_bella` — bright female
- `af_nicole` — clear female
- `af_sarah` — soft female
- `af_sky` — energetic female
- `am_adam` — deep male
- `am_michael` — neutral male
- `am_eric` — resonant male

### British English (bf_*, bm_*)
- `bf_emma` — polished female
- `bf_isabella` — warm female
- `bf_alice` — clear female
- `bf_lily` — bright female
- `bm_george` — authoritative male
- `bm_lewis` — friendly male
- `bm_daniel` — neutral male
- `bm_oliver` — warm male