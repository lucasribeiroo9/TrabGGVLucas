#!/usr/bin/env python3
"""Setor, cargo e chefia — o que a base de origem não guarda.

Vem do `equipe.py` do Prev. O que muda aqui é só o conteúdo: no Prev os
setores eram cinco (Direção, Jurídico, Documentação, Captação, Financeiro);
aqui o Lucas respondeu outra coisa (resposta 8):

    "Existe um setor próprio para cada etapa."

Ou seja: o setor não é rótulo genérico, é **quem responde pela etapa**. Quem
aprova a inicial é a equipe de Petição Inicial, não a Gestão. Por isso a lista
abaixo nasce dos setores por etapa, e não dos cinco do Prev.

A origem (FUNCIONARIOS, 72 registros) tem FUNCOES — advogado, captador,
entrevistador, responsável inicial — e não tem setor nem organograma. Então:

  · `pessoas.setor` sai daqui, aplicado depois da migração (sobrevive a ela);
  · `pessoas.supervisor_id` sai de CHEFIA, pelo mesmo caminho.

[CONFIRMAR — pergunta 30] A lista fechada de setores e quem chefia cada um.
Nada abaixo é invenção sobre pessoas: AJUSTES e CHEFIA estão VAZIOS de
propósito. Preencher com palpite seria pôr na tela um organograma que ninguém
do escritório disse.
"""
import banco

# ---------------------------------------------------------------------------
# Os setores. [CONFIRMAR pergunta 30: esta lista é a fechada?]
#
# ATENÇÃO à divergência que o portal já encontrou: `fluxo_etapas.grupo`, em
# governanca.sql, usa hoje SETE nomes — Captação, Documentação, Atendimento,
# Jurídico, Gestão, Financeiro, Direção. A lista de doze abaixo é a que o
# diretor passou. Enquanto as duas não forem a mesma, o portal mostra o grupo
# da ETAPA (que é dado, vindo da tabela) e usa esta lista só para o cadastro
# de pessoa. Ver docs/portal-adaptacoes.md.
SETORES = [
    "Captação",
    "Atendimento/Entrevista",
    "Documentação",
    "Petição Inicial",
    "Jurídico/Processual",
    "Audiências",
    "Execução",
    "Testemunhas",
    "Financeiro",
    "TI",
    "Publicação",
    "Direção",
]

# Os nomes que `fluxo_etapas.grupo` usa hoje, e para qual setor da lista acima
# cada um aponta. Serve para a tela dizer "esta etapa é da Documentação" e a
# fila por setor casar — sem reescrever a governança antes do OK do Lucas.
GRUPO_DA_ETAPA = {
    "Captação":     "Captação",
    "Atendimento":  "Atendimento/Entrevista",
    "Documentação": "Documentação",
    "Jurídico":     "Jurídico/Processual",
    # A aprovação da inicial JÁ é da etapa de grupo "Petição Inicial" em
    # governanca.sql (resposta 8, implementada em 03/09/2026: papel ADVOGADO +
    # gate setor_peticao_inicial). "Gestão" só sobra em PRAZO → PERDIDO, que é
    # registro de quem gere o escritório. [CONFIRMAR pergunta 30: qual setor
    # da lista responde por isso — Direção?]
    "Gestão":       "Direção",
    "Petição Inicial": "Petição Inicial",
    "Financeiro":   "Financeiro",
    "Direção":      "Direção",
}


def setor_da_etapa(grupo):
    """O setor do escritório que responde por uma etapa do mapa."""
    return GRUPO_DA_ETAPA.get(grupo, grupo)


# ---------------------------------------------------------------------------
# O que o escritório sabe e a base não guarda. VAZIO até o Lucas responder a
# pergunta 30 — cargo e chefia inventados apareceriam na tela como se fossem
# fato, e organograma errado manda tarefa para a pessoa errada.
#
#   AJUSTES["NOME NORMALIZADO"] = dict(setor="Jurídico/Processual", cargo="...")
AJUSTES = {}          # [CONFIRMAR pergunta 30]

#   CHEFIA["QUEM"] = "O CHEFE"        (nomes normalizados, como em pessoas.nome_norm)
CHEFIA = {}           # [CONFIRMAR pergunta 30]


def aplicar(db):
    """Escreve setor, cargo e chefia em `pessoas`. Idempotente.

    Roda depois da migração, e de novo a cada remontagem: é isto que faz o
    organograma sobreviver a uma carga que recria as linhas.
    """
    mexidas = 0
    for nome_norm, campos in AJUSTES.items():
        pares = ", ".join(f"{k}=?" for k in campos)
        cur = db.execute(f"UPDATE pessoas SET {pares} WHERE nome_norm=?",
                         tuple(campos.values()) + (nome_norm,))
        mexidas += cur.rowcount or 0
    for quem, chefe in CHEFIA.items():
        cur = db.execute("""UPDATE pessoas SET supervisor_id =
                              (SELECT id FROM pessoas WHERE nome_norm=?)
                            WHERE nome_norm=?""", (chefe, quem))
        mexidas += cur.rowcount or 0
    db.commit()
    return mexidas


def carga(db, setor=None):
    """Quantas tarefas abertas cada pessoa tem. Urgente pesa 3, atrasada 2.

    É a conta que a distribuição automática usa, e é a mesma que a tela de
    Equipe mostra — se fossem duas contas, a tela explicaria uma distribuição
    que não aconteceu.
    """
    return db.execute("""SELECT p.id, p.nome, p.setor,
                COUNT(t.id) FILTER (WHERE t.status IN ('ABERTA','EM_ANDAMENTO')) abertas,
                COALESCE(SUM(CASE
                    WHEN t.status NOT IN ('ABERTA','EM_ANDAMENTO') THEN 0
                    WHEN t.prioridade='URGENTE' THEN 3
                    WHEN t.prazo IS NOT NULL AND t.prazo < date('now') THEN 2
                    ELSE 1 END), 0) peso
             FROM pessoas p
             LEFT JOIN tarefas t ON t.responsavel_id = p.id
             WHERE p.ativo = true AND (? IS NULL OR p.setor = ?)
             GROUP BY p.id, p.nome, p.setor
             ORDER BY peso DESC, p.nome""", (setor, setor)).fetchall()


if __name__ == "__main__":
    db = banco.conectar()
    n = aplicar(db)
    print(f"{n} ajuste(s) aplicado(s).")
    if not AJUSTES and not CHEFIA:
        print("AJUSTES e CHEFIA estão vazios: falta a resposta 30 do Lucas "
              "(setores fechados e quem chefia cada um).")
    print()
    print(f"{'pessoa':<34}{'setor':<26}{'abertas':>8}{'peso':>7}")
    print("-" * 76)
    for r in carga(db):
        print(f"{(r['nome'] or '')[:32]:<34}{(r['setor'] or '—')[:24]:<26}"
              f"{r['abertas']:>8}{r['peso']:>7}")
    db.close()
