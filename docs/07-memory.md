# 07 — Memoria persistente

Cada sesión de Claude Code tiene un context window que se compacta al llenarse. Sin memoria persistente externa, observaciones que no caben se pierden. Este documento describe cómo persistir lo que vale la pena recordar entre sesiones.

## Ubicación

```
$CLAUDE_CONFIG_DIR/projects/<project-id>/memory/
├── MEMORY.md         índice — una línea por entrada
├── feedback_*.md     reglas de comportamiento
├── project_*.md      estado de proyectos
├── reference_*.md    datos puntuales
└── user_*.md         perfil del operador
```

`<project-id>` es el path del workspace con barras reemplazadas por guiones, derivado por Claude Code cuando arranca con un `WorkingDirectory` dado. Inspeccionar `$CLAUDE_CONFIG_DIR/projects/` para ver el ID asignado.

`MEMORY.md` es el único archivo siempre cargado al system prompt (las primeras ~200 líneas se inyectan automáticamente). Por eso es un índice, no un repositorio — apunta a archivos detallados.

## Cuatro tipos

Cada `*.md` lleva frontmatter con un `type:`. El tipo guía cuándo se aplica.

### `user`

Información sobre el operador: rol, preferencias, conocimiento, contexto profesional.

```markdown
---
name: User es ingeniero senior con foco en backend
description: Background técnico del operador para calibrar nivel de explicación
type: user
---
{contenido}
```

### `feedback`

Guía de cómo trabajar — correcciones o validaciones explícitas. Estructura recomendada:

```markdown
---
name: Regla X
description: Una línea — cuándo aplica
type: feedback
---
La regla.

**Why:** {razón — incidente pasado, preferencia fuerte}

**How to apply:** {dónde y cuándo aplica}
```

### `project`

Estado de iniciativas, decisiones, deadlines, capacidades activas. Decae rápido — se actualiza con frecuencia.

```markdown
---
name: Capacidad X disponible
description: Qué hace, desde cuándo, cómo invocar
type: project
---
{contenido + Why + How to apply}
```

### `reference`

Punteros a recursos externos. Datos puntuales.

```markdown
---
name: Canal Discord principal
description: chat_id donde el agente reporta
type: reference
---
{el dato + cómo se usa}
```

## Qué no va en memoria

- Patrones de código, convenciones, arquitectura, paths. Eso se deriva leyendo el proyecto.
- Historia de git o quién cambió qué. `git log` / `git blame` son autoritativos.
- Soluciones de debugging. El fix está en el código; el commit message tiene contexto.
- Algo ya documentado en `CLAUDE.md`, `SOUL.md`, `USER.md`.
- Detalles efímeros de una conversación en curso.

Estas exclusiones aplican incluso cuando el operador pide guardar algo. Si la petición es "guarda esta lista de PRs" o "guarda este resumen", una respuesta más útil es preguntar qué fue *sorprendente* o *no obvio* — eso es lo que vale guardar.

## Cómo escribir una memoria

Dos pasos.

**1. Archivo nuevo.** `memory/<type>_<topic>.md`:

```markdown
---
name: {nombre humano}
description: {una línea — Claude Code la usa para decidir relevancia}
type: {user/feedback/project/reference}
---

{contenido — para feedback/project incluir Why y How to apply}
```

**2. Indexar.** `memory/MEMORY.md` (sin frontmatter):

```
- [Título](archivo.md) — gancho de una línea
```

Mantener el gancho corto (≤ 150 chars) para que `MEMORY.md` quepa en el preview de 200 líneas que se inyecta al prompt.

## Caps duros

Para que la memoria no rompa el context window:

| Cap | Valor | Aplica a |
|-----|-------|----------|
| `MEMORY_FILE_MAX_CHARS` | 32 000 | preview de `MEMORY.md` |
| `SOUL_FILE_MAX_CHARS` | 16 000 | preview de `SOUL.md` |
| `USER_FILE_MAX_CHARS` | 16 000 | preview de `USER.md` |
| `HISTORY_ENTRY_HARD_CAP` | 64 000 | emergencia por entrada |
| `HISTORY_ENTRY_PREVIEW_MAX_CHARS` | 4 000 | preview por entrada |

Si una memoria excede 32k caracteres, dividirla en archivos separados.

## Versionado con git

Recomendado: `memory/` (no `$CLAUDE_CONFIG_DIR` entero) bajo git.

### Setup inicial

```bash
cd "$CLAUDE_CONFIG_DIR/projects/<project-id>/"
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

### Prefijos de commit

| Prefijo | Significado |
|---------|-------------|
| `dream:` | Phase 2 de Dream consolidate. Estructurado, automático. |
| `memory:` | Edición fuera del flujo Dream. |
| `session:` | Modificación durante una conversación normal. |
| `init:` / `setup:` | Primeros commits. |

`git log --grep "^dream:"` muestra todas las consolidaciones. `git revert <sha>` deshace una iteración completa.

### Auto-commit en Dream

Después de cada Phase 2, commit estructurado:

```
dream: 2026-04-30T22:00, 4 changes

phase1_summary: 2 entradas marcadas viejas, 1 contradicción detectada
phase2_actions:
- updated memory/feedback_X.md
- archived memory/feedback_old.md → memory/_archive/
- created memory/project_new.md
- updated MEMORY.md index
proposals_for_operator: 1 (SOUL.md tweak — pendiente aprobación)
```

## Antigüedad y relevancia

`git blame --date=relative -- memory/MEMORY.md` muestra cuánto tiempo lleva cada línea sin ediciones. Útil como input para Dream Phase 1, no como criterio único de eliminación. Distinguir:

- **Hábitos / preferencias / rasgos permanentes** — relevantes regardless de antigüedad.
- **Eventos pasados resueltos** — candidatos a archivar.
- **Tracking superado** — candidatos a archivar.
- **Approaches reemplazados por otros mejores** — candidatos.

`SOUL.md` y `USER.md` nunca se anotan con antigüedad. Son canon.

## Cuándo acceder a memoria

- Cuando parece relevante. El frontmatter `description` guía la decisión.
- Cuando el operador referencia trabajo previo de otra sesión.
- Si el operador pide explícitamente "recuerda" o "qué sabes de X".
- Antes de actuar en algo no trivial: verificar si hay `feedback_*` que aplique.

Si el operador dice "ignora tu memoria": no aplicar hechos memorizados, no citar, no comparar contra memoria.

## Antes de actuar sobre memoria

Una memoria que cita un archivo, función o flag es una declaración del estado *al momento que se escribió*. Puede haber sido renombrado, removido, o nunca mergeado.

Antes de recomendar:

- Si la memoria nombra un path: chequear que existe.
- Si nombra una función o flag: `grep` por ella.
- Si el operador va a actuar sobre la recomendación: verificar primero.

"La memoria dice que X existe" no es lo mismo que "X existe ahora".

## Memoria vs otras formas de persistencia

| Mecanismo | Cuándo |
|-----------|--------|
| `memory/*.md` | información útil entre conversaciones |
| TaskCreate/Update | pasos de la conversación actual |
| `HEARTBEAT.md` | tareas recurrentes |
| `CronCreate` / `agent-cron` | timestamps duros |
| `CLAUDE.md` | reglas del proyecto siempre cargadas |

No mezclar. Cada uno tiene su rol.
