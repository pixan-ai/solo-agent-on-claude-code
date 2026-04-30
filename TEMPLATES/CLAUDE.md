# CLAUDE.md — proyecto {{PROJECT_NAME}}

> Plantilla opcional. Reglas de proyecto que `~/.claude/CLAUDE.md` global no cubre.
> Claude Code lo carga automáticamente cuando arranca en este `WorkingDirectory`.

## Convenciones del proyecto

- {{Lenguaje predominante: Python 3.12, TypeScript con Bun, Go 1.22, etc.}}
- {{Indentación / formatter: ej. "ruff format, no black"}}
- {{Test framework: ej. "pytest, nothing else"}}
- {{Commit convention: ej. "Conventional Commits con scopes"}}

## Reglas operativas específicas

- **Antes de tocar `production/`,** abrir PR. Nunca push directo a main.
- **Commits van como** `{{git-bot-user}}` (no como el operador humano).
- **Secrets viven en** `{{path}}` con permisos 600. NUNCA en código versionado.

## Cuándo NOT trigger ciertas skills

- En este proyecto, NO uses skill `<X>` porque {{razón específica}}.

## Stack notas

- {{librería peculiar 1}}: {{lo que tienes que saber}}.
- {{integración delicada}}: {{regla operativa}}.

## Antes de mergear

Checklist mínimo:

- [ ] Tests pasan: `{{comando}}`.
- [ ] Lint pasa: `{{comando}}`.
- [ ] CHANGELOG actualizado si feature.
- [ ] PR description con before/after si toca UI.

## Lo que NO va aquí

- Reglas globales de Claude Code (van en `~/.claude/CLAUDE.md`).
- Personalidad del agente (va en `SOUL.md`).
- Tareas recurrentes (van en `HEARTBEAT.md`).
- Memoria de proyecto (va en `memory/project_*.md`).

`CLAUDE.md` es para reglas que aplican a este código en este directorio.
