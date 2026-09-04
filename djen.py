#!/usr/bin/env python3
"""O cliente do DJEN — o Diário de Justiça Eletrônico Nacional, pela API
pública de comunicações processuais do CNJ.

Escolha do Lucas em 04/09/2026, entre DJEN, AASP e PJe. É a mais limpa das
três: **não pede credencial** (é diário oficial), é nacional (não depende de a
assinatura da AASP cobrir o trabalhista) e devolve JSON estruturado, com o
número do processo em campo próprio — não preso no meio do texto, como no
e-mail da AASP, onde o Prev precisa caçá-lo por expressão regular.

O recorte é a **OAB do escritório**: o DJEN publica o diário inteiro do país, e
o que é nosso é o que sai no nome dos nossos advogados.

    ./.venv/bin/python djen.py --oab 123456 --uf SP --dias 3 --cru lote.json
    ./.venv/bin/python dejt.py --arquivo lote.json      # e daí o de sempre

## A trava: forma desconhecida é RECUSA, não palpite

Este arquivo segue a mesma regra do `do_conector.py`: **o que não se reconhece
não vira palpite, vira erro**. Cada campo tem uma lista de nomes candidatos, e
se nenhum casar num campo obrigatório o lote inteiro é recusado, com as chaves
que de fato vieram impressas na tela.

Isso não é excesso de zelo. A API pode mudar nome de campo entre versões, e o
modo de falha silencioso seria gravar publicação sem data ou sem texto — que na
prática é prazo que não nasce e ninguém percebe. Melhor parar e me mostrar o
que veio.

Por isso, na PRIMEIRA vez, rode com `--cru`: ele baixa e salva sem gravar nada
no banco. Aí se confere a forma antes de deixar entrar.
"""
import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

API = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

# Os nomes que cada campo pode ter, do mais provável para o menos. A API do CNJ
# mistura camelCase e snake_case entre recursos, e já mudou de um para o outro.
CANDIDATOS = {
    "id":        ("id", "idComunicacao", "id_comunicacao", "hash"),
    "cnj":       ("numeroprocessocommascara", "numeroProcessoComMascara",
                  "numero_processo_mascara", "numero_processo", "numeroProcesso"),
    "tribunal":  ("siglaTribunal", "sigla_tribunal", "tribunal"),
    "orgao":     ("nomeOrgao", "nome_orgao", "orgao", "nomeorgao"),
    "tipo_ato":  ("tipoComunicacao", "tipo_comunicacao", "tipoDocumento",
                  "tipodocumento", "nomeClasse"),
    "data":      ("data_disponibilizacao", "dataDisponibilizacao",
                  "datadisponibilizacao", "dataDisponibilizacaoDiario"),
    "texto":     ("texto", "conteudo", "textoComunicacao", "teor"),
}

# Sem estes dois não há publicação: a data é de onde o prazo conta, e o texto é
# o que diz qual prazo é. Faltando um, o lote é recusado.
OBRIGATORIOS = ("data", "texto")


class FormaDesconhecida(Exception):
    """A resposta veio com uma forma que este arquivo não sabe ler."""


def _pega(item, campo):
    for nome in CANDIDATOS[campo]:
        if nome in item and item[nome] not in (None, ""):
            return item[nome]
    return None


def _lista(payload):
    """Onde estão os itens. A API já devolveu em `items` e em `content`."""
    if isinstance(payload, list):
        return payload
    for chave in ("items", "content", "registros", "data", "comunicacoes"):
        v = payload.get(chave)
        if isinstance(v, list):
            return v
    raise FormaDesconhecida(
        "não achei a lista de comunicações na resposta. Chaves do topo: %s"
        % ", ".join(sorted(payload.keys())[:20]))


def converter(payload):
    """Do JSON do DJEN para a forma que `dejt.ingerir` já lê.

    Recusa o lote inteiro se um campo obrigatório não aparecer em NENHUM item —
    porque isso é mudança de contrato da API, não item estranho.
    """
    itens = _lista(payload)
    if not itens:
        return []

    faltando = [c for c in OBRIGATORIOS
                if not any(_pega(i, c) for i in itens if isinstance(i, dict))]
    if faltando:
        exemplo = next((i for i in itens if isinstance(i, dict)), {})
        raise FormaDesconhecida(
            "campo obrigatório sem nome conhecido: %s.\n"
            "  As chaves que vieram: %s\n"
            "  Acrescente o nome certo em CANDIDATOS, em djen.py."
            % (", ".join(faltando), ", ".join(sorted(exemplo.keys())[:30])))

    saida = []
    for i in itens:
        if not isinstance(i, dict):
            continue
        data = str(_pega(i, "data") or "")[:10]      # 'YYYY-MM-DD', com ou sem hora
        texto = _pega(i, "texto")
        if not data or not texto:
            continue                                  # item incompleto: pula, não inventa
        saida.append({
            "id": _pega(i, "id"),
            "numero_cnj": _pega(i, "cnj"),
            "tribunal": _pega(i, "tribunal"),
            "orgao": _pega(i, "orgao"),
            "tipo_ato": _pega(i, "tipo_ato"),
            "disponibilizado_em": data,
            "texto": texto,
            "bruto": i,
        })
    return saida


def buscar(oab=None, uf=None, tribunal=None, dias=3, ate=None, por_pagina=100,
           paginas_max=50):
    """As comunicações da janela. Devolve a lista JÁ CONVERTIDA.

    A janela é por data de DISPONIBILIZAÇÃO, que é a data que a lei manda
    contar — não a de publicação, que é derivada dela.
    """
    fim = ate or date.today()
    inicio = fim - timedelta(days=dias)
    if not (oab or tribunal):
        sys.exit("✗ diga o recorte: --oab/--uf (o que é nosso) ou --tribunal.\n"
                 "  Sem recorte o DJEN devolve o diário do país inteiro.")

    tudo, pagina = [], 1
    while pagina <= paginas_max:
        p = {"dataDisponibilizacaoInicio": inicio.isoformat(),
             "dataDisponibilizacaoFim": fim.isoformat(),
             "itensPorPagina": por_pagina, "pagina": pagina}
        if oab:
            p["numeroOab"] = oab
            p["ufOab"] = (uf or "SP").upper()
        if tribunal:
            p["siglaTribunal"] = tribunal

        url = API + "?" + urllib.parse.urlencode(p)
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            # Identificar-se é educação com serviço público, e ajuda o CNJ a
            # separar robô de gente quando alguma coisa vai mal.
            "User-Agent": "GGV-Trabalhista/1.0 (sistema do escritorio)"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            sys.exit(f"✗ o DJEN respondeu {e.code} na página {pagina}: {e.reason}")
        except urllib.error.URLError as e:
            sys.exit(f"✗ não cheguei ao DJEN: {e.reason}\n"
                     "  De dentro do Claude Code na web este host é bloqueado pela\n"
                     "  política de rede da sessão. Rode de uma máquina comum.")

        lote = converter(payload)
        tudo.extend(lote)
        if len(lote) < por_pagina:
            break
        pagina += 1
    return tudo


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--oab", help="número da OAB do escritório (o recorte do que é nosso)")
    p.add_argument("--uf", default="SP", help="UF da OAB (padrão SP)")
    p.add_argument("--tribunal", help="sigla, ex.: TRT2. Use junto ou no lugar da OAB")
    p.add_argument("--dias", type=int, default=3, help="janela de disponibilização")
    p.add_argument("--cru", help="salva o lote convertido neste arquivo e NÃO grava no banco")
    a = p.parse_args()

    lote = buscar(oab=a.oab, uf=a.uf, tribunal=a.tribunal, dias=a.dias)
    print(f"{len(lote)} comunicação(ões) na janela de {a.dias} dia(s).")
    if a.cru:
        with open(a.cru, "w") as f:
            json.dump({"fonte": "DJEN", "registros": lote}, f, ensure_ascii=False, indent=1)
        print(f"salvo em {a.cru}. Confira a forma e depois:\n"
              f"  ./.venv/bin/python dejt.py --arquivo {a.cru}")
    else:
        print("nada gravado. Use --cru ARQUIVO, ou chame por dejt.py --djen.")


if __name__ == "__main__":
    main()
