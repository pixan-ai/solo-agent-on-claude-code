# 06 — Scheduling

Tres mecanismos para "hacer algo en el futuro":

| Mecanismo | Cuándo se usa | Consume cupo Claude |
|-----------|---------------|---------------------|
| `HEARTBEAT.md` (heartbeat) | tareas evaluables que pueden saltarse | no — corre dentro de la sesión vigente |
| `CronCreate` (harness) | timestamp exacto, dentro de la sesión | sí |
| `agent-cron` (systemd timer) | timestamp persistente, sobrevive reboots | no — no dispara sesión Claude |
| `ScheduleWakeup` | pausa corta dentro de un loop dinámico | sí |
| `RemoteTrigger` | webhook externo | sí |

Los runs de `CronCreate`, `ScheduleWakeup` y `RemoteTrigger` comparten cupo. Verificar el límite vigente para tu plan; al momento de escribir, MAX permite 15/24h.

## Heartbeat

El heartbeat es la sesión actual del agente revisando `HEARTBEAT.md` periódicamente. No consume runs porque no abre una sesión nueva — es la misma sesión despertando con `ScheduleWakeup` o reaccionando a un trigger.

### Patrón de tres fases

Skill típico: `heartbeat-pulse`. Por cada tick:

#### Fase 1 — Decidir

Por cada tarea `[ ]` en `HEARTBEAT.md`:

- ¿La cadencia aplica ahora? (`cada tick` siempre, `1x día` solo si no corrió hoy, ventana horaria si la tarea la define).
- ¿La condición de disparo se cumple? (e.g. "al detectar PR nuevo" implica verificar primero).
- ¿Hay algo `[~]` (en progreso) que bloquee re-disparo de esta tarea?

Si ninguna tarea pasa los tres filtros → skip silencioso. No reportar.

#### Fase 2 — Ejecutar

Por cada tarea elegible:

- Marcar `[~]` antes de empezar.
- Ejecutar la acción.
- Capturar resultado: `OK` / `anomaly` / `decision_needed` / `error`.
- Marcar `[ ]` (sigue activa) o `[x]` (one-shot terminada).

#### Fase 3 — Evaluar antes de notificar

| Resultado | Acción |
|-----------|--------|
| `OK` | no notificar |
| `anomaly` | notificar: qué, severidad, propuesta |
| `decision_needed` | notificar: contexto + 2-3 opciones + recomendación |
| `error` | notificar solo si crítico; transitorio → log y reintentar |

La fase 3 es el filtro que separa un agente útil de un firehose. Lista negra de patrones que indican output no entregable (auto-narración del modelo, referencias a archivos internos, "couldn't produce a final answer") aplicada antes de cualquier notificación; la skill `evaluator-self-check` la encapsula.

### Formato de `HEARTBEAT.md`

```markdown
# HEARTBEAT — tareas activas

- [ ] **server-check** | skill: server-check | cadencia: cada 4h | reporta solo anomalía
- [ ] **email-triage** | skill: email-triage | cadencia: 2h | builder hours | diff vs anterior
- [ ] **calendar-conflicts** | skill: calendar-conflicts | cadencia: 1x día 6:30am
- [~] tarea-en-curso (no re-disparar)

## Histórico (limpieza periódica)
- [x] one-shot completada
```

### Cadencia

El heartbeat se dispara con `ScheduleWakeup` (consume runs) o con `CronCreate` recurrente (también consume). Para una cuenta con cupo 15/24h:

| Cadencia | Runs/día | Margen para webhooks |
|----------|----------|----------------------|
| 1h | 24 | excede |
| 90 min | 16 | sin margen |
| 2h | 12 | 3 |
| 3h | 8 | 7 |

Cadencias finas (< 60 min) saturan rápido. 2–3h es razonable para uso continuo.

## `CronCreate` (harness)

Tool del binario Claude Code para programar un run en un timestamp futuro o con cron expression.

```python
CronCreate(
  name="morning-brief",
  schedule="0 7 * * 1-5",
  prompt="Lee BOOTSTRAP.md y SOUL.md. Después ejecuta /morning-brief y reporta.",
)
```

Casos típicos:

| Caso | Ejemplo |
|------|---------|
| Reminder one-shot exacto | "Mañana 9am, manda este mensaje" |
| Recurrente con timestamp duro | "Lun-vie 7am, morning brief" |
| Job nocturno | "3am, limpia entradas `[x]` viejas" |

### Cuándo no usar `CronCreate`

- Si la tarea se puede expresar como condición evaluable, va a `HEARTBEAT.md` y el heartbeat la atiende sin gastar runs.
- Si necesita sobrevivir un restart del agente o reboot del servidor: `CronCreate` es session-only en muchas versiones del binario (el flag `durable=true` se ignora). Usa `agent-cron`.

### Salirse de carácter en cron jobs

Cuando un cron dispara, el agente arranca una sesión nueva. Si el `prompt` es solo "manda el brief", la sesión arranca sin haber leído `BOOTSTRAP.md` / `SOUL.md` / `USER.md` y puede responder con tono genérico. El `prompt` debe incluir explícitamente la lectura de los archivos canon antes de la acción.

## `agent-cron` (systemd timer)

Wrapper sobre `systemd --user` timers para reminders persistentes. Es el único skill incluido en este repo (`skills/agent-cron/`).

### Por qué existe

| | `CronCreate` del harness | `agent-cron` |
|---|---|---|
| Persistencia | session-only en muchos setups | persistente |
| Sobrevive restart del agente | no | sí |
| Sobrevive reboot del servidor | no | sí |
| Logs persistentes | no | `journalctl --user -u <unit>` |
| Sintaxis | cron 5 campos | systemd `OnCalendar` |
| Validación | implícita | `systemd-analyze calendar` |
| Costo | consume runs | no consume runs |

`CronCreate` sigue siendo útil dentro de una sesión interactiva del operador. Para cualquier reminder que deba sobrevivir al ciclo de vida del agente, `agent-cron` es más robusto.

### Uso

```bash
# One-shot
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
    --at "2026-04-30 21:00:00" \
    --command "..." \
    --name "review-deploy"

# Recurrente
python3 .claude/skills/agent-cron/scripts/agent-cron.py add \
    --on-calendar "Mon..Fri 09:00" \
    --command "..." \
    --name "morning-brief"

# Listar
python3 .claude/skills/agent-cron/scripts/agent-cron.py list

# Borrar
python3 .claude/skills/agent-cron/scripts/agent-cron.py rm <name>
```

Detalles —incluyendo el archivo `EnvironmentFile` para inyectar tokens sin hardcodearlos en el comando— en `skills/agent-cron/SKILL.md`.

## Dream

Patrón opcional de consolidación de memoria. Un cron semanal corre un skill `dream-consolidate` que:

1. Lee toda la memoria, anota antigüedad, detecta redundancias y contradicciones.
2. Aplica cambios "ligeros" autónomamente: reorganizar memorias por tema, archivar entradas obsoletas, crear nuevas que cumplen el criterio "vale la pena guardar".
3. Propone cambios "pesados" (a `SOUL.md` o `USER.md`) al operador para aprobación explícita.
4. Auto-commitea con prefijo `dream:` para que `git revert` deshaga una iteración completa.

`SOUL.md` y `USER.md` nunca se editan en vivo. La separación previene deriva de personalidad por agregación silenciosa.

Cadencia recomendada: semanal (domingo 22:00 o lunes 04:00). Más frecuente es ruido — la memoria no cambia tanto. Menos frecuente pierde la oportunidad de detectar deriva.

Origen: el patrón Dream proviene de [hkuds/nanobot](https://github.com/hkuds/nanobot) (`agent/memory.py:Dream`). La adaptación a Claude Code es un único flujo conversacional en lugar del two-stage runner Python.

## Diagrama

```
                ┌──────────────────────┐
                │ ScheduleWakeup /     │
                │ CronCreate / Remote  │ ── consume runs
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │ Sesión Claude Code   │
                │   ↓                  │
                │   heartbeat-pulse    │
                │   (lee HEARTBEAT.md) │
                └──────────┬───────────┘
                           ▼
                  ¿anomalía/decisión/error?
                           ▼
                ┌──────────────────────┐
                │ reply al canal       │
                │ (Discord/Telegram)   │
                └──────────────────────┘

         ─── separado del heartbeat ───

                ┌──────────────────────┐
                │ agent-cron timer     │ ── no consume runs
                │ (systemd --user)     │
                └──────────┬───────────┘
                           ▼
                comando shell directo,
                no abre sesión Claude
```
