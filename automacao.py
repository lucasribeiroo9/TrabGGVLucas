#!/usr/bin/env python3
"""O motor de regras. Cria tarefa e rascunho; NUNCA protocola nem move etapa.

Vem do `automacao.py` do Prev — o MOTOR veio inteiro: registro das regras,
config, `_uma_vez`, abertura de tarefa e o `Distribuidor` são os mesmos, com as
colunas deste esquema. O que não veio foram as REGRAS: as do Prev falam de
INSS, CNIS, exigência e Tema 350, e não há tradução honesta disso para o
trabalhista. As regras abaixo são novas e todas param no mesmo lugar — abrem
tarefa com dono e prazo, e ponto. Quem decide é gente.

**Toda execução deixa rastro** (`automacao_log.resultado`), porque o modo de
falha de automação é o silêncio: rodada que falhou tem de ser distinguível de
dia sem nada a fazer. Quem vigia isso é `execucao.py`.

**A idempotência é a chave natural** `(automacao, chave)`, com UNIQUE no banco:
a segunda passagem pela mesma situação encontra a linha e não faz nada. Sem
isso, três rodadas por dia abririam três tarefas iguais.

    python3 automacao.py            # roda tudo e diz o que fez
    python3 automacao.py --seco     # só diz o que faria
"""
import json
import sys

import banco

# codigo, nome, descrição em linguagem de operador
REGRAS = [
    ("PRESCRICAO_BIENAL", "Prescrição bienal chegando abre tarefa urgente",
     "Quando faltam 60 dias ou menos para os dois anos do fim do contrato "
     "(CF art. 7º XXIX; CLT art. 11) e o caso ainda não foi distribuído, nasce "
     "tarefa URGENTE para quem cuida do caso."),
    ("AUDIENCIA_PREPARAR", "Audiência marcada abre a tarefa de preparação",
     "Sete dias antes da audiência, se nenhum item do checklist foi feito, "
     "nasce a tarefa de preparar: orientar o cliente, confirmar as testemunhas "
     "(que comparecem sem intimação, CLT art. 825 — se falhar, é preciso pedir "
     "a intimação com antecedência), fazer o ad video e conferir os documentos."),
    ("PRAZO_A_VENCER", "Prazo a dois dias úteis abre tarefa para quem responde",
     "Prazo aberto vencendo em até 2 dias úteis vira tarefa com prioridade "
     "ALTA. A contagem é em dias úteis (CLT art. 775) e usa os feriados de "
     "prazo_legal.py."),
    ("PENDENCIA_PARADA", "Documento pedido e sem resposta vira cobrança",
     "Pendência de documento pedida há mais de 15 dias e ainda sem recebimento "
     "confirmado abre tarefa de cobrança para a Documentação. Pedido sem "
     "confirmação continua pendente — foi o que o Lucas respondeu na 7."),
    ("ACORDO_PARCELA_ATRASADA", "Parcela de acordo atrasada abre tarefa no jurídico",
     "Parcela vencida e sem pagamento registrado é quebra de acordo: multa da "
     "cláusula penal e execução do saldo."),
    ("DISTRIBUIR_FILA", "Tarefa sem dono vai para quem está mais leve no setor",
     "Tarefa que nasce sem responsável é entregue a quem tem menos peso no "
     "mesmo setor — urgente pesa 3, atrasada 2, o resto 1. Teto de 15 por "
     "pessoa; quem passa disso não recebe mais e a tarefa fica na fila para o "
     "supervisor resolver."),
]


# ------------------------------------------------------------------ motor
def garantir(db):
    for codigo, nome, desc in REGRAS:
        db.execute("""INSERT INTO automacoes (codigo, nome, descricao)
                      VALUES (?,?,?)
                      ON CONFLICT (codigo) DO UPDATE SET nome=excluded.nome,
                        descricao=excluded.descricao""", (codigo, nome, desc))
    db.commit()


def config(db, codigo, padrao=None):
    r = db.execute("SELECT config FROM automacoes WHERE codigo=?", (codigo,)).fetchone()
    cfg = dict(padrao or {})
    if r and r[0]:
        bruto = r[0] if isinstance(r[0], dict) else json.loads(r[0])
        cfg.update({k: v for k, v in bruto.items() if v not in (None, "")})
    return cfg


def ativa(db, codigo):
    r = db.execute("SELECT ativa FROM automacoes WHERE codigo=?", (codigo,)).fetchone()
    return bool(r and r[0])


def _uma_vez(db, codigo, chave, detalhe, cliente_id=None, processo_id=None):
    """True se esta chave ainda não foi tratada por esta regra.

    O UNIQUE (automacao, chave) é a trava. `banco.Integridade` pega o erro nos
    dois motores, e cada escrita roda em SAVEPOINT — o duplicado desfaz só a
    si mesmo, e a rodada segue.
    """
    try:
        db.execute("""INSERT INTO automacao_log (automacao, chave, detalhe, resultado,
                        cliente_id, processo_id)
                      VALUES (?,?,?, 'OK', ?,?)""",
                   (codigo, chave, detalhe, cliente_id, processo_id))
        return True
    except banco.Integridade:
        return False


class Distribuidor:
    """Quem recebe o próximo trabalho — com a carga andando a cada entrega.

    É objeto, e não função pura, porque a carga tem de ANDAR: distribuir oito
    tarefas chamando uma função pura mandaria as oito para a mesma pessoa — a
    mais leve no instante zero, que depois da primeira já não é mais.

    Peso, e não contagem: urgente pesa 3, atrasada 2, o resto 1. Quem carrega
    urgência não é o mais leve só por ter menos linhas.
    """

    def __init__(self, db, teto=15):
        self.teto = teto
        self.carga = {r["id"]: r["peso"] for r in db.execute("""
            SELECT pe.id, COALESCE(SUM(CASE WHEN t.prioridade='URGENTE' THEN 3
                        WHEN t.prazo IS NOT NULL AND t.prazo < date('now') THEN 2
                        ELSE 1 END), 0) peso
            FROM pessoas pe LEFT JOIN tarefas t
              ON t.responsavel_id = pe.id AND t.status IN ('ABERTA','EM_ANDAMENTO')
            WHERE pe.ativo = true GROUP BY pe.id""")}
        self.abertas = {r["id"]: r["n"] for r in db.execute("""
            SELECT responsavel_id id, COUNT(*) n FROM tarefas
            WHERE status IN ('ABERTA','EM_ANDAMENTO') AND responsavel_id IS NOT NULL
            GROUP BY responsavel_id""")}
        self.equipe = {}
        for r in db.execute("""SELECT id, nome, setor FROM pessoas
                               WHERE ativo = true AND setor IS NOT NULL ORDER BY nome"""):
            self.equipe.setdefault(r["setor"], []).append(dict(id=r["id"], nome=r["nome"]))

    def escolher(self, setor, urgente=False):
        """(id, nome, carga_antes). (None, None, None) quando todos no teto."""
        gente = [x for x in self.equipe.get(setor or "", [])
                 if self.abertas.get(x["id"], 0) < self.teto]
        if not gente:
            return None, None, None
        e = min(gente, key=lambda x: (self.carga.get(x["id"], 0), x["nome"]))
        antes = self.carga.get(e["id"], 0)
        self.carga[e["id"]] = antes + (3 if urgente else 1)
        self.abertas[e["id"]] = self.abertas.get(e["id"], 0) + 1
        return e["id"], e["nome"], antes


def abrir_tarefa(db, titulo, detalhe, tipo, cliente_id=None, processo_id=None,
                 grupo=None, prazo_dias=None, prioridade="NORMAL", responsavel=None):
    """Abre a tarefa se não houver uma igual em aberto. Devolve True se abriu."""
    ja = db.execute("""SELECT 1 FROM tarefas
                       WHERE titulo=? AND status IN ('ABERTA','EM_ANDAMENTO')
                         AND COALESCE(cliente_id,0)=COALESCE(?,0)
                         AND COALESCE(processo_id,0)=COALESCE(?,0)""",
                    (titulo, cliente_id, processo_id)).fetchone()
    if ja:
        return False
    prazo = None
    if prazo_dias is not None:
        prazo = db.execute("SELECT date('now', ?)", (f"+{int(prazo_dias)} days",)).fetchone()[0]
    db.execute("""INSERT INTO tarefas (titulo, detalhe, tipo, cliente_id, processo_id,
                    grupo, responsavel_id, prazo, prioridade, origem)
                  VALUES (?,?,?,?,?,?,?,?,?, 'AUTOMACAO')""",
               (titulo, detalhe, tipo, cliente_id, processo_id, grupo, responsavel,
                prazo, prioridade))
    return True


# ------------------------------------------------------------------ regras
def _prescricao(db, seco, feitos):
    codigo = "PRESCRICAO_BIENAL"
    for r in db.execute("""SELECT c.id, c.nome, c.responsavel_id, c.rescisao_modalidade,
                    ((c.data_demissao::date + INTERVAL '2 years')::date
                     - (now() AT TIME ZONE 'America/Sao_Paulo')::date) faltam
                 FROM clientes c
                 JOIN fluxo_etapas fe ON fe.fluxo_id = 1 AND fe.codigo = c.status
                 WHERE fe.tipo <> 'FINAL' AND c.data_demissao IS NOT NULL
                   AND NOT COALESCE(c.contrato_vivo, false)
                   AND COALESCE(c.dispensa_prescricao_motivo,'') = ''
                   AND (c.data_demissao::date + INTERVAL '2 years')::date
                       <= (now() AT TIME ZONE 'America/Sao_Paulo')::date + 60""").fetchall():
        chave = f"prescricao:{r['id']}"
        detalhe = f"faltam {r['faltam']} dia(s) para a prescrição bienal"
        if seco or not _uma_vez(db, codigo, chave, detalhe, cliente_id=r["id"]):
            continue
        if abrir_tarefa(db, "Distribuir antes da prescrição bienal", detalhe, "ETAPA",
                        cliente_id=r["id"], grupo="Jurídico",
                        prazo_dias=max(1, min(5, r["faltam"] or 1)),
                        prioridade="URGENTE", responsavel=r["responsavel_id"]):
            feitos.append((codigo, chave))


def _audiencias(db, seco, feitos):
    """Só a FILA VIVA: audiência que ainda vai acontecer.

    `v_audiencias_sem_preparacao` não tem piso de data — devolve também as
    2.649 audiências com data no passado que a migração gravou como DESIGNADA
    (a origem não dizia o resultado e a carga não inventou um). Sem o piso, a
    primeira rodada desta regra abriria **2.670 tarefas de uma vez**, e as
    poucas audiências que acontecem nesta semana — a fila de trabalho de
    verdade — sumiriam dentro do passivo. Automação que despeja o histórico no
    colo de alguém não é ajuda: é a lista que ninguém volta a abrir.

    É o mesmo princípio da `DISTRIBUIR_FILA` do Prev, que só alcança o que
    nasce depois de a regra ser ligada. Regra nova trabalha para a frente; o
    passivo é decisão de gestão, e se resolve caso a caso na fila de
    `/audiencias?janela=todas`, não por 2.670 tarefas abertas de madrugada.
    """
    codigo = "AUDIENCIA_PREPARAR"
    for r in db.execute("""SELECT v.id, v.processo_id, v.data_hora, v.dias_para_audiencia dias,
                                  a.responsavel_id, p.cliente_id
                           FROM v_audiencias_sem_preparacao v
                           JOIN audiencias a ON a.id = v.id
                           JOIN processos p ON p.id = v.processo_id
                           WHERE v.dias_para_audiencia >= 0""").fetchall():
        chave = f"audiencia:{r['id']}"
        detalhe = (f"audiência em {r['dias']} dia(s) ({(r['data_hora'] or '')[:16]}) e nenhum "
                   f"item do checklist feito")
        if seco or not _uma_vez(db, codigo, chave, detalhe, processo_id=r["processo_id"]):
            continue
        if abrir_tarefa(db, "Preparar a audiência", detalhe, "AUDIENCIA",
                        cliente_id=r["cliente_id"], processo_id=r["processo_id"],
                        grupo="Jurídico", prazo_dias=max(1, (r["dias"] or 1) - 1),
                        prioridade="ALTA", responsavel=r["responsavel_id"]):
            feitos.append((codigo, chave))


def _prazos(db, seco, feitos):
    import prazo_legal
    codigo = "PRAZO_A_VENCER"
    for r in db.execute("""SELECT z.id, z.processo_id, z.vencimento, z.responsavel_id,
                                  COALESCE(pt.nome, z.tipo, 'prazo') nome, p.cliente_id
                           FROM prazos z JOIN processos p ON p.id = z.processo_id
                           LEFT JOIN prazo_tipos pt ON pt.codigo = z.tipo
                           WHERE z.situacao='ABERTO' AND z.vencimento IS NOT NULL
                             AND z.vencimento <= date('now','+6 day')""").fetchall():
        uteis = prazo_legal.faltam(r["vencimento"])
        if uteis is None or uteis > 2:
            continue
        chave = f"prazo:{r['id']}"
        detalhe = f"{r['nome']} vence em {r['vencimento']} ({uteis} dia(s) úteis)"
        if seco or not _uma_vez(db, codigo, chave, detalhe, processo_id=r["processo_id"]):
            continue
        if abrir_tarefa(db, f"Cumprir prazo: {r['nome']}", detalhe, "PRAZO",
                        cliente_id=r["cliente_id"], processo_id=r["processo_id"],
                        grupo="Jurídico", prazo_dias=max(1, uteis), prioridade="ALTA",
                        responsavel=r["responsavel_id"]):
            feitos.append((codigo, chave))


def _pendencias(db, seco, feitos):
    codigo = "PENDENCIA_PARADA"
    for r in db.execute("""SELECT p.id, p.cliente_id, p.processo_id, p.documento_tipo,
                                  p.solicitado_em, p.responsavel_id,
                                  cast(julianday('now') - julianday(p.solicitado_em) as int) dias
                           FROM pendencias p
                           WHERE p.tipo='DOCUMENTO' AND p.recebido_em IS NULL
                             AND p.dispensado_motivo IS NULL AND p.solicitado_em IS NOT NULL
                             AND p.solicitado_em <= date('now','-15 day')""").fetchall():
        chave = f"pendencia:{r['id']}"
        detalhe = (f"{(r['documento_tipo'] or 'documento')} pedido em {r['solicitado_em']} "
                   f"({r['dias']} dias) e ainda sem confirmação de recebimento")
        if seco or not _uma_vez(db, codigo, chave, detalhe, cliente_id=r["cliente_id"],
                                processo_id=r["processo_id"]):
            continue
        if abrir_tarefa(db, "Cobrar documento pendente", detalhe, "DOCUMENTO",
                        cliente_id=r["cliente_id"], processo_id=r["processo_id"],
                        grupo="Documentação", prazo_dias=3, prioridade="NORMAL",
                        responsavel=r["responsavel_id"]):
            feitos.append((codigo, chave))


def _parcelas(db, seco, feitos):
    codigo = "ACORDO_PARCELA_ATRASADA"
    for r in db.execute("""SELECT ap.id, a.processo_id, p.cliente_id, ap.numero, ap.vencimento
                           FROM acordo_parcelas ap
                           JOIN acordos a ON a.id = ap.acordo_id
                           JOIN processos p ON p.id = a.processo_id
                           WHERE ap.pago_em IS NULL AND ap.vencimento IS NOT NULL
                             AND ap.vencimento < date('now')
                             AND a.situacao = 'EM_ANDAMENTO'""").fetchall():
        chave = f"parcela:{r['id']}"
        detalhe = (f"parcela {r['numero']} venceu em {r['vencimento']} e não há pagamento "
                   f"registrado — é quebra de acordo")
        if seco or not _uma_vez(db, codigo, chave, detalhe, processo_id=r["processo_id"]):
            continue
        if abrir_tarefa(db, f"Parcela {r['numero']} do acordo atrasada", detalhe, "ANDAMENTO",
                        cliente_id=r["cliente_id"], processo_id=r["processo_id"],
                        grupo="Execução", prazo_dias=2, prioridade="ALTA"):
            feitos.append((codigo, chave))


def _distribuir(db, seco, feitos):
    codigo = "DISTRIBUIR_FILA"
    cfg = config(db, codigo, {"teto": 15})
    d = Distribuidor(db, teto=int(cfg.get("teto") or 15))
    for r in db.execute("""SELECT id, titulo, grupo, prioridade FROM tarefas
                           WHERE responsavel_id IS NULL AND status='ABERTA'
                             AND grupo IS NOT NULL
                           ORDER BY (prioridade<>'URGENTE'), (prazo IS NULL), prazo,
                                    id""").fetchall():
        pid, nome, antes = d.escolher(r["grupo"], r["prioridade"] == "URGENTE")
        if not pid:
            continue                       # todo mundo no teto: fica na fila
        chave = f"tarefa:{r['id']}"
        if seco or not _uma_vez(db, codigo, chave, f"para {nome} (carga {antes})"):
            continue
        db.execute("UPDATE tarefas SET responsavel_id=? WHERE id=? AND responsavel_id IS NULL",
                   (pid, r["id"]))
        feitos.append((codigo, chave))


PASSOS = [("PRESCRICAO_BIENAL", _prescricao), ("AUDIENCIA_PREPARAR", _audiencias),
          ("PRAZO_A_VENCER", _prazos), ("PENDENCIA_PARADA", _pendencias),
          ("ACORDO_PARCELA_ATRASADA", _parcelas), ("DISTRIBUIR_FILA", _distribuir)]


def rodar(db, seco=False):
    """Roda as regras ativas. Devolve a lista de (regra, chave) do que fez.

    **A RODADA deixa rastro, mesmo sem fazer nada.** `_uma_vez` grava uma linha
    por AÇÃO; uma rodada em que nenhuma regra teve o que fazer não gravava
    linha nenhuma, e aí "rodou e não havia nada" e "não rodou" ficam idênticos
    no banco — o silêncio que a regra 6 da casa proíbe, e o modo de falha que
    `execucao.py` existe para vigiar. Na segunda-feira o prazo já correu dois
    dias e ninguém soube.

    `execucao.registrar` grava OK com a contagem, SEM_ACAO quando a rodada foi
    vazia e ERRO com a mensagem se estourar (e deixa a exceção subir). É o
    `resultado` dessa linha que distingue os três casos.
    """
    import execucao                        # tardio: execucao importa banco, e só
    garantir(db)
    feitos = []
    if seco:                               # modo seco não escreve, nem o rastro
        for codigo, passo in PASSOS:
            if ativa(db, codigo):
                passo(db, seco, feitos)
        return feitos
    with execucao.registrar("AUTOMACAO_RODADA", db=db) as e:
        ligadas = []
        for codigo, passo in PASSOS:
            if not ativa(db, codigo):
                continue
            ligadas.append(codigo)
            passo(db, seco, feitos)
        db.commit()
        e.itens = len(feitos)
        e.detalhe = (f"{len(ligadas)} regra(s) ligada(s): {', '.join(ligadas) or 'nenhuma'}"
                     if ligadas else "nenhuma regra ligada")
    return feitos


if __name__ == "__main__":
    seco = "--seco" in sys.argv
    db = banco.conectar()
    feitos = rodar(db, seco=seco)
    if not feitos:
        print("nada a fazer" + (" (modo seco)" if seco else ""))
    for regra, chave in feitos:
        print(f"{regra:26} {chave}")
    db.close()
