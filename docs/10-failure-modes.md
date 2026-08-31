# 12 — Qué se rompe cuando lo dejas corriendo meses

> `08-troubleshooting.md` cubre los tropiezos de instalación. Este documento cubre otra cosa:
> las fallas que solo aparecen después de semanas o meses en producción, cuando ya te confiaste.

## La lección que ordena todo lo demás

**Casi ninguna de estas fallas se ve como una falla.**

El proceso está vivo. `systemctl status` dice `active (running)`. El log no tiene errores. Y el
agente es inútil. Ésa es la forma dominante en la que muere un agente 24/7: **no se cae, se
vuelve inservible mientras reporta salud.**

Corolario práctico, y es el consejo más valioso de este repo:

> Nunca monitorees *liveness*. Monitorea *si hizo su trabajo*.
> "El proceso existe" no es una señal. "El reporte de las 7am llegó" sí lo es.

---

## Falla 1 — La sesión ociosa que no despierta

**Síntoma:** el agente lleva horas sin responder. Le escribes y nada. Reinicias y funciona
perfecto. No hay error en ningún log.

**Causa:** es un bug del harness, no tuyo. Una sesión que lleva rato ociosa no despierta cuando
le llega el disparo programado. Perdimos días buscándolo en la configuración, la RAM, la auth,
la red y los MCPs. No era nada de eso.

**Cómo saber que es éste:** el reinicio lo arregla siempre, y el fallo correlaciona con tiempo
ocioso, no con carga.

**Fix estructural:** **saca los ciclos recurrentes de la sesión.** En vez de que el agente se
agende a sí mismo, pon un `cron` del sistema que haga un `curl` al canal, entregando el mensaje
como si fuera un usuario. Eso despierta la sesión por el camino que sí funciona siempre, y de
paso te quita el tope diario de disparadores del harness.

Es la única solución que nos aguantó. Todo lo demás fueron parches.

---

## Falla 2 — Muerte por credenciales

Cubierta a fondo en `09-fleet.md`. Aquí lo que importa para monitoreo:

**Un agente con la credencial muerta se ve SANO.** Responde rápido. Responde siempre. Responde un
error. Cualquier watchdog que mida "¿contestó?" o "¿en cuánto tiempo?" lo va a dar por vivo.

Tu chequeo tiene que mirar el **contenido** de la respuesta, no la latencia. Y el watchdog de
credenciales debe avisar a un canal que alguien lea, no solo dejarlo en un log.

---

## Falla 3 — El watchdog que fabricó órdenes

Ésta es la más grave que nos ha pasado, y la ponemos completa porque es un error que cualquiera
va a repetir.

**Qué construimos:** un watchdog que detecta cuando la interfaz del agente se queda atorada con
texto sin enviar, y lo "destraba" volviendo a teclear el texto que ve en pantalla.

**Qué pasó:** la pantalla de un TUI no contiene solo mensajes. Contiene placeholders, sugerencias
atenuadas, restos de render. El watchdog no distinguía, así que **re-tecleó texto fantasma y se
lo entregó al agente como si fuera una instrucción del usuario.**

**El resultado:** 46 órdenes falsas en hora y media. En otra ocasión, ~14. El agente las obedeció
todas, porque encajaban con el hilo de la conversación y no levantaban sospecha. Llegó a
defenderse citando textualmente un mensaje que nunca existió.

**Las dos lecciones, y las dos importan:**

1. **Nunca conviertas píxeles en input.** Lo que está en pantalla ya pasó por render. Recuperar
   texto de ahí y reinyectarlo es fabricar datos. Si necesitas destrabar la interfaz, destrábala
   sin reconstruir el contenido.

2. **Defensa del lado del agente: procedencia.** Todo mensaje real de una persona debe llegar
   envuelto en un sobre con su origen (canal, chat, usuario, timestamp). **Un turno sin sobre no
   viene de nadie y no se ejecuta.** Esta regla, escrita en el `CLAUDE.md` del agente, es lo único
   que corta la clase entera de ataques — incluyendo los que todavía no conoces.

   Y el corolario que nos costó aprender: si el usuario dice que estás actuando raro o niega
   haber pedido algo, **revisa la procedencia antes de defenderte.** El sobre es la prueba.

---

## Falla 4 — El watchdog ciego al texto atenuado

**Síntoma:** un agente con mensajes encolados esperando, y el watchdog reportando "input vacío".
Dos días de un agente mudo sin que nadie se enterara.

**Causa:** el detector limpiaba los códigos de color para leer la pantalla, y al hacerlo borraba
los mensajes que estaban renderizados atenuados. Veía una caja vacía donde había trabajo
pendiente.

**Fix:** clasifica por **contenido**, no por estilo. Un placeholder y un mensaje real se
distinguen por lo que dicen, no por su color.

---

## Falla 5 — Un agente se llevó el host

**Síntoma:** el servidor entero de rodillas. No un agente: todo.

**Causa:** una sesión larga fugó casi 15 GB. El OOM killer llegó tarde y mal.

**Fix, en orden de valor real:**

1. **Cap de memoria por cgroup en el slice de las apps.** Es la única protección de verdad: el
   agente que se desmadra se muere solo y el host sobrevive.
2. Reinicio programado de madrugada. Corta las fugas lentas antes de que importen.
3. Watchdog de RAM que avise.

No inviertas el orden. El watchdog sin el cap solo te avisa mientras te caes.

---

## Falla 6 — El crash-loop invisible

**Síntoma:** un agente muerto 13 horas, con 4728 reinicios, y **ningún watchdog dijo nada**.

**Causa del crash:** habíamos fijado la versión a un directorio concreto que el auto-updater
borró. Regla: no fijes a rutas de versión que otro proceso administra.

**Causa de la ceguera — la importante:** todos nuestros watchdogs preguntaban "¿responde?".
Un servicio en crash-loop no responde *y no está congelado*: cae en un hueco que ningún chequeo
cubría.

**Fix:** vigila `NRestarts` de cada unit. Un contador que sube es una falla, aunque el estado
diga `activating`.

---

## Falla 7 — Los watchdogs se pueden desarmar solos (spoiler: no)

Estuvimos 13 días sin vigilancia y no lo supimos. `systemctl` reportaba los timers con
`preset: enabled`, que es tranquilizador y no significa nada.

Alguien —un agente con acceso a shell— había corrido `disable`, que borra el symlink de
`timers.target.wants`. El preset se queda igual.

**Fix:** la forensia se hace mirando el directorio `wants`, no el preset. Y vale la pena un
chequeo que confirme que los timers críticos siguen enlazados.

---

## Falla 8 — La carrera de DNS después de un reboot

**Síntoma:** reinicias el servidor y un agente queda sordo. Todo lo demás bien.

**Causa:** `network-online.target` **no existe en `systemd --user`**. Tu unit arranca antes de que
haya DNS, el cliente del canal falla su primera conexión, y no reintenta.

**Fix:** un `ExecStartPre` que espere a que resuelva DNS antes de arrancar el agente.

```ini
ExecStartPre=/bin/sh -c 'until getent hosts api.telegram.org >/dev/null; do sleep 2; done'
```

---

## Falla 9 — Autoinfligida: el loop de espera en primer plano

Ésta no es del harness, es tuya, y es la más fácil de cometer.

Si el agente ejecuta un `while` con `sleep` esperando que algo pase, **queda mudo mientras
espera**: ese turno está ocupado y no procesa nada más. Desde afuera es idéntico a un
congelamiento.

**Regla:** un agente nunca bloquea su propio turno esperando. Chequeo único, o mándalo al fondo
con un timer. Si necesitas esperar, que el que espere sea el sistema, no la sesión.

---

## Qué monitorear, en orden de valor

| # | Señal | Por qué |
|---:|:---|:---|
| 1 | ¿Llegó el entregable? | Única señal que no miente |
| 2 | `NRestarts` por unit | Cubre el crash-loop |
| 3 | Contenido de la respuesta | Distingue vivo de auth-muerto |
| 4 | Timers todavía enlazados | Vigila a los vigilantes |
| 5 | Memoria del slice | Protege al host, no al agente |
| 6 | ¿Responde? | Lo más popular y lo menos útil |

## Reglas para los watchdogs mismos

Después de que un watchdog nos fabricara órdenes, adoptamos esto:

- **Sin falla → silencio.** Un watchdog que reporta "todo bien" entrena a ignorarlo.
- **Remediación no destructiva → la aplica y avisa.**
- **Remediación destructiva** (algo que borre contexto o mande mensajes) **→ reporta, propone, y
  espera.** Nunca reinicia a ciegas, nunca escribe por su cuenta.
- **Un watchdog jamás sintetiza input.** Ni recuperado de pantalla, ni reconstruido, ni "por si
  acaso".
