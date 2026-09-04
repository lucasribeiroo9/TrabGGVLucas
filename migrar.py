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
contas de acesso (`usuarios` — mesmo id, mesmo hash de senha, mesmo papel,
recasadas com a pessoa pelo record do Airtable; vale também com `--recriar`),
a configuração das automações (`automacoes`, que a carga não toca) e o que já
foi decidido em `conferencias` — dono, situação e anotação, recasados pela
`chave`. O que nasce no portal e NÃO sobrevive a uma recarga: prazos,
petições, repasses e parcelas — a carga é para antes de o portal entrar em
uso; depois dela, recarregar exige cópia (pg_dump) antes.

## O que a carga NÃO inventa

Campo sem fonte fica NULL e a tela mostra vazio (regra 3 da casa). A carga não
grava data de homologação, de notificação, de trânsito, de arquivamento nem de
confirmação de testemunha que a origem não tem; o FATO fica onde cabe (situação
da execução, booleano, situação do incidente) e a data fica em branco. O
histórico de etapas recebe a melhor data que a origem oferece e, na falta,
a criação do registro no Airtable — nunca a data da carga. O "hoje" da carga
é `data_referencia()`: a data em que a origem foi lida, gravada no dump.
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


def data_referencia():
    """O 'hoje' da carga: a data em que a origem foi lida (`baixado_em` do
    dump da CÓPIA). Audiência anterior a ela é passado; histórico não pode ser
    posterior a ela. Sai do dump, não do relógio, para `migrar.py` e
    `conferir.py` concordarem mesmo rodando em dias diferentes."""
    caminho = os.path.join(DADOS, "copia.json")
    if not os.path.exists(caminho):
        return time.strftime("%Y-%m-%d")
    with open(caminho) as f:
        cabeca = f.read(400)
    m = re.search(r'"baixado_em":\s*"(\d{4}-\d{2}-\d{2})', cabeca)
    return m.group(1) if m else time.strftime("%Y-%m-%d")


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

    def guardar(self):
        """O que gente decidiu e a carga não pode apagar. Lê ANTES de limpar.

        `usuarios` referencia `pessoas`, e o TRUNCATE de `pessoas` é CASCADE:
        sem guardar aqui, a recarga apagava TODAS as contas de acesso (provado
        pelo Auditor: 37 → 0). A pessoa de cada conta é recasada pelo record
        do Airtable, porque o id de `pessoas` muda a cada carga. O mesmo vale
        para o dono e quem resolveu cada conferência decidida.
        """
        g = {"conferencias": {}, "usuarios": []}
        if self.arquivo or self.con is None:
            return g
        try:
            for linha in self.consultar(
                    "SELECT c.chave, c.situacao, c.dono_id, c.anotacao, c.resolvido_em, "
                    "c.resolvido_por, d.airtable_record_id, r.airtable_record_id "
                    "FROM conferencias c LEFT JOIN pessoas d ON d.id = c.dono_id "
                    "LEFT JOIN pessoas r ON r.id = c.resolvido_por WHERE c.situacao <> 'ABERTA'"):
                g["conferencias"][linha[0]] = linha
            for linha in self.consultar(
                    "SELECT u.id, u.email, u.senha_hash, u.papel, u.ativo, u.trocar_senha, "
                    "u.ultimo_acesso, u.criado_em, p.airtable_record_id, p.nome_norm "
                    "FROM usuarios u LEFT JOIN pessoas p ON p.id = u.pessoa_id ORDER BY u.id"):
                g["usuarios"].append(linha)
        except Exception:
            # banco ainda sem as tabelas (primeira carga): não há o que guardar
            self.con.rollback()
        return g

    def limpar(self):
        """Apaga o que a migração escreve e PRESERVA o que gente decidiu."""
        guardadas = self.guardar()
        self.executar("""TRUNCATE processo_alias, testemunha_vinculos, testemunha_auditoria,
            pendencias, peticoes, anotacoes, contatos, eventos, tarefas, documentos,
            acordo_parcelas, acordos, calculos, recebimentos, repasses, decisoes, recursos,
            pericias, prazos, audiencias, incidentes, conferencia_faltantes, processos,
            clientes, testemunhas, fragilidades, empresas, pessoa_papeis, pessoas,
            conferencias, automacao_log, historico_etapas, auditoria RESTART IDENTITY CASCADE""")
        return guardadas

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
        self.pessoa_por_nome = {}          # nome_norm → id (recasa conta cuja pessoa mudou de record)
        self.empresa_nome = {}             # record → nome
        self.empresa_situacao = {}         # record → situação traduzida
        self.empresa_cnpj = defaultdict(lambda: defaultdict(int))   # id → {cnpj: n}
        self.empresa_razao = defaultdict(lambda: defaultdict(int))  # (id, cnpj) → {razão: n}
        self.cliente_assinatura = {}       # id → data (o que a ficha já tem)
        self.cliente_nascimento = {}
        self.cliente_origem = {}           # id → (origem, record)
        self.distribuicao_do_cliente = {}  # id → a menor DISTRIBUIÇAO dos processos dele
        self.hoje = data_referencia()
        self.hist = []                     # dicts: entidade, id, etapa, candidatos, criado

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

    # ---------------------------------------------------------- o histórico
    def _h(self, entidade, eid, etapa, candidatos=(), criado=None):
        """Anota a etapa migrada e as datas que a origem oferece para ela."""
        self.hist.append(dict(entidade=entidade, id=eid, etapa=etapa,
                              candidatos=list(candidatos), criado=criado))

    def quando(self, candidatos, criado):
        """A melhor data que a origem oferece para a etapa atual — e o motivo.

        Percorre os candidatos na ordem dada (o mais próximo da entrada na
        etapa primeiro). Sem nenhum, vale a criação do registro no Airtable,
        dita como tal. NUNCA a data da carga: foi ela que zerou o SLA de 10.183
        registros — `v_estagnados` devolvia 0 linhas para 3.855 processos.
        """
        for rotulo, valor in candidatos:
            d = data_iso(valor)
            if d and "1990-01-01" <= d <= self.hoje:
                return d, "carga inicial do Airtable — data de %s" % rotulo
        d = data_iso(criado)
        if d and d <= self.hoje:
            return d, ("carga inicial do Airtable — a origem não tem a data desta etapa: "
                       "usada a criação do registro no Airtable")
        return self.hoje, ("carga inicial do Airtable — sem data na origem nem criação do "
                           "registro: data em que a origem foi lida")

    def restaurar_usuarios(self, guardadas):
        """As contas voltam como estavam: mesmo id, mesmo hash de senha, mesmo
        papel. A pessoa é recasada pelo record do Airtable (ou pelo nome, se o
        record mudou); quem saiu da origem fica com a conta sem pessoa — não
        sem conta."""
        n = 0
        for (uid, email, senha_hash, papel, ativo, trocar, ultimo, criado, rec,
             nome_norm) in guardadas.get("usuarios", []):
            pid = self.pessoa.get(rec) or self.pessoa_por_nome.get(nome_norm)
            self.bd.executar(
                "INSERT INTO usuarios (id, pessoa_id, email, senha_hash, papel, ativo, "
                "trocar_senha, ultimo_acesso, criado_em) OVERRIDING SYSTEM VALUE "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (uid, pid, email, senha_hash, papel, ativo, trocar, ultimo, criado))
            n += 1
        if n:
            self.bd.conta["usuarios (preservados)"] = n

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
            self.pessoa_por_nome[norm(nome)] = pid
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
            self.empresa_nome[r["id"]] = nome
            self.empresa_situacao[r["id"]] = sit
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
            self._h("clientes", cid, etapa, self.candidatos_cliente(etapa, f), r.get("createdTime"))
            self.cliente_assinatura[cid] = data_iso(campo(f, "DATA DE ASSINATURA"))
            self.cliente_nascimento[cid] = data_iso(campo(f, "NASCIMENTO"))
            self.cliente_origem[cid] = ("PRE PROCESSUAL", r["id"])
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

    @staticmethod
    def candidatos_cliente(etapa, f):
        """As datas que a origem oferece para a etapa atual da ficha, da mais
        próxima da entrada na etapa para a mais distante. DISTRIBUIDO ganha,
        em `historico()`, a DISTRIBUIÇAO do processo — que só se conhece
        depois de carregar os processos. As saídas (cancelado, prescrito,
        stand by, sem resposta) não têm data na origem: vale a criação."""
        assinatura = ("DATA DE ASSINATURA", campo(f, "DATA DE ASSINATURA"))
        entrevista = ("DATA ENTREVISTA", campo(f, "DATA ENTREVISTA"))
        if etapa in ("LEAD", "DOCUMENTACAO", "ENTREVISTA"):
            return [assinatura]
        if etapa.startswith("PETICAO") or etapa == "DISTRIBUIDO":
            return [entrevista, assinatura]
        return []

    def cadastro_incompleto(self):
        """O que a ficha ainda não tem e a origem — PRÉ, CÓPIA ou PROCESSUAL —
        também não tinha: pendência com tipo, não conferência genérica. Sem
        data de assinatura, o contrato de honorários não está registrado
        (DOCUMENTO/CONTRATO, obrigatório). Sem nascimento, é dado de cadastro
        (CADASTRO). Roda DEPOIS dos processos, porque a CÓPIA completa a ficha
        da PRÉ: 1.556 fichas dos autos nasciam sem assinatura tendo-a nos autos."""
        for cid, (origem, rec) in self.cliente_origem.items():
            if not self.cliente_assinatura.get(cid):
                self.bd.inserir("pendencias", dict(
                    cliente_id=cid, tipo="DOCUMENTO", documento_tipo="CONTRATO", obrigatorio=True,
                    descricao="contrato de honorários: sem data de assinatura na origem (%s)" % origem,
                    origem="MIGRACAO", grupo="Documentação", airtable_record_id=rec))
            if not self.cliente_nascimento.get(cid):
                self.bd.inserir("pendencias", dict(
                    cliente_id=cid, tipo="CADASTRO", obrigatorio=False,
                    descricao="data de nascimento: não consta na origem (%s)" % origem,
                    origem="MIGRACAO", grupo="Documentação", airtable_record_id=rec))

    def completar_ficha(self, cid, fc, fp):
        """A CÓPIA (e a PROCESSUAL) completam o que a ficha não tinha: data de
        assinatura e nascimento. Só onde está vazio — a PRÉ, quando tem, vence."""
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        assinatura = data_iso(v("ASSINATURA"))
        nasc, _ = data_br(v("NASCIMENTO"), "nascimento_parte")
        if assinatura and not self.cliente_assinatura.get(cid):
            self.bd.executar("UPDATE clientes SET data_assinatura_contrato=%s WHERE id=%s",
                             (assinatura, cid))
            self.cliente_assinatura[cid] = assinatura
        if nasc and not self.cliente_nascimento.get(cid):
            self.bd.executar("UPDATE clientes SET data_nascimento=%s WHERE id=%s", (nasc, cid))
            self.cliente_nascimento[cid] = nasc

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
               "DECISAO SENTENCA", "ENCERRAMENTO", "STATUS ACORDO", "EMPRESA")

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
        st, _ = N._traduz(N.STATUS_PROCESSO, st_proc, "fase")
        if not fase and not (st and st[0] in ("FASE", "RESULTADO")):
            # 58 registros só da PROCESSUAL, sem número, sem fase e sem status:
            # entram na etapa inicial, mas isso é decisão da carga, e fica dito
            avisos.append(aviso("VALOR_SEM_TRADUCAO", "fase", "(vazio)",
                                "sem FASE PROCESSUAL e sem STATUS DO PROCESSO que diga a fase: "
                                "entrou em CONHECIMENTO, a etapa inicial [CONFIRMAR]"))
        fase = fase or "CONHECIMENTO"
        resultado_final = incidente_situacao = None
        if st:
            destino, valor_st = st
            if destino == "FASE" and valor_st == "SOBRESTADO":
                fase = "SOBRESTADO"
            elif destino == "RESULTADO":
                resultado_final, fase = valor_st, "ENCERRADO"
            elif destino == "INCIDENTE":
                incidente_situacao = valor_st
        # AUSÊNCIA do reclamante arquiva (art. 844 CLT): o processo encerrado por
        # ausência ganha o resultado que diz isso — é perda evitável e precisa
        # ser medida. Onde a fase discorda, ninguém encerra em silêncio.
        st_conh = N.STATUS_CONHECIMENTO.get(v("STATUS CONHECIMENTO")) or (None, None)
        if st_conh[0] == "AUSENCIA":
            if fase == "ENCERRADO" and resultado_final in (None, "ARQUIVADO"):
                resultado_final = st_conh[1]
            else:
                avisos.append(aviso("DIVERGENCIA_FONTE", "resultado_final", "AUSÊNCIA",
                                    "STATUS CONHECIMENTO diz ausência (arquivamento, art. 844 CLT), "
                                    "mas a fase é %s e o resultado %s: não se encerrou em silêncio"
                                    % (fase, resultado_final or "(vazio)")))
        return fase, resultado_final, incidente_situacao, transito, avisos

    def completar_execucao(self, fc, fp, fase, sit, orig):
        """STATUS EXECUÇÃO manda. Onde ele calou, STATUS CumPrSe, depois STATUS
        DO CALCULO, depois STATUS PAGAMENTO completam a situação da execução —
        do mais específico ao mais genérico, cada um só onde o anterior não
        disse nada. Estes três de/para existiam em `normalizar.py` e a carga
        nunca os aplicava (0 linhas no banco, apontado pelo Auditor). Onde o
        CumPrSe discorda do STATUS EXECUÇÃO abre conferência; o cálculo e o
        pagamento são campos mais grossos e não contradizem, só completam.

        Devolve (situacao, original, avisos, credito_cedido). O `conferir.py`
        recalcula esta mesma função da origem.
        """
        avisos, credito = [], False
        for nome, tabela in (("STATUS CumPrSe", N.STATUS_CUMPRSE),
                             ("STATUS DO CALCULO", N.STATUS_CALCULO),
                             ("STATUS PAGAMENTO", N.STATUS_PAGAMENTO)):
            bruto = self.valor(fc, fp, nome)
            par, av = N._traduz(tabela, bruto, "situacao_execucao")
            if av:
                avisos.append(av)
                continue
            if not par:
                continue
            destino, valor = par
            if destino == "CESSAO":
                credito = True
            elif destino == "SIT":
                if sit is None:
                    # o texto do STATUS EXECUÇÃO, quando havia, continua no _original
                    sit = valor
                    orig = ("%s | " % orig if orig else "") + "%s: %s" % (nome, txt(bruto))
                elif sit != valor and nome == "STATUS CumPrSe":
                    avisos.append(aviso("DIVERGENCIA_FONTE", "situacao_execucao",
                                        "%s = %s" % (nome, txt(bruto)),
                                        "STATUS EXECUÇÃO diz %s e %s diz %s: ficou o STATUS "
                                        "EXECUÇÃO, que a equipe edita hoje" % (sit, nome, valor)))
            elif destino == "FASE" and fase != valor:
                avisos.append(aviso("DIVERGENCIA_FONTE", "fase", "%s = %s" % (nome, txt(bruto)),
                                    "%s diz fase %s, mas a fase gravada é %s" % (nome, valor, fase)))
        return sit, orig, avisos, credito

    def revogacao_destino(self, fc, fp, st_proc, incidente_situacao):
        """Onde vai REVOGAÇÃO e onde vai DATA REVOG.

        Sentido 2 (o CLIENTE nos revogou): o STATUS DO PROCESSO diz ROUBADO /
        RECEBIDO POR ELES / RECUPERADO, ou a REVOGAÇÃO diz ROUBADO — aí a data
        é do incidente (`revogacao_nos_autos_em`). Em qualquer outro caso é o
        sentido 1 (NÓS juntamos a revogação do patrono anterior) e a data é do
        processo (`revogacao_em`), esteja a REVOGAÇÃO preenchida ou não. A
        DATA REVOG nunca fica sem coluna: eram 648 processos com a data só no
        bruto. REVOGAÇÃO = NÃO com data é contradição da origem: grava-se e
        abre-se conferência. [CONFIRMAR pergunta 20.]

        Devolve (destino, valor, avisos, data, onde).
        """
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        destino, valor, av = N.revogacao(v("REVOGAÇÃO"), st_proc)
        avisos = [av] if av else []
        data = data_iso(v("DATA REVOG"))
        onde = "INCIDENTE" if (incidente_situacao or destino == "INCIDENTE") else "PROCESSO"
        if data and destino == "PROCESSO" and valor is False:
            avisos.append(aviso("DIVERGENCIA_FONTE", "DATA REVOG", "REVOGAÇÃO = NÃO",
                                "há DATA REVOG (%s) num registro cuja REVOGAÇÃO diz NÃO: a data "
                                "foi gravada no %s e o sinal ficou como estava [CONFIRMAR 20]"
                                % (data, "incidente" if onde == "INCIDENTE" else "processo")))
        return destino, valor, avisos, data, onde

    def situacao_audiencia(self, fc, fp, fase, tipo):
        """A situação com que a audiência migrada nasce — pela EVIDÊNCIA.

        A carga anterior gravava toda audiência como DESIGNADA, e 2.649 do
        passado entravam na pauta como pendentes (Auditor). Aqui: ausência do
        reclamante → NAO_REALIZADA; data futura ou sem data → DESIGNADA; data
        passada com decisão, acordo ou encerramento POSTERIOR na origem, ou
        instrução já encerrada, ou processo já além do conhecimento →
        REALIZADA, com a evidência escrita; data passada sem nada disso →
        REALIZADA com conferência AUDIENCIA_SEM_RESULTADO, porque a máquina
        não tem etapa "não sei" (o mesmo remédio de `fase_execucao`). O
        `conferir.py` recalcula esta função da origem.

        Devolve (situacao, motivo, evidencia, aviso).
        """
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        st_conh_bruto = v("STATUS CONHECIMENTO")
        st_conh = N.STATUS_CONHECIMENTO.get(st_conh_bruto) or (None, None)
        if st_conh[0] == "AUSENCIA":
            return "NAO_REALIZADA", "AUSENCIA_RECLAMANTE", "STATUS CONHECIMENTO = AUSÊNCIA", None
        data = (datahora_iso(v("DATA AUDIENCIA")) or "")[:10]
        if not data or data >= self.hoje:
            return "DESIGNADA", None, None, None
        for rotulo, valor in (("sentença", campo(fc, "DATA SENTENCA")),
                              ("acórdão", v("DATA ACORDAO")),
                              ("acordo", campo(fc, "DATA DO ACORDO")),
                              ("encerramento", v("ENCERRAMENTO"))):
            d = data_iso(valor)
            if d and d >= data:
                return "REALIZADA", None, "%s em %s, depois da audiência" % (rotulo, d), None
        if st_conh[0] == "DECISAO" or norm(st_conh_bruto) == "AGUARDANDO SENTENCA":
            return ("REALIZADA", None,
                    "STATUS CONHECIMENTO = %s (instrução encerrada)" % txt(st_conh_bruto), None)
        if fase in ("RECURSAL", "EXECUCAO_PROVISORIA", "EXECUCAO_DEFINITIVA", "RECEBENDO") \
                and tipo != "CONCILIACAO_EXECUCAO":
            return "REALIZADA", None, "processo já em %s" % fase, None
        return "REALIZADA", None, None, aviso(
            "AUDIENCIA_SEM_RESULTADO", "situacao", data,
            "audiência (%s) em %s, no passado, sem resultado, decisão, acordo ou encerramento "
            "posterior na origem: entrou como REALIZADA [CONFIRMAR: aconteceu? qual o resultado?]"
            % (tipo or "tipo não informado", data))

    def candidatos_processo(self, fase, fc, fp):
        """As datas que a origem oferece para a fase atual, da mais próxima da
        entrada na fase para a mais distante."""
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        dist = [("DISTRIBUIÇAO", v("DISTRIBUIÇAO")), ("AÇÃO", v("AÇÃO"))]
        sent = ("DATA SENTENCA", campo(fc, "DATA SENTENCA"))
        acor = ("DATA ACORDAO", v("DATA ACORDAO"))
        acordo = ("DATA DO ACORDO", campo(fc, "DATA DO ACORDO"))
        enc = ("ENCERRAMENTO", v("ENCERRAMENTO"))
        if fase in ("RECURSAL", "EXECUCAO_PROVISORIA"):
            return [sent] + dist
        if fase == "EXECUCAO_DEFINITIVA":
            return [acor, sent] + dist
        if fase == "ACORDO":
            return [acordo, sent] + dist
        if fase == "RECEBENDO":
            return [acordo, acor, sent] + dist
        if fase in ("ENCERRADO", "DESISTENCIA"):
            return [enc, ("ARQUIVO TST", campo(fc, "ARQUIVO TST")), acor, sent, acordo] + dist
        if fase == "SOBRESTADO":
            return [("ULTIMA MOV", v("ULTIMA MOV")), acor, sent] + dist
        return dist

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
            sit_exec, sit_orig, avs_exec, credito = self.completar_execucao(
                fc, fp, fase, sit_exec, sit_orig)
            pct, av_pct = N.percentual(v("SUCUMBENCIA %"))
            cnpj, razao = N.cnpj_razao(campo(fc, "CNPJ RECLAMADA"))
            nasc, av_nasc = data_br(v("NASCIMENTO"), "nascimento_parte")
            valor_causa, av_valor = N.dinheiro(v("VALOR"), "valor_causa_centavos")
            complexidade = txt(v("COMPLEXIDADE"))
            ultima_mov = txt(v("ULTIMA MOV"))
            mov_em = (ultima_mov or "")[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", ultima_mov or "") else None
            criado = (copia_r or proc_r).get("createdTime")
            rec_emp = um_link(fc, "EMPRESA") or um_link(fp, "EMPRESA")
            eid = self.empresa.get(rec_emp)

            cliente_id, av_cli = self.achar_cliente(fc, fp, criado)
            self.completar_ficha(cliente_id, fc, fp)
            pid = self.bd.inserir("processos", dict(
                cliente_id=cliente_id, fase=fase,
                numero_cnj=txt(v("Nº PROCESSO")),
                nome_parte=txt(v("NOME")), cpf_parte=so_digitos(campo(fc, "CPF")),
                email_parte=txt(campo(fc, "E-MAIL")),
                telefone_parte=so_digitos(v("TELEFONE")), nascimento_parte=nasc,
                empresa_id=eid,
                cnpj_reclamada=cnpj, razao_social_reclamada=razao,
                trt=trt_, vara=txt(v("VARA")), turma=turma_,
                cadeira=txt(campo(fc, "CADEIRA")), relator=txt(campo(fc, "RELATOR")),
                turma_tst=txt(campo(fc, "TURMA TST")), relator_tst=txt(campo(fc, "RELATOR TST")),
                arquivo_tst_em=data_iso(campo(fc, "ARQUIVO TST")),
                tel_vara=txt(v("TEL VARA")),
                rito=rito, classe_cnj=classe, classe_incidente=classe_inc,
                valor_causa_centavos=valor_causa,
                complexidade=complexidade,
                # A/B/C sai do valor (docs/de-para.md); onde alguém decidiu diferente,
                # a decisão vence e fica marcada. Na carga real: 0 casos.
                complexidade_manual=bool(complexidade and valor_causa is not None
                                         and N.complexidade_da_faixa(valor_causa) != complexidade),
                credito_cedido=credito,
                distribuicao_em=data_iso(v("DISTRIBUIÇAO")),
                ajuizamento_em=data_iso(v("AÇÃO")), assinatura_em=data_iso(v("ASSINATURA")),
                advogado_id=self.pessoa.get(um_link(fc, "ADVOGADO") or um_link(fp, "ADVOGADO")),
                captador_id=self.pessoa.get(um_link(fc, "CAPTADOR") or um_link(fp, "CAPTADOR")),
                situacao_execucao=sit_exec, situacao_execucao_original=sit_orig,
                numero_cumprse=cumprse,
                # STATUS DO PROCESSO diz que transitou; a DATA do trânsito a
                # origem não tem — e a data da sentença não é ela. Fica NULL,
                # e o fato vai para uma anotação na ficha (abaixo).
                transito_em=None,
                resultado_final=resultado_final, resultado_texto=txt(v("RESULTADO")),
                encerrado_em=data_iso(v("ENCERRAMENTO")),
                sucumbencia_percent=pct,
                pericia_medica=bool(v("PERICIA MEDICA")), pericia_tecnica=bool(v("PERICIA TECNICA")),
                ultima_movimentacao=ultima_mov, ultima_movimentacao_em=mov_em,
                drive_url=txt(v("DRIVE")), astrea_url=txt(v("ASTREA")),
                airtable_record_id=rec_copia, airtable_record_id_processual=rec_proc,
                airtable_tabela=("CÓPIA DA PROCESSUAL" if rec_copia else "PROCESSUAL"),
                airtable_bruto={"copia": fc, "processual": fp},
                # na PROCESSUAL o campo "Created By" é lastModifiedTime com nome errado
                atualizado_em=datahora_iso(campo(fp, "Created By"))
                if isinstance(campo(fp, "Created By"), str) else None,
                criado_em=datahora_iso(criado)))
            self.processo[rec_copia or rec_proc] = pid
            if rec_proc:
                self.processo[rec_proc] = pid
            cnj = so_digitos(v("Nº PROCESSO"))
            if cnj:
                self.processo_por_cnj.setdefault(cnj, pid)
            self._h("processos", pid, fase, self.candidatos_processo(fase, fc, fp), criado)
            dist = data_iso(v("DISTRIBUIÇAO"))
            if dist and (cliente_id not in self.distribuicao_do_cliente
                         or dist < self.distribuicao_do_cliente[cliente_id]):
                self.distribuicao_do_cliente[cliente_id] = dist
            if transito:
                self.bd.inserir("anotacoes", dict(
                    processo_id=pid, origem="MIGRACAO", campo_origem="STATUS DO PROCESSO",
                    texto="Trânsito em julgado registrado na origem (STATUS DO PROCESSO = TRÂNSITO "
                          "EM JULGADO), sem data. [CONFIRMAR: data do trânsito]"))
            if eid and cnpj:
                self.empresa_cnpj[eid][cnpj] += 1
                if razao:
                    self.empresa_razao[(eid, cnpj)][razao] += 1
            for a in [av_cl, av_trt, av_turma, av_exec, av_pct, av_cli, av_nasc, av_valor] + avs_exec:
                self.anotar(a, "processos", pid, rec_copia or rec_proc,
                            origem_a="CÓPIA" if rec_copia else "PROCESSUAL", grupo="Jurídico")
            self.situacao_da_empresa(pid, fc, fp, rec_copia or rec_proc)
            self.divergencias(pid, fc, fp, rec_copia)
            self.filhos_do_processo(pid, fc, fp, rec_copia or rec_proc, st_proc,
                                    incidente_situacao, criado)
        self.cnpj_das_empresas()

    def situacao_da_empresa(self, pid, fc, fp, rec):
        """SITU. EMPRESA é lookup do STATUS EMPRESA da reclamada ligada. Quando
        os dois lados apontam para reclamadas diferentes, a divergência é do
        LINK (conferência EMPRESA, em `divergencias`), não da situação. Só
        quando o link é o mesmo e o lookup ainda discorda do cadastro é que a
        situação está desatualizada em algum lugar — e isso vira conferência."""
        a, b = um_link(fc, "EMPRESA"), um_link(fp, "EMPRESA")
        if a and b and a != b:
            return
        rec_emp = a or b
        lk = self.valor(fc, fp, "SITU. EMPRESA")
        lk = lk[0] if isinstance(lk, list) and lk else lk
        if not (rec_emp and lk and rec_emp in self.empresa):
            return
        sit, _ = N._traduz(N.SITUACAO_EMPRESA, lk, "situacao")
        if sit and sit != self.empresa_situacao.get(rec_emp):
            self.anotar(aviso("DIVERGENCIA_FONTE", "SITU. EMPRESA", txt(lk),
                              "o lookup do processo diz %s e o cadastro da reclamada diz %s"
                              % (sit, self.empresa_situacao.get(rec_emp) or "(vazio)")),
                        "processos", pid, rec, origem_a="lookup do processo",
                        valor_b=self.empresa_situacao.get(rec_emp), origem_b="EMPRESAS",
                        escolhido=self.empresa_situacao.get(rec_emp), grupo="Jurídico")

    def cnpj_das_empresas(self):
        """O CNPJ da reclamada vem da CÓPIA, no processo. Sobe para a empresa
        quando é INEQUÍVOCO: todos os processos da empresa trazem o mesmo CNPJ.
        Empresa com mais de um CNPJ (filiais, ou cadastro que mistura duas) não
        recebe nenhum e abre EMPRESA_AMBIGUA; o mesmo CNPJ em mais de um
        cadastro de empresa é duplicidade, e também abre. A razão social só
        sobe quando é uma só."""
        por_cnpj = defaultdict(set)
        for eid, cnpjs in self.empresa_cnpj.items():
            for c in cnpjs:
                por_cnpj[c].add(eid)
        for eid, cnpjs in sorted(self.empresa_cnpj.items()):
            if len(cnpjs) == 1:
                cnpj = next(iter(cnpjs))
                razoes = self.empresa_razao.get((eid, cnpj), {})
                self.bd.executar("UPDATE empresas SET cnpj=%s, razao_social=%s WHERE id=%s",
                                 (cnpj, next(iter(razoes)) if len(razoes) == 1 else None, eid))
            else:
                self.anotar(aviso("EMPRESA_AMBIGUA", "cnpj", "%d CNPJs distintos" % len(cnpjs),
                                  "os processos desta reclamada trazem CNPJs diferentes (%s): "
                                  "nenhum subiu para o cadastro" % ", ".join(
                                      "%s ×%d" % (c, n) for c, n in sorted(cnpjs.items()))),
                            "empresas", eid, grupo="Jurídico")
        for cnpj, eids in sorted(por_cnpj.items()):
            if len(eids) > 1:
                self.anotar(aviso("EMPRESA_AMBIGUA", "cnpj", cnpj,
                                  "o mesmo CNPJ aparece nos processos de %d cadastros de empresa "
                                  "(ids %s): cadastro repetido?" % (len(eids), ", ".join(map(str, sorted(eids))))),
                            "empresas", min(eids), grupo="Jurídico")

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
            if nome == "EMPRESA":
                # link: compara o record e mostra o NOME de cada lado — 423
                # processos apontam para reclamadas diferentes nas duas tabelas
                a, b = um_link(fc, nome), um_link(fp, nome)
                if a and b and a != b:
                    self.anotar(aviso("DIVERGENCIA_FONTE", nome, self.empresa_nome.get(a, a),
                                      "a CÓPIA e a PROCESSUAL ligam o processo a reclamadas diferentes"),
                                "processos", pid, rec, origem_a="CÓPIA",
                                valor_b=self.empresa_nome.get(b, b), origem_b="PROCESSUAL",
                                escolhido=self.empresa_nome.get(a, a), grupo="Jurídico")
                continue
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

    def dono_do_processo(self, fc, fp):
        """A regra de quem é o cliente do processo, do mais forte para o mais
        fraco: o link vivo da PROCESSUAL, o CPF dos autos, o nome. Devolve
        ('ACHOU', id, None) ou ('NOVO', None, aviso). Pura: não escreve — o
        `conferir.py` a repete da origem para contar as fichas criadas dos autos."""
        rec_pre = um_link(fp, "PRE PROCESSUAL")
        if rec_pre and rec_pre in self.cliente:
            return "ACHOU", self.cliente[rec_pre], None
        cpf = so_digitos(campo(fc, "CPF"))
        if cpf and cpf_valido(cpf) and cpf in self.cliente_por_cpf:
            return "ACHOU", self.cliente_por_cpf[cpf], None
        nome = txt(campo(fc, "NOME") or campo(fp, "NOME"))
        candidatos = self.cliente_por_nome.get(norm(nome or ""), [])
        if len(candidatos) == 1:
            return "ACHOU", candidatos[0], None
        av = None
        if len(candidatos) > 1:
            av = aviso("CLIENTE_AMBIGUO", "cliente_id", nome,
                       "%d fichas com o mesmo nome: o processo ficou com uma ficha nova" % len(candidatos))
        return "NOVO", None, av

    def lembrar_cliente(self, cid, cpf, nome):
        if cpf and cpf_valido(cpf):
            self.cliente_por_cpf.setdefault(cpf, cid)
        if nome:
            self.cliente_por_nome[norm(nome)].append(cid)

    def achar_cliente(self, fc, fp, criado=None):
        """Todo processo tem dono. Do mais forte para o mais fraco:
        o link vivo da PROCESSUAL, o CPF dos autos, o nome + a reclamada.
        O que não é seguro NÃO vira palpite: nasce ficha com origem PROCESSO e
        uma conferência aberta, porque cliente errado é pior que cliente novo.

        A ficha nova leva o que os autos têm: CPF, telefone, e-mail, data de
        assinatura e nascimento (1.556 nasciam sem assinatura e 1.934 sem
        nascimento tendo-os no processo — Auditor). O que a origem não tem
        vira pendência de cadastro em `cadastro_incompleto()`."""
        como, cid, av = self.dono_do_processo(fc, fp)
        if como == "ACHOU":
            return cid, None
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        cpf = so_digitos(campo(fc, "CPF"))
        nome = txt(campo(fc, "NOME") or campo(fp, "NOME"))
        assinatura = data_iso(v("ASSINATURA"))
        nasc, _ = data_br(v("NASCIMENTO"), "nascimento_parte")
        cid = self.bd.inserir("clientes", dict(
            status="DISTRIBUIDO", nome=nome or "(sem nome nos autos)", nome_norm=norm(nome),
            cpf=cpf, cpf_valido=bool(cpf and cpf_valido(cpf)),
            email=txt(campo(fc, "E-MAIL")), telefone=so_digitos(v("TELEFONE")),
            data_assinatura_contrato=assinatura, data_nascimento=nasc,
            empresa_id=self.empresa.get(um_link(fc, "EMPRESA") or um_link(fp, "EMPRESA")),
            origem_cadastro="PROCESSO",
            airtable_tabela="CÓPIA DA PROCESSUAL",
            airtable_bruto={"origem": "ficha criada a partir dos autos"},
            criado_em=datahora_iso(criado)))
        self._h("clientes", cid, "DISTRIBUIDO",
                [("DISTRIBUIÇAO", v("DISTRIBUIÇAO")), ("AÇÃO", v("AÇÃO")), ("ASSINATURA", assinatura)],
                criado)
        self.cliente_assinatura[cid] = assinatura
        self.cliente_nascimento[cid] = nasc
        self.cliente_origem[cid] = ("autos: CÓPIA DA PROCESSUAL", None)
        self.lembrar_cliente(cid, cpf, nome)
        return cid, av

    # ------------------------------------------------ o que pende do processo
    def filhos_do_processo(self, pid, fc, fp, rec, st_proc, incidente_situacao, criado=None):
        v = lambda nome: self.valor(fc, fp, nome)                          # noqa: E731
        fase = self.fase_final(fc, fp)[0]

        # --- audiência: uma LINHA, não um campo sobrescrito; a situação pela evidência
        if v("DATA AUDIENCIA") or v("AUDIENCIA"):
            tipo = mod = rito = None
            par, av = N._traduz(N.AUDIENCIA, v("AUDIENCIA"), "tipo")
            if par:
                tipo, mod, rito = par
            situacao, motivo, evidencia, av_sit = self.situacao_audiencia(fc, fp, fase, tipo)
            aid = self.bd.inserir("audiencias", dict(
                processo_id=pid, situacao=situacao,
                data_hora=datahora_iso(v("DATA AUDIENCIA")), tipo=tipo, modalidade=mod,
                motivo=motivo,
                observacao=(("situação inferida na carga: " + evidencia) if evidencia else
                            (av_sit["prova"] if av_sit else None)),
                advideo_em=datahora_iso(v("DATA ADVIDEO")),
                advideo_responsavel_id=self.pessoa.get(um_link(fp, "RESP ADVIDEO")),
                advideo_previsto=bool(v("STATUS ADVIDEO")),
                airtable_record_id=rec, airtable_tabela="PROCESSUAL",
                airtable_bruto={"AUDIENCIA": v("AUDIENCIA"), "STATUS ADVIDEO": v("STATUS ADVIDEO"),
                                "DATA AUDIENCIA": v("DATA AUDIENCIA"),
                                "STATUS CONHECIMENTO": v("STATUS CONHECIMENTO")}))
            self._h("audiencias", aid, situacao,
                    [("DATA AUDIENCIA", v("DATA AUDIENCIA"))] if situacao != "DESIGNADA" else [],
                    criado)
            self.bd.inserir("eventos", dict(tipo="AUDIENCIA", processo_id=pid, audiencia_id=aid,
                                            data_hora=datahora_iso(v("DATA AUDIENCIA")),
                                            situacao=("REALIZADO" if situacao in ("REALIZADA", "NAO_REALIZADA")
                                                      else "AGENDADO")))
            if rito:
                self.bd.executar("UPDATE processos SET rito=COALESCE(rito,%s) WHERE id=%s", (rito, pid))
            self.anotar(av, "audiencias", aid, rec, origem_a="AUDIENCIA")
            self.anotar(av_sit, "audiencias", aid, rec, origem_a="DATA AUDIENCIA", grupo="Jurídico")

        # --- REDISTRIBUIR: era opção de STATUS DO PROCESSO; é trabalho a fazer
        st = N.STATUS_PROCESSO.get(st_proc) if st_proc else None
        if st and st[0] == "TAREFA":
            self.bd.inserir("tarefas", dict(titulo=st[1], tipo="REDISTRIBUICAO", processo_id=pid,
                                            grupo="Jurídico", origem="MIGRACAO",
                                            texto_original=txt(st_proc)))

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
                # A data da homologação a origem NÃO tem (era gravada a data de
                # ENCERRAMENTO em 411 linhas — inventada). O fato fica dito.
                self.bd.inserir("calculos", dict(
                    processo_id=pid, base=base, valor_centavos=centavos(val),
                    sucumbencia_centavos=centavos(suc), honorario_centavos=centavos(hon),
                    homologado_em=None,
                    observacao=("STATUS DO CALCULO = %s na origem; a data não foi registrada lá"
                                % txt(v("STATUS DO CALCULO")) if st_calc and base == "HOMOLOGADO"
                                else None)))
        st_ac, _ = N._traduz(N.STATUS_ACORDO, v("STATUS ACORDO"), "situacao")
        if st_ac or v("VALOR ACORDO") or campo(fc, "DATA DO ACORDO"):
            # QUEBRA: `quebrado_em` fica NULL — a origem não tem a data da quebra,
            # só o status (docs/de-para.md).
            self.bd.inserir("acordos", dict(
                processo_id=pid, valor_centavos=centavos(v("VALOR ACORDO")),
                honorario_centavos=centavos(campo(fc, "HONOR TOTAL ACORDO")),
                parcelas=v("PARCELAS"),
                valor_parcela_centavos=centavos(campo(fc, "VALOR PARCELA")),
                homologado_em=data_iso(campo(fc, "DATA DO ACORDO")),
                situacao=st_ac or "EM_ANDAMENTO",
                observacao=("as parcelas nascem no portal: a origem só guardava quantas eram"
                            if v("PARCELAS") else None)))
            if not st_ac:
                # acordo com valor ou data e sem status: EM_ANDAMENTO é a etapa
                # inicial da tabela, não um fato da origem — fica dito
                self.anotar(aviso("VALOR_SEM_TRADUCAO", "situacao_acordo", "(vazio)",
                                  "há VALOR ACORDO ou DATA DO ACORDO e nenhum STATUS ACORDO: o acordo "
                                  "nasceu EM_ANDAMENTO, que é o padrão da tabela [CONFIRMAR]"),
                            "acordos", None, rec, origem_a="STATUS ACORDO", grupo="Jurídico")
        for base, valor_bruto in (("TOTAL", v("TOTAL RECEBIDO")),
                                  ("SUCUMBENCIA", v("SUCUMB RECEBIDO")),
                                  ("HONORARIOS", v("HONOR TOTAL"))):
            c = centavos(valor_bruto)
            if c:
                self.bd.inserir("recebimentos", dict(processo_id=pid, base=base, valor_centavos=c))

        # --- o incidente de representação
        destino_rev, valor_rev, avs_rev, data_rev, onde = self.revogacao_destino(
            fc, fp, st_proc, incidente_situacao)
        notif = N.NOTIFICACAO.get(v("NOTIFICAÇÃO"))
        prov = txt(v("PROVIDENCIAS"))
        if incidente_situacao or notif or destino_rev == "INCIDENTE" or prov:
            situacao = incidente_situacao or (notif[0] if notif else "DETECTADO")
            # As datas da notificação (redigida, enviada, recebida, respondida) e
            # do aviso ao cliente a origem NÃO tem — a carga anterior punha a
            # DATA REVOG ou o ENCERRAMENTO nelas (72 inventadas). Ficam NULL; a
            # situação do incidente carrega o fato, e o bruto guarda os campos.
            iid = self.bd.inserir("incidentes", dict(
                processo_id=pid, situacao=situacao, tipo="TROCA_DE_ADVOGADO",
                providencia_texto=prov,
                revogacao_nos_autos_em=(data_rev if onde == "INCIDENTE" else None),
                airtable_bruto={k: v(k) for k in ("STATUS DO PROCESSO", "REVOGAÇÃO", "DATA REVOG",
                                                  "NOTIFICAÇÃO", "PROVIDENCIAS", "CLIENTE AVISADO?")
                                if v(k) not in (None, "", [])}))
            self._h("incidentes", iid, situacao,
                    [("DATA REVOG", data_rev)] if onde == "INCIDENTE" else [], criado)
            for chave, titulo in N.PROVIDENCIAS.items():
                if prov and norm(chave) in norm(prov):
                    self.bd.inserir("tarefas", dict(titulo=titulo, tipo="NOTIFICACAO",
                                                    processo_id=pid, incidente_id=iid,
                                                    grupo="Jurídico", origem="MIGRACAO",
                                                    texto_original=prov))
        # o sentido 1 é do processo, haja ou não incidente por outro motivo
        # (164 processos perdiam o sinal por estarem no `elif` — Auditor)
        if onde == "PROCESSO" and (destino_rev == "PROCESSO" or data_rev):
            self.bd.executar("UPDATE processos SET revogou_patrono_anterior=%s, revogacao_em=%s "
                             "WHERE id=%s",
                             (valor_rev if destino_rev == "PROCESSO" else None, data_rev, pid))
        if destino_rev == "TAREFA":
            self.bd.inserir("tarefas", dict(titulo=valor_rev, tipo="OUTRO", processo_id=pid,
                                            grupo="Jurídico", origem="MIGRACAO",
                                            texto_original=txt(v("REVOGAÇÃO"))))
        for a in avs_rev:
            self.anotar(a, "processos", pid, rec, origem_a="REVOGAÇÃO", grupo="Jurídico")

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
            # o registro do PÓS inteiro vai para o bruto do processo (perda zero)
            self.bd.executar("UPDATE processos SET airtable_bruto = airtable_bruto || %s::jsonb "
                             "WHERE id=%s", (json.dumps({"pos": f}, ensure_ascii=False), pid))
            arq = N.STATUS_ARQUIVAMENTO.get(campo(f, "STATUS ARQUIVAMENTO"))
            if arq and arq[0] == "DATA":
                # "Arquivado" diz o fato; a data a origem não tem (era copiada
                # do encerramento em 37 linhas — inventada). `arquivado_em` fica NULL.
                self.bd.executar("UPDATE processos SET arquivado=true WHERE id=%s", (pid,))
            elif arq and arq[0] == "NADA":
                self.bd.executar("UPDATE processos SET arquivado=false WHERE id=%s", (pid,))
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
                # a data da confirmação a origem não tem; o último contato não é
                # necessariamente ela. Fica NULL — o status carrega o fato.
                confirmada_em=None,
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
                # só a ÚLTIMA cobrança tem data conhecida (DATA ULTIMO CONTATO);
                # as anteriores ficam sem data em vez de repetir a última
                self.bd.inserir("contatos", dict(
                    testemunha_id=tid,
                    em=(data_iso(campo(f, "DATA ULTIMO CONTATO")) if i + 1 == cob else None),
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
        `origem = 'MIGRACAO'` e a MELHOR DATA que a origem oferece para a
        etapa atual (`quando()`); o motivo diz de qual campo a data saiu. É
        essa data que `v_estagnados` lê — datada da carga, o SLA nascia zerado."""
        for h in self.hist:
            candidatos = h["candidatos"]
            if h["entidade"] == "clientes" and h["etapa"] == "DISTRIBUIDO":
                candidatos = [("DISTRIBUIÇAO do processo",
                               self.distribuicao_do_cliente.get(h["id"]))] + candidatos
            em, motivo = self.quando(candidatos, h["criado"])
            self.bd.inserir("historico_etapas", dict(
                entidade=h["entidade"], entidade_id=h["id"], de=None, para=h["etapa"],
                motivo=motivo, origem="MIGRACAO", em=em))

    def gravar_conferencias(self, guardadas):
        vistas = set()
        decididas = guardadas.get("conferencias", {}) if isinstance(guardadas, dict) else guardadas
        for c in self.conf:
            if c["chave"] in vistas:
                continue
            vistas.add(c["chave"])
            antes = decididas.get(c["chave"])
            if antes:
                # dono e quem resolveu são recasados pelo record da pessoa: o id mudou
                c.update(situacao=antes[1], dono_id=self.pessoa.get(antes[6]),
                         anotacao=antes[3], resolvido_em=antes[4],
                         resolvido_por=self.pessoa.get(antes[7]))
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
            # as contas de acesso sobrevivem até ao --recriar: lê antes de derrubar
            guardadas = bd.guardar()
            bd.executar("DROP SCHEMA IF EXISTS public CASCADE")
            bd.executar("CREATE SCHEMA public")
            aplicar_arquivos(bd, ["esquema.sql", "governanca.sql"])
            bd.executar("ALTER TABLE historico_etapas ADD CONSTRAINT fk_hist_pessoa "
                        "FOREIGN KEY (pessoa_id) REFERENCES pessoas(id) ON DELETE SET NULL")
            bd.executar("ALTER TABLE prazos ADD CONSTRAINT fk_prazo_tipo "
                        "FOREIGN KEY (tipo) REFERENCES prazo_tipos(codigo)")
            # o tipo de prazo que a leitura do diário SUGERE sai da mesma lista
            # fechada do prazo que ela pode virar — senão a proposta ofereceria
            # um tipo que o `prazos` recusaria na hora de criar
            bd.executar("ALTER TABLE publicacoes ADD CONSTRAINT fk_pub_prazo_tipo "
                        "FOREIGN KEY (prazo_tipo_sugerido) REFERENCES prazo_tipos(codigo)")
            # a governança criou cinco tabelas DEPOIS do esquema: RLS de novo,
            # senão o mapa de etapas fica aberto na API pública
            bd.executar("SELECT ligar_rls()")
        else:
            guardadas = bd.limpar()

        bd.governanca(False)                 # a carga do passivo passa por fora
        m = Migracao(bd, a.amostra)
        for passo, funcao in (("equipe", m.equipe),
                              ("contas de acesso", lambda: m.restaurar_usuarios(guardadas)),
                              ("empresas", m.empresas),
                              ("fragilidades", m.fragilidades), ("clientes", m.clientes),
                              ("processos", m.processos), ("pós-processual", m.pos_processual),
                              ("cadastro incompleto", m.cadastro_incompleto),
                              ("testemunhas", m.testemunhas),
                              ("auditoria de testemunhas", m.auditoria_testemunhas),
                              ("faltantes", m.faltantes), ("histórico", m.historico)):
            t0 = time.time()
            funcao()
            print("%-26s %5.1fs" % (passo, time.time() - t0))
        m.gravar_conferencias(guardadas)
        bd.governanca(True)                  # e a regra volta inteira

        resumo = {t: n for t, n in sorted(bd.conta.items())}
        resumo["_data_referencia"] = m.hoje
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
