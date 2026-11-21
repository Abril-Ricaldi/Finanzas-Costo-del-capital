"""
01_extraccion_api.py
Proyecto : Costo del capital en mercados emergentes: Perú, Chile, Colombia y México
Autora   : Abril Shantal Ricaldi Bravo · Código 2024200519L
Curso    : Finanzas I (055D) · UNCP · 2026-II · Tema 64

Descarga por API:
  - Rendimiento del bono soberano a 10 años: FRED (Chile, Colombia),
    Banxico SIE (México) y BCRPData (Perú)
  - Inflación anual (IPC, %): Banco Mundial WDI
  - Tipo de cambio mensual frente al USD: Yahoo Finance
Los archivos se guardan tal como salen de la fuente en /datos_crudos.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf

# ------------------------------------------------------------------
# 1. PARÁMETROS
# ------------------------------------------------------------------
FECHA_INICIO = '2005-01-01'
FECHA_CORTE = '2025-12-31'
# El tipo de cambio empieza 12 meses antes para calcular la
# depreciación interanual desde enero de 2005
FECHA_INICIO_TC = '2004-01-01'

BASE = Path(__file__).resolve().parent.parent
CRUDOS = BASE / 'datos_crudos'
LOG = BASE / 'log_ejecucion.txt'
CRUDOS.mkdir(exist_ok=True)

# Claves de API desde variables de entorno (ver .env.example)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE / '.env')
except ImportError:
    pass

FRED_API_KEY = os.getenv('FRED_API_KEY')
BANXICO_TOKEN = os.getenv('BANXICO_TOKEN')

HEADERS = {'User-Agent': 'UNCP-Finanzas1-Tema64/1.0 (proyecto academico)'}


# ------------------------------------------------------------------
# 2. FUNCIONES DE APOYO
# ------------------------------------------------------------------
def registrar(mensaje):
    """Imprime el mensaje y lo agrega a log_ejecucion.txt con fecha y hora de Lima."""
    linea = f'[{datetime.now(ZoneInfo("America/Lima")):%Y-%m-%d %H:%M:%S}] 01_extraccion_api | {mensaje}'
    print(linea)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(linea + '\n')


def consultar(url, params=None, headers=None, intentos=3, pausa=2):
    """GET con reintentos. Las claves nunca se escriben en el log."""
    for i in range(1, intentos + 1):
        try:
            r = requests.get(url, params=params,
                             headers={**HEADERS, **(headers or {})}, timeout=60)
            if r.status_code == 200:
                return r
            registrar(f'Intento {i}: HTTP {r.status_code} en {url}')
        except requests.RequestException as e:
            registrar(f'Intento {i}: error de conexión en {url}: {type(e).__name__}')
        time.sleep(pausa * i)
    raise RuntimeError(f'No se pudo descargar {url} tras {intentos} intentos')


# ------------------------------------------------------------------
# 3. EXTRACCIONES
# ------------------------------------------------------------------
def extraer_fred():
    """Bono 10 años de Chile y Colombia (OCDE vía FRED)."""
    url = 'https://api.stlouisfed.org/fred/series/observations'
    series = {'CHL': 'IRLTLT01CLM156N', 'COL': 'COLIRLTLT01STM'}
    for pais, sid in series.items():
        params = {'series_id': sid, 'api_key': FRED_API_KEY, 'file_type': 'json',
                  'observation_start': FECHA_INICIO, 'observation_end': FECHA_CORTE}
        r = consultar(url, params=params)
        df = pd.DataFrame(r.json()['observations'])
        archivo = CRUDOS / f'fred_bono10a_{pais}.csv'
        df.to_csv(archivo, index=False)
        registrar(f'FRED {sid} ({pais}) | HTTP {r.status_code} | {len(df)} filas -> {archivo.name}')
        time.sleep(1)


def extraer_banxico():
    """Bono M 10 años de México: resultados de subasta (Banxico SIE)."""
    sid = 'SF44071'
    url = (f'https://www.banxico.org.mx/SieAPIRest/service/v1/series/'
           f'{sid}/datos/{FECHA_INICIO}/{FECHA_CORTE}')
    r = consultar(url, headers={'Bmx-Token': BANXICO_TOKEN})
    serie = r.json()['bmx']['series'][0]
    df = pd.DataFrame(serie['datos'])
    df['serie'] = sid
    archivo = CRUDOS / 'banxico_bono10a_MEX.csv'
    df.to_csv(archivo, index=False)
    con_dato = (df['dato'] != 'N/E').sum()
    registrar(f'Banxico {sid} (MEX) | HTTP {r.status_code} | {len(df)} registros '
              f'({con_dato} subastas con dato) -> {archivo.name}')
    time.sleep(1)


def extraer_bcrp():
    """Bono 10 años de Perú (BCRPData)."""
    cod = 'PD31895MM'
    ini = pd.Timestamp(FECHA_INICIO)
    fin = pd.Timestamp(FECHA_CORTE)
    url = (f'https://estadisticas.bcrp.gob.pe/estadisticas/series/api/'
           f'{cod}/json/{ini.year}-{ini.month}/{fin.year}-{fin.month}')
    r = consultar(url)
    periodos = r.json()['periods']
    df = pd.DataFrame({'periodo': [p['name'] for p in periodos],
                       'valor': [p['values'][0] for p in periodos],
                       'serie': cod})
    archivo = CRUDOS / 'bcrp_bono10a_PER.csv'
    df.to_csv(archivo, index=False)
    registrar(f'BCRP {cod} (PER) | HTTP {r.status_code} | {len(df)} filas -> {archivo.name}')
    time.sleep(1)


def extraer_banco_mundial():
    """Inflación anual, IPC (%), de los 4 países (Banco Mundial WDI)."""
    url = 'https://api.worldbank.org/v2/country/PER;CHL;COL;MEX/indicator/FP.CPI.TOTL.ZG'
    params = {'format': 'json', 'per_page': 500,
              'date': f'{FECHA_INICIO[:4]}:{FECHA_CORTE[:4]}'}
    r = consultar(url, params=params)
    datos = r.json()[1]
    df = pd.DataFrame([{'pais_iso3': d['countryiso3code'],
                        'pais': d['country']['value'],
                        'anio': d['date'],
                        'valor': d['value'],
                        'indicador': d['indicator']['id']} for d in datos])
    archivo = CRUDOS / 'bm_inflacion_anual.csv'
    df.to_csv(archivo, index=False)
    vacios = df['valor'].isna().sum()
    registrar(f'Banco Mundial FP.CPI.TOTL.ZG | HTTP {r.status_code} | {len(df)} filas '
              f'({vacios} sin dato) -> {archivo.name}')
    time.sleep(1)


def extraer_yahoo():
    """Tipo de cambio mensual (moneda local por USD) desde Yahoo Finance."""
    fin = (pd.Timestamp(FECHA_CORTE) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    for ticker in ['PEN=X', 'CLP=X', 'COP=X', 'MXN=X']:
        df = yf.download(ticker, start=FECHA_INICIO_TC, end=fin, interval='1mo',
                         auto_adjust=False, progress=False)
        if df.empty:
            raise RuntimeError(f'Yahoo no devolvió datos para {ticker}')
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        archivo = CRUDOS / f"yahoo_tc_{ticker.replace('=X', '')}.csv"
        df.to_csv(archivo)
        registrar(f'Yahoo {ticker} | {len(df)} meses '
                  f'({df.index.min():%Y-%m} a {df.index.max():%Y-%m}) -> {archivo.name}')
        time.sleep(1)


# ------------------------------------------------------------------
# 4. EJECUCIÓN
# ------------------------------------------------------------------
if __name__ == '__main__':
    registrar('=== Inicio de la extracción por API ===')
    registrar(f'Python {sys.version.split()[0]} | pandas {pd.__version__} | '
              f'requests {requests.__version__} | yfinance {yf.__version__}')
    registrar(f'Ventana: {FECHA_INICIO} a {FECHA_CORTE}')

    if not FRED_API_KEY or not BANXICO_TOKEN:
        raise SystemExit('Faltan FRED_API_KEY o BANXICO_TOKEN. Revisa .env.example')

    for paso in (extraer_fred, extraer_banxico, extraer_bcrp,
                 extraer_banco_mundial, extraer_yahoo):
        paso()

    registrar('=== Fin de la extracción por API ===')
