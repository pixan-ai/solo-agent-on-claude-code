# 08 — Memoria persistente

Cada sesión de Claude Code tiene un context window que se compacta al llenarse. Sin **memoria persistente externa**, el agente "olvida" cualquier observación que no quepa. Este documento define cómo se persiste lo que vale la pena recordar.

## Dónde vive

```
$CLAUDE_CONFIG_DIR/projects/<project-id>/memory/
├── MEMORY.md       ← índice (lista de entradas, una línea cada una)
├── feedback_*.md   ← reglas de comportamiento
├── project_*.md    ← estado de proyectos / capacidades
├── reference_*.md  ← datos puntuales (chat IDs, paths, etc.)
└── user_*.md       ← perfil del operador
```

`MEMORY.md` es **el único archivo siempre cargado** en el context. Las primeras ~200 líneas se inyectan al system prompt automáticamente. Por eso es un índice, no una memoria — apunta a archivos detallados.

## Cuatro tipos de memoria

Cada `*.md` lleva frontmatter con un `type:`. El tipo define cuándo se aplica:

### 1. `user`

Información sobre el operador: rol, preferencias, conocimiento, contexto profesional.

```markdown
---
name: User es ingeniero senior con foco en backend
description: Background técnico del operador para calibrar nivel de explicación
type: user
---
{contenido}
```

### 2. `feedback`

Guía de cómo trabajar — corrections o validations explícitas. Estructura recomendada:

```markdown
---
name: Regla X
description: Una línea cuándo aplica
type: feedback
---
La regla.

**Why:** {razón — incidente pasado o preferencia fuerte}

**How to apply:** {dónde/cuándo aplica}
```

### 3. `project`

Estado de iniciativas, decisiones, deadlines, capacidades activas. Decae rápido — se actualiza con frecuencia.

```markdown
---
name: Capacidad X disponible
description: Qué hace, desde cuándo, cómo invocar
type: project
---
{contenido + Why + How to apply}
```

### 4. `reference`

Punteros a recursos externos. Datos puntuales.

```markdown
---
name: Canal Discord principal
description: chat_id 1498... donde el agente reporta
type: reference
---
{el dato + cómo se usa}
```

## Qué NO va en memoria

- **Patrones de código, convenciones, arquitectura, paths.** Eso se deriva leyendo el proyecto.
- **Git history o quién cambió qué.** `git log` / `git blame` son autoritativos.
- **Soluciones de debugging.** El fix está en el código; el commit message tiene contexto.
- **Algo ya documentado en CLAUDE.md / SOUL.md / USER.md.**
- **Detalles efímeros de una conversación en curso.**

Estas exclusiones aplican incluso cuando el operador pide explícitamente "guarda esto". Si pide guardar una lista de PRs o un summary de actividad, pregunta qué fue **sorprendente** — eso es lo que vale guardar.

## Cómo se escribe una memoria nueva

Dos pasos:

### 1. Escribir el archivo

`memory/<type>_<topic>.md`:

```markdown
---
name: {nombre humano}
description: {una línea — usado para decidir relevancia}
type: {user/feedback/project/reference}
---

{contenido — para feedback/project, estructura: regla/hecho + **Why:** + **How to apply:**}
```

### 2. Indexar en MEMORY.md

`memory/MEMORY.md` (índice, sin frontmatter):

```
- [Título](archivo.md) — gancho de una línea
```

Mantén ese gancho corto (<150 chars) para que MEMORY.md quepa en context.

## Caps duros

Para que la memoria nunca rompa el context window:

| Cap | Valor | Aplica a |
|-----|-------|----------|
| `MEMORY_FILE_MAX_CHARS` | 32 000 | preview de MEMORY.md cargado al prompt de Dream |
| `SOUL_FILE_MAX_CHARS` | 16 000 | preview de SOUL.md |
| `USER_FILE_MAX_CHARS` | 16 000 | preview de USER.md |
| `HISTORY_ENTRY_HARD_CAP` | 64 000 | emergency cap por entrada |
| `HISTORY_ENTRY_PREVIEW_MAX_CHARS` | 4 000 | preview de cada entrada |
| `ARCHIVE_SUMMARY_MAX_CHARS` | 8 000 | resumen LLM de bloque consolidado |
| `RAW_ARCHIVE_MAX_CHARS` | 16 000 | dump fallback si LLM falla |

Si una memoria genuinamente excede 32k, divídela en archivos separados.

## Versionado con git

Recomendado: el directorio `memory/` (no `$CLAUDE_CONFIG_DIR` entero) está bajo git.

### Setup inicial

```bash
cd $CLAUDE_CONFIG_DIR/projects/<project-id>/

git init -b main
cat > .gitignore <<'EOF'
# Solo versionar memoria — sessions/jsonl son privadas y gigantes
*
!memory/
!memory/**
!.gitignore
EOF
git add .gitignore memory/
git -c user.name=agent -c user.email=agent@local commit -m "memory: initial snapshot"
```

### Auto-commit en Dream

Después de cada Dream Phase 2, commit con prefijo `dream:` y mensaje estructurado:

```
dream: 2026-04-30T22:00, 4 changes

phase1_summary: 2 entradas marcadas viejas, 1 contradicción
phase2_actions:
- updated memory/feedback_X.md
- archived memory/feedback_old.md → memory/_archive/
- created memory/project_new.md
- updated MEMORY.md index
proposals_for_alfredo: 1 (SOUL.md tweak — pendiente aprobación)
```

`git log --grep "^dream:"` muestra todos los Dreams. `git revert <sha>` deshace uno completo.

### Otros prefijos

- `memory:` — edición manual o automática fuera del flujo Dream.
- `session:` — modificación durante una conversación normal.
- `init:` / `setup:` — para los primeros commits.

Mantener prefijos te permite distinguir qué Dream cambió qué vs qué se editó a mano.

## `dream-blame-staleness`

Antes de Phase 1 de Dream, anotar líneas de MEMORY.md con su edad:

```bash
git blame --date=relative -- memory/MEMORY.md
```

Sufijo `← Nd` (N>14) marca línea para revisión.

**Regla cardinal:** la edad **NO es razón de eliminación**. Distinguir:
- **Hábitos / preferencias / rasgos de personalidad** — permanentes regardless de edad.
- **Eventos pasados resueltos** — sí candidatos a archivar.
- **Tracking superado** — sí candidatos.
- **Approaches superseded** — sí candidatos.

**SOUL.md y USER.md jamás se anotan.** Son canon, permanentes.

## Patrones recomendados

### Cuando una conversación valida una preferencia (no obvia)

→ Crear `feedback_<topic>.md` con `**Why:**` que cite el momento.

### Cuando se descubre un dato puntual reusable

→ `reference_<topic>.md`.

### Cuando se inicia un proyecto que va a durar > 1 semana

→ `project_<topic>.md`. Actualizar conforme avanza. Archivar al cerrar.

### Cuando el operador corrige un comportamiento

→ `feedback_<topic>.md` con la regla + por qué.

## Cuándo acceder memoria

- **Cuando parece relevante.** El frontmatter `description` guía relevancia.
- **Cuando el user referencia trabajo previo de otra sesión.**
- **Si el user pide explícitamente "recuerda" o "qué sabes de X".**
- **Antes de actuar en algo no trivial:** verificar si hay `feedback_*` que aplique.

**Si el user dice "ignora tu memoria":** no aplicas hechos memorizados, no citas, no comparas con memoria.

## Antes de recomendar desde memoria

Una memoria que cita un archivo, función o flag es una declaración del estado **al momento que se escribió**. Puede haber sido renombrado, removido, o nunca mergeado. **Antes de recomendarlo, verifica:**

- Si la memoria nombra un path: chequea que existe.
- Si nombra una función o flag: `grep` por ella.
- Si el user va a actuar sobre tu recomendación, verifica primero.

"La memoria dice que X existe" ≠ "X existe ahora".

## Memoria vs otras formas de persistencia

| Mecanismo | Cuándo |
|-----------|--------|
| **Memoria** (`memory/*.md`) | información útil **entre conversaciones** |
| **Plan** (TaskCreate/Update) | pasos de la conversación actual |
| **HEARTBEAT.md** | tareas recurrentes que se evaluan |
| **CronCreate** | jobs con timestamp duro |
| **CLAUDE.md** | reglas del proyecto siempre cargadas |

No los mezcles. Cada uno tiene su rol.
