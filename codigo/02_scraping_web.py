"""
02_scraping_web.py
Proyecto : Costo del capital en mercados emergentes: Perú, Chile, Colombia y México
Autora   : Abril Shantal Ricaldi Bravo · Código 2024200519L
Curso    : Finanzas I (055D) · UNCP · 2026-II · Tema 64

Vía 2 (web scraping / descarga programática):
  1. Rastrea la página de datos archivados de Aswath Damodaran (NYU Stern),
     identifica los archivos de primas por riesgo país (ctryprem) de cada
     enero y los descarga intactos en /datos_crudos/damodaran/.
  2. Lee la prima por riesgo país (CRP, basada en la calificación de
     Moody's) de Chile, Colombia, México y Perú en cada archivo y la valida.
  3. Consolida todos los datos crudos (API + scraping) en
     datos_crudos_2024200519L.csv, en formato largo y sin editar valores.

Convención de la fuente: la etiqueta "1/YY" corresponde a los datos
publicados el 1 de enero de 20YY; el archivo lleva el año anterior en el
nombre (ej.: "1/06" -> ctryprem05.xls). La CRP del año T es la publicada
en enero de T, vigente durante ese año.
"""

import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ------------------------------------------------------------------
# 1. PARÁMETROS
# ------------------------------------------------------------------
ANIO_INICIO = 2005
ANIO_FIN = 2025
CODIGO = '2024200519L'
ZONA = ZoneInfo('America/Lima')

BASE = Path(__file__).resolve().parent.parent
CRUDOS = BASE / 'datos_crudos'
DESTINO = CRUDOS / 'damodaran'
LOG = BASE / 'log_ejecucion.txt'
DESTINO.mkdir(parents=True, exist_ok=True)

SITIO = 'https://pages.stern.nyu.edu'
PAGINA = 'https://pages.stern.nyu.edu/~adamodar/New_Home_Page/dataarchived.html'
PATRON_ARCHIVO = re.compile(r'ctryprem(\d{2})\.xlsx?$', re.IGNORECASE)
PATRON_ETIQUETA = re.compile(r'1/(\d{2})')

PAISES = {'Chile': 'CHL', 'Colombia': 'COL', 'Mexico': 'MEX', 'Peru': 'PER'}
TOLERANCIA = 1e-6

HEADERS = {'User-Agent': 'UNCP-Finanzas1-Tema64/1.0 (proyecto academico)'}
PAUSA = 2  # segundos entre solicitudes

MESES_BCRP = {'Ene': 1, 'Feb': 2, 'Mar': 3, 'Abr': 4, 'May': 5, 'Jun': 6,
              'Jul': 7, 'Ago': 8, 'Sep': 9, 'Set': 9, 'Oct': 10, 'Nov': 11, 'Dic': 12}


# ------------------------------------------------------------------
# 2. FUNCIONES DE APOYO
# ------------------------------------------------------------------
def registrar(mensaje):
    linea = f'[{datetime.now(ZONA):%Y-%m-%d %H:%M:%S}] 02_scraping_web | {mensaje}'
    print(linea)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(linea + '\n')


def consultar(url, intentos=3):
    for i in range(1, intentos + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r
            registrar(f'Intento {i}: HTTP {r.status_code} en {url}')
        except requests.RequestException as e:
            registrar(f'Intento {i}: error de conexión en {url}: {type(e).__name__}')
        time.sleep(PAUSA * i)
    raise RuntimeError(f'No se pudo descargar {url} tras {intentos} intentos')


def cargar_robots():
    """Lee robots.txt del sitio. Si no existe (404), se permite rastrear."""
    rp = RobotFileParser()
    r = requests.get(SITIO + '/robots.txt', headers=HEADERS, timeout=30)
    rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    registrar(f'robots.txt | HTTP {r.status_code}')
    return rp


# ------------------------------------------------------------------
# 3. PASO 1: RASTREO Y DESCARGA
# ------------------------------------------------------------------
def rastrear_pagina(robots):
    """Devuelve {año de vigencia: url del archivo ctryprem de ese enero}."""
    if not robots.can_fetch(HEADERS['User-Agent'], PAGINA):
        raise SystemExit(f'robots.txt no permite rastrear {PAGINA}')
    r = consultar(PAGINA)
    soup = BeautifulSoup(r.text, 'html.parser')
    enlaces = {}
    for a in soup.find_all('a', href=True):
        m_archivo = PATRON_ARCHIVO.search(a['href'])
        if not m_archivo:
            continue
        m_etiqueta = PATRON_ETIQUETA.search(a.get_text(' ', strip=True))
        if m_etiqueta:
            anio = 2000 + int(m_etiqueta.group(1))
        else:
            # Sin etiqueta visible: se aplica la convención de la fuente
            anio = 2000 + int(m_archivo.group(1)) + 1
        enlaces[anio] = urljoin(PAGINA, a['href'])
    registrar(f'Página {PAGINA} | HTTP {r.status_code} | {len(enlaces)} enlaces ctryprem encontrados')
    time.sleep(PAUSA)
    return enlaces


def descargar(anio, url, robots):
    if not robots.can_fetch(HEADERS['User-Agent'], url):
        registrar(f'robots.txt no permite {url}: se omite')
        return None
    r = consultar(url)
    archivo = DESTINO / url.split('/')[-1]
    archivo.write_bytes(r.content)
    registrar(f'Enero {anio} -> {archivo.name} | HTTP {r.status_code} | {len(r.content)/1024:.0f} KB')
    time.sleep(PAUSA)
    return archivo


# ------------------------------------------------------------------
# 4. PASO 2: EXTRACCIÓN Y VALIDACIÓN DE LA CRP
# ------------------------------------------------------------------
def extraer_crp(anio, archivo):
    """Lee la CRP (basada en calificación) de los 4 países en un archivo.

    Formatos de la fuente:
      2005-2008: [País, Rating, Spread, ERP total, CRP]          -> CRP en col. 4
      2009-2025: [País, Región, Rating, Spread, ERP total, CRP]  -> CRP en col. 5
    Validación: ERP total - ERP madura (EE. UU.) = CRP.
    """
    xl = pd.ExcelFile(archivo)
    hoja = 'ERPs by country' if 'ERPs by country' in xl.sheet_names else 'Country premiums'
    df = xl.parse(hoja, header=None)
    col0 = df[0].astype(str).str.strip()

    fila_madura = df[col0.str.startswith('Enter the current risk premium for a mature equity market')].index[0]
    erp_madura = float(df.iloc[fila_madura, 4])

    filas = []
    for nombre, iso in PAISES.items():
        coincidencias = df[col0 == nombre].index
        if len(coincidencias) == 0:
            raise ValueError(f'{nombre} no aparece en {archivo.name}')
        fila = df.iloc[coincidencias[0]]
        con_region = isinstance(fila[2], str)
        c_crp = 5 if con_region else 4
        calificacion = str(fila[2] if con_region else fila[1]).strip()
        erp_total = float(fila[c_crp - 1])
        crp = float(fila[c_crp])

        if abs(erp_total - erp_madura - crp) > TOLERANCIA:
            raise ValueError(f'Validación fallida: {nombre} {anio} ({archivo.name}): '
                             f'{erp_total} - {erp_madura} != {crp}')

        filas.append({'pais_iso3': iso, 'pais': nombre, 'anio_vigencia': anio,
                      'archivo': archivo.name, 'hoja': hoja,
                      'calificacion_moodys': calificacion, 'erp_madura': erp_madura,
                      'erp_total': erp_total, 'crp': crp})
    return filas


# ------------------------------------------------------------------
# 5. PASO 3: CONSOLIDADO DE DATOS CRUDOS (formato largo)
# ------------------------------------------------------------------
def fecha_archivo(ruta):
    return datetime.fromtimestamp(ruta.stat().st_mtime, ZONA).strftime('%Y-%m-%d %H:%M:%S')


def bloque(fuente, codigo, variable, pais, frecuencia, periodos, valores, ruta):
    return pd.DataFrame({'fuente': fuente, 'codigo_serie': codigo, 'variable': variable,
                         'pais': pais, 'frecuencia': frecuencia,
                         'periodo': periodos, 'valor': valores,
                         'fecha_extraccion': fecha_archivo(ruta)})


def consolidar():
    """Une todos los crudos sin modificar los valores (se leen como texto)."""
    partes = []

    for iso, sid in [('CHL', 'IRLTLT01CLM156N'), ('COL', 'COLIRLTLT01STM')]:
        ruta = CRUDOS / f'fred_bono10a_{iso}.csv'
        d = pd.read_csv(ruta, dtype=str)
        partes.append(bloque('FRED', sid, 'rend_bono10a', iso, 'M',
                             d['date'].str[:7].tolist(), d['value'].tolist(), ruta))

    ruta = CRUDOS / 'banxico_bono10a_MEX.csv'
    d = pd.read_csv(ruta, dtype=str)
    fechas = pd.to_datetime(d['fecha'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
    partes.append(bloque('Banxico', 'SF44071', 'rend_bono10a', 'MEX', 'W',
                         fechas.tolist(), d['dato'].tolist(), ruta))

    ruta = CRUDOS / 'bcrp_bono10a_PER.csv'
    d = pd.read_csv(ruta, dtype=str)
    periodos = [f"{p.split('.')[1]}-{MESES_BCRP[p.split('.')[0]]:02d}" for p in d['periodo']]
    partes.append(bloque('BCRP', 'PD31895MM', 'rend_bono10a', 'PER', 'M',
                         periodos, d['valor'].tolist(), ruta))

    ruta = CRUDOS / 'bm_inflacion_anual.csv'
    d = pd.read_csv(ruta, dtype=str)
    partes.append(bloque('Banco Mundial', 'FP.CPI.TOTL.ZG', 'inflacion', d['pais_iso3'].tolist(), 'A',
                         d['anio'].tolist(), d['valor'].tolist(), ruta))

    for moneda, iso in [('PEN', 'PER'), ('CLP', 'CHL'), ('COP', 'COL'), ('MXN', 'MEX')]:
        ruta = CRUDOS / f'yahoo_tc_{moneda}.csv'
        d = pd.read_csv(ruta, dtype=str)
        partes.append(bloque('Yahoo Finance', f'{moneda}=X', 'tipo_cambio', iso, 'M',
                             d['Date'].str[:7].tolist(), d['Close'].tolist(), ruta))

    ruta = CRUDOS / 'damodaran_crp_anual.csv'
    d = pd.read_csv(ruta, dtype=str)
    partes.append(bloque('Damodaran', d['archivo'].str.replace(r'\.xlsx?$', '', regex=True).tolist(),
                         'crp', d['pais_iso3'].tolist(), 'A',
                         d['anio_vigencia'].tolist(), d['crp'].tolist(), ruta))

    consolidado = pd.concat(partes, ignore_index=True)
    salida = CRUDOS / f'datos_crudos_{CODIGO}.csv'
    consolidado.to_csv(salida, index=False)
    resumen = consolidado.groupby('fuente', sort=False).size().to_dict()
    registrar(f'Consolidado -> {salida.name} | {len(consolidado)} filas | {resumen}')


# ------------------------------------------------------------------
# 6. EJECUCIÓN
# ------------------------------------------------------------------
if __name__ == '__main__':
    registrar('=== Inicio del scraping de Damodaran ===')
    registrar(f'Python {sys.version.split()[0]} | pandas {pd.__version__} | requests {requests.__version__}')

    # Paso 1
    robots = cargar_robots()
    enlaces = rastrear_pagina(robots)
    archivos = {}
    for anio in range(ANIO_INICIO, ANIO_FIN + 1):
        if anio in enlaces:
            archivos[anio] = descargar(anio, enlaces[anio], robots)
        else:
            registrar(f'AVISO: no se encontró enlace ctryprem para enero {anio}')

    # Paso 2
    filas = []
    for anio, archivo in archivos.items():
        if archivo is not None:
            filas.extend(extraer_crp(anio, archivo))
    crp = pd.DataFrame(filas)
    ruta_crp = CRUDOS / 'damodaran_crp_anual.csv'
    crp.to_csv(ruta_crp, index=False)
    registrar(f'CRP extraída y validada -> {ruta_crp.name} | {len(crp)} filas '
              f'({crp["anio_vigencia"].min()}-{crp["anio_vigencia"].max()}, {crp["pais"].nunique()} países)')

    # Paso 3
    consolidar()
    registrar('=== Fin del scraping de Damodaran ===')
