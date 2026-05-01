---
name: agent-cron
description: Reminders persistentes vía systemd --user timers. One-shot ("a las 9pm") o recurrentes ("Mon-Fri 7am"). Sobreviven restart del agente y reboot del servidor. Útil cuando CronCreate del harness no es persistente en tu setup.
allowed-tools: Bash, Read
---

# agent-cron

Crea, lista y borra timers de **systemd --user** desde una llamada de skill.
Útil cuando `CronCreate` del harness Claude Code es session-only en tu setup
(en muchas versiones, el flag `durable=true` se ignora silenciosamente y los
crons mueren al reiniciar el agente).

## Comparación

| | `CronCreate` (harness) | `agent-cron` |
|---|---|---|
| Persistencia | session-only en muchos setups | persistente |
| Sobrevive restart del agente | no | sí |
| Sobrevive reboot del servidor | no | sí |
| Logs persistentes | no | `journalctl --user -u <unit>` |
| Sintaxis | cron 5 campos | systemd `OnCalendar` |
| Validación | implícita | `systemd-analyze calendar` |
| Costo de runs Claude | consume cupo | no consume cupo |

`CronCreate` sigue siendo apropiado para reminders dentro de una sesión
interactiva. Para reminders que deben sobrevivir al ciclo de vida del agente,
`agent-cron` es más confiable.

## Cuándo aplica

- "Recuérdame X mañana 9am" → one-shot.
- "Cada lunes 7am, ejecuta morning-brief" → recurrente.
- "El día 1 de cada mes a las 12pm, reporte mensual" → recurrente.
- Cualquier mensaje a Discord/Telegram, llamada a script local, o trigger de
  skill que requiera timing exacto y persistencia.

## Cuándo no aplica

- La tarea se puede expresar como condición (no de tiempo): usar `HEARTBEAT.md`.
  Ejemplo: "cuando el deploy termine".
- Frecuencia muy alta (> 1/min): usar systemd timer directo, no este wrapper.
- Estado complejo entre runs: armar un servicio dedicado.

## Uso

### One-shot

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
    --at "2026-04-30 21:00:00" \
    --command "..." \
    --name "review-deploy"
```

`--at` acepta ISO-8601 (`YYYY-MM-DD HH:MM:SS`). El timer se autoborra después
de disparar.

### Recurrente

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
    --on-calendar "Mon..Fri 09:00" \
    --command "..." \
    --name "morning-brief"
```

`--on-calendar` acepta cualquier expresión válida de `OnCalendar` de systemd.
Ejemplos:

| Expresión | Cuándo dispara |
|-----------|----------------|
| `Mon..Fri 09:00` | lun-vie a las 9am |
| `*-*-1 12:00` | día 1 de cada mes a las 12pm |
| `*:0/15` | cada 15 minutos |
| `Sat,Sun 22:00` | sábados y domingos a las 10pm |

Validar con `systemd-analyze calendar "<spec>"`.

### Con secrets

Cuando el comando requiere variables de entorno con secrets (tokens, API
keys), pasar `--env-file`:

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
    --at "2026-05-01 07:00:00" \
    --command 'curl -s "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" -d "chat_id=...&text=..."' \
    --env-file ~/.env.global \
    --name "morning-ping"
```

`--env-file` se inyecta como `EnvironmentFile=` del `.service` generado. El
comando ya tiene las variables en su entorno cuando systemd lo ejecuta. NUNCA
hardcodear el token en `--command` literal — quedaría en plano en el archivo
de unidad.

### Listar

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py list
```

Muestra cada timer activo con su próximo disparo. `--short` omite la línea del
comando.

### Borrar

```bash
python3 .claude/skills/agent-cron/scripts/agent-cron.py rm <name>
```

Hace `systemctl --user disable --now`, borra los archivos `.timer` y
`.service`, recarga el daemon.

## Archivos generados

`.service`:

```ini
[Unit]
Description=agent-cron task: <name>
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=<path>          ; solo si --env-file
ExecStart=/bin/bash -c '<comando>'
ExecStartPost=...                ; solo en one-shot — autocleanup
```

`.timer`:

```ini
[Unit]
Description=agent-cron timer: <name>

[Timer]
OnCalendar=<spec>
Persistent=false                 ; true si recurrente
AccuracySec=1s                   ; 1min si recurrente
Unit=agent-cron-<name>.service

[Install]
WantedBy=timers.target
```

`Persistent=true` en recurrentes hace que dispare runs perdidos si el servidor
estuvo offline. `Persistent=false` en one-shots evita disparos tarde si pasaste
la hora.

## Validación previa

Antes de escribir los archivos, el script corre `systemd-analyze calendar
<spec>` para validar la expresión. Si rechaza, error claro. Esto evita timers
que silenciosamente nunca disparan por sintaxis mala.

## Naming

Cada timer va prefijado `agent-cron-<name>`. `<name>` se sluggifica
(lowercase, no-alfanumérico → `-`). Si omites `--name`, se genera con
timestamp + uuid corto.

## Logs

```bash
journalctl --user -u agent-cron-<name>.service -n 50
```

Útil para depurar `curl` con tokens mal escapados, comandos con paths
relativos, etc.

## Anti-patterns

- Hardcodear secrets en `--command`. Usar `--env-file`.
- Crear timers para flujos cortos (< 5 min): `sleep` directo o el harness son
  más simples.
- Olvidarse de borrar timers obsoletos. Recurrentes viven indefinidamente;
  podar con `list` periódicamente.
- Usar `--at` para "en X minutos": solo acepta ISO absoluto. Para offsets,
  calcular en shell: `date -d "+5 minutes" "+%Y-%m-%d %H:%M:%S"`.
- Asumir que el comando corre en el cwd del workspace. Los user services
  arrancan en el home por default. Si el comando depende de cwd, prefijar con
  `cd /path && ...`.

## Referencias

- `systemd.time(7)` — sintaxis OnCalendar:
  https://www.freedesktop.org/software/systemd/man/systemd.time.html
- `systemd.timer(5)`:
  https://www.freedesktop.org/software/systemd/man/systemd.timer.html
