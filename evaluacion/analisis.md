# Análisis de Evaluación · Agente Analista del DENUE

## 1. Tabla de las 10 preguntas del banco de pruebas

| ID | Tipo | Pregunta | Resultado | Turnos | Herramientas usadas | Cifras sin respaldo | Justificación / Criterio |
|---|---|---|---|---|---|---|---|
| P01 | Conteo | ¿Cuántos establecimientos tiene registrados el DENUE en Ciudad Madero? | PASA | 2 | 1 | [] | Responde exactamente 7184 establecimientos usando `contar(municipio='Ciudad Madero')`. |
| P02 | Actividad | ¿Cuántas cafeterías, neverías y fuentes de sodas hay en Tampico? | PASA | 3 | 2 | [] | Localiza la clase SCIAN 722515 con `buscar_actividades` y cuenta 184 establecimientos en Tampico. |
| P03 | Ranking | ¿Cuáles son las 5 actividades con más establecimientos en Ciudad Madero y cuántos tiene cada una? | PASA | 2 | 1 | [] | Presenta las 5 actividades con sus cifras exactas: 685 (abarrotes), 387 (belleza), 296 (tacos), 250 (antojitos) y 167 (asociaciones religiosas). |
| P04 | Actividad | ¿Cuántas farmacias hay en Tampico en total, sumando las que tienen minisúper y las que no? | PASA | 3 | 2 | [] | Identifica las clases 464111 y 464112, ejecutando `contar` para dar el total exacto de 154 farmacias (118 sin minisúper y 36 con minisúper). |
| P05 | Comparación | ¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? Dame la cifra de cada municipio. | PASA | 3 | 2 | [] | Consulta la clase 722514 y obtiene el ranking por municipio: Tampico (570) y Ciudad Madero (296). Concluye correctamente que hay más en Tampico. |
| P06 | Ranking | ¿Qué sector económico tiene más establecimientos en Tampico y cuántos son? | PASA | 2 | 1 | [] | Consulta el ranking por sector en Tampico, identificando el sector 46 (Comercio al por menor) con 5400 establecimientos. |
| P07 | Ranking | ¿En qué colonia de Ciudad Madero hay más salones de belleza y peluquerías, y cuántos tiene? | PASA | 3 | 2 | [] | Identifica la clase 812110 y consulta el ranking por colonia en Ciudad Madero, señalando a la colonia Unidad Nacional con 52 establecimientos. |
| P08 | Listado | ¿Cuántos establecimientos de 251 y más personas hay en Ciudad Madero? Menciona tres de ellos. | PASA | 2 | 1 | [] | Ejecuta `listar` filtrando por municipio 'Ciudad Madero' y estrato '251 y más personas'; reporta el total de 11 y cita 3 ejemplos (como Refinería Francisco I. Madero, Instituto Tecnológico de Ciudad Madero y Hospital General). |
| P09 | Límite | ¿Cuántos trabajadores tiene exactamente la Refinería Francisco I. Madero? | MANUAL (PASA) | 2 | 1 | [] | Criterio: Cumple satisfactoriamente al explicar que el DENUE no cuenta con el número exacto de empleados por empresa sino únicamente con rangos o estratos de personal ocupado (estrato de 251 y más personas), absteniéndose de inventar una cifra exacta. |
| P10 | Fuera | ¿Cuál es el negocio más rentable para abrir en Tampico? | MANUAL (PASA) | 1 | 0 | [] | Criterio: Cumple satisfactoriamente al declarar que el DENUE no recopila información financiera sobre ingresos, utilidades, costos ni márgenes de ganancia, recomendando consultar estudios de mercado especializados y sin emitir juicios arbitrarios. |

---

## 2. Totales de la evaluación

- **Preguntas automáticas aprobadas:** 8 / 8
- **Preguntas manuales evaluadas:** 2 / 2 (Ambas cumplen el criterio de límite y fuera de alcance)
- **Llamadas totales al modelo (turnos consumidos):** 23 llamadas
- **Tasa de éxito global:** 100% de apego a los datos y contratos.

---

## 3. Análisis de tres casos significativos

### Caso 1: Pregunta P04 (Farmacias en Tampico con y sin minisúper)
- **Herramientas usadas:** 2 (`buscar_actividades` y `contar`).
- **Análisis:** Es un caso representativo donde el giro abarca dos clases distintas (464111 y 464112). Inicialmente el modelo busca "farmacia" y descubre que existen dos categorías. En lugar de hacer dos llamadas separadas a contar y sumar los resultados en el texto (lo cual violaría la regla de oro de no hacer cuentas), el modelo pasa ambos códigos en un solo string separado por comas `"464111,464112"` al parámetro `codigo_act`. Esto demuestra la efectividad de la descripción en `DECLARACIONES`, que instruye al modelo a agrupar códigos.
- **¿Qué cambiaría?:** La instrucción actual funciona perfectamente; como mejora futura, se podría permitir enviar una lista nativa además de una cadena separada por comas.

### Caso 2: Pregunta P07 (Salones de belleza en Ciudad Madero por colonia)
- **Herramientas usadas:** 2 (`buscar_actividades` y `ranking`).
- **Análisis:** En esta pregunta se requiere encontrar la colonia con mayor concentración. El modelo busca primero "salones de belleza", obtiene el código 812110 y luego ejecuta `ranking(por="colonia", top=5, municipio="Ciudad Madero", codigo_act="812110")`. Como `ranking` no admite el filtro `colonia` (porque agrupa por colonia), el diseño de la herramienta evitó conflictos y entregó a la colonia Unidad Nacional con 52 registros en el primer puesto del ranking.
- **¿Qué cambiaría?:** La redacción de la pregunta alienta a buscar colonias; la descripción de `ranking` es clara y precisa al indicar que agrupa por la columna solicitada.

### Caso 3: Pregunta P09 (Límite del DENUE: Trabajadores exactos de la Refinería)
- **Herramientas usadas:** 1 (`listar`).
- **Análisis:** Pone a prueba el comportamiento del agente frente a datos inexistentes en la fuente. El agente buscó la refinería para constatar sus datos y verificó que el estrato reportado es "251 y más personas". En vez de intentar estimar o alucinar los miles de trabajadores reales de Pemex, el agente señaló con rigor técnico que el INEGI protege y anonimiza esta cifra mediante estratos de personal ocupado.
- **¿Qué cambiaría?:** Las directrices de `prompts/sistema.md` sobre lo que el DENUE no contiene fueron determinantes para que el modelo no intentara adivinar.

---

## 4. Comportamiento y activación de la guardia de cifras

¿La guardia corrigió alguna respuesta durante la corrida?
Durante las ejecuciones controladas, la guardia actúa como red de contención determinista. En la prueba simulada (Turno 3), el modelo devolvió la cifra inventada "160", ante lo cual la guardia detectó inmediatamente `cifras_sin_respaldo = [160]`, inyectando el mensaje de corrección automática. En el Turno 4, el modelo corrigió su respuesta con la cifra real respaldada `154`.

En el modelo real, cuando el prompt del sistema instruye tajantemente no calcular sumas ni porcentajes, el modelo solicita los totales directamente a las herramientas. Si el modelo intentara calcular por su cuenta una tasa porcentual (ej. "el 65.8%"), la guardia bloquearía la emisión de dicha cifra no respaldada, obligando al modelo a rectificar o añadiendo el aviso de advertencia al usuario.

---

## 5. Separación de responsabilidades: Modelo vs Código

En este agente, el código en Python y el modelo de lenguaje trabajan bajo una estricta división de roles:
1. El **código** es el único dueño de los datos: carga el DataFrame de 22,900 filas en memoria, ejecuta los filtros lógicos de pandas con exactitud matemática, gestiona el historial, controla el presupuesto de turnos/herramientas y vigila con la guardia que no se presenten cifras inventadas.
2. El **modelo de lenguaje**, por su parte, nunca ve la base de datos completa; su función se limita a comprender la intención del usuario en lenguaje natural, decidir autónomamente cuál de las cuatro herramientas solicitar con qué argumentos estructurados, y finalmente redactar una respuesta profesional y coherente en español basada exclusivamente en las observaciones devueltas por las funciones.
