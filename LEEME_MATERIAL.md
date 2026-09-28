# Material del Proyecto · Unidad 1 · ACD-2504

Agente analista del DENUE para Tampico y Ciudad Madero.

- **Entrega:** miércoles 30 de septiembre de 2026, 23:59.
- **Defensa:** jueves 1 y viernes 2 de octubre.

Copie todo este material en la raíz de su repositorio `agente-denue-NUMERODECONTROL`. Este archivo puede borrarlo después.

| Archivo | Qué es | ¿Lo modifica? |
|---|---|---|
| `data/denue_tampico_madero.csv` | DENUE 05/2026 (INEGI) de Tampico y Ciudad Madero: 22,900 establecimientos, 16 columnas, UTF-8 | **No** |
| `data/sectores_scian.csv` | Nombre de cada sector SCIAN | **No** |
| `data/mini_denue.csv` | Tabla ficticia de 8 filas para la traza E.3 | **No** |
| `data/diccionario_datos.md` | Descripción de columnas, estratos y códigos SCIAN | No |
| `data/preguntas_prueba.json` | Banco de 10 preguntas | **No** |
| `README.md` | Plantilla del README. Sustituya cada `COMPLETAR` | Sí |
| `traza_manual.md` | Plantilla de la Parte E. Sustituya cada `(escriba aquí)` **a mano** | Sí |
| `verificar_entrega.py` | Revisa su entrega: `python verificar_entrega.py` | No |

Todo el código lo escribe usted, con la estructura y los contratos del documento del proyecto.

Antes del primer commit, cree `.gitignore` con `.env` adentro. En `.env` van la clave de Gemini **y el token de su bot de Telegram**; ninguno de los dos se sube.

Necesita la app de Telegram en su celular. El bot se crea gratis con @BotFather (Parte H del documento).

Fuente de los datos: INEGI, *Directorio Estadístico Nacional de Unidades Económicas*, edición 05/2026. Se usa bajo los Términos de Libre Uso de la Información del INEGI. Se retiraron las columnas de razón social, teléfono, correo y sitio web.
