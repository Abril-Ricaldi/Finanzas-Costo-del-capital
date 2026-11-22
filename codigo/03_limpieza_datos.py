# Nombres y apellidos: Abril Shantal Ricaldi Bravo
# Código de matrícula: 2024200519L
# Tema N.º 64 del temario: Costo del capital en mercados emergentes: Perú, Chile, Colombia y México
# Fecha de extracción: 19/11/2026 (API) y 21/11/2026 (scraping)
"""
03_limpieza_datos.py
Curso    : Finanzas I (055D) · UNCP · 2026-II

Construye la base procesada a partir de datos_crudos_2024200519L.csv:
  - rend10a      : rendimiento del bono soberano a 10 años (%), mensual.
                   México: última subasta del mes; meses sin subasta se
                   completan con la última subasta vigente (imputación
                   autorizada por el docente, marcada en rend10a_tipo).
  - crp          : prima por riesgo país de Damodaran (%), anual repetida.
  - inflacion    : inflación anual IPC del Banco Mundial (%), anual repetida.
  - depreciacion : variación % interanual del tipo de cambio (moneda local
                   por USD, cierre de mes). Positivo = depreciación.
Llave: pais + fecha (AAAA-MM). Identifica atípicos (se conservan) y calcula
el hash SHA-256 del archivo final.
"""

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# 1. PARÁMETROS
# ------------------------------------------------------------------
FECHA_INICIO = '2005-01'
FECHA_CORTE = '2025-12'
CODIGO = '2024200519L'
ZONA = ZoneInfo('America/Lima')

BASE = Path(__file__).resolve().parent.parent
CRUDOS = BASE / 'datos_crudos'
PROCESADOS = BASE / 'datos_procesados'
SALIDAS = BASE / 'salidas'
LOG = BASE / 'log_ejecucion.txt'
PROCESADOS.mkdir(exist_ok=True)
SALIDAS.mkdir(exist_ok=True)

NOMBRES = {'CHL': 'Chile', 'COL': 'Colombia', 'MEX': 'Mexico', 'PER': 'Peru'}
MESES = pd.period_range(FECHA_INICIO, FECHA_CORTE, freq='M')
SUSTANTIVAS = ['rend10a', 'crp', 'inflacion', 'depreciacion']
FACTOR_RIC = 3  # regla de Tukey para atípicos extremos


# ------------------------------------------------------------------
# 2. FUNCIONES DE APOYO
# ------------------------------------------------------------------
def registrar(mensaje):
    linea = f'[{datetime.now(ZONA):%Y-%m-%d %H:%M:%S}] 03_limpieza_datos | {mensaje}'
    print(linea)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(linea + '\n')


def a_numero(serie):
    """Convierte texto a número; 'N/E', '.', 'n.d.' quedan como vacío."""
    return pd.to_numeric(serie, errors='coerce')


# ------------------------------------------------------------------
# 3. CONSTRUCCIÓN DE CADA VARIABLE
# ------------------------------------------------------------------
def construir_rendimiento(crudos):
    partes = []

    # Chile y Colombia (FRED) y Perú (BCRP): series mensuales
    mens = crudos[(crudos['variable'] == 'rend_bono10a') & (crudos['frecuencia'] == 'M')].copy()
    mens['valor'] = a_numero(mens['valor'])
    mens = mens.dropna(subset=['valor'])
    mens['fecha'] = pd.PeriodIndex(mens['periodo'], freq='M')
    mens['rend10a_tipo'] = 'observado'
    partes.append(mens[['pais', 'fecha', 'valor', 'rend10a_tipo']])

    # México (Banxico): resultados de subasta
    mx = crudos[(crudos['variable'] == 'rend_bono10a') & (crudos['pais'] == 'MEX')].copy()
    mx['valor'] = a_numero(mx['valor'])
    mx = mx.dropna(subset=['valor'])
    mx['dia'] = pd.to_datetime(mx['periodo'])
    mx['fecha'] = mx['dia'].dt.to_period('M')
    dobles = int((mx.groupby('fecha').size() > 1).sum())
    mx = mx.sort_values('dia').groupby('fecha').last()          # última subasta del mes
    mx = mx.reindex(MESES)
    mx['rend10a_tipo'] = np.where(mx['valor'].isna(), 'imputado_ultima_subasta', 'observado')
    mx['valor'] = mx['valor'].ffill()                           # última subasta vigente
    mx['pais'] = 'MEX'
    mx = mx.rename_axis('fecha').reset_index().dropna(subset=['valor'])
    imputados = int((mx['rend10a_tipo'] == 'imputado_ultima_subasta').sum())
    registrar(f'México: {len(mx) - imputados} meses observados, {imputados} imputados '
              f'(última subasta vigente), {dobles} meses con 2+ subastas (se usa la última)')
    partes.append(mx[['pais', 'fecha', 'valor', 'rend10a_tipo']])

    y = pd.concat(partes, ignore_index=True).rename(columns={'valor': 'rend10a'})
    return y[(y['fecha'] >= MESES[0]) & (y['fecha'] <= MESES[-1])]


def expandir_anual(crudos, variable, nombre, factor=1.0):
    """Repite el valor anual en los 12 meses del año (sin interpolar)."""
    a = crudos[crudos['variable'] == variable].copy()
    a[nombre] = a_numero(a['valor']) * factor
    a['anio'] = a['periodo'].astype(int)
    meses = pd.DataFrame({'fecha': MESES})
    meses['anio'] = meses['fecha'].dt.year
    out = a[['pais', 'anio', nombre]].merge(meses, on='anio')
    out[f'{nombre}_tipo'] = 'anual_repetido'
    return out[['pais', 'fecha', nombre, f'{nombre}_tipo']]


def construir_depreciacion(crudos):
    tc = crudos[crudos['variable'] == 'tipo_cambio'].copy()
    tc['tipo_cambio'] = a_numero(tc['valor'])
    tc['fecha'] = pd.PeriodIndex(tc['periodo'], freq='M')
    tc = tc[['pais', 'fecha', 'tipo_cambio']]
    previo = tc.copy()
    previo['fecha'] = previo['fecha'] + 12                      # mismo mes, año siguiente
    previo = previo.rename(columns={'tipo_cambio': 'tc_hace_12m'})
    tc = tc.merge(previo, on=['pais', 'fecha'], how='left')
    tc['depreciacion'] = (tc['tipo_cambio'] / tc['tc_hace_12m'] - 1) * 100
    return tc[['pais', 'fecha', 'tipo_cambio', 'depreciacion']]


def identificar_atipicos(panel):
    """Regla de Tukey extrema (3 x RIC) por país y variable.

    Los atípicos se identifican y se CONSERVAN: corresponden a episodios
    reales (crisis 2008-09, caída del petróleo 2014-16, pandemia 2020,
    inflación 2021-23), no a errores de la fuente. Eliminarlos quitaría
    justamente los periodos de estrés que interesan al estudio.
    """
    filas = []
    for pais, d in panel.groupby('pais'):
        for v in SUSTANTIVAS:
            q1, q3 = d[v].quantile([0.25, 0.75])
            ric = q3 - q1
            lim_inf, lim_sup = q1 - FACTOR_RIC * ric, q3 + FACTOR_RIC * ric
            fuera = d[(d[v] < lim_inf) | (d[v] > lim_sup)]
            for _, f in fuera.iterrows():
                filas.append({'pais': NOMBRES[pais], 'fecha': str(f['fecha']), 'variable': v,
                              'valor': round(f[v], 4), 'limite_inferior': round(lim_inf, 4),
                              'limite_superior': round(lim_sup, 4)})
    tabla = pd.DataFrame(filas, columns=['pais', 'fecha', 'variable', 'valor',
                                         'limite_inferior', 'limite_superior'])
    tabla.to_csv(SALIDAS / 'tabla0_atipicos.csv', index=False)
    resumen = tabla.groupby(['pais', 'variable']).size().to_dict() if len(tabla) else {}
    registrar(f'Atípicos (regla {FACTOR_RIC} x RIC por país): {len(tabla)} identificados y conservados '
              f'-> salidas/tabla0_atipicos.csv | {resumen}')


# ------------------------------------------------------------------
# 4. EJECUCIÓN
# ------------------------------------------------------------------
if __name__ == '__main__':
    registrar('=== Inicio de la limpieza y unión de datos ===')
    registrar(f'Python {sys.version.split()[0]} | pandas {pd.__version__} | numpy {np.__version__}')

    ruta_crudos = CRUDOS / f'datos_crudos_{CODIGO}.csv'
    crudos = pd.read_csv(ruta_crudos, dtype=str)
    registrar(f'Lectura {ruta_crudos.name} | {len(crudos)} filas')

    y = construir_rendimiento(crudos)
    crp = expandir_anual(crudos, 'crp', 'crp', factor=100)      # decimal -> %
    inf = expandir_anual(crudos, 'inflacion', 'inflacion')
    dep = construir_depreciacion(crudos)

    # Unión por la llave pais + fecha (la base la define la variable Y)
    panel = (y.merge(crp, on=['pais', 'fecha'], how='left')
              .merge(inf, on=['pais', 'fecha'], how='left')
              .merge(dep, on=['pais', 'fecha'], how='left'))

    # Control de vacíos: no debe faltar ninguna variable sustantiva
    vacios = panel[SUSTANTIVAS].isna().sum()
    if vacios.sum() > 0:
        registrar(f'ERROR: vacíos por variable: {vacios.to_dict()}')
        raise SystemExit('Hay datos faltantes en la base procesada. Revisar el log.')

    # Control de atípicos (se informan, no se eliminan)
    for v in SUSTANTIVAS:
        rangos = panel.groupby('pais')[v].agg(['min', 'max']).round(2)
        registrar(f'Rango de {v} por país: {rangos.to_dict("index")}')
    identificar_atipicos(panel)

    # Formato final
    panel['pais'] = panel['pais'].map(NOMBRES)
    panel['fecha'] = panel['fecha'].astype(str)
    columnas = ['pais', 'fecha'] + SUSTANTIVAS + ['tipo_cambio', 'rend10a_tipo',
                                                  'crp_tipo', 'inflacion_tipo']
    panel = panel[columnas].sort_values(['pais', 'fecha']).reset_index(drop=True)
    panel[SUSTANTIVAS + ['tipo_cambio']] = panel[SUSTANTIVAS + ['tipo_cambio']].round(6)

    salida = PROCESADOS / f'datos_procesados_{CODIGO}.csv'
    panel.to_csv(salida, index=False)

    por_pais = panel.groupby('pais').size().to_dict()
    registrar(f'Base procesada -> {salida.name} | {len(panel)} filas x {panel.shape[1]} columnas | {por_pais}')

    sha = hashlib.sha256(salida.read_bytes()).hexdigest()
    registrar(f'SHA-256 de {salida.name}: {sha}')
    registrar('=== Fin de la limpieza y unión de datos ===')
