# Diccionario de variables

**Proyecto:** Costo del capital en mercados emergentes: Perú, Chile, Colombia y México (Tema N.º 64)
**Autora:** Abril Shantal Ricaldi Bravo · Código 2024200519L

## 1. Base procesada: `datos_procesados/datos_procesados_2024200519L.csv`

1 004 filas (Chile 252, Colombia 252, México 252, Perú 248) × 10 columnas. Llave: `pais` + `fecha`.

| Variable | Definición | Unidad | Frecuencia | Fuente exacta | URL / endpoint de origen |
|---|---|---|---|---|---|
| `pais` | País de la Alianza del Pacífico | Texto (Chile, Colombia, Mexico, Peru) | — | Identificador | — |
| `fecha` | Mes de la observación | AAAA-MM | Mensual | Identificador | — |
| `rend10a` | Rendimiento del bono soberano a 10 años en moneda local. México: tasa de la última subasta vigente al cierre del mes | % anual | Mensual | Chile: FRED/OCDE IRLTLT01CLM156N · Colombia: FRED/OCDE COLIRLTLT01STM · México: Banxico SIE SF44071 · Perú: BCRPData PD31895MM | `https://api.stlouisfed.org/fred/series/observations` · `https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF44071/datos/...` · `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD31895MM/json/...` |
| `crp` | Prima por riesgo país (*country risk premium*) basada en la calificación soberana de Moody's, publicada por Damodaran el 1 de enero de cada año y vigente durante ese año (valor original × 100) | % | Anual, repetida en los 12 meses | Damodaran (NYU Stern), hojas *Country premiums* (2005-2012) y *ERPs by country* (2013-2025) de los archivos ctryprem04 a ctryprem24 | `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html` → `https://pages.stern.nyu.edu/~adamodar/pc/archives/ctrypremYY.xls(x)` |
| `inflacion` | Inflación, precios al consumidor | % anual | Anual, repetida en los 12 meses | Banco Mundial, World Development Indicators, FP.CPI.TOTL.ZG | `https://api.worldbank.org/v2/country/PER;CHL;COL;MEX/indicator/FP.CPI.TOTL.ZG?format=json&date=2005:2025` |
| `depreciacion` | Variación interanual del tipo de cambio: (TC_t / TC_t−12 − 1) × 100. Positivo = depreciación de la moneda local | % | Mensual | Calculada a partir de `tipo_cambio` | — |
| `tipo_cambio` | Tipo de cambio de cierre de mes (columna *Close*) | Unidades de moneda local por USD | Mensual | Yahoo Finance: PEN=X, CLP=X, COP=X, MXN=X | librería `yfinance` (`https://finance.yahoo.com/quote/PEN=X`, etc.) |
| `rend10a_tipo` | Origen del valor de `rend10a`: `observado` o `imputado_ultima_subasta` (61 meses de México sin subasta) | Texto | Mensual | Bandera generada en `03_limpieza_datos.py` | — |
| `crp_tipo` | Indica que la CRP es un valor anual repetido en cada mes (`anual_repetido`) | Texto | — | Bandera generada en `03_limpieza_datos.py` | — |
| `inflacion_tipo` | Indica que la inflación es un valor anual repetido en cada mes (`anual_repetido`) | Texto | — | Bandera generada en `03_limpieza_datos.py` | — |

## 2. Base cruda consolidada: `datos_crudos/datos_crudos_2024200519L.csv`

2 727 filas en formato largo (FRED 504, Banxico 751, BCRP 248, Banco Mundial 84, Yahoo Finance 1 056, Damodaran 84). Los valores no se editan: se copian como texto desde cada archivo crudo.

| Variable | Definición | Unidad / formato |
|---|---|---|
| `fuente` | Institución que publica el dato | FRED, Banxico, BCRP, Banco Mundial, Yahoo Finance, Damodaran |
| `codigo_serie` | Código de la serie en la fuente (o nombre del archivo de Damodaran) | Texto |
| `variable` | Variable del proyecto: `rend_bono10a`, `inflacion`, `tipo_cambio`, `crp` | Texto |
| `pais` | Código ISO de 3 letras | CHL, COL, MEX, PER |
| `frecuencia` | M = mensual, W = semanal (subastas de Banxico), A = anual | Texto |
| `periodo` | Periodo del dato | AAAA-MM, AAAA-MM-DD (Banxico) o AAAA |
| `valor` | Valor tal como lo entrega la fuente (Banxico usa `N/E` en semanas sin subasta; la CRP de Damodaran está en decimal) | Texto |
| `fecha_extraccion` | Fecha y hora (Lima) en que se guardó el archivo crudo | AAAA-MM-DD HH:MM:SS |

## 3. CRP extraída: `datos_crudos/damodaran_crp_anual.csv`

| Variable | Definición |
|---|---|
| `pais_iso3`, `pais` | País |
| `anio_vigencia` | Año en que rige la prima (publicada el 1 de enero de ese año) |
| `archivo`, `hoja` | Archivo de Damodaran y hoja de la que se leyó el dato |
| `calificacion_moodys` | Calificación soberana de Moody's en ese archivo |
| `erp_madura` | Prima de riesgo de un mercado maduro (EE. UU.) usada por Damodaran, en decimal |
| `erp_total` | Prima de riesgo total del país, en decimal |
| `crp` | Prima por riesgo país, en decimal. Se verifica que `erp_total − erp_madura = crp` |
