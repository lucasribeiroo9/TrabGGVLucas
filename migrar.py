#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migra a BASE GGV - TRAB V3 (Airtable) para o Postgres do trabalhista.

O Airtable é SOMENTE LEITURA: este script só faz GET. Nada aqui escreve lá.

    ./.venv/bin/python migrar.py --baixar        # Airtable → dados/*.json (só GET)
    ./.venv/bin/python migrar.py --do-conector --origem PASTA   # JSON do conector MCP → dados/*.json
    ./.venv/bin/python migrar.py                 # dados/*.json → banco
    ./.venv/bin/python migrar.py --recriar       # apaga o public e refaz do esquema
    ./.venv/bin/python migrar.py --amostra 40    # 40 registros por tabela, para provar o caminho
    ./.venv/bin/python migrar.py --sql-saida carga.sql   # não conecta: escreve o SQL

De onde vem a ligação com o banco: `GGV_SUPABASE_TRAB` (ou `--dsn`). O token do
Airtable: `GGV_AIRTABLE_TRAB`. Mesma convenção do `chaves.py` do Prev — ambiente
primeiro, porque em Linux não existe Keychain.

## As três decisões que este script materializa

1. **A base é a CÓPIA DA PROCESSUAL**, casada por número CNJ com a PROCESSUAL,
   que vence nos campos que a equipe edita hoje. Onde as duas divergem em campo
   relevante, ninguém escolhe em silêncio: nasce linha em `conferencias`.
2. **Perda zero**: cada linha guarda o record de origem e o registro ORIGINAL
   INTEIRO em `airtable_bruto`. Nos processos o bruto tem os dois lados.
3. **A governança não pode barrar a carga do passivo.** Os gatilhos recusam
   nascer fora da etapa inicial e recusam ação depois da prescrição bienal —
   corretíssimo para o dia a dia, impossível para 3.722 processos de 2017 a 2026.
   Os gatilhos são DESLIGADOS durante a carga e RELIGADOS no fim, como o
   `--baixar` do Prev faz. O histórico das etapas migradas entra à mão, com
   `origem = 'MIGRACAO'`, para a ficha não nascer sem passado.

O que a migração PRESERVA entre execuções (não se apaga trabalho humano):
contas de acesso (`usuarios`), a configuração das automações (`automacoes`) e o
que já foi decidido em `conferencias` — dono, situação e anotação, recasados
pela `chave`.
"""
import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import normalizar as N                                        # noqa: E402
from normalizar import (aviso, centavos, cpf_valido, data_br, data_iso, datahora_iso,  # noqa: E402
                        norm, so_digitos, txt)

DADOS = os.path.join(AQUI, "dados")
BASE = "appMFTjWGygZ4ob5T"
TABELAS = {                       # nome do arquivo → (id da tabela, quantos registros hoje)
    "pre_processual":  ("tblucQ0Cz5MEQEdCR", 797),
    "processual":      ("tbl6rDaSPCQRbbzjq", 2652),
    "copia":           ("tblvyoun2V0CQKmxF", 3722),
    "pos_processual":  ("tblEInHoBmUuuShxk", 556),
    "funcionarios":    ("tblisgqzJvF0EUFr1", 72),
    "testemunhas":     ("tbl9nZjfmxqVy60NM", 424),
    "empresas":        ("tblkfWQhjp2F1dK0y", 1103),
    "faltantes":       ("tblnQHm5yTj2EPscB", 1067),
    "auditoria_testemunhas": ("tblKp6rhoOGL2ChrO", 2),
    "fragilidades":    ("tblmxkxgQEbc0KwvV", 17),
}


def segredo(nome):
    """Ambiente primeiro; Keychain só existe no Mac e não pode ser requisito."""
    v = (os.environ.get(nome) or "").strip()
    if v:
        return v
    import subprocess
    alvo = nome.replace("GGV_", "").lower().replace("_", "-")
    try:
        return subprocess.run(["security", "find-generic-password", "-s", alvo, "-w"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


# ==================================================================== o download

def baixar(so_estas=None):
    """Airtable → dados/*.json. SÓ GET: nenhuma chamada aqui escreve na base."""
    import requests
    tok = segredo("GGV_AIRTABLE_TRAB")
    if not tok:
        sys.exit("falta GGV_AIRTABLE_TRAB (token de LEITURA da base do trabalhista)")
    os.makedirs(DADOS, exist_ok=True)
    for nome, (tid, esperado) in TABELAS.items():
        if so_estas and nome not in so_estas:
            continue
        registros, offset = [], None
        while True:
            r = requests.get("https://api.airtable.com/v0/%s/%s" % (BASE, tid),
                             headers={"Authorization": "Bearer " + tok},
                             params={"pageSize": 100, **({"offset": offset} if offset else {})},
                             timeout=60)
            r.raise_for_status()
            d = r.json()
            registros += d.get("records", [])
            offset = d.get("offset")
            if not offset:
                break
            time.sleep(0.25)                      # o limite da API é 5 req/s
        caminho = os.path.join(DADOS, nome + ".json")
        json.dump({"tabela": tid, "baixado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "registros": registros}, open(caminho, "w"), ensure_ascii=False)
        marca = "" if len(registros) == esperado else "   ⚠ esperava %d" % esperado
        print("%-24s %6d registros%s" % (nome, len(registros), marca))


_avisou_amostra = set()


def ler(nome):
    """Lê o dump. Avisa em voz alta quando o dump é a amostra sintética de
    `dados_exemplo.py`: carregar dado inventado por engano na produção é o tipo
    de acidente que só se descobre quando alguém abre uma ficha e não reconhece
    o cliente."""
    caminho = os.path.join(DADOS, nome + ".json")
    if not os.path.exists(caminho):
        sys.exit("falta %s — rode antes: migrar.py --baixar" % caminho)
    d = json.load(open(caminho))
    if d.get("amostra_sintetica") and not _avisou_amostra:
        _avisou_amostra.add(nome)
        print("\n  ⚠  ATENÇÃO: dados/ é a AMOSTRA SINTÉTICA de dados_exemplo.py,\n"
              "     não a base do escritório. Para a carga de verdade:\n"
              "     rm -rf dados/ && ./.venv/bin/python migrar.py --baixar\n")
    return d["registros"]


def campo(f, *nomes):
    """Lê o campo tolerando o espaço sobrando no nome ('Nº  CumPrSe', 'SIM ')."""
    for n in nomes:
        for k in (n, n + " ", n.strip(), n.replace("  ", " ")):
            if k in f and f[k] not in (None, "", [], {}):
                return f[k]
    return None


def link(f, nome):
    """Campo de link do Airtable: lista de record ids."""
    v = campo(f, nome)
    if not v:
        return []
    return [x for x in v if isinstance(x, str) and x.startswith("rec")]


def um_link(f, nome):
    ls = link(f, nome)
    return ls[0] if ls else None


# ==================================================================== o banco

class Banco:
    """Fala psycopg quando há DSN e escreve SQL quando não há.

    Os ids são SEMPRE explícitos (`OVERRIDING SYSTEM VALUE`). Não é capricho:
    id determinístico faz a carga dar o MESMO resultado duas vezes, e é o que
    permite ao `conferir.py` comparar sem depender da ordem em que o Postgres
    resolveu numerar as linhas.
    """

    def __init__(self, dsn=None, sql_saida=None):
        self.seq = defaultdict(int)
        self.conta = defaultdict(int)
        self.arquivo = open(sql_saida, "w") if sql_saida else None
        self.con = None
        if self.arquivo:
            # o arquivo não pode depender da configuração de quem o aplica
            self.arquivo.write("SET standard_conforming_strings = on;\n")
        if not sql_saida:
            import psycopg
            self.con = psycopg.connect(dsn, autocommit=False)

    # -------------------------------------------------- primitivas
    def executar(self, sql, params=None):
        if self.arquivo:
            self.arquivo.write(self._render(sql, params or ()) + ";\n")
            return None
        cur = self.con.cursor()
        # params vazio tem de virar None: com `()` o psycopg ainda procura `%s`
        # no texto, e o `format('%I')` dos blocos DO da governança quebraria.
        cur.execute(sql, params if params else None)
        return cur

    def _render(self, sql, params):
        out, i = [], 0
        for parte in sql.split("%s"):
            out.append(parte)
            if i < len(params):
                out.append(self._literal(params[i]))
                i += 1
        return "".join(out)

    @staticmethod
    def _literal(v):
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return repr(v)
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        # Só a aspa dobra. A barra invertida fica como está: com
        # `standard_conforming_strings` ligado (padrão do Postgres e do Supabase)
        # '\' dentro de aspas simples é literal, e dobrá-la corrompia o JSON do
        # `airtable_bruto` que traz `\"` — o SQL do plano B parava no INSERT 3.171.
        return "'" + str(v).replace("'", "''") + "'"

    def inserir(self, tabela, dados):
        """Insere e devolve o id. Valor None não vira coluna: deixa o DEFAULT valer."""
        if tabela not in self.seq:
            # começa do maior id que já existe, não do zero. As tabelas que a
            # carga NÃO apaga (o log de execuções, por exemplo) sobreviveriam à
            # segunda rodada com id repetido — e o erro só apareceria na segunda.
            self.seq[tabela] = (self.consultar(
                "SELECT COALESCE(MAX(id),0) FROM %s" % tabela) or [[0]])[0][0]
        self.seq[tabela] += 1
        pk = self.seq[tabela]
        d = {"id": pk}
        d.update({k: v for k, v in dados.items() if v is not None})
        cols = ", ".join(d)
        marc = ", ".join(["%s"] * len(d))
        vals = [json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                for v in d.values()]
        self.executar("INSERT INTO %s (%s) OVERRIDING SYSTEM VALUE VALUES (%s)"
                      % (tabela, cols, marc), vals)
        self.conta[tabela] += 1
        return pk

    # -------------------------------------------------- a governança de lado
    GOVERNADAS = ("clientes", "processos", "audiencias", "prazos", "incidentes")

    def governanca(self, ligada):
        """Os gatilhos recusam nascer fora da etapa inicial e recusam ação depois
        da prescrição bienal. Restaurar o passado não é negócio novo: são 3.722
        processos de 2017 a 2026, e o Tema 350 do Prev ensinou que a carga tem de
        passar por fora e a regra voltar inteira no fim."""
        for t in self.GOVERNADAS:
            self.executar("ALTER TABLE %s %s TRIGGER USER" % (t, "ENABLE" if ligada else "DISABLE"))

    def limpar(self):
        """Apaga o que a migração escreve e PRESERVA o que gente decidiu."""
        guardadas = self.consultar(
            "SELECT chave, situacao, dono_id, anotacao, resolvido_em, resolvido_por "
            "FROM conferencias WHERE situacao <> 'ABERTA'") or []
        self.executar("""TRUNCATE processo_alias, testemunha_vinculos, testemunha_auditoria,
            pendencias, peticoes, anotacoes, contatos, eventos, tarefas, documentos,
            acordo_parcelas, acordos, calculos, recebimentos, repasses, decisoes, recursos,
            pericias, prazos, audiencias, incidentes, conferencia_faltantes, processos,
            clientes, testemunhas, fragilidades, empresas, pessoa_papeis, pessoas,
            conferencias, automacao_log, historico_etapas, auditoria RESTART IDENTITY CASCADE""")
        return {g[0]: g for g in guardadas}

    def acertar_sequencias(self):
        """Sem isto, a PRIMEIRA linha que o sistema criar depois da migração
        estoura com "duplicate key". `OVERRIDING SYSTEM VALUE` grava o id que a
        carga escolheu e NÃO adianta a sequência de identidade — ela continua
        no 1. O defeito não aparece na carga nem na conferência de contagem:
        aparece no primeiro cadastro que alguém fizer na tela, e foi um gatilho
        de histórico que o denunciou no cluster de teste."""
        self.executar("""
            DO $$
            DECLARE t TEXT; s TEXT; m BIGINT;
            BEGIN
              FOR t IN SELECT c.relname FROM pg_class c
                       JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'id'
                       WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r'
              LOOP
                s := pg_get_serial_sequence('public.' || quote_ident(t), 'id');
                IF s IS NOT NULL THEN
                  EXECUTE format('SELECT COALESCE(MAX(id),0) FROM public.%I', t) INTO m;
                  PERFORM setval(s, m + 1, false);
                END IF;
              END LOOP;
            END $$""")

    def consultar(self, sql, params=None):
        if self.arquivo:
            return []
        cur = self.executar(sql, params)
        return cur.fetchall()

    def fim(self, ok=True):
        if self.arquivo:
            self.arquivo.close()
        elif ok:
            self.con.commit()
        else:
            self.con.rollback()


# ==================================================================== a migração

class Migracao:
    def __init__(self, bd, amostra=None):
        self.bd = bd
        self.amostra = amostra
        self.conf = []                     # o que vai para `conferencias`
        self.pessoa = {}                   # record do Airtable → id
        self.empresa = {}
        self.cliente = {}
        self.cliente_por_cpf = {}
        self.cliente_por_nome = defaultdict(list)
        self.processo = {}
        self.processo_por_cnj = {}         # dígitos do CNJ → id do PRIMEIRO processo com ele
        self.testemunha = {}
        self.hist = []                     # (entidade, id, etapa)

    # ---------------------------------------------------------- conferências
    def anotar(self, av, entidade, entidade_id=None, rec=None, origem_a=None,
               valor_b=None, origem_b=None, escolhido=None, grupo=None):
        if not av:
            return
        chave = "%s|%s|%s|%s" % (entidade, rec or entidade_id, av["campo"],
                                 (av.get("valor_a") or "")[:60])
        self.conf.append(dict(chave=chave, tipo=av["tipo"], entidade=entidade,
                              entidade_id=entidade_id, campo=av["campo"],
                              valor_a=av.get("valor_a"), origem_a=origem_a,
                              valor_b=valor_b, origem_b=origem_b, escolhido=escolhido,
                              prova=av.get("prova"), airtable_record_id=rec, grupo=grupo))

    def _corta(self, registros):
        return registros[:self.amostra] if self.amostra else registros

    # ---------------------------------------------------------- 1. a equipe
    def equipe(self):
        for r in self._corta(ler("funcionarios")):
            f = r["fields"]
            nome = txt(campo(f, "NOME"))
            if not nome:
                continue
            pid = self.bd.inserir("pessoas", dict(
                nome=nome, nome_norm=norm(nome),
                ativo=(norm(campo(f, "STATUS")) != "INATIVO"),
                observacao=txt(campo(f, "OBSERVACOES")),
                ntfy_topic=txt(campo(f, "ntfy_topic")),
                ntfy_ativo=(norm(campo(f, "ntfy_ativo")) == "ATIVO") if campo(f, "ntfy_ativo") else None,
                airtable_record_id=r["id"], airtable_tabela="FUNCIONARIOS", airtable_bruto=f))
            self.pessoa[r["id"]] = pid
            for p in (campo(f, "FUNCOES") or []):
                papel = N.PAPEL.get(p)
                if papel:
                    self.bd.inserir("pessoa_papeis", dict(pessoa_id=pid, papel=papel))
                else:
                    self.anotar(aviso("VALOR_SEM_TRADUCAO", "papel", str(p), "papel não previsto"),
                                "pessoas", pid, r["id"])

    # ---------------------------------------------------------- 2. as reclamadas
    def empresas(self):
        for r in self._corta(ler("empresas")):
            f = r["fields"]
            nome = txt(campo(f, "EMPRESA"))
            if not nome:
                continue
            sit, av = N._traduz(N.SITUACAO_EMPRESA, campo(f, "STATUS EMPRESA"), "situacao")
            hist, _ = N._traduz(N.HIST_PAGAMENTO, campo(f, "HIST. PAGAMENTO"), "hist_pagamento")
            bens, _ = N._traduz(N.SIM_NAO, campo(f, "BENS IDENTIFICADOS"), "bens_identificados")
            eid = self.bd.inserir("empresas", dict(
                nome=nome, nome_norm=norm(nome), segmento=txt(campo(f, "SEGMENTO")),
                situacao=sit, hist_pagamento=hist, bens_identificados=bens,
                ggv_record_key=txt(campo(f, "GGV_RECORD_KEY")),
                airtable_record_id=r["id"], airtable_tabela="EMPRESAS", airtable_bruto=f))
            self.empresa[r["id"]] = eid
            self.anotar(av, "empresas", eid, r["id"])

    def fragilidades(self):
        for r in self._corta(ler("fragilidades")):
            f = r["fields"]
            forca, _ = N._traduz(N.FORCA, campo(f, "FORCA"), "forca")
            sit, _ = N._traduz(N.STATUS_FRAGILIDADE, campo(f, "STATUS"), "situacao")
            atualizado, av = data_br(campo(f, "ATUALIZADO EM"), "atualizado_em")
            fid = self.bd.inserir("fragilidades", dict(
                empresa_id=self.empresa.get(um_link(f, "EMPRESA")),
                achado=txt(campo(f, "ACHADO")) or "(sem título)",
                eixo=txt(campo(f, "EIXO")), forca=forca, situacao=sit,
                descricao=txt(campo(f, "DESCRICAO")), fundamento=txt(campo(f, "FUNDAMENTO")),
                prova=txt(campo(f, "PROVA")), como_explorar=txt(campo(f, "COMO EXPLORAR")),
                doc_a_requerer=txt(campo(f, "DOC A REQUERER")),
                processos_texto=txt(campo(f, "PROCESSOS")), periodo=txt(campo(f, "PERIODO")),
                valor_estimado_centavos=centavos(campo(f, "VALOR ESTIMADO")),
                atualizado_em=atualizado or data_iso(campo(f, "ATUALIZADO EM")),
                airtable_record_id=r["id"], airtable_tabela="FRAGILIDADES", airtable_bruto=f))
            self.anotar(av, "fragilidades", fid, r["id"])
            self.anexos(f, "DOSSIE", dict(fragilidade_id=fid, tipo="DOSSIE"), r["id"])

    # ---------------------------------------------------------- anexos e n8n
    def anexos(self, f, nome_campo, alvo, rec):
        """Anexo entra SÓ como metadado: nome, url, tamanho. Nunca uma cópia."""
        for a in (campo(f, nome_campo) or []):
            if not isinstance(a, dict):
                continue
            d = dict(alvo)
            d.update(nome_arquivo=a.get("filename") or "(sem nome)", mime=a.get("type"),
                     tamanho_bytes=a.get("size"), url_origem=a.get("url"),
                     fonte="ANEXO_AIRTABLE", airtable_attachment_id=a.get("id"),
                     airtable_record_id=rec, airtable_bruto=a)
            self.bd.inserir("documentos", d)

    def disparos(self, f, rec, **alvo):
        """Os campos do n8n (status_disparo, tipo_disparo, …) são RASTRO DE
        AUTOMAÇÃO, não estado de ninguém. Viram linha de log com resultado —
        e resultado é obrigatório porque o modo de falha da automação é o
        silêncio: rodada que falhou tem de ser distinguível de dia sem nada."""
        st = txt(campo(f, "status_disparo"))
        if not st:
            return
        erro = txt(campo(f, "erro_disparo"))
        resultado = "ERRO" if (erro or "erro" in st.lower()) else "MIGRADO"
        detalhe = "; ".join(x for x in [
            "tipo=" + (txt(campo(f, "tipo_disparo")) or "?"),
            "status=" + st,
            "responsavel=" + (txt(campo(f, "responsavel_interno")) or "?"),
            "solicitante=" + (txt(campo(f, "solicitante_disparo")) or "?"),
            ("erro=" + erro) if erro else None] if x)
        d = dict(automacao="LAILLA_DISPARO", chave="%s|%s" % (rec, st),
                 resultado=resultado, detalhe=detalhe, origem="N8N",
                 em=datahora_iso(campo(f, "data_solicitacao_disparo")))
        d.update(alvo)
        self.bd.inserir("automacao_log", d)

    def notificacao_n8n(self, f, rec, cliente_id):
        for nome, automacao in (("STATUS_NOTIFICACAO_PRESCRICAO", "AVISO_PRESCRICAO"),
                                ("STATUS_NOTIFICACAO_RI", "COBRANCA_RESCISAO_INDIRETA")):
            v = txt(campo(f, nome))
            if v and norm(v) != "NENHUM":
                self.bd.inserir("automacao_log", dict(
                    automacao=automacao, chave="%s|%s" % (rec, v), resultado="MIGRADO",
                    detalhe=v, origem="N8N", cliente_id=cliente_id))

    # ---------------------------------------------------------- 3. o cliente
    def clientes(self):
        for r in self._corta(ler("pre_processual")):
            f = r["fields"]
            nome = txt(campo(f, "NOME"))
            if not nome:
                continue
            etapa, motivo, avisos = N.etapa_cliente(
                campo(f, "ETAPA PRE PROCESSUAL"), campo(f, "STATUS PETICAO INICIAL"),
                campo(f, "STATUS ENTREVISTA"), campo(f, "STATUS DOCUMENTAÇÃO"))
            modalidade, av_resc = N.rescisao(campo(f, "RESCISAO"))
            demissao, av_dem = data_br(campo(f, "DEMISSAO"), "data_demissao")
            canal, campanha = None, None
            fonte = campo(f, "FONTE")
            if fonte:
                par, av_f = N._traduz(N.FONTE, fonte, "canal")
                if par:
                    canal, campanha = par
                else:
                    avisos.append(av_f)
            cpf = so_digitos(campo(f, "CPF"))
            doc_status = N.STATUS_DOCUMENTACAO.get(campo(f, "STATUS DOCUMENTAÇÃO"))
            cid = self.bd.inserir("clientes", dict(
                status=etapa, nome=nome, nome_norm=norm(nome),
                cpf=cpf, cpf_valido=bool(cpf and cpf_valido(cpf)),
                telefone=so_digitos(campo(f, "TELEFONE")), email=txt(campo(f, "E-MAIL")),
                data_nascimento=data_iso(campo(f, "NASCIMENTO")),
                empresa_id=self.empresa.get(um_link(f, "EMPRESA")),
                funcao=txt(campo(f, "FUNCAO")),
                data_assinatura_contrato=data_iso(campo(f, "DATA DE ASSINATURA")),
                contrato_vivo=(modalidade == "CONTRATO_VIVO"),
                data_demissao=demissao, data_demissao_original=txt(campo(f, "DEMISSAO")),
                rescisao_modalidade=modalidade, rescisao_original=txt(campo(f, "RESCISAO")),
                canal=canal, campanha=campanha, fonte_original=txt(fonte),
                captador_id=self.pessoa.get(um_link(f, "CAPTADOR")),
                entrevistador_id=self.pessoa.get(um_link(f, "ENTREVISTADOR")),
                responsavel_id=self.pessoa.get(um_link(f, "RESPONSAVEL INICIAL")),
                entrevista_em=datahora_iso(campo(f, "DATA ENTREVISTA")),
                entrevista_resumo=txt(campo(f, "RESUMO ENTREVISTA")),
                pericia_medica=bool(campo(f, "PERICIA MEDICA")),
                pericia_tecnica=bool(campo(f, "PERICIA INSALUB/PERIC")),
                em_tratamento=bool(doc_status and doc_status[0] == "FLAG"),
                passar_de_fase=bool(campo(f, "PASSAR DE FASE?")),
                drive_url=txt(campo(f, "DRIVE")), astrea_url=txt(campo(f, "ASTREA")),
                motivo=motivo, origem_cadastro="PRE_PROCESSUAL",
                criado_em=datahora_iso(campo(f, "Created")),
                airtable_record_id=r["id"], airtable_tabela="PRE PROCESSUAL", airtable_bruto=f))
            self.cliente[r["id"]] = cid
            self.hist.append(("clientes", cid, etapa))
            if cpf and cpf_valido(cpf):
                self.cliente_por_cpf.setdefault(cpf, cid)
            self.cliente_por_nome[norm(nome)].append(cid)
            for a in avisos + [av_resc, av_dem]:
                self.anotar(a, "clientes", cid, r["id"], origem_a="PRE PROCESSUAL", grupo="Documentação")

            # a agenda e os contatos da entrevista
            ent = N.STATUS_ENTREVISTA.get(campo(f, "STATUS ENTREVISTA"))
            if campo(f, "DATA ENTREVISTA"):
                self.bd.inserir("eventos", dict(
                    tipo="ENTREVISTA", cliente_id=cid,
                    data_hora=datahora_iso(campo(f, "DATA ENTREVISTA")),
                    situacao=("REALIZADO" if (ent and ent[0] == "FATO") else
                              (ent[1] if ent and ent[0] == "EVENTO" else "AGENDADO")),
                    responsavel_id=self.pessoa.get(um_link(f, "ENTREVISTADOR"))))
            if ent and ent[0] == "CONTATO":
                self.bd.executar("UPDATE clientes SET contatos_entrevista=%s WHERE id=%s",
                                 (ent[1], cid))
                for i in range(ent[1]):
                    self.bd.inserir("contatos", dict(cliente_id=cid, canal="TELEFONE",
                                                     origem="MIGRACAO",
                                                     resultado="contato %d (STATUS ENTREVISTA)" % (i + 1)))
            # os documentos que faltam
            for p in (campo(f, "PENDENCIAS") or []):
                tipo_doc = N.DOCUMENTO.get(p, "__nao__")
                if tipo_doc == "__nao__":
                    self.anotar(aviso("VALOR_SEM_TRADUCAO", "documento_tipo", str(p),
                                      "item de PENDENCIAS que não é documento"),
                                "pendencias", None, r["id"])
                elif tipo_doc:
                    self.bd.inserir("pendencias", dict(
                        cliente_id=cid, tipo="DOCUMENTO", documento_tipo=tipo_doc,
                        obrigatorio=(tipo_doc in ("CNH_RG", "CTPS", "TRCT")),
                        origem="MIGRACAO", grupo="Documentação", airtable_record_id=r["id"]))
            if txt(campo(f, "AVISOS")):
                self.bd.inserir("anotacoes", dict(cliente_id=cid, texto=txt(campo(f, "AVISOS")),
                                                  origem="MIGRACAO", campo_origem="AVISOS"))
            self.disparos(f, r["id"], cliente_id=cid)
            self.notificacao_n8n(f, r["id"], cid)

    # ---------------------------------------------------------- 4. os processos
    @staticmethod
    def _cnj(f):
        return so_digitos(campo(f, "Nº PROCESSO", "N° DO PROCESSO")) or None

    def casar_processos(self):
        """A CÓPIA é a base; a PROCESSUAL entra por cima nos campos que ela vence.

        O casamento é pelo número CNJ só com dígitos. Duplicado dos dois lados
        (8 na PROCESSUAL, 19 na CÓPIA) e os 106 sem número não somem: entram, e
        a divergência fica escrita em `conferencias`.
        """
        copia = self._corta(ler("copia"))
        proc = self._corta(ler("processual"))
        por_cnj_proc = defaultdict(list)
        for r in proc:
            c = self._cnj(r["fields"])
            if c:
                por_cnj_proc[c].append(r)
        usados, pares, vistos = set(), [], {}
        for r in copia:
            c = self._cnj(r["fields"])
            fila = por_cnj_proc.get(c) or []
            # cada registro da PROCESSUAL casa com UM da CÓPIA e só um. Sem
            # isso, os 19 números repetidos da cópia grudariam o mesmo registro
            # em duas linhas — e o índice único do record de origem, que existe
            # justamente para isso, derrubaria a carga no meio.
            par = fila.pop(0) if fila else None
            if par:
                usados.add(par["id"])
            if c and c in vistos:
                self.anotar(aviso("CNJ_DUPLICADO", "numero_cnj", "(número repetido)",
                                  "mais de um registro da CÓPIA com o mesmo número: "
                                  "cada um virou um processo, para não perder linha"),
                            "processos", None, r["id"], origem_a="CÓPIA")
            elif c and len(por_cnj_proc.get(c) or []) and par:
                self.anotar(aviso("CNJ_DUPLICADO", "numero_cnj", "(número repetido)",
                                  "mais de um registro da PROCESSUAL com o mesmo número"),
                            "processos", None, r["id"], origem_a="PROCESSUAL")
            vistos[c] = True
            pares.append((r, par))
        for r in proc:                      # os 22 só na PROCESSUAL e os 106 sem número
            if r["id"] in usados:
                continue
            if not self._cnj(r["fields"]):
                self.anotar(aviso("SEM_NUMERO", "numero_cnj", "(vazio)",
                                  "registro da PROCESSUAL sem número: não há como casar com a CÓPIA"),
                            "processos", None, r["id"], origem_a="PROCESSUAL")
            pares.append((None, r))
        return pares

    # os campos em que a PROCESSUAL vence a CÓPIA (docs/de-para.md)
    VENCE_PROCESSUAL = ("DATA REVOG", "Nº  CumPrSe", "VALOR HOM", "SUCUMB RECEBIDO",
                        "STATUS EXECUÇÃO", "REVOGAÇÃO", "NOTIFICAÇÃO", "PROVIDENCIAS",
                        "CLIENTE AVISADO?", "AND. NECESSÁRIO", "SITU. EMPRESA")
    # os campos cuja divergência entre as duas é relevante e vira conferência
    CONFERE = ("FASE PROCESSUAL", "STATUS DO PROCESSO", "NOME", "VARA", "VALOR",
               "DECISAO SENTENCA", "ENCERRAMENTO", "STATUS ACORDO")

    def valor(self, copia, proc, nome):
        """De qual lado sai o valor deste campo, e a divergência que sobra."""
        vc = campo(copia, nome) if copia else None
        vp = campo(proc, nome) if proc else None
        if nome in self.VENCE_PROCESSUAL:
            return (vp if vp not in (None, "", []) else vc)
        return (vc if vc not in (None, "", []) else vp)

    def fase_final(self, fc, fp):
        """A fase do processo, das duas fontes e das duas colunas que a
        guardavam. Fica aqui, num método só, porque o `conferir.py` recalcula a
        MESMA regra a partir da origem — se a regra viver em dois lugares, um
        dia as duas versões discordam e a prova deixa de provar nada.

        Devolve (fase, resultado_final, incidente_situacao, transito, avisos).
        `fase = None` quer dizer FORA DO ESCOPO: não vira processo.
        """
        avisos = []
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        fase, av = N._traduz(N.FASE, v("FASE PROCESSUAL"), "fase")
        avisos.append(av)
        st_proc = v("STATUS DO PROCESSO")
        transito = "TRÂNSITO EM JULGADO" if norm(st_proc) == "TRANSITO EM JULGADO" else None
        if fase == "EXECUCAO":
            fase, av = N.fase_execucao(txt(v("Nº  CumPrSe")), transito)
            avisos.append(av)
        if fase == "FORA_DO_ESCOPO":
            avisos.append(aviso("FORA_DO_ESCOPO", "fase", "INAPLICÁVEL",
                                "marcado como inaplicável na origem: não é processo trabalhista nosso"))
            return None, None, None, None, avisos
        fase = fase or "CONHECIMENTO"
        resultado_final = incidente_situacao = None
        st, _ = N._traduz(N.STATUS_PROCESSO, st_proc, "fase")
        if st:
            destino, valor_st = st
            if destino == "FASE" and valor_st == "SOBRESTADO":
                fase = "SOBRESTADO"
            elif destino == "RESULTADO":
                resultado_final, fase = valor_st, "ENCERRADO"
            elif destino == "INCIDENTE":
                incidente_situacao = valor_st
        return fase, resultado_final, incidente_situacao, transito, avisos

    def processos(self):
        for copia_r, proc_r in self.casar_processos():
            fc = copia_r["fields"] if copia_r else {}
            fp = proc_r["fields"] if proc_r else {}
            v = lambda nome: self.valor(fc, fp, nome)                      # noqa: E731
            rec_copia = copia_r["id"] if copia_r else None
            rec_proc = proc_r["id"] if proc_r else None

            fase, resultado_final, incidente_situacao, transito, avisos = self.fase_final(fc, fp)
            cumprse = txt(v("Nº  CumPrSe"))
            st_proc = v("STATUS DO PROCESSO")
            for a in avisos:
                self.anotar(a, "processos", None, rec_copia or rec_proc,
                            origem_a="CÓPIA" if rec_copia else "PROCESSUAL")
            if fase is None:
                continue
            classe, rito, classe_inc = (None, None, None)
            cl, av_cl = N._traduz(N.CLASSIFICACAO, v("CLASSIFICACAO"), "rito")
            if cl:
                classe, rito, classe_inc = cl

            trt_, av_trt = N.trt(v("TRT"))
            turma_, av_turma = N.turma(v("TURMA"))
            par_aud, _ = N._traduz(N.AUDIENCIA, v("AUDIENCIA"), "tipo")
            sit_exec, sit_orig, av_exec, aplicado = self.situacao_execucao(
                fc, fp, fase, par_aud[0] if par_aud else None)
            if aplicado and aplicado[0] == "resultado_final" and not resultado_final:
                resultado_final = aplicado[1]
            pct, av_pct = N.percentual(v("SUCUMBENCIA %"))
            cnpj, razao = N.cnpj_razao(campo(fc, "CNPJ RECLAMADA"))
            nasc, av_nasc = data_br(v("NASCIMENTO"), "nascimento_parte")
            valor_causa, av_valor = N.dinheiro(v("VALOR"), "valor_causa_centavos")
            ultima_mov = txt(v("ULTIMA MOV"))
            mov_em = (ultima_mov or "")[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", ultima_mov or "") else None

            cliente_id, av_cli = self.achar_cliente(fc, fp)
            pid = self.bd.inserir("processos", dict(
                cliente_id=cliente_id, fase=fase,
                numero_cnj=txt(v("Nº PROCESSO")),
                nome_parte=txt(v("NOME")), cpf_parte=so_digitos(campo(fc, "CPF")),
                email_parte=txt(campo(fc, "E-MAIL")),
                telefone_parte=so_digitos(v("TELEFONE")), nascimento_parte=nasc,
                empresa_id=self.empresa.get(um_link(fc, "EMPRESA") or um_link(fp, "EMPRESA")),
                cnpj_reclamada=cnpj, razao_social_reclamada=razao,
                trt=trt_, vara=txt(v("VARA")), turma=turma_,
                cadeira=txt(campo(fc, "CADEIRA")), relator=txt(campo(fc, "RELATOR")),
                turma_tst=txt(campo(fc, "TURMA TST")), relator_tst=txt(campo(fc, "RELATOR TST")),
                arquivo_tst_em=data_iso(campo(fc, "ARQUIVO TST")),
                tel_vara=txt(v("TEL VARA")),
                rito=rito, classe_cnj=classe, classe_incidente=classe_inc,
                valor_causa_centavos=valor_causa,
                complexidade=txt(v("COMPLEXIDADE")),
                distribuicao_em=data_iso(v("DISTRIBUIÇAO")),
                ajuizamento_em=data_iso(v("AÇÃO")), assinatura_em=data_iso(v("ASSINATURA")),
                advogado_id=self.pessoa.get(um_link(fc, "ADVOGADO") or um_link(fp, "ADVOGADO")),
                captador_id=self.pessoa.get(um_link(fc, "CAPTADOR") or um_link(fp, "CAPTADOR")),
                situacao_execucao=sit_exec, situacao_execucao_original=sit_orig,
                numero_cumprse=cumprse,
                transito_em=(data_iso(campo(fc, "DATA SENTENCA")) if transito else None),
                resultado_final=resultado_final, resultado_texto=txt(v("RESULTADO")),
                encerrado_em=data_iso(v("ENCERRAMENTO")),
                sucumbencia_percent=pct,
                pericia_medica=bool(v("PERICIA MEDICA")), pericia_tecnica=bool(v("PERICIA TECNICA")),
                ultima_movimentacao=ultima_mov, ultima_movimentacao_em=mov_em,
                drive_url=txt(v("DRIVE")), astrea_url=txt(v("ASTREA")),
                airtable_record_id=rec_copia, airtable_record_id_processual=rec_proc,
                airtable_tabela=("CÓPIA DA PROCESSUAL" if rec_copia else "PROCESSUAL"),
                airtable_bruto={"copia": fc, "processual": fp}))
            self.processo[rec_copia or rec_proc] = pid
            if rec_proc:
                self.processo[rec_proc] = pid
            cnj = so_digitos(v("Nº PROCESSO"))
            if cnj:
                self.processo_por_cnj.setdefault(cnj, pid)
            self.hist.append(("processos", pid, fase))
            for a in (av_cl, av_trt, av_turma, av_exec, av_pct, av_cli, av_nasc, av_valor):
                self.anotar(a, "processos", pid, rec_copia or rec_proc,
                            origem_a="CÓPIA" if rec_copia else "PROCESSUAL", grupo="Jurídico")
            self.divergencias(pid, fc, fp, rec_copia)
            self.filhos_do_processo(pid, fc, fp, rec_copia or rec_proc, st_proc, incidente_situacao)

    def resultado_sentenca(self, fc, fp):
        """(resultado de DECISAO SENTENCA, nota de SENTENCA, resultado FINAL).

        ULTIMA DECISAO só completa o que ficou vazio — e só quando existe
        sentença para completar (nota ou data). Fica num método só porque o
        `conferir.py` recalcula a MESMA regra da origem: foi a prova real que
        pegou um IMPROCEDENTE a mais no banco, vindo deste complemento.
        """
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        obj, _ = N._traduz(N.DECISAO_OBJETIVA, v("DECISAO SENTENCA"), "resultado_objetivo")
        nota, _ = N._traduz(N.NOTA, v("SENTENCA"), "nota")
        final = obj
        if not obj and (nota or campo(fc, "DATA SENTENCA")):
            ud, _ = N._traduz(N.ULTIMA_DECISAO, v("ULTIMA DECISAO"), "resultado_objetivo")
            if ud and ud[0] == "RESULTADO":
                final = ud[1]
        return obj, nota, final

    def situacao_execucao(self, fc, fp, fase=None, tipo_audiencia=None):
        """PROCESSUAL vence (59 preenchidos só nela); a lista limpa é a da CÓPIA.

        Devolve (situacao, original, aviso, aplicado). O campo misturava estado
        da execução com fase, resultado e evento: a carga real tem 198 processos
        em que o valor estava na coluna errada. Onde ele é COERENTE com o que a
        fase já disse (ARQUIVADO/EXTINTA em processo ENCERRADO; a mesma fase;
        audiência de conciliação que existe), aplica-se ou nada há a fazer, e
        `aplicado` diz o quê. Onde DISCORDA, abre conferência — guardar só no
        `_original` e seguir seria escolher em silêncio. O `conferir.py`
        recalcula esta mesma função da origem.
        """
        bruto = campo(fp, "STATUS EXECUÇÃO") or campo(fc, "STATUS EXECUÇÃO")
        if not bruto:
            return None, None, None, None
        par, av = N._traduz(N.STATUS_EXECUCAO, bruto, "situacao_execucao")
        if par is None:
            return None, txt(bruto), (av or aviso(
                "VALOR_SEM_TRADUCAO", "situacao_execucao", txt(bruto),
                "opção poluída sem tradução: fica em branco, com o texto original guardado")), None
        destino, valor = par
        if destino == "SIT":
            return valor, txt(bruto), None, None
        if destino == "RESULTADO":
            if fase == "ENCERRADO":
                return None, txt(bruto), None, ("resultado_final", valor)
            return None, txt(bruto), aviso(
                "VALOR_SEM_TRADUCAO", "situacao_execucao", txt(bruto),
                "STATUS EXECUÇÃO diz %s, mas a fase gravada é %s: não se aplica em silêncio"
                % (valor, fase)), None
        if destino == "FASE":
            if fase == valor:
                return None, txt(bruto), None, ("fase", valor)
            return None, txt(bruto), aviso(
                "VALOR_SEM_TRADUCAO", "situacao_execucao", txt(bruto),
                "STATUS EXECUÇÃO diz fase %s, mas FASE PROCESSUAL e STATUS DO PROCESSO deram %s"
                % (valor, fase)), None
        # EVENTO: audiência de conciliação em execução, sem data neste campo
        if tipo_audiencia == valor:
            return None, txt(bruto), None, ("audiencia", valor)
        return None, txt(bruto), aviso(
            "VALOR_SEM_TRADUCAO", "situacao_execucao", txt(bruto),
            "STATUS EXECUÇÃO registra audiência de conciliação em execução, sem data e sem "
            "audiência correspondente no campo AUDIENCIA: não virou evento"), None

    def divergencias(self, pid, fc, fp, rec):
        """Onde a CÓPIA e a PROCESSUAL discordam em campo relevante. Ninguém
        escolhe em silêncio — e são 1.403 divergências só de FASE."""
        if not (fc and fp):
            return
        for nome in self.CONFERE:
            a, b = campo(fc, nome), campo(fp, nome)
            if a in (None, "", []) or b in (None, "", []) or norm(a) == norm(b):
                continue
            self.anotar(aviso("DIVERGENCIA_FONTE", nome, str(a),
                              "a CÓPIA e a PROCESSUAL discordam neste campo"),
                        "processos", pid, rec, origem_a="CÓPIA", valor_b=str(b),
                        origem_b="PROCESSUAL", escolhido=str(self.valor(fc, fp, nome)),
                        grupo="Jurídico")
            if nome in ("NOME", "VARA", "NASCIMENTO", "TELEFONE"):
                perdido = b if nome not in self.VENCE_PROCESSUAL else a
                self.bd.inserir("processo_alias", dict(
                    processo_id=pid, campo=nome, valor=str(perdido),
                    origem=("PROCESSUAL" if perdido is b else "COPIA")))

    def achar_cliente(self, fc, fp):
        """Todo processo tem dono. Do mais forte para o mais fraco:
        o link vivo da PROCESSUAL, o CPF dos autos, o nome + a reclamada.
        O que não é seguro NÃO vira palpite: nasce ficha com origem PROCESSO e
        uma conferência aberta, porque cliente errado é pior que cliente novo."""
        rec_pre = um_link(fp, "PRE PROCESSUAL")
        if rec_pre and rec_pre in self.cliente:
            return self.cliente[rec_pre], None
        cpf = so_digitos(campo(fc, "CPF"))
        if cpf and cpf_valido(cpf) and cpf in self.cliente_por_cpf:
            return self.cliente_por_cpf[cpf], None
        nome = txt(campo(fc, "NOME") or campo(fp, "NOME"))
        candidatos = self.cliente_por_nome.get(norm(nome or ""), [])
        if len(candidatos) == 1:
            return candidatos[0], None
        av = None
        if len(candidatos) > 1:
            av = aviso("CLIENTE_AMBIGUO", "cliente_id", nome,
                       "%d fichas com o mesmo nome: o processo ficou com uma ficha nova" % len(candidatos))
        cid = self.bd.inserir("clientes", dict(
            status="DISTRIBUIDO", nome=nome or "(sem nome nos autos)", nome_norm=norm(nome),
            cpf=cpf, cpf_valido=bool(cpf and cpf_valido(cpf)),
            email=txt(campo(fc, "E-MAIL")), telefone=so_digitos(campo(fc, "TELEFONE")),
            empresa_id=self.empresa.get(um_link(fc, "EMPRESA") or um_link(fp, "EMPRESA")),
            origem_cadastro="PROCESSO",
            airtable_tabela="CÓPIA DA PROCESSUAL",
            airtable_bruto={"origem": "ficha criada a partir dos autos"}))
        self.hist.append(("clientes", cid, "DISTRIBUIDO"))
        if cpf and cpf_valido(cpf):
            self.cliente_por_cpf.setdefault(cpf, cid)
        if nome:
            self.cliente_por_nome[norm(nome)].append(cid)
        return cid, av

    # ------------------------------------------------ o que pende do processo
    def filhos_do_processo(self, pid, fc, fp, rec, st_proc, incidente_situacao):
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731

        # --- audiência: uma LINHA, não um campo sobrescrito
        if v("DATA AUDIENCIA") or v("AUDIENCIA"):
            tipo = mod = rito = None
            par, av = N._traduz(N.AUDIENCIA, v("AUDIENCIA"), "tipo")
            if par:
                tipo, mod, rito = par
            st_conh = N.STATUS_CONHECIMENTO.get(v("STATUS CONHECIMENTO")) or (None, None)
            ausencia = st_conh[0] == "AUSENCIA"
            aid = self.bd.inserir("audiencias", dict(
                processo_id=pid, situacao=("NAO_REALIZADA" if ausencia else "DESIGNADA"),
                data_hora=datahora_iso(v("DATA AUDIENCIA")), tipo=tipo, modalidade=mod,
                motivo=("AUSENCIA_RECLAMANTE" if ausencia else None),
                advideo_em=datahora_iso(v("DATA ADVIDEO")),
                advideo_responsavel_id=self.pessoa.get(um_link(fp, "RESP ADVIDEO")),
                advideo_previsto=bool(v("STATUS ADVIDEO")),
                airtable_record_id=rec, airtable_tabela="PROCESSUAL",
                airtable_bruto={"AUDIENCIA": v("AUDIENCIA"), "STATUS ADVIDEO": v("STATUS ADVIDEO")}))
            self.hist.append(("audiencias", aid, "NAO_REALIZADA" if ausencia else "DESIGNADA"))
            self.bd.inserir("eventos", dict(tipo="AUDIENCIA", processo_id=pid, audiencia_id=aid,
                                            data_hora=datahora_iso(v("DATA AUDIENCIA")),
                                            situacao="REALIZADO" if ausencia else "AGENDADO"))
            if rito:
                self.bd.executar("UPDATE processos SET rito=COALESCE(rito,%s) WHERE id=%s", (rito, pid))
            self.anotar(av, "audiencias", aid, rec, origem_a="AUDIENCIA")

        # --- perícias
        for nome_data, tipo in (("DATA PERÍCIA MÉDICA", "MEDICA"), ("DATA PERÍCIA TECNICA", "TECNICA")):
            if v(nome_data):
                self.bd.inserir("pericias", dict(processo_id=pid, tipo=tipo,
                                                 data_hora=datahora_iso(v(nome_data))))

        # --- decisões: o resultado OBJETIVO e a NOTA são coisas diferentes
        obj, nota, obj_final = self.resultado_sentenca(fc, fp)
        if obj or nota or campo(fc, "DATA SENTENCA"):
            self.bd.inserir("decisoes", dict(
                processo_id=pid, tipo="SENTENCA", data=data_iso(campo(fc, "DATA SENTENCA")),
                resultado_objetivo=obj_final, nota=nota, grau="PRIMEIRO",
                magistrado=txt(campo(fc, "MAGISTRADO")), orgao=txt(v("VARA"))))
        obj_rec, _ = N._traduz(N.RESULTADO_RECURSO, campo(fc, "RESULTADO RECURSO"), "resultado_objetivo")
        nota_ac, _ = N._traduz(N.NOTA, v("RESULTADO ACORDAO"), "nota")
        if obj_rec or nota_ac or v("DATA ACORDAO"):
            did = self.bd.inserir("decisoes", dict(
                processo_id=pid, tipo="ACORDAO", data=data_iso(v("DATA ACORDAO")),
                resultado_objetivo=obj_rec, nota=nota_ac, grau="TRT",
                orgao=txt(campo(fc, "TURMA"))))
            if obj_rec:
                self.bd.inserir("recursos", dict(
                    processo_id=pid, tipo="OUTRO", grau="TRT", resultado=obj_rec,
                    julgado_em=data_iso(v("DATA ACORDAO")), decisao_id=did,
                    relator=txt(campo(fc, "RELATOR")), orgao=txt(campo(fc, "TURMA")),
                    observacao="tipo do recurso não registrado na origem [CONFIRMAR 22]"))
        # --- recurso pendente (o que o STATUS RECURSAL sabia dizer)
        st_rec, _ = N._traduz(N.STATUS_RECURSAL, v("STATUS RECURSAL"), "grau")
        if st_rec:
            self.bd.inserir("recursos", dict(
                processo_id=pid, tipo="OUTRO", grau=st_rec[0],
                observacao="recurso pendente inferido do STATUS RECURSAL [CONFIRMAR 22: de quem]"))

        # --- o dinheiro
        for base, val, suc, hon in (
                ("RECLAMANTE", v("CALCULO RCTE"), v("SUCUMB RCTE"), campo(fc, "HONOR TOTAL CALCULO RCTE")),
                ("RECLAMADA",  v("CALCULO RCDA"), v("SUCUMB RCDA"), campo(fc, "HONOR TOTAL CALCULO RCDA")),
                ("HOMOLOGADO", v("VALOR HOM"),    v("SUCUMB HOM"),  campo(fc, "HONOR  TOTAL HOMOL"))):
            if any(x not in (None, "") for x in (val, suc, hon)):
                st_calc, _ = N._traduz(N.STATUS_CALCULO, v("STATUS DO CALCULO"), "situacao_execucao")
                self.bd.inserir("calculos", dict(
                    processo_id=pid, base=base, valor_centavos=centavos(val),
                    sucumbencia_centavos=centavos(suc), honorario_centavos=centavos(hon),
                    homologado_em=(data_iso(v("ENCERRAMENTO")) if base == "HOMOLOGADO"
                                   and st_calc and st_calc[1] == "HOMOLOGADO" else None)))
        st_ac, _ = N._traduz(N.STATUS_ACORDO, v("STATUS ACORDO"), "situacao")
        if st_ac or v("VALOR ACORDO") or campo(fc, "DATA DO ACORDO"):
            self.bd.inserir("acordos", dict(
                processo_id=pid, valor_centavos=centavos(v("VALOR ACORDO")),
                honorario_centavos=centavos(campo(fc, "HONOR TOTAL ACORDO")),
                parcelas=v("PARCELAS"),
                valor_parcela_centavos=centavos(campo(fc, "VALOR PARCELA")),
                homologado_em=data_iso(campo(fc, "DATA DO ACORDO")),
                situacao=st_ac or "EM_ANDAMENTO",
                observacao=("as parcelas nascem no portal: a origem só guardava quantas eram"
                            if v("PARCELAS") else None)))
        for base, valor_bruto in (("TOTAL", v("TOTAL RECEBIDO")),
                                  ("SUCUMBENCIA", v("SUCUMB RECEBIDO")),
                                  ("HONORARIOS", v("HONOR TOTAL"))):
            c = centavos(valor_bruto)
            if c:
                self.bd.inserir("recebimentos", dict(processo_id=pid, base=base, valor_centavos=c))

        # --- o incidente de representação
        destino_rev, valor_rev, av_rev = N.revogacao(v("REVOGAÇÃO"), st_proc)
        notif = N.NOTIFICACAO.get(v("NOTIFICAÇÃO"))
        prov = txt(v("PROVIDENCIAS"))
        if incidente_situacao or notif or destino_rev == "INCIDENTE" or prov:
            situacao = incidente_situacao or (notif[0] if notif else "DETECTADO")
            campos = dict(processo_id=pid, situacao=situacao, tipo="TROCA_DE_ADVOGADO",
                          providencia_texto=prov,
                          cliente_avisado_em=(data_iso(v("ENCERRAMENTO")) if v("CLIENTE AVISADO?") else None),
                          revogacao_nos_autos_em=(data_iso(v("DATA REVOG"))
                                                  if destino_rev == "INCIDENTE" else None))
            if notif and notif[1]:
                campos[notif[1]] = data_iso(v("DATA REVOG")) or data_iso(v("ENCERRAMENTO"))
            iid = self.bd.inserir("incidentes", campos)
            self.hist.append(("incidentes", iid, situacao))
            for chave, titulo in N.PROVIDENCIAS.items():
                if prov and norm(chave) in norm(prov):
                    self.bd.inserir("tarefas", dict(titulo=titulo, tipo="NOTIFICACAO",
                                                    processo_id=pid, incidente_id=iid,
                                                    grupo="Jurídico", origem="MIGRACAO",
                                                    texto_original=prov))
        elif destino_rev == "PROCESSO":
            self.bd.executar("UPDATE processos SET revogou_patrono_anterior=%s, revogacao_em=%s "
                             "WHERE id=%s", (valor_rev, data_iso(v("DATA REVOG")), pid))
        elif destino_rev == "TAREFA":
            self.bd.inserir("tarefas", dict(titulo=valor_rev, tipo="OUTRO", processo_id=pid,
                                            grupo="Jurídico", origem="MIGRACAO",
                                            texto_original=txt(v("REVOGAÇÃO"))))
        self.anotar(av_rev, "processos", pid, rec, origem_a="REVOGAÇÃO")

        # --- o andamento necessário: tarefa, que é o que sempre foi
        andamento = txt(v("AND. NECESSÁRIO"))
        if andamento:
            titulo = N.AND_NECESSARIO.get(andamento, "__livre__")
            if titulo == "__livre__":
                titulo = (andamento[:57] + "…") if len(andamento) > 58 else andamento
            if titulo:
                self.bd.inserir("tarefas", dict(titulo=titulo, tipo="ANDAMENTO", processo_id=pid,
                                                grupo="Jurídico", origem="MIGRACAO",
                                                texto_original=andamento))
        if txt(v("OBSERVACOES")):
            self.bd.inserir("anotacoes", dict(processo_id=pid, texto=txt(v("OBSERVACOES")),
                                              origem="MIGRACAO", campo_origem="OBSERVACOES"))
        # os atributos da reclamada que estavam na ficha do processo
        self.atributos_da_empresa(fc, fp, rec)
        self.disparos({**fc, **{k: x for k, x in fp.items() if x}}, rec, processo_id=pid)

    def atributos_da_empresa(self, fc, fp, rec):
        eid = self.empresa.get(um_link(fc, "EMPRESA") or um_link(fp, "EMPRESA"))
        if not eid:
            return
        hist, _ = N._traduz(N.HIST_PAGAMENTO, (campo(fc, "HIST. PAGAMENTO") or [None])[0]
                            if isinstance(campo(fc, "HIST. PAGAMENTO"), list)
                            else campo(fc, "HIST. PAGAMENTO"), "hist_pagamento")
        bens_v = campo(fc, "BENS IDENTIFICADOS") or campo(fp, "BENS IDENTIFICADOS")
        bens, _ = N._traduz(N.SIM_NAO, bens_v[0] if isinstance(bens_v, list) else bens_v,
                            "bens_identificados")
        if hist is not None:
            self.bd.executar("UPDATE empresas SET hist_pagamento=COALESCE(hist_pagamento,%s) "
                             "WHERE id=%s", (hist, eid))
        if bens is not None:
            self.bd.executar("UPDATE empresas SET bens_identificados=COALESCE(bens_identificados,%s) "
                             "WHERE id=%s", (bens, eid))

    # ---------------------------------------------------------- 5. o pós
    def pos_processual(self):
        """O PÓS não é entidade: é recebimento, repasse e arquivo do processo.

        O casamento por CNJ usa o mapa em MEMÓRIA (`processo_por_cnj`), não um
        SELECT: em modo `--sql-saida` não há banco para perguntar, e o SQL
        gerado tem de produzir o MESMO banco que a carga direta — senão o plano B
        (subir por `apply_migration`) entregaria PÓS sem processo e faltantes
        sem ligação, calado."""
        por_cnj = self.processo_por_cnj
        for r in self._corta(ler("pos_processual")):
            f = r["fields"]
            pid = self.processo.get(um_link(f, "PROCESSUAL")) or por_cnj.get(self._cnj(f))
            if not pid:
                self.anotar(aviso("LINK_QUEBRADO", "processo_id", "(sem processo)",
                                  "registro do PÓS PROCESSUAL sem link e sem número que case"),
                            "recebimentos", None, r["id"], origem_a="PÓS PROCESSUAL")
                continue
            for base, nome in (("CLIENTE", "VALOR RECEBIDO CLIENTE"),
                               ("HONORARIOS", "VALOR HONORARIOS"),
                               ("SUCUMBENCIA", "VALOR SUCUMBENCIA")):
                c = centavos(campo(f, nome))
                if c:
                    self.bd.executar(
                        "INSERT INTO recebimentos (id, processo_id, base, valor_centavos, airtable_bruto) "
                        "OVERRIDING SYSTEM VALUE VALUES (%s,%s,%s,%s,%s) "
                        "ON CONFLICT (processo_id, base) DO NOTHING",
                        (self.bd.seq["recebimentos"] + 1, pid, base, c,
                         json.dumps({"origem": "PÓS PROCESSUAL"}, ensure_ascii=False)))
                    self.bd.seq["recebimentos"] += 1
            arq = N.STATUS_ARQUIVAMENTO.get(campo(f, "STATUS ARQUIVAMENTO"))
            if arq and arq[0] == "DATA":
                self.bd.executar("UPDATE processos SET arquivado_em=COALESCE(arquivado_em, "
                                 "encerrado_em) WHERE id=%s", (pid,))
            elif arq and arq[0] == "TAREFA":
                self.bd.inserir("tarefas", dict(titulo=arq[1], tipo="ARQUIVAMENTO", processo_id=pid,
                                                responsavel_id=self.pessoa.get(um_link(f, "RESPONSAVEL")),
                                                grupo="Jurídico", origem="MIGRACAO"))
            if txt(campo(f, "RESULTADO FINAL")):
                self.bd.executar("UPDATE processos SET resultado_texto=COALESCE(resultado_texto,%s) "
                                 "WHERE id=%s", (txt(campo(f, "RESULTADO FINAL")), pid))

    # ---------------------------------------------------------- 6. testemunhas
    def testemunhas(self):
        for r in self._corta(ler("testemunhas")):
            f = r["fields"]
            nome = txt(campo(f, "NOME TESTEMUNHA"))
            av_nome = None
            if not nome:
                # a carga real tem 2 registros sem nome (status, origem e um link
                # com processo, mais nada). Pular seria perder linha — e o link.
                # Entram com nome de aviso e conferência, para gente decidir.
                nome = "(sem nome na origem)"
                av_nome = aviso("VALOR_SEM_TRADUCAO", "nome", "(vazio)",
                                "registro de TESTEMUNHAS sem NOME TESTEMUNHA: entrou para não "
                                "perder o vínculo e o status; confira se é lixo ou cadastro incompleto")
            vinc, av_v = N._traduz(N.VINCULO, campo(f, "VINCULO"), "vinculo")
            sit, av_s = N._traduz(N.STATUS_TESTEMUNHA, campo(f, "STATUS TESTEMUNHA"), "situacao")
            cob, _ = N._traduz(N.COBRANCA, campo(f, "COBRANÇA"), "cobrancas")
            tem, _ = N._traduz(N.SIM_NAO, campo(f, "TEM PROCESSO?"), "tem_processo")
            trab, _ = N._traduz(N.SIM_NAO, campo(f, "AINDA TRABALHA NA EMPRESA?"), "ainda_trabalha")
            dup, _ = N._traduz(N.SIM_NAO, campo(f, "DUPLICADO?"), "duplicado")
            tid = self.bd.inserir("testemunhas", dict(
                nome=nome, nome_norm=norm(nome),
                telefone=so_digitos(campo(f, "TELEFONE TESTEMUNHA")),
                cpf=so_digitos(campo(f, "CPF")), endereco=txt(campo(f, "ENDEREÇO")),
                empresa_id=self.empresa.get(um_link(f, "EMPRESA")),
                captador_id=self.pessoa.get(um_link(f, "CAPTADOR")),
                vinculo=vinc, admissao_em=data_iso(campo(f, "DATA DE ADMISSÃO")),
                horario_trabalho=txt(campo(f, "HORARIO DE TRABALHO")),
                ainda_trabalha=trab, demissao_em=data_iso(campo(f, "DATA DE DEMISSÃO")),
                tem_processo=tem, situacao=sit or "PENDENTE",
                confirmada_em=(data_iso(campo(f, "DATA ULTIMO CONTATO")) if sit == "CONFIRMADA" else None),
                cobrancas=cob or 0, ultimo_contato_em=data_iso(campo(f, "DATA ULTIMO CONTATO")),
                duplicado=dup,
                origem=N.ORIGEM_TESTEMUNHA.get(txt(campo(f, "origem_testemunha"))),
                origem_registro_id=txt(campo(f, "origem_comercial_registro_id")),
                airtable_record_id=r["id"], airtable_tabela="TESTEMUNHAS", airtable_bruto=f))
            self.testemunha[r["id"]] = tid
            for a in (av_nome, av_v, av_s):
                self.anotar(a, "testemunhas", tid, r["id"], origem_a="TESTEMUNHAS")
            for rec_p in link(f, "TESTEMUNHA DE:"):
                if self.processo.get(rec_p):
                    self.bd.inserir("testemunha_vinculos", dict(
                        testemunha_id=tid, processo_id=self.processo[rec_p],
                        observacao=txt(campo(f, "ENCONTROU NOSSO CLIENTE NA ETAPA PROCESSUAL"))))
            for rec_c in link(f, "TESTEMUNHA DE"):
                if self.cliente.get(rec_c):
                    self.bd.inserir("testemunha_vinculos", dict(
                        testemunha_id=tid, cliente_id=self.cliente[rec_c]))
            for i in range(cob or 0):
                self.bd.inserir("contatos", dict(
                    testemunha_id=tid, em=data_iso(campo(f, "DATA ULTIMO CONTATO")),
                    canal="TELEFONE", origem="MIGRACAO", resultado="cobrança %d" % (i + 1)))
            if txt(campo(f, "OBSERVACOES")):
                self.bd.inserir("anotacoes", dict(testemunha_id=tid,
                                                  texto=txt(campo(f, "OBSERVACOES")),
                                                  origem="MIGRACAO", campo_origem="OBSERVACOES"))
            self.anexos(f, "ARQUIVOS ENVIADOS PELA TESTEMUNHA", dict(testemunha_id=tid), r["id"])
            self.disparos(f, r["id"], testemunha_id=tid)
            if txt(campo(f, "notif_captador_status")):
                self.bd.inserir("automacao_log", dict(
                    automacao="NOTIFICAR_CAPTADOR", chave=r["id"], resultado="MIGRADO",
                    detalhe=txt(campo(f, "notif_captador_status")), origem="N8N",
                    testemunha_id=tid, em=datahora_iso(campo(f, "notif_captador_ultimo_envio"))))

    def auditoria_testemunhas(self):
        for r in self._corta(ler("auditoria_testemunhas")):
            f = r["fields"]
            self.bd.inserir("testemunha_auditoria", dict(
                evento_id=txt(campo(f, "EVENTO ID")), em=txt(campo(f, "DATA/HORA")),
                ator_record_id=txt(campo(f, "ATOR RECORD ID")),
                ator_nome=txt(campo(f, "ATOR NOME SNAPSHOT")),
                setor=txt(campo(f, "SETOR SNAPSHOT")), acao=txt(campo(f, "AÇÃO")),
                testemunha_record_id=txt(campo(f, "TESTEMUNHA RECORD ID")),
                testemunha_id=self.testemunha.get(txt(campo(f, "TESTEMUNHA RECORD ID"))),
                testemunha_nome=txt(campo(f, "TESTEMUNHA NOME SNAPSHOT")),
                contexto=txt(campo(f, "CONTEXTO")),
                campos_alterados=txt(campo(f, "CAMPOS ALTERADOS")),
                antes=txt(campo(f, "ANTES")), depois=txt(campo(f, "DEPOIS")),
                operation_id=txt(campo(f, "OPERATION ID")), resultado=txt(campo(f, "RESULTADO")),
                origem_sistema=txt(campo(f, "ORIGEM/SISTEMA")),
                airtable_record_id=r["id"], airtable_bruto=f))

    # ---------------------------------------------------------- 7. os faltantes
    def faltantes(self):
        por_cnj = self.processo_por_cnj            # em memória: ver pos_processual()
        for r in self._corta(ler("faltantes")):
            f = r["fields"]
            # a carga real achou aqui um número de processo digitado como VALOR
            valor, av_valor = N.dinheiro(campo(f, "VALOR"), "valor_causa_centavos")
            fid = self.bd.inserir("conferencia_faltantes", dict(
                nome=txt(campo(f, "NOME")), numero_cnj=txt(campo(f, "Nº PROCESSO")),
                empresa_id=self.empresa.get(um_link(f, "EMPRESA")),
                processo_id=por_cnj.get(self._cnj(f)),
                valor_causa_centavos=valor,
                trt=txt(campo(f, "TRT")), vara=txt(campo(f, "VARA")),
                distribuicao_em=data_iso(campo(f, "DISTRIBUIÇÃO")),
                fase_recomendada=txt(campo(f, "FASE RECOMENDADA (DATAJUD)")),
                status_recomendado=txt(campo(f, "STATUS RECOMENDADO (DATAJUD)")),
                ultimo_movimento=txt(campo(f, "ÚLTIMO MOVIMENTO (DATAJUD)")),
                status_processo=txt(campo(f, "STATUS PROCESSO")),
                validar_e_subir=bool(campo(f, "✅ VALIDAR E SUBIR")),
                observacoes=txt(campo(f, "OBSERVAÇÕES")),
                airtable_record_id=r["id"], airtable_tabela="Conferência de Faltantes",
                airtable_bruto=f))
            self.anotar(av_valor, "conferencia_faltantes", fid, r["id"],
                        origem_a="Conferência de Faltantes", grupo="Jurídico")

    # ---------------------------------------------------------- 8. o fecho
    def historico(self):
        """A ficha não nasce sem passado. Uma linha por entidade migrada, com
        `origem = 'MIGRACAO'` — assim o `v_estagnados` sabe desde quando cada
        uma está parada e ninguém confunde carga com trabalho de gente."""
        for entidade, eid, etapa in self.hist:
            self.bd.inserir("historico_etapas", dict(
                entidade=entidade, entidade_id=eid, de=None, para=etapa,
                motivo="carga inicial do Airtable", origem="MIGRACAO"))

    def gravar_conferencias(self, guardadas):
        vistas = set()
        for c in self.conf:
            if c["chave"] in vistas:
                continue
            vistas.add(c["chave"])
            antes = guardadas.get(c["chave"])
            if antes:
                c.update(situacao=antes[1], dono_id=antes[2], anotacao=antes[3],
                         resolvido_em=antes[4], resolvido_por=antes[5])
            self.bd.inserir("conferencias", c)


# ==================================================================== execução

def aplicar_arquivos(bd, arquivos):
    for nome in arquivos:
        caminho = os.path.join(AQUI, nome)
        if not os.path.exists(caminho):
            sys.exit("falta %s" % caminho)
        bd.executar(open(caminho).read())


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--baixar", action="store_true", help="Airtable → dados/*.json (só GET)")
    p.add_argument("--do-conector", action="store_true",
                   help="converte os JSON do conector MCP (--origem) para dados/*.json; ver do_conector.py")
    p.add_argument("--origem", help="pasta com os JSON do conector e o nomes.tsv (com --do-conector)")
    p.add_argument("--recriar", action="store_true", help="apaga o public e refaz do esquema")
    p.add_argument("--amostra", type=int, help="N registros por tabela, para provar o caminho")
    p.add_argument("--sql-saida", help="não conecta: escreve o SQL da carga neste arquivo")
    p.add_argument("--dsn", help="ligação com o Postgres (senão GGV_SUPABASE_TRAB)")
    a = p.parse_args()

    if a.baixar:
        return baixar()
    if a.do_conector:
        if not a.origem:
            sys.exit("--do-conector exige --origem PASTA")
        import do_conector
        return do_conector.converter(a.origem)

    dsn = a.dsn or segredo("GGV_SUPABASE_TRAB")
    if not dsn and not a.sql_saida:
        sys.exit("falta GGV_SUPABASE_TRAB (ou --dsn, ou --sql-saida para só escrever o SQL)")

    bd = Banco(dsn, a.sql_saida)
    inicio = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        if a.recriar:
            bd.executar("DROP SCHEMA IF EXISTS public CASCADE")
            bd.executar("CREATE SCHEMA public")
            aplicar_arquivos(bd, ["esquema.sql", "governanca.sql"])
            bd.executar("ALTER TABLE historico_etapas ADD CONSTRAINT fk_hist_pessoa "
                        "FOREIGN KEY (pessoa_id) REFERENCES pessoas(id) ON DELETE SET NULL")
            bd.executar("ALTER TABLE prazos ADD CONSTRAINT fk_prazo_tipo "
                        "FOREIGN KEY (tipo) REFERENCES prazo_tipos(codigo)")
            # a governança criou cinco tabelas DEPOIS do esquema: RLS de novo,
            # senão o mapa de etapas fica aberto na API pública
            bd.executar("SELECT ligar_rls()")
            guardadas = {}
        else:
            guardadas = bd.limpar()

        bd.governanca(False)                 # a carga do passivo passa por fora
        m = Migracao(bd, a.amostra)
        for passo, funcao in (("equipe", m.equipe), ("empresas", m.empresas),
                              ("fragilidades", m.fragilidades), ("clientes", m.clientes),
                              ("processos", m.processos), ("pós-processual", m.pos_processual),
                              ("testemunhas", m.testemunhas),
                              ("auditoria de testemunhas", m.auditoria_testemunhas),
                              ("faltantes", m.faltantes), ("histórico", m.historico)):
            t0 = time.time()
            funcao()
            print("%-26s %5.1fs" % (passo, time.time() - t0))
        m.gravar_conferencias(guardadas)
        bd.governanca(True)                  # e a regra volta inteira

        resumo = {t: n for t, n in sorted(bd.conta.items())}
        bd.inserir("migracao_execucoes", dict(
            iniciada_em=inicio, terminada_em=time.strftime("%Y-%m-%d %H:%M:%S"),
            fonte="BASE GGV - TRAB V3 (%s)" % BASE,
            versao=("amostra de %d" % a.amostra) if a.amostra else "carga completa",
            resumo=resumo, resultado="OK"))
        bd.acertar_sequencias()   # por último: senão o primeiro cadastro na tela estoura
        bd.fim(True)
    except Exception:
        bd.fim(False)
        raise

    print("-" * 42)
    for t, n in sorted(bd.conta.items()):
        print("%-26s %8d" % (t, n))
    print("-" * 42)
    print("conferências abertas: %d" % len({c["chave"] for c in m.conf}))
    print("\nAgora rode: ./.venv/bin/python conferir.py\n")


if __name__ == "__main__":
    main()
