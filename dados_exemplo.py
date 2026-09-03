#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Uma amostra SINTÉTICA no formato exato do Airtable, com os casos difíceis.

Existe porque a prova da migração não pode depender de dado de cliente: nome,
CPF e número de processo aqui são inventados, e nenhum deles entra no
repositório de verdade — `dados/` é ignorado pelo git.

O que a amostra tem de propósito, e que a base real também tem:

  · as 6 grafias de data do campo DEMISSAO, mais um telefone digitado no lugar
  · RESCISAO em texto livre, incluindo "NÃO SEI O CERTO AINDA"
  · STATUS EXECUÇÃO poluído: `SIM `, `Discutindo cálculos. `, `PESQUISA `
  · TURMA com um número de processo digitado como opção, e `11ª TURMA ` com espaço
  · TRT `85ª`, que não existe
  · SUCUMBENCIA % com `2500%`
  · um processo `EXECUÇÃO` sem CumPrSe e sem trânsito (não dá para dizer qual é)
  · um `INAPLICÁVEL`, que não vira processo
  · o mesmo número CNJ em dois registros da CÓPIA
  · um registro só na PROCESSUAL e um sem número nenhum
  · VARA e FASE divergindo entre a CÓPIA e a PROCESSUAL
  · um PÓS PROCESSUAL apontando para processo que não existe
  · AND. NECESSÁRIO com recado longo, e REVOGAÇÃO com recado

    ./.venv/bin/python dados_exemplo.py      # escreve dados/*.json
    ./.venv/bin/python migrar.py --recriar   # e a carga roda em cima dela
    ./.venv/bin/python conferir.py           # tem de dar TUDO CONFERE
"""
import json, os, random
random.seed(7)
D = "/home/user/trabggvlucas/dados"
os.makedirs(D, exist_ok=True)

def rid(p, i): return "rec%s%011d" % (p, i)
def salvar(nome, tid, regs):
    json.dump({"tabela": tid, "baixado_em": "2026-09-03 00:00:00",
               "amostra_sintetica": True, "registros": regs},
              open(os.path.join(D, nome + ".json"), "w"), ensure_ascii=False)
    print("%-24s %4d" % (nome, len(regs)))

# ---------------- FUNCIONARIOS
func = []
papeis = [["Advogado","Gestor"],["Captador"],["Entrevistador","Juridico"],["Advogado"],
          ["Responsável Inicial"],["TI"],["Documentação"],["Testemunhas"],["Publicação"],["Zelador"]]
for i, ps in enumerate(papeis, 1):
    func.append({"id": rid("FUN", i), "createdTime": "2026-05-01T10:00:00.000Z",
                 "fields": {"NOME": "Colaborador %d" % i, "FUNCOES": ps,
                            "STATUS": "ATIVO" if i % 3 else "INATIVO",
                            "ntfy_topic": "topico-%d" % i, "ntfy_ativo": "ATIVO"}})
salvar("funcionarios", "tblisgqzJvF0EUFr1", func)

# ---------------- EMPRESAS
emp = []
sits = ["ATIVA", "EM RECUPERACAO", None, "ATIVA", "INATIVA"]
for i in range(1, 6):
    f = {"EMPRESA": "Reclamada %d Ltda" % i, "SEGMENTO": "Transporte" if i == 1 else None,
         "GGV_RECORD_KEY": "K%016d" % i}
    if sits[i-1]: f["STATUS EMPRESA"] = sits[i-1]
    if i == 1: f["HIST. PAGAMENTO"] = "BOA"; f["BENS IDENTIFICADOS"] = "SIM"
    emp.append({"id": rid("EMP", i), "createdTime": "2026-05-01T10:00:00.000Z",
                "fields": {k: v for k, v in f.items() if v is not None}})
salvar("empresas", "tblkfWQhjp2F1dK0y", emp)

# ---------------- FRAGILIDADES
frag = [{"id": rid("FRG", 1), "createdTime": "2026-08-24T10:00:00.000Z", "fields": {
    "ACHADO": "Cartão de ponto britânico", "EMPRESA": [rid("EMP", 1)],
    "EIXO": "Controle de ponto", "FORCA": "Prova documental própria da ré",
    "STATUS": "Inédita — nunca enfrentada", "DESCRICAO": "Marcações idênticas.",
    "FUNDAMENTO": "Súmula 338, III, TST", "PROVA": "Cartões juntados pela ré",
    "COMO EXPLORAR": "Requerer os cartões de todo o período",
    "PERIODO": "2019-2023", "VALOR ESTIMADO": 12500.5, "ATUALIZADO EM": "2026-08-25",
    "DOSSIE": [{"id": "att00000000000001", "filename": "dossie.pdf", "type": "application/pdf",
                "size": 12345, "url": "https://exemplo/att1"}]}}]
salvar("fragilidades", "tblmxkxgQEbc0KwvV", frag)

# ---------------- PRE PROCESSUAL (os casos do funil)
casos = [
    # etapa,                status peticao,          status entrevista,   status doc,    rescisao,               demissao
    ("DOCUMENTAÇÃO",        None,                    "PENDENTE",          "PENDENTE",    "DEMISSÃO SEM JUSTA CAUSA", "3/1/2024"),
    ("ENTREVISTA",          None,                    "ENTREVISTA AGENDADA","COMPLETA",   "RESCISÃO INDIRETA",     "12/05/2023"),
    ("PETIÇÃO INICIAL",     "AGUARDANDO APROVAÇÃO",  "ENTREVISTA-OK",     "COMPLETA",    "PEDIDO DE DEMISSÃO",    "05-11-2022"),
    ("PETIÇÃO INICIAL",     "DISTRIBUIDA",           "ENTREVISTA-OK",     "COMPLETA",    "JUSTA CAUSA",           "2021-07-30"),
    ("CONCLUÍDO",           "APROVADA",              "ENTREVISTA-OK",     "COMPLETA",    "SEM JUSTA CAUSA",       "9/9/2020."),
    ("CANCELAMENTO",        "DESISTENCIA",           "DESISTÊNCIA ",      "DESISTÊNCIA", "NÃO SEI O CERTO AINDA", "11999998888"),
    ("ENTREVISTA",          None,                    "STAND-BY",          "TRATAMENTO",  "AINDA TRABALHA",        None),
    ("ENTREVISTA",          None,                    "SEM RESPOSTA",      "AGUARDANDO",  "RECISÃO INDIRETA",      "1/2/2025"),
    ("PETIÇÃO INICIAL",     "PRESCRITO",             "PRIMEIRO CONTATO",  "PARCIAL",     "acordo 484-A",          "3/3/2019"),
    ("CONCLUÍDO",           "DISTRIBUIDA",           "ENTREVISTA-OK",     "COMPLETA",    "DEMISSÃO SEM JUSTA CAUSA", "20/12/2023"),
]
fontes = ["Indicação", "PROJETO PUXADA", "PXD", "INDICAÇAO", "PROJETO JUXADA", None, "Site", None, None, "Instagram"]
pends = [["TRCT","CTPS"], ["TRCT","HOLERITE","OK"], ["CNH/RG"], [], ["TRCT","FGTS","HOLERITES"],
         [], ["PROVAS"], [], ["DOCUMENTAÇÃO OK"], ["TRCT"]]
pre = []
for i, (etapa, pet, ent, doc, resc, dem) in enumerate(casos, 1):
    f = {"NOME": "Reclamante %02d" % i, "TELEFONE": "+5511900000%02d" % i,
         "CPF": "111444777%02d" % (35 + i), "NASCIMENTO": "1985-0%d-1%d" % (i % 9 + 1, i % 9),
         "EMPRESA": [rid("EMP", (i % 5) + 1)], "FUNCAO": "Motorista",
         "DATA DE ASSINATURA": "2026-0%d-1%d" % (i % 8 + 1, i % 9),
         "CAPTADOR": [rid("FUN", 2)], "ETAPA PRE PROCESSUAL": etapa,
         "STATUS ENTREVISTA": ent, "STATUS DOCUMENTAÇÃO": doc, "RESCISAO": resc,
         "DRIVE": "https://drive/exemplo/%d" % i, "Created": "2026-06-0%dT09:00:00.000Z" % (i % 9 + 1),
         "PASSAR DE FASE?": bool(i % 2)}
    if pet: f["STATUS PETICAO INICIAL"] = pet
    if dem: f["DEMISSAO"] = dem
    if fontes[i-1]: f["FONTE"] = fontes[i-1]
    if pends[i-1]: f["PENDENCIAS"] = pends[i-1]
    if i in (2, 3, 5, 10):
        f["ENTREVISTADOR"] = [rid("FUN", 3)]; f["DATA ENTREVISTA"] = "2026-07-0%dT14:00:00.000Z" % i
        f["RESUMO ENTREVISTA"] = "Relato da jornada."
        f["RESPONSAVEL INICIAL"] = [rid("FUN", 5)]
    if i == 6: f["AVISOS"] = "🔴 20 dias sem distribuir"
    if i in (1, 4): f["status_disparo"] = "enviada"; f["tipo_disparo"] = "compromisso"; \
        f["data_solicitacao_disparo"] = "2026-07-01T10:00:00Z"
    if i == 7: f["status_disparo"] = "aniversario_erro"; f["erro_disparo"] = "webhook 500"
    if i == 3: f["STATUS_NOTIFICACAO_RI"] = "RI 15D ENVIADO"
    if i == 9: f["STATUS_NOTIFICACAO_PRESCRICAO"] = "VENCIDO NOTIFICADO"
    if i in (4, 10): f["PROCESSUAL"] = [rid("PRO", i)]
    pre.append({"id": rid("PRE", i), "createdTime": "2026-06-01T09:00:00.000Z", "fields": f})
salvar("pre_processual", "tblucQ0Cz5MEQEdCR", pre)

CNJ = ["100010%02d20265020001" % i for i in range(1, 15)]

# ---------------- PROCESSUAL (o que está vivo)
proc = []
def P(i, extra, cnj=None):
    f = {"NOME": "Reclamante %02d" % i, "EMPRESA": [rid("EMP", (i % 5) + 1)],
         "DISTRIBUIÇAO": "2026-0%d-05" % (i % 8 + 1), "VALOR": 45000.0 + i * 100,
         "COMPLEXIDADE": "C", "VARA": "%dª VARA DO TRABALHO" % (i % 9 + 1), "TRT": "2ª",
         "TELEFONE": "11900000%03d" % i, "CAPTADOR": [rid("FUN", 2)]}
    if cnj: f["Nº PROCESSO"] = cnj
    f.update(extra)
    return {"id": rid("PRO", i), "createdTime": "2026-06-01T09:00:00.000Z", "fields": f}

proc.append(P(4, {"FASE PROCESSUAL": "CONHECIMENTO", "STATUS DO PROCESSO": "AGUARDANDO AUDIÊNCIA",
                  "PRE PROCESSUAL": [rid("PRE", 4)], "DATA AUDIENCIA": "2026-10-01T14:00:00.000Z",
                  "AUDIENCIA": "UNA", "ADVOGADO": [rid("FUN", 1)],
                  "CLASSIFICACAO": "AT - ORDINÁRIO", "TURMA": "11ª TURMA "}, CNJ[0]))
proc.append(P(10, {"FASE PROCESSUAL": "EXECUÇÃO", "STATUS DO PROCESSO": "EXECUCAO",
                   "PRE PROCESSUAL": [rid("PRE", 10)], "Nº  CumPrSe": "CPS-0001",
                   "STATUS EXECUÇÃO": "SIM ", "DATA REVOG": "2026-04-02",
                   "REVOGAÇÃO": "SIM ", "VALOR HOM": 31000.0,
                   "SUCUMB RECEBIDO": 900.0}, CNJ[1]))
proc.append(P(11, {"FASE PROCESSUAL": "RECURSAL", "STATUS RECURSAL": "TST",
                   "STATUS DO PROCESSO": "ROUBADO", "NOTIFICAÇÃO": "REDIGIDA",
                   "PROVIDENCIAS": "NOTIFICAR", "REVOGAÇÃO": "SIM ",
                   "DATA REVOG": "2026-03-10", "CLIENTE AVISADO?": True,
                   "TURMA": "10001012026502000%d" % 1}, CNJ[2]))
proc.append(P(12, {"FASE PROCESSUAL": "CONHECIMENTO", "AND. NECESSÁRIO": "PEDIR ANDAMENTO",
                   "STATUS EXECUÇÃO": "Discutindo cálculos. ",
                   "SUCUMBENCIA %": "2500%"}, CNJ[3]))
proc.append(P(13, {"FASE PROCESSUAL": "ACORDO", "STATUS ACORDO": "ACORDO EM ANDAMENTO",
                   "VALOR ACORDO": 20000.0, "PARCELAS": 6}, CNJ[12]))   # só na PROCESSUAL
proc.append(P(14, {"FASE PROCESSUAL": "CONHECIMENTO"}, None))            # sem número
salvar("processual", "tbl6rDaSPCQRbbzjq", proc)

# ---------------- CÓPIA (a base: o acervo inteiro)
copia = []
def C(i, extra, cnj):
    f = {"NOME": "Reclamante %02d" % i, "Nº PROCESSO": cnj, "EMPRESA": [rid("EMP", (i % 5) + 1)],
         "DISTRIBUIÇAO": "2026-0%d-05" % (i % 8 + 1), "VARA": "%dª VARA DO TRABALHO" % (i % 9 + 1),
         "TRT": "2ª", "VALOR": 45000.0 + i * 100, "COMPLEXIDADE": "C",
         "CPF": "111444777%02d" % (35 + i), "E-MAIL": "reclamante%02d@exemplo.test" % i,
         "CNPJ RECLAMADA": "12.345.678/0001-9%d RECLAMADA %d LTDA" % (i % 10, (i % 5) + 1),
         "NASCIMENTO": "1985-0%d-1%d" % (i % 9 + 1, i % 9), "ASSINATURA": "2026-01-1%d" % (i % 9),
         "TELEFONE": "11900000%03d" % i, "ULTIMA MOV": "2026-07-1%d - conclusos" % (i % 9)}
    f.update(extra)
    return {"id": rid("COP", i), "createdTime": "2026-08-01T09:00:00.000Z", "fields": f}

copia.append(C(4, {"FASE PROCESSUAL": "CONHECIMENTO", "STATUS DO PROCESSO": "AGUARDANDO AUDIÊNCIA",
                   "DATA AUDIENCIA": "2026-10-01T14:00:00.000Z", "AUDIENCIA": "UNA-RS/VIDEO",
                   "CLASSIFICACAO": "AT - SUMARÍSSIMO", "TURMA": "11ª TURMA",
                   "VARA": "3ª VARA DO TRABALHO"}, CNJ[0]))            # VARA diverge da PROCESSUAL
copia.append(C(10, {"FASE PROCESSUAL": "ENCERRADO", "STATUS DO PROCESSO": "ARQUIVADO",
                    "STATUS EXECUÇÃO": "AGUARDANDO ALVARÁ", "ENCERRAMENTO": "2026-08-01",
                    "DECISAO SENTENCA": "PARCIALMENTE PROCEDENTE", "SENTENCA": "MÉDIA",
                    "DATA SENTENCA": "2026-02-10", "MAGISTRADO": "Juiz Fictício",
                    "CALCULO RCTE": 30000.0, "SUCUMB RCTE": 3000.0,
                    "HONOR TOTAL CALCULO RCTE": 9000.0, "VALOR HOM": 28000.0,
                    "TOTAL RECEBIDO": 28000.0, "HONOR TOTAL": 8400.0,
                    "STATUS DO CALCULO": "HOMOLOGADO"}, CNJ[1]))       # FASE diverge
copia.append(C(11, {"FASE PROCESSUAL": "RECURSAL", "STATUS DO PROCESSO": "ROUBADO",
                    "RESULTADO RECURSO": "PARCIALMENTE PROVIDO", "RESULTADO ACORDAO": "MÉDIO",
                    "DATA ACORDAO": "2026-05-20", "RELATOR": "Desembargador Fictício",
                    "TURMA": "9ª TURMA ", "CADEIRA": "CADEIRA 3", "TURMA TST": "5ª Turma",
                    "RELATOR TST": "Ministro Fictício", "ARQUIVO TST": "2026-06-01"}, CNJ[2]))
copia.append(C(12, {"FASE PROCESSUAL": "CONHECIMENTO", "STATUS CONHECIMENTO": "AUSÊNCIA",
                    "DATA AUDIENCIA": "2026-03-02T10:00:00.000Z", "AUDIENCIA": "INICIAL/VIDEO",
                    "STATUS EXECUÇÃO": "PESQUISA "}, CNJ[3]))
copia.append(C(20, {"FASE PROCESSUAL": "ENCERRADO", "STATUS DO PROCESSO": "ARQUIVADO",
                    "DECISAO SENTENCA": "IMPROCEDENTE", "SENTENCA": "RUIM",
                    "DATA SENTENCA": "2019-05-05", "ENCERRAMENTO": "2019-09-09",
                    "STATUS ACORDO": "ACORDO CUMPRIDO", "VALOR ACORDO": 15000.0,
                    "HONOR TOTAL ACORDO": 4500.0, "DATA DO ACORDO": "2019-08-01",
                    "PARCELAS": 3, "VALOR PARCELA": 5000.0}, CNJ[4]))   # passivo histórico
copia.append(C(21, {"FASE PROCESSUAL": "ENCERRADO", "STATUS DO PROCESSO": "RECEBIDO POR ELES",
                    "DECISAO SENTENCA": "EXTINTO S/ RESOLUCAO DO MERITO",
                    "ULTIMA DECISAO": "PROCEDENTE",
                    "DATA PERÍCIA MÉDICA": "2018-04-04T09:00:00.000Z",
                    "PERICIA MEDICA": True}, CNJ[5]))
copia.append(C(22, {"FASE PROCESSUAL": "INAPLICÁVEL ", "STATUS DO PROCESSO": "INAPLICÁVEL"}, CNJ[6]))
copia.append(C(23, {"FASE PROCESSUAL": "EXECUÇÃO DEFINITIVA", "STATUS EXECUÇÃO": "AGUARDANDO CÁLCULO",
                    "TRT": "85ª", "STATUS DO PROCESSO": "SOBRESTADO"}, CNJ[7]))
copia.append(C(24, {"FASE PROCESSUAL": "EXECUÇÃO", "STATUS EXECUÇÃO": "RECURSO EXECUÇÃO",
                    "STATUS DO PROCESSO": "TRÂNSITO EM JULGADO", "DATA SENTENCA": "2024-01-15",
                    "SUCUMB RECEBIDO": 1200.0, "TOTAL RECEBIDO": 50000.0}, CNJ[8]))
copia.append(C(25, {"FASE PROCESSUAL": "EXECUÇÃO"}, CNJ[9]))            # execução sem nenhum fato
copia.append(C(26, {"FASE PROCESSUAL": "CONHECIMENTO", "AND. NECESSÁRIO":
                    "Juiza dificil em Glauco, o atendente felipe disse que tentaria apressar. ",
                    "REVOGAÇÃO": "fazer revogaçao ", "OBSERVACOES": "Cliente não atende."}, CNJ[10]))
copia.append(C(27, {"FASE PROCESSUAL": "CONHECIMENTO", "REVOGAÇÃO": "NÃO SE APLICA"}, CNJ[11]))
copia.append(C(28, {"FASE PROCESSUAL": "ENCERRADO"}, CNJ[1]))           # CNJ repetido de propósito
salvar("copia", "tblvyoun2V0CQKmxF", copia)

# ---------------- PÓS PROCESSUAL
pos = [{"id": rid("POS", 1), "createdTime": "2026-08-01T09:00:00.000Z", "fields": {
        "N° DO PROCESSO": CNJ[1], "PROCESSUAL": [rid("PRO", 10)],
        "VALOR RECEBIDO CLIENTE": 19600.0, "VALOR HONORARIOS": 8400.0,
        "STATUS RECEBIMENTO": "CONCLUIDO", "STATUS ARQUIVAMENTO": "Arquivado",
        "RESPONSAVEL": [rid("FUN", 7)], "RESULTADO FINAL": "Alvará levantado."}},
       {"id": rid("POS", 2), "createdTime": "2026-08-01T09:00:00.000Z", "fields": {
        "N° DO PROCESSO": CNJ[4], "VALOR RECEBIDO CLIENTE": 10500.0,
        "VALOR SUCUMBENCIA": 500.0, "STATUS ARQUIVAMENTO": "Em andamento",
        "RESPONSAVEL": [rid("FUN", 7)]}},
       {"id": rid("POS", 3), "createdTime": "2026-08-01T09:00:00.000Z", "fields": {
        "N° DO PROCESSO": "99999999999999999999", "VALOR RECEBIDO CLIENTE": 100.0}}]
salvar("pos_processual", "tblEInHoBmUuuShxk", pos)

# ---------------- TESTEMUNHAS
tes = []
for i in range(1, 7):
    f = {"NOME TESTEMUNHA": "Testemunha %d" % i, "TELEFONE TESTEMUNHA": "1198888%04d" % i,
         "CPF": "222555888%02d" % (10 + i), "EMPRESA": [rid("EMP", (i % 5) + 1)],
         "STATUS TESTEMUNHA": ["PENDENTE", "A CONFIRMAR", "CONFIRMADA", "CONFIRMADA",
                               "DESCARTADA", "NAO USAR"][i-1],
         "VINCULO": ["COLEGA DE TRABALHO", "EX-COLEGA", "NAO INFORMADO", "TERCEIRO",
                     "COLEGA DE TRABALHO", "GESTOR/SUPERVISOR"][i-1],
         "origem_testemunha": "JURIDICO" if i % 2 else "COMERCIAL",
         "DATA ULTIMO CONTATO": "2026-08-1%d" % i, "TEM PROCESSO?": "SIM" if i == 2 else "NÃO"}
    if i in (1, 2): f["CAPTADOR"] = [rid("FUN", 2)]
    if i in (1, 3): f["COBRANÇA"] = "1º"
    if i in (1, 2, 3): f["TESTEMUNHA DE:"] = [rid("PRO", 4)]
    if i in (4, 5): f["TESTEMUNHA DE"] = [rid("PRE", 2)]
    if i == 6: f["ARQUIVOS ENVIADOS PELA TESTEMUNHA"] = [
        {"id": "att00000000000002", "filename": "carteira.jpg", "type": "image/jpeg",
         "size": 54321, "url": "https://exemplo/att2"}]
    if i == 2: f["OBSERVACOES"] = "Mora longe."
    if i in (1, 4): f["status_disparo"] = "PENDENTE"; f["tipo_disparo"] = "lembrete"
    if i == 3: f["notif_captador_status"] = "PENDENTE DE DADOS"
    tes.append({"id": rid("TES", i), "createdTime": "2026-07-01T09:00:00.000Z", "fields": f})
salvar("testemunhas", "tbl9nZjfmxqVy60NM", tes)

# ---------------- AUDITORIA TESTEMUNHAS
salvar("auditoria_testemunhas", "tblKp6rhoOGL2ChrO", [{
    "id": rid("AUD", 1), "createdTime": "2026-08-24T09:00:00.000Z", "fields": {
        "EVENTO ID": "COPY_PUBLIC_LINK:op1:recTES00000000001",
        "DATA/HORA": "2026-08-24T12:00:00Z", "ATOR RECORD ID": rid("FUN", 3),
        "ATOR NOME SNAPSHOT": "Colaborador 3", "SETOR SNAPSHOT": "Jurídico",
        "AÇÃO": "COPY_PUBLIC_LINK", "TESTEMUNHA RECORD ID": rid("TES", 1),
        "TESTEMUNHA NOME SNAPSHOT": "Testemunha 1", "CONTEXTO": "FORM_TESTEMUNHAS",
        "CAMPOS ALTERADOS": "[]", "ANTES": "{}", "DEPOIS": "{}",
        "OPERATION ID": "op1", "RESULTADO": "OK", "ORIGEM/SISTEMA": "FORM_TESTEMUNHAS"}}])

# ---------------- Conferência de Faltantes
falt = []
for i in range(1, 5):
    falt.append({"id": rid("FAL", i), "createdTime": "2026-08-01T09:00:00.000Z", "fields": {
        "NOME": "Reclamante %02d" % (19 + i), "Nº PROCESSO": CNJ[3 + i],
        "EMPRESA": [rid("EMP", (i % 5) + 1)], "VALOR": 8000.0 * i, "TRT": "2",
        "VARA": "%dª VARA DO TRABALHO" % i, "DISTRIBUIÇÃO": "2021-0%d-01" % i,
        "FASE RECOMENDADA (DATAJUD)": "ENCERRADO", "STATUS RECOMENDADO (DATAJUD)": "ARQUIVADO",
        "ÚLTIMO MOVIMENTO (DATAJUD)": "Arquivamento definitivo",
        "STATUS PROCESSO": "ARQUIVADO"}})
salvar("faltantes", "tblnQHm5yTj2EPscB", falt)
