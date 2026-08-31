# HEARTBEAT — tareas activas

Lista de checkboxes que el agente revisa cada tick del heartbeat. Estados:

- `[ ]` activa — el heartbeat decide si ejecuta según cadencia y condición.
- `[~]` en progreso — no re-disparar mientras esté así.
- `[x]` completada — limpieza periódica.

Formato de cada entrada:

```
- [ ] descripción | skill: {nombre} | cadencia: {cada N / 1x día / al detectar X} | ventana: {24/7 / horario operador / etc.} | reporte: {silencio si OK / siempre / diff vs anterior}
```

## Activas

- [ ] **server-check** | skill: server-check | cadencia: cada 4h | ventana: 24/7 | reporte: silencio si OK
- [ ] **email-triage** | skill: email-triage | cadencia: cada 2h | ventana: builder hours | reporte: diff vs anterior
- [ ] **calendar-conflicts** | skill: calendar-conflicts | cadencia: 1x día 06:30 | reporte: silencio si limpio
- [ ] **fail2ban-watch** | skill: fail2ban-watch | cadencia: 1x día 08:00 | reporte: nuevas IPs

## Histórico

> One-shots completadas. Limpieza periódica.

- [x] (vacío)
