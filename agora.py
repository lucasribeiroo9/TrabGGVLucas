#!/usr/bin/env python3
"""O que faz parar o que se está fazendo.

Vem do `agora.py` do Prev, com a mesma regra e outro conteúdo: só entra o que
tem **gente parada** ou **relógio externo correndo**. O que pode esperar até
amanhã sem consequência não entra — lista que cresce demais perde o sentido, e
o teto continua sendo 6 itens.

No trabalhista o que faz parar é isto:

  1. **Audiência em até 7 dias sem nenhuma preparação.** Confirmar testemunha
     leva tempo: ela comparece sem intimação (CLT art. 825) e, se falhar, é
     preciso pedir a intimação com antecedência.
  2. **Prazo vencendo em até 2 dias úteis** (ou já vencido). Dias ÚTEIS,
     art. 775 da CLT — contar corridos aqui adiantaria o alarme, o que é
     seguro, mas atrasaria a ordenação de quem vence primeiro.
  3. **Prescrição bienal a menos de 60 dias** e o caso ainda sem distribuir.
     É a perda evitável que o escritório precisa medir (CF art. 7º XXIX).
  4. **Pendência de documento sem resposta há mais de 15 dias.** Pedido sem
     recebimento confirmado continua pendente (resposta 7 do Lucas).
  5. **Minuta aguardando aprovação há mais de 2 dias.** É o gargalo do funil:
     54 casos parados ali contra 6 em redação.
  6. Tarefa vencida, ou marcada URGENTE na mão.

A conta é sempre DENTRO do recorte: quem tem `pessoa_id` vê o que é seu e o
que não tem dono; a Direção vê o escritório.
"""
import banco
import prazo_legal

TETO = 6


def _linha(chave, titulo, motivo, link, quem=None, quando=None, peso=0):
    tipo, _, ref = chave.partition(":")
    return dict(chave=chave, titulo=titulo, motivo=motivo, link=link, quem=quem,
                quando=quando, peso=peso, tipo=tipo, ref=ref)


def listar(db, pessoa_id=None, setor=None, papel=None):
    """A lista do que é para agora. Ordenada do mais urgente."""
    q = lambda s, a=(): db.execute(s, a).fetchall()
    itens = []
    meu = pessoa_id

    # 1. audiência em até 7 dias sem nenhum item do checklist
    for r in q("""SELECT v.id, v.dias_para_audiencia dias, v.data_hora, v.tipo,
                         p.id proc_id, p.numero_cnj, c.nome cliente
                  FROM v_audiencias_sem_preparacao v
                  JOIN processos p ON p.id = v.processo_id
                  JOIN clientes c ON c.id = p.cliente_id
                  ORDER BY v.data_hora LIMIT 6"""):
        dias = r["dias"]
        itens.append(_linha(
            f"audiencia:{r['id']}",
            "Preparar a audiência" + (f" ({(r['tipo'] or '').lower()})" if r["tipo"] else ""),
            ("é hoje e nada foi preparado" if dias is not None and dias <= 0
             else f"em {dias} dia(s) e nada foi preparado — cliente, testemunhas, ad video, documentos"),
            f"/audiencias/{r['id']}", r["cliente"], (r["data_hora"] or "")[:16],
            peso=-1 if (dias or 0) <= 1 else 0))

    # 2. prazo vencendo em até 2 dias úteis, ou vencido
    for r in q("""SELECT z.id, z.vencimento, z.tipo, z.descricao, pt.nome tipo_nome,
                         p.id proc_id, c.nome cliente
                  FROM prazos z
                  JOIN processos p ON p.id = z.processo_id
                  JOIN clientes c ON c.id = p.cliente_id
                  LEFT JOIN prazo_tipos pt ON pt.codigo = z.tipo
                  WHERE z.situacao='ABERTO' AND z.vencimento IS NOT NULL
                    AND z.vencimento <= date('now','+6 day')
                    AND (? IS NULL OR z.responsavel_id=? OR z.responsavel_id IS NULL)
                  ORDER BY z.vencimento LIMIT 10""", (meu, meu)):
        uteis = prazo_legal.faltam(r["vencimento"])
        if uteis is None or uteis > 2:
            continue
        itens.append(_linha(
            f"prazo:{r['id']}", r["tipo_nome"] or r["descricao"] or "Prazo processual",
            ("prazo VENCIDO" if uteis < 0 else
             "vence hoje" if uteis == 0 else f"vence em {uteis} dia(s) úteis"),
            f"/processos/{r['proc_id']}", r["cliente"], r["vencimento"],
            peso=-2 if uteis <= 0 else 0))

    # 3. prescrição bienal a menos de 60 dias, ainda sem distribuir
    for r in q("""SELECT c.id, c.nome, c.status, c.data_demissao,
                         (c.data_demissao::date + INTERVAL '2 years')::date prescreve,
                         ((c.data_demissao::date + INTERVAL '2 years')::date
                          - (now() AT TIME ZONE 'America/Sao_Paulo')::date) faltam
                  FROM clientes c
                  JOIN fluxo_etapas fe ON fe.fluxo_id = 1 AND fe.codigo = c.status
                  WHERE fe.tipo <> 'FINAL'
                    AND c.data_demissao IS NOT NULL
                    AND NOT COALESCE(c.contrato_vivo, false)
                    AND COALESCE(c.dispensa_prescricao_motivo,'') = ''
                    AND (c.data_demissao::date + INTERVAL '2 years')::date
                        <= (now() AT TIME ZONE 'America/Sao_Paulo')::date + 60
                    AND (? IS NULL OR c.responsavel_id=? OR c.responsavel_id IS NULL)
                  ORDER BY prescreve LIMIT 8""", (meu, meu)):
        faltam = r["faltam"]
        itens.append(_linha(
            f"prescricao:{r['id']}", "Prescrição bienal chegando",
            ("JÁ PRESCREVEU" if faltam is not None and faltam < 0
             else f"prescreve em {faltam} dia(s) e o caso não foi distribuído"),
            f"/clientes/{r['id']}", r["nome"], str(r["prescreve"]),
            peso=-2 if (faltam or 0) < 15 else 0))

    # 4. pendência de documento sem resposta há mais de 15 dias
    for r in q("""SELECT p.id, p.documento_tipo, p.descricao, p.solicitado_em,
                         c.id cliente_id, c.nome,
                         cast(julianday('now') - julianday(p.solicitado_em) as int) dias
                  FROM pendencias p JOIN clientes c ON c.id = p.cliente_id
                  WHERE p.tipo='DOCUMENTO' AND p.recebido_em IS NULL
                    AND p.dispensado_motivo IS NULL AND p.solicitado_em IS NOT NULL
                    AND p.solicitado_em <= date('now','-15 day')
                    AND (? IS NULL OR p.responsavel_id=? OR p.responsavel_id IS NULL)
                  ORDER BY p.solicitado_em LIMIT 6""", (meu, meu)):
        itens.append(_linha(
            f"pendencia:{r['id']}",
            "Cobrar " + (r["documento_tipo"] or "documento").replace("_", "/").lower(),
            f"pedido há {r['dias']} dias e sem resposta",
            f"/clientes/{r['cliente_id']}", r["nome"], r["solicitado_em"], peso=1))

    # 5. minuta esperando aprovação há mais de 2 dias
    # `julianday(...)` só é traduzido com UM nível de parênteses dentro
    # (banco.py); por isso o COALESCE aninhado sai numa subconsulta com nome,
    # e não empilhado dentro da chamada.
    for r in q("""SELECT x.id, x.nome,
                         cast(julianday('now') - julianday(x.desde) as int) dias
                  FROM (SELECT c.id, c.nome,
                               COALESCE((SELECT MAX(h.em) FROM historico_etapas h
                                          WHERE h.entidade='clientes' AND h.entidade_id=c.id
                                            AND h.para='PETICAO_AGUARDANDO_APROVACAO'),
                                        c.criado_em) desde
                        FROM clientes c
                        WHERE c.status='PETICAO_AGUARDANDO_APROVACAO') x
                  ORDER BY dias DESC LIMIT 6"""):
        if (r["dias"] or 0) <= 2:
            continue
        itens.append(_linha(
            f"aprovar:{r['id']}", "Aprovar ou devolver a inicial",
            f"a minuta espera aprovação há {r['dias']} dias",
            f"/clientes/{r['id']}", r["nome"], None, peso=1))

    # 6. tarefa vencida ou marcada urgente
    if meu:
        for r in q("""SELECT t.id, t.titulo, t.prazo, t.prioridade,
                             c.nome cliente, c.id cliente_id, p.id proc_id
                      FROM tarefas t
                      LEFT JOIN clientes c ON c.id = t.cliente_id
                      LEFT JOIN processos p ON p.id = t.processo_id
                      WHERE t.responsavel_id=? AND t.status IN ('ABERTA','EM_ANDAMENTO')
                        AND (t.prioridade='URGENTE'
                             OR (t.prazo IS NOT NULL AND t.prazo < date('now')))
                      ORDER BY (t.prioridade<>'URGENTE'), t.prazo LIMIT 8""", (meu,)):
            itens.append(_linha(
                f"tarefa:{r['id']}", r["titulo"],
                "marcada como urgente" if r["prioridade"] == "URGENTE"
                else f"prazo venceu em {r['prazo']}",
                (f"/processos/{r['proc_id']}" if r["proc_id"]
                 else f"/clientes/{r['cliente_id']}" if r["cliente_id"] else "/tarefas"),
                r["cliente"], r["prazo"], peso=0))

    itens.sort(key=lambda i: (i["peso"], i["quando"] or ""))
    return itens[:TETO]


if __name__ == "__main__":
    db = banco.conectar()
    for i in listar(db):
        print(f"· {i['titulo'][:46]:46} | {i['motivo'][:44]:44} | {i['quem'] or ''}")
    db.close()
