#!/usr/bin/env python3
"""A publicação do diário vira PROPOSTA de prazo. Nunca vira prazo sozinha.

Este é o equivalente trabalhista do `aasp.py` do Prev, e a diferença não é de
sotaque — é de direito. Lá a publicação é praticamente log, e o prazo do JEF
corre em dias corridos. Aqui:

  · a contagem é em **dias úteis** (CLT art. 775, redação da Lei 13.467/2017);
  · o **recesso de 20/12 a 20/01 suspende** (art. 775-A);
  · **publicação** é o primeiro dia útil seguinte à disponibilização no DEJT
    (Lei 11.419/2006, art. 4º, §§ 3º e 4º), e o prazo começa no dia útil
    seguinte a ela — são DUAS datas, não uma, e confundi-las adianta ou atrasa
    o vencimento em dois dias;
  · intimação feita em audiência conta da audiência (Súmula 197 do TST);
  · o tipo do prazo sai de `prazo_tipos`, a lista da CLT que a governança
    guarda — 8 dias para recurso ordinário, 5 para embargos de declaração, e
    por aí.

Quem faz a conta é `prazo_legal.py`. Este módulo lê, casa com o processo,
propõe — e para.

**A regra 5 da casa vale inteira aqui**: automação cria tarefa e rascunho,
nunca protocola nem move etapa. A publicação entra como `NOVA`, com o tipo e o
vencimento que a máquina ACHA, e o prazo só nasce quando alguém do Jurídico lê
e manda criar. É a mesma decisão que o Lucas tomou no Prev em 23/08/2026 para
as decisões do diário, pelo mesmo motivo: para o hábito de ler não se perder.

    ./.venv/bin/python dejt.py --amostra              # prova o caminho sem rede
    ./.venv/bin/python dejt.py --arquivo lote.json    # um lote já baixado
    ./.venv/bin/python dejt.py --djen --dias 3        # a API pública do CNJ
    ./.venv/bin/python dejt.py --resumo               # o que já entrou
"""
import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata

import banco
import prazo_legal

# A API pública de comunicações processuais do CNJ (DJEN). Não pede
# credencial: é diário oficial. O que ela pede é o recorte — tribunal, datas e
# OAB — e é por OAB que se pega o que é NOSSO.
DJEN = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

CNJ = re.compile(r"\b(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})\b")

# O texto de uma intimação é longo e repete o inteiro teor. 12 mil caracteres
# cobrem folgado o que é ato; o que passa disso costuma ser peça anexada.
TEXTO_MAX = 12000


def _sem_acento(s):
    """"MANIFESTAÇÃO" → "manifestacao". O diário mistura caixa e acento na
    mesma frase, e comparar texto acentuado é como a rescisão indireta se
    perdeu na migração: um de/para "melhorado" à mão que nunca casava."""
    return unicodedata.normalize("NFKD", (s or "")).encode("ascii", "ignore").decode().lower()


# ------------------------------------------------------ o que o ato pede
#
# Cada linha: (marcas no texto, código em `prazo_tipos`, por que).
# A ORDEM IMPORTA — o primeiro que casar vence, e os mais específicos vêm
# primeiro. "embargos de declaração" tem de ser testado antes de "sentença",
# senão toda publicação de ED viraria recurso ordinário.
#
# O que NÃO está aqui não é chutado: cai em OUTRO, com o prazo padrão de 5 dias
# do CPC art. 218 §3º, e a tarefa diz que o tipo precisa ser confirmado. Chutar
# tipo de prazo é errar vencimento, e vencimento errado é prazo perdido.
REGRAS = [
    (("embargos de declaracao", "embargos declaratorios"), "EMBARGOS_DECLARACAO",
     "o texto fala em embargos de declaração (CLT art. 897-A: 5 dias)"),
    (("agravo de peticao",), "AGRAVO_PETICAO",
     "agravo de petição na execução (CLT art. 897, a: 8 dias)"),
    (("agravo de instrumento", "airr"), "AGRAVO_INSTRUMENTO",
     "agravo de instrumento (CLT art. 897, b: 8 dias)"),
    (("recurso de revista", "rr "), "RECURSO_REVISTA",
     "recurso de revista (CLT art. 896: 8 dias)"),
    (("contrarrazoes", "contra-razoes"), "CONTRARRAZOES",
     "prazo para contrarrazões (CLT art. 900: 8 dias)"),
    (("impugnacao aos calculos", "impugnar os calculos", "calculos de liquidacao",
      "conta de liquidacao"), "IMPUGNACAO_CALCULOS",
     "impugnação aos cálculos (CLT art. 879 §2º: 8 dias, sob pena de preclusão)"),
    (("laudo pericial", "manifestar sobre o laudo", "laudo do perito"),
     "MANIFESTACAO_LAUDO",
     "manifestação sobre laudo pericial (CPC art. 477 §1º c/c CLT art. 769)"),
    (("replica", "manifeste-se sobre a defesa", "manifestacao sobre a contestacao",
      "impugnacao a contestacao"), "REPLICA",
     "réplica à defesa; o juízo fixa o prazo (CPC art. 218 §3º no silêncio)"),
    (("razoes finais", "memoriais"), "RAZOES_FINAIS",
     "razões finais em memoriais (CLT art. 850)"),
    (("emenda a inicial", "emende a inicial"), "EMENDA_INICIAL",
     "emenda à inicial (CPC art. 321: 15 dias, sob pena de indeferimento)"),
    (("documentos juntados", "manifestar sobre os documentos"),
     "MANIFESTACAO_DOCUMENTOS",
     "manifestação sobre documentos juntados"),
    # Sentença por último entre os de recurso: quase toda publicação de mérito
    # cita a palavra, e ela só decide o tipo quando nenhum recurso foi nomeado.
    (("sentenca", "julgo procedente", "julgo improcedente",
      "julgo parcialmente procedente"), "RECURSO_ORDINARIO",
     "sentença publicada; o prazo que corre é o do recurso ordinário "
     "(CLT art. 895, I: 8 dias)"),
]

# Atos que NÃO abrem prazo para nós. Reconhecê-los evita encher a fila do
# Jurídico de publicação que não pede nada — que é como o hábito de ler morre.
SEM_PRAZO = ("arquivem-se os autos", "arquivamento definitivo", "transitado em julgado",
             "certidao de transito", "nada a prover", "ciencia as partes",
             "homologo o acordo", "designo audiencia", "redesigno a audiencia")


def classificar(texto):
    """(codigo_do_tipo, motivo, abre_prazo). Nunca levanta, nunca inventa."""
    t = _sem_acento(texto)
    for marca in SEM_PRAZO:
        if marca in t:
            return None, f"ato que não abre prazo para a parte ({marca})", False
    for marcas, codigo, porque in REGRAS:
        if any(m in t for m in marcas):
            return codigo, porque, True
    return "OUTRO", ("não reconheci o ato: entra como OUTRO, 5 dias (CPC art. 218 §3º). "
                     "[CONFIRMAR o tipo antes de criar o prazo]"), True


# ------------------------------------------------------ casar com o processo
def casar(bd, numero_cnj):
    """(processo_id, casou_por). O CNJ é exato; o alias é a outra grafia que a
    migração guardou quando a CÓPIA e a PROCESSUAL discordaram."""
    if not numero_cnj:
        return None, None
    digitos = re.sub(r"\D", "", numero_cnj)
    if not digitos:
        return None, None
    r = bd.execute("SELECT id FROM processos WHERE numero_cnj_digitos = ?",
                   (digitos,)).fetchone()
    if r:
        return r[0], "CNJ"
    r = bd.execute("""SELECT processo_id FROM processo_alias
                      WHERE regexp_replace(valor, '\\D', '', 'g') = ?""",
                   (digitos,)).fetchone()
    if r:
        return r[0], "ALIAS"
    return None, None


# ------------------------------------------------------ a proposta
def propor(bd, texto, disponibilizado_em, audiencia_id=None):
    """O que a máquina ACHA: (tipo, publicado_em, vencimento, motivo).

    A conta inteira é do `prazo_legal`: publicação no primeiro dia útil
    seguinte, início no dia útil depois dela, e os dias em ÚTEIS com recesso.
    """
    tipo, motivo, abre = classificar(texto)
    if not abre:
        pub, _, _ = prazo_legal.calcular(disponibilizado_em=disponibilizado_em)
        return None, pub, None, motivo

    r = bd.execute("SELECT dias, dias_padrao, nome FROM prazo_tipos WHERE codigo = ?",
                   (tipo,)).fetchone()
    if not r:
        return None, None, None, f"tipo {tipo} não está em prazo_tipos"
    dias_legais, dias_padrao, nome = r[0], r[1], r[2]
    # `dias` é o prazo legal; NULL quer dizer "o juízo fixa", e aí vale o
    # `dias_padrao` que o sistema propõe. A tela deixa corrigir, e a correção
    # fica no histórico.
    dias = dias_legais if dias_legais is not None else dias_padrao
    fixado = " (prazo legal)" if dias_legais is not None else " (padrão; o juízo fixa)"

    pub, inicio, venc = prazo_legal.calcular(
        disponibilizado_em=disponibilizado_em, dias=dias,
        da_audiencia=bool(audiencia_id))
    return tipo, pub, venc, f"{nome}: {dias} dias úteis{fixado}. {motivo}"


# ------------------------------------------------------ a entrada
def ingerir(bd, comunicacoes, fonte="DJEN"):
    """Grava o lote. Devolve o resumo — e NÃO cria prazo nenhum."""
    conta = {"novas": 0, "repetidas": 0, "casaram": 0, "orfas": 0,
             "com_proposta": 0, "sem_prazo": 0}
    for c in comunicacoes:
        texto = (c.get("texto") or "")[:TEXTO_MAX]
        cnj = c.get("numero_cnj") or (CNJ.search(texto).group(1) if CNJ.search(texto) else None)
        disp = c.get("disponibilizado_em")
        if not disp or not texto:
            continue

        # A chave contra duplicata: o id da origem quando existe, senão o hash
        # do próprio conteúdo. A leitura roda de novo o tempo todo — por retry
        # e por janela de datas sobreposta — e sem isto a mesma intimação
        # entraria duas vezes e o Jurídico leria duas vezes.
        fonte_id = str(c.get("id") or hashlib.sha256(
            f"{disp}|{cnj}|{texto}".encode()).hexdigest()[:32])
        if bd.execute("SELECT 1 FROM publicacoes WHERE fonte=? AND fonte_id=?",
                      (fonte, fonte_id)).fetchone():
            conta["repetidas"] += 1
            continue

        processo_id, casou_por = casar(bd, cnj)
        tipo, pub, venc, motivo = propor(bd, texto, disp)

        bd.execute("""INSERT INTO publicacoes
              (fonte, fonte_id, numero_cnj, tribunal, orgao, tipo_ato,
               disponibilizado_em, publicado_em, texto, processo_id, casou_por,
               prazo_tipo_sugerido, vencimento_sugerido, sugestao_motivo, bruto)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (fonte, fonte_id, cnj, c.get("tribunal"), c.get("orgao"),
                    c.get("tipo_ato"), disp, pub, texto, processo_id, casou_por,
                    tipo, venc, motivo, json.dumps(c, ensure_ascii=False)))
        conta["novas"] += 1
        conta["casaram" if processo_id else "orfas"] += 1
        conta["com_proposta" if tipo else "sem_prazo"] += 1
    bd.commit()
    return conta


# ------------------------------------------------------ a amostra
def amostra():
    """Publicações SINTÉTICAS com os casos que importam. Nenhum número de
    processo aqui é de gente de verdade: são CNJ inventados, no formato certo.

    Cobre o que a prova precisa distinguir: sentença (abre RO de 8 dias),
    embargos de declaração (5), cálculos (8, com preclusão), laudo pericial,
    réplica sem prazo legal fixo, um ato que NÃO abre prazo, um que o mapa não
    reconhece, e uma disponibilização em sexta-feira — que empurra a publicação
    para segunda e o início para terça.
    """
    return [
        {"id": "amostra-1", "numero_cnj": "1000000-11.2025.5.02.0001",
         "tribunal": "TRT2", "orgao": "1ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Sentença", "disponibilizado_em": "2026-09-03",
         "texto": "Fica a parte reclamante intimada da SENTENÇA de fls., que JULGO "
                  "PARCIALMENTE PROCEDENTE os pedidos."},
        {"id": "amostra-2", "numero_cnj": "1000000-22.2025.5.02.0002",
         "tribunal": "TRT2", "orgao": "2ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Despacho", "disponibilizado_em": "2026-09-03",
         "texto": "Intime-se para ciência dos EMBARGOS DE DECLARAÇÃO opostos pela "
                  "reclamada, querendo manifestar-se."},
        {"id": "amostra-3", "numero_cnj": "1000000-33.2025.5.02.0003",
         "tribunal": "TRT2", "orgao": "3ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Despacho", "disponibilizado_em": "2026-09-03",
         "texto": "Manifeste-se a parte sobre os CÁLCULOS DE LIQUIDAÇÃO apresentados, "
                  "sob pena de preclusão."},
        {"id": "amostra-4", "numero_cnj": "1000000-44.2025.5.02.0004",
         "tribunal": "TRT2", "orgao": "4ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Despacho", "disponibilizado_em": "2026-09-03",
         "texto": "Manifestem-se as partes sobre o LAUDO PERICIAL de insalubridade."},
        {"id": "amostra-5", "numero_cnj": "1000000-55.2025.5.02.0005",
         "tribunal": "TRT2", "orgao": "5ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Despacho", "disponibilizado_em": "2026-09-03",
         "texto": "MANIFESTE-SE SOBRE A DEFESA e os documentos, no prazo legal."},
        # não abre prazo: não pode encher a fila de quem lê
        {"id": "amostra-6", "numero_cnj": "1000000-66.2025.5.02.0006",
         "tribunal": "TRT2", "orgao": "6ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Certidão", "disponibilizado_em": "2026-09-03",
         "texto": "Certifico o TRÂNSITO EM JULGADO da r. sentença. ARQUIVEM-SE OS AUTOS "
                  "definitivamente."},
        # o mapa não reconhece: entra como OUTRO e pede confirmação
        {"id": "amostra-7", "numero_cnj": "1000000-77.2025.5.02.0007",
         "tribunal": "TRT2", "orgao": "7ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Despacho", "disponibilizado_em": "2026-09-03",
         "texto": "Cumpra-se o determinado no despacho retro, no que couber."},
        # sexta-feira: publicação cai na segunda, início na terça
        {"id": "amostra-8", "numero_cnj": "1000000-88.2025.5.02.0008",
         "tribunal": "TRT2", "orgao": "8ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Sentença", "disponibilizado_em": "2026-09-04",
         "texto": "Intimada a parte da SENTENÇA que JULGO PROCEDENTE os pedidos."},
        # dentro do recesso: tudo escorrega para depois de 20/01
        {"id": "amostra-9", "numero_cnj": "1000000-99.2025.5.02.0009",
         "tribunal": "TRT2", "orgao": "9ª Vara do Trabalho de São Paulo",
         "tipo_ato": "Sentença", "disponibilizado_em": "2026-12-22",
         "texto": "Intimada a parte da SENTENÇA. JULGO IMPROCEDENTE."},
    ]


def resumo(bd):
    # Os apelidos NÃO são enfeite: sem eles as três colunas se chamariam
    # `count`, e a linha volta como dicionário — as três colapsam numa chave
    # só e o acesso por posição estoura. É a mesma armadilha que a ponte do
    # Prev documenta entre `Row` do sqlite3 e o dict do psycopg.
    for linha in bd.execute("""
            SELECT situacao,
                   COUNT(*)                                                  AS total,
                   COUNT(processo_id)                                        AS casadas,
                   COUNT(*) FILTER (WHERE prazo_tipo_sugerido IS NOT NULL)   AS com_proposta
              FROM publicacoes GROUP BY situacao ORDER BY 1""").fetchall():
        print("  %-14s %5d   casadas: %4d   com proposta de prazo: %4d"
              % (linha[0], linha[1], linha[2], linha[3]))
    n = bd.execute("SELECT COUNT(*) FROM publicacoes WHERE processo_id IS NULL").fetchone()[0]
    if n:
        print(f"\n  {n} sem processo: ou não é nosso, ou o CNJ não está no cadastro.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--amostra", action="store_true", help="a amostra sintética (não usa rede)")
    p.add_argument("--arquivo", help="lote já baixado, no formato do DJEN")
    p.add_argument("--djen", action="store_true", help="busca na API pública do CNJ")
    p.add_argument("--oab", help="número da OAB do escritório: o recorte do que é nosso")
    p.add_argument("--uf", default="SP", help="UF da OAB (padrão SP)")
    p.add_argument("--tribunal", help="sigla, ex.: TRT2 — junto ou no lugar da OAB")
    p.add_argument("--dias", type=int, default=3, help="janela de dias, com --djen")
    p.add_argument("--resumo", action="store_true", help="o que já entrou")
    p.add_argument("--dsn", help="ligação com o Postgres (senão GGV_SUPABASE_TRAB)")
    a = p.parse_args()

    if a.dsn:
        os.environ["GGV_DSN"] = a.dsn
    bd = banco.conectar()

    if a.resumo:
        resumo(bd)
    elif a.amostra:
        c = ingerir(bd, amostra(), fonte="MANUAL")
        print("amostra sintética:", c)
        resumo(bd)
    elif a.arquivo:
        with open(a.arquivo) as f:
            dados = json.load(f)
        itens = dados.get("items") or dados.get("registros") or dados
        print("do arquivo:", ingerir(bd, itens))
    elif a.djen:
        import djen
        if not (a.oab or a.tribunal):
            sys.exit("✗ --djen precisa do recorte: --oab (com --uf) ou --tribunal.\n"
                     "  Sem ele o DJEN devolve o diário do país inteiro, e nada\n"
                     "  disso é nosso. Ver docs/dejt.md.")
        lote = djen.buscar(oab=a.oab, uf=a.uf, tribunal=a.tribunal, dias=a.dias)
        print(f"{len(lote)} comunicação(ões) na janela de {a.dias} dia(s).")
        print("do DJEN:", ingerir(bd, lote, fonte="DJEN"))
        resumo(bd)
    else:
        p.print_help()
    bd.close()


if __name__ == "__main__":
    main()
