# 04 — Skills

Skills son rutinas modulares que Claude Code descubre desde `.claude/skills/`. Cada skill es un directorio con un `SKILL.md` y opcionalmente `scripts/` y `references/`.

## Anatomía

```
.claude/skills/<kebab-name>/
├── SKILL.md            obligatorio
├── scripts/            opcional — código ejecutable
└── references/         opcional — documentación cargable on-demand
```

`SKILL.md` empieza con frontmatter YAML:

```yaml
---
name: kebab-case-name
description: Una línea — cuándo usar, qué hace, qué NO hace si tiene dual.
allowed-tools: Bash, Read, Edit
---
```

| Campo | Función |
|-------|---------|
| `name` | Identificador. Kebab-case, único, ≤ 64 chars. |
| `description` | Lo que Claude Code usa para decidir si la skill aplica. Empieza con verbo concreto. Incluye disparador y alcance. |
| `allowed-tools` | Restringe qué tools puede invocar la skill. Omitir hereda el contexto. |

El body sigue una estructura predecible:

```markdown
# nombre

Una o dos líneas que reiteran el `description`.

## Cuándo aplica
- ...

## Cuándo NO aplica
- ...

## Patrón
{procedimiento, pseudocódigo, o invocación de script}

## Anti-patterns
- ...
```

## Tres niveles de carga

1. **Frontmatter** — siempre cargado. ~100 palabras por skill. Es lo que Claude Code lee para decidir si la skill aplica.
2. **Body de `SKILL.md`** — cargado cuando la skill se invoca. Mantenerlo bajo 500 líneas.
3. **`scripts/` y `references/`** — leídos on-demand. Cuando el body se acerca a 500 líneas, mover detalle a `references/<topic>.md` y referenciar desde `SKILL.md`.

## Cuándo escribir una skill

| Forma del conocimiento | Dónde vive |
|------------------------|------------|
| Pasos repetibles con disparador claro, > 2 invocaciones esperadas | skill |
| Regla de comportamiento que aplica siempre | `memory/feedback_*.md` |
| Dato puntual (chat ID, ruta, identificador) | `memory/reference_*.md` |
| Estado de un proyecto en curso | `memory/project_*.md` |
| Convención del repo | `CLAUDE.md` |

Dos preguntas guía:

1. ¿Tiene un trigger discreto? ("cuando llegue un audio", "cada hora") → skill.
2. ¿Aplica en background sin trigger? ("siempre uso este tono") → memoria de feedback.

## `description` como contrato

Es el campo de mayor impacto. Claude Code lo usa para matching automático. Ejemplos:

- Vago: `"Hace cosas con email"` — no triggea de forma confiable.
- Concreto: `"Identifico mails que requieran respuesta. Solo lectura, nunca escribo ni draftear."` — triggea cuando aplica, NO triggea cuando no.

Si no puedes escribir el `description` en una oración antes de empezar, probablemente no entiendes la skill todavía.

## Niveles de libertad según riesgo

| Tipo de tarea | Forma del SKILL.md |
|---------------|---------------------|
| Múltiples enfoques válidos según contexto | texto narrativo con principios |
| Patrón preferido pero acepta variación | pseudocódigo o script con flags |
| Operación frágil con una sola secuencia válida | script ejecutable con pasos numerados |

Un puente angosto necesita barandales (script). Un campo abierto deja al agente elegir ruta (texto).

## Lo que no va en una skill

- README, INSTALLATION, QUICK_REFERENCE, CHANGELOG. La skill no es un proyecto open-source independiente.
- Documentación retrospectiva ("decisiones de diseño", "evolución"). Eso vive en `git log`.
- Reglas universales de comportamiento. Esas van en `feedback_*.md` o `CLAUDE.md`.
- Audiencia humana. Tu lector es el agente. No "este skill es un archivo markdown".

## Skill incluido en este repo: `agent-cron`

`skills/agent-cron/` es el único skill versionado aquí. Implementa reminders persistentes vía `systemd --user` timers. Los detalles operativos están en su `SKILL.md`.

Es el único skill que viaja con este repo porque resuelve un problema concreto (`CronCreate` es session-only en muchos setups) con una utilidad genérica. Otros skills útiles para un agente —`heartbeat-pulse`, `evaluator-self-check`, `dream-consolidate`, `skill-creator`, etc.— son específicos del comportamiento de un agente y se construyen en cada workspace según necesidad. Ver [hkuds/nanobot](https://github.com/hkuds/nanobot) para inspiración de patrones equivalentes en otro runtime.

## Convenciones de archivos

- Scripts ejecutables: `chmod +x` y shebang. Si los invocas como `python3 script.py`, no aplica.
- Documentar argumentos del script en el `SKILL.md`, no solo en `--help`.
- Si la skill tiene origen externo (adoptado de otro proyecto), cita al final.
- Nombre del directorio = `name` del frontmatter, exacto.
