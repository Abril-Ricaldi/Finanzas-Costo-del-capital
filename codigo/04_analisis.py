# Nombres y apellidos: Abril Shantal Ricaldi Bravo
# Código de matrícula: 2024200519L
# Tema N.º 64 del temario: Costo del capital en mercados emergentes: Perú, Chile, Colombia y México
# Fecha de extracción: 19/11/2026 (API) y 21/11/2026 (scraping)
"""
04_analisis.py
Proyecto : Costo del capital en mercados emergentes: Perú, Chile, Colombia y México
Autora   : Abril Shantal Ricaldi Bravo · Código 2024200519L
Curso    : Finanzas I (055D) · UNCP · 2026-II · Tema 64

Modelo: rend10a_it = a_i + b1*crp_it + b2*inflacion_it + b3*depreciacion_it + e_it
Signos esperados: b1 > 0, b2 > 0, b3 > 0.

Genera en /salidas: estadísticos descriptivos, correlaciones, VIF, pruebas de
raíz unitaria, estimaciones (MCO agrupado, efectos fijos, EF con errores
Driscoll-Kraay y robustez sin meses imputados), pruebas de especificación y
diagnóstico, y figuras.

Nota metodológica: el modelo de efectos aleatorios y la prueba de Hausman no
son estimables, porque con 4 países y 4 parámetros (constante + 3 regresores)
la regresión "between" no tiene grados de libertad. Se usan la prueba F y el
LM de Breusch-Pagan para elegir entre MCO agrupado y efectos por país.
"""

import sys
import warnings
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.tsa.stattools import adfuller
from scipy import stats
import linearmodels
from linearmodels.panel import PooledOLS, PanelOLS

warnings.filterwarnings('ignore')

# ------------------------------------------------------------------
# 1. PARÁMETROS
# ------------------------------------------------------------------
CODIGO = '2024200519L'
ZONA = ZoneInfo('America/Lima')

BASE = Path(__file__).resolve().parent.parent
PROCESADOS = BASE / 'datos_procesados'
SALIDAS = BASE / 'salidas'
LOG = BASE / 'log_ejecucion.txt'
SALIDAS.mkdir(exist_ok=True)

Y = 'rend10a'
X = ['crp', 'inflacion', 'depreciacion']
VARIABLES = [Y] + X

ETIQUETAS = {'rend10a': 'Rendimiento del bono soberano a 10 años (%)',
             'crp': 'Prima por riesgo país, CRP (%)',
             'inflacion': 'Inflación anual (%)',
             'depreciacion': 'Depreciación cambiaria interanual (%)'}
FUENTES = {'rend10a': 'FRED (OCDE), Banxico y BCRP',
           'crp': 'Damodaran (NYU Stern)',
           'inflacion': 'Banco Mundial (WDI)',
           'depreciacion': 'Yahoo Finance'}
COLORES = {'Chile': '#2a78d6', 'Colombia': '#eb6834', 'Mexico': '#1baf7a', 'Peru': '#eda100'}
TINTA, TINTA_2, GRILLA = '#0b0b0b', '#52514e', '#e6e5e1'


# ------------------------------------------------------------------
# 2. FUNCIONES DE APOYO
# ------------------------------------------------------------------
def registrar(mensaje):
    linea = f'[{datetime.now(ZONA):%Y-%m-%d %H:%M:%S}] 04_analisis | {mensaje}'
    print(linea)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(linea + '\n')


def estrellas(p):
    return '***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else ''


# ------------------------------------------------------------------
# 3. ESTADÍSTICA DESCRIPTIVA
# ------------------------------------------------------------------
def descriptivos(df):
    filas = []
    for grupo, d in [('Panel', df)] + list(df.groupby('pais')):
        for v in VARIABLES:
            s = d[v]
            filas.append({'grupo': grupo, 'variable': v, 'n': int(s.count()),
                          'media': s.mean(), 'desv_est': s.std(),
                          'min': s.min(), 'max': s.max()})
    tabla = pd.DataFrame(filas).round(4)
    tabla.to_csv(SALIDAS / 'tabla1_descriptivos.csv', index=False)

    corr = df[VARIABLES].corr().round(4)
    corr.to_csv(SALIDAS / 'tabla2_correlaciones.csv')

    xc = sm.add_constant(df[X])
    vif = pd.DataFrame({'variable': X,
                        'vif': [variance_inflation_factor(xc.values, i + 1) for i in range(len(X))]}).round(4)
    vif.to_csv(SALIDAS / 'tabla3_vif.csv', index=False)
    registrar(f'Descriptivos, correlaciones y VIF guardados | VIF máximo = {vif["vif"].max():.2f}')


def raiz_unitaria(df):
    """ADF por país y combinación de Fisher (Maddala-Wu) para el panel."""
    filas = []
    for v in VARIABLES:
        pvalores = []
        for pais, d in df.groupby('pais'):
            serie = d.sort_values('fecha')[v].dropna()
            est, p, *_ = adfuller(serie, autolag='AIC', regression='c')
            pvalores.append(p)
            filas.append({'variable': v, 'unidad': pais, 'estadistico': est, 'p_valor': p})
        p_arr = np.clip(pvalores, 1e-16, 1)
        fisher = -2 * np.sum(np.log(p_arr))
        filas.append({'variable': v, 'unidad': 'Panel (Fisher-ADF)', 'estadistico': fisher,
                      'p_valor': stats.chi2.sf(fisher, 2 * len(p_arr))})
    tabla = pd.DataFrame(filas).round(4)
    tabla.to_csv(SALIDAS / 'tabla4_raiz_unitaria.csv', index=False)
    panel = tabla[tabla['unidad'] == 'Panel (Fisher-ADF)']
    registrar(f'Raíz unitaria (p-valor Fisher-ADF): {dict(zip(panel["variable"], panel["p_valor"]))}')


# ------------------------------------------------------------------
# 4. ESTIMACIÓN
# ------------------------------------------------------------------
def estimar(panel):
    y = panel[Y]
    xc = sm.add_constant(panel[X])
    # Efectos aleatorios no es estimable (4 países y 4 parámetros:
    # la regresión "between" no tiene grados de libertad).
    modelos = {
        'MCO agrupado': PooledOLS(y, xc).fit(cov_type='robust'),
        'Efectos fijos': PanelOLS(y, xc, entity_effects=True).fit(cov_type='robust'),
        'EF Driscoll-Kraay': PanelOLS(y, xc, entity_effects=True).fit(cov_type='kernel'),
    }
    # Robustez: sin los meses imputados de México
    obs = panel[panel['rend10a_tipo'] == 'observado']
    modelos['EF D-K sin imputados'] = PanelOLS(obs[Y], sm.add_constant(obs[X]),
                                               entity_effects=True).fit(cov_type='kernel')
    return modelos


def tablas_modelos(modelos):
    filas = []
    for nombre, r in modelos.items():
        for v in ['const'] + X:
            filas.append({'modelo': nombre, 'variable': v, 'coef': r.params[v],
                          'error_est': r.std_errors[v], 't': r.tstats[v], 'p_valor': r.pvalues[v],
                          'r2': r.rsquared, 'n': int(r.nobs)})
    pd.DataFrame(filas).round(6).to_csv(SALIDAS / 'tabla5_modelos.csv', index=False)

    presentable = pd.DataFrame(
        {nombre: [f'{r.params[v]:.4f}{estrellas(r.pvalues[v])} ({r.std_errors[v]:.4f})'
                  for v in ['const'] + X] + [f'{r.rsquared:.4f}', f'{int(r.nobs)}']
         for nombre, r in modelos.items()},
        index=['const'] + X + ['R2', 'N'])
    presentable.to_csv(SALIDAS / 'tabla5_modelos_presentable.csv')

    with open(SALIDAS / 'resumen_modelos.txt', 'w', encoding='utf-8') as f:
        for nombre, r in modelos.items():
            f.write(f'\n{"=" * 78}\n{nombre}\n{"=" * 78}\n{r.summary}\n')
    registrar('Tablas de modelos y resumen_modelos.txt guardados')


def pruebas(panel, df, modelos):
    y = panel[Y]
    xc = sm.add_constant(panel[X])
    filas = []
    fe = PanelOLS(y, xc, entity_effects=True).fit()

    # LM de Breusch-Pagan para efectos por país (versión de Baltagi-Li para
    # panel desbalanceado). Reemplaza a Hausman, que no es calculable con 4 países.
    e = pd.Series(sm.OLS(y.values, xc.values).fit().resid, index=panel.index)
    t_i = e.groupby(level='pais').size()
    n_obs = t_i.sum()
    suma_i = e.groupby(level='pais').sum()
    lm_re = (n_obs ** 2 / (2 * ((t_i ** 2).sum() - n_obs))) * \
            ((suma_i ** 2).sum() / (e ** 2).sum() - 1) ** 2
    filas.append({'prueba': 'LM Breusch-Pagan (efectos por país)', 'estadistico': lm_re,
                  'p_valor': stats.chi2.sf(lm_re, 1), 'h0': 'Sin efecto por país'})

    # F de efectos individuales (MCO agrupado vs EF)
    filas.append({'prueba': 'F efectos individuales', 'estadistico': fe.f_pooled.stat,
                  'p_valor': fe.f_pooled.pval, 'h0': 'Sin efectos por país'})

    # Breusch-Pagan de heterocedasticidad sobre MCO agrupado
    mco = sm.OLS(y.values, xc.values).fit()
    lm, lm_p, _, _ = het_breuschpagan(mco.resid, xc.values)
    filas.append({'prueba': 'Breusch-Pagan (heterocedasticidad)', 'estadistico': lm,
                  'p_valor': lm_p, 'h0': 'Homocedasticidad'})

    # Wooldridge: autocorrelación de primer orden en paneles
    d = df.sort_values(['pais', 'fecha']).copy()
    for v in VARIABLES:
        d['d_' + v] = d.groupby('pais')[v].diff()
    d = d.dropna(subset=['d_' + v for v in VARIABLES])
    m1 = sm.OLS(d['d_' + Y], d[['d_' + v for v in X]]).fit()
    d['u'] = m1.resid
    d['u_rez'] = d.groupby('pais')['u'].shift(1)
    d = d.dropna(subset=['u_rez'])
    m2 = sm.OLS(d['u'], d[['u_rez']]).fit(cov_type='HC1')
    f_w = ((m2.params['u_rez'] + 0.5) / m2.bse['u_rez']) ** 2
    filas.append({'prueba': 'Wooldridge AR(1)', 'estadistico': f_w,
                  'p_valor': stats.f.sf(f_w, 1, len(d) - 1), 'h0': 'Sin autocorrelación'})

    # Pesaran CD: dependencia entre países (residuos de EF)
    w = fe.resids.unstack('pais')
    paises = list(w.columns)
    suma = 0.0
    for i in range(len(paises)):
        for j in range(i + 1, len(paises)):
            par = w[[paises[i], paises[j]]].dropna()
            suma += np.sqrt(len(par)) * par.corr().iloc[0, 1]
    n = len(paises)
    cd = np.sqrt(2 / (n * (n - 1))) * suma
    filas.append({'prueba': 'Pesaran CD', 'estadistico': cd,
                  'p_valor': 2 * stats.norm.sf(abs(cd)), 'h0': 'Independencia entre países'})

    tabla = pd.DataFrame(filas).round(6)
    tabla.to_csv(SALIDAS / 'tabla6_pruebas.csv', index=False)
    for _, f in tabla.iterrows():
        registrar(f'{f["prueba"]}: estadístico = {f["estadistico"]:.4f}, p-valor = {f["p_valor"]:.4f}')

    elegido = 'Efectos fijos' if tabla.loc[1, 'p_valor'] < 0.05 else 'MCO agrupado'
    registrar(f'Prueba F sugiere: {elegido}. EA y Hausman no estimables (4 países, 4 parámetros). '
              f'Modelo principal: EF con errores Driscoll-Kraay')


# ------------------------------------------------------------------
# 5. FIGURAS
# ------------------------------------------------------------------
def estilo():
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.edgecolor': '#8a8984', 'axes.grid': True, 'grid.color': GRILLA,
                         'grid.linewidth': 0.6, 'xtick.color': TINTA_2, 'ytick.color': TINTA_2,
                         'axes.labelcolor': TINTA_2})


def figura_series(df, v, numero):
    fig, ax = plt.subplots(figsize=(9, 4.8))
    finales = []
    for pais, d in df.groupby('pais'):
        d = d.sort_values('fecha')
        ax.plot(d['fecha'], d[v], color=COLORES[pais], linewidth=1.6, label=pais)
        finales.append([d[v].iloc[-1], pais])

    if v == Y:  # meses imputados de México
        imp = df[df['rend10a_tipo'] != 'observado']
        ax.scatter(imp['fecha'], imp[Y], s=16, facecolors='white', edgecolors=COLORES['Mexico'],
                   linewidths=1, zorder=3, label='Mexico: mes imputado')
    if v == 'depreciacion':
        ax.axhline(0, color='#8a8984', linewidth=0.8)

    # Etiquetas directas al final de cada línea, sin superponerse
    lo, hi = ax.get_ylim()
    separacion = (hi - lo) * 0.06
    finales.sort()
    for k in range(1, len(finales)):
        finales[k][0] = max(finales[k][0], finales[k - 1][0] + separacion)
    x_fin = df['fecha'].max() + pd.Timedelta(days=60)
    for valor, pais in finales:
        ax.text(x_fin, valor, pais, va='center', fontsize=9, color=TINTA_2)
    ax.set_xlim(right=df['fecha'].max() + pd.Timedelta(days=700))

    ax.set_title(ETIQUETAS[v], loc='left', fontsize=12, color=TINTA)
    ax.set_ylabel('%')
    ax.legend(frameon=False, ncol=5, loc='upper left', bbox_to_anchor=(0, -0.07), fontsize=9)
    fig.text(0.01, 0.01, f'Fuente: {FUENTES[v]}. Elaboración propia.', fontsize=8, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(SALIDAS / f'figura{numero}_{v}.png', dpi=200)
    plt.close(fig)


def figura_dispersion(df):
    fig, ejes = plt.subplots(2, 2, figsize=(9, 7), sharex=True, sharey=True)
    for ax, (pais, d) in zip(ejes.flat, df.groupby('pais')):
        ax.scatter(d['crp'], d[Y], s=10, color=COLORES[pais], alpha=0.6, edgecolors='none')
        m, c = np.polyfit(d['crp'], d[Y], 1)
        xs = np.linspace(d['crp'].min(), d['crp'].max(), 50)
        ax.plot(xs, m * xs + c, color=TINTA_2, linewidth=1.2)
        ax.set_title(pais, loc='left', fontsize=10, color=TINTA)
    for ax in ejes[1]:
        ax.set_xlabel('CRP (%)')
    for ax in ejes[:, 0]:
        ax.set_ylabel('Rendimiento 10 años (%)')
    fig.suptitle('Rendimiento del bono a 10 años frente a la prima por riesgo país',
                 x=0.01, ha='left', fontsize=12, color=TINTA)
    fig.text(0.01, 0.01, 'Fuente: FRED, Banxico, BCRP y Damodaran. Elaboración propia.',
             fontsize=8, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    fig.savefig(SALIDAS / 'figura5_dispersion_rend10a_crp.png', dpi=200)
    plt.close(fig)


def figura_correlaciones(df):
    # Figura 6: mapa de calor de la matriz de correlaciones de Pearson (mismos valores que tabla2_correlaciones.csv)
    nombres = {'rend10a': 'Rendimiento\n10 años', 'crp': 'Prima por\nriesgo país',
               'inflacion': 'Inflación', 'depreciacion': 'Depreciación'}
    corr = df[VARIABLES].corr().round(4)
    n = len(VARIABLES)
    fig, ax = plt.subplots(figsize=(6.6, 5.6))
    im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1)
    for i in range(n):
        for j in range(n):
            r = corr.iloc[i, j]
            p = stats.pearsonr(df[VARIABLES[i]], df[VARIABLES[j]])[1] if i != j else 0
            marca = '' if i == j else ('***' if p < 0.01 else '**' if p < 0.05 else '*' if p < 0.10 else '')
            texto = f'{r:.2f}'.replace('.', ',').replace('-', '−') + marca
            ax.text(j, i, texto, ha='center', va='center', fontsize=11,
                    color='white' if abs(r) > 0.6 else TINTA)
    etiquetas = [nombres[v] for v in VARIABLES]
    ax.set_xticks(range(n), etiquetas, fontsize=9)
    ax.set_yticks(range(n), etiquetas, fontsize=9)
    ax.tick_params(length=0)
    ax.grid(False)
    for lado in ax.spines.values():
        lado.set_visible(False)
    barra = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    barra.outline.set_visible(False)
    barra.ax.yaxis.set_major_formatter(lambda x, _: f'{x:.2f}'.replace('.', ',').replace('-', '−'))
    ax.set_title('Matriz de correlaciones de Pearson (n = 1 004)', loc='left', fontsize=12, color=TINTA)
    fig.text(0.01, 0.01, '*** p < 0,01; ** p < 0,05; * p < 0,10. Fuente: FRED, Banxico, BCRP, Damodaran, '
             'Banco Mundial y Yahoo Finance. Elaboración propia.', fontsize=7, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(SALIDAS / 'figura6_correlaciones.png', dpi=200)
    plt.close(fig)


def figura_coeficientes(modelos):
    # Figura 7: coeficientes de los 4 modelos con intervalos de confianza al 95 % (coef ± 1,96 × error estándar)
    nombres = {'crp': 'Prima por riesgo país', 'inflacion': 'Inflación', 'depreciacion': 'Depreciación'}
    lista = list(modelos.keys())
    fig, ejes = plt.subplots(1, 3, figsize=(10, 4.2), sharey=True)
    for ax, v in zip(ejes, X):
        for k, nombre in enumerate(lista):
            r = modelos[nombre]
            b, ee = r.params[v], r.std_errors[v]
            color = '#eb6834' if nombre == 'EF Driscoll-Kraay' else TINTA_2
            ax.errorbar(b, k, xerr=1.96 * ee, fmt='o', color=color, ecolor=color,
                        elinewidth=2, capsize=4, markersize=6)
        ax.axvline(0, color='#8a8984', linewidth=1, linestyle='--')
        ax.set_title(nombres[v], loc='left', fontsize=11, color=TINTA)
        ax.xaxis.set_major_formatter(lambda x, _: f'{x:g}'.replace('.', ',').replace('-', '−'))
        ax.grid(axis='y', visible=False)
    ejes[0].set_yticks(range(len(lista)), lista)
    ejes[0].invert_yaxis()
    fig.suptitle('Coeficientes estimados e intervalos de confianza al 95 % (en naranja, el modelo principal)',
                 x=0.01, ha='left', fontsize=12, color=TINTA)
    fig.text(0.01, 0.01, 'Variable dependiente: rendimiento del bono a 10 años (%). Fuente: tabla5_modelos.csv. '
             'Elaboración propia.', fontsize=8, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(SALIDAS / 'figura7_coeficientes.png', dpi=200)
    plt.close(fig)


def figura_cajas(df):
    # Figura 8: distribución del rendimiento a 10 años por país (diagrama de cajas)
    paises = sorted(df['pais'].unique())
    fig, ax = plt.subplots(figsize=(8, 4.8))
    cajas = ax.boxplot([df.loc[df['pais'] == p, Y] for p in paises], patch_artist=True, widths=0.55,
                       medianprops={'color': TINTA, 'linewidth': 1.5},
                       flierprops={'marker': 'o', 'markersize': 3, 'markerfacecolor': TINTA_2,
                                   'markeredgecolor': 'none'})
    for caja, p in zip(cajas['boxes'], paises):
        caja.set_facecolor(COLORES[p])
        caja.set_alpha(0.75)
        caja.set_edgecolor(TINTA_2)
    ax.set_xticks(range(1, len(paises) + 1), paises)
    ax.set_ylabel('%')
    ax.grid(axis='x', visible=False)
    ax.set_title('Rendimiento del bono soberano a 10 años por país, 2005-2025', loc='left',
                 fontsize=12, color=TINTA)
    fig.text(0.01, 0.01, 'Fuente: FRED (OCDE), Banxico y BCRP. Elaboración propia.', fontsize=8, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(SALIDAS / 'figura8_cajas_rend10a.png', dpi=200)
    plt.close(fig)

def newey_west(y, Xc, rezagos=4):
    # MCO con errores estándar de Newey-West (núcleo de Bartlett, corrección n/(n-k))
    n, k = Xc.shape
    XtX_inv = np.linalg.inv(Xc.T @ Xc)
    b = XtX_inv @ Xc.T @ y
    u = y - Xc @ b
    Xu = Xc * u[:, None]
    S = Xu.T @ Xu
    for l in range(1, rezagos + 1):
        peso = 1 - l / (rezagos + 1)
        G = Xu[l:].T @ Xu[:-l]
        S += peso * (G + G.T)
    V = XtX_inv @ S @ XtX_inv * n / (n - k)
    ee = np.sqrt(np.diag(V))
    t = b / ee
    p = 2 * stats.norm.sf(np.abs(t))
    r2 = 1 - (u @ u) / ((y - y.mean()) @ (y - y.mean()))
    return b, ee, t, p, r2, n


def modelos_por_pais(df):
    # Regresión por país con errores de Newey-West (4 rezagos) y prueba F de homogeneidad de pendientes
    filas = []
    for pais, d in df.groupby('pais'):
        d = d.sort_values('fecha')
        Xc = np.column_stack([np.ones(len(d)), d[X].to_numpy()])
        b, ee, t, p, r2, n = newey_west(d[Y].to_numpy(), Xc)
        for j, v in enumerate(['const'] + X):
            filas.append({'pais': pais, 'variable': v, 'coef': b[j], 'error_est': ee[j], 't': t[j],
                          'p_valor': p[j], 'ic_inf': b[j] - 1.96 * ee[j], 'ic_sup': b[j] + 1.96 * ee[j],
                          'r2': r2, 'n': n})
    tabla = pd.DataFrame(filas).round(6)
    tabla.to_csv(SALIDAS / 'tabla7_modelos_por_pais.csv', index=False)

    # Prueba F: pendientes comunes (restringido) frente a pendientes propias de cada país
    dummies = pd.get_dummies(df['pais'], dtype=float)
    Xr = np.column_stack([dummies.to_numpy(), df[X].to_numpy()])
    Xu = np.column_stack([dummies.to_numpy()] + [dummies.to_numpy() * df[[v]].to_numpy() for v in X])
    y = df[Y].to_numpy()
    rss = lambda M: np.sum((y - M @ np.linalg.lstsq(M, y, rcond=None)[0]) ** 2)
    q = Xu.shape[1] - Xr.shape[1]
    gl = len(y) - Xu.shape[1]
    f = ((rss(Xr) - rss(Xu)) / q) / (rss(Xu) / gl)
    homog = pd.DataFrame([{'prueba': 'Homogeneidad de pendientes entre países', 'estadistico_F': f,
                           'gl_numerador': q, 'gl_denominador': gl, 'p_valor': stats.f.sf(f, q, gl)}]).round(6)
    homog.to_csv(SALIDAS / 'tabla8_homogeneidad.csv', index=False)
    registrar(f'Modelos por país (Newey-West, 4 rezagos) guardados | Homogeneidad: F({q}, {gl}) = {f:.4f}, '
              f'p = {stats.f.sf(f, q, gl):.4f}')
    return tabla


def tabla_hipotesis(modelo):
    # Contraste de hipótesis con el modelo principal (EF con errores de Driscoll-Kraay)
    hip = {'crp': ('H1', '+'), 'inflacion': ('H2', '+'), 'depreciacion': ('H3', '+')}
    filas = []
    for v in X:
        b, p = modelo.params[v], modelo.pvalues[v]
        if p >= 0.05:
            decision = 'No significativa al 5 %'
        elif np.sign(b) > 0:
            decision = 'Se acepta'
        else:
            decision = 'Se rechaza: signo contrario'
        filas.append({'hipotesis': hip[v][0], 'variable': v, 'signo_esperado': hip[v][1],
                      'coef': b, 'error_est': modelo.std_errors[v], 'p_valor': p, 'decision': decision})
    pd.DataFrame(filas).round(6).to_csv(SALIDAS / 'tabla9_hipotesis.csv', index=False)


def figura_coef_por_pais(tabla):
    # Figura 9: coeficientes por país con intervalos de confianza al 95 %
    nombres = {'crp': 'Prima por riesgo país', 'inflacion': 'Inflación', 'depreciacion': 'Depreciación'}
    paises = sorted(tabla['pais'].unique())
    fig, ejes = plt.subplots(1, 3, figsize=(10, 3.8), sharey=True)
    for ax, v in zip(ejes, X):
        for k, pais in enumerate(paises):
            fila = tabla[(tabla['pais'] == pais) & (tabla['variable'] == v)].iloc[0]
            ax.errorbar(fila['coef'], k, xerr=fila['coef'] - fila['ic_inf'], fmt='o', color=COLORES[pais],
                        ecolor=COLORES[pais], elinewidth=2, capsize=4, markersize=6)
        ax.axvline(0, color='#8a8984', linewidth=1, linestyle='--')
        ax.set_title(nombres[v], loc='left', fontsize=11, color=TINTA)
        ax.xaxis.set_major_formatter(lambda x, _: f'{x:g}'.replace('.', ',').replace('-', '−'))
        ax.grid(axis='y', visible=False)
    ejes[0].set_yticks(range(len(paises)), paises)
    ejes[0].invert_yaxis()
    fig.suptitle('Coeficientes por país e intervalos de confianza al 95 % (MCO con errores de Newey-West)',
                 x=0.01, ha='left', fontsize=12, color=TINTA)
    fig.text(0.01, 0.01, 'Variable dependiente: rendimiento del bono a 10 años (%). Fuente: tabla7_modelos_por_pais.csv. '
             'Elaboración propia.', fontsize=8, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(SALIDAS / 'figura9_coef_por_pais.png', dpi=200)
    plt.close(fig)

# ------------------------------------------------------------------
# 6. EJECUCIÓN
# ------------------------------------------------------------------
if __name__ == '__main__':
    registrar('=== Inicio del análisis ===')
    registrar(f'Python {sys.version.split()[0]} | pandas {pd.__version__} | numpy {np.__version__} | '
              f'statsmodels {statsmodels.__version__} | linearmodels {linearmodels.__version__} | '
              f'matplotlib {matplotlib.__version__}')

    ruta = PROCESADOS / f'datos_procesados_{CODIGO}.csv'
    df = pd.read_csv(ruta)
    df['fecha'] = pd.to_datetime(df['fecha'] + '-01')
    registrar(f'Lectura {ruta.name} | {len(df)} filas')

    descriptivos(df)
    raiz_unitaria(df)

    panel = df.set_index(['pais', 'fecha'])
    modelos = estimar(panel)
    tablas_modelos(modelos)

    principal = modelos['EF Driscoll-Kraay']
    for v in X:
        signo = 'positivo (esperado)' if principal.params[v] > 0 else 'negativo (contrario al esperado)'
        registrar(f'EF D-K | {v}: coef = {principal.params[v]:.4f}, p = {principal.pvalues[v]:.4f} -> {signo}')

    pruebas(panel, df, modelos)
    tabla_hipotesis(principal)
    por_pais = modelos_por_pais(df)

    estilo()
    for numero, v in enumerate(VARIABLES, start=1):
        figura_series(df, v, numero)
    figura_dispersion(df)
    figura_correlaciones(df)
    figura_coeficientes(modelos)
    figura_cajas(df)
    figura_coef_por_pais(por_pais)
    registrar('Figuras guardadas en /salidas (figura1 a figura9)')
    registrar('=== Fin del análisis ===')
