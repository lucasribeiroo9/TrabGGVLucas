#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Converte o que o conector MCP do Airtable devolve para o formato que `migrar.py` lê.

    ./.venv/bin/python do_conector.py --origem /caminho/dos/jsons/do/conector
    ./.venv/bin/python migrar.py --do-conector --origem /caminho   # o mesmo, por dentro

Por que este arquivo existe: `migrar.py --baixar` fala com a API REST e precisa
de um token que esta máquina não tem. O agente Leitor baixou as dez tabelas pelo
conector MCP, que é SOMENTE LEITURA, mas devolve os registros numa forma
diferente da REST. Em vez de ensinar `migrar.py` a ler duas formas (e ter duas
leituras para manter), converte-se aqui para a forma que ele já conhece.

## As diferenças de forma que este arquivo trata

| o que | conector MCP | API REST (o que `migrar.py` lê) |
|---|---|---|
| registros | `records[].cellValuesByFieldId` | `records[].fields` |
| chave do campo | id (`fld…`) | NOME do campo |
| select único | `{"id","name","color"}` | `"name"` |
| select múltiplo | `[{"id","name","color"}, …]` | `["name", …]` |
| link | `[{"id": "rec…", "name"}, …]` | `["rec…", …]` |
| lookup | `{"linkedRecordIds": [...], "valuesByLinkedRecordId": {rec: [v…]}}` | `[v…]` na ordem dos links |
| colaborador (Created By) | `{"id","email","name","permissionLevel","profilePicUrl"}` | `{"id","email","name"}` |
| botão | `{"label","url"}` | igual |
| anexo | `[{"id","filename","size","type","url","thumbnails"…}]` | igual |
| texto, número, moeda, data, data-hora, checkbox, fórmula, createdTime | igual | igual |
| célula vazia | ausente | ausente |

Um lookup pode devolver select por dentro (SITU. EMPRESA olha o STATUS EMPRESA
da reclamada): a regra se aplica de novo ao valor de dentro.

## O que se recusa a fazer

- **Campo sem nome é perda, e perda é falha.** Todo id de campo presente em
  qualquer registro tem de estar no mapa id → nome (`nomes.tsv`, que o Leitor
  gerou de `list_tables_for_base`). Um id fora do mapa derruba a conversão com a
  lista do que faltou, em vez de gravar `fldXXXX` como nome e seguir.
- **Forma desconhecida é falha.** Um valor cuja forma não está na tabela acima
  não é "convertido do jeito que der": a conversão para e diz qual campo, qual
  tabela e qual forma. Adivinhar aqui é gravar no banco uma coisa que a origem
  não disse.
- **Nome repetido não engole campo.** Se dois campos da mesma tabela têm o
  mesmo nome (FUNCIONARIOS tem dois "PROCESSUAL copy"), o segundo recebe o
  sufixo ` [fld…]` e o fato é anunciado. A REST também não saberia distinguir
  os dois — mas aqui nenhum dos dois some.

O tipo do campo é deduzido pela FORMA do valor, não pelo schema: o schema bruto
guardado em `docs/` cobre 8 das 10 tabelas, e a forma é inequívoca por tipo
(`sel…` é opção, `rec…` é link, `linkedRecordIds` é lookup). Onde o schema
existe, ele é usado só como conferência, e a discordância é anunciada.

Saída: `dados/<nome>.json` para cada entrada de `migrar.TABELAS`, no formato
`{"tabela", "baixado_em", "origem": "conector MCP", "registros": [{"id",
"createdTime", "fields"}]}` — SEM a marca `amostra_sintetica`, que é o que
`migrar.ler()` usa para avisar que o dump é inventado.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from migrar import DADOS, TABELAS                                # noqa: E402

# nome do arquivo do conector → nome do arquivo que `migrar.py` lê
ARQUIVOS = {
    "pre": "pre_processual", "proc": "processual", "copia": "copia",
    "pos": "pos_processual", "func": "funcionarios", "test": "testemunhas",
    "emp": "empresas", "falt": "faltantes", "frag": "fragilidades",
    "audit": "auditoria_testemunhas",
}
SCHEMA_BRUTO = os.path.join(AQUI, "docs", ".airtable_schema_raw.json")


class FormaDesconhecida(Exception):
    pass


def ler_nomes(origem):
    """`nomes.tsv`: tabela \\t id do campo \\t nome. Um mapa por tabela."""
    caminho = os.path.join(origem, "nomes.tsv")
    if not os.path.exists(caminho):
        sys.exit("falta %s (tabela, id do campo, nome — sai de list_tables_for_base)" % caminho)
    nomes = defaultdict(dict)
    for linha in open(caminho, encoding="utf-8"):
        linha = linha.rstrip("\n")
        if not linha:
            continue
        tabela, fid, nome = linha.split("\t", 2)
        nomes[tabela][fid] = nome
    return nomes


def ler_tipos():
    """Os tipos do schema bruto, onde ele existe. Só para conferir."""
    if not os.path.exists(SCHEMA_BRUTO):
        return {}
    tipos = defaultdict(dict)
    for t in json.load(open(SCHEMA_BRUTO))["tables"]:
        tid = t.get("tableId") or t.get("id")
        for f in t["fields"]:
            tipos[tid][f["id"]] = f["type"]
    return tipos


def e_select(v):
    return isinstance(v, dict) and set(v) <= {"id", "name", "color"} and \
        str(v.get("id", "")).startswith("sel")


def e_link(v):
    return isinstance(v, dict) and set(v) <= {"id", "name"} and str(v.get("id", "")).startswith("rec")


def e_anexo(v):
    return isinstance(v, dict) and "filename" in v and "url" in v and str(v.get("id", "")).startswith("att")


def converter_valor(v, contexto, contagem):
    """Devolve (valor na forma REST, rótulo da forma). Forma que não conhece → erro."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        contagem["escalar"] += 1
        return v, "escalar"
    if e_select(v):
        contagem["select"] += 1
        return v["name"], "select"
    if isinstance(v, dict) and "linkedRecordIds" in v:
        # lookup: os valores na ordem dos links; o valor de dentro pode ser select
        valores = []
        for rec in v.get("linkedRecordIds") or []:
            for x in (v.get("valuesByLinkedRecordId") or {}).get(rec, []) or []:
                valores.append(converter_valor(x, contexto, Counter())[0])
        contagem["lookup"] += 1
        return valores, "lookup"
    if isinstance(v, dict) and "email" in v and "permissionLevel" in v:
        contagem["colaborador"] += 1
        return {k: v[k] for k in ("id", "email", "name") if k in v}, "colaborador"
    if isinstance(v, dict) and set(v) == {"label", "url"}:
        contagem["botão"] += 1
        return v, "botão"
    if isinstance(v, list):
        if not v:
            contagem["lista vazia"] += 1
            return v, "lista vazia"
        if all(e_select(x) for x in v):
            contagem["multi-select"] += 1
            return [x["name"] for x in v], "multi-select"
        if all(e_link(x) for x in v):
            contagem["link"] += 1
            return [x["id"] for x in v], "link"
        if all(e_anexo(x) for x in v):
            contagem["anexo"] += 1
            return v, "anexo"
        if all(isinstance(x, (str, int, float, bool)) for x in v):
            contagem["lista de escalares"] += 1
            return v, "lista de escalares"
    raise FormaDesconhecida("%s: forma não prevista: %s" % (contexto, json.dumps(v, ensure_ascii=False)[:200]))


# a forma esperada para cada tipo do schema — só para a conferência cruzada
FORMA_POR_TIPO = {
    "singleSelect": {"select"}, "multipleSelects": {"multi-select", "lista vazia"},
    "multipleRecordLinks": {"link", "lista vazia"}, "multipleLookupValues": {"lookup"},
    "createdBy": {"colaborador"}, "button": {"botão"}, "multipleAttachments": {"anexo"},
}


def converter_tabela(chave, origem, nomes, tipos, saida):
    nome_saida = ARQUIVOS[chave]
    tid, esperado = TABELAS[nome_saida]
    caminho = os.path.join(origem, chave + ".json")
    if not os.path.exists(caminho):
        sys.exit("falta %s" % caminho)
    dump = json.load(open(caminho, encoding="utf-8"))
    registros = dump["records"]
    mapa = nomes.get(tid) or {}
    if not mapa:
        sys.exit("%s: nenhum nome de campo para a tabela %s em nomes.tsv" % (chave, tid))

    # 1. todo id presente nos registros tem nome?
    ids = {fid for r in registros for fid in r.get("cellValuesByFieldId", {})}
    sem_nome = sorted(ids - set(mapa))
    if sem_nome:
        sys.exit("%s (%s): %d campo(s) sem nome no mapa — perda, então falha: %s"
                 % (chave, tid, len(sem_nome), ", ".join(sem_nome)))

    # 2. nome repetido dentro da tabela: o segundo ganha sufixo, e se avisa
    nome_final, vistos = {}, {}
    for fid, nome in mapa.items():
        if nome in vistos:
            nome_final[fid] = "%s [%s]" % (nome, fid)
            print("  ⚠ %s: nome repetido %r — o campo %s virou %r"
                  % (chave, nome, fid, nome_final[fid]))
        else:
            vistos[nome] = fid
            nome_final[fid] = nome

    # 3. a conversão em si
    contagem, formas_por_campo, saida_regs = Counter(), defaultdict(set), []
    for r in registros:
        fields = {}
        for fid, v in r.get("cellValuesByFieldId", {}).items():
            valor, forma = converter_valor(v, "%s.%s (%s)" % (chave, nome_final[fid], fid), contagem)
            formas_por_campo[fid].add(forma)
            if valor in (None, "", []):
                continue                       # a REST também omite célula vazia
            fields[nome_final[fid]] = valor
        saida_regs.append({"id": r["id"], "createdTime": r.get("createdTime"), "fields": fields})

    # 4. conferência cruzada com o schema bruto, onde ele existe
    discordancias = []
    for fid, formas in formas_por_campo.items():
        tipo = (tipos.get(tid) or {}).get(fid)
        if tipo in FORMA_POR_TIPO and not formas <= FORMA_POR_TIPO[tipo]:
            discordancias.append("%s (%s) é %s mas veio como %s" % (nome_final[fid], fid, tipo, sorted(formas)))
    for d in discordancias:
        print("  ⚠ %s: %s" % (chave, d))

    os.makedirs(saida, exist_ok=True)
    destino = os.path.join(saida, nome_saida + ".json")
    json.dump({"tabela": tid, "baixado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
               "origem": "conector MCP (%s)" % chave, "registros": saida_regs},
              open(destino, "w", encoding="utf-8"), ensure_ascii=False)
    marca = "" if len(saida_regs) == esperado else "   ⚠ esperava %d" % esperado
    print("%-24s %6d registros  %3d campos  %s%s"
          % (nome_saida, len(saida_regs), len(ids),
             " ".join("%s=%d" % kv for kv in sorted(contagem.items())), marca))
    return len(saida_regs), contagem, discordancias


def converter(origem, saida=DADOS):
    nomes, tipos = ler_nomes(origem), ler_tipos()
    total, formas = 0, Counter()
    for chave in ARQUIVOS:
        n, c, _ = converter_tabela(chave, origem, nomes, tipos, saida)
        total += n
        formas.update(c)
    print("-" * 74)
    print("%d registros em %d tabelas → %s" % (total, len(ARQUIVOS), saida))
    print("formas convertidas: " + ", ".join("%s=%d" % kv for kv in sorted(formas.items())))
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--origem", required=True, help="pasta com pre.json, proc.json, … e nomes.tsv")
    p.add_argument("--saida", default=DADOS, help="pasta de saída (padrão: dados/)")
    a = p.parse_args()
    converter(a.origem, a.saida)


if __name__ == "__main__":
    main()
