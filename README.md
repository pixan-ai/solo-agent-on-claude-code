# solo-agent-on-claude-code

Configuración de referencia para correr [Claude Code](https://docs.claude.com/en/docs/claude-code) como un proceso persistente en un servidor Linux. Reusa una suscripción Claude (Pro o MAX) vía OAuth y no requiere otros runtimes de agente.

Este repositorio documenta una sola configuración funcional: la del autor. No es un framework, una librería, ni un producto. Si te resulta útil como punto de partida, cópialo y modifícalo.

**Ejemplo vivo:** [key.pixan.bot](https://key.pixan.bot) — el sitio del agente que corre bajo esta configuración, con la teoría de cómo opera y datos de su instancia en producción.

## Qué resuelve

Claude Code es un CLI interactivo. Para usarlo como agente que reacciona a webhooks, mensajes de chat o eventos de tiempo, hay que:

1. Aislar su configuración (`CLAUDE_CONFIG_DIR`) de la del CLI que usas en tu laptop.
2. Mantenerlo corriendo como `systemd --user` service.
3. Conectarlo a uno o más canales (Discord, Telegram) vía plugins.
4. Definir su comportamiento con archivos markdown que el binario carga al arranque.

Ninguno de estos pasos es complicado individualmente. La documentación oficial los cubre por separado. Este repo los junta en una secuencia que ha estado en producción desde principios de 2026 en un servidor de 2 vCPU.

## Qué no resuelve

- **Orquestación multi-agente empaquetada.** El patrón sí escaló a una flota (ver [09](docs/09-fleet.md) y [12](docs/12-agentic-leadership.md)), pero con archivos compartidos y leases, no con un framework. Si quieres estado compartido y protocolo de mensajes ya resueltos, mira proyectos como [hkuds/nanobot](https://github.com/hkuds/nanobot).
- **Empresas.** No hay autenticación multi-usuario, audit log centralizado, ni controles de cumplimiento.
- **Escalado horizontal.** Una sola sesión de Claude Code por servicio. Los plugins son outbound, no exponen endpoints HTTP propios.
- **Garantías de uptime.** Es lo que sea que tu servidor + Claude API + tu cuota MAX te den.

## Costo

| Componente | Costo |
|------------|-------|
| Servidor (Hetzner CX22, DigitalOcean basic, etc.) | $5–10/mes |
| Suscripción Claude Pro o MAX | tu plan actual |
| ElevenLabs (opcional, para audio) | desde $5/mes |
| Replicate (opcional, para imágenes) | pago por uso |

Los runs disparados por `CronCreate`, `ScheduleWakeup` y `RemoteTrigger` consumen un cupo combinado de la cuenta Claude (15/24h en MAX al momento de escribir). El cupo aplica al plan, no a este patrón en particular.

## Documentación

| # | Archivo | Contenido |
|---|---------|-----------|
| 1 | [docs/01-install.md](docs/01-install.md) | Node, Claude Code, `CLAUDE_CONFIG_DIR`, OAuth |
| 2 | [docs/02-systemd.md](docs/02-systemd.md) | Unit file, `EnvironmentFile`, lingering, operación |
| 3 | [docs/03-workspace.md](docs/03-workspace.md) | Layout del workspace y rol de cada archivo |
| 4 | [docs/04-skills.md](docs/04-skills.md) | Anatomía de un skill, frontmatter, cuándo escribir uno |
| 5 | [docs/05-channels.md](docs/05-channels.md) | Plugins Discord/Telegram, MCPs heredados, allowlists |
| 6 | [docs/06-scheduling.md](docs/06-scheduling.md) | Heartbeat, `CronCreate`, `agent-cron`, presupuesto de runs |
| 7 | [docs/07-memory.md](docs/07-memory.md) | Directorio de memoria, tipos, caps, versionado git |
| 8 | [docs/08-troubleshooting.md](docs/08-troubleshooting.md) | Problemas observados, síntomas, fixes |
| 9 | [docs/09-fleet.md](docs/09-fleet.md) | De uno a varios: aislamiento, credenciales, convivencia |
| 10 | [docs/10-failure-modes.md](docs/10-failure-modes.md) | Qué se rompe tras meses y qué monitorear |
| 11 | [docs/11-emergent-cases.md](docs/11-emergent-cases.md) | Conductas no programadas, con su mecanismo |
| 12 | [docs/12-agentic-leadership.md](docs/12-agentic-leadership.md) | Dirigir agentes: delegación, supervisión, confianza |

`templates/` contiene archivos de configuración listos para copiar y modificar. `skills/agent-cron/` es el único skill incluido — un wrapper sobre `systemd --user` timers para reminders persistentes.

## Sobre el nombre

"Solo" carga dos sentidos: **una sola persona** — el dev solo que ya paga su suscripción y quiere exprimirla cuando no está chateando — y **un solo agente**, sin framework ni capa ajena.

El primero sigue intacto. El segundo se quedó chico: la configuración terminó corriendo una flota de ocho agentes durante meses. No renombramos el repo porque un agente solo sigue siendo la puerta de entrada correcta — nadie empieza con siete. Lo aprendido al crecer está en los documentos 09 a 12, que no existían en la versión original.

## Asunciones

La documentación asume:

- Ubuntu 24.04 LTS o equivalente con `systemd`.
- Un usuario no-root con acceso `sudo` para la instalación inicial.
- Familiaridad con `systemctl --user`, `journalctl`, archivos de unidad systemd.
- Lectura previa de la documentación oficial de Claude Code.

Si algo de lo anterior no aplica, los pasos pueden necesitar adaptación.

## Estado

La configuración descrita corre en producción en un servidor del autor. La documentación se actualiza cuando algo cambia en el setup vivo. No hay versionado SemVer ni changelog formal — `git log` es la fuente de verdad.

Issues y PRs bienvenidos. No hay garantía de respuesta rápida.

## Licencia

MIT. Ver [LICENSE](LICENSE).

## Referencias

- [Anthropic — Claude Code](https://docs.claude.com/en/docs/claude-code)
- [hkuds/nanobot](https://github.com/hkuds/nanobot) — patrones de heartbeat / dream / ask-user adoptados aquí.
- [systemd.timer(5)](https://www.freedesktop.org/software/systemd/man/systemd.timer.html) — base del skill `agent-cron`.
