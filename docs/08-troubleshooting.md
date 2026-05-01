# 08 — Troubleshooting

Problemas observados con síntoma y fix. La lista no es exhaustiva.

## El servicio falla con "User not authenticated"

**Síntoma.** Logs con `Error: not authenticated` o `OAuth token expired`.

**Causa.** `.credentials.json` no se está cargando o expiró.

**Diagnóstico y fix.**
```bash
systemctl --user show myagent.service -p Environment | grep CLAUDE_CONFIG_DIR
ls -la "$CLAUDE_CONFIG_DIR/.credentials.json"

# Si expiró, re-loguear:
CLAUDE_CONFIG_DIR=~/.claude-myagent claude login
systemctl --user restart myagent.service
```

## "MCP server disconnected" mid-sesión

**Síntoma.** Un connector heredado de claude.ai (Notion / Gmail / etc.) deja de funcionar; system reminder anuncia "no longer available".

**Causa.** El backend de Anthropic para ese MCP tuvo un blip. La sesión headless no reconecta automáticamente.

**Fix.** Reiniciar el servicio. Pierde el contexto de la sesión actual pero recupera todos los connectors.
```bash
systemctl --user restart myagent.service
```

**Prevención.** Si un MCP es crítico para la operación, considerar un cron diario que reinicie el agente. El reinicio nocturno también ayuda con leaks de memoria de sesiones largas.

## "Failed to connect to bus"

**Síntoma.** Cualquier `systemctl --user` falla con `Failed to connect to bus`.

**Causa.** Lingering inactivo, o shell sin sesión user adecuada.

**Fix.**
```bash
sudo loginctl enable-linger $USER
# Reconectar SSH una vez para que el bus user arranque:
exit
ssh user@server
systemctl --user status
```

## El servicio reinicia en loop

**Síntoma.** `Restart=on-failure` respawnea cada 10s.

**Diagnóstico.**
```bash
journalctl --user -u myagent.service -n 200 --no-pager
```

**Mientras debugueas, evitar el loop:**
```bash
systemctl --user stop myagent.service
```

**Causas frecuentes.**
- Variable de entorno faltante (no se cargó `EnvironmentFile`).
- `WorkingDirectory` no existe.
- Plugin con bug que tira el proceso al iniciar.

## El bot está online pero ignora mensajes

**Síntoma.** Discord/Telegram muestra el bot conectado, no responde.

**Causas posibles.**

1. **No estás en allowlist.** Verificar `$CLAUDE_CONFIG_DIR/channels/<canal>/access.json`. Tu user_id o nombre debe estar en `users` o `user_ids`.
2. **Token incorrecto.** Logs muestran `401 Unauthorized` o `invalid token`.
3. **Plugin no cargado.** `settings.json` debe tener `enabledPlugins.<canal>@claude-plugins-official: true`. Restart después de editar.
4. **Falta `--channels` en `ExecStart`.** El plugin está instalado pero no escucha eventos.
5. **Discord: intent "Message Content" no activado** en el developer dashboard.

Diagnóstico rápido:
```bash
journalctl --user -u myagent.service -n 100 | grep -iE "discord|telegram|auth|denied"
```

## Rate limit

**Síntoma.** `429 Too Many Requests` o degradación de respuesta.

**Causa.** Saturaste el cupo diario de la cuenta. Heartbeats demasiado frecuentes son la causa más común.

**Fix.** Bajar la cadencia. Tabla en [06-scheduling.md](06-scheduling.md). Recomendado: heartbeat cada 2–3h, Dream una vez por semana, reservar margen para webhooks.

## Memoria infla el context y rompe la sesión

**Síntoma.** Sesiones largas terminan con errores de context window o auto-compact agresivo.

**Causa.** `MEMORY.md` o entradas individuales crecieron sin caps.

**Fix.**
1. Aplicar caps duros (ver [07-memory.md](07-memory.md)).
2. Si una entrada genuinamente excede 32k, dividirla.
3. Correr Dream consolidate para detectar redundancias.

## Un cron de `CronCreate` no se ejecuta

**Síntomas y causas.**

1. **Saturaste el cupo diario.** El cron skipea silenciosamente. Bajar otras cargas o consolidar.
2. **Cron expression incorrecta.** Confundir DOM y DOW, mal `*/N` con N grande. Validar con [crontab.guru](https://crontab.guru/).
3. **Timezone.** Si el servidor está en UTC y necesitas hora local, ajustar la expression. `timedatectl` muestra el tz actual.
4. **`CronCreate` es session-only.** En muchas versiones del binario, `durable=true` se ignora silenciosamente y los crons mueren al reiniciar el servicio. Para reminders persistentes, usar `agent-cron` (ver [06-scheduling.md](06-scheduling.md)).

```bash
timedatectl | grep "Time zone"
sudo timedatectl set-timezone America/Mexico_City   # ejemplo
```

## "Not a git repository" al correr Dream

**Síntoma.** El skill `dream-consolidate` corre `git blame memory/MEMORY.md` y falla.

**Causa.** `$CLAUDE_CONFIG_DIR/projects/<id>/` no tiene git inicializado.

**Fix.** Ver setup en [07-memory.md](07-memory.md), sección "Versionado con git".

## El agente "se sale de carácter" en cron jobs

**Síntoma.** Una respuesta disparada por cron suena genérica, sin la voz definida en `SOUL.md`.

**Causa.** El `prompt` del cron es muy corto y no carga el ritual de bootstrap.

**Fix.** El `prompt` debe incluir explícitamente la lectura de archivos canon antes de la acción. Ejemplo bueno:

```
Lee BOOTSTRAP.md y SOUL.md. Después ejecuta el skill /morning-brief y reporta en tu voz.
```

Mal:

```
manda el brief
```

## `pip install` falla con "externally-managed-environment"

**Síntoma.**
```
error: externally-managed-environment
```

**Causa.** Ubuntu 24.04 marca el Python del sistema como externally-managed (PEP 668). `pip install --user` está bloqueado.

**Fix.** Crear venv aislado.
```bash
mkdir -p ~/.local/share/myagent-tools
python3 -m venv ~/.local/share/myagent-tools/venv
~/.local/share/myagent-tools/venv/bin/pip install <package>
```

`--break-system-packages` funciona pero no es recomendado.

## tmux: el servicio arranca pero `claude` no responde

**Síntoma.** `systemctl status` dice activo, pero el bot no reacciona.

**Diagnóstico.** Conectarse al tmux:
```bash
tmux -L myagent attach -t myagent
```

Mirar la salida de `claude`. Si el binario está esperando input (typical: prompt OAuth, prompt de permisos), `--dangerously-skip-permissions` no se aplicó o `skipDangerousModePermissionPrompt` está en false.

**Detach sin matar la sesión:** `Ctrl-b d`. NUNCA `Ctrl-c` — eso mata el proceso.

## Cómo pedir ayuda

Si nada de lo anterior aplica, abrir issue con:

- Output de `journalctl --user -u myagent.service -n 200`.
- Output de `systemctl --user show myagent.service -p Environment -p ExecStart`.
- `claude --version` y `node --version`.
- Distribución (`lsb_release -a`).

Para problemas del binario `claude` o connectors de claude.ai en sí, los canales oficiales de Anthropic son más rápidos.
