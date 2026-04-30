# 07 — Heartbeat / Cron / Dream

Tres ciclos temporales que mantienen al agente vivo, observador, y consistente. Cada uno tiene su propósito y NO se mezclan.

| Ciclo | Cadencia | Cuándo se usa | Costo (runs MAX) |
|-------|----------|---------------|------------------|
| **Heartbeat** | cada N min/h, en sesión activa | tareas evaluables que pueden ignorarse | ❌ no cuenta |
| **Cron** (`CronCreate`) | timestamp exacto / cron expression | recordatorios de tiempo, jobs programados | ✅ cuenta hacia 15/24h |
| **Dream** (semanal típico) | 1x/semana | consolidar memoria, propuestas a SOUL/USER | ✅ cuenta como cron |

## Heartbeat

El **heartbeat** es la sesión actual del agente revisando `HEARTBEAT.md` periódicamente. NO consume runs porque no es un proceso nuevo — es la misma sesión despertando con `ScheduleWakeup` o reaccionando a un signal.

### Patrón canónico de tres fases

Skill `heartbeat-pulse` lo formaliza:

#### Fase 1 — Decidir (skip vs run)

Por cada tarea `[ ]` en HEARTBEAT.md:

1. ¿La cadencia aplica ahora? (`cada tick` siempre, `1x día` solo si no corrió hoy, `cuándo: builder hours` solo entre rangos definidos)
2. ¿La condición de disparo se cumple? (e.g. "al detectar PR nuevo" → verificar antes de actuar)
3. ¿Hay algo `[~]` (en progreso) que bloquee re-disparo de esta misma tarea?

Si ninguna pasa los tres filtros → **skip silencioso**. No reportes a ningún canal. Sale.

#### Fase 2 — Ejecutar

Por cada tarea elegible:

1. Marcarla `[~]` antes de empezar.
2. Ejecutar la acción.
3. Capturar resultado: `OK` / `anomaly` / `decision_needed` / `error`.
4. Marcarla de vuelta `[ ]` (sigue activa) o `[x]` (one-shot terminada).

#### Fase 3 — Evaluar antes de notificar

| Resultado | Acción |
|-----------|--------|
| `OK` | **No notificar.** Silencio. |
| `anomaly` | Notificar: qué, severidad, propuesta. |
| `decision_needed` | Notificar: contexto + 2-3 opciones + voto. |
| `error` | Notificar solo si crítico. Si es transitorio, log y reintentar. |

**Esta fase es la diferencia entre un bot ruidoso y uno respetuoso.** Un agente que reporta "tick OK, nada que reportar" cada hora es ruido. Uno que solo despierta cuando hay algo accionable es señal.

### Filtros de no-deliverable

Antes de notificar, aplicar `evaluator-self-check`. Lista negra de patrones leak:

- "couldn't produce a final answer"
- referencias a archivos internos: "HEARTBEAT.md", "SOUL.md", "AGENTS.md"
- "judgment call:", "decision logic", "valid options are"
- "my instructions", "i am supposed to"

Esos son síntomas del modelo auto-narrándose. Reescribir o suprimir.

### HEARTBEAT.md formato

```markdown
# HEARTBEAT — tareas activas

Formato: lista de checkboxes. Cada tick revisa con tres fases.

- `[ ]` activa — heartbeat decide si ejecuta
- `[~]` en progreso (no re-disparar)
- `[x]` completada — limpieza diaria

---

## Activas

- [ ] **server-check** | skill: server-check | cadencia: cada 4h | ventana: 24/7 | reporta solo anomalía
- [ ] **email-triage** | skill: email-triage | cadencia: 2h | ventana: builder hours | diff vs anterior
- [ ] **calendar-conflicts** | skill: calendar-conflicts | cadencia: 1x día 6:30am | silencio si limpio
- [ ] **fail2ban-watch** | skill: fail2ban-watch | cadencia: 1x día 8:00am | reporta IPs nuevas

---

## Histórico (limpiar 1x mes)

- [x] (one-shots completadas)
```

### Cadencia recomendada

Diseña la frecuencia del heartbeat según presupuesto de runs. Para MAX (15/24h):

- Heartbeat cada 2h (12 ticks/día) → margen de 3 runs/día para webhooks/cron extras.
- Heartbeat cada 3h (8 ticks/día) → margen de 7 runs/día.

El heartbeat se dispara con `ScheduleWakeup` (cuenta hacia los 15) o con `CronCreate` recurrente (también cuenta).

---

## Cron

Para timestamps exactos o jobs recurrentes que NO se pueden expresar como condición evaluable.

### Cuándo usar Cron

| Caso | Ejemplo |
|------|---------|
| Reminder one-shot exacto | "Mañana 9am, recuérdame llamar a X" |
| Reminder recurrente con timestamp duro | "Todos los lunes 7am, mándame el morning brief" |
| Job nocturno fuera de ventana de chat | "3am, limpiar archivos `[x]` viejos en HEARTBEAT.md" |

### Cuándo NO usar Cron — usar HEARTBEAT.md

| Caso | Por qué a HEARTBEAT, no Cron |
|------|------------------------------|
| Verificación que puede esperar al próximo tick | El heartbeat ya se dispara solo |
| Condición evaluable, no de tiempo | "Cuando el PR X se mergee" |
| Reporte que solo aplica a veces | El heartbeat filtra solo |

**Regla:** si se puede expresar como condición → HEARTBEAT.md (no consume runs). Si requiere timestamp duro → Cron (consume).

### CronCreate

Tool del harness Claude Code:

```python
CronCreate(
  name="morning-brief",
  schedule="0 7 * * 1-5",  # lunes-viernes 7am
  prompt="ejecuta /morning-brief y reporta",
  user_id=...,
)
```

Variantes según harness exact. Lee la doc del binario (`claude --help` y subcomandos).

### Anti-patterns

- **Reminders en MEMORY.md.** No dispara nada. Si ves "Recuérdame X" en una memoria, es un fantasma — muévelo a Cron o HEARTBEAT.
- **Cadencia muy fina.** Heartbeat cada 30 min con MAX = 48 runs/día = saturas el cupo. Mínimo razonable: 90 min, recomendado 2-3h.
- **Cron sin `Restart` en el prompt.** El cron lanza una sesión nueva del agente; debe leer SOUL/USER/MEMORY como en el bootstrap. Si tu prompt es solo "manda email", el agente puede salirse de carácter.

---

## Dream

Job semanal (típico domingo 22:00 o lunes 04:00) que consolida memoria. Skill `dream-consolidate`.

### Por qué Dream

- La memoria acumula entradas durante la semana — algunas redundantes, otras obsoletas, algunas contradictorias.
- SOUL.md y USER.md NO se editan en vivo (son canon del operador).
- El operador no debería estar revisando memoria a mano cada semana — el agente lo hace y propone.

### Flujo

#### Phase 1 — Análisis

1. **Pre-step:** `dream-blame-staleness` — anotar líneas de MEMORY.md con `← Nd` (días desde último commit) cuando >14d. SOUL/USER nunca se anotan.
2. Leer todas las memorias en `memory/*.md`.
3. Por cada archivo:
   - ¿Hay info contradictoria con observaciones recientes?
   - ¿Hay info redundante con SOUL/USER/CLAUDE.md?
   - ¿Hay patrones que se repitieron 3+ veces y no están registrados?
   - ¿Hay memorias viejas que ya no se confirman?
4. Output: marcas `[FILE]` (agregar), `[FILE-REMOVE]` (quitar), `[SKILL]` (proponer skill nueva).

#### Phase 2 — Aplicar lo propio

Sin pedir permiso, el agente puede:

- Reorganizar memorias por tema.
- Actualizar `IDENTITY.md` y `BOOTSTRAP.md` con aprendizajes.
- Limpiar `HEARTBEAT.md` `[x]` viejos.
- Crear nuevas entradas que cumplan criterio "vale la pena guardar".

**Reglas duras:**
- Nunca editar SOUL.md o USER.md directo.
- Nunca borrar memoria sin archivar (`memory/_archive/`).

#### Phase 3 — Proponer al operador

Si hay hallazgos para SOUL/USER, escribir `memory/proposals/dream-{fecha}.md` con:

- Cambios propuestos a SOUL.md (con razón).
- Cambios propuestos a USER.md (con razón).

Notificar: "Dream listo. {N} propuestas — link al diff." Esperar `apply` / `discard`.

#### Phase 4 — Auto-commit

Después de Phase 2, commit estructurado al repo de memoria:

```
dream: 2026-04-30T23:00, 4 changes

phase1_summary: 3 entradas marcadas viejas, 1 contradicción detectada
phase2_actions:
- updated memory/feedback_X.md
- archived memory/feedback_old.md → memory/_archive/
- created memory/project_new.md
- updated MEMORY.md index
proposals_for_alfredo: 1 (SOUL.md tweak)
```

`git revert <sha>` para deshacer un Dream completo si no late.

### Caps duros (anti-context-bloat)

Antes de cargar memoria al prompt de Phase 1, aplicar caps:

| Constante | Valor | Aplica a |
|-----------|-------|----------|
| `MEMORY_FILE_MAX_CHARS` | 32 000 | preview de MEMORY.md |
| `SOUL_FILE_MAX_CHARS` | 16 000 | preview de SOUL.md |
| `USER_FILE_MAX_CHARS` | 16 000 | preview de USER.md |
| `HISTORY_ENTRY_HARD_CAP` | 64 000 | emergency cap por entrada de history |
| `HISTORY_ENTRY_PREVIEW_MAX_CHARS` | 4 000 | preview de cada entrada |

Si excede, truncar con marca `… [truncado: N chars elididos]`.

### Cadencia recomendada

- **Cron semanal:** `0 22 * * 0` (domingo 22:00) o `0 4 * * 1` (lunes 04:00).
- **Trigger manual:** "haz dream" o "consolida memoria".

Más frecuente que semanal es ruido (la memoria no se mueve tanto). Menos frecuente que cada 2 semanas pierde la oportunidad de detectar deriva.

### Origen

Patrón Dream adoptado de [hkuds/nanobot](https://github.com/hkuds/nanobot) — `nanobot/agent/memory.py:Dream`. Adaptado a Claude Code (sin Python loop, sin two-stage agent runner — un solo flujo conversacional).

---

## Cómo se conectan los tres

```
                ┌─────────────────────┐
                │  CronCreate (15/24h) │
                │  hard timestamps     │
                │  consumes runs      │
                └─────────┬───────────┘
                          │
                          ▼
                  ScheduleWakeup
                          │
                          ▼
                ┌─────────────────────┐
                │  Heartbeat (current  │
                │  session, evaluates  │
                │  HEARTBEAT.md)      │
                │  free               │
                └─────────┬───────────┘
                          │
            (anomaly/decision/error/deliverable)
                          │
                          ▼
                ┌─────────────────────┐
                │  Channel reply       │
                │  (Discord/Telegram)  │
                └─────────────────────┘

       ─── separado, una vez por semana ───

                ┌─────────────────────┐
                │  Cron Dream weekly   │
                │  consumes 1 run/wk   │
                └─────────┬───────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │  Dream consolidate   │
                │  - blame staleness   │
                │  - phase 1 análisis  │
                │  - phase 2 aplicar   │
                │  - phase 3 proponer  │
                │  - auto-commit       │
                └─────────────────────┘
```

Tres ciclos, un agente, presupuesto de runs respetado.
