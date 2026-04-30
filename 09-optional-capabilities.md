# 09 — Capacidades opcionales

El core del agente (chat, memoria, heartbeat, dream) funciona **sin gastar nada extra del MAX**. Si quieres que también hable con voz, escuche audio, genere imágenes, o entienda video, hay módulos enchufables. Cada uno requiere una API key distinta y tiene su propio costo per-use.

| Capacidad | API externa | Costo aprox | Skill |
|-----------|-------------|-------------|-------|
| Hablar (TTS) | ElevenLabs | ~$5/M chars | `elevenlabs-tts` |
| Escuchar audio (STT) | ElevenLabs Scribe | ~$0.40/h audio | `elevenlabs-tts` |
| Generar imagen | Replicate Flux | ~$0.04/img Pro | `image-gen` |
| Analizar video | ffmpeg local + ElevenLabs (STT del audio) | ~$0.40/h | `video-vision` |

Ninguna es obligatoria.

---

## TTS / STT con ElevenLabs

Misma API key (`ELEVENLABS_API_KEY`) cubre síntesis (TTS) y transcripción (STT con modelo Scribe v1).

### Setup

1. Crea cuenta en [elevenlabs.io](https://elevenlabs.io). Plan Starter $5/mes da margen para uso personal.
2. Settings → API Keys → Create Key.
3. Pega en `~/.env.global`:
   ```
   ELEVENLABS_API_KEY="sk_..."
   ```
4. Reinicia el servicio para que recoja la env var.

### Skill `elevenlabs-tts`

Estructura:

```
.claude/skills/elevenlabs-tts/
├── SKILL.md
├── generate.py     ← TTS
└── transcribe.py   ← STT
```

#### `generate.py` (TTS)

Stdlib pura, sin pip. Lee `ELEVENLABS_API_KEY` del env. Defaults canónicos: voz `Lumina` multilingual, `eleven_multilingual_v2`, español, stability 0.75, similarity 0.85.

```python
#!/usr/bin/env python3
"""ElevenLabs TTS generator. Stdlib only.
Reads ELEVENLABS_API_KEY from env. Returns mp3 path on stdout.
"""
import argparse, json, os, pathlib, sys, time, urllib.request, urllib.error

API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
DEFAULT_VOICE = "x5IDPSl4ZUbhosMmVFTk"  # Lumina multilingual
DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_OUT_DIR = "/tmp/key-tts"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--lang", default="es")
    ap.add_argument("--stability", type=float, default=0.75)
    ap.add_argument("--similarity", type=float, default=0.85)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        sys.stderr.write("ERROR: ELEVENLABS_API_KEY no está en env\n")
        return 2

    out = pathlib.Path(args.out or f"{DEFAULT_OUT_DIR}/eleven_{int(time.time())}.mp3")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "text": args.text,
        "model_id": DEFAULT_MODEL,
        "language_code": args.lang,
        "voice_settings": {
            "stability": args.stability,
            "similarity_boost": args.similarity,
        },
    }
    req = urllib.request.Request(
        f"{API_BASE}/{args.voice}",
        data=json.dumps(payload).encode(),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code}: {e.read().decode()}\n")
        return 1
    print(out)

if __name__ == "__main__":
    sys.exit(main())
```

#### `transcribe.py` (STT)

Acepta cualquier formato de audio o video (Scribe maneja mp3, ogg, mp4, webm, etc. — no hay que extraer audio antes con ffmpeg).

```python
#!/usr/bin/env python3
"""ElevenLabs Scribe (STT). Stdlib only multipart upload.
Reads ELEVENLABS_API_KEY from env. Prints transcript on stdout.
"""
import argparse, json, mimetypes, os, pathlib, sys, urllib.request, urllib.error, uuid

API_URL = "https://api.elevenlabs.io/v1/speech-to-text"

def build_multipart(fields, file_path):
    boundary = f"----Boundary{uuid.uuid4().hex}"
    crlf = b"\r\n"
    parts = []
    for name, value in fields.items():
        parts.append(f"--{boundary}".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b"")
        parts.append(str(value).encode())
    mime, _ = mimetypes.guess_type(file_path.name)
    parts.append(f"--{boundary}".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; '
        f'filename="{file_path.name}"'.encode()
    )
    parts.append(f"Content-Type: {mime or 'application/octet-stream'}".encode())
    parts.append(b"")
    parts.append(file_path.read_bytes())
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    return crlf.join(parts), boundary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        sys.stderr.write("ERROR: ELEVENLABS_API_KEY missing\n")
        return 2

    audio = pathlib.Path(args.audio).resolve()
    fields = {"model_id": "scribe_v1"}
    if args.lang:
        fields["language_code"] = args.lang
    body, boundary = build_multipart(fields, audio)

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "xi-api-key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code}: {e.read().decode()}\n")
        return 1
    if not args.quiet:
        sys.stderr.write(json.dumps({
            "language": data.get("language_code"),
        }, ensure_ascii=False) + "\n")
    print(data.get("text", "").strip())

if __name__ == "__main__":
    sys.exit(main())
```

### Cómo se invoca desde el agente

Cuando llega un audio (Telegram/Discord):

1. Detecta el adjunto en el `<channel>` block.
2. Descarga: `download_attachment(file_id)` → path local.
3. `python3 .claude/skills/elevenlabs-tts/transcribe.py <path>` → texto en stdout.
4. Procesa el texto. Si es pregunta, responde; si es instrucción, ejecuta.

Cuando el user pide audio:

1. `python3 .claude/skills/elevenlabs-tts/generate.py "<texto>"` → mp3 path.
2. Adjunta al canal: `reply(files=[<path>])`.

---

## Generación de imágenes con Replicate Flux

### Setup

1. Cuenta en [replicate.com](https://replicate.com). Sin tier gratuito a 2026 — mínima carga $5.
2. Account settings → API tokens → Create token. Token formato `r8_...`.
3. Pega en `~/.env.global`:
   ```
   REPLICATE_API_TOKEN="r8_..."
   ```

### Skill `image-gen`

```
.claude/skills/image-gen/
├── SKILL.md
└── generate.py
```

`generate.py` usa el endpoint de Replicate `models/{model}/predictions` con polling. Defaults: `black-forest-labs/flux-1.1-pro` (~$0.04/img), aspect 1:1, png. Variantes baratas: `flux-schnell` (~$0.003), `flux-dev` (~$0.025).

Pseudocódigo:

```python
import json, os, urllib.request, time

token = os.environ["REPLICATE_API_TOKEN"]
url = "https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions"
body = {
    "input": {
        "prompt": "...",
        "aspect_ratio": "1:1",
        "output_format": "png",
        "safety_tolerance": 2,
    }
}
req = urllib.request.Request(
    url,
    data=json.dumps(body).encode(),
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": "wait=60",
    },
    method="POST",
)
# ... poll until status == "succeeded", download output[0]
```

Output a `/tmp/key-imgs/flux_<ts>.png`. Logs de uso en `~/.claude-code-key/image-usage.jsonl`.

### Variaciones útiles

- **Avatar editorial monocromo:** prompt con "black and white editorial portrait, high contrast chiaroscuro, Lindbergh / Newton style, square composition for circular crop".
- **Iteración rápida:** `flux-schnell` ($0.003) para drafts, `flux-1.1-pro` ($0.04) para la final.

### Anti-patterns

- Generar imágenes sin que el user lo pida.
- Subir mp4 a Drive/Notion sin confirmación. Entrega + descarte.
- Hardcodear la API key en el script.

---

## Análisis de video

Mezcla de **ffmpeg local** (frames) + **Read nativo** del agente (visión) + **Scribe** (audio). NO requiere API de visión externa porque Claude Code ya ve imágenes con su tool `Read`.

### Setup ffmpeg sin sudo

Instalar ffmpeg como binario aislado (no toca el sistema):

```bash
mkdir -p ~/.local/share/key-tools
python3 -m venv ~/.local/share/key-tools/venv
~/.local/share/key-tools/venv/bin/pip install --quiet imageio-ffmpeg
mkdir -p ~/.local/bin
ln -sf "$(~/.local/share/key-tools/venv/bin/python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" ~/.local/bin/ffmpeg
~/.local/bin/ffmpeg -version | head -1  # verificar
```

Esto te da ffmpeg 7.0.2 estático sin pelear con apt o PEP 668.

### Skill `video-vision`

```
.claude/skills/video-vision/
├── SKILL.md
└── extract_frames.py
```

`extract_frames.py` extrae N frames espaciados uniformemente con ffmpeg. Default 3.

```python
#!/usr/bin/env python3
"""Extract N frames from video. Default 3 frames evenly spaced."""
import argparse, json, pathlib, subprocess, sys, time

DEFAULT_FFMPEG = str(pathlib.Path.home() / ".local/bin/ffmpeg")
DEFAULT_OUT = "/tmp/key-vision"

def probe_duration(video, ffmpeg):
    p = subprocess.run([ffmpeg, "-i", str(video), "-hide_banner"], capture_output=True, text=True)
    for line in p.stderr.splitlines():
        if line.strip().startswith("Duration:"):
            ts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = ts.split(":")
            return int(h)*3600 + int(m)*60 + float(s)
    raise RuntimeError("no duration")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("-n", type=int, default=3)
    args = ap.parse_args()

    video = pathlib.Path(args.video).resolve()
    duration = probe_duration(video, DEFAULT_FFMPEG)
    out_dir = pathlib.Path(DEFAULT_OUT) / f"{int(time.time())}_{video.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    step = duration / (args.n + 1)
    paths = []
    for i in range(args.n):
        ts = step * (i + 1)
        out = out_dir / f"frame_{i:02d}.jpg"
        subprocess.run([
            DEFAULT_FFMPEG, "-ss", f"{ts:.3f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "3", "-y", str(out)
        ], capture_output=True)
        paths.append(str(out))
    print("\n".join(paths))

if __name__ == "__main__":
    sys.exit(main())
```

### Cómo se invoca desde el agente

Cuando llega un video (mp4, video note de Telegram, etc.):

1. `download_attachment(file_id)` → path local.
2. `extract_frames.py <path> -n 3` → 3 jpg paths.
3. **Read cada frame** con la tool nativa Read del agente. Claude Code es multimodal — ve la imagen sin Claude API anidada.
4. `transcribe.py <path>` (mismo skill `elevenlabs-tts`) → texto del audio.
5. Combinar respuesta: descripción visual + transcripción.

**Cero overhead de API externa de visión.** Solo paga el STT.

---

## Multi-modal en Mia / nanobot real

Si además del agente Claude Code corres un **nanobot real** (Python instalado por pip), su channel handler invoca scripts via subprocess. Patrón:

- Mensaje entrante con voz → handler descarga attachment → `subprocess.run(["python3", "skills/elevenlabs-tts/transcribe.py", path], capture_output=True)` → stdout entra al loop del agente como texto.
- Saliente con audio → agente decide responder por voz → `subprocess.run(["python3", "skills/elevenlabs-tts/generate.py", text], capture_output=True)` → stdout es el path del mp3 → handler lo adjunta al canal.

Las skills `elevenlabs-tts`, `image-gen`, etc. son **transversales** — funcionan tanto en Claude Code como en nanobot porque son scripts Python sin imports especiales del runtime.

## Anti-patterns

- **Default a voz cuando el user pidió texto.** Si el user escribió texto, responde con texto. Audio solo si lo pide o si el contexto lo justifica claramente.
- **Mandar contenido sensible (tokens, contraseñas, info financiera/médica) a APIs externas.** Avisar al user antes.
- **Loggear el contenido transcrito en archivos persistentes** salvo que el user lo pida. Los audios pueden tener PII.
- **No registrar consumo.** Cada skill loguea a `~/.claude-code-key/<capability>-usage.jsonl` para auditar costos.

## Rotación de tokens

Las API keys de ElevenLabs y Replicate son **secrets**. Rotación recomendada:

- **Cada 90 días** o cuando alguien externo haya tenido acceso al server.
- **Inmediato** si se pegó accidentalmente al chat o git.
- Revocar la vieja antes de cargar la nueva.
- Editar `~/.env.global`, restart `myagent.service`.
