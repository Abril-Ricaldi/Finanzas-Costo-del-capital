# Costo del capital en mercados emergentes: Perú, Chile, Colombia y México

| | |
|---|---|
| **Autora** | Abril Shantal Ricaldi Bravo |
| **Código de matrícula** | 2024200519L |
| **Tema del temario** | N.º 64 — Costo del capital en mercados emergentes: Perú, Chile, Colombia y México |
| **Curso** | Finanzas I (055D) — Ciclo V — Periodo 2026-II |
| **Docente** | Dr. Ciro Iván Machacuay Meza |
| **Institución** | Universidad Nacional del Centro del Perú — Facultad de Economía |
| **Repositorio** | https://github.com/Abril-Ricaldi/Finanzas-Costo-del-capital |

**Título del artículo:** Costo del capital en mercados emergentes: Perú, Chile, Colombia y México. El rendimiento soberano como referencia del costo de financiamiento y sus determinantes, 2005–2025.

## Descripción

El proyecto compara las condiciones de financiamiento soberano de los cuatro países de la Alianza del Pacífico entre enero de 2005 y diciembre de 2025 e identifica sus factores asociados. La variable dependiente es el rendimiento del bono soberano a 10 años en moneda local, que se usa como referencia del costo de financiamiento de cada país y, por tanto, como punto de partida para analizar su costo del capital. El proyecto no estima el costo del capital propio ni el WACC de empresas concretas. Se estima un modelo de datos de panel país-mes con 1 004 observaciones:

```
rend10a_it = α_i + β1·crp_it + β2·inflacion_it + β3·depreciacion_it + ε_it
```

Signos esperados según la literatura: β1 > 0, β2 > 0 y β3 > 0. Además, se compara la asociación entre países con regresiones por país.

La base se construyó con extracción automatizada: consumo de API (FRED, Banxico, BCRPData, Banco Mundial y Yahoo Finance) y rastreo con descarga programática de archivos (Damodaran, NYU Stern).

## Fuentes y endpoints

| Variable | País | Fuente | Serie / archivo | Endpoint | Vía |
|---|---|---|---|---|---|
| Rendimiento bono 10 años (%) | Chile | FRED (OCDE) | IRLTLT01CLM156N | `https://api.stlouisfed.org/fred/series/observations` | API |
| Rendimiento bono 10 años (%) | Colombia | FRED (OCDE) | COLIRLTLT01STM | `https://api.stlouisfed.org/fred/series/observations` | API |
| Rendimiento bono 10 años (%) | México | Banxico, SIE | SF44071 | `https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF44071/datos/2005-01-01/2025-12-31` | API |
| Rendimiento bono 10 años (%) | Perú | BCRPData | PD31895MM | `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD31895MM/json/2005-1/2025-12` | API |
| Inflación anual (%) | Los 4 | Banco Mundial, WDI | FP.CPI.TOTL.ZG | `https://api.worldbank.org/v2/country/PER;CHL;COL;MEX/indicator/FP.CPI.TOTL.ZG?format=json&date=2005:2025` | API |
| Tipo de cambio (moneda local por USD) | Los 4 | Yahoo Finance | PEN=X, CLP=X, COP=X, MXN=X | librería `yfinance`, intervalo mensual | API |
| Prima por riesgo país, CRP (%) | Los 4 | Damodaran (NYU Stern) | ctryprem04.xls … ctryprem24.xlsx | página rastreada: `https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html`; archivos: `https://pages.stern.nyu.edu/~adamodar/pc/archives/ctrypremYY.xls(x)` | Scraping + descarga programática |

**Ventana de datos:** `FECHA_INICIO = 2005-01-01`, `FECHA_CORTE = 2025-12-31` (parámetros fijos en el código).
**Fechas de extracción:** 19/11/2026 (vía API) y 21/11/2026 (scraping de Damodaran).

## Estructura del repositorio

```
codigo/
  01_extraccion_api.py      Consumo de las API y guardado de los datos crudos
  02_scraping_web.py        Rastreo de Damodaran, extracción y validación de la CRP, consolidado de crudos
  03_limpieza_datos.py      Armonización, imputación documentada, atípicos, unión y hash
  04_analisis.py            Descriptivos, pruebas, estimaciones, tablas y figuras
datos_crudos/
  datos_crudos_2024200519L.csv   Todos los crudos en formato largo (2 727 filas, sin editar)
  damodaran_crp_anual.csv        CRP extraída de cada archivo de Damodaran (84 filas)
  damodaran/                     21 archivos ctryprem tal como se descargaron
  fred_*, banxico_*, bcrp_*, bm_*, yahoo_*.csv   Respuesta de cada API
datos_procesados/
  datos_procesados_2024200519L.csv   Base final: 1 004 filas × 10 columnas
salidas/                     Tablas (.csv), resumen de modelos (.txt) y figuras (.png)
diccionario_variables.md
incidencias_fuente.md
requirements.txt
.env.example
log_ejecucion.txt
hash_sha256.txt
enlace_repositorio_github.txt
```

## Orden de ejecución

Los scripts se ejecutan en orden, desde la carpeta raíz del proyecto:

```bash
pip install -r requirements.txt
cp .env.example .env          # y colocar las claves propias en .env
python codigo/01_extraccion_api.py
python codigo/02_scraping_web.py
python codigo/03_limpieza_datos.py
python codigo/04_analisis.py
```

En Google Colab, después de montar Drive y ubicarse en la carpeta del proyecto, se usan los mismos comandos con `!` delante. Las claves se cargan desde los Secretos de Colab como variables de entorno.

### Claves de API

| Variable | Cómo obtenerla |
|---|---|
| `FRED_API_KEY` | Gratuita: crear una cuenta en https://fred.stlouisfed.org y solicitarla en *My Account → API Keys* |
| `BANXICO_TOKEN` | Gratuito: https://www.banxico.org.mx/SieAPIRest/service/v1/token |

BCRPData, Banco Mundial, Yahoo Finance y Damodaran no requieren clave. Ninguna clave personal está incluida en el código ni en el repositorio.

## Tratamiento de los datos

- **Datos crudos:** se guardan tal como los entrega cada fuente y no se editan.
- **México:** el Bono M a 10 años no se subasta todos los meses. Se usa la tasa de la última subasta vigente al cierre de cada mes; los 61 meses sin subasta conservan la tasa de la subasta anterior y quedan marcados como `imputado_ultima_subasta`. La imputación fue autorizada por el docente el 18/11/2026 (ver `incidencias_fuente.md`).
- **CRP e inflación:** las fuentes son anuales. El valor publicado para cada año se repite en sus 12 meses, sin interpolar, de modo que cada valor de la base coincide con la cifra publicada. La CRP del año T corresponde al archivo que Damodaran publicó el 1 de enero de T.
- **Depreciación:** variación porcentual interanual del tipo de cambio de cierre de mes: (TC_t / TC_t−12 − 1) × 100. Un valor positivo indica depreciación de la moneda local.
- **Atípicos:** se identifican por país con la regla de 3 × rango intercuartílico y se conservan, porque corresponden a episodios reales (crisis de 2008-09, caída del petróleo en 2014-16, pandemia de 2020, inflación de 2021-23).
- **Perú:** la serie del bono a 10 años empieza en mayo de 2005, por eso Perú tiene 248 meses y los demás países 252.

## Métodos

Estadística descriptiva, correlaciones, VIF, raíz unitaria (ADF por país y Fisher-ADF para el panel), MCO agrupado, efectos fijos y efectos fijos con errores Driscoll-Kraay (modelo principal). Pruebas: F de efectos individuales, LM de Breusch-Pagan, Breusch-Pagan de heterocedasticidad, Wooldridge AR(1) y Pesaran CD.

Comparación entre países: regresiones por país con errores de Newey-West (4 rezagos) y prueba F de homogeneidad de pendientes.

Robustez: modelo sin los meses imputados de México; modelo con efectos fijos de país y de mes (errores Driscoll-Kraay), que absorbe los choques comunes; regresiones por país con Newey-West de 12 rezagos; y prueba de Wald de homogeneidad con errores Driscoll-Kraay.

No se usa el modelo de efectos aleatorios: los cuatro países son toda la Alianza del Pacífico (no una muestra aleatoria) y, con solo cuatro países, los componentes de varianza de ese modelo y la prueba de Hausman serían poco fiables. Los resultados se interpretan como asociaciones, no como efectos causales.

## Fuentes de datos (APA 7.ª ed.)

Banco Central de Reserva del Perú. (2026). *Rendimiento de los bonos del Gobierno peruano a 10 años (PD31895MM)* [Conjunto de datos]. BCRPData. Recuperado el 19 de noviembre de 2026, de https://estadisticas.bcrp.gob.pe/estadisticas/series/

Banco de México. (2026). *Valores gubernamentales: resultados de la subasta semanal, tasa de rendimiento, Bono tasa fija 10 años (SF44071)* [Conjunto de datos]. Sistema de Información Económica. Recuperado el 19 de noviembre de 2026, de https://www.banxico.org.mx/SieAPIRest/service/v1/

Damodaran, A. (2005-2025). *Country default spreads and risk premiums* [Conjunto de datos; archivos ctryprem04 a ctryprem24]. Stern School of Business, New York University. Recuperado el 21 de noviembre de 2026, de https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html

Organisation for Economic Co-operation and Development. (2026). *Interest rates: Long-term government bond yields: 10-year: Main (including benchmark) for Chile (IRLTLT01CLM156N) and for Colombia (COLIRLTLT01STM)* [Conjunto de datos]. FRED, Federal Reserve Bank of St. Louis. Recuperado el 19 de noviembre de 2026, de https://fred.stlouisfed.org/

World Bank. (2026). *Inflation, consumer prices (annual %) (FP.CPI.TOTL.ZG)* [Conjunto de datos]. World Development Indicators. Recuperado el 19 de noviembre de 2026, de https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG

Yahoo Finance. (2026). *Tipos de cambio USD/PEN, USD/CLP, USD/COP y USD/MXN (PEN=X, CLP=X, COP=X, MXN=X), datos históricos mensuales* [Conjunto de datos]. Recuperado el 19 de noviembre de 2026, de https://finance.yahoo.com/

## Ética del rastreo

`02_scraping_web.py` consulta `robots.txt` antes de cada solicitud, se identifica con un User-Agent propio (`UNCP-Finanzas1-Tema64/1.0 (proyecto academico)`), espera 2 segundos entre solicitudes y solo descarga archivos que la fuente publica abiertamente. Cuando el índice de directorio respondió HTTP 403, no se intentó evadir el bloqueo: se usó la página pública que enlaza los mismos archivos (ver `incidencias_fuente.md`).

## Declaración de uso de inteligencia artificial

En este proyecto se usó Claude (Anthropic) como asistente para redactar y depurar el código, revisar la disponibilidad de las fuentes, preparar la documentación y elaborar un primer borrador del artículo. Las decisiones del proyecto (tema, variables, fuentes, tratamiento de los datos y lectura de los resultados), la ejecución de todos los scripts y la verificación de cada salida las realicé yo, y puedo explicar cada bloque del código.

## Versiones

Python 3.13.18 (Google Colab). Las versiones exactas de las librerías están en `requirements.txt`.

## Integridad del archivo procesado

```
SHA-256 (datos_procesados/datos_procesados_2024200519L.csv):
9c36941eaee7bebecfa65bf2f9f522dec1b8c046c69e3d77ff0956e709a7cea5
```

El hash se calcula al final de `03_limpieza_datos.py` y queda registrado en `log_ejecucion.txt`. Como las fuentes son vivas, una reextracción futura puede incorporar revisiones oficiales de los datos y producir un hash distinto; el hash declarado corresponde al archivo entregado.

## Registro de ejecución

`log_ejecucion.txt` registra la fecha y hora (Lima), las filas descargadas y el código HTTP de cada consulta. Incluye también los intentos fallidos (HTTP 403 del índice de archivos de Damodaran y una primera corrida incompleta de `04_analisis.py`) y las ejecuciones posteriores de `04_analisis.py` del 26 y 27 de noviembre de 2026, en las que se agregaron figuras, regresiones por país y pruebas de robustez sin modificar los datos, como evidencia del proceso de trabajo.
