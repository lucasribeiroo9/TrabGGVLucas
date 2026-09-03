#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""As tabelas de/para da migração — explícitas, uma linha por valor da origem.

Por que este arquivo existe separado de `migrar.py`: as listas poluídas são a
parte que MUDA quando o Lucas responde uma pergunta. Ficando aqui, mexer numa
tradução não obriga a ler a carga inteira, e o que foi decidido está num lugar
só, legível por quem não programa.

Três regras valem para tudo aqui:

1. **O valor original nunca se perde.** Toda função devolve `(valor, aviso)`.
   Quem chama grava o valor traduzido E o texto original — na coluna `_original`
   quando ela existe, e sempre no `airtable_bruto`.
2. **O que não casa não vira palpite.** Devolve `valor = None` e um `aviso` que
   o `migrar.py` transforma em linha de `conferencias`, com o texto de origem
   como prova. Adivinhar aqui é escrever no banco uma coisa que ninguém disse.
3. **Nada de comparação por semelhança.** As chaves são os textos EXATOS da
   origem, com espaço sobrando e erro de digitação incluídos (`'SIM '`,
   `'11ª TURMA '`, `'PROJETO JUXADA'`). Semelhança casa `Marina` com `Marize` —
   no Prev isso já custou caro.

    ./.venv/bin/python normalizar.py    # imprime as tabelas e o que não cobrem
"""
import re
import sys
import unicodedata

# ---------------------------------------------------------------- utilidades

def norm(s):
    """MAIÚSCULA sem acento, espaço colapsado. Para casar grafia, nunca para gravar."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def txt(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def so_digitos(v):
    return re.sub(r"\D", "", str(v)) if v not in (None, "") else None


def cpf_valido(c):
    if not c or len(c) != 11 or len(set(c)) == 1:
        return False
    for n in (9, 10):
        s = sum(int(c[i]) * ((n + 1) - i) for i in range(n))
        if int(c[n]) != (0 if s % 11 < 2 else 11 - s % 11):
            return False
    return True


def centavos(v):
    """R$ para inteiro. Dinheiro em float perde centavo e ninguém acha depois."""
    if v in (None, ""):
        return None
    if isinstance(v, str):
        v = v.replace("R$", "").replace("$", "").strip().replace(".", "").replace(",", ".")
        if not v:
            return None
    try:
        return int(round(float(v) * 100))
    except (TypeError, ValueError):
        return None


def data_iso(v):
    """O que o Airtable já entrega como data ISO."""
    if not v:
        return None
    s = str(v)[:10]
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else None


def datahora_iso(v):
    if not v:
        return None
    s = str(v).replace("T", " ").replace("Z", "")
    return s[:19] if len(s) >= 10 else None


MESES = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
         "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}


def data_br(v, campo="data"):
    """O campo DEMISSAO é texto em SEIS formatos: `d/m/aaaa`, `dd/mm/aaaa`,
    `dd-mm-aaaa`, com ponto final, com espaço, e já em ISO.

    A fórmula PRESCREVE do Airtable parseia só com `D/M/YYYY` — os 5 registros
    com hífen quebravam lá e a prescrição deles nunca foi calculada. Aqui os
    seis entram; o que não for data devolve aviso, não um palpite.
    """
    s = txt(v)
    if not s:
        return None, None
    s = s.strip().rstrip(".").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10], None
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", s)
    if m:
        d, mes, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a < 100:
            a += 2000 if a < 50 else 1900
        if 1 <= mes <= 12 and 1 <= d <= 31 and 1900 <= a <= 2100:
            return "%04d-%02d-%02d" % (a, mes, d), None
    m = re.match(r"^(\d{1,2})\s*de?\s*([A-Za-zçÇ]{3,})\s*de?\s*(\d{4})$", s, re.I)
    if m and norm(m.group(2))[:3] in MESES:
        return "%s-%02d-%02d" % (m.group(3), MESES[norm(m.group(2))[:3]], int(m.group(1))), None
    return None, aviso("DATA_ILEGIVEL", campo, s, "não é data em nenhum dos formatos da origem")


def percentual(v):
    """SUCUMBENCIA %: texto '5%', '10%', e um '2500%' que é erro de digitação.
    Art. 791-A da CLT fixa entre 5 e 15: fora disso, aviso."""
    s = txt(v)
    if not s:
        return None, None
    s = s.replace("%", "").replace(",", ".").strip()
    try:
        p = float(s)
    except ValueError:
        return None, aviso("VALOR_SEM_TRADUCAO", "sucumbencia_percent", s, "não é número")
    if not (0 < p <= 30):
        return None, aviso("VALOR_SEM_TRADUCAO", "sucumbencia_percent", s,
                           "fora da faixa do art. 791-A da CLT (5 a 15%)")
    return p, None


def cnpj_razao(v):
    """`CNPJ RECLAMADA` traz CNPJ e razão social no mesmo campo. Separa os dois;
    o que não tiver 14 dígitos fica só como razão social."""
    s = txt(v)
    if not s:
        return None, None
    m = re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", s)
    cnpj = so_digitos(m.group(0)) if m else None
    razao = s.replace(m.group(0), "").strip(" -–—,;") if m else s
    return (cnpj if cnpj and len(cnpj) == 14 else None), (razao or None)


def aviso(tipo, campo, valor, prova):
    """O que vira linha de `conferencias`. Sem entidade_id ainda: quem chama põe."""
    return {"tipo": tipo, "campo": campo, "valor_a": valor, "prova": prova}


def _traduz(tabela, valor, campo, tipo_aviso="VALOR_SEM_TRADUCAO"):
    """O mecanismo comum: chave exata primeiro, chave normalizada depois.

    A chave normalizada é o que salva `'11ª TURMA '` de `'11ª TURMA'` sem que
    seja preciso escrever as duas — mas as duas ESTÃO escritas quando o
    significado difere.
    """
    if valor in (None, "", []):
        return None, None
    if valor in tabela:
        return tabela[valor], None
    n = norm(valor)
    for k, v in tabela.items():
        if norm(k) == n:
            return v, None
    return None, aviso(tipo_aviso, campo, str(valor), "valor não previsto na tabela de/para")


# ================================================================= PESSOAS

PAPEL = {
    "Captador": "CAPTADOR", "Entrevistador": "ENTREVISTADOR", "Advogado": "ADVOGADO",
    "Responsável Inicial": "RESPONSAVEL_INICIAL", "Outro": "OUTRO",
    "Administrativo": "ADMINISTRATIVO", "Financeiro": "FINANCEIRO", "TI": "TI",
    "Gestor": "GESTOR", "Juridico": "JURIDICO", "Correspondente": "CORRESPONDENTE",
    "Testemunhas": "TESTEMUNHAS", "CEO": "CEO", "Documentação": "DOCUMENTACAO",
    "Atendimento": "ATENDIMENTO", "Publicação": "PUBLICACAO",
}

# ================================================================= CLIENTE

# ETAPA PRE PROCESSUAL: a etapa-mãe. Sozinha ela não basta — 40 fichas estão em
# PETIÇÃO INICIAL com a petição já DISTRIBUIDA. Quem decide é `etapa_cliente()`.
ETAPA_PRE = {
    "DOCUMENTAÇÃO": "DOCUMENTACAO",
    "ENTREVISTA": "ENTREVISTA",
    "PETIÇÃO INICIAL": "PETICAO_PENDENTE",   # refinada pelo STATUS PETICAO INICIAL
    "CONCLUÍDO": "DISTRIBUIDO",
    "CANCELAMENTO": "CANCELADO",
}

STATUS_PETICAO = {
    "PENDENTE": "PETICAO_PENDENTE",
    "EM CRIAÇÃO": "PETICAO_EM_CRIACAO",
    "AGUARDANDO APROVAÇÃO": "PETICAO_AGUARDANDO_APROVACAO",
    "APROVADA": "PETICAO_APROVADA",
    "DISTRIBUIDA": "DISTRIBUIDO",
    "DESISTENCIA": "CANCELADO",
    "PRESCRITO": "PRESCRITO",
    "VALIDAÇÃO": None,      # 0 usos; se for "revisão antes de aprovar" já é AGUARDANDO_APROVACAO
}

# STATUS ENTREVISTA: só três das opções são etapa da ficha inteira. O resto é
# contador, evento de agenda ou o fato que destrava a petição.
STATUS_ENTREVISTA = {
    "PENDENTE":            ("ETAPA", "ENTREVISTA"),
    "ENTREVISTA AGENDADA": ("EVENTO", "AGENDADO"),
    "REMARCAR":            ("EVENTO", "REMARCADO"),
    "PRIMEIRO CONTATO":    ("CONTATO", 1),
    "SEGUNDO CONTATO":     ("CONTATO", 2),
    "TERCEIRO CONTATO":    ("CONTATO", 3),
    "ENTREVISTA-OK":       ("FATO", "ENTREVISTA_REALIZADA"),
    "STAND-BY":            ("ETAPA", "STAND_BY"),
    "SEM RESPOSTA":        ("ETAPA", "SEM_RESPOSTA"),
    "DESISTÊNCIA ":        ("ETAPA", "CANCELADO"),      # com o espaço, como está na base
    "DESISTÊNCIA":         ("ETAPA", "CANCELADO"),
    # digitação livre que virou opção; nenhum registro usa
    "0": None, "ok": None, "ag": None, "SEM": None,
}

STATUS_DOCUMENTACAO = {
    "COMPLETA":    ("DERIVADO", None),
    "PENDENTE":    ("DERIVADO", None),
    "AGUARDANDO":  ("DERIVADO", None),
    "PARCIAL":     ("DERIVADO", None),
    "TRATAMENTO":  ("FLAG", "em_tratamento"),   # [CONFIRMAR o que significa]
    "DESISTÊNCIA": ("ETAPA", "CANCELADO"),
}

# FONTE mistura canal (Site, Instagram) com campanha (PROJETO PUXADA) e traz
# três grafias de Indicação. Cada opção vira (canal, campanha).
FONTE = {
    "Indicação":  ("INDICACAO", None),
    "INDICAÇÃO":  ("INDICACAO", None),
    "INDICAÇAO":  ("INDICACAO", None),
    "Site":       ("SITE", None),
    "Facebook":   ("FACEBOOK", None),
    "Instagram":  ("INSTAGRAM", None),
    "DISP LAILLA": ("DISPARO", "LAILLA"),
    "ENTRADA DE LEAD": ("OUTRO", None),
    "PROJETO PUXADA": ("PROJETO", "PUXADA"),
    "PROJETO PUXADA 17/06": ("PROJETO", "PUXADA 17/06"),
    "PROJETO JUXADA": ("PROJETO", "PUXADA"),          # erro de digitação, mesma campanha
    "PXD": ("PROJETO", "PUXADA"),                     # a abreviação usada pela captação
    "PROJETO CLIENTE ATIVO": ("PROJETO", "CLIENTE ATIVO"),
    "PROJETO BENEFICIO E ERROS DE CÁLCULO": ("PROJETO", "BENEFICIO E ERROS DE CALCULO"),
}

# RESCISAO é texto livre digitado por gente. Casa por trecho, do mais
# específico para o mais geral — a ordem importa: "SEM JUSTA CAUSA" tem de ser
# testado antes de "JUSTA CAUSA".
RESCISAO_TRECHOS = [
    (("RESCISAO INDIRET", "RECISAO INDIRET", "RESCISÃO INDIRET", "R.I", "RI "), "RESCISAO_INDIRETA"),
    (("SEM JUSTA CAUSA", "DEMISSAO SEM JUSTA", "DISPENSA SEM JUSTA"), "SEM_JUSTA_CAUSA"),
    (("PEDIDO DE DEMISSAO", "PEDIU DEMISSAO", "PEDIDO DEMISSAO"), "PEDIDO_DEMISSAO"),
    (("JUSTA CAUSA",), "JUSTA_CAUSA"),
    (("ACORDO 484", "484-A", "484 A", "ACORDO DE DEMISSAO"), "ACORDO_484A"),
    (("AINDA TRABALHA", "TRABALHANDO", "CONTRATO ATIVO", "EM ABERTO", "ATIVO NA EMPRESA"), "CONTRATO_VIVO"),
    (("TERMINO DE CONTRATO", "FIM DE CONTRATO", "EXPERIENCIA", "PRAZO DETERMINADO"), "TERMINO_CONTRATO"),
]


def rescisao(v):
    """Devolve (modalidade, aviso). O texto original é gravado sempre."""
    s = txt(v)
    if not s:
        return None, None
    n = norm(s)
    for trechos, destino in RESCISAO_TRECHOS:
        if any(t in n for t in trechos):
            return destino, None
    if re.match(r"^[\d/\-.\s()+]+$", s):
        return None, aviso("VALOR_SEM_TRADUCAO", "rescisao_modalidade", s,
                           "o campo traz data ou telefone, não modalidade de rescisão")
    return None, aviso("VALOR_SEM_TRADUCAO", "rescisao_modalidade", s,
                       "texto livre sem modalidade reconhecível")


# PENDENCIAS: a lista de documentos do caso trabalhista. HOLERITE e HOLERITES
# eram a mesma coisa; OK e DOCUMENTAÇÃO OK não são documento nenhum.
DOCUMENTO = {
    "CNH/RG": "CNH_RG", "CTPS": "CTPS", "TRCT": "TRCT", "DOCS. MÉDICOS": "DOCS_MEDICOS",
    "PROVAS": "PROVAS", "FGTS": "FGTS", "HOLERITES": "HOLERITES", "HOLERITE": "HOLERITES",
    "PIS": "PIS",
    "DOCUMENTAÇÃO OK": None, "OK": None,
}

# ================================================================= PROCESSO

FASE = {
    "CONHECIMENTO": "CONHECIMENTO",
    "RECURSAL": "RECURSAL",
    "EXECUÇÃO PROVISÓRIA": "EXECUCAO_PROVISORIA",
    "EXECUÇÃO DEFINITIVA": "EXECUCAO_DEFINITIVA",
    "EXECUÇÃO": "EXECUCAO",          # sem qualificação: decidida por `fase_execucao()`
    "ACORDO": "ACORDO",
    "RECEBENDO": "RECEBENDO",
    "ENCERRADO": "ENCERRADO",
    "DESISTENCIA": "DESISTENCIA",
    "INAPLICÁVEL ": "FORA_DO_ESCOPO",
    "INAPLICÁVEL": "FORA_DO_ESCOPO",
}


def fase_execucao(numero_cumprse, transito_em):
    """`EXECUÇÃO` sem qualificação é o que o script punha sem saber qual.

    Provisória é a que corre ANTES do trânsito, com número próprio de CumPrSe
    (art. 899 da CLT). Definitiva é depois dele. Sem nenhum dos dois fatos o
    sistema não tem etapa "não sei": fica DEFINITIVA e abre conferência.
    """
    if numero_cumprse and not transito_em:
        return "EXECUCAO_PROVISORIA", None
    if transito_em:
        return "EXECUCAO_DEFINITIVA", None
    return "EXECUCAO_DEFINITIVA", aviso(
        "VALOR_SEM_TRADUCAO", "fase", "EXECUÇÃO",
        "execução sem número de CumPrSe e sem data de trânsito: não dá para dizer "
        "se é provisória ou definitiva")


# STATUS DO PROCESSO: o campo que misturava fase, espera, incidente e arquivo.
# ('DERIVADO', x) = não se grava; ('FASE', x) = fase; ('RESULTADO', x) = fase
# ENCERRADO com esse resultado; ('INCIDENTE', x) = fluxo 5; ('TAREFA', x) = tarefa.
STATUS_PROCESSO = {
    "AGUARDANDO AUDIÊNCIA":  ("DERIVADO", "audiência futura"),
    "AGUARDANDO SENTENÇA":   ("DERIVADO", "instrução encerrada sem sentença"),
    "AGUARDANDO ACORDAO":    ("DERIVADO", "fase recursal sem acórdão"),
    "TRÂNSITO EM JULGADO":   ("FATO", "transito_em"),
    "EXECUCAO":              ("FASE", "EXECUCAO"),
    "ACORDO":                ("FASE", "ACORDO"),
    "SOBRESTADO":            ("FASE", "SOBRESTADO"),
    "DESISTENCIA":           ("FASE", "DESISTENCIA"),
    "ARQUIVADO":             ("RESULTADO", "ARQUIVADO"),
    "ROUBADO":               ("INCIDENTE", "DETECTADO"),
    "RECEBIDO POR ELES":     ("INCIDENTE", "PERDIDO"),
    "RECUPERADO":            ("INCIDENTE", "RECUPERADO"),
    "REDISTRIBUIR":          ("TAREFA", "Redistribuir o processo"),
    "INAPLICÁVEL":           ("FORA_DO_ESCOPO", None),
}

STATUS_CONHECIMENTO = {
    "AGUARDANDO AUDIÊNCIA":  ("DERIVADO", None),
    "AGUARDANDO SENTENÇA":   ("DERIVADO", None),
    "AGUARDANDO PERICIA":    ("DERIVADO", None),
    "ADVIDEO":               ("DERIVADO", None),
    "SENTENCIADA":           ("DECISAO", "SENTENCA"),
    "ACORDO EM ANDAMENTO":   ("FASE", "ACORDO"),
    "AUSÊNCIA":              ("AUSENCIA", "ARQUIVADO_AUSENCIA"),   # art. 844 CLT
    "DESISTÊNCIA":           ("FASE", "DESISTENCIA"),
    "ARQUIVADO":             ("RESULTADO", "ARQUIVADO"),
}

# STATUS EXECUÇÃO: 36 opções na PROCESSUAL, das quais só 16 são estado — as
# mesmas que a CÓPIA manteve limpas. O resto é texto que virou opção.
# ('SIT', x) = processos.situacao_execucao; ('FASE'/'RESULTADO'/'EVENTO', x) =
# o valor estava na coluna errada; None = sem tradução, vira conferência.
STATUS_EXECUCAO = {
    # --- os 16 estados limpos
    "AGUARDANDO TRANSITO":      ("SIT", "AGUARDANDO_TRANSITO"),
    "AGUARDANDO TRANSITO ":     ("SIT", "AGUARDANDO_TRANSITO"),
    "AGUARDANDO CÁLCULO":       ("SIT", "AGUARDANDO_CALCULO"),
    "AGUARDANDO CÁLCULOS":      ("SIT", "AGUARDANDO_CALCULO"),
    "FASE DE CÁLCULOS":         ("SIT", "CALCULOS_APRESENTADOS"),
    "AGUARDANDO PERICIA":       ("SIT", "AGUARDANDO_PERICIA_CONTABIL"),
    "HOMOLOGADO":               ("SIT", "HOMOLOGADO"),
    "RECURSO EXECUÇÃO":         ("SIT", "EM_RECURSO_EXECUCAO"),
    "PROCURANDO BENS":          ("SIT", "PESQUISA_PATRIMONIAL"),
    "NEGOCIANDO ACORDO":        ("SIT", "NEGOCIANDO_ACORDO"),
    "PARCELAMENTO 916 CPC":     ("SIT", "PARCELAMENTO_916"),
    "AGUARDANDO ALVARÁ":        ("SIT", "AGUARDANDO_ALVARA"),
    "RECEBIDO":                 ("SIT", "RECEBIDO"),
    "AUDIÊNCIA CONCILIAÇÃO":    ("EVENTO", "CONCILIACAO_EXECUCAO"),
    "ARQUIVADO":                ("RESULTADO", "ARQUIVADO"),
    "EXTINTA S/ RESOLUÇAO":     ("RESULTADO", "EXTINTA_SEM_RESOLUCAO"),
    "SOBRESTADO":               ("FASE", "SOBRESTADO"),
    "EXECUÇAO PROVISÓRIA":      ("FASE", "EXECUCAO_PROVISORIA"),
    # --- o texto digitado que virou opção, traduzido só onde é óbvio
    "FASE DE CALCULOS":            ("SIT", "CALCULOS_APRESENTADOS"),
    "FASE DE CALCULO":             ("SIT", "CALCULOS_APRESENTADOS"),
    "CALCULOS":                    ("SIT", "CALCULOS_APRESENTADOS"),
    "LIQUIDAÇAO":                  ("SIT", "CALCULOS_APRESENTADOS"),
    "Discutindo cálculos. ":       ("SIT", "CALCULOS_APRESENTADOS"),
    "Aguardando homologação":      ("SIT", "CALCULOS_APRESENTADOS"),
    "Homologado. ":                ("SIT", "HOMOLOGADO"),
    "ALVARA":                      ("SIT", "AGUARDANDO_ALVARA"),
    "PESQUISA ":                   ("SIT", "PESQUISA_PATRIMONIAL"),
    "Aguardando perícia contabil ":  ("SIT", "AGUARDANDO_PERICIA_CONTABIL"),
    "Designado a pericia contabil ": ("SIT", "AGUARDANDO_PERICIA_CONTABIL"),
    "Aguardando laudo contabil ":    ("SIT", "AGUARDANDO_PERICIA_CONTABIL"),
    # --- sem tradução possível: viram NULL + conferência (nada de inventar)
    "SIM": None, "SIM ": None, "NÃO": None, "NÃO ": None,
    "EXECUÇÃO": None, "RECURSAL": None,
}

STATUS_CUMPRSE = {
    "AGUARDANDO SENTENÇA":              ("SIT", "AGUARDANDO_TRANSITO"),
    "DECISÃO POSITIVA EM 1ª INSTÂNCIA": ("SIT", "AGUARDANDO_TRANSITO"),
    "DECISÃO POSITIVA EM 2ª INSTÂNCIA": ("SIT", "AGUARDANDO_TRANSITO"),
    "PERICIA CONTÁBIL":                 ("SIT", "AGUARDANDO_PERICIA_CONTABIL"),
    "FASE DE CÁLCULOS":                 ("SIT", "CALCULOS_APRESENTADOS"),
    "RECEBIDO":                         ("SIT", "RECEBIDO"),
    "ACORDO":                           ("FASE", "ACORDO"),
    "SOBRESTADO":                       ("FASE", "SOBRESTADO"),
}

STATUS_CALCULO = {
    "PENDENTE":          ("SIT", "AGUARDANDO_CALCULO"),
    "JUNTADO AOS AUTOS": ("SIT", "CALCULOS_APRESENTADOS"),
    "HOMOLOGADO":        ("SIT", "HOMOLOGADO"),
}

STATUS_ACORDO = {
    "ACORDO EM ANDAMENTO": "EM_ANDAMENTO",
    "ACORDO CUMPRIDO":     "CUMPRIDO",
    "QUEBRA DE ACORDO":    "QUEBRADO",
}

STATUS_PAGAMENTO = {
    "PENDENTE": ("DERIVADO", None), "CONCLUIDO": ("DERIVADO", None),
    "PAGO PARCIALMENTE": ("DERIVADO", None), "AGUARDANDO PAGAMENTO": ("DERIVADO", None),
    "PAGAMENTO EM DIA": ("DERIVADO", None), "PAGAMENTO ATRASADO": ("DERIVADO", None),
    "PARCELAMENTO CPC": ("SIT", "PARCELAMENTO_916"),
    "CESSAO DE CREDITOS": ("CESSAO", None),
}

DECISAO_OBJETIVA = {
    "PROCEDENTE": "PROCEDENTE",
    "PARCIALMENTE PROCEDENTE": "PARCIALMENTE_PROCEDENTE",
    "IMPROCEDENTE": "IMPROCEDENTE",
    "EXTINTO S/ RESOLUCAO DO MERITO": "EXTINTO_SEM_RESOLUCAO",
}

RESULTADO_RECURSO = {
    "PROVIDO": "PROVIDO",
    "PARCIALMENTE PROVIDO": "PARCIALMENTE_PROVIDO",
    "NEGADO PROVIMENTO": "NEGADO_PROVIMENTO",
    "NÃO CONHECIDO": "NAO_CONHECIDO",
}

NOTA = {"RUIM": "RUIM", "MÉDIA": "MEDIA", "MÉDIO": "MEDIA", "ÓTIMA": "OTIMA", "ÓTIMO": "OTIMA"}

# ULTIMA DECISAO mistura nota com resultado e ainda tem SEM DECISÃO.
ULTIMA_DECISAO = {
    "RUIM": ("NOTA", "RUIM"), "MÉDIA": ("NOTA", "MEDIA"), "ÓTIMA": ("NOTA", "OTIMA"),
    "PROCEDENTE": ("RESULTADO", "PROCEDENTE"), "IMPROCEDENTE": ("RESULTADO", "IMPROCEDENTE"),
    "SEM DECISÃO": ("NADA", None),
}

# CLASSIFICACAO: rito e classe no mesmo campo, e a CÓPIA ainda misturou classe
# de incidente e de recurso. Devolve (classe_cnj, rito, classe_incidente).
CLASSIFICACAO = {
    "RT - ORDINÁRIO":     ("RT", "ORDINARIO", None),
    "AT - ORDINÁRIO":     ("AT", "ORDINARIO", None),
    "AT - SUMARÍSSIMO":   ("AT", "SUMARISSIMO", None),
    "AT - SUMÁRIO":       ("AT", "SUMARIO", None),
    "EXECUCAO PROVISORIA": (None, None, "EXECUCAO_PROVISORIA"),
    "EXECUCAO DEFINITIVA": (None, None, "EXECUCAO_DEFINITIVA"),
    "EMBARGOS DE TERCEIRO": (None, None, "EMBARGOS_DE_TERCEIRO"),
    "RR":   (None, None, "RR"),
    "AIRR": (None, None, "AIRR"),
    "RRAg": (None, None, "RRAg"),
    "Emb":  (None, None, "EMBARGOS"),
}

# AUDIENCIA: tipo e modalidade viviam no mesmo campo, e UNA-RS ainda escondia o
# rito. Devolve (tipo, modalidade, rito).
AUDIENCIA = {
    "INICIAL":                 ("INICIAL", "PRESENCIAL", None),
    "INICIAL/VIDEO":           ("INICIAL", "VIDEO", None),
    "INSTRUÇÃO":               ("INSTRUCAO", "PRESENCIAL", None),
    "INSTRUCAO/VIDEO":         ("INSTRUCAO", "VIDEO", None),
    "UNA":                     ("UNA", "PRESENCIAL", None),
    "UNA/VIDEO":               ("UNA", "VIDEO", None),
    "UNA-RS":                  ("UNA", "PRESENCIAL", "SUMARISSIMO"),   # [CONFIRMAR 17]
    "UNA-RS/VIDEO":            ("UNA", "VIDEO", "SUMARISSIMO"),
    "HOMOLOGAÇÃO":             ("HOMOLOGACAO", None, None),
    "CONCILIAÇÃO EM EXECUÇÃO": ("CONCILIACAO_EXECUCAO", None, None),
    "JULGAMENTO":              ("JULGAMENTO", None, None),
}

STATUS_RECURSAL = {
    "TST":                   ("TST", None),
    "AGUARDANDO JULGAMENTO": ("TRT", None),
}

# REVOGAÇÃO tem DOIS sentidos e nove recados. O sentido depende do STATUS DO
# PROCESSO — ver `revogacao()` logo abaixo. ('SIM'/'NAO'/'NA') = o valor;
# ('TAREFA', titulo) = recado que é trabalho a fazer.
REVOGACAO = {
    "SIM ": "SIM", "SIM": "SIM",
    "NÃO": "NAO",
    "NÃO SE APLICA": "NA",
    "ROUBADO": "INCIDENTE",
    "VERIFICAR": ("TAREFA", "Verificar a revogação nos autos"),
    "fazer revogaçao": ("TAREFA", "Fazer a revogação"),
    "fazer revogaçao ": ("TAREFA", "Fazer a revogação"),
    "BRUNO - juntar revogaçao nestes autos ": ("TAREFA", "Juntar a revogação nestes autos"),
    "BRUNO - ver se colocaram a revogaçao acima": ("TAREFA", "Conferir se a revogação foi juntada"),
    "ver se colocaram a revogaçao acima": ("TAREFA", "Conferir se a revogação foi juntada"),
    "BRUNO -tem revogaçao nos autos abaixo": ("TAREFA", "Conferir a revogação nos autos"),
    "SEM REVOGAÇAO - RENAN QUE ASSINOU PROCURAÇAO": "NAO",
}


def revogacao(valor, status_processo):
    """Devolve (destino, valor, aviso).

    Sentido 1 — processo normal: NÓS juntamos a revogação do patrono anterior
    do cliente, e isso é atributo do processo.
    Sentido 2 — processo ROUBADO / RECEBIDO POR ELES: o CLIENTE nos revogou, e
    isso é o incidente de representação.
    A migração decide pelo STATUS DO PROCESSO. [CONFIRMAR pergunta 20.]
    """
    v, av = _traduz(REVOGACAO, valor, "revogacao")
    if av or v is None:
        return None, None, av
    if isinstance(v, tuple):
        return "TAREFA", v[1], None
    incidente = norm(status_processo) in ("ROUBADO", "RECEBIDO POR ELES", "RECUPERADO")
    if v == "INCIDENTE" or (v == "SIM" and incidente):
        return "INCIDENTE", True, None
    if v == "SIM":
        return "PROCESSO", True, None
    if v == "NAO":
        return "PROCESSO", False, None
    return "PROCESSO", None, None            # NÃO SE APLICA


NOTIFICACAO = {
    "PENDENTE":     ("DETECTADO", None),
    "EM AVALIAÇÃO": ("DETECTADO", None),
    "REDIGIDA":     ("DETECTADO", "notificacao_redigida_em"),
    "ENVIADA":      ("NOTIFICADO", "notificacao_enviada_em"),
    "RECEBIDA":     ("NOTIFICADO", "notificacao_recebida_em"),
    "RESPONDIDA":   ("NOTIFICADO", "resposta_em"),
}

# PROVIDENCIAS é to-do escrito à mão no campo errado.
PROVIDENCIAS = {
    "NOTIFICAR": "Enviar a notificação extrajudicial",
    "TRAVAR O RECEBIMENTO": "Pedir a reserva de honorários nos autos (EOAB art. 22 §4º)",
    "TRAVAR ULTIMA PARCELA": "Pedir a reserva de honorários sobre a última parcela (EOAB art. 22 §4º)",
}

# AND. NECESSÁRIO é o próximo passo — tarefa por definição. Encerrado e ACORDO
# são redundantes com a fase e não viram tarefa nenhuma.
AND_NECESSARIO = {
    "PEDIR ANDAMENTO":       "Pedir andamento processual",
    "Prosseguimento":        "Pedir prosseguimento",
    "EXPEDIÇAO DE ALVARÁ":   "Pedir a expedição do alvará",
    "Alvará":                "Pedir a expedição do alvará",
    "Alvará ":               "Pedir a expedição do alvará",
    "Alvara ":               "Pedir a expedição do alvará",
    "TENTAR ACORDO":         "Tentar acordo",
    "PEDIR AUD CONCILIAÇÃO": "Pedir audiência de conciliação",
    "Encerrado":             None,      # redundante com a fase
    "ACORDO":                None,      # idem
}

TRT_LIMPO = re.compile(r"^(\d{1,2})\s*[ªa]?$")


def trt(v):
    """21 opções com duplicata (`1ª` duas vezes, `9`/`9ª`, `10`/`10ª`, `85ª`) e
    duas opções de nome vazio na CÓPIA. Vira o número, e só."""
    s = txt(v)
    if not s:
        return None, None
    m = TRT_LIMPO.match(s.strip())
    if m and 1 <= int(m.group(1)) <= 24:
        return str(int(m.group(1))), None
    return None, aviso("VALOR_SEM_TRADUCAO", "trt", s,
                       "não é um dos 24 Tribunais Regionais do Trabalho")


TURMA_RX = re.compile(r"^(\d{1,2})\s*[ªa]?\s*TURMA$", re.I)
CAMARA_RX = re.compile(r"^(\d{1,2})\s*[ªa]?\s*C[ÂA]MARA$", re.I)
ORGAOS = ("VICE-PRESIDENCIA JUDICIAL", "PRESIDENCIA", "ANALISE DE RECURSOS",
          "ANALISE DE RECURSOS/VICE-PRESIDENCIA JUDICIAL",
          "ORGAO ESPECIAL - ANALISE DE RECURSO")


def turma(v):
    """41 opções: turmas com e sem espaço final, `18ª turma`, `11`, `7ª Câmara`,
    órgãos, e SETE números de processo digitados como opção.

    Número de processo não é turma: vai para conferência e o campo fica vazio.
    """
    s = txt(v)
    if not s:
        return None, None
    s = s.strip()
    m = TURMA_RX.match(s)
    if m:
        return "%dª TURMA" % int(m.group(1)), None
    m = CAMARA_RX.match(s)
    if m:
        return "%dª CÂMARA" % int(m.group(1)), None
    if norm(s) in ORGAOS:
        return norm(s).replace("ORGAO", "ÓRGÃO").replace("ANALISE", "ANÁLISE") \
                      .replace("PRESIDENCIA", "PRESIDÊNCIA"), None
    if len(so_digitos(s) or "") >= 15:
        return None, aviso("VALOR_SEM_TRADUCAO", "turma", "(número de processo digitado como turma)",
                           "o campo TURMA recebeu um número de processo")
    return None, aviso("VALOR_SEM_TRADUCAO", "turma", s, "não é turma, câmara nem órgão conhecido")


# ================================================================= EMPRESA / TESTEMUNHA

SITUACAO_EMPRESA = {"ATIVA": "ATIVA", "INATIVA": "INATIVA", "EM RECUPERACAO": "EM_RECUPERACAO"}
HIST_PAGAMENTO = {"BOA": "BOA", "RUIM": "RUIM", "PÉSSIMA": "PESSIMA"}
SIM_NAO = {"SIM": True, "NÃO": False, "NAO": False}

VINCULO = {
    "COLEGA DE TRABALHO": "COLEGA_DE_TRABALHO", "EX-COLEGA": "EX_COLEGA",
    "GESTOR/SUPERVISOR": "GESTOR_SUPERVISOR", "TERCEIRO": "TERCEIRO",
    "NAO INFORMADO": "NAO_INFORMADO",
}
STATUS_TESTEMUNHA = {
    "PENDENTE": "PENDENTE", "A CONFIRMAR": "A_CONFIRMAR", "CONFIRMADA": "CONFIRMADA",
    "DESCARTADA": "DESCARTADA", "NAO USAR": "NAO_USAR",
}
COBRANCA = {"1º": 1, "2º": 2, "3º": 3, "4º": 4}
ORIGEM_TESTEMUNHA = {"JURIDICO": "JURIDICO", "COMERCIAL": "COMERCIAL"}

FORCA = {
    "Prova documental própria da ré": "PROVA_DOCUMENTAL_DA_RE",
    "Confissão em depoimento": "CONFISSAO_EM_DEPOIMENTO",
    "Aritmética verificável": "ARITMETICA_VERIFICAVEL",
    "Tese a construir": "TESE_A_CONSTRUIR",
    "Depende de prova oral": "DEPENDE_DE_PROVA_ORAL",
}
STATUS_FRAGILIDADE = {
    "Inédita — nunca enfrentada": "INEDITA", "Acolhida": "ACOLHIDA",
    "Acolhida em parte": "ACOLHIDA_EM_PARTE", "Rejeitada": "REJEITADA",
    "Em julgamento": "EM_JULGAMENTO",
}

STATUS_ARQUIVAMENTO = {
    "Arquivado": ("DATA", None), "Em andamento": ("TAREFA", "Arquivar a pasta do processo"),
    "Não arquivado": ("NADA", None),
}

# ================================================================= a etapa do cliente


def etapa_cliente(etapa_pre, status_peticao, status_entrevista, status_doc):
    """A etapa da ficha, das quatro colunas que na origem discordavam entre si.

    A ordem de prioridade não é arbitrária: o STATUS PETICAO INICIAL é a etapa
    de verdade da petição (é ele que a automação PRÉ → PROCESSUAL lê), e as
    saídas — cancelamento, prescrição, stand by, sem resposta — valem sobre
    qualquer etapa de trabalho, porque a ficha inteira parou.

    Devolve (etapa, motivo, avisos). `motivo` preenche `clientes.motivo`.
    """
    avisos = []
    e_pre, av = _traduz(ETAPA_PRE, etapa_pre, "status", "DIVERGENCIA_FONTE")
    if av:
        avisos.append(av)
    e_pet, av = _traduz(STATUS_PETICAO, status_peticao, "status", "DIVERGENCIA_FONTE")
    if av:
        avisos.append(av)

    # as saídas vencem tudo
    if e_pre == "CANCELADO" or e_pet == "CANCELADO":
        return "CANCELADO", "DESISTENCIA", avisos
    if e_pet == "PRESCRITO":
        return "PRESCRITO", "prescrição registrada na origem", avisos
    ent = STATUS_ENTREVISTA.get(status_entrevista)
    if ent and ent[0] == "ETAPA" and ent[1] in ("STAND_BY", "SEM_RESPOSTA", "CANCELADO"):
        return ent[1], ("DESISTENCIA" if ent[1] == "CANCELADO" else None), avisos
    doc = STATUS_DOCUMENTACAO.get(status_doc)
    if doc and doc[0] == "ETAPA":
        return doc[1], "DESISTENCIA", avisos

    # o funil normal: a petição manda quando existe
    if e_pet:
        if e_pre == "DISTRIBUIDO" and e_pet != "DISTRIBUIDO":
            # os 3 CONCLUÍDOS com petição só APROVADA: fica na petição e anota
            avisos.append(aviso("DIVERGENCIA_FONTE", "status", "%s / %s" % (etapa_pre, status_peticao),
                                "ETAPA PRE PROCESSUAL diz concluído, STATUS PETICAO INICIAL não"))
        return e_pet, None, avisos
    return e_pre or "DOCUMENTACAO", None, avisos


# ================================================================= autoconferência

TABELAS = {
    "PAPEL": PAPEL, "ETAPA_PRE": ETAPA_PRE, "STATUS_PETICAO": STATUS_PETICAO,
    "STATUS_ENTREVISTA": STATUS_ENTREVISTA, "STATUS_DOCUMENTACAO": STATUS_DOCUMENTACAO,
    "FONTE": FONTE, "DOCUMENTO": DOCUMENTO, "FASE": FASE, "STATUS_PROCESSO": STATUS_PROCESSO,
    "STATUS_CONHECIMENTO": STATUS_CONHECIMENTO, "STATUS_EXECUCAO": STATUS_EXECUCAO,
    "STATUS_CUMPRSE": STATUS_CUMPRSE, "STATUS_CALCULO": STATUS_CALCULO,
    "STATUS_ACORDO": STATUS_ACORDO, "STATUS_PAGAMENTO": STATUS_PAGAMENTO,
    "DECISAO_OBJETIVA": DECISAO_OBJETIVA, "RESULTADO_RECURSO": RESULTADO_RECURSO,
    "NOTA": NOTA, "ULTIMA_DECISAO": ULTIMA_DECISAO, "CLASSIFICACAO": CLASSIFICACAO,
    "AUDIENCIA": AUDIENCIA, "STATUS_RECURSAL": STATUS_RECURSAL, "REVOGACAO": REVOGACAO,
    "NOTIFICACAO": NOTIFICACAO, "PROVIDENCIAS": PROVIDENCIAS, "AND_NECESSARIO": AND_NECESSARIO,
    "SITUACAO_EMPRESA": SITUACAO_EMPRESA, "HIST_PAGAMENTO": HIST_PAGAMENTO, "VINCULO": VINCULO,
    "STATUS_TESTEMUNHA": STATUS_TESTEMUNHA, "COBRANCA": COBRANCA, "FORCA": FORCA,
    "STATUS_FRAGILIDADE": STATUS_FRAGILIDADE, "STATUS_ARQUIVAMENTO": STATUS_ARQUIVAMENTO,
}

# Quantas opções cada select tem na origem (dicionario-dados.md, 03/09/2026).
# Serve de alarme: opção nova no Airtable é opção que a migração não conhece.
OPCOES_NA_ORIGEM = {
    "STATUS_ENTREVISTA": 14, "STATUS_PETICAO": 8, "ETAPA_PRE": 5, "STATUS_DOCUMENTACAO": 6,
    "FONTE": 14, "FASE": 10, "STATUS_PROCESSO": 14, "STATUS_CONHECIMENTO": 9,
    "STATUS_EXECUCAO": 36, "STATUS_CUMPRSE": 8, "STATUS_CALCULO": 3, "STATUS_ACORDO": 3,
    "STATUS_PAGAMENTO": 8, "DECISAO_OBJETIVA": 4, "RESULTADO_RECURSO": 4,
    "CLASSIFICACAO": 11, "AUDIENCIA": 11, "STATUS_RECURSAL": 2, "REVOGACAO": 12,
    "NOTIFICACAO": 6, "VINCULO": 5, "STATUS_TESTEMUNHA": 5, "COBRANCA": 4,
    "PAPEL": 16, "FORCA": 5, "STATUS_FRAGILIDADE": 5,
}


def conferir():
    """As tabelas cobrem as opções que a base tem hoje?"""
    falhas = 0
    print("%-22s %8s %8s" % ("tabela de/para", "linhas", "origem"))
    print("-" * 42)
    for nome in sorted(TABELAS):
        n = len(TABELAS[nome])
        o = OPCOES_NA_ORIGEM.get(nome)
        marca = ""
        if o is not None and n < o:
            marca, falhas = "  ⚠ falta opção", falhas + 1
        print("%-22s %8d %8s%s" % (nome, n, o if o is not None else "—", marca))
    sem_traducao = sum(1 for t in TABELAS.values() for v in t.values() if v is None)
    print("-" * 42)
    print("valores sem tradução (viram conferência): %d" % sem_traducao)
    print("\n%s\n" % ("TUDO CONFERE" if not falhas else "%d tabela(s) com opção faltando" % falhas))
    return falhas


if __name__ == "__main__":
    sys.exit(1 if conferir() else 0)
