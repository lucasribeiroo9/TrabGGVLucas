#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A prova da migração: recalcula da ORIGEM e compara com o banco.

Se qualquer linha der DIVERGE, a migração não pode ser considerada boa e nada
sobe. É o mesmo contrato do Prev — só termina com **TUDO CONFERE**.

    ./.venv/bin/python conferir.py            # tudo
    ./.venv/bin/python conferir.py --amostra 40   # confere a carga de amostra

O que se prova aqui, e por quê:

  contagem por tabela      — nenhuma linha ficou pelo caminho
  contagem por opção       — a tradução dos selects poluídos entregou onde disse
  soma de cada valor em R$ — o dinheiro atravessou inteiro, ao centavo
  cada link                — nenhuma ligação do Airtable virou NULL calado
  integridade              — nada de record repetido, órfão ou etapa fora do mapa

Recalcular da origem não é redundância: é a única forma de pegar a carga que
"funcionou" e perdeu 300 linhas no meio. A regra de fase mora num lugar só
(`migrar.Migracao.fase_final`) justamente para que esta prova use a MESMA
regra — duas cópias da regra provariam apenas que as duas cópias concordam.
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import normalizar as N                                              # noqa: E402
import migrar as M                                                  # noqa: E402
from normalizar import centavos, cpf_valido, norm, so_digitos, txt   # noqa: E402
from migrar import campo, link, um_link, ler, segredo               # noqa: E402


def dinheiro(v):
    """A origem guarda R$ como número; aqui tudo é centavo inteiro."""
    return centavos(v) or 0


class Prova:
    def __init__(self, dsn, amostra=None):
        import psycopg
        self.con = psycopg.connect(dsn)
        self.amostra = amostra
        self.linhas = []
        self.falhas = 0

    def q(self, sql, params=None):
        cur = self.con.cursor()
        cur.execute(sql, params or ())
        r = cur.fetchone()
        return r[0] if r else 0

    def dist(self, sql):
        cur = self.con.cursor()
        cur.execute(sql)
        return {a: b for a, b in cur.fetchall()}

    def corta(self, registros):
        return registros[:self.amostra] if self.amostra else registros

    def checar(self, rotulo, esperado, obtido, tolerancia=0):
        ok = abs((esperado or 0) - (obtido or 0)) <= tolerancia
        if not ok:
            self.falhas += 1
        self.linhas.append((rotulo, esperado, obtido, ok))

    def secao(self, titulo):
        self.linhas.append((titulo, None, None, None))

    # ================================================================ contagens
    def contagens(self):
        self.secao("CONTAGEM POR TABELA")
        func = self.corta(ler("funcionarios"))
        self.checar("pessoas", sum(1 for r in func if txt(campo(r["fields"], "NOME"))),
                    self.q("SELECT COUNT(*) FROM pessoas"))
        self.checar("papéis da equipe",
                    sum(1 for r in func for p in (campo(r["fields"], "FUNCOES") or [])
                        if N.PAPEL.get(p)),
                    self.q("SELECT COUNT(*) FROM pessoa_papeis"))

        emp = self.corta(ler("empresas"))
        self.checar("empresas", sum(1 for r in emp if txt(campo(r["fields"], "EMPRESA"))),
                    self.q("SELECT COUNT(*) FROM empresas"))
        self.checar("fragilidades", len(self.corta(ler("fragilidades"))),
                    self.q("SELECT COUNT(*) FROM fragilidades"))

        pre = self.corta(ler("pre_processual"))
        self.checar("clientes vindos da PRÉ", sum(1 for r in pre if txt(campo(r["fields"], "NOME"))),
                    self.q("SELECT COUNT(*) FROM clientes WHERE origem_cadastro='PRE_PROCESSUAL'"))
        self.checar("clientes com CPF válido na PRÉ",
                    sum(1 for r in pre if cpf_valido(so_digitos(campo(r["fields"], "CPF")) or "")),
                    self.q("SELECT COUNT(*) FROM clientes WHERE cpf_valido AND "
                           "origem_cadastro='PRE_PROCESSUAL'"))

        pares = self.pares()
        vivos = [(fc, fp) for fc, fp in pares if self.fase(fc, fp)[0]]
        self.checar("processos", len(vivos), self.q("SELECT COUNT(*) FROM processos"))
        self.checar("processos fora do escopo (não migram)", len(pares) - len(vivos),
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='FORA_DO_ESCOPO'"))
        self.checar("todo processo tem cliente", 0,
                    self.q("SELECT COUNT(*) FROM processos WHERE cliente_id IS NULL"))

        tes = self.corta(ler("testemunhas"))
        self.checar("testemunhas", sum(1 for r in tes if txt(campo(r["fields"], "NOME TESTEMUNHA"))),
                    self.q("SELECT COUNT(*) FROM testemunhas"))
        self.checar("faltantes (lista de conferência)", len(self.corta(ler("faltantes"))),
                    self.q("SELECT COUNT(*) FROM conferencia_faltantes"))
        self.checar("log do formulário de testemunhas", len(self.corta(ler("auditoria_testemunhas"))),
                    self.q("SELECT COUNT(*) FROM testemunha_auditoria"))

        # anexos: só metadado, mas o metadado tem de estar inteiro
        anexos = [a for r in tes for a in (campo(r["fields"], "ARQUIVOS ENVIADOS PELA TESTEMUNHA") or [])]
        anexos += [a for r in self.corta(ler("fragilidades"))
                   for a in (campo(r["fields"], "DOSSIE") or [])]
        self.checar("anexos (metadado)", len(anexos),
                    self.q("SELECT COUNT(*) FROM documentos WHERE fonte='ANEXO_AIRTABLE'"))
        self.checar("bytes de anexo", sum(a.get("size", 0) for a in anexos if isinstance(a, dict)),
                    self.q("SELECT COALESCE(SUM(tamanho_bytes),0) FROM documentos "
                           "WHERE fonte='ANEXO_AIRTABLE'"))

        self.checar("pendências de documento",
                    sum(1 for r in pre for p in (campo(r["fields"], "PENDENCIAS") or [])
                        if N.DOCUMENTO.get(p)),
                    self.q("SELECT COUNT(*) FROM pendencias WHERE tipo='DOCUMENTO'"))
        self.checar("audiências",
                    sum(1 for fc, fp in vivos if self.v(fc, fp, "DATA AUDIENCIA") or self.v(fc, fp, "AUDIENCIA")),
                    self.q("SELECT COUNT(*) FROM audiencias"))
        self.checar("perícias",
                    sum(1 for fc, fp in vivos for k in ("DATA PERÍCIA MÉDICA", "DATA PERÍCIA TECNICA")
                        if self.v(fc, fp, k)),
                    self.q("SELECT COUNT(*) FROM pericias"))
        self.checar("histórico de etapas (origem MIGRACAO)",
                    self.q("SELECT COUNT(*) FROM clientes") + self.q("SELECT COUNT(*) FROM processos")
                    + self.q("SELECT COUNT(*) FROM audiencias") + self.q("SELECT COUNT(*) FROM incidentes"),
                    self.q("SELECT COUNT(*) FROM historico_etapas WHERE origem='MIGRACAO'"))

    # ================================================================ os pares
    def pares(self):
        """A CÓPIA como base, casada por CNJ com a PROCESSUAL — a mesma regra do
        `migrar.py`, refeita da origem."""
        if hasattr(self, "_pares"):
            return self._pares
        copia, proc = self.corta(ler("copia")), self.corta(ler("processual"))
        por_cnj = defaultdict(list)
        for r in proc:
            c = so_digitos(campo(r["fields"], "Nº PROCESSO"))
            if c:
                por_cnj[c].append(r)
        usados, pares = set(), []
        for r in copia:
            c = so_digitos(campo(r["fields"], "Nº PROCESSO"))
            fila = por_cnj.get(c) or []
            par = fila.pop(0) if fila else None
            if par:
                usados.add(par["id"])
            pares.append((r["fields"], par["fields"] if par else {}))
        for r in proc:
            if r["id"] not in usados:
                pares.append(({}, r["fields"]))
        self._pares = pares
        return pares

    _m = None

    def v(self, fc, fp, nome):
        if Prova._m is None:
            Prova._m = M.Migracao.__new__(M.Migracao)
        return Prova._m.valor(fc, fp, nome)

    def fase(self, fc, fp):
        if Prova._m is None:
            Prova._m = M.Migracao.__new__(M.Migracao)
        return Prova._m.fase_final(fc, fp)

    # ================================================================ por opção
    def opcoes(self):
        self.secao("CONTAGEM POR OPÇÃO DE SELECT")
        pre, tes = self.corta(ler("pre_processual")), self.corta(ler("testemunhas"))
        vivos = [(fc, fp) for fc, fp in self.pares() if self.fase(fc, fp)[0]]

        esperado = Counter()
        for r in self.corta(ler("funcionarios")):
            for p in (campo(r["fields"], "FUNCOES") or []):
                if N.PAPEL.get(p):
                    esperado[N.PAPEL[p]] += 1
        self.comparar("papel", esperado,
                      self.dist("SELECT papel, COUNT(*) FROM pessoa_papeis GROUP BY 1"))

        esperado = Counter()
        for r in self.corta(ler("empresas")):
            s, _ = N._traduz(N.SITUACAO_EMPRESA, campo(r["fields"], "STATUS EMPRESA"), "situacao")
            if s:
                esperado[s] += 1
        self.comparar("situação da empresa", esperado,
                      self.dist("SELECT situacao, COUNT(*) FROM empresas "
                                "WHERE situacao IS NOT NULL GROUP BY 1"))

        esperado = Counter()
        for r in tes:
            s, _ = N._traduz(N.STATUS_TESTEMUNHA, campo(r["fields"], "STATUS TESTEMUNHA"), "situacao")
            esperado[s or "PENDENTE"] += 1
        self.comparar("situação da testemunha", esperado,
                      self.dist("SELECT situacao, COUNT(*) FROM testemunhas GROUP BY 1"))

        esperado = Counter()
        for r in pre:
            f = r["fields"]
            if not txt(campo(f, "NOME")):
                continue
            etapa, _, _ = N.etapa_cliente(campo(f, "ETAPA PRE PROCESSUAL"),
                                          campo(f, "STATUS PETICAO INICIAL"),
                                          campo(f, "STATUS ENTREVISTA"),
                                          campo(f, "STATUS DOCUMENTAÇÃO"))
            esperado[etapa] += 1
        self.comparar("etapa do cliente (só as da PRÉ)", esperado,
                      self.dist("SELECT status, COUNT(*) FROM clientes "
                                "WHERE origem_cadastro='PRE_PROCESSUAL' GROUP BY 1"))

        esperado = Counter(self.fase(fc, fp)[0] for fc, fp in vivos)
        self.comparar("fase do processo", esperado,
                      self.dist("SELECT fase, COUNT(*) FROM processos GROUP BY 1"))

        esperado = Counter()
        for fc, fp in vivos:
            s, _, _ = Prova._m.situacao_execucao(fc, fp)
            if s:
                esperado[s] += 1
        self.comparar("situação da execução", esperado,
                      self.dist("SELECT situacao_execucao, COUNT(*) FROM processos "
                                "WHERE situacao_execucao IS NOT NULL GROUP BY 1"))

        esperado = Counter()
        for fc, fp in vivos:
            par, _ = N._traduz(N.AUDIENCIA, self.v(fc, fp, "AUDIENCIA"), "tipo")
            if par and par[0]:
                esperado[par[0]] += 1
        self.comparar("tipo de audiência", esperado,
                      self.dist("SELECT tipo, COUNT(*) FROM audiencias WHERE tipo IS NOT NULL GROUP BY 1"))

        esperado = Counter()
        for fc, fp in vivos:
            o, _ = N._traduz(N.DECISAO_OBJETIVA, self.v(fc, fp, "DECISAO SENTENCA"), "r")
            if o:
                esperado[o] += 1
        self.comparar("resultado da sentença", esperado,
                      self.dist("SELECT resultado_objetivo, COUNT(*) FROM decisoes "
                                "WHERE tipo='SENTENCA' AND resultado_objetivo IN "
                                "('PROCEDENTE','PARCIALMENTE_PROCEDENTE','IMPROCEDENTE',"
                                "'EXTINTO_SEM_RESOLUCAO') GROUP BY 1"))

        esperado = Counter()
        for fc, fp in vivos:
            o, _ = N._traduz(N.RESULTADO_RECURSO, campo(fc, "RESULTADO RECURSO"), "r")
            if o:
                esperado[o] += 1
        self.comparar("resultado do acórdão", esperado,
                      self.dist("SELECT resultado_objetivo, COUNT(*) FROM decisoes "
                                "WHERE tipo='ACORDAO' AND resultado_objetivo IS NOT NULL GROUP BY 1"))

        esperado = Counter()
        for fc, fp in vivos:
            s, _ = N._traduz(N.STATUS_ACORDO, self.v(fc, fp, "STATUS ACORDO"), "situacao")
            if s:
                esperado[s] += 1
        obtido = self.dist("SELECT situacao, COUNT(*) FROM acordos GROUP BY 1")
        obtido.pop("EM_ANDAMENTO", None)                 # nasce por valor sem status
        esperado.pop("EM_ANDAMENTO", None)
        self.comparar("situação do acordo (fora EM_ANDAMENTO)", esperado, obtido)

    def comparar(self, rotulo, esperado, obtido):
        for k in sorted(set(esperado) | set(obtido)):
            self.checar("  %s = %s" % (rotulo, k), esperado.get(k, 0), obtido.get(k, 0))

    # ================================================================ dinheiro
    def dinheiro_(self):
        self.secao("SOMA DE CADA CAMPO EM R$ (centavos)")
        vivos = [(fc, fp) for fc, fp in self.pares() if self.fase(fc, fp)[0]]

        self.checar("valor da causa",
                    sum(dinheiro(self.v(fc, fp, "VALOR")) for fc, fp in vivos),
                    self.q("SELECT COALESCE(SUM(valor_causa_centavos),0) FROM processos"))

        for base, campos in (("RECLAMANTE", ("CALCULO RCTE", "SUCUMB RCTE", "HONOR TOTAL CALCULO RCTE")),
                             ("RECLAMADA",  ("CALCULO RCDA", "SUCUMB RCDA", "HONOR TOTAL CALCULO RCDA")),
                             ("HOMOLOGADO", ("VALOR HOM", "SUCUMB HOM", "HONOR  TOTAL HOMOL"))):
            for i, (coluna, nome) in enumerate(zip(
                    ("valor_centavos", "sucumbencia_centavos", "honorario_centavos"), campos)):
                so_copia = i == 2                     # os honorários por base só existem na CÓPIA
                esperado = sum(dinheiro(campo(fc, nome) if so_copia else self.v(fc, fp, nome))
                               for fc, fp in vivos)
                self.checar("cálculo %s · %s" % (base, nome),
                            esperado,
                            self.q("SELECT COALESCE(SUM(%s),0) FROM calculos WHERE base='%s'"
                                   % (coluna, base)))

        self.checar("valor do acordo",
                    sum(dinheiro(self.v(fc, fp, "VALOR ACORDO")) for fc, fp in vivos),
                    self.q("SELECT COALESCE(SUM(valor_centavos),0) FROM acordos"))
        self.checar("honorário do acordo",
                    sum(dinheiro(campo(fc, "HONOR TOTAL ACORDO")) for fc, fp in vivos),
                    self.q("SELECT COALESCE(SUM(honorario_centavos),0) FROM acordos"))
        self.checar("valor da parcela",
                    sum(dinheiro(campo(fc, "VALOR PARCELA")) for fc, fp in vivos),
                    self.q("SELECT COALESCE(SUM(valor_parcela_centavos),0) FROM acordos"))

        # recebimentos: o processo primeiro; o PÓS só entra onde o processo calou
        esperado = defaultdict(int)
        tem = defaultdict(set)
        for i, (fc, fp) in enumerate(vivos):
            for base, nome in (("TOTAL", "TOTAL RECEBIDO"), ("SUCUMBENCIA", "SUCUMB RECEBIDO"),
                               ("HONORARIOS", "HONOR TOTAL")):
                c = dinheiro(self.v(fc, fp, nome))
                if c:
                    esperado[base] += c
                    tem[base].add(so_digitos(campo(fc, "Nº PROCESSO") or campo(fp, "Nº PROCESSO")))
        # o PÓS só entra quando há processo do outro lado: registro do PÓS sem
        # link e sem número que case não tem onde pousar, e vira LINK_QUEBRADO
        cnjs = {so_digitos(campo(fc, "Nº PROCESSO") or campo(fp, "Nº PROCESSO"))
                for fc, fp in vivos}
        for r in self.corta(ler("pos_processual")):
            f = r["fields"]
            cnj = so_digitos(campo(f, "N° DO PROCESSO"))
            if cnj not in cnjs:
                continue
            for base, nome in (("CLIENTE", "VALOR RECEBIDO CLIENTE"),
                               ("HONORARIOS", "VALOR HONORARIOS"),
                               ("SUCUMBENCIA", "VALOR SUCUMBENCIA")):
                c = dinheiro(campo(f, nome))
                if c and cnj and cnj not in tem[base]:
                    esperado[base] += c
                    tem[base].add(cnj)
        for base in ("TOTAL", "SUCUMBENCIA", "HONORARIOS", "CLIENTE"):
            self.checar("recebido · %s" % base, esperado[base],
                        self.q("SELECT COALESCE(SUM(valor_centavos),0) FROM recebimentos "
                               "WHERE base='%s'" % base))

        self.checar("valor estimado das fragilidades",
                    sum(dinheiro(campo(r["fields"], "VALOR ESTIMADO"))
                        for r in self.corta(ler("fragilidades"))),
                    self.q("SELECT COALESCE(SUM(valor_estimado_centavos),0) FROM fragilidades"))
        self.checar("valor da causa nos faltantes",
                    sum(dinheiro(campo(r["fields"], "VALOR")) for r in self.corta(ler("faltantes"))),
                    self.q("SELECT COALESCE(SUM(valor_causa_centavos),0) FROM conferencia_faltantes"))

    # ================================================================ os links
    def carregados(self, arquivo):
        """Os records que a carga viu. Com `--amostra` o corte deixa link
        apontando para registro que ficou de fora — e link para quem não entrou
        NÃO é ligação perdida, é a amostra sendo amostra. Contar isso como
        defeito faria a conferência reclamar sempre, e conferência que sempre
        reclama deixa de ser lida."""
        if not hasattr(self, "_ids"):
            self._ids = {}
        if arquivo not in self._ids:
            self._ids[arquivo] = {r["id"] for r in self.corta(ler(arquivo))}
        return self._ids[arquivo]

    def links(self):
        self.secao("CADA LIGAÇÃO DO AIRTABLE")
        pre = self.corta(ler("pre_processual"))
        pessoas, empresas = self.carregados("funcionarios"), self.carregados("empresas")

        def liga(f, nome, alvos):
            r = um_link(f, nome)
            return bool(r and r in alvos)

        for nome, coluna, alvos in (("EMPRESA", "empresa_id", empresas),
                                    ("CAPTADOR", "captador_id", pessoas),
                                    ("ENTREVISTADOR", "entrevistador_id", pessoas),
                                    ("RESPONSAVEL INICIAL", "responsavel_id", pessoas)):
            self.checar("clientes.%s" % coluna,
                        sum(1 for r in pre if liga(r["fields"], nome, alvos)),
                        self.q("SELECT COUNT(*) FROM clientes WHERE %s IS NOT NULL "
                               "AND origem_cadastro='PRE_PROCESSUAL'" % coluna))

        vivos = [(fc, fp) for fc, fp in self.pares() if self.fase(fc, fp)[0]]
        for nome, coluna, alvos in (("EMPRESA", "empresa_id", empresas),
                                    ("ADVOGADO", "advogado_id", pessoas),
                                    ("CAPTADOR", "captador_id", pessoas)):
            self.checar("processos.%s" % coluna,
                        sum(1 for fc, fp in vivos
                            if liga(fc, nome, alvos) or liga(fp, nome, alvos)),
                        self.q("SELECT COUNT(*) FROM processos WHERE %s IS NOT NULL" % coluna))

        tes = self.corta(ler("testemunhas"))
        for nome, coluna, alvos in (("EMPRESA", "empresa_id", empresas),
                                    ("CAPTADOR", "captador_id", pessoas)):
            self.checar("testemunhas.%s" % coluna,
                        sum(1 for r in tes if liga(r["fields"], nome, alvos)),
                        self.q("SELECT COUNT(*) FROM testemunhas WHERE %s IS NOT NULL" % coluna))
        proc_ids = self.carregados("processual")
        self.checar("testemunha × processo",
                    sum(1 for r in tes for x in link(r["fields"], "TESTEMUNHA DE:") if x in proc_ids),
                    self.q("SELECT COUNT(*) FROM testemunha_vinculos WHERE processo_id IS NOT NULL"))
        pre_ids = self.carregados("pre_processual")
        self.checar("testemunha × cliente",
                    sum(1 for r in tes for x in link(r["fields"], "TESTEMUNHA DE") if x in pre_ids),
                    self.q("SELECT COUNT(*) FROM testemunha_vinculos WHERE cliente_id IS NOT NULL"))
        self.checar("fragilidades.empresa_id",
                    sum(1 for r in self.corta(ler("fragilidades"))
                        if liga(r["fields"], "EMPRESA", empresas)),
                    self.q("SELECT COUNT(*) FROM fragilidades WHERE empresa_id IS NOT NULL"))
        self.checar("faltantes.empresa_id",
                    sum(1 for r in self.corta(ler("faltantes"))
                        if liga(r["fields"], "EMPRESA", empresas)),
                    self.q("SELECT COUNT(*) FROM conferencia_faltantes WHERE empresa_id IS NOT NULL"))

    # ================================================================ integridade
    def integridade(self):
        self.secao("INTEGRIDADE — estas linhas TÊM de dar zero")
        for tabela in ("pessoas", "empresas", "clientes", "processos", "testemunhas",
                       "conferencia_faltantes"):
            self.checar("%s com record repetido" % tabela, 0, self.q(
                "SELECT COUNT(*) FROM (SELECT airtable_record_id FROM %s "
                "WHERE airtable_record_id IS NOT NULL GROUP BY 1 HAVING COUNT(*)>1) x" % tabela))
        self.checar("linha migrada sem o registro original", 0, self.q(
            "SELECT COUNT(*) FROM processos WHERE airtable_bruto IS NULL"))
        self.checar("cliente sem o registro original", 0, self.q(
            "SELECT COUNT(*) FROM clientes WHERE airtable_bruto IS NULL"))
        self.checar("fase fora do mapa da governança", 0, self.q(
            "SELECT COUNT(*) FROM processos p WHERE NOT EXISTS (SELECT 1 FROM fluxo_etapas e "
            "JOIN fluxos f ON f.id=e.fluxo_id WHERE f.codigo='PROCESSO' AND e.codigo=p.fase)"))
        self.checar("etapa de cliente fora do mapa", 0, self.q(
            "SELECT COUNT(*) FROM clientes c WHERE NOT EXISTS (SELECT 1 FROM fluxo_etapas e "
            "JOIN fluxos f ON f.id=e.fluxo_id WHERE f.codigo='CLIENTE' AND e.codigo=c.status)"))
        self.checar("prazo em dias corridos sem motivo", 0, self.q(
            "SELECT COUNT(*) FROM prazos WHERE contagem<>'UTEIS' AND COALESCE(contagem_motivo,'')=''"))
        self.checar("entidade governada sem histórico", 0, self.q(
            "SELECT COUNT(*) FROM processos p WHERE NOT EXISTS (SELECT 1 FROM historico_etapas h "
            "WHERE h.entidade='processos' AND h.entidade_id=p.id)"))
        self.checar("gatilho de governança desligado", 0, self.q(
            "SELECT COUNT(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid "
            "WHERE c.relname IN ('clientes','processos','audiencias','prazos','incidentes') "
            "AND NOT t.tgisinternal AND t.tgenabled='D'"))
        # o defeito que só apareceria no primeiro cadastro feito na tela: a
        # carga grava id explícito e a sequência de identidade fica para trás
        cur = self.con.cursor()
        cur.execute("""SELECT c.relname, pg_get_serial_sequence('public.'||quote_ident(c.relname),'id')
                       FROM pg_class c JOIN pg_attribute a ON a.attrelid=c.oid AND a.attname='id'
                       WHERE c.relnamespace='public'::regnamespace AND c.relkind='r'""")
        atrasadas = 0
        for tabela, seq in cur.fetchall():
            if not seq:
                continue
            maior = self.q("SELECT COALESCE(MAX(id),0) FROM %s" % tabela)
            proximo = self.q("SELECT last_value + (CASE WHEN is_called THEN 1 ELSE 0 END) FROM %s" % seq)
            if proximo <= maior:
                atrasadas += 1
        self.checar("sequência atrás do maior id", 0, atrasadas)
        self.checar("tabela sem RLS", 0, self.q(
            "SELECT COUNT(*) FROM pg_tables t JOIN pg_class c ON c.relname=t.tablename "
            "WHERE t.schemaname='public' AND c.relnamespace='public'::regnamespace "
            "AND NOT c.relrowsecurity"))
        self.checar("valor poluído sem conferência aberta",
                    0 if self.q("SELECT COUNT(*) FROM processos WHERE situacao_execucao IS NULL "
                                "AND situacao_execucao_original IS NOT NULL") ==
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='VALOR_SEM_TRADUCAO' "
                           "AND campo='situacao_execucao'") else 1, 0)

    # ================================================================ o retrato
    def retrato(self):
        print("-" * 74)
        print("o acervo que entrou:")
        for rot, sql in (("clientes", "SELECT COUNT(*) FROM clientes"),
                         ("  vindos da PRÉ", "SELECT COUNT(*) FROM clientes WHERE origem_cadastro='PRE_PROCESSUAL'"),
                         ("  criados dos autos", "SELECT COUNT(*) FROM clientes WHERE origem_cadastro='PROCESSO'"),
                         ("processos", "SELECT COUNT(*) FROM processos"),
                         ("  com sentença registrada", "SELECT COUNT(DISTINCT processo_id) FROM decisoes WHERE tipo='SENTENCA'"),
                         ("  encerrados", "SELECT COUNT(*) FROM processos WHERE fase='ENCERRADO'"),
                         ("empresas", "SELECT COUNT(*) FROM empresas"),
                         ("testemunhas", "SELECT COUNT(*) FROM testemunhas"),
                         ("incidentes abertos", "SELECT COUNT(*) FROM incidentes"),
                         ("tarefas criadas pela carga", "SELECT COUNT(*) FROM tarefas WHERE origem='MIGRACAO'"),
                         ("conferências abertas", "SELECT COUNT(*) FROM conferencias WHERE situacao='ABERTA'")):
            print("%-34s %12s" % (rot, "{:,}".format(self.q(sql)).replace(",", ".")))
        print("\nconferências por tipo:")
        for tipo, n in sorted(self.dist("SELECT tipo, COUNT(*) FROM conferencias GROUP BY 1").items(),
                              key=lambda x: -x[1]):
            print("  %-24s %8d" % (tipo, n))

    def imprimir(self):
        for rotulo, esp, obt, ok in self.linhas:
            if ok is None:
                print("\n" + rotulo)
                print("-" * 74)
                continue
            print("%-44s %12s %12s   %s" % (rotulo[:44], "{:,}".format(esp).replace(",", "."),
                                            "{:,}".format(obt).replace(",", "."),
                                            "ok" if ok else "DIVERGE"))
        self.retrato()
        print("\n%s\n" % ("TUDO CONFERE" if not self.falhas
                          else "%d divergência(s) — a migração NÃO está boa" % self.falhas))
        return self.falhas


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dsn")
    p.add_argument("--amostra", type=int)
    a = p.parse_args()
    dsn = a.dsn or segredo("GGV_SUPABASE_TRAB")
    if not dsn:
        sys.exit("falta GGV_SUPABASE_TRAB (ou --dsn)")
    pr = Prova(dsn, a.amostra)
    pr.contagens()
    pr.opcoes()
    pr.dinheiro_()
    pr.links()
    pr.integridade()
    sys.exit(1 if pr.imprimir() else 0)


if __name__ == "__main__":
    main()
