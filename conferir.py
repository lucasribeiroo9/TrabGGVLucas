#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A prova da migração: recalcula da ORIGEM e compara com o banco.

Se qualquer linha der DIVERGE, a migração não pode ser considerada boa e nada
sobe. É o mesmo contrato do Prev — só termina com **TUDO CONFERE**.

    ./.venv/bin/python conferir.py            # tudo
    ./.venv/bin/python conferir.py --amostra 40   # confere a carga de amostra

O que se prova aqui, e por quê:

  contagem por tabela      — nenhuma linha ficou pelo caminho: TODA tabela que a
                             carga escreve tem a sua linha, contada da origem
  contagem por opção       — a tradução dos selects poluídos entregou onde disse
  soma de cada valor em R$ — o dinheiro atravessou inteiro, ao centavo
  cada link                — nenhuma ligação do Airtable virou NULL calado
  integridade              — nada de record repetido, órfão ou etapa fora do mapa
  nada inventado           — data que a origem não tem está NULL; histórico nunca
                             datado da carga; audiência do passado nunca pendente

As fichas criadas dos autos são contadas repetindo da origem a regra de quem é
o dono do processo (`Migracao.dono_do_processo`), sem tocar no banco — antes
esta prova comparava o histórico com o próprio banco, o que não prova nada.

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
        self.hoje = M.data_referencia()

    def q(self, sql, params=None):
        cur = self.con.cursor()
        cur.execute(sql, params or None)
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
        # TODAS entram, inclusive as sem nome (a carga real tem 2): pular seria perder linha
        self.checar("testemunhas", len(tes), self.q("SELECT COUNT(*) FROM testemunhas"))
        self.checar("testemunhas sem nome → conferência aberta",
                    sum(1 for r in tes if not txt(campo(r["fields"], "NOME TESTEMUNHA"))),
                    self.q("SELECT COUNT(*) FROM conferencias WHERE entidade='testemunhas' AND campo='nome'"))
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

        self.checar("pendências de documento (PENDENCIAS da PRÉ)",
                    sum(1 for r in pre for p in (campo(r["fields"], "PENDENCIAS") or [])
                        if N.DOCUMENTO.get(p)),
                    self.q("SELECT COUNT(*) FROM pendencias WHERE tipo='DOCUMENTO' "
                           "AND documento_tipo <> 'CONTRATO'"))
        sim = self.simulacao()
        self.checar("clientes criados dos autos", sim["novos"],
                    self.q("SELECT COUNT(*) FROM clientes WHERE origem_cadastro='PROCESSO'"))
        self.checar("  … com nome ambíguo → conferência", sim["ambiguos"],
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='CLIENTE_AMBIGUO'"))
        self.checar("ficha sem data de assinatura → pendência CONTRATO",
                    sum(1 for c in sim["assinatura"].values() if not c),
                    self.q("SELECT COUNT(*) FROM pendencias WHERE documento_tipo='CONTRATO'"))
        self.checar("ficha sem nascimento → pendência CADASTRO",
                    sum(1 for c in sim["nascimento"].values() if not c),
                    self.q("SELECT COUNT(*) FROM pendencias WHERE tipo='CADASTRO'"))
        self.checar("clientes com data de assinatura",
                    sum(1 for c in sim["assinatura"].values() if c),
                    self.q("SELECT COUNT(*) FROM clientes WHERE data_assinatura_contrato IS NOT NULL"))
        self.checar("clientes com nascimento",
                    sum(1 for c in sim["nascimento"].values() if c),
                    self.q("SELECT COUNT(*) FROM clientes WHERE data_nascimento IS NOT NULL"))
        n_aud = sum(1 for fc, fp in vivos if self.v(fc, fp, "DATA AUDIENCIA") or self.v(fc, fp, "AUDIENCIA"))
        self.checar("audiências", n_aud, self.q("SELECT COUNT(*) FROM audiencias"))
        self.checar("perícias",
                    sum(1 for fc, fp in vivos for k in ("DATA PERÍCIA MÉDICA", "DATA PERÍCIA TECNICA")
                        if self.v(fc, fp, k)),
                    self.q("SELECT COUNT(*) FROM pericias"))

        # --- as tabelas que a prova anterior não contava (Auditor, seção 3)
        sent = sum(1 for fc, fp in vivos if self.tem_sentenca(fc, fp))
        acor = sum(1 for fc, fp in vivos if self.tem_acordao(fc, fp))
        self.checar("decisões · sentenças", sent,
                    self.q("SELECT COUNT(*) FROM decisoes WHERE tipo='SENTENCA'"))
        self.checar("decisões · acórdãos", acor,
                    self.q("SELECT COUNT(*) FROM decisoes WHERE tipo='ACORDAO'"))
        self.checar("recursos (acórdão com resultado + STATUS RECURSAL)",
                    sum(1 for fc, fp in vivos
                        if N._traduz(N.RESULTADO_RECURSO, campo(fc, "RESULTADO RECURSO"), "r")[0])
                    + sum(1 for fc, fp in vivos
                          if N._traduz(N.STATUS_RECURSAL, self.v(fc, fp, "STATUS RECURSAL"), "g")[0]),
                    self.q("SELECT COUNT(*) FROM recursos"))
        self.checar("acordos",
                    sum(1 for fc, fp in vivos if self.tem_acordo(fc, fp)),
                    self.q("SELECT COUNT(*) FROM acordos"))
        self.checar("  … sem STATUS ACORDO → conferência",
                    sum(1 for fc, fp in vivos if self.tem_acordo(fc, fp)
                        and not N._traduz(N.STATUS_ACORDO, self.v(fc, fp, "STATUS ACORDO"), "s")[0]),
                    self.q("SELECT COUNT(*) FROM conferencias WHERE campo='situacao_acordo'"))
        self.checar("cálculos (uma linha por base com valor)",
                    sum(1 for fc, fp in vivos for base, campos in self.BASES_CALCULO
                        if any(x not in (None, "") for x in self.valores_calculo(fc, fp, campos))),
                    self.q("SELECT COUNT(*) FROM calculos"))
        self.checar("incidentes de representação",
                    sum(1 for fc, fp in vivos if self.tem_incidente(fc, fp)),
                    self.q("SELECT COUNT(*) FROM incidentes"))
        esperado = Counter()
        for fc, fp in vivos:
            st_proc = self.v(fc, fp, "STATUS DO PROCESSO")
            fase, _, inc, _, _ = self.fase(fc, fp)
            destino, valor, _, _, _ = Prova._m.revogacao_destino(fc, fp, st_proc, inc)
            if destino == "TAREFA":
                esperado["OUTRO"] += 1
            st = N.STATUS_PROCESSO.get(st_proc) if st_proc else None
            if st and st[0] == "TAREFA":
                esperado["REDISTRIBUICAO"] += 1
            prov = txt(self.v(fc, fp, "PROVIDENCIAS"))
            if self.tem_incidente(fc, fp) and prov:
                esperado["NOTIFICACAO"] += sum(1 for k in N.PROVIDENCIAS if norm(k) in norm(prov))
            andamento = txt(self.v(fc, fp, "AND. NECESSÁRIO"))
            if andamento and N.AND_NECESSARIO.get(andamento, "__livre__"):
                esperado["ANDAMENTO"] += 1
        cnjs = {so_digitos(campo(fc, "Nº PROCESSO") or campo(fp, "Nº PROCESSO")) for fc, fp in vivos}
        recs_proc = {r["id"] for r in self.corta(ler("processual"))}
        for r in self.corta(ler("pos_processual")):
            f = r["fields"]
            if not (um_link(f, "PROCESSUAL") in recs_proc or so_digitos(campo(f, "N° DO PROCESSO")) in cnjs):
                continue
            arq = N.STATUS_ARQUIVAMENTO.get(campo(f, "STATUS ARQUIVAMENTO"))
            if arq and arq[0] == "TAREFA":
                esperado["ARQUIVAMENTO"] += 1
        self.comparar("tarefas da carga, por tipo", esperado,
                      self.dist("SELECT tipo, COUNT(*) FROM tarefas WHERE origem='MIGRACAO' GROUP BY 1"))
        self.checar("anotações (AVISOS da PRÉ + OBSERVACOES + trânsito sem data)",
                    sum(1 for r in pre if txt(campo(r["fields"], "NOME")) and txt(campo(r["fields"], "AVISOS")))
                    + sum(1 for fc, fp in vivos if txt(self.v(fc, fp, "OBSERVACOES")))
                    + sum(1 for r in tes if txt(campo(r["fields"], "OBSERVACOES")))
                    + sum(1 for fc, fp in vivos if self.fase(fc, fp)[3]),
                    self.q("SELECT COUNT(*) FROM anotacoes"))
        self.checar("eventos (entrevistas com data + audiências)",
                    sum(1 for r in pre if txt(campo(r["fields"], "NOME")) and campo(r["fields"], "DATA ENTREVISTA"))
                    + n_aud,
                    self.q("SELECT COUNT(*) FROM eventos"))
        self.checar("contatos (STATUS ENTREVISTA + cobranças de testemunha)",
                    sum((N.STATUS_ENTREVISTA.get(campo(r["fields"], "STATUS ENTREVISTA")) or (None, 0))[1]
                        for r in pre if txt(campo(r["fields"], "NOME"))
                        and (N.STATUS_ENTREVISTA.get(campo(r["fields"], "STATUS ENTREVISTA")) or (None,))[0] == "CONTATO")
                    + sum(N._traduz(N.COBRANCA, campo(r["fields"], "COBRANÇA"), "c")[0] or 0 for r in tes),
                    self.q("SELECT COUNT(*) FROM contatos"))
        self.checar("processo_alias (NOME e VARA divergentes entre as fontes)",
                    sum(1 for fc, fp in vivos if fc and fp for nome in ("NOME", "VARA")
                        if campo(fc, nome) not in (None, "", []) and campo(fp, nome) not in (None, "", [])
                        and norm(campo(fc, nome)) != norm(campo(fp, nome))),
                    self.q("SELECT COUNT(*) FROM processo_alias"))
        disparos = sum(1 for r in pre if txt(campo(r["fields"], "NOME")) and txt(campo(r["fields"], "status_disparo")))
        disparos += sum(1 for fc, fp in vivos if txt(self.v({**fc, **{k: x for k, x in fp.items() if x}}, {}, "status_disparo")))
        disparos += sum(1 for r in tes if txt(campo(r["fields"], "status_disparo")))
        notif = sum(1 for r in pre if txt(campo(r["fields"], "NOME"))
                    for k in ("STATUS_NOTIFICACAO_PRESCRICAO", "STATUS_NOTIFICACAO_RI")
                    if txt(campo(r["fields"], k)) and norm(campo(r["fields"], k)) != "NENHUM")
        captador = sum(1 for r in tes if txt(campo(r["fields"], "notif_captador_status")))
        self.checar("automacao_log (disparos + notificações n8n)", disparos + notif + captador,
                    self.q("SELECT COUNT(*) FROM automacao_log"))
        self.checar("histórico de etapas (origem MIGRACAO)",
                    sum(1 for r in pre if txt(campo(r["fields"], "NOME"))) + sim["novos"] + len(vivos)
                    + n_aud + sum(1 for fc, fp in vivos if self.tem_incidente(fc, fp)),
                    self.q("SELECT COUNT(*) FROM historico_etapas WHERE origem='MIGRACAO'"))

    # ------------------------------------------------ as regras repetidas da origem
    BASES_CALCULO = (("RECLAMANTE", ("CALCULO RCTE", "SUCUMB RCTE", "HONOR TOTAL CALCULO RCTE")),
                     ("RECLAMADA", ("CALCULO RCDA", "SUCUMB RCDA", "HONOR TOTAL CALCULO RCDA")),
                     ("HOMOLOGADO", ("VALOR HOM", "SUCUMB HOM", "HONOR  TOTAL HOMOL")))

    def valores_calculo(self, fc, fp, campos):
        return (self.v(fc, fp, campos[0]), self.v(fc, fp, campos[1]), campo(fc, campos[2]))

    def tem_sentenca(self, fc, fp):
        obj, nota, _ = Prova._m.resultado_sentenca(fc, fp)
        return bool(obj or nota or campo(fc, "DATA SENTENCA"))

    def tem_acordao(self, fc, fp):
        obj_rec, _ = N._traduz(N.RESULTADO_RECURSO, campo(fc, "RESULTADO RECURSO"), "r")
        nota_ac, _ = N._traduz(N.NOTA, self.v(fc, fp, "RESULTADO ACORDAO"), "nota")
        return bool(obj_rec or nota_ac or self.v(fc, fp, "DATA ACORDAO"))

    def tem_acordo(self, fc, fp):
        st_ac, _ = N._traduz(N.STATUS_ACORDO, self.v(fc, fp, "STATUS ACORDO"), "s")
        return bool(st_ac or self.v(fc, fp, "VALOR ACORDO") or campo(fc, "DATA DO ACORDO"))

    def tem_incidente(self, fc, fp):
        _, _, inc, _, _ = self.fase(fc, fp)
        st_proc = self.v(fc, fp, "STATUS DO PROCESSO")
        destino, _, _, _, _ = Prova._m.revogacao_destino(fc, fp, st_proc, inc)
        return bool(inc or N.NOTIFICACAO.get(self.v(fc, fp, "NOTIFICAÇÃO"))
                    or destino == "INCIDENTE" or txt(self.v(fc, fp, "PROVIDENCIAS")))

    def simulacao(self):
        """Repete da origem, sem escrever, a regra de quem é o dono de cada
        processo (`Migracao.dono_do_processo`) e o que a ficha ganha dos autos.
        Daqui saem as fichas criadas dos autos, os nomes ambíguos e as
        pendências de cadastro — antes contadas contra o próprio banco."""
        if hasattr(self, "_sim"):
            return self._sim
        m = M.Migracao.__new__(M.Migracao)
        m.cliente, m.cliente_por_cpf, m.cliente_por_nome = {}, {}, defaultdict(list)
        assinatura, nascimento, prox = {}, {}, [0]

        def novo():
            prox[0] += 1
            return prox[0]
        for r in self.corta(ler("pre_processual")):
            f = r["fields"]
            if not txt(campo(f, "NOME")):
                continue
            cid = novo()
            m.cliente[r["id"]] = cid
            m.lembrar_cliente(cid, so_digitos(campo(f, "CPF")), txt(campo(f, "NOME")))
            assinatura[cid] = M.data_iso(campo(f, "DATA DE ASSINATURA"))
            nascimento[cid] = M.data_iso(campo(f, "NASCIMENTO"))
        novos = ambiguos = 0
        for fc, fp in self.pares():
            if not self.fase(fc, fp)[0]:
                continue
            como, cid, av = m.dono_do_processo(fc, fp)
            if como == "NOVO":
                novos += 1
                ambiguos += bool(av)
                cid = novo()
                m.lembrar_cliente(cid, so_digitos(campo(fc, "CPF")),
                                  txt(campo(fc, "NOME") or campo(fp, "NOME")))
                assinatura[cid] = nascimento[cid] = None
            ass = M.data_iso(self.v(fc, fp, "ASSINATURA"))
            nasc, _ = M.data_br(self.v(fc, fp, "NASCIMENTO"), "n")
            assinatura[cid] = assinatura.get(cid) or ass
            nascimento[cid] = nascimento.get(cid) or nasc
        self._sim = dict(novos=novos, ambiguos=ambiguos, assinatura=assinatura, nascimento=nascimento)
        return self._sim

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
        self._criado = {}
        for r in copia:
            c = so_digitos(campo(r["fields"], "Nº PROCESSO"))
            fila = por_cnj.get(c) or []
            par = fila.pop(0) if fila else None
            if par:
                usados.add(par["id"])
            pares.append((r["fields"], par["fields"] if par else {}))
            self._criado[id(r["fields"])] = r.get("createdTime")
        for r in proc:
            if r["id"] not in usados:
                pares.append(({}, r["fields"]))
                self._criado[id(r["fields"])] = r.get("createdTime")
        self._pares = pares
        return pares

    def criado(self, fc, fp):
        """O createdTime do record que originou o par (CÓPIA, senão PROCESSUAL)."""
        self.pares()
        return self._criado.get(id(fc)) or self._criado.get(id(fp))

    _m = None

    def _regra(self):
        if Prova._m is None:
            Prova._m = M.Migracao.__new__(M.Migracao)
            Prova._m.hoje = self.hoje
        return Prova._m

    def v(self, fc, fp, nome):
        return self._regra().valor(fc, fp, nome)

    def fase(self, fc, fp):
        if not hasattr(self, "_fases"):
            self._fases = {}
        chave = id(fc), id(fp)
        if chave not in self._fases:
            self._fases[chave] = self._regra().fase_final(fc, fp)
        return self._fases[chave]

    def sit_exec(self, fc, fp):
        """A MESMA regra de `migrar.Migracao.situacao_execucao`, com a fase e a
        audiência que ela consulta — refeita da origem. Devolve o que a
        primeira função devolve; o complemento (CumPrSe, cálculo, pagamento)
        está em `sit_completa`."""
        par_aud, _ = N._traduz(N.AUDIENCIA, self.v(fc, fp, "AUDIENCIA"), "tipo")
        return self._regra().situacao_execucao(fc, fp, self.fase(fc, fp)[0],
                                               par_aud[0] if par_aud else None)

    def sit_completa(self, fc, fp):
        """situacao_execucao + completar_execucao, como a carga faz.
        Devolve (situacao, original, avisos_do_complemento, credito_cedido)."""
        s, orig, _, _ = self.sit_exec(fc, fp)
        return self._regra().completar_execucao(fc, fp, self.fase(fc, fp)[0], s, orig)

    def audiencia(self, fc, fp):
        par, _ = N._traduz(N.AUDIENCIA, self.v(fc, fp, "AUDIENCIA"), "tipo")
        return self._regra().situacao_audiencia(fc, fp, self.fase(fc, fp)[0], par[0] if par else None)

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

        # a modalidade da rescisão e o canal: foi a falta destas duas linhas que
        # deixou passar um trecho quebrado (90 rescisões indiretas viraram NULL)
        esperado = Counter()
        for r in pre:
            m, _ = N.rescisao(campo(r["fields"], "RESCISAO"))
            esperado[m or "(sem tradução)"] += 1 if campo(r["fields"], "RESCISAO") else 0
        self.comparar("modalidade da rescisão", esperado,
                      self.dist("SELECT COALESCE(rescisao_modalidade,'(sem tradução)'), COUNT(*) "
                                "FROM clientes WHERE origem_cadastro='PRE_PROCESSUAL' "
                                "AND rescisao_original IS NOT NULL GROUP BY 1"))
        esperado = Counter()
        for r in pre:
            par, _ = N._traduz(N.FONTE, campo(r["fields"], "FONTE"), "canal")
            if par:
                esperado["%s/%s" % (par[0], par[1] or "-")] += 1
        self.comparar("canal/campanha do lead", esperado,
                      self.dist("SELECT canal||'/'||COALESCE(campanha,'-'), COUNT(*) FROM clientes "
                                "WHERE canal IS NOT NULL GROUP BY 1"))
        esperado = Counter()
        for r in pre:
            for p in (campo(r["fields"], "PENDENCIAS") or []):
                if N.DOCUMENTO.get(p):
                    esperado[N.DOCUMENTO[p]] += 1
        self.comparar("documento pendente", esperado,
                      self.dist("SELECT documento_tipo, COUNT(*) FROM pendencias WHERE tipo='DOCUMENTO' "
                                "AND documento_tipo <> 'CONTRATO' GROUP BY 1"))
        esperado = Counter()
        vivos_ = [(fc, fp) for fc, fp in self.pares() if self.fase(fc, fp)[0]]
        for fc, fp in vivos_:
            t, _ = N.turma(self.v(fc, fp, "TURMA"))
            if t:
                esperado[t] += 1
        self.comparar("turma/órgão", esperado,
                      self.dist("SELECT turma, COUNT(*) FROM processos WHERE turma IS NOT NULL GROUP BY 1"))

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
            s = self.sit_completa(fc, fp)[0]
            if s:
                esperado[s] += 1
        self.comparar("situação da execução (STATUS EXECUÇÃO + CumPrSe + cálculo + pagamento)",
                      esperado,
                      self.dist("SELECT situacao_execucao, COUNT(*) FROM processos "
                                "WHERE situacao_execucao IS NOT NULL GROUP BY 1"))
        esperado = Counter()
        for fc, fp in vivos:
            orig = self.sit_completa(fc, fp)[1] or ""
            for nome in ("STATUS CumPrSe", "STATUS DO CALCULO", "STATUS PAGAMENTO"):
                if nome + ":" in orig:
                    esperado[nome] += 1
        self.comparar("  … completada por", esperado, {
            nome: self.q("SELECT COUNT(*) FROM processos WHERE situacao_execucao_original LIKE %s",
                         ("%" + nome + ":%",)) for nome in esperado})

        # o resultado final do processo: STATUS DO PROCESSO, STATUS EXECUÇÃO na
        # coluna errada e AUSÊNCIA (art. 844 CLT) — a mesma regra da carga
        esperado = Counter()
        for fc, fp in vivos:
            fase, res, _, _, _ = self.fase(fc, fp)
            apl = self.sit_exec(fc, fp)[3]
            if apl and apl[0] == "resultado_final" and not res:
                res = apl[1]
            if res:
                esperado[res] += 1
        self.comparar("resultado final do processo", esperado,
                      self.dist("SELECT resultado_final, COUNT(*) FROM processos "
                                "WHERE resultado_final IS NOT NULL GROUP BY 1"))

        # a situação da audiência migrada, pela evidência (Auditor: 2.649 do
        # passado nasciam DESIGNADA)
        esperado = Counter()
        for fc, fp in vivos:
            if self.v(fc, fp, "DATA AUDIENCIA") or self.v(fc, fp, "AUDIENCIA"):
                esperado[self.audiencia(fc, fp)[0]] += 1
        self.comparar("situação da audiência", esperado,
                      self.dist("SELECT situacao, COUNT(*) FROM audiencias GROUP BY 1"))
        self.checar("  … passada sem evidência → AUDIENCIA_SEM_RESULTADO",
                    sum(1 for fc, fp in vivos
                        if (self.v(fc, fp, "DATA AUDIENCIA") or self.v(fc, fp, "AUDIENCIA"))
                        and self.audiencia(fc, fp)[3]),
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='AUDIENCIA_SEM_RESULTADO'"))

        # REVOGAÇÃO, os dois sentidos, e a DATA REVOG que nunca fica sem coluna
        esperado, datas, contradicoes = Counter(), 0, 0
        for fc, fp in vivos:
            st_proc = self.v(fc, fp, "STATUS DO PROCESSO")
            destino, valor, avs, data, onde = self._regra().revogacao_destino(
                fc, fp, st_proc, self.fase(fc, fp)[2])
            if onde == "PROCESSO" and destino == "PROCESSO" and valor is not None:
                esperado["true" if valor else "false"] += 1
            datas += bool(data)
            contradicoes += sum(1 for a in avs if a["campo"] == "DATA REVOG")
        self.comparar("revogou o patrono anterior (sentido 1)", esperado,
                      self.dist("SELECT revogou_patrono_anterior::text, COUNT(*) FROM processos "
                                "WHERE revogou_patrono_anterior IS NOT NULL GROUP BY 1"))
        self.checar("DATA REVOG preenchida → gravada no processo ou no incidente", datas,
                    self.q("SELECT COUNT(revogacao_em) FROM processos")
                    + self.q("SELECT COUNT(revogacao_nos_autos_em) FROM incidentes"))
        self.checar("  … REVOGAÇÃO = NÃO com data → conferência", contradicoes,
                    self.q("SELECT COUNT(*) FROM conferencias WHERE campo='DATA REVOG'"))

        # o que os de/para declaravam e a carga não aplicava (Auditor, seção 1)
        self.checar("crédito cedido (STATUS PAGAMENTO = CESSAO)",
                    sum(1 for fc, fp in vivos if self.sit_completa(fc, fp)[3]),
                    self.q("SELECT COUNT(*) FROM processos WHERE credito_cedido"))
        self.checar("complexidade decidida à mão (fora da faixa do valor)",
                    sum(1 for fc, fp in vivos
                        if txt(self.v(fc, fp, "COMPLEXIDADE")) and centavos(self.v(fc, fp, "VALOR")) is not None
                        and N.complexidade_da_faixa(centavos(self.v(fc, fp, "VALOR"))) != txt(self.v(fc, fp, "COMPLEXIDADE"))),
                    self.q("SELECT COUNT(*) FROM processos WHERE complexidade_manual"))
        self.checar("trânsito registrado sem data → anotação",
                    sum(1 for fc, fp in vivos if self.fase(fc, fp)[3]),
                    self.q("SELECT COUNT(*) FROM anotacoes WHERE campo_origem='STATUS DO PROCESSO'"))
        cnjs = {so_digitos(campo(fc, "Nº PROCESSO") or campo(fp, "Nº PROCESSO")) for fc, fp in vivos}
        recs_proc = {r["id"] for r in self.corta(ler("processual"))}
        arquivados = Counter()
        for r in self.corta(ler("pos_processual")):
            f = r["fields"]
            if not (um_link(f, "PROCESSUAL") in recs_proc or so_digitos(campo(f, "N° DO PROCESSO")) in cnjs):
                continue
            arq = N.STATUS_ARQUIVAMENTO.get(campo(f, "STATUS ARQUIVAMENTO"))
            if arq and arq[0] in ("DATA", "NADA"):
                arquivados["true" if arq[0] == "DATA" else "false"] += 1
        self.comparar("pasta arquivada (PÓS, sem data)", arquivados,
                      self.dist("SELECT arquivado::text, COUNT(*) FROM processos "
                                "WHERE arquivado IS NOT NULL GROUP BY 1"))

        esperado = Counter()
        for fc, fp in vivos:
            par, _ = N._traduz(N.AUDIENCIA, self.v(fc, fp, "AUDIENCIA"), "tipo")
            if par and par[0]:
                esperado[par[0]] += 1
        self.comparar("tipo de audiência", esperado,
                      self.dist("SELECT tipo, COUNT(*) FROM audiencias WHERE tipo IS NOT NULL GROUP BY 1"))

        esperado = Counter()
        for fc, fp in vivos:
            o = Prova._m.resultado_sentenca(fc, fp)[2]     # inclui o complemento de ULTIMA DECISAO
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
        linhas = 0                      # uma por processo × base; o CNJ não serve de chave (106 sem número)
        for i, (fc, fp) in enumerate(vivos):
            for base, nome in (("TOTAL", "TOTAL RECEBIDO"), ("SUCUMBENCIA", "SUCUMB RECEBIDO"),
                               ("HONORARIOS", "HONOR TOTAL")):
                c = dinheiro(self.v(fc, fp, nome))
                if c:
                    esperado[base] += c
                    linhas += 1
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
                    linhas += 1
                    tem[base].add(cnj)
        for base in ("TOTAL", "SUCUMBENCIA", "HONORARIOS", "CLIENTE"):
            self.checar("recebido · %s" % base, esperado[base],
                        self.q("SELECT COALESCE(SUM(valor_centavos),0) FROM recebimentos "
                               "WHERE base='%s'" % base))
        self.checar("recebimentos (linhas: processo × base)", linhas,
                    self.q("SELECT COUNT(*) FROM recebimentos"))

        self.checar("valor estimado das fragilidades",
                    sum(dinheiro(campo(r["fields"], "VALOR ESTIMADO"))
                        for r in self.corta(ler("fragilidades"))),
                    self.q("SELECT COALESCE(SUM(valor_estimado_centavos),0) FROM fragilidades"))
        self.checar("valor da causa nos faltantes",
                    sum(dinheiro(campo(r["fields"], "VALOR")) for r in self.corta(ler("faltantes"))),
                    self.q("SELECT COALESCE(SUM(valor_causa_centavos),0) FROM conferencia_faltantes"))
        # o que não é dinheiro (número de processo no campo de valor) não some
        # calado: fica NULL, o original no bruto, e UMA conferência por ocorrência
        vivos = [(fc, fp) for fc, fp in self.pares() if self.fase(fc, fp)[0]]
        implausiveis = sum(1 for r in self.corta(ler("faltantes"))
                           if N.dinheiro(campo(r["fields"], "VALOR"))[1]) \
            + sum(1 for fc, fp in vivos if N.dinheiro(self.v(fc, fp, "VALOR"))[1])
        self.checar("valor implausível → conferência aberta", implausiveis,
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='VALOR_SEM_TRADUCAO' "
                           "AND campo='valor_causa_centavos'"))

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

        # o CNPJ da reclamada (CÓPIA) sobe para a empresa só quando é inequívoco
        por_emp, por_cnpj = defaultdict(set), defaultdict(set)
        for fc, fp in vivos:
            rec = um_link(fc, "EMPRESA") or um_link(fp, "EMPRESA")
            cnpj, _ = N.cnpj_razao(campo(fc, "CNPJ RECLAMADA"))
            if rec in empresas and cnpj:
                por_emp[rec].add(cnpj)
                por_cnpj[cnpj].add(rec)
        self.checar("empresas.cnpj (um CNPJ só nos processos dela)",
                    sum(1 for s in por_emp.values() if len(s) == 1),
                    self.q("SELECT COUNT(*) FROM empresas WHERE cnpj IS NOT NULL"))
        self.checar("EMPRESA_AMBIGUA (vários CNPJs, ou CNPJ em vários cadastros)",
                    sum(1 for s in por_emp.values() if len(s) > 1)
                    + sum(1 for s in por_cnpj.values() if len(s) > 1),
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='EMPRESA_AMBIGUA'"))
        self.checar("EMPRESA divergente entre CÓPIA e PROCESSUAL → conferência",
                    sum(1 for fc, fp in vivos if um_link(fc, "EMPRESA") and um_link(fp, "EMPRESA")
                        and um_link(fc, "EMPRESA") != um_link(fp, "EMPRESA")),
                    self.q("SELECT COUNT(*) FROM conferencias WHERE campo='EMPRESA'"))
        sit_emp = {}
        for r in self.corta(ler("empresas")):
            sit_emp[r["id"]] = N._traduz(N.SITUACAO_EMPRESA, campo(r["fields"], "STATUS EMPRESA"), "s")[0]
        desatualizadas = 0
        for fc, fp in vivos:
            a, b = um_link(fc, "EMPRESA"), um_link(fp, "EMPRESA")
            if a and b and a != b:
                continue
            rec = a or b
            lk = self.v(fc, fp, "SITU. EMPRESA")
            lk = lk[0] if isinstance(lk, list) and lk else lk
            if rec in empresas and lk:
                sit = N._traduz(N.SITUACAO_EMPRESA, lk, "s")[0]
                desatualizadas += bool(sit and sit != sit_emp.get(rec))
        self.checar("SITU. EMPRESA ≠ cadastro da reclamada → conferência", desatualizadas,
                    self.q("SELECT COUNT(*) FROM conferencias WHERE campo='SITU. EMPRESA'"))

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
        # STATUS EXECUÇÃO poluído ou na coluna errada: cada ocorrência ou virou
        # conferência ou foi aplicada onde era coerente — nunca ficou só no _original
        vivos = [(fc, fp) for fc, fp in self.pares() if self.fase(fc, fp)[0]]
        avisos = aplicados = extintas = cumprse_div = sem_nada = 0
        for fc, fp in vivos:
            s, orig, av, apl = self.sit_exec(fc, fp)
            s2, _, avs2, _ = self.sit_completa(fc, fp)
            if av:
                avisos += 1
            if apl:
                aplicados += 1
                if apl == ("resultado_final", "EXTINTA_SEM_RESOLUCAO") and not self.fase(fc, fp)[1]:
                    extintas += 1
            if (av or apl) and s2 is None:
                sem_nada += 1
            cumprse_div += sum(1 for a in avs2 if a["tipo"] == "DIVERGENCIA_FONTE")
        self.checar("STATUS EXECUÇÃO sem tradução → conferência", avisos,
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='VALOR_SEM_TRADUCAO' "
                           "AND campo='situacao_execucao'"))
        self.checar("STATUS EXECUÇÃO na coluna errada e nada a completou", sem_nada,
                    self.q("SELECT COUNT(*) FROM processos WHERE situacao_execucao IS NULL "
                           "AND situacao_execucao_original IS NOT NULL"))
        self.checar("  … dos quais EXTINTA virou resultado_final", extintas,
                    self.q("SELECT COUNT(*) FROM processos WHERE resultado_final='EXTINTA_SEM_RESOLUCAO'"))
        self.checar("CumPrSe/cálculo discordando da fase ou da execução → conferência", cumprse_div,
                    self.q("SELECT COUNT(*) FROM conferencias WHERE tipo='DIVERGENCIA_FONTE' "
                           "AND valor_a LIKE 'STATUS CumPrSe%' OR valor_a LIKE 'STATUS DO CALCULO%' "
                           "OR valor_a LIKE 'STATUS PAGAMENTO%'"))

        # --- nada inventado: o que a origem não tem está NULL, e o relógio é o da origem
        self.secao("NADA INVENTADO — estas linhas TÊM de dar zero")
        for rotulo, sql in (
                ("histórico da carga datado da carga (SLA zerado)",
                 "SELECT COUNT(*) FROM historico_etapas WHERE origem='MIGRACAO' AND substr(em,1,10) >= "
                 "substr((SELECT MAX(iniciada_em) FROM migracao_execucoes),1,10)"),
                ("histórico da carga anterior a 1990 ou posterior à leitura da origem",
                 "SELECT COUNT(*) FROM historico_etapas WHERE origem='MIGRACAO' "
                 "AND (substr(em,1,10) < '1990-01-01' OR substr(em,1,10) > %s)"),
                ("audiência DESIGNADA com data no passado",
                 "SELECT COUNT(*) FROM audiencias WHERE situacao='DESIGNADA' AND substr(data_hora,1,10) < %s"),
                ("cálculo com data de homologação (a origem não tem)",
                 "SELECT COUNT(*) FROM calculos WHERE homologado_em IS NOT NULL"),
                ("incidente com data de notificação ou de aviso (a origem não tem)",
                 "SELECT COUNT(*) FROM incidentes WHERE notificacao_redigida_em IS NOT NULL "
                 "OR notificacao_enviada_em IS NOT NULL OR notificacao_recebida_em IS NOT NULL "
                 "OR resposta_em IS NOT NULL OR cliente_avisado_em IS NOT NULL"),
                ("processo com data de trânsito (a origem não tem)",
                 "SELECT COUNT(*) FROM processos WHERE transito_em IS NOT NULL"),
                ("processo com data de arquivamento (a origem não tem)",
                 "SELECT COUNT(*) FROM processos WHERE arquivado_em IS NOT NULL"),
                ("acordo quebrado com data da quebra (a origem não tem)",
                 "SELECT COUNT(*) FROM acordos WHERE quebrado_em IS NOT NULL"),
                ("testemunha com data de confirmação (a origem não tem)",
                 "SELECT COUNT(*) FROM testemunhas WHERE confirmada_em IS NOT NULL"),
                ("processo ou cliente criado com a data da carga",
                 "SELECT (SELECT COUNT(*) FROM processos WHERE substr(criado_em,1,10) >= "
                 "substr((SELECT MAX(iniciada_em) FROM migracao_execucoes),1,10)) + "
                 "(SELECT COUNT(*) FROM clientes WHERE origem_cadastro='PROCESSO' AND substr(criado_em,1,10) >= "
                 "substr((SELECT MAX(iniciada_em) FROM migracao_execucoes),1,10))")):
            self.checar(rotulo, 0, self.q(sql, (self.hoje,) if "%s" in sql else None))
        # o histórico dos processos, ano a ano, pela MESMA regra da carga
        esperado = Counter()
        for fc, fp in vivos:
            fase = self.fase(fc, fp)[0]
            criado = self.criado(fc, fp)
            em, _ = self._regra().quando(self._regra().candidatos_processo(fase, fc, fp), criado)
            esperado[em[:4]] += 1
        self.comparar("histórico dos processos por ano de entrada na fase", esperado,
                      self.dist("SELECT substr(em,1,4), COUNT(*) FROM historico_etapas "
                                "WHERE origem='MIGRACAO' AND entidade='processos' GROUP BY 1"))
        self.secao("INTEGRIDADE (continuação)")

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
                         ("conferências abertas", "SELECT COUNT(*) FROM conferencias WHERE situacao='ABERTA'"),
                         ("contas de acesso preservadas", "SELECT COUNT(*) FROM usuarios"),
                         ("pendências de cadastro (CONTRATO + CADASTRO)",
                          "SELECT COUNT(*) FROM pendencias WHERE tipo='CADASTRO' OR documento_tipo='CONTRATO'"),
                         ("audiências passadas sem evidência", "SELECT COUNT(*) FROM conferencias WHERE tipo='AUDIENCIA_SEM_RESULTADO'"),
                         ("v_estagnados (antes: 0, SLA zerado)", "SELECT COUNT(*) FROM v_estagnados"),
                         ("v_audiencias_sem_preparacao (antes: 2.670)", "SELECT COUNT(*) FROM v_audiencias_sem_preparacao")):
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
