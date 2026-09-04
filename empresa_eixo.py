#!/usr/bin/env python3
"""A reclamada como eixo: preenche o que a carga do Airtable deixa implícito.

**A base continua sendo o Airtable** — decisão do Lucas, e é o que está mais
preenchido. Este arquivo NÃO carrega nada: ele lê o que `migrar.py` já trouxe e
escreve as ligações que o modelo antigo não tinha onde guardar. Por isso é um
passo DEPOIS da carga, e não uma alteração dela: a carga está provada em 249
verificações, e mexer nela para acrescentar isto poria a prova em risco por
nada.

O que o Drive ensinou (`docs/acervo-drive.md`) e que motivou estas tabelas: o
acervo inteiro é indexado pela empresa, e a carteira dos advogados é dividida
por reclamada — não por carga de trabalho.

    ./.venv/bin/python empresa_eixo.py --sincronizar   # a reclamada de cada processo
    ./.venv/bin/python empresa_eixo.py --duplicatas    # cadastros repetidos da mesma empresa
    ./.venv/bin/python empresa_eixo.py --carteira equipe_empresas.csv --aplicar
    ./.venv/bin/python empresa_eixo.py --resumo

Tudo é IDEMPOTENTE: rodar duas vezes não duplica nada.
"""
import argparse
import csv
import os
import re
import sys
import unicodedata

import banco


def norm(s):
    """Mesma normalização de `normalizar.py`: sem acento, caixa alta, espaço só."""
    t = unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t).strip().upper()


# Palavras que não distinguem uma empresa de outra. Sem tirá-las, "TRANSPORTES
# ALFA LTDA" e "ALFA TRANSPORTES LTDA ME" parecem empresas diferentes.
RUIDO = {"LTDA", "ME", "EPP", "EIRELI", "SA", "S/A", "S.A", "CIA", "E", "DE", "DA",
         "DO", "DAS", "DOS", "EM", "RECUPERACAO", "JUDICIAL", "-", "&"}


def chave_fraca(nome):
    """As palavras que sobram, ordenadas. É pista de duplicata, NÃO prova.

    Palavra curta sai — MAS NÚMERO FICA, mesmo com um dígito. Descartar o
    número casava "Reclamada 3" com "Reclamada 5" como se fossem a mesma
    empresa, e na vida real casaria filiais numeradas e "Grupo 3" com "Grupo 5":
    justamente o dígito que as distingue.
    """
    return " ".join(sorted(p for p in norm(nome).split()
                           if p not in RUIDO and (len(p) > 2 or p.isdigit())))


def sincronizar(db):
    """`processos.empresa_id` → `processo_empresas` como RECLAMADA.

    A coluna antiga continua sendo a reclamada principal e ninguém a perde;
    esta tabela é onde as co-rés e o tomador vão poder entrar depois, com a
    responsabilidade que a inicial pede (solidária no grupo econômico, art. 2º
    §2º; subsidiária no tomador, Súmula 331 do TST).
    """
    n = db.execute("""
        INSERT INTO processo_empresas (processo_id, empresa_id, papel)
        SELECT pr.id, pr.empresa_id, 'RECLAMADA'
          FROM processos pr
         WHERE pr.empresa_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM processo_empresas pe
                            WHERE pe.processo_id = pr.id AND pe.empresa_id = pr.empresa_id)
        """).rowcount
    db.commit()
    return n


def duplicatas(db, aplicar=False):
    """Cadastros que parecem a MESMA empresa. Por CNPJ é prova; por nome é pista.

    O Drive tem a mesma reclamada em pastas separadas, com variante de grafia e
    erro de digitação — e duas empresas homônimas desambiguadas pelo CNPJ
    escrito no nome. Por isso: **não funde nada**. Marcar `MESMA_EMPRESA`
    preserva os dois cadastros e o histórico de cada um; fundir apagaria um dos
    dois lados, e deduplicar é decisão de gente.
    """
    achados = []

    # 1. mesmo CNPJ: é prova, não semelhança.
    #    Os apelidos são obrigatórios: sem eles as colunas se chamariam `id`,
    #    `nome`, `id`, `nome`, e como a linha volta como dicionário as duas
    #    últimas apagariam as duas primeiras. É a mesma armadilha da ponte
    #    sqlite→psycopg que o `dejt.py` já documenta.
    for linha in db.execute("""
            SELECT a.id AS a_id, a.nome AS a_nome, b.id AS b_id, b.nome AS b_nome,
                   a.cnpj AS o_cnpj
              FROM empresas a JOIN empresas b
                ON a.cnpj = b.cnpj AND a.id < b.id
             WHERE a.cnpj IS NOT NULL AND a.cnpj <> ''
             ORDER BY a.cnpj""").fetchall():
        achados.append(("CNPJ", linha["a_id"], linha["a_nome"], linha["b_id"],
                        linha["b_nome"], f"mesmo CNPJ {linha['o_cnpj']}"))

    # 2. mesmo conjunto de palavras fortes, e sem CNPJ que os separe. Se os dois
    #    TÊM CNPJ e são diferentes, são empresas diferentes com nome parecido —
    #    exatamente as homônimas que o Drive desambiguou à mão.
    por_chave = {}
    for e in db.execute("SELECT id, nome, cnpj FROM empresas ORDER BY id").fetchall():
        k = chave_fraca(e["nome"])
        if k:
            por_chave.setdefault(k, []).append(e)
    for k, grupo in por_chave.items():
        if len(grupo) < 2:
            continue
        for i in range(len(grupo)):
            for j in range(i + 1, len(grupo)):
                a, b = grupo[i], grupo[j]
                if a["cnpj"] and b["cnpj"] and a["cnpj"] != b["cnpj"]:
                    continue                      # CNPJ diferente: são outras
                if a["cnpj"] and b["cnpj"]:
                    continue                      # já pego pela regra do CNPJ
                achados.append(("NOME", a["id"], a["nome"], b["id"], b["nome"],
                                "mesmas palavras, e nenhum CNPJ os separa"))

    if aplicar:
        for _, aid, _, bid, _, prova in achados:
            db.execute("""INSERT INTO empresa_relacoes (empresa_id, relacionada_id, tipo, prova)
                          VALUES (?,?, 'MESMA_EMPRESA', ?)
                          ON CONFLICT (empresa_id, relacionada_id, tipo) DO NOTHING""",
                       (aid, bid, prova))
        db.commit()
    return achados


def carteira(db, caminho, aplicar=False, quem=None):
    """A carteira empresa → advogado, da planilha `DIVISÃO DAS EMPRESAS / ADVS`.

    CSV com cabeçalho: `empresa,responsavel[,papel]`. Casa a empresa por
    nome normalizado e a pessoa por nome normalizado — e RECUSA a linha que não
    casa ou que casa em dois, em vez de escolher por semelhança. Semelhança
    casa Marina com Marize, e aqui o erro entregaria a carteira de uma reclamada
    a quem não a acompanha.
    """
    emp = {}
    for e in db.execute("SELECT id, nome, nome_norm FROM empresas").fetchall():
        emp.setdefault(norm(e["nome_norm"] or e["nome"]), []).append(e["id"])
    pes = {}
    for p in db.execute("SELECT id, nome FROM pessoas WHERE ativo = true").fetchall():
        pes.setdefault(norm(p["nome"]), []).append(p["id"])

    ok, recusadas = [], []
    with open(caminho, encoding="utf-8-sig") as f:
        for i, linha in enumerate(csv.DictReader(f), 2):
            e_nome = (linha.get("empresa") or "").strip()
            r_nome = (linha.get("responsavel") or "").strip()
            papel = (linha.get("papel") or "RESPONSAVEL").strip().upper() or "RESPONSAVEL"
            if not e_nome or not r_nome:
                recusadas.append((i, e_nome, r_nome, "linha incompleta"))
                continue
            e_ids = emp.get(norm(e_nome), [])
            p_ids = pes.get(norm(r_nome), [])
            if len(e_ids) != 1:
                recusadas.append((i, e_nome, r_nome,
                                  "empresa não encontrada" if not e_ids
                                  else f"empresa casa em {len(e_ids)} cadastros"))
                continue
            if len(p_ids) != 1:
                recusadas.append((i, e_nome, r_nome,
                                  "pessoa não encontrada" if not p_ids
                                  else f"pessoa casa em {len(p_ids)}"))
                continue
            if papel not in ("RESPONSAVEL", "APOIO"):
                recusadas.append((i, e_nome, r_nome, f"papel desconhecido: {papel}"))
                continue
            ok.append((e_ids[0], p_ids[0], papel, e_nome, r_nome))

    # Nada pela metade: uma linha ruim impede a carga toda, como em
    # `equipe_setores.py`. Carteira meio aplicada é pior que não aplicada.
    if aplicar and recusadas:
        return ok, recusadas, False
    if aplicar:
        for eid, pid, papel, _, _ in ok:
            ja = db.execute("""SELECT 1 FROM empresa_carteira
                                WHERE empresa_id=? AND pessoa_id=? AND papel=? AND ate IS NULL""",
                            (eid, pid, papel)).fetchone()
            if not ja:
                db.execute("""INSERT INTO empresa_carteira (empresa_id, pessoa_id, papel, desde)
                              VALUES (?,?,?, date('now'))""", (eid, pid, papel))
        db.commit()
    return ok, recusadas, aplicar


def resumo(db):
    r = db.execute("""
        SELECT (SELECT COUNT(*) FROM empresas) empresas,
               (SELECT COUNT(*) FROM empresas WHERE cnpj IS NOT NULL AND cnpj <> '') com_cnpj,
               (SELECT COUNT(*) FROM processo_empresas) partes,
               (SELECT COUNT(*) FROM processo_empresas WHERE papel <> 'RECLAMADA') corres,
               (SELECT COUNT(*) FROM empresa_relacoes) relacoes,
               (SELECT COUNT(*) FROM empresa_relacoes WHERE tipo='MESMA_EMPRESA') repetidas,
               (SELECT COUNT(*) FROM empresa_carteira WHERE ate IS NULL) carteira,
               (SELECT COUNT(DISTINCT empresa_id) FROM empresa_carteira WHERE ate IS NULL) emp_com_dono
        """).fetchone()
    print(f"  empresas ................. {r['empresas']}  ({r['com_cnpj']} com CNPJ)")
    print(f"  partes em processos ...... {r['partes']}  ({r['corres']} co-rés ou tomadores)")
    print(f"  relações entre empresas .. {r['relacoes']}  ({r['repetidas']} marcadas como repetidas)")
    print(f"  carteira ................. {r['carteira']} vínculos, {r['emp_com_dono']} empresas com dono")
    sem = r["empresas"] - r["emp_com_dono"]
    if sem > 0:
        print(f"\n  {sem} empresa(s) sem responsável na carteira. Caso novo dessas cai na fila\n"
              "  geral em vez de ir para quem acompanha a reclamada.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sincronizar", action="store_true",
                   help="processos.empresa_id → processo_empresas (RECLAMADA)")
    p.add_argument("--duplicatas", action="store_true", help="cadastros repetidos da mesma empresa")
    p.add_argument("--carteira", help="CSV empresa,responsavel[,papel]")
    p.add_argument("--aplicar", action="store_true", help="grava (senão só confere)")
    p.add_argument("--resumo", action="store_true")
    p.add_argument("--dsn", help="ligação com o Postgres (senão GGV_SUPABASE_TRAB)")
    a = p.parse_args()
    if a.dsn:
        os.environ["GGV_DSN"] = a.dsn
    db = banco.conectar()
    try:
        if a.sincronizar:
            print(f"{sincronizar(db)} parte(s) de processo criadas como RECLAMADA.")
        if a.duplicatas:
            achados = duplicatas(db, a.aplicar)
            if not achados:
                print("nenhum cadastro repetido de empresa.")
            for tipo, aid, anome, bid, bnome, prova in achados:
                print(f"  [{tipo}] #{aid} {anome!r}  ==  #{bid} {bnome!r}   ({prova})")
            if achados and not a.aplicar:
                print(f"\n{len(achados)} par(es). Com --aplicar, cada um vira uma relação\n"
                      "MESMA_EMPRESA. Nada é fundido: os dois cadastros continuam, e quem\n"
                      "decide juntar é gente.")
        if a.carteira:
            ok, recusadas, gravou = carteira(db, a.carteira, a.aplicar)
            print(f"{len(ok)} linha(s) boa(s), {len(recusadas)} recusada(s).")
            for i, e, r, porque in recusadas:
                print(f"  linha {i}: {e!r} → {r!r} — {porque}")
            if recusadas and a.aplicar:
                print("\nNADA foi gravado: uma linha ruim impede a carga toda. Corrija e rode de novo.")
            elif gravou:
                print("carteira aplicada.")
        if a.resumo or not any((a.sincronizar, a.duplicatas, a.carteira)):
            resumo(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
