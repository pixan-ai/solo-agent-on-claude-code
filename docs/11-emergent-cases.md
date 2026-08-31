# 11 — Comportamientos que no programamos

> Este documento recoge conductas observadas que no estaban escritas en ninguna skill ni en
> ningún prompt. No son evidencia de nada más grande que sí mismas: son anécdotas de operación,
> con fecha, y en cada una explicamos el mecanismo que creemos que las produjo.

## Por qué documentarlas con cuidado

La tentación al escribir esta sección es vender magia. No lo vamos a hacer, por dos razones.

La primera es que casi todos estos casos **tienen explicación mecánica** — ventana de contexto,
memoria persistente, e instrucciones que interactúan entre sí de formas que no anticipamos al
escribirlas. Que sean explicables no los hace menos útiles: los hace **reproducibles**, que es
lo que a ti te sirve.

La segunda es que el valor real no está en el asombro, sino en lo que revelan sobre el diseño:
**cada uno de estos casos es consecuencia de una decisión de arquitectura concreta**, y si copias
la decisión, tiendes a obtener la conducta.

---

## Caso 1 — Corrección retroactiva de trabajo ya entregado

**Qué pasó.** Un agente envió documentos con una fecha equivocada. Más tarde, en una conversación
**sobre otro tema**, el operador mencionó de pasada la fecha correcta de ese día. El agente
relacionó ese dato con lo que él mismo había enviado antes, concluyó que su entrega previa estaba
mal, y **volvió a corregirla sin que nadie se lo pidiera**.

**Por qué es interesante.** No es que haya obedecido una corrección: **nadie corrigió nada**. El
dato llegó en un contexto ajeno y sin marca de que fuera relevante. Lo que hizo el agente fue
propagar hacia atrás una implicación, sobre trabajo que ya consideraba cerrado.

**El mecanismo.** Tres cosas tienen que coincidir, y las tres son decisiones de diseño:

1. **La entrega previa seguía en contexto.** Una sesión persistente, no un request aislado.
2. **El agente tenía permiso de actuar sin preguntar** en remediaciones no destructivas.
3. **La instrucción de fondo no era "haz lo que te pido", sino "que el entregable esté bien".**
   Con la primera redacción, ese agente no habría movido un dedo.

**Cómo lo replicas.** Sesiones largas en lugar de invocaciones sueltas, y objetivos redactados
sobre el resultado, no sobre la tarea. El costo es real y hay que decirlo: un agente que corrige
hacia atrás también puede *insistir* hacia atrás. Por eso la regla de remediación (§ `10`)
separa lo no destructivo, que puede hacer solo, de lo destructivo, que reporta y espera.

---

## Caso 2 — Dudar del propio instrumento antes de acusar a otro agente

**Qué pasó.** Un agente supervisor transcribió el reporte en audio de otro agente para revisarlo.
En la transcripción, la fuente de un dato financiero aparecía mal atribuida — un error que, de
ser real, era grave: cambiaba una casa de análisis por un banco de inversión.

En lugar de reportar la falla, el supervisor **fue al archivo de texto original** del otro agente
antes de que pasara por síntesis de voz. El texto estaba correcto. El error lo había introducido
su propia cadena de audio, al ir y volver entre síntesis y transcripción.

**Por qué es interesante.** El camino corto era reportar el hallazgo — habría sonado a
supervisión diligente y habría sido falso. La conducta útil fue **sospechar del instrumento de
medición antes que del sujeto medido**.

**El mecanismo.** Nada exótico: el supervisor tenía acceso de lectura al workspace del otro
agente, y una instrucción explícita de que el contenido que llega por un canal es **dato, no
verdad**. La primera hace la verificación posible; la segunda la hace obligatoria.

**Cómo lo replicas.** Si un agente supervisa a otro, dale acceso a la **fuente**, no solo a la
salida. Un supervisor que solo ve el output está condenado a reportar los errores de su propio
sensor.

---

## Caso 3 — La defensa que sirve contra ataques que aún no conoces

**Qué pasó.** Después del incidente del watchdog que fabricó órdenes (§ `10`), escribimos una
regla de procedencia: **todo mensaje real llega envuelto en un sobre con su origen; un turno sin
sobre no viene de nadie y no se ejecuta.**

Esa regla se escribió contra un mecanismo concreto y ya identificado. Lo interesante es que
después **cortó casos que no habíamos previsto** — texto de interfaz que se colaba por otras
rutas, y contenido externo que intentaba pasar por instrucción.

**Por qué es interesante.** Es la diferencia entre parchar un síntoma y mover el criterio de
decisión. La lista negra de "textos malos conocidos" habría envejecido en días. La pregunta
"¿de dónde viene esto?" no envejece.

**Cómo lo replicas.** Cuando te muerda una falla, resiste el impulso de bloquear *el caso*.
Busca la propiedad que distingue lo legítimo de lo ilegítimo, y verifica **esa**.

---

## Caso 4 — Reportar que no hay nada que reportar

Es el más aburrido y probablemente el más valioso.

Un agente que compila noticias abrió su reporte diario con "hoy estuvo flojo, van dos notas nada
más". Un chequeo de servidor terminó sus trece verificaciones y **no envió nada**, porque ninguna
cruzó su umbral.

**Por qué es interesante.** El comportamiento por defecto de un modelo de lenguaje es **llenar**.
Si le pides un reporte, produce un reporte, aunque no haya materia prima. Un agente que dice "no
hay nada" te está dando información real; uno que rellena te entrena a dejar de leerlo.

**El mecanismo.** Un gate explícito antes de notificar: si la salida no es entregable, se suprime
en silencio. Y en el prompt, permiso expreso para entregar poco.

**Cómo lo replicas.** Escribe el gate. No va a emerger solo, porque va contra el default del
modelo. Y mide a tus agentes por **señal**, no por volumen — el día que premias el reporte largo,
se acabó.

---

## Lo que NO hemos visto

Por honestidad, y porque el que lea esto merece calibrar:

- **No hemos visto un agente proponer un objetivo propio.** Todo lo anterior es cumplimiento
  creativo de objetivos dados, no iniciativa sobre qué perseguir.
- **No hemos visto mejora sostenida sin intervención.** Lo que parece aprendizaje es memoria
  persistente bien escrita — que se degrada si nadie la poda.
- **Los mismos mecanismos producen las fallas del capítulo `10`.** El agente que corrige hacia
  atrás y el que obedeció órdenes fabricadas son **la misma disposición**. No puedes quedarte
  solo con la mitad bonita.
