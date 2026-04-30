# 10 — Troubleshooting

Gotchas vistos en producción. Cada uno con síntoma, causa, fix.

## El servicio crashea: "User not authenticated"

**Síntoma:** logs `Error: not authenticated` o `OAuth token expired`.

**Causa:** `.credentials.json` no se está cargando o expiró.

**Fix:**
```bash
# Verifica que CLAUDE_CONFIG_DIR esté en el .service:
systemctl --user show myagent.service -p Environment | grep CLAUDE_CONFIG_DIR

# Verifica que el archivo exista:
ls -la $CLAUDE_CONFIG_DIR/.credentials.json

# Si expiró, re-loguea:
CLAUDE_CONFIG_DIR=~/.claude-myagent claude login
systemctl --user restart myagent.service
```

---

## "MCP server disconnected" mid-sesión (Notion / Gmail / etc.)

**Síntoma:** un connector heredado de claude.ai (`mcp__claude_ai_<servicio>__*`) deja de funcionar a la mitad de la sesión. El system reminder anuncia "MCP server disconnected".

**Causa:** el server de Anthropic para ese MCP tuvo un blip; tu agente headless NO reconecta automáticamente.

**Fix:**
```bash
systemctl --user restart myagent.service
```

Esto pierde el contexto de la sesión actual pero recupera todos los connectors.

**Prevención:** si el MCP es crítico, considera correr un cron diario que reinicie el agente proactivamente (ej. 04:00 AM). El reinicio nocturno también ayuda con leaks de memoria de sesiones largas.

---

## Anthropic provider en nanobot/Mia: "No API key configured for provider 'None'"

**Síntoma:** instalas nanobot real, lo apuntas a tu MAX, y el `gateway` falla con "No API key configured".

**Causa:** **nanobot NO soporta OAuth para Anthropic, solo API key**. Tu MAX usa OAuth (`.credentials.json`), no API key — no se puede reusar.

**Fix:**
1. Crea API key separada en [console.anthropic.com](https://console.anthropic.com) (cuesta aparte del MAX).
2. Mete la key en `providers.anthropic.apiKey` del `~/.nanobot/config.json` (NO en env var — nanobot lee el config, no el env).
3. Setea `agents.defaults.provider = "anthropic"` explícito (no `"auto"`).
4. Restart.

Alternativa más barata: provider OpenRouter, DeepSeek, Kimi, etc. Una key con uso por demanda.

---

## ffmpeg / pip install falla con "externally-managed-environment"

**Síntoma:**
```
error: externally-managed-environment
× This environment is externally managed
note: If you believe this is a mistake...
```

**Causa:** Ubuntu 24.04 marca el Python del sistema como "externally-managed" (PEP 668). `pip install --user` está bloqueado.

**Fix (mejor):** crear venv aislado.
```bash
mkdir -p ~/.local/share/key-tools
python3 -m venv ~/.local/share/key-tools/venv
~/.local/share/key-tools/venv/bin/pip install <package>
```

**Fix (rápido):** `pip install --break-system-packages` — funciona pero feo, no recomendado.

Para ffmpeg específicamente: `imageio-ffmpeg` en venv aislado, symlink a `~/.local/bin/ffmpeg`. Ver `09-optional-capabilities.md`.

---

## `systemctl --user` falla con "Failed to connect to bus"

**Síntoma:** cualquier `systemctl --user` da `Failed to connect to bus`.

**Causa:** falta lingering, o estás en un shell sin sesión user proper.

**Fix:**
```bash
sudo loginctl enable-linger $USER
# Reconecta SSH una vez para que arranque el bus user
exit
ssh user@server
systemctl --user status  # ya debería funcionar
```

---

## El agente arranca pero no responde a Discord/Telegram

**Síntoma:** el bot está online pero ignora mensajes.

**Causas posibles:**

1. **No estás en allowlist.** Verifica `$CLAUDE_CONFIG_DIR/channels/<canal>/access.json`. Tu user_id o nombre debe estar en `users` o `user_ids`.
2. **Token incorrecto.** Logs mostrarán `401 Unauthorized` o `invalid token`.
3. **Plugin no cargado.** `settings.json` debe tener `enabledPlugins.<canal>@claude-plugins-official: true` y `extraKnownMarketplaces` con el repo. Restart después de editar.
4. **Intents Discord faltantes.** En el dashboard de Discord developer, el bot necesita "Message Content" intent activado.

```bash
# Diagnóstico rápido:
journalctl --user -u myagent.service -n 50 | grep -iE "discord|telegram|auth|denied"
```

---

## Rate limit de Claude MAX

**Síntoma:** `429 Too Many Requests` o degradación en velocidad de respuesta.

**Causa:** saturaste el cupo diario del MAX. Pasa con heartbeats muy frecuentes.

**Fix:** baja la cadencia. Ver tabla en `01-prerequisites.md`. Recomendado:
- Heartbeat cada 2-3h.
- Cron Dream una vez por semana.
- Reservar margen para webhooks/RemoteTrigger.

---

## Discord bot foto de perfil no cambia

**Síntoma:** quieres cambiarle la foto al bot vía la API y no encuentras endpoint.

**Causa:** la Bot API de Discord no expone `setMyProfilePhoto`. La foto del bot se cambia **manualmente** vía @BotFather (Telegram) o desde el Developer Portal (Discord).

**Fix:**
- Discord: developer.discord.com → Application → General Information → "App Icon" upload.
- Telegram: `/setuserpic` en @BotFather, sigue las instrucciones.

---

## Memoria infla el context y rompe la sesión

**Síntoma:** sesiones largas terminan con errores de context window o auto-compact muy agresivo.

**Causa:** `MEMORY.md` o entradas individuales crecieron sin cap.

**Fix:**
1. Aplica caps duros (ver `08-memory.md`):
   - `MEMORY.md` preview: 32k chars max.
   - Entrada individual: 64k hard cap.
2. Si una entrada genuinamente excede 32k, divídela en archivos separados.
3. Corre Dream consolidate para detectar redundancias.

---

## Un cron del agente no se ejecuta

**Síntoma:** programaste `CronCreate` pero nunca dispara.

**Causas posibles:**

1. **Saturaste el límite diario** (15 runs/24h MAX). Cron silenciosamente skipea. Verifica con tu dashboard de Anthropic.
2. **El cron expression está mal.** `CronCreate` usa cron syntax estándar (`min hour dom mon dow`). Errores comunes: confundir DOM y DOW, usar `*/N` con N grande.
3. **Timezone.** El servidor puede estar en UTC. Si quieres "07:00 CDMX" pero el cron es UTC, ajusta a `0 13 * * *` (UTC = CDMX + 6h en invierno).
4. **`CronCreate` es session-only y reiniciaste el agente.** En muchos setups (verificado en Claude Code 2.1.x), el flag `durable=true` se ignora silenciosamente — todos los crons mueren al reiniciar el service. Para reminders persistentes, **usa el skill `agent-cron`** (systemd timers). Ver `skills/agent-cron/SKILL.md`.

```bash
# Verifica timezone del servidor:
timedatectl | grep "Time zone"

# Si quieres cambiar:
sudo timedatectl set-timezone America/Mexico_City
```

---

## "Not a git repository" al intentar Dream

**Síntoma:** Dream consolidate intenta `git blame memory/MEMORY.md` y falla con `fatal: not a git repository`.

**Causa:** `$CLAUDE_CONFIG_DIR/projects/<id>/` no tiene git inicializado.

**Fix:**
```bash
cd $CLAUDE_CONFIG_DIR/projects/<id>/
git init -b main
cat > .gitignore <<'EOF'
*
!memory/
!memory/**
!.gitignore
EOF
git add .gitignore memory/
git -c user.name=agent -c user.email=agent@local commit -m "memory: initial snapshot"
```

Después el Dream funciona normal y los siguientes commits van como `dream: <ts>, N changes`.

---

## El agente "se sale de carácter" en cron jobs

**Síntoma:** el agente responde en cron con tono genérico de asistente, no su voz personalizada (Key, Mia, etc.).

**Causa:** el prompt del cron es muy corto y no carga BOOTSTRAP/SOUL/USER.

**Fix:** prompts de cron deben incluir contexto de bootstrap. Ejemplo bueno:

```
prompt = "Lee BOOTSTRAP.md y SOUL.md. Después ejecuta el skill /morning-brief. Reporta en tu voz."
```

Mal:

```
prompt = "manda el brief"
```

Alternativa: usa `--append-system-prompt-file AGENTS.md` en cada invocación si tu wrapper lo permite.

---

## Audio TTS suena cortado / robótico

**Síntoma:** ElevenLabs genera audio pero la voz suena entrecortada o con artifacts.

**Causa:** texto muy largo (>5000 chars) en una sola request.

**Fix:** divide en oraciones, genera mp3 por chunk, concatena con ffmpeg:

```bash
ffmpeg -f concat -safe 0 -i list.txt -c copy out.mp3
```

`list.txt`:
```
file 'chunk1.mp3'
file 'chunk2.mp3'
file 'chunk3.mp3'
```

---

## El agente reinicia en loop

**Síntoma:** `Restart=on-failure` lo respawnea cada 10s.

**Diagnóstico:**
```bash
journalctl --user -u myagent.service -n 200 --no-pager
```

Buscar el error real. Mientras debugeas, evita el loop:
```bash
systemctl --user stop myagent.service
```

Causas frecuentes:
- Variable de entorno faltante (no se cargó `.env.global`).
- Workspace path incorrecto (`WorkingDirectory` no existe).
- Plugin con bug que tira el proceso al iniciar.

---

## Cómo pedir ayuda

Si nada de aquí aplica:

- Issue en este repo (cuando se publique) con: log de `journalctl`, output de `systemctl --user show myagent.service -p Environment -p ExecStart`, versión de claude (`claude --version`), versión Node (`node --version`), distro.
- Anthropic Discord (oficiales) para issues del binario `claude` o connectors claude.ai.
- nanobot Discord/Feishu para preguntas sobre nanobot real, no este patrón.
