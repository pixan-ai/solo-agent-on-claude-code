# HEARTBEAT — tareas activas

> Plantilla. Cada tick del heartbeat revisa este archivo siguiendo el patrón de tres fases (`.claude/skills/heartbeat-pulse/SKILL.md`).

Formato: lista de checkboxes.

- `[ ]` activa — el heartbeat decide si ejecuta
- `[~]` en progreso (no re-disparar)
- `[x]` completada — limpieza diaria

Formato de cada tarea:
`- [ ] {nombre} | skill: {ruta o nombre} | cadencia: {expr} | ventana: {24/7 | builder | weekday morning} | contexto: {qué reporta}`

---

## Activas

- [ ] **server-check** | skill: `.claude/skills/server-check/SKILL.md` | cadencia: cada 4h | ventana: 24/7 | contexto: salud del server (uptime, disco, RAM, load, servicios systemd críticos, journal errors). Reporta solo si hay anomalía.

- [ ] **email-triage** | skill: `.claude/skills/email-triage/SKILL.md` | cadencia: cada 2h | ventana: builder hours | contexto: identifica mails que requieran respuesta del operador. **Solo lectura** — nunca escribir ni draftear. Reporta diferencia vs tick anterior.

- [ ] **calendar-conflicts** | skill: `.claude/skills/calendar-conflicts/SKILL.md` | cadencia: 1x día | ventana: 6:30am | contexto: conflictos en próximos 3 días — doble booking, invasión builder, falta de buffers. Silencio si limpio.

- [ ] **fail2ban-watch** | skill: `.claude/skills/fail2ban-watch/SKILL.md` | cadencia: 1x día | ventana: 8:00am | contexto: bloqueos nuevos en sshd. Silencio si nada cambió.

- [ ] **momentum-weekly** | skill: `.claude/skills/momentum-weekly/SKILL.md` | cadencia: 1x semana | ventana: domingo 22:00 | contexto: vista de la semana — código, email, calendario, server. Siempre se entrega (es para dirección).

---

## Cron jobs propuestos

Para que estas tareas vivan, hacen falta los `CronCreate` correspondientes. Ejemplo:

| Cron | Cadencia | Tareas que dispara |
|------|----------|--------------------|
| `heartbeat-main` | cada 2h, 24/7 | server-check (cada 2 ticks), email-triage (en builder hours) |
| `morning-routine` | 1x día 6:30am L-V | calendar-conflicts |
| `morning-security` | 1x día 8:00am | fail2ban-watch |
| `weekly-momentum` | 1x semana domingo 22:00 | momentum-weekly |
| `weekly-dream` | 1x semana domingo 23:00 | dream-consolidate |

**Cuota estimada (MAX 15/24h):** 12 (heartbeat) + 1 (calendar) + 1 (fail2ban) + 0.14 (weekly) + 0.14 (dream) ≈ **14.3 runs/día**. Cabe con 0.7 slots libres para webhooks.

Si saturado, opciones:
- Heartbeat cada 3h (8 ticks/día) — pierde resolución de email-triage.
- Combinar calendar + fail2ban en un solo cron 7:00am.

---

## Histórico (limpiar 1x mes)

<!-- vacío al inicio -->
