---
name: agent-cron
description: Reminders persistentes via systemd --user timers. One-shot ("a las 9pm") o recurrentes ("Mon-Fri 7am"). Sobreviven restart del agente y reboot del server. Reemplazo robusto del CronCreate session-only del harness.
allowed-tools: Bash, Read
---

# agent-cron

Crea, lista y borra timers persistentes de **systemd --user**. Diseñado como reemplazo del `CronCreate` del harness Claude Code, que en muchos setups es session-only y muere cuando reinicias el agente.

## Por qué este skill (vs CronCreate del harness)

| | `CronCreate` del harness | `agent-cron` (este skill) |
|---|---|---|
| Persistencia | session-only en muchos setups, `durable=true` se ignora | persistente garantizado |
| Sobrevive restart agente | ❌ | ✅ |
| Sobrevive reboot del server | ❌ | ✅ |
| Logs persistentes | ❌ | ✅ via `journalctl --user -u <unit>` |
| Auto-expira en 7 días | ✅ (sin avisar) | ❌ vive hasta que la borres |
| Sintaxis | cron 5 campos | cron OnCalendar (más legible) |
| Validación de tiempo | implícita | `systemd-analyze calendar` real |
| Costo de runs MAX | ✅ cuenta hacia 15/24h | ❌ no cuenta (no dispara sesión nueva) |

`CronCreate` sigue siendo útil para reminders dentro de **una conversación interactiva**. Para reminders robustos que sobrevivan al ciclo de vida del agente, **usa este skill**.

## Cuándo aplica

- "Recuérdame X mañana 9am" → one-shot.
- "Cada lunes a las 7am, ejecuta morning-brief" → recurrente.
- "El día 1 de cada mes, manda el reporte mensual" → recurrente.
- Cualquier mensaje a Discord/Telegram, llamada a script local, o trigger de skill que requiera timing exacto.

## Cuándo NO aplica

- Decisiones que pueden expresarse como condición (no de tiempo): usa `HEARTBEAT.md`. Ej: "cuando el deploy de X termine".
- Reminders muy frecuentes (>1/min): cron del SO o systemd timer directo, no esto.
- Tareas que necesitan estado complejo entre runs: armar un servicio dedicado.

## Patrón canónico

### One-shot

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
  --at "2026-04-30 21:00:00" \
  --command "curl ..." \
  --name "review-deploy"
```

`--at` acepta ISO-8601 (`YYYY-MM-DD HH:MM:SS`). El timer se autoborra después de disparar (`ExecStartPost` lo desinstala).

### Recurrente

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
  --on-calendar "Mon..Fri 09:00" \
  --command "..." \
  --name "morning-brief"
```

`--on-calendar` acepta cualquier expresión válida de systemd OnCalendar. Ejemplos:
- `Mon..Fri 09:00` — lun-vie 9am.
- `*-*-1 12:00` — primer día de cada mes a las 12pm.
- `*:0/15` — cada 15 minutos.
- `Sat,Sun 22:00` — sábados y domingos a las 10pm.

Verifica con `systemd-analyze calendar "<spec>"` si tienes duda.

### Con secrets (env file)

Cuando el comando necesita variables de entorno con secrets (tokens, API keys):

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
  --at "2026-05-01 07:00:00" \
  --command 'curl -s "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" -d "chat_id=...&text=..."' \
  --env-file ~/.env.global \
  --name "morning-ping"
```

`--env-file` se inyecta como `EnvironmentFile=` del `.service` generado. El comando ya tiene las vars en su entorno cuando systemd lo ejecuta. **NUNCA hardcodear el token en `--command` literal** — quedaría en plano en el .service file.

### Listar

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py list
```

Muestra cada timer activo con su próximo disparo. `--short` omite la línea del comando.

### Borrar

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py rm <name>
```

Hace `systemctl --user disable --now`, borra ambos archivos `.timer` y `.service`, recarga.

## Anatomía del .service generado

```ini
[Unit]
Description=agent-cron task: review-repo-9pm
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/home/user/.env.global   ← solo si --env-file
ExecStart=/bin/bash -c 'curl ...'
ExecStartPost=/bin/bash -c 'systemctl --user disable .timer; rm -f .timer .service'
                                                               ↑ solo en one-shot
```

Y el `.timer`:

```ini
[Unit]
Description=agent-cron timer: review-repo-9pm

[Timer]
OnCalendar=2026-04-30 21:00:00
Persistent=false                ← true si recurring
AccuracySec=1s                  ← 1min si recurring
Unit=agent-cron-review-repo-9pm.service

[Install]
WantedBy=timers.target
```

`Persistent=true` en recurrentes hace que dispare missed runs si el server estuvo offline cuando tocaba. `Persistent=false` en one-shots evita que dispare tarde si pasaste la hora ya.

## Naming

Cada timer va prefijado `agent-cron-<name>`. El `<name>` se sluggifica (lowercase, no-alfanumérico → `-`). Si omites `--name`, se genera con timestamp + uuid corto.

## Validación

Antes de escribir los unit files, el script corre `systemd-analyze calendar <spec>` para validar la expresión. Si rechaza, error claro. Esto evita timers silenciosamente nunca-disparando por sintaxis mala.

## Anti-patterns

- **Hardcodear secrets en `--command`.** Usa `--env-file`.
- **Crear timers para flujos cortos** (< 5 min) — usa `sleep` directo o el harness.
- **Olvidarse de borrar timers obsoletos.** Recurrentes viven indefinidamente. Lista periódicamente con `list` y poda.
- **Usar `--at` para "en X minutos"** — solo acepta ISO absoluto. Para offset, calcula el target en tu shell: `date -d "+5 minutes" "+%Y-%m-%d %H:%M:%S"`.
- **Suponer que el comando corre en el cwd del workspace.** systemd-user services arrancan en home del usuario por default. Si el comando depende de cwd, agrega `cd /path && ...` al inicio.

## Ejemplo end-to-end: reminder de las 9pm

Caso real (2026-04-30):

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
  --at "2026-04-30 21:03:00" \
  --command 'curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_CCKEYBOT_TOKEN}/sendMessage" --data-urlencode "chat_id=7183589410" --data-urlencode "text=Hora de revisar el repo"' \
  --env-file ~/.env.global \
  --name "review-repo-9pm"
```

A las 21:03:00 CDMX, el timer dispara, systemd carga `~/.env.global`, expande `${TELEGRAM_CCKEYBOT_TOKEN}`, manda el mensaje, y se autodestruye. Sin involucrar al agente.

## Logs de cada job

```bash
journalctl --user -u agent-cron-<name>.service -n 50
```

Si el job falló, ahí está el error. Útil para debuggear curl con tokens mal escapados, comandos con paths relativos, etc.

## Origen y diferenciación

Este patrón es el **diferenciador del repo público `solo-agent-on-claude-code`**. Ni nanobot real ni Claude Code stock lo expone como skill. El insight clave: para un agente que debe sobrevivir restarts y reboots, el cron **no puede vivir dentro del agente** — debe vivir en el sistema (systemd) que ya gestiona el ciclo de vida del agente mismo.

## Referencias

- systemd-analyze calendar: https://www.freedesktop.org/software/systemd/man/systemd.time.html
- systemd timer units: https://www.freedesktop.org/software/systemd/man/systemd.timer.html
- OnCalendar syntax: https://www.freedesktop.org/software/systemd/man/systemd.time.html#Calendar%20Events
