#!/usr/bin/env python3
"""Motor de governança: quais transições estão abertas, e o que cada uma exige.

Vem do `fluxo.py` do Prev, reescrito para as colunas DESTE esquema. A divisão
de trabalho é a mesma:

  · o BANCO recusa transição fora do mapa (`gov_transicao`, em governanca.sql)
    e recusa prazo mal fechado e ação prescrita. Isso vale para qualquer
    caminho — sistema, script ou mão humana no psql.
  · aqui ficam os GATES: as condições de negócio que precisam estar
    satisfeitas antes de avançar. A tela nunca oferece um botão que o gate
    reprovaria sem dizer por quê, e nunca esconde uma saída sem explicar.

O contrato com o esquema está escrito em governanca.sql, na seção "SÓ POSTGRES
DAQUI PARA BAIXO". Cada gate abaixo lê exatamente as colunas de lá.

**O que se resolve na própria janela.** Alguns gates não olham o banco: olham
o que a pessoa está digitando naquele momento — o motivo, o número CNJ, o novo
vencimento, o protocolo. Travar o botão por causa de um campo que está logo
ali em cima, esperando ser preenchido, é o tipo de tela que ensina a pessoa a
desconfiar do sistema. Esses gates viram CAMPO na janela (`campos_na_janela`),
e o veredito só é cobrado no POST.
"""
import re

FLUXO_DE = {
    "clientes":   ("CLIENTE",   "status"),
    "processos":  ("PROCESSO",  "fase"),
    "audiencias": ("AUDIENCIA", "situacao"),
    "prazos":     ("PRAZO",     "situacao"),
    "incidentes": ("INCIDENTE", "situacao"),
}

# O mesmo vocabulário de `usuarios.papel` e de `fluxo_transicoes.papel`.
HIERARQUIA = {"DIRECAO": 3, "GESTOR": 2, "ADVOGADO": 1}

# ---------------------------------------------------------------------------
# Os gates que se resolvem NA JANELA da transição: nome do campo, rótulo e
# tipo do <input>. O que estiver aqui não trava o botão — o formulário pede.
CAMPOS_NA_JANELA = {
    "motivo":               [("motivo", "O que aconteceu", "text", None)],
    "numero_cnj":           [("numero_cnj", "Número do processo (CNJ, 20 dígitos)", "text", None)],
    "novo_vencimento":      [("novo_vencimento", "Novo vencimento (recontado em dias úteis)", "date", None)],
    "protocolo_registrado": [("protocolo", "Número do protocolo no PJe", "text", None),
                             ("cumprido_em", "Data do protocolo", "date", None)],
    "numero_cumprse":       [("numero_cumprse", "Número do cumprimento provisório (CumPrSe)", "text", None)],
    "transito_registrado":  [("transito_em", "Data do trânsito em julgado", "date", None)],
    "notificacao_enviada":  [("notificacao_enviada_em", "Data de envio da notificação", "date", None)],
    "resultado":            [("resultado_final", "Resultado final do processo", "select",
                              ["PROCEDENTE", "PARCIALMENTE_PROCEDENTE", "IMPROCEDENTE",
                               "ACORDO_CUMPRIDO", "EXECUCAO_SATISFEITA", "ARQUIVADO",
                               "ARQUIVADO_PROVISORIO", "ARQUIVADO_AUSENCIA",
                               "EXTINTA_SEM_RESOLUCAO", "DESISTENCIA", "SEM_RECEBIMENTO",
                               "REDISTRIBUIDO", "OUTRO"])],
    "resultado_audiencia":  [("resultado", "O que aconteceu na audiência", "select",
                              ["ACORDO", "DEFESA_JUNTADA", "INSTRUCAO_ENCERRADA",
                               "SENTENCA_DESIGNADA", "ADIADA", "SEM_ACORDO", "OUTRO"])],
}

# Onde cada campo da janela é gravado: (tabela, coluna). A tabela é a própria
# entidade governada — nenhum gate escreve em tabela de outra entidade.
GRAVA = {
    "numero_cumprse":         ("processos",  "numero_cumprse"),
    "transito_em":            ("processos",  "transito_em"),
    "resultado_final":        ("processos",  "resultado_final"),
    "resultado":              ("audiencias", "resultado"),
    "protocolo":              ("prazos",     "protocolo"),
    "cumprido_em":            ("prazos",     "cumprido_em"),
    "novo_vencimento":        ("prazos",     "vencimento"),
    "notificacao_enviada_em": ("incidentes", "notificacao_enviada_em"),
}

# Onde o MOTIVO da transição fica gravado, em cada entidade — além do
# histórico. Não é redundância: `gov_prazo_regras` RECUSA um prazo PERDIDO sem
# `prazos.motivo`, e o gatilho não lê o histórico. Sem isto, registrar prazo
# perdido dava erro do banco na cara de quem clicou — no pior dia do escritório.
MOTIVO_COLUNA = {
    "prazos":     "motivo",
    "incidentes": "motivo",
    "clientes":   "motivo",
    "audiencias": "motivo_texto",   # `audiencias.motivo` é lista fechada
}

DOC_NOME = {"CNH_RG": "RG ou CNH", "CTPS": "CTPS", "TRCT": "TRCT",
            "DOCS_MEDICOS": "documentos médicos", "PROVAS": "provas",
            "FGTS": "extrato do FGTS", "HOLERITES": "holerites", "PIS": "PIS",
            "OUTRO": "outro documento"}


def _um(db, sql, args=()):
    r = db.execute(sql, args).fetchone()
    return r[0] if r else None


def _tem(db, sql, args=()):
    return bool(_um(db, sql, args))


def _preenchido(v):
    return bool(v is not None and str(v).strip())


# ------------------------------------------------------------------ gates
def documentos_faltando(db, cliente_id):
    """Os documentos obrigatórios que ainda não voltaram. Lista de nomes.

    Lê a visão `documentos_pendentes`, que é `pendencias` filtrada por
    tipo='DOCUMENTO' — a resposta 7 do Lucas: pendência é uma tabela só, com
    tipo, e só a de documento trava etapa.
    """
    linhas = db.execute("""SELECT tipo FROM documentos_pendentes
                           WHERE cliente_id=? AND obrigatorio = true
                             AND recebido_em IS NULL AND dispensado_motivo IS NULL
                           ORDER BY tipo""", (cliente_id,)).fetchall()
    return [DOC_NOME.get(l[0], l[0] or "documento sem tipo") for l in linhas]


def pendencias_abertas(db, cliente_id=None, processo_id=None):
    """Tudo o que falta, de qualquer tipo, com há quantos dias espera resposta.

    "Espera resposta há N dias" conta de `solicitado_em` — pedido sem
    recebimento confirmado continua pendente (resposta 7, complemento).
    """
    onde = "cliente_id=?" if cliente_id else "processo_id=?"
    return db.execute(f"""SELECT p.*, pe.nome responsavel,
                CASE WHEN p.solicitado_em IS NULL THEN NULL
                     ELSE cast(julianday('now') - julianday(p.solicitado_em) as int)
                END espera_dias
             FROM pendencias p LEFT JOIN pessoas pe ON pe.id = p.responsavel_id
             WHERE {onde} AND p.recebido_em IS NULL AND p.dispensado_motivo IS NULL
             ORDER BY (p.tipo <> 'DOCUMENTO'), p.solicitado_em""",
                      (cliente_id or processo_id,)).fetchall()


def _gate(db, exige, entidade, rid, dados, para=None):
    """Devolve (liberado, explicação). `dados` é o que veio do formulário."""
    d = dados or {}

    # -------- os que se resolvem na janela
    if exige == "motivo":
        return _preenchido(d.get("motivo")), "escreva o motivo da mudança"

    if exige == "numero_cnj":
        digitos = re.sub(r"\D", "", str(d.get("numero_cnj") or ""))
        return (len(digitos) == 20,
                "informe o número CNJ com 20 dígitos — é ele que faz o processo nascer")

    if exige == "novo_vencimento":
        return _preenchido(d.get("novo_vencimento")), "informe o novo vencimento"

    # -------- CLIENTE
    if exige == "contrato_assinado":
        v = _um(db, "SELECT data_assinatura_contrato FROM clientes WHERE id=?", (rid,))
        return _preenchido(v), ("falta o contrato de honorários assinado, com data. "
                                "Sem ele o escritório não representa ninguém")

    if exige == "documentos_obrigatorios":
        faltam = documentos_faltando(db, rid)
        if not faltam:
            return True, None
        return (False, "falta: " + ", ".join(faltam[:4]) +
                (f" e mais {len(faltam) - 4}" if len(faltam) > 4 else ""))

    if exige == "entrevista_registrada":
        r = db.execute("SELECT entrevista_em, entrevista_resumo FROM clientes WHERE id=?",
                       (rid,)).fetchone()
        ok = bool(r and _preenchido(r["entrevista_em"]) and _preenchido(r["entrevista_resumo"]))
        return ok, "registre a entrevista: data, entrevistador e resumo"

    if exige == "minuta_anexada":
        return (_tem(db, """SELECT 1 FROM peticoes
                            WHERE cliente_id=? AND tipo='INICIAL' AND arquivo_id IS NOT NULL
                              AND status <> 'DESCARTADA' LIMIT 1""", (rid,)),
                "anexe a minuta da inicial na ficha — não se aprova o que não está escrito")

    if exige == "prescricao_viva":
        # O mesmo cálculo do gatilho `gov_prescricao_bienal`. Repetido aqui
        # de propósito: o banco recusa o INSERT, e a tela precisa dizer isso
        # ANTES, senão o operador só descobre com a transação já recusada.
        r = db.execute("""SELECT data_demissao, contrato_vivo, dispensa_prescricao_motivo,
                                 (data_demissao IS NOT NULL
                                  AND NOT COALESCE(contrato_vivo,false)
                                  AND (data_demissao::date + INTERVAL '2 years')
                                      < (now() AT TIME ZONE 'America/Sao_Paulo')::date) venceu
                          FROM clientes WHERE id=?""", (rid,)).fetchone()
        if not r or not r["venceu"]:
            return True, None
        if _preenchido(r["dispensa_prescricao_motivo"]):
            return True, None
        return (False, "a prescrição bienal já se consumou (CF art. 7º XXIX; CLT art. 11). "
                       "Registre a dispensa justificada na ficha antes de distribuir")

    # -------- PROCESSO
    if exige == "sentenca_registrada":
        return (_tem(db, """SELECT 1 FROM decisoes
                            WHERE processo_id=? AND tipo IN ('SENTENCA','ACORDAO')
                              AND resultado_objetivo IS NOT NULL AND data IS NOT NULL
                            LIMIT 1""", (rid,)),
                "registre a decisão (resultado objetivo, data e nota) antes de mudar de fase — "
                "é isso que alimenta o mapa de onde estamos perdendo")

    if exige == "transito_registrado":
        if _preenchido(d.get("transito_em")):
            return True, None
        return (_preenchido(_um(db, "SELECT transito_em FROM processos WHERE id=?", (rid,))),
                "informe a data do trânsito em julgado")

    if exige == "acordo_registrado":
        return (_tem(db, """SELECT 1 FROM acordos
                            WHERE processo_id=? AND valor_centavos IS NOT NULL
                              AND homologado_em IS NOT NULL LIMIT 1""", (rid,)),
                "registre o acordo: valor, parcelas e a data da homologação")

    if exige == "numero_cumprse":
        if _preenchido(d.get("numero_cumprse")):
            return True, None
        return (_preenchido(_um(db, "SELECT numero_cumprse FROM processos WHERE id=?", (rid,))),
                "informe o número do cumprimento provisório de sentença (CumPrSe)")

    if exige == "resultado":
        if _preenchido(d.get("resultado_final")):
            return True, None
        return (_preenchido(_um(db, "SELECT resultado_final FROM processos WHERE id=?", (rid,))),
                "informe o resultado final do processo antes de encerrar")

    if exige == "valor_recebido":
        if entidade == "incidentes":
            return (_um(db, "SELECT valor_recebido_centavos FROM incidentes WHERE id=?",
                        (rid,)) is not None,
                    "registre o valor recebido pelo trabalho feito")
        return (_tem(db, """SELECT 1 FROM recebimentos
                            WHERE processo_id=? AND valor_centavos > 0 LIMIT 1""", (rid,)),
                "registre o valor efetivamente recebido, a data e o comprovante")

    if exige == "parcelas_quitadas":
        cadastradas = _um(db, """SELECT COUNT(*) FROM acordo_parcelas ap
                                 JOIN acordos a ON a.id = ap.acordo_id
                                 WHERE a.processo_id=?""", (rid,)) or 0
        if not cadastradas:
            return (False, "as parcelas do acordo ainda não estão cadastradas. A origem não "
                           "guardava o vencimento de cada uma — cadastre-as na ficha")
        abertas = _um(db, """SELECT COUNT(*) FROM acordo_parcelas ap
                             JOIN acordos a ON a.id = ap.acordo_id
                             WHERE a.processo_id=? AND ap.pago_em IS NULL""", (rid,)) or 0
        return (abertas == 0,
                f"há {abertas} parcela(s) sem pagamento registrado. Registre cada uma, "
                f"ou mude para quebra de acordo")

    if exige == "repasse_registrado":
        # Resposta 26: o repasse é DO FINANCEIRO. Aqui basta a referência —
        # houve, quando, quanto (ou por que não havia) — e a marca de que foi
        # entregue ao financeiro.
        r = db.execute("""SELECT 1 FROM repasses
                          WHERE processo_id=?
                            AND (valor_centavos IS NOT NULL OR sem_valor_motivo IS NOT NULL)
                            AND entregue_ao_financeiro_em IS NOT NULL LIMIT 1""",
                       (rid,)).fetchone()
        return (bool(r), "registre o repasse ao cliente (valor, data, comprovante) — ou marque "
                         "que não havia valor a repassar, com motivo — e a entrega ao financeiro")

    if exige == "retorna_fase_anterior":
        anterior = _um(db, "SELECT fase_anterior FROM processos WHERE id=?", (rid,))
        if not anterior:
            return (False, "não há registro da fase em que o processo estava antes de sobrestar. "
                           "Informe-a na ficha antes de retomar")
        return (anterior == para,
                f"sobrestado só volta para a fase em que estava: {anterior.replace('_', ' ').lower()}")

    # -------- AUDIÊNCIA
    if exige == "resultado_audiencia":
        if _preenchido(d.get("resultado")):
            return True, None
        return (_preenchido(_um(db, "SELECT resultado FROM audiencias WHERE id=?", (rid,))),
                "registre o que aconteceu: acordo, defesa juntada, instrução encerrada, "
                "sentença designada")

    if exige == "nova_audiencia":
        return (_tem(db, "SELECT 1 FROM audiencias WHERE redesignada_de=? LIMIT 1", (rid,)),
                "cadastre primeiro a nova audiência com a data redesignada, ligada a esta")

    # -------- PRAZO
    if exige == "protocolo_registrado":
        protocolo = d.get("protocolo") or _um(db, "SELECT protocolo FROM prazos WHERE id=?", (rid,))
        quando = d.get("cumprido_em") or _um(db, "SELECT cumprido_em FROM prazos WHERE id=?", (rid,))
        return (_preenchido(protocolo) and _preenchido(quando),
                "informe a data do protocolo e o número do protocolo no PJe")

    # -------- INCIDENTE
    if exige == "notificacao_enviada":
        if _preenchido(d.get("notificacao_enviada_em")):
            return True, None
        return (_preenchido(_um(db, "SELECT notificacao_enviada_em FROM incidentes WHERE id=?",
                                (rid,))),
                "registre a data de envio da notificação extrajudicial")

    if exige == "peticao_reserva":
        return (_um(db, "SELECT peticao_reserva_id FROM incidentes WHERE id=?", (rid,)) is not None,
                "anexe a petição de reserva de honorários protocolada nos autos "
                "(EOAB art. 22 §4º)")

    # gate desconhecido não trava em silêncio: diz que não sabe conferir
    return False, f"o sistema não sabe conferir o pré-requisito '{exige}'"


def caminho(db, exige, entidade, rid):
    """ONDE se resolve o impedimento.

    Dizer o que falta e não dizer onde se faz é metade da informação.
    """
    def cliente_do_processo():
        return _um(db, "SELECT cliente_id FROM processos WHERE id=?", (rid,))

    if exige == "contrato_assinado":
        return dict(texto="Registrar o contrato assinado nesta mesma ficha",
                    link=None,
                    extra="O que destrava é o documento do ZapSign: a assinatura é a métrica "
                          "que o escritório mais usa.")
    if exige == "documentos_obrigatorios":
        return dict(texto="A lista do que falta está nesta ficha, em Pendências",
                    link=None,
                    extra="Só a pendência do tipo DOCUMENTO trava a etapa; as outras viram "
                          "tarefa com dono.")
    if exige == "entrevista_registrada":
        return dict(texto="Registrar a entrevista nesta ficha", link=None,
                    extra="Data, entrevistador e resumo — é o que a inicial vai usar.")
    if exige == "minuta_anexada":
        return dict(texto="Anexar a minuta da inicial nesta ficha", link=None, extra=None)
    if exige == "prescricao_viva":
        return dict(texto="Registrar a dispensa justificada na ficha do cliente",
                    link=None,
                    extra="Contrato ainda vivo, causa interruptiva ou decisão de assumir o "
                          "risco. O banco recusa o processo sem isso.")
    if exige == "sentenca_registrada":
        return dict(texto="Registrar a decisão em Decisões, nesta ficha", link=None,
                    extra="Resultado objetivo, data e a nota — que é avaliação nossa, "
                          "coisa diferente do que a decisão diz.")
    if exige == "acordo_registrado":
        return dict(texto="Registrar o acordo em Acordo, nesta ficha", link=None, extra=None)
    if exige == "parcelas_quitadas":
        return dict(texto="Cadastrar e baixar as parcelas em Acordo, nesta ficha", link=None,
                    extra="Parcela atrasada é quebra: multa da cláusula penal e execução do saldo.")
    if exige == "valor_recebido":
        return dict(texto="Registrar o recebimento em Dinheiro, nesta ficha", link=None,
                    extra=None)
    if exige == "repasse_registrado":
        return dict(texto="Registrar o repasse em Dinheiro, nesta ficha", link=None,
                    extra="O lançamento é do financeiro; aqui fica só a referência — houve, "
                          "quando, quanto — e a marca de entrega.")
    if exige == "nova_audiencia":
        pid = _um(db, "SELECT processo_id FROM audiencias WHERE id=?", (rid,))
        return dict(texto="Cadastrar a nova audiência na ficha do processo",
                    link=f"/processos/{pid}" if pid else None, extra=None)
    if exige == "peticao_reserva":
        return dict(texto="Anexar a petição de reserva no incidente", link=None, extra=None)
    if exige == "retorna_fase_anterior":
        return dict(texto="O histórico desta ficha diz de onde o processo veio", link=None,
                    extra=None)
    return None                    # o resto se resolve no próprio formulário


def _e_volta(db, fluxo, de, para):
    """A transição leva o caso para trás no mapa?"""
    r = db.execute("""SELECT (SELECT ordem FROM fluxo_etapas e2 JOIN fluxos f2 ON f2.id=e2.fluxo_id
                              WHERE f2.codigo=? AND e2.codigo=?) atual,
                             (SELECT ordem FROM fluxo_etapas e3 JOIN fluxos f3 ON f3.id=e3.fluxo_id
                              WHERE f3.codigo=? AND e3.codigo=?) destino""",
                   (fluxo, de, fluxo, para)).fetchone()
    return bool(r and r[0] is not None and r[1] is not None and r[1] < r[0])


def etapa_atual(db, entidade, rid):
    fluxo, coluna = FLUXO_DE[entidade]
    r = db.execute(f"SELECT {coluna} FROM {entidade} WHERE id=?", (rid,)).fetchone()
    return r[0] if r else None


def trilha(db, entidade):
    """As etapas do fluxo desta entidade, em ordem, com o texto do operador."""
    fluxo, _ = FLUXO_DE[entidade]
    return db.execute("""SELECT e.codigo, e.nome, e.ordem, e.tipo, e.grupo, e.sla_dias,
                                e.texto_operador
                         FROM fluxo_etapas e JOIN fluxos f ON f.id = e.fluxo_id
                         WHERE f.codigo=? ORDER BY e.ordem""", (fluxo,)).fetchall()


def percorridas(db, entidade, rid):
    return {r[0] for r in db.execute(
        """SELECT DISTINCT para FROM historico_etapas
           WHERE entidade=? AND entidade_id=?""", (entidade, rid))}


def transicoes(db, entidade, rid, papel="ADVOGADO", dados=None):
    """Todas as saídas possíveis da etapa atual, já com veredito de cada gate."""
    fluxo, coluna = FLUXO_DE[entidade]
    atual = etapa_atual(db, entidade, rid)
    if not atual:
        return []
    saida = []
    for t in db.execute("""SELECT t.para, t.acao, t.papel, t.exige, fe.nome, t.texto_bloqueio
                           FROM fluxo_transicoes t
                           JOIN fluxos f ON f.id = t.fluxo_id
                           LEFT JOIN fluxo_etapas fe
                                  ON fe.fluxo_id = t.fluxo_id AND fe.codigo = t.para
                           WHERE f.codigo=? AND t.de=? ORDER BY fe.ordem""",
                        (fluxo, atual)).fetchall():
        para, acao, papel_exigido, exige, nome, texto_bloqueio = (
            t["para"], t["acao"], t["papel"], t["exige"], t["nome"], t["texto_bloqueio"])
        pode_papel = (not papel_exigido) or \
            HIERARQUIA.get(papel, 0) >= HIERARQUIA.get(papel_exigido, 9)

        falhas, caminhos, quais, campos = [], [], [], []
        for cada in [e.strip() for e in (exige or "").split(",") if e.strip()]:
            ok1, porque1 = _gate(db, cada, entidade, rid, dados, para)
            if cada in CAMPOS_NA_JANELA:
                for c in CAMPOS_NA_JANELA[cada]:
                    if c[0] not in [x["nome"] for x in campos]:
                        campos.append(dict(nome=c[0], rotulo=c[1], tipo=c[2], opcoes=c[3]))
            if not ok1:
                falhas.append(porque1)
                quais.append(cada)
                c = caminho(db, cada, entidade, rid)
                if c:
                    caminhos.append(c)

        ok = not falhas
        porque = "; e ".join(f for f in falhas if f) if falhas else None
        # o que falta é só campo desta janela: o botão não trava, o formulário pede
        so_falta_janela = bool(quais) and all(q in CAMPOS_NA_JANELA for q in quais)

        saida.append({
            "para": para, "nome_destino": nome or para, "acao": acao,
            "papel_exigido": papel_exigido, "pode_papel": pode_papel,
            "exige": exige, "gate_ok": ok, "impedimento": None if ok else porque,
            # `impedimento` é a razão técnica; `texto_bloqueio` é a humana, e
            # vem de `fluxo_transicoes` — dado, não texto no template
            "texto_bloqueio": texto_bloqueio if not ok else None,
            "liberado": pode_papel and ok,
            "caminhos": caminhos,
            "campos": campos,
            "so_falta_motivo": so_falta_janela,      # o nome que a janela do Prev usa
            "volta": _e_volta(db, fluxo, atual, para),
        })
    return saida


def mover(db, entidade, rid, para, pessoa_id=None, papel="ADVOGADO", dados=None):
    """Executa a transição. Levanta ValueError com a razão exata se não puder.

    A ordem é: GRAVA o que a janela trouxe (dentro do savepoint de cada
    escrita), depois muda a etapa. O contrário faria a etapa andar e o campo
    ficar para trás quando o gatilho recusasse — e é o gatilho que manda.
    """
    fluxo, coluna = FLUXO_DE[entidade]
    d = dados or {}
    op = [t for t in transicoes(db, entidade, rid, papel, d) if t["para"] == para]
    if not op:
        raise ValueError(f"não existe caminho da etapa atual para {para}")
    t = op[0]
    if not t["pode_papel"]:
        raise ValueError(f"esta ação exige papel {t['papel_exigido']}")
    if not t["gate_ok"]:
        raise ValueError(t["impedimento"])

    for campo in t["campos"]:
        alvo = GRAVA.get(campo["nome"])
        valor = (d.get(campo["nome"]) or "").strip() if d.get(campo["nome"]) is not None else None
        if alvo and alvo[0] == entidade and valor:
            db.execute(f"UPDATE {entidade} SET {alvo[1]}=? WHERE id=?", (valor, rid))

    motivo = (d.get("motivo") or "").strip() or None
    coluna_motivo = MOTIVO_COLUNA.get(entidade)
    if motivo and coluna_motivo:
        db.execute(f"UPDATE {entidade} SET {coluna_motivo}=? WHERE id=?", (motivo, rid))

    # SOBRESTADO guarda de onde veio, senão a volta não tem para onde ir
    if entidade == "processos" and para == "SOBRESTADO":
        db.execute("UPDATE processos SET fase_anterior=fase, sobrestado_motivo=? WHERE id=?",
                   (motivo, rid))

    db.execute(f"UPDATE {entidade} SET {coluna}=? WHERE id=?", (para, rid))
    # o gatilho `gov_historico` já gravou a linha; aqui entra quem e por quê
    db.execute("""UPDATE historico_etapas SET pessoa_id=?, motivo=? WHERE id=(
                    SELECT MAX(id) FROM historico_etapas
                     WHERE entidade=? AND entidade_id=?)""",
               (pessoa_id, motivo, entidade, rid))
    db.commit()
    return True
