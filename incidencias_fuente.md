# Registro de incidencias de las fuentes

**Proyecto:** Costo del capital en mercados emergentes: Perú, Chile, Colombia y México (Tema N.º 64)
**Autora:** Abril Shantal Ricaldi Bravo · Código 2024200519L

## Incidencia 1 — Meses sin dato en el bono a 10 años de México

| | |
|---|---|
| **Fuente afectada** | FRED, serie IRLTLT01MXM156N (OCDE) |
| **Fecha de detección** | 16/11/2026 |
| **Descripción** | En la ventana enero 2005 – diciembre 2025, la serie tiene 191 de 252 meses con dato (61 meses vacíos, el primero en octubre de 2007). Con esa serie el panel sumaba 943 observaciones, por debajo del mínimo de 1 000. |
| **Causa** | El Bono M a 10 años no se subasta todos los meses; la serie de la OCDE se construye a partir de esas subastas. |
| **Consulta al docente** | 18/11/2026, en clase. El docente indicó: (1) buscar fuentes más completas para reducir los datos en blanco, autorizando el uso de Banxico para México; (2) si aún quedaran huecos, realizar imputación; (3) el mínimo de 1 000 observaciones es obligatorio. |
| **Acción** | Se reemplazó FRED por la fuente primaria, Banxico SIE, serie SF44071 (resultados de la subasta semanal, tasa de rendimiento, Bono tasa fija 10 años), consumida por API con token. Verificación del 18/11/2026: 194 subastas con dato, 191 de 252 meses con dato y los mismos 61 meses sin subasta. |
| **Imputación aplicada** | Para cada mes se toma la tasa de la última subasta vigente. En los 61 meses sin subasta se mantiene la tasa de la subasta anterior (arrastre del último valor). Si un mes tuvo dos subastas (3 casos), se usa la última. Los meses imputados quedan marcados en la columna `rend10a_tipo` como `imputado_ultima_subasta`. Se prefirió este método frente a la interpolación lineal porque el valor imputado existe en la fuente (es la subasta anterior). |
| **Efecto en los resultados** | La estimación sin los meses imputados (943 observaciones) da coeficientes prácticamente iguales a los del modelo principal (`salidas/tabla5_modelos_presentable.csv`, columna "EF D-K sin imputados"). |

## Incidencia 2 — Índice de archivos de Damodaran bloqueado (HTTP 403)

| | |
|---|---|
| **Fuente afectada** | Damodaran (NYU Stern), índice de directorio `https://pages.stern.nyu.edu/~adamodar/pc/archives/` |
| **Fecha y hora** | 20/11/2026, 23:30:21 – 23:30:27 (hora de Lima) |
| **Código HTTP** | 403 (Forbidden) en tres intentos consecutivos (registrados en `log_ejecucion.txt`) |
| **Acción** | No fue necesario sustituir la fuente. El script se modificó para rastrear la página oficial de datos archivados (`https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html`, HTTP 200), que enlaza los mismos archivos. Los 21 archivos ctryprem04 a ctryprem24 se descargaron con HTTP 200 el 21/11/2026, respetando robots.txt, con User-Agent identificado y pausas de 2 segundos. |

## Incidencia 3 — Series de inflación mensual descontinuadas en FRED

| | |
|---|---|
| **Fuente afectada** | FRED (OCDE): CPALTT01CLM659N (Chile), COLCPALTT01GYM (Colombia), CPALTT01MXM659N (México) |
| **Fecha de detección** | 16/11/2026 |
| **Descripción** | Las series dejaron de actualizarse: Chile hasta diciembre de 2023, México hasta julio de 2024 y Colombia hasta abril de 2025. No cubren la ventana del estudio. |
| **Acción** | Se usó la inflación anual del Banco Mundial (WDI, FP.CPI.TOTL.ZG), disponible para los cuatro países hasta 2025. El valor anual se repite en los 12 meses del año, sin interpolar. |
