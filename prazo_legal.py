#!/usr/bin/env python3
"""Quando o prazo trabalhista começa e quando vence.

Não é a regra do Prev. Lá o prazo é do JEF e sai em dias corridos; aqui vale
a CLT:

  · **contagem em DIAS ÚTEIS** — art. 775 da CLT (redação da Lei 13.467/2017).
    Dias corridos só com justificativa escrita, e o gatilho `gov_prazo_regras`
    recusa sem ela.
  · **publicação** = primeiro dia útil seguinte à disponibilização no DEJT
    (Lei 11.419/2006, art. 4º, §§ 3º e 4º);
  · **início** = primeiro dia útil depois da publicação;
  · **recesso de 20/12 a 20/01 suspende** o prazo (art. 775-A da CLT);
  · intimação feita em audiência conta da audiência (Súmula 197 do TST) — aí
    a publicação não entra na conta, e quem chama passa `da_audiencia=True`.

[CONFIRMAR] Os feriados aqui são os NACIONAIS. Faltam os do TRT (portarias
anuais, que variam por região e por ano) e os municipais da sede da vara.
Enquanto não vierem, a conta ERRA PARA O LADO CURTO em quem tem feriado local
— e errar para o lado curto é o lado seguro: o prazo aparece vencendo antes,
não depois. O lado errado deste erro é o que faz perder prazo.
"""
from datetime import date, timedelta

# ------------------------------------------------------------ feriados
FIXOS = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15),
         (11, 20), (12, 25)]     # 20/11 é nacional desde a Lei 14.759/2023


def _pascoa(ano):
    """Algoritmo de Meeus/Jones/Butcher."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(ano, mes, dia + 1)


def feriados(ano):
    """Os feriados nacionais do ano, incluindo os móveis. Conjunto de `date`."""
    p = _pascoa(ano)
    fora = {date(ano, m, d) for m, d in FIXOS}
    fora |= {p - timedelta(days=48),        # carnaval (segunda)
             p - timedelta(days=47),        # carnaval (terça)
             p - timedelta(days=2),         # sexta-feira santa
             p + timedelta(days=60)}        # corpus christi
    return fora


_CACHE = {}


def _do_ano(ano):
    if ano not in _CACHE:
        _CACHE[ano] = feriados(ano)
    return _CACHE[ano]


def no_recesso(d):
    """20/12 a 20/01: prazo suspenso (CLT art. 775-A)."""
    return (d.month == 12 and d.day >= 20) or (d.month == 1 and d.day <= 20)


def dia_util(d):
    return d.weekday() < 5 and d not in _do_ano(d.year) and not no_recesso(d)


def proximo_util(d):
    while not dia_util(d):
        d += timedelta(days=1)
    return d


def somar_uteis(inicio, dias):
    """`dias` dias úteis a partir de `inicio` (que não é contado)."""
    d, faltam = inicio, int(dias)
    while faltam > 0:
        d += timedelta(days=1)
        if dia_util(d):
            faltam -= 1
    return d


def entre_uteis(de, ate):
    """Quantos dias úteis faltam de `de` até `ate`. Negativo se já passou."""
    if ate < de:
        return -entre_uteis(ate, de)
    n, d = 0, de
    while d < ate:
        d += timedelta(days=1)
        if dia_util(d):
            n += 1
    return n


# ------------------------------------------------------------ a conta
def _iso(v):
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def calcular(disponibilizado_em=None, publicado_em=None, dias=None,
             da_audiencia=None):
    """Devolve (publicado_em, inicio, vencimento) em ISO, ou None onde faltar.

    Nada é chutado: sem a origem da contagem, devolve None e a tela pede.
    """
    if da_audiencia:
        base = _iso(da_audiencia)
        pub = None
    elif publicado_em:
        pub = _iso(publicado_em)
        base = pub
    elif disponibilizado_em:
        pub = proximo_util(_iso(disponibilizado_em) + timedelta(days=1))
        base = pub
    else:
        return None, None, None
    inicio = proximo_util(base + timedelta(days=1))
    venc = somar_uteis(inicio - timedelta(days=1), dias) if dias else None
    return (pub.isoformat() if pub else None,
            inicio.isoformat(),
            venc.isoformat() if venc else None)


def faltam(vencimento, hoje=None):
    """Dias ÚTEIS até o vencimento. É a conta que a fila de prazos ordena."""
    if not vencimento:
        return None
    return entre_uteis(hoje or date.today(), _iso(vencimento))


if __name__ == "__main__":
    hoje = date.today()
    print(f"hoje: {hoje} · dia útil: {dia_util(hoje)}")
    pub, ini, venc = calcular(disponibilizado_em=hoje.isoformat(), dias=8)
    print("disponibilizado hoje, prazo de 8 dias úteis (RO, CLT art. 895 I):")
    print(f"  publicação {pub} · começa {ini} · vence {venc}")
