# 03 — Servicio systemd

El agente corre como **`systemd --user` service** — sin sudo, sin tocar systemd-system. Esto es lo que permite "agente 24/7" sin convertirte en root del servidor.

## Pre-checks

```bash
# 1. Lingering activado para que el user service sobreviva al logout SSH:
loginctl show-user $USER | grep Linger
# Debe decir: Linger=yes
# Si dice no:
sudo loginctl enable-linger $USER

# 2. Directorio de unidades systemd-user existe:
mkdir -p ~/.config/systemd/user
```

## El archivo `.service`

`~/.config/systemd/user/myagent.service`:

```ini
[Unit]
Description=Claude Code Agent — myagent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/agents/myagent
EnvironmentFile=%h/.env.global
Environment=CLAUDE_CONFIG_DIR=%h/.claude-myagent
Environment=PATH=%h/.bun/bin:%h/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=NODE_OPTIONS=--max-old-space-size=2048

ExecStart=/usr/bin/env claude \
  --dangerously-skip-permissions \
  --append-system-prompt-file %h/agents/myagent/AGENTS.md

Restart=on-failure
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=%h
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

### Anatomy de los campos clave

| Campo | Por qué |
|-------|---------|
| `WorkingDirectory=%h/agents/myagent` | Donde el agente "vive" — ahí lee SOUL/USER/etc. |
| `EnvironmentFile=%h/.env.global` | Secrets (API keys externas, tokens). Patrón: archivo `.env` con `VAR="..."` lines. |
| `CLAUDE_CONFIG_DIR=%h/.claude-myagent` | Aisla credentials/plugins de tu CLI normal. |
| `--dangerously-skip-permissions` | Sin esto, en sesión sin TTY el agente se cuelga esperando aprobaciones. |
| `Restart=on-failure` | Si crashea, reinicia. NO `always` — eso re-arranca incluso después de un `stop` voluntario. |
| `ProtectSystem=strict` + `ReadWritePaths=%h` | El agente solo puede escribir en su home. Reduce blast radius. |
| `NODE_OPTIONS=--max-old-space-size=2048` | Cap de heap Node a 2GB. Sin esto, sesiones largas pueden inflar memoria. |

### Sobre `EnvironmentFile`

Patrón canónico para secrets:

```bash
# ~/.env.global  (perms 600)
ANTHROPIC_API_KEY=""  # vacío si solo usas OAuth via .credentials.json
ELEVENLABS_API_KEY="sk_..."
REPLICATE_API_TOKEN="r8_..."
GITHUB_PAT="ghp_..."
```

```bash
chmod 600 ~/.env.global
```

systemd lee este archivo y exporta cada variable al proceso del agente. **Nunca lo commitees a git.** Inclúyelo en `.gitignore` global (ver `04-workspace-structure.md`).

### `--append-system-prompt-file`

Apunta a `AGENTS.md` del workspace. Es el primer prompt que el agente ve cuando arranca cada sesión. Contiene instrucciones operativas (cuándo usar cron vs heartbeat, cómo se reportan errores, etc.). Ver `04-workspace-structure.md`.

## Habilitar y arrancar

```bash
systemctl --user daemon-reload
systemctl --user enable --now myagent.service
```

`--now` arranca inmediatamente. Sin él, solo enable (arranca al próximo boot/lingering).

## Operaciones comunes

```bash
# Status
systemctl --user status myagent.service

# Logs en vivo (Ctrl-C para salir)
journalctl --user -u myagent.service -f

# Logs últimas 50 líneas
journalctl --user -u myagent.service -n 50

# Reload tras editar el .service
systemctl --user daemon-reload
systemctl --user restart myagent.service

# Restart sin recargar (si solo cambiaste config en CLAUDE_CONFIG_DIR)
systemctl --user restart myagent.service

# Stop sin que reinicie
systemctl --user stop myagent.service

# Disable (que no arranque al boot)
systemctl --user disable myagent.service
```

## Múltiples agentes en el mismo servidor

Patrón: un `.service` por agente, cada uno con `CLAUDE_CONFIG_DIR` distinto y `WorkingDirectory` distinto.

```
~/.config/systemd/user/
├── alpha.service     → CLAUDE_CONFIG_DIR=~/.claude-alpha    WorkingDirectory=~/agents/alpha
├── beta.service      → CLAUDE_CONFIG_DIR=~/.claude-beta     WorkingDirectory=~/agents/beta
└── gamma.service     → CLAUDE_CONFIG_DIR=~/.claude-gamma    WorkingDirectory=~/agents/gamma
```

Ventajas:
- Cada uno tiene OAuth y plugins independientes (puedes loguear cada uno con cuenta distinta).
- Reinicios individuales sin tirar todos.
- Cuotas separadas si las cuentas Claude son distintas.

## Healthcheck (opcional)

Si quieres vigilancia activa, agrega un cron del usuario que pingee el agente:

```bash
crontab -e
# */15 * * * * systemctl --user is-active myagent.service > /dev/null || systemctl --user restart myagent.service
```

systemd ya hace `Restart=on-failure`, este cron es belt-and-suspenders para casos donde el proceso "vive" pero está colgado (no se cae).

## Gotchas

### `systemctl --user` no encuentra el servicio

```
Failed to start myagent.service: Unit myagent.service not found.
```

→ Olvidaste `daemon-reload` después de crear el archivo. Corre:
```bash
systemctl --user daemon-reload
```

### `Failed to connect to bus`

Falta lingering O estás corriendo desde un shell sin sesión user proper. Activa lingering:
```bash
sudo loginctl enable-linger $USER
```

Y reconecta la sesión SSH una vez para que el bus user arranque.

### El servicio arranca pero loguea "User not authenticated"

`.credentials.json` no está siendo encontrado. Verifica:
1. `CLAUDE_CONFIG_DIR` en el `Environment=` del .service.
2. Que el archivo exista y sea legible: `ls -la $CLAUDE_CONFIG_DIR/.credentials.json`.
3. Que tenga el OAuth válido: `cat $CLAUDE_CONFIG_DIR/.credentials.json | jq '.expires_at'` debe estar en el futuro o cerca.

### El servicio cumple Restart en loop

Si crashea siempre con el mismo error, `Restart=on-failure` lo va a respawnear cada 10s. Para detener el loop:
```bash
systemctl --user stop myagent.service
```

Investiga el error en `journalctl --user -u myagent.service -n 100`.

### Permission denied al editar archivos del workspace

`ProtectSystem=strict` con `ReadWritePaths=%h` debería permitir TODO el home. Si te aparece error en otro path, agrégalo a `ReadWritePaths=`. Ej: `ReadWritePaths=%h /tmp`.
