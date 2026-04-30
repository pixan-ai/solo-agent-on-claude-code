# 01 — Prerequisitos

## Cuenta Claude

- Suscripción **Claude MAX** activa (o Pro). MAX da más cupo de uso, lo cual importa para un agente que corre 24/7.
- Login funcional en [claude.ai](https://claude.ai) — vas a reusar el OAuth del CLI.
- (Opcional pero recomendado) cuenta secundaria para el agente, distinta de la que usas en Desktop. Ventaja: cuotas y connectors no se mezclan. Desventaja: pagas dos suscripciones. La mayoría arranca con una sola y separa después si se justifica.

## Servidor Linux

Recomendado: Ubuntu 24.04 LTS o Debian 12. Otras distros funcionan; los pasos asumen `systemd --user` y `apt`.

**Recursos mínimos:**

| Recurso | Mínimo | Cómodo |
|---------|--------|--------|
| RAM | 1 GB | 2 GB |
| Disco | 10 GB | 20 GB |
| CPU | 1 vCPU | 2 vCPU |
| Red | conexión estable, no necesita IP pública si no expones HTTP |

Cualquier VPS de $5–10/mes (Hetzner CX11, DigitalOcean basic, AWS Lightsail) sobra.

**Si ya tienes un homelab:** cualquier máquina vieja con Linux corriendo sirve. El consumo en idle es ~50-200MB RAM.

## Cuenta de usuario en el servidor

- Un usuario no-root (`pixan`, `agent`, lo que sea) con su propio home.
- Acceso `sudo` para la instalación inicial (Node.js, opcionalmente Python venv tools).
- **Lingering activado** para que `systemd --user` siga corriendo cuando cierres la sesión SSH:
  ```bash
  sudo loginctl enable-linger $USER
  ```
- (Recomendado) clave SSH en lugar de password.

## Node.js para Claude Code

Claude Code se distribuye como paquete npm. Necesitas Node 20 LTS o superior. Opciones:

```bash
# Opción 1: nvm (recomendado, instalación per-user sin sudo)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts

# Opción 2: nodesource (sistema)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
```

Verifica:

```bash
node --version  # >= v20.x
npm --version
```

## Python (opcional, para skills con scripts)

Solo necesario si vas a usar skills que ejecuten Python (TTS, STT, image gen, video vision). Ubuntu 24.04 viene con Python 3.12 — sirve.

```bash
python3 --version  # >= 3.10
```

**PEP 668 caveat:** Ubuntu 24.04 marca el Python del sistema como "externally-managed". Si una skill necesita instalar paquetes pip, **NO uses `pip install --user`** directo. Mejor crea venvs aislados (ver `09-optional-capabilities.md`).

## Plan de cuota Claude

El plan MAX en 2026 tiene un límite combinado de runs disparados por `CronCreate`, `ScheduleWakeup`, y `RemoteTrigger` por cuenta:

- **MAX (\$200/mes):** 15 runs/24h.
- **MAX Pro (\$300/mes):** más, varía. Consulta el plan vigente.

Si vas a tener heartbeat cada 90 min (16/día), ya saturas el cupo y dejas cero para webhooks. Diseña tu cadencia según esto:

| Cadencia heartbeat | Runs/día | Margen para webhooks |
|--------------------|----------|----------------------|
| Cada 60 min | 24 | ❌ excede |
| Cada 90 min | 16 | ❌ marginal |
| Cada 2 h | 12 | ✅ 3 webhooks/día |
| Cada 3 h | 8 | ✅ 7 webhooks/día |

`08-memory.md` y `07-heartbeat-cron-dream.md` profundizan en cómo armar tu cadencia.

## Domain / DNS (opcional)

Solo necesario si vas a exponer el agente vía HTTP (webhooks externos, OpenAI-compat API, gateway). Para chat interno en Discord/Telegram **no necesitas dominio** — los plugins usan polling outbound.

Si quieres exponer:
- Cloudflare Tunnel (gratis, sin abrir puertos) — recomendado.
- Caddy / nginx + Let's Encrypt — clásico, requiere puerto 80/443 abierto.

## Cuentas opcionales para capacidades extendidas

Solo si vas a usar el doc 09 (capacidades opcionales):

- **ElevenLabs** (TTS + STT) — [elevenlabs.io](https://elevenlabs.io). Tier gratuito limitado. Plan Starter $5/mes da margen para uso personal.
- **Replicate** (Flux para imágenes) — [replicate.com](https://replicate.com). Sin tier gratis a 2026, mínima carga $5 que rinde ~125 imágenes Flux Pro o ~1500 Schnell.
- **OpenAI / Together / OpenRouter** (modelos alternativos) — solo si quieres correr Mia o un nanobot real al lado del agente Claude. **No es necesario para el patrón core.**

## Lo que NO necesitas

- LangChain / LlamaIndex / cualquier framework de agentes.
- API key de Anthropic separada — la suscripción MAX es OAuth, suficiente para Claude Code.
- Base de datos externa — la memoria vive en archivos markdown.
- Vector DB — el contexto se maneja con auto-compact de Claude Code, no embeddings.
- Docker / Kubernetes — opcional, pero el patrón asume systemd directo. Más simple, menos sorpresas.
