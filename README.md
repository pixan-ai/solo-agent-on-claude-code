# Solo Agent on Claude Code

> **Cómo correr un agente Claude Code 24/7 en tu propio servidor Linux, usando solo tu suscripción Claude MAX, sin frameworks de terceros.**

Este repositorio documenta el patrón completo: cómo configurar Claude Code como un agente persistente con personalidad propia, memoria persistente, canales de chat (Discord, Telegram), tareas recurrentes (heartbeat, cron, dream), y capacidades extensibles — sin LangChain, sin nanobot empresarial, sin OpenAI API, sin frameworks externos. Solo tu cuenta Claude.ai con plan MAX y un servidor Linux modesto.

**Ejemplo vivo del patrón:** [key.pixan.bot](https://key.pixan.bot) — Key, el agente que opera bajo este template, con datos reales de su instancia en producción.

## Instala el skill `agent-cron` en 30 segundos

`agent-cron` es el diferenciador técnico de este repo: crones persistentes con `systemd --user` que sobreviven restarts y reboots, reemplazando el `CronCreate` session-only del harness.

```bash
claude --plugin-url https://github.com/pixan-ai/solo-agent-on-claude-code/releases/download/agent-cron-v1.0.0/agent-cron-v1.0.0.zip
```

Requiere Claude Code ≥ 9 mayo 2026 (release con soporte para `--plugin-url`). Para detalles y otros patrones, sigue leyendo.

## Para quién es esto

- Desarrolladores que quieren un agente personal corriendo 24/7 sin pagar SaaS adicional.
- Operadores que ya tienen Claude MAX y quieren explotar su cupo más allá de chats puntuales.
- Builders solos / equipos chicos que necesitan automatización event-driven (mensajes Discord/Telegram, emails, recordatorios) sin vendor lock-in.
- Personas curiosas sobre el modelo de OpenClaw / nanobot / Claude Code agentes pero que prefieren leer un caso real antes de pelear con un framework.

## Por qué este patrón

- **Ya pagaste el MAX.** Los $200/mes incluyen un cupo grande de uso. Un agente headless lo aprovecha en momentos en que no estás chateando.
- **Sin SaaS recurrente.** Cero costo extra mensual salvo el server (~$5-20/mes en Hetzner/DigitalOcean) y opcionalmente APIs externas (ElevenLabs, Replicate) que ya pagas por uso.
- **Tu data en tu disco.** Memoria, transcripts, configs viven local. No hay BD ajena que vaya a quebrar y llevarse tus datos.
- **Personalizable a fondo.** SOUL.md y USER.md te dan voz y conocimiento del usuario propios. No es un asistente genérico.
- **Hackeable.** Skills son markdown editable. Sin compilación, sin runtime ajeno.

## Lo que vas a tener al final

- Un servicio `systemd --user` que corre Claude Code en background, sin TTY.
- Tu cuenta de Claude reusada vía OAuth — un solo `.credentials.json` para CLI y agente.
- Un workspace con `SOUL.md` (personalidad), `USER.md` (perfil del operador), `HEARTBEAT.md` (tareas recurrentes), `BOOTSTRAP.md` (ritual de arranque), `MEMORY.md` (índice de memoria persistente), `.claude/skills/` (rutinas modulares).
- Plugins de Discord y/o Telegram para que te escriba (y te oiga, si conectas STT/TTS).
- Heartbeat cada N minutos que evalúa una lista de chequeos y solo te despierta si hay algo accionable.
- Dream semanal que consolida memoria y propone ajustes (con aprobación tuya para cambios canónicos).
- Capacidades opcionales: voz (ElevenLabs), imágenes (Replicate Flux), análisis de video (ffmpeg + visión nativa de Claude).

## Tabla de contenidos

| # | Documento | Qué cubre |
|---|-----------|-----------|
| 1 | [Prerequisitos](01-prerequisites.md) | Cuenta Claude MAX, servidor Linux, recursos mínimos, lingering |
| 2 | [Instalación](02-installation.md) | Claude Code, `CLAUDE_CONFIG_DIR` aislado, login OAuth |
| 3 | [Servicio systemd](03-systemd-service.md) | `.service` user, `Environment`, `--dangerously-skip-permissions`, journalctl |
| 4 | [Estructura del workspace](04-workspace-structure.md) | SOUL, USER, AGENTS, BOOTSTRAP, IDENTITY, HEARTBEAT, CLAUDE.md, TOOLS.md |
| 5 | [Patrón de skills](05-skills-pattern.md) | Frontmatter, anatomy, progressive disclosure, anti-patterns |
| 6 | [Canales y MCPs](06-channels-mcp.md) | Plugins Discord/Telegram, MCPs de claude.ai, allowlists |
| 7 | [Heartbeat / cron / dream](07-heartbeat-cron-dream.md) | Tres ciclos, fases del heartbeat, evaluator-self-check |
| 8 | [Memoria persistente](08-memory.md) | `memory/`, tipos, git, caps, blame staleness, auto-commit |
| 9 | [Capacidades opcionales](09-optional-capabilities.md) | TTS/STT, image gen, video analysis (con costo per-use) |
| 10 | [Troubleshooting](10-troubleshooting.md) | Gotchas vistos en producción |
| - | [TEMPLATES/](TEMPLATES/) | SOUL/USER/etc. genéricos con placeholders |

## Stack mínimo (sin terceros)

```
Servidor Linux (Ubuntu 24.04+ recomendado)
├── Claude Code (npm install -g @anthropic-ai/claude-code)
├── CLAUDE_CONFIG_DIR aislado (~/.claude-myagent/)
├── Suscripción Claude MAX → .credentials.json (OAuth)
├── systemd --user service
├── Workspace dir (~/agents/<name>/)
│   ├── SOUL.md, USER.md, AGENTS.md, BOOTSTRAP.md
│   ├── HEARTBEAT.md, IDENTITY.md, CLAUDE.md, TOOLS.md
│   └── .claude/skills/<rutina>/SKILL.md
└── Plugins (opcionales, comunitarios):
    ├── discord (claude-plugins-official/discord)
    └── telegram (claude-plugins-official/telegram)
```

## Stack extendido (con APIs externas opcionales)

| Capacidad | API externa | Costo aproximado | Skill |
|-----------|-------------|------------------|-------|
| Hablar (TTS) | ElevenLabs Lumina | ~$5/M chars | `elevenlabs-tts/generate.py` |
| Escuchar (STT) | ElevenLabs Scribe | ~$0.40/h audio | `elevenlabs-tts/transcribe.py` |
| Generar imagen | Replicate Flux 1.1 Pro | ~$0.04/imagen | `image-gen/generate.py` |
| Ver video | ffmpeg local + Read nativo | $0 (excepto STT del audio) | `video-vision/extract_frames.py` |

Ninguna de estas es obligatoria. El core funciona sin ellas.

## Estado del proyecto

Este es un **patrón en producción**, no una librería empaquetada. La idea es que lo leas, lo adaptes, y lo deformes a tu agente. No esperes una API estable o versionado SemVer — esto es opinión expresada en archivos.

## Licencia

MIT (propuesta — confirmar antes de hacer público).

## Reconocimientos

- [Anthropic](https://www.anthropic.com/) — Claude, Claude Code, MAX.
- [hkuds/nanobot](https://github.com/hkuds/nanobot) — fuente de inspiración para varios patrones (`heartbeat`, `dream`, `ask_user`, `on_progress`, `skill-creator`). Adoptamos los conceptos, no el runtime Python.
- [Andrej Karpathy](https://github.com/forrestchang/andrej-karpathy-skills) — las cuatro reglas operativas (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution).
- [OpenClaw](https://github.com/openclaw/openclaw) — referencia de filosofía de agentes hackeables.
