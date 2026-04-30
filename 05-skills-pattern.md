# 05 — Patrón de skills

Las **skills** son el mecanismo principal para extender al agente con rutinas modulares. Cada skill es un folder con un `SKILL.md` (markdown con frontmatter) y opcionalmente `scripts/`, `references/`, `assets/`. Claude Code las descubre automáticamente desde `.claude/skills/`.

## Por qué skills (vs todo en SOUL/AGENTS)

- **Cargado on-demand.** Solo el frontmatter (~100 palabras por skill) está siempre en context. El body del SKILL.md se carga cuando la skill triggea. Esto te permite tener decenas de rutinas sin inflar el system prompt.
- **Modulares.** Una skill por rutina = una unidad versionable, editable sin tocar el resto.
- **Triggers automáticos.** El description del frontmatter le dice a Claude Code cuándo aplicar la skill. Bien escrito, dispara solo cuando toca.

## Anatomy

```
.claude/skills/<kebab-case-name>/
├── SKILL.md          ← obligatorio
└── (opcional)
    ├── scripts/      ← código ejecutable (Python/Bash/etc.)
    ├── references/   ← docs cargables on-demand
    └── assets/       ← templates/imagenes/fonts que el output usa
```

### `SKILL.md` — frontmatter

```yaml
---
name: kebab-case-name
description: Una línea concreta. Cuándo usar el skill, qué hace, qué NO hace si tiene dual.
allowed-tools: Bash, Read, Edit  # opcional, restringe lo que el skill puede invocar
---
```

| Campo | Reglas |
|-------|--------|
| `name` | kebab-case, < 64 chars, único, descriptivo. **No** `helper-1` o `mi-skill-bueno`. |
| `description` | El campo de mayor impacto. Claude Code lo usa para matching. Empieza con verbo o sustantivo concreto. Incluye **trigger** (cuándo aplica) y **scope** (qué cubre). |
| `allowed-tools` | Solo si quieres limitar (ej. `email-triage` solo lee, sin Write). Si omitas, hereda contexto. |

### `SKILL.md` — body

Sigue una estructura predecible:

```markdown
# {nombre}

{1-2 líneas que reiteren el description, en la voz del agente}

## Cuándo aplica

- {trigger 1}
- {trigger 2}

## Cuándo NO aplica

- {anti-trigger 1}
- {anti-trigger 2}

## Patrón canónico

{procedimiento paso a paso, o pseudocódigo, o invocación de script}

## Anti-patterns

- {error común 1}
- {error común 2}

## Origen (si aplica)

{atribución si vino de adopción externa}
```

## Progressive disclosure de tres niveles

1. **Metadata (frontmatter)** — siempre cargado, ~100 palabras. Es lo que Claude Code lee para decidir si la skill aplica.
2. **Body (SKILL.md)** — se carga al disparar, < 500 líneas idealmente.
3. **Bundled resources** (`scripts/`, `references/`) — se leen on-demand, ilimitado.

Si el body se acerca a 500 líneas, parte contenido a `references/<topic>.md` y desde SKILL.md di "para detalles de X, lee references/X.md".

## Grados de libertad acordes al riesgo

| Tipo de tarea | Grado | Forma |
|---|---|---|
| Múltiples enfoques válidos, decisión por contexto | **Alta libertad** | Texto narrativo con principios |
| Hay un patrón preferido pero acepta variación | **Media** | Pseudocódigo o scripts con flags |
| Operación frágil, una sola secuencia válida | **Baja** | Script ejecutable con pasos numerados |

Si el path es un puente angosto con precipicio, pones barandales (script). Si es un campo abierto, dejas elegir ruta (texto).

## Lo que NO va en una skill

- README.md
- INSTALLATION_GUIDE.md
- QUICK_REFERENCE.md
- CHANGELOG.md
- TODO.md, NOTES.md, IDEAS.md

La skill no es un proyecto open-source independiente. Es un set de instrucciones para el agente. Info auxiliar (cómo se construyó, decisiones de diseño retroactivas, changelog) **NO va**. Para evolución usa `git log`.

## Anti-patterns observados en producción

- **Description vaga.** "Hace cosas con email" ≠ "Identifica mails que requieran respuesta. Solo lectura". El primero no triggea automáticamente; el segundo sí.
- **Body que duplica el description.** El body es para detalle operativo, no para repetir lo que ya dice el frontmatter.
- **Scripts sin shebang ni `chmod +x`.** Si vas a ejecutar `python3 script.py`, está bien. Si quieres `./script.py`, lo necesita.
- **Mezclar narrativa con tabla.** Una sección de cuándo-aplica funciona mejor como tabla; filosofía como párrafos. No las cruces.
- **Documentar para humanos no familiarizados.** Tu audiencia es el agente. No digas "este skill es un archivo markdown".
- **Skills que se cubren con CLAUDE.md o memoria.** Si la regla es operativa-permanente (ej. "Telegram quieto, Discord verbose"), va a memoria de feedback. Si es flujo de pasos disparable, va a skill.

## Decisión: ¿skill o memoria?

| Forma del knowledge | Dónde |
|---|---|
| Pasos repetibles con triggers claros, > 2 invocaciones esperadas | Skill |
| Regla universal de comportamiento (siempre aplica) | `feedback_*.md` en memoria |
| Un dato puntual (chat_id, ruta, contraseña) | `reference_*.md` en memoria |
| Estado actual de un proyecto | `project_*.md` en memoria |
| Convención de cómo se hacen las cosas en este repo | CLAUDE.md, no skill |

Cuando dudas, dos preguntas:
1. ¿Tiene un trigger discreto? (ej. "cuando llegue audio") → skill.
2. ¿Aplica en background sin trigger explícito? (ej. "siempre uso este tono") → memoria.

## Workflow para crear una skill nueva

1. Pensar `name` y `description` PRIMERO. Si no puedes escribir un description en una oración, no entiendes la skill todavía.
2. `mkdir -p .claude/skills/<name>/`.
3. Escribir SKILL.md frontmatter + body. Mantener body bajo 500 líneas.
4. Si necesita scripts: `scripts/<name>.py` con `chmod +x` y docstring. Documenta args en SKILL.md.
5. Probar: invocar mentalmente "si Claude Code lee solo el description, ¿sabe cuándo dispararme?"
6. Si tiene origen externo (adoptado de otro proyecto), citar al final: "Origen: ..."

## Skills core que casi cualquier agente quiere

Plantillas y ejemplos de SKILL.md útiles para empezar. (Tu agente puede tener más o menos según foco.)

| Skill | Propósito |
|-------|-----------|
| `heartbeat-pulse` | Procesar HEARTBEAT.md con tres fases (skip / run / evaluate-before-notify). Ver `07-heartbeat-cron-dream.md`. |
| `evaluator-self-check` | Gate antes de notificar — lista negra de patrones leak. |
| `dream-consolidate` | Job semanal que revisa memoria y propone ajustes. |
| `dream-blame-staleness` | Anotar líneas de MEMORY con edad. |
| `skill-creator` | Meta-skill, este documento como skill cargable. |
| `ask-user-pattern` | Cuándo paro y pregunto vs decido. |
| `on-progress-edits` | Edición incremental en chat para flujos largos. |
| `server-check` | Health check del server. |
| `github-ops` | Operaciones git/PR como bot dedicado. |

Capacidades opcionales (`elevenlabs-tts`, `image-gen`, `video-vision`, etc.) en `09-optional-capabilities.md`.

## Ejemplo mínimo: una skill útil en 30 líneas

`.claude/skills/morning-brief/SKILL.md`:

```markdown
---
name: morning-brief
description: Genera reporte matutino con calendario del día, mails sin leer prioritarios, y top 3 PRs abiertos. Aplica solo si el user pide "morning brief" o si el cron 7am dispara.
allowed-tools: Read, Bash
---

# morning-brief

Reporte de arranque del día. 5 líneas máximo de salida.

## Cuándo aplica
- User dice "brief", "qué tengo hoy", "morning"
- Cron 07:00 lunes-viernes (configurar via CronCreate)

## Patrón

1. Calendario hoy (`mcp__claude_ai_Google_Calendar__list_events` start=today end=today+1)
2. Mails inbox sin leer prioritarios (`mcp__claude_ai_Gmail__search_threads` query="is:unread label:important")
3. PRs asignados a mí (`gh pr list --search "review-requested:@me"`)

## Output

```
☀ {fecha}
- Cal: {N} eventos. Próximo: {hora} {título}
- Mail: {N} importantes
- PR: {N} pendientes review (top: {título})
```

## Cuándo NO aplica
- Fines de semana (default off, override si user pide)
- Si el cron disparó pero ningún canal está activo (silencio)
```

Eso es todo. Frontmatter + 4 secciones. Deployable mañana.
