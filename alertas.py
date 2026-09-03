#!/usr/bin/env python3
"""O que pega fogo NUM processo — o mesmo sinal em toda tela que leva a ele.

Vem do `alertas.py` do Prev. A ideia é a que importa: quem abre uma lista não
deveria precisar entrar caso a caso para descobrir o que está pegando fogo, e
o sinal tem de ser o MESMO na lista, na ficha e no início. Sinal que muda de
tela para tela ensina a pessoa a não confiar em nenhum.

O que é sinal aqui, do mais grave para o menos:

  vermelho  prazo vencido ou vencendo hoje · audiência hoje ou amanhã ·
            incidente de representação aberto (o cliente trocou de advogado)
  âmbar     prazo em até 2 dias úteis · audiência em até 7 dias sem preparação ·
            parcela de acordo vencida sem pagamento
  neutro    pendência de documento parada há mais de 15 dias

`por_processo` responde a lista inteira em poucas consultas: uma por sinal,
não uma por processo. Com 3.722 processos, o contrário seria a tela.
"""
import prazo_legal

NIVEIS = {"vermelho": 0, "ambar": 1, "neutro": 2}


def _a(nivel, resumo, detalhe=None, quando=None):
    return dict(nivel=nivel, resumo=resumo, detalhe=detalhe, quando=quando, n=1)


def por_processo(db, ids):
    """{processo_id: sinal} — só o mais grave de cada, com `n` = quantos há."""
    ids = [i for i in (ids or []) if i]
    if not ids:
        return {}
    marca = ",".join("?" for _ in ids)
    achados = {}

    def juntar(pid, sinal):
        atual = achados.get(pid)
        if atual is None:
            achados[pid] = sinal
            return
        atual["n"] += 1
        if NIVEIS[sinal["nivel"]] < NIVEIS[atual["nivel"]]:
            sinal["n"] = atual["n"]
            achados[pid] = sinal

    # prazos abertos
    for r in db.execute(f"""SELECT z.processo_id, z.vencimento, COALESCE(pt.nome, z.tipo,
                                   'prazo') nome
                            FROM prazos z LEFT JOIN prazo_tipos pt ON pt.codigo = z.tipo
                            WHERE z.situacao='ABERTO' AND z.vencimento IS NOT NULL
                              AND z.processo_id IN ({marca})
                              AND z.vencimento <= date('now','+10 day')
                            ORDER BY z.vencimento""", tuple(ids)):
        uteis = prazo_legal.faltam(r["vencimento"])
        if uteis is None or uteis > 2:
            continue
        juntar(r["processo_id"], _a(
            "vermelho" if uteis <= 0 else "ambar",
            "prazo vencido" if uteis < 0 else "prazo hoje" if uteis == 0
            else f"prazo em {uteis}d úteis",
            r["nome"], r["vencimento"]))

    # audiências marcadas
    for r in db.execute(f"""SELECT a.processo_id, a.data_hora, a.tipo,
                    (substr(a.data_hora,1,10)::date
                     - (now() AT TIME ZONE 'America/Sao_Paulo')::date) dias,
                    (a.cliente_orientado_em IS NULL AND a.testemunhas_confirmadas_em IS NULL
                     AND a.advideo_em IS NULL AND a.documentos_conferidos_em IS NULL) crua
                 FROM audiencias a
                 WHERE a.situacao IN ('DESIGNADA','EM_PREPARACAO')
                   AND a.data_hora IS NOT NULL AND a.processo_id IN ({marca})
                   AND substr(a.data_hora,1,10)::date
                       BETWEEN (now() AT TIME ZONE 'America/Sao_Paulo')::date
                           AND (now() AT TIME ZONE 'America/Sao_Paulo')::date + 7
                 ORDER BY a.data_hora""", tuple(ids)):
        dias = r["dias"] or 0
        if dias <= 1:
            juntar(r["processo_id"], _a("vermelho",
                   "audiência hoje" if dias == 0 else "audiência amanhã",
                   (r["tipo"] or "").lower() or None, (r["data_hora"] or "")[:16]))
        elif r["crua"]:
            juntar(r["processo_id"], _a("ambar", f"audiência em {dias}d sem preparação",
                   "cliente, testemunhas, ad video e documentos", (r["data_hora"] or "")[:16]))

    # incidente de representação aberto
    for r in db.execute(f"""SELECT processo_id, situacao FROM incidentes
                            WHERE processo_id IN ({marca})
                              AND situacao IN ('DETECTADO','NOTIFICADO','HONORARIOS_RESERVADOS')""",
                        tuple(ids)):
        juntar(r["processo_id"], _a("vermelho", "outro advogado nos autos",
               "incidente de representação " + (r["situacao"] or "").lower()))

    # parcela de acordo vencida e sem pagamento
    for r in db.execute(f"""SELECT a.processo_id, MIN(ap.vencimento) venceu, COUNT(*) n
                            FROM acordo_parcelas ap JOIN acordos a ON a.id = ap.acordo_id
                            WHERE a.processo_id IN ({marca}) AND ap.pago_em IS NULL
                              AND ap.vencimento IS NOT NULL AND ap.vencimento < date('now')
                            GROUP BY a.processo_id""", tuple(ids)):
        juntar(r["processo_id"], _a("ambar", f"{r['n']} parcela(s) atrasada(s)",
               "parcela atrasada é quebra: multa da cláusula penal e execução do saldo",
               r["venceu"]))

    # pendência parada
    for r in db.execute(f"""SELECT processo_id, COUNT(*) n FROM pendencias
                            WHERE processo_id IN ({marca}) AND recebido_em IS NULL
                              AND dispensado_motivo IS NULL
                              AND solicitado_em IS NOT NULL
                              AND solicitado_em <= date('now','-15 day')
                            GROUP BY processo_id""", tuple(ids)):
        juntar(r["processo_id"], _a("neutro", f"{r['n']} pendência(s) sem resposta",
               "pedido há mais de 15 dias"))

    return achados


def do_processo(db, processo_id):
    """Os sinais de um processo só, todos, para a ficha."""
    achado = por_processo(db, [processo_id]).get(processo_id)
    return [achado] if achado else []


def por_cliente(db, ids):
    """{cliente_id: sinal} — o pior sinal entre os processos da pessoa."""
    ids = [i for i in (ids or []) if i]
    if not ids:
        return {}
    marca = ",".join("?" for _ in ids)
    de_quem = {r["id"]: r["cliente_id"] for r in db.execute(
        f"SELECT id, cliente_id FROM processos WHERE cliente_id IN ({marca})", tuple(ids))}
    saida = {}
    for pid, sinal in por_processo(db, list(de_quem)).items():
        cid = de_quem[pid]
        atual = saida.get(cid)
        if atual is None or NIVEIS[sinal["nivel"]] < NIVEIS[atual["nivel"]]:
            saida[cid] = sinal
    return saida
