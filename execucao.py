#!/usr/bin/env python3
"""Registro de execução, retry e vigia do silêncio.

O risco do diário não é a automação errar — é ela **calar**. Hoje uma rodada
que leu zero publicações porque o site da AASP caiu produz exatamente o mesmo
resultado visível de uma sexta-feira sem publicação nova: nada na tela, nada no
log, ninguém avisado. Na segunda o prazo já correu dois dias.

`automacao_log` guardava só a AÇÃO tomada. Aqui ela passa a guardar também a
TENTATIVA feita — com resultado, quantidade, erro e número da tentativa. A
diferença entre as duas é o que permite responder "rodou e não achou nada" ou
"não rodou".

    ./.venv/bin/python execucao.py            # o que o vigia está vendo agora
    ./.venv/bin/python execucao.py --vigiar   # e alerta se alguém estiver mudo

Uso no código:

    with execucao.registrar("AASP_LEITURA") as e:
        n = ler_o_diario()
        e.itens = n

Sai OK com o número de itens; se estourar exceção, grava ERRO com a mensagem e
deixa a exceção subir. Quem chama decide se tenta de novo — `com_retry` faz isso.
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta

import banco

FUSO_FMT = "%Y-%m-%d %H:%M:%S"
# fora deste intervalo não se cobra execução: o launchd não roda de madrugada
# e o diário não circula no fim de semana.
DIAS_UTEIS = (0, 1, 2, 3, 4)          # segunda a sexta, como datetime.weekday()


def agora():
    return datetime.now()


def config(db, codigo):
    r = db.execute("SELECT config FROM automacoes WHERE codigo=?", (codigo,)).fetchone()
    if not r or not r[0]:
        return {}
    try:
        return json.loads(r[0])
    except ValueError:
        return {}


class _Execucao:
    def __init__(self, db, codigo, tentativa, chave):
        self.db, self.codigo, self.tentativa = db, codigo, tentativa
        self.chave = chave
        self.itens = None
        self.detalhe = None

    def gravar(self, resultado, erro=None):
        # No Postgres, a instrução que falhou deixa a transação abortada: tudo
        # depois dela erra até alguém dar rollback. Sem este rollback, gravar a
        # FALHA também falhava — ou seja, o registro de execução quebrava
        # exatamente no caso em que ele existe para servir.
        if resultado == "ERRO":
            try:
                self.db.rollback()
            except Exception:
                pass
        # ADAPTAÇÃO (docs/portal-adaptacoes.md): o `automacao_log` daqui não tem
        # as colunas `itens`, `erro` e `tentativa` que o do Prev tem — tem
        # (automacao, chave, resultado, detalhe, origem). Nada se perde: o que
        # ia em três colunas vai no `detalhe`, e `resultado` continua sendo o
        # que distingue rodada que falhou de dia sem nada a fazer, que é o
        # ponto inteiro deste arquivo.
        partes = [p for p in (self.detalhe,
                              None if self.itens is None else f"itens={self.itens}",
                              f"tentativa={self.tentativa}",
                              f"erro: {(erro or '')[:400]}" if erro else None) if p]
        self.db.execute(
            """INSERT INTO automacao_log (automacao, chave, detalhe, resultado)
               VALUES (?,?,?,?)""",
            (self.codigo, self.chave, " · ".join(partes) or None, resultado))
        self.db.commit()


class registrar:
    """Contexto que grava uma linha de execução, dê certo ou dê errado."""

    def __init__(self, codigo, tentativa=1, db=None):
        self.codigo, self.tentativa = codigo, tentativa
        self.db = db
        self._meu_db = db is None

    def __enter__(self):
        if self._meu_db:
            self.db = banco.conectar()
        # a chave precisa ser única por execução: a regra de idempotência do
        # motor usa (automacao, chave), e execução não é idempotente — cada
        # rodada é um fato novo.
        chave = f"exec:{agora().strftime('%Y-%m-%dT%H:%M:%S')}:{self.tentativa}"
        self.e = _Execucao(self.db, self.codigo, self.tentativa, chave)
        return self.e

    def __exit__(self, tipo, valor, tb):
        if tipo is None:
            self.e.gravar("OK" if (self.e.itens or 0) else "SEM_ACAO")
        else:
            self.e.gravar("ERRO", f"{tipo.__name__}: {valor}")
        if self._meu_db:
            self.db.close()
        return False                 # a exceção continua subindo


def com_retry(codigo, funcao, db=None):
    """Roda `funcao()`, e em falha tenta de novo nos minutos que a config manda.

    O launchd já roda de novo em algumas horas; o retry serve para o caso comum,
    que é instabilidade de minutos. O valor maior, porém, não é a nova tentativa
    — é a FALHA FICAR REGISTRADA quando as tentativas acabam.
    """
    proprio = db is None
    db = db or banco.conectar()
    esperas = config(db, codigo).get("retries_min", [20, 30])
    erro_final = None
    for i in range(len(esperas) + 1):
        try:
            with registrar(codigo, tentativa=i + 1, db=db) as e:
                r = funcao()
                e.itens = r if isinstance(r, int) else None
            if proprio:
                db.close()
            return r
        except Exception as ex:
            erro_final = ex
            # a conexão vem suja da tentativa que falhou; sem limpar, toda
            # tentativa seguinte morre em InFailedSqlTransaction e o retry vira
            # teatro — três tentativas que falham pelo motivo errado.
            try:
                db.rollback()
            except Exception:
                pass
            if i < len(esperas):
                espera = esperas[i] * 60
                print(f"   tentativa {i+1} falhou ({ex}). Nova em {esperas[i]} min.", flush=True)
                time.sleep(espera)
    if proprio:
        db.close()
    raise erro_final


# ------------------------------------------------------------------ o vigia
def _esperadas_ate(horarios, quando, tolerancia_min):
    """Quantas execuções já deveriam ter acontecido hoje, com folga."""
    n = 0
    for h in horarios:
        try:
            hh, mm = (int(x) for x in h.split(":"))
        except ValueError:
            continue
        alvo = quando.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if quando >= alvo + timedelta(minutes=tolerancia_min):
            n += 1
    return n


def vigiar(db=None, codigo="DEJT_LEITURA", quando=None):
    """Compara o horário esperado com a última execução. Devolve o veredito.

    Silêncio é erro. A ausência de notícia não é notícia boa: é o modo de falha
    mais provável e o único que ninguém percebe.
    """
    proprio = db is None
    db = db or banco.conectar()
    # o vigia é chamado LOGO DEPOIS de um erro, para contar o que houve. Se a
    # conexão vier abortada, ele não consegue nem ler a config.
    try:
        db.rollback()
    except Exception:
        pass
    quando = quando or agora()
    cfg = config(db, codigo)
    horarios = cfg.get("horarios", ["09:30", "14:00", "18:30"])
    tol = int(cfg.get("tolerancia_min", 90))

    ult = db.execute("""SELECT em, resultado, detalhe FROM automacao_log
                        WHERE automacao=? AND resultado IS NOT NULL
                        ORDER BY em DESC LIMIT 1""", (codigo,)).fetchone()
    hoje = quando.strftime("%Y-%m-%d")
    rodou_hoje = db.execute("""SELECT count(*) FROM automacao_log
                               WHERE automacao=? AND resultado IS NOT NULL
                                 AND substr(em,1,10)=?""", (codigo, hoje)).fetchone()[0]
    falhas_hoje = db.execute("""SELECT count(*) FROM automacao_log
                                WHERE automacao=? AND resultado='ERRO'
                                  AND substr(em,1,10)=?""", (codigo, hoje)).fetchone()[0]
    if proprio:
        db.close()

    esperadas = _esperadas_ate(horarios, quando, tol) if quando.weekday() in DIAS_UTEIS else 0
    v = dict(codigo=codigo, esperadas=esperadas, rodou_hoje=rodou_hoje,
             falhas_hoje=falhas_hoje, ultima=ult[0] if ult else None,
             ultimo_resultado=ult[1] if ult else None,
             ultimo_erro=ult[2] if ult else None, horarios=horarios)

    if ult and ult[0]:
        try:
            v["horas_desde"] = round(
                (quando - datetime.strptime(ult[0][:19], FUSO_FMT)).total_seconds() / 3600, 1)
        except ValueError:
            v["horas_desde"] = None
    else:
        v["horas_desde"] = None

    if esperadas == 0:
        v["nivel"], v["recado"] = "ok", "fora de horário de cobrança"
    elif rodou_hoje == 0:
        v["nivel"] = "vermelho"
        v["recado"] = (f"o DEJT não foi lido hoje — {esperadas} leitura(s) já deveriam ter "
                       f"acontecido. Publicação não lida é prazo correndo sem ninguém saber.")
    elif rodou_hoje < esperadas:
        v["nivel"] = "amarelo"
        v["recado"] = f"{rodou_hoje} de {esperadas} leituras esperadas até agora"
    elif falhas_hoje:
        v["nivel"] = "amarelo"
        v["recado"] = f"rodou, mas {falhas_hoje} tentativa(s) falharam hoje"
    else:
        v["nivel"], v["recado"] = "ok", f"{rodou_hoje} leitura(s) hoje, sem falha"
    return v


def avisar(v):
    """Alerta na tela do terminal e no Centro de Notificações do Mac.

    Notificação para celular ainda não existe: exige serviço externo, e mandar
    dado de processo para fora do escritório é decisão do Lucas, não minha.
    Isto aqui alcança quem está na máquina do escritório, que é o servidor.
    """
    if v["nivel"] == "ok":
        return False
    titulo = "GGV — o diário não foi lido" if v["nivel"] == "vermelho" else "GGV — leitura do diário"
    corpo = v["recado"].replace('"', "'")
    try:
        import subprocess
        subprocess.run(["osascript", "-e",
                        f'display notification "{corpo}" with title "{titulo}" sound name "Basso"'],
                       capture_output=True, timeout=10)
    except Exception:
        pass
    print(f"⚠ {titulo}: {v['recado']}", file=sys.stderr)
    return True


if __name__ == "__main__":
    v = vigiar()
    marca = {"ok": "✓", "amarelo": "⚠", "vermelho": "✗"}[v["nivel"]]
    print(f"{marca} {v['codigo']}: {v['recado']}")
    print(f"   esperadas hoje até agora: {v['esperadas']} · executadas: {v['rodou_hoje']}"
          f" · falhas: {v['falhas_hoje']}")
    print(f"   última execução: {v['ultima'] or '(nenhuma registrada)'}"
          + (f" · há {v['horas_desde']}h" if v["horas_desde"] is not None else ""))
    if v["ultimo_erro"]:
        print(f"   último erro: {v['ultimo_erro'][:120]}")
    if "--vigiar" in sys.argv:
        avisar(v)
    sys.exit(2 if v["nivel"] == "vermelho" else 0)
