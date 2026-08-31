# 12 — Liderazgo agéntico

> Los capítulos anteriores son de instalación y operación. Éste es de **dirección**: qué cambia
> en tu trabajo cuando dejas de usar agentes y empiezas a dirigirlos.

Es el documento menos técnico del repo y probablemente el que más te va a costar aplicar.

---

## La transición que nadie te avisa

Con un agente, tu trabajo es **pedir**. Con varios, tu trabajo es **diseñar el sistema que
decide** — qué se delega, quién verifica, y qué pasa cuando algo falla mientras duermes.

El primer síntoma de que cruzaste esa línea es incómodo: **empiezas a ser el cuello de botella.**
Cinco agentes produciendo trabajo que solo tú puedes aprobar es peor que uno, no mejor. Si al
crecer tu flota tu bandeja crece igual, no montaste un equipo: montaste cinco formas nuevas de
generarte pendientes.

La salida no es delegar más ejecución. Es **delegar verificación**.

---

## El nivel de supervisión: un agente que revisa a otros

En nuestra operación hay un agente con rol de líder. No es un agente más grande ni con mejor
modelo: es uno con **acceso de lectura al trabajo de los demás** y con permiso explícito para
señalar problemas.

Lo que sí hace bien:

- **Verifica contra la fuente**, no contra el output (§ `11`, caso 2).
- **Detecta el silencio.** Un agente que dejó de entregar no genera error; genera ausencia. Nadie
  nota una ausencia salvo quien la esté esperando.
- **Traduce entre dominios.** Le pasa a un agente el contexto que generó otro, sin que tú seas
  el cable.

Y lo que hay que decir con todas sus letras: **un supervisor es otro agente y falla igual.**
Puede tener la credencial muerta, congelarse, o —lo peor— reportar salud mientras no revisa nada.
Si tu única defensa es "el líder lo vigila", tu punto único de falla ahora tiene opinión.

---

## Redundancia mutua en vez de jerarquía

El arreglo que nos ha funcionado no es una pirámide, son **dos agentes que se vigilan entre sí**,
con roles distintos:

- El **interactivo**, que vive donde tú trabajas y tiene contexto de la conversación.
- El **ejecutor 24/7**, headless, que atiende canales y ciclos.

Cada uno vigila al otro. Cuando uno se cae, el otro lo detecta y —según la regla de remediación
del § `10`— lo repara si es no destructivo, o te reporta y espera si no lo es.

**El problema que esto trae, y su solución.** Dos agentes vigilando la misma cosa la ejecutan dos
veces. Un archivo de **lease con TTL** en el directorio compartido lo resuelve: el que toma la
tarea escribe su lease, el otro lo ve y se abstiene. Si el lease expira sin renovarse, el segundo
asume que el primero murió y entra. Son treinta líneas y evitan la clase entera de duplicados.

```
shared/leases/<tarea>.lease   →  { agente, tomado_en, expira_en }
```

**La capa que no tiene agentes.** Debajo de todo esto necesitas al menos un vigilante que **no
sea un agente**: un timer del sistema con un script tonto. Si toda tu supervisión corre sobre el
mismo runtime que estás supervisando, un fallo del runtime te deja ciego y callado a la vez.
Nosotros lo aprendimos con 13 días sin vigilancia y un agente muerto 13 horas.

---

## Qué se delega y qué no

| | Ejemplos | Por qué |
|:---|:---|:---|
| **Se delega bien** | Monitoreo, resúmenes, primer borrador, verificación mecánica, seguimiento | Verificable contra un criterio |
| **Se delega con red** | Escribir a terceros, cambios en repos, gasto | Reversible, pero caro de deshacer |
| **No se delega** | Publicar, borrar, decidir a nombre tuyo | Irreversible o de tu autoría |

La línea no es la dificultad de la tarea: es **la reversibilidad y de quién es la firma**. Un
agente puede escribir mejor que tú un capítulo entero y aun así no le toca decidir si sale al
mundo.

Consecuencia práctica que sí duele: si le pides a un agente algo irreversible y lo hace, el error
es de diseño, no suyo. **Los permisos son parte del liderazgo.**

---

## Calibrar la confianza

Con personas, la confianza sube con el tiempo. Con agentes es distinto, y confundirlo es caro:

- **La confianza no se acumula.** Un agente que llevaba tres meses impecable puede obedecer una
  orden fabricada hoy. No "se ganó" nada.
- **Confía en el mecanismo, no en el historial.** La pregunta útil no es "¿ha fallado antes?",
  sino "¿qué lo detendría si esto estuviera mal?".
- **La confianza es por tipo de tarea, no por agente.** El mismo agente puede ser excelente
  verificando y pésimo decidiendo alcance.

---

## Cómo dar instrucciones que sobreviven

Casi todos los problemas de conducta que hemos tenido se arreglaron con redacción, no con código.

1. **Escribe el porqué, no solo el qué.** Una regla sin motivo se aplica literal y se rompe en el
   primer caso raro. Con motivo, el agente generaliza bien.
2. **Escribe el caso que la originó.** Nuestras reglas más efectivas traen el incidente adentro,
   con fecha. Sirve para el agente y para ti dentro de seis meses.
3. **Di explícitamente qué NO hacer**, sobre todo cuando choca con el default del modelo.
   "Si no hay nada que reportar, no reportes" hay que escribirlo, porque lo natural es rellenar.
4. **Una regla nueva no está aplicada hasta que reiniciaste las sesiones vivas** (§ `09`).

---

## El costo que sí hay que decir

Dirigir agentes no es gratis, y el repo perdería credibilidad si no lo dijera:

- **El trabajo se mueve, no desaparece.** Ejecutas menos y diseñas más verificación. Para mucha
  gente eso es *menos* divertido.
- **Las fallas son más raras y más difíciles.** Un bug se depura. Un agente que hizo algo
  razonable con premisas equivocadas hay que reconstruirlo desde su contexto.
- **Se siente lento antes de sentirse rápido.** Las primeras semanas revisas todo. La ganancia
  llega cuando ya sabes qué revisar.
- **La atención es el recurso escaso.** No los tokens, no el servidor. Cuántas cosas puedes
  supervisar de verdad antes de empezar a aprobar sin leer — y aprobar sin leer es peor que no
  tener el agente.

---

## Lo mínimo, si te llevas una sola cosa

> Diseña primero **cómo te enteras de que algo salió mal**, y hasta después qué hace el agente
> cuando sale bien.

Todo lo demás de este capítulo se deriva de ahí.
