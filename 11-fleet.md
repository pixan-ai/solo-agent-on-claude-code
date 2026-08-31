# 11 — De uno a varios (la flota)

> Este documento es el que el título del repo deja fuera. "Solo agent" es la puerta de entrada
> correcta — nadie empieza con siete. Pero si el patrón te funciona, en algún momento vas a querer
> un segundo agente, y ahí empiezan problemas que no existen cuando corres uno solo.

Lo que sigue es lo aprendido corriendo una flota de ocho agentes durante cuatro meses.

---

## Cuándo NO necesitas un segundo agente

Primero lo honesto: la mayoría de las razones para clonar son malas.

| Razón | Veredicto |
|:---|:---|
| "Quiero que uno hable y otro ejecute" | ✅ Buena. Es la primera división útil |
| "Quiero separar dominios con datos distintos" | ✅ Buena |
| "Quiero que corra más rápido" | ❌ No. Dos agentes no paralelizan tu trabajo |
| "Quiero más cupo" | ❌ No. El cupo es de la cuenta, no del proceso |
| "Se siente más pro" | ❌ Cada agente es un servicio más que se cae |

**El costo real de un agente extra no son tokens: es superficie de falla.** Cada uno trae su
servicio, sus credenciales, su cache, su allowlist y su memoria. Todo eso se rompe por separado.

## La primera división que sí vale la pena

**Un conversador interactivo + un ejecutor 24/7.**

El interactivo vive en tu terminal, planea contigo, tiene contexto largo de la conversación.
El ejecutor corre headless bajo systemd, atiende el heartbeat, los webhooks y los canales.

Son perfiles incompatibles en un solo proceso: el interactivo necesita que no lo interrumpan, y
el ejecutor necesita despertar cada rato. Meterlos en la misma sesión los degrada a los dos.

## Aislamiento: qué debe ser propio de cada agente

No negociable — cada agente necesita **todo** esto por separado:

```
~/.claude-<agente>/          ← CLAUDE_CONFIG_DIR propio
├── .credentials.json        ← credencial propia (ver abajo, es lo más delicado)
├── projects/…/memory/       ← memoria propia
└── channels/<canal>/.env    ← token de bot propio

~/agents/<agente>/workspace/ ← workspace propio
└── .claude/skills/          ← copia propia de las skills

<agente>.service             ← unit systemd propia
```

Compartir cualquiera de esos cinco produce fallas que parecen embrujadas. Las dos peores tienen
nombre y las documento abajo.

---

## Gotcha 1 — El cache de plugins se hereda por ruta absoluta

**Síntoma:** clonas el workspace de un agente sano para crear otro. El nuevo arranca, se ve bien,
y sus canales no responden. O peor: responden con la configuración del agente original.

**Causa:** los archivos de configuración de plugins guardan **rutas absolutas** al cache del
agente del que copiaste. El `settings.json` del clon se ve impecable — el problema está en el
cache, no en la config visible.

**Nos pasó dos veces**, con tres meses de diferencia y sin que la primera nos vacunara: dos
agentes colgados del cache del primero, y después dos más colgados del cache de un clon
intermedio. La segunda vez tardamos igual en verlo que la primera.

**Fix:** después de clonar, purga el cache de plugins del clon y deja que se reconstruya. Y
`grep` recursivo por la ruta del agente original en todo el config dir del clon, antes de
arrancarlo:

```bash
grep -rl "/home/$USER/.claude-<agente-original>" ~/.claude-<agente-nuevo>/
```

Si eso devuelve algo, todavía no terminaste de clonar.

---

## Gotcha 2 — La rotación de credenciales mata a los clones

**Síntoma:** un agente que llevaba semanas bien empieza a devolver 401. Te vuelves loco buscando
qué cambió. No cambió nada: le tocó rotar.

**Causa:** el refresh token es **de un solo uso**. Si dos agentes heredaron el mismo
`.credentials.json` (porque uno se clonó del otro), el primero que rota invalida al otro. El
linaje del clon comparte destino con su padre y ninguno de los dos lo sabe.

**Fix — el correcto, no el parche:** cada agente saca su **propia** credencial de larga duración
en vez de heredar una:

```bash
CLAUDE_CONFIG_DIR=~/.claude-<agente> claude setup-token
```

Eso emite un token propio por agente, con vigencia larga, y rompe el linaje compartido. Nunca
copies `.credentials.json` de un agente a otro — es la causa raíz de la mayoría de las "muertes
misteriosas".

**Parche mientras tanto:** un watchdog horario que revise que cada config dir todavía tenga
`refreshToken` y te avise antes de que el agente se muera del todo. Ver `12-failure-modes.md`.

---

## Gotcha 3 — Las skills clonadas divergen en silencio

Endureces una regla en el `SKILL.md` de un agente. Crees que arreglaste el problema. No: cada
clon tiene su **copia** del archivo, y además **las sesiones vivas cargaron la versión vieja al
arrancar**.

Un cambio de skill no está aplicado hasta que:

1. Parchaste las N copias del archivo.
2. Reiniciaste las N sesiones que lo tenían cargado.

Si tu flota crece, esto se vuelve el problema dominante de mantenimiento. Vale la pena tener las
skills compartidas en un solo lugar y enlazadas, o un script que propague y reinicie — pero
decídelo temprano, porque migrar seis copias divergentes después duele.

---

## Comunicación entre agentes

**Directorio compartido.** Lo más simple y lo más robusto: un `~/shared/` donde los agentes
dejan contexto que otros pueden leer. Sin protocolo, sin servidor. Archivos.

**Si van a coordinarse de verdad, necesitas un lease.** Dos agentes que vigilan la misma cosa
la van a ejecutar dos veces. Un archivo de lease con TTL en el directorio compartido resuelve el
99% de los casos sin meter una cola de mensajes.

**Bot a bot en Telegram:** un bot no ve los mensajes de otro bot por default. Se habilita
**por bot, en BotFather** — no es un ajuste del grupo, y la API no expone el flag, así que la
única forma de saber si quedó es probarlo y mirar el lado del receptor. Además, para leer sin
mención, el receptor necesita ser admin del grupo.

---

## Reglas de convivencia (las de verdad importan)

Con un agente, el comportamiento social no existe. Con varios, es la mitad del trabajo.

- **Regla de oro: si un mensaje nombra a una destinataria, las demás se callan.** Sin esto, cada
  mensaje al grupo produce N respuestas y el canal se vuelve inusable.
- **Un acuse ya dado por otra no se repite.** Aplica igual a broadcasts.
- **Voz distinta por agente.** Si usas TTS, dale a cada uno una voz diferente. Suena a detalle
  cosmético y no lo es: es cómo sabes quién habló sin leer.
- **Membresía ≠ acceso.** Que un agente esté en un grupo no significa que deba atenderlo.
  Allowlist explícita por agente.
- **Aísla los temas.** Si un agente maneja algo personal o confidencial, bloquéalo por
  configuración en los demás. No confíes en que "no le va a tocar".

---

## Los límites que sí te van a pegar

- **El cupo es de la cuenta.** Más agentes no es más cupo: es el mismo repartido.
- **Los disparadores programados del harness tienen tope diario** y se comparten entre todos los
  mecanismos. Un heartbeat cada 90 minutos ya consume 16 al día. Si vas a tener varios agentes
  con heartbeat, saca los ciclos del harness y ponlos en `cron` del sistema — más barato, más
  confiable, y no compite con los webhooks.
- **La RAM.** Cada agente es un proceso Node con contexto en memoria. Ocho sesiones en un equipo
  modesto es real, pero necesitas cap por cgroup. Ver `12-failure-modes.md`.

---

## Checklist de alta de un agente nuevo

```
□ CLAUDE_CONFIG_DIR propio creado
□ Credencial propia con `claude setup-token` (NO copiada)
□ Cache de plugins purgado y verificado con grep de rutas absolutas
□ Workspace propio; SOUL/USER/CLAUDE.md revisados, no heredados a ciegas
□ Token de bot propio en channels/<canal>/.env
□ Allowlist explícita: a qué chats responde
□ Unit systemd propia, con Environment= (systemd NO lee tu .bashrc)
□ Voz TTS distinta, si usas audio
□ Primer arranque manual: los gates interactivos ("¿confías en esta carpeta?")
  bloquean el arranque headless y no dejan error obvio
□ Dado de alta en el watchdog de credenciales
```

Ese último punto del arranque manual nos costó una tarde: un agente nuevo que "no arrancaba" y
en realidad estaba esperando una confirmación que nadie podía darle, porque corría sin TTY.
