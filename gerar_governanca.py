#!/usr/bin/env python3
"""Escreve a documentação da governança A PARTIR DAS TABELAS, nunca do código.

    python3 gerar_governanca.py            # lê governanca.sql num SQLite em memória
    python3 gerar_governanca.py --banco    # lê o banco de verdade (banco.py), quando existir

A governança do sistema é dado, não código: vive em `fluxos`, `fluxo_etapas` e
`fluxo_transicoes`. Documentar isso à mão seria criar uma segunda verdade que
envelhece na primeira vez que alguém mexer no mapa. Este script lê o mapa e
reescreve os arquivos — se a etapa mudar, rode de novo e a documentação acompanha.

Enquanto o banco do trabalhista não existe, a fonte é o próprio `governanca.sql`:
a parte de cima (DDL + INSERTs) é carregada num SQLite em memória, com duas
traduções de dialeto (identity → INTEGER PRIMARY KEY; default de data). A parte
de baixo, marcada ">>> SÓ POSTGRES", são os gatilhos em PL/pgSQL e as views —
não entra aqui.

Gera:
    docs/governanca.md          uma seção por fluxo, etapa por etapa
    docs/bpmn/<fluxo>.md        o diagrama em Mermaid
    docs/bpmn/README.md         os cinco fluxos em texto corrido, para quem não é técnico
"""
import os
import re
import sqlite3
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(AQUI, "docs")
BPMN = os.path.join(DOCS, "bpmn")
SQL = os.path.join(AQUI, "governanca.sql")
MARCA = "-- >>> SÓ POSTGRES DAQUI PARA BAIXO"


def _id(codigo):
    """Mermaid não aceita acento nem hífen no id do nó; o rótulo aceita."""
    return codigo.replace("-", "_")


def abrir_do_sql():
    """Carrega a metade portável do governanca.sql num SQLite em memória."""
    texto = open(SQL, encoding="utf-8").read()
    parte = texto.split(MARCA, 1)[0]
    parte = re.sub(r"BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY", "INTEGER PRIMARY KEY", parte)
    parte = re.sub(r"DEFAULT to_char\(now\(\) AT TIME ZONE '[^']+','[^']+'\)",
                   "DEFAULT (datetime('now','localtime'))", parte)
    db = sqlite3.connect(":memory:")
    db.executescript(parte)
    return db


def abrir_do_banco():
    import banco  # a ponte sqlite→psycopg herdada do Prev
    return banco.conectar()


def ler(db):
    """Os fluxos, com suas etapas e transições, como estão no banco."""
    fluxos = []
    for f in db.execute("SELECT id, codigo, nome, entidade, coluna FROM fluxos ORDER BY id"):
        etapas = db.execute("""SELECT codigo, nome, ordem, tipo, sla_dias, grupo, texto_operador
                               FROM fluxo_etapas WHERE fluxo_id=? ORDER BY ordem""", (f[0],)).fetchall()
        trans = db.execute("""SELECT de, para, acao, papel, exige, texto_bloqueio
                              FROM fluxo_transicoes WHERE fluxo_id=? ORDER BY de, para""",
                           (f[0],)).fetchall()
        fluxos.append(dict(id=f[0], codigo=f[1], nome=f[2], entidade=f[3], coluna=f[4],
                           etapas=list(map(tuple, etapas)), trans=list(map(tuple, trans))))
    return fluxos


def ler_prazo_tipos(db):
    try:
        return [tuple(r) for r in db.execute(
            "SELECT codigo, nome, dias, dias_padrao, fundamento, fase_usual, observacao "
            "FROM prazo_tipos ORDER BY fase_usual NULLS LAST, codigo")]
    except sqlite3.OperationalError:
        return [tuple(r) for r in db.execute(
            "SELECT codigo, nome, dias, dias_padrao, fundamento, fase_usual, observacao "
            "FROM prazo_tipos ORDER BY fase_usual IS NULL, fase_usual, codigo")]


def conferir(fluxos):
    """O que o mapa promete: uma inicial por fluxo, pelo menos uma final,
    toda transição aponta para etapa que existe, toda etapa não final tem saída."""
    erros = []
    for f in fluxos:
        cods = {e[0] for e in f["etapas"]}
        ini = [e for e in f["etapas"] if e[3] == "INICIAL"]
        fim = [e for e in f["etapas"] if e[3] == "FINAL"]
        if len(ini) != 1:
            erros.append(f"{f['codigo']}: {len(ini)} etapas iniciais (tem de ser 1)")
        if not fim:
            erros.append(f"{f['codigo']}: nenhuma etapa final")
        for de, para, *_ in f["trans"]:
            if de not in cods or para not in cods:
                erros.append(f"{f['codigo']}: transição {de} → {para} aponta para etapa inexistente")
        com_saida = {t[0] for t in f["trans"]}
        for e in f["etapas"]:
            if e[3] != "FINAL" and e[0] not in com_saida:
                erros.append(f"{f['codigo']}: etapa {e[0]} não é final e não tem saída")
    return erros


def governanca(fluxos, prazo_tipos):
    L = ["# Governança — as cinco máquinas de estado do escritório trabalhista", "",
         "> Gerado por `gerar_governanca.py` **a partir das tabelas** `fluxos`, `fluxo_etapas`,",
         "> `fluxo_transicoes` e `prazo_tipos` (hoje lidas de `governanca.sql`). Não editar à mão:",
         "> rode o script de novo depois de mexer no mapa. A prosa para o Lucas aprovar está em",
         "> `governanca-para-confirmar.md`; o que cada opção do Airtable virou está em `etapa-ou-atributo.md`.",
         "",
         "A regra não mora na tela nem no código. Mora no banco, e vale para qualquer caminho que",
         "chegue até ele — sistema, script, migração ou mão humana no `psql`. Transição que não",
         "estiver na tabela é recusada por gatilho, com `RAISE EXCEPTION`, não corrigida em silêncio.", ""]
    tot_e = sum(len(f["etapas"]) for f in fluxos)
    tot_t = sum(len(f["trans"]) for f in fluxos)
    L += [f"**{len(fluxos)} fluxos · {tot_e} etapas · {tot_t} transições · {len(prazo_tipos)} tipos de prazo.**",
          "", "---", ""]

    for f in fluxos:
        L += [f"## {f['nome']} (`{f['codigo']}`)", "",
              f"Governa `{f['entidade']}.{f['coluna']}` · {len(f['etapas'])} etapas · "
              f"{len(f['trans'])} transições.", ""]
        for e in f["etapas"]:
            cod, nome, ordem, tipo, sla, grupo, texto = e
            sla_txt = f"{sla} dias" if sla else "—"
            L += [f"### {ordem}. {nome} — `{cod}`", "",
                  "| | |", "|---|---|",
                  f"| tipo | {tipo} |",
                  f"| prazo interno (SLA) | {sla_txt} |",
                  f"| setor responsável | {grupo or '**(sem grupo)**'} |", ""]
            if texto:
                L += [f"**O que fazer aqui:** {texto}", ""]
            saidas = [t for t in f["trans"] if t[0] == cod]
            if not saidas:
                L += ["*Etapa final: não há saída.*", ""]
            else:
                L += ["| vai para | ação | quem pode | exige | por que trava |",
                      "|---|---|---|---|---|"]
                for _, para, acao, papel, exige, bloq in saidas:
                    nome_destino = next((x[1] for x in f["etapas"] if x[0] == para), para)
                    L.append(f"| **{nome_destino}** (`{para}`) | {acao} | {papel or 'qualquer'} "
                             f"| {exige or '—'} | {bloq or '—'} |")
                L.append("")
        L += ["---", ""]

    if prazo_tipos:
        L += ["## Tipos de prazo (`prazo_tipos`)", "",
              "Contagem em **dias úteis** (CLT art. 775), a partir do primeiro dia útil depois da",
              "publicação no DEJT (Lei 11.419/2006, art. 4º §§ 3º–4º). `dias` vazio = o juízo fixa;",
              "`padrão` é o que o sistema propõe e a pessoa pode corrigir (a correção fica no histórico).", "",
              "| código | prazo | dias | padrão | fundamento | fase usual | observação |",
              "|---|---|---|---|---|---|---|"]
        for cod, nome, dias, padrao, fund, fase, obs in prazo_tipos:
            L.append(f"| `{cod}` | {nome} | {dias if dias else 'juízo fixa'} | {padrao} | {fund} "
                     f"| {fase or '—'} | {obs or '—'} |")
        L.append("")
    return "\n".join(L)


def mermaid(f):
    """Um diagrama por fluxo, direto das transições."""
    L = [f"# {f['nome']} — diagrama", "",
         f"> Gerado de `fluxo_transicoes` por `gerar_governanca.py`. Governa "
         f"`{f['entidade']}.{f['coluna']}`.", "",
         "```mermaid", "flowchart TD"]
    for cod, nome, ordem, tipo, sla, grupo, _ in f["etapas"]:
        rot = f"{nome}<br/><small>{grupo or 'sem setor'}"
        rot += f" · {sla}d</small>" if sla else "</small>"
        if tipo == "INICIAL":
            L.append(f'    {_id(cod)}(["{rot}"])')
        else:
            L.append(f'    {_id(cod)}["{rot}"]')
    L.append("")
    for de, para, acao, papel, exige, _ in f["trans"]:
        rot = acao or ""
        if papel:
            rot += f" ({papel})"
        if exige:
            rot += " 🔒"
        L.append(f'    {_id(de)} -->|"{rot}"| {_id(para)}')
    L.append("")
    ini = [_id(e[0]) for e in f["etapas"] if e[3] == "INICIAL"]
    fim = [_id(e[0]) for e in f["etapas"] if e[3] == "FINAL"]
    if ini:
        L += ["    classDef inicial fill:#dcfce7,stroke:#16a34a,color:#14532d",
              f"    class {','.join(ini)} inicial"]
    if fim:
        L += ["    classDef final fill:#e5e7eb,stroke:#6b7280,color:#374151",
              f"    class {','.join(fim)} final"]
    L += ["```", "",
          "🔒 = a ação só aparece quando o pré-requisito está cumprido. O que cada um exige está",
          "em [`../governanca.md`](../governanca.md).", ""]
    return "\n".join(L)


def leigo(fluxos):
    """Os fluxos em texto corrido, para quem não é técnico."""
    L = ["# Como o escritório trabalha, em cinco fluxos", "",
         "> Gerado a partir do próprio sistema por `gerar_governanca.py`. O que está escrito aqui",
         "> é o que o software realmente faz — não é folheto.", "",
         "Todo caso caminha por etapas, e o sistema **não deixa pular etapa**. Não é recomendação na",
         "tela: é regra dentro do banco, que recusa a mudança mesmo por fora do sistema. São cinco",
         "caminhos, e um caso percorre vários ao mesmo tempo — o processo anda enquanto uma audiência",
         "se prepara e um prazo corre.", ""]
    intro = {
        "CLIENTE": ("Do primeiro contato à distribuição da inicial",
                    "Começa quando alguém liga ou o captador traz. Com contrato e procuração assinados, "
                    "a Documentação reúne TRCT, CTPS, holerites e FGTS; a entrevista levanta os fatos e as "
                    "testemunhas; o Jurídico redige a inicial, alguém aprova e ela é distribuída. O relógio "
                    "aqui é a prescrição de dois anos da saída — e, na rescisão indireta, o contrato que "
                    "ainda está correndo."),
        "PROCESSO": ("O processo, da distribuição ao arquivo",
                     "Conhecimento (audiências, defesa, perícias, sentença), recursal (TRT e TST), execução "
                     "provisória enquanto a reclamada recorre, execução definitiva depois do trânsito, acordo "
                     "em qualquer ponto, recebimento e repasse ao cliente antes de encerrar. Cliente que "
                     "troca de advogado não muda a fase do processo: vira um incidente com ciclo próprio."),
        "AUDIENCIA": ("Cada audiência",
                      "Designada, preparada (cliente orientado, testemunhas confirmadas, ad video feito, "
                      "documentos), realizada, redesignada, adiada ou não realizada. Audiência a menos de uma "
                      "semana sem preparação acende alerta."),
        "PRAZO": ("Cada prazo",
                  "Nasce da publicação no DEJT, da intimação ou da ata; conta em dias úteis (CLT art. 775) "
                  "com os feriados do TRT e o recesso; é cumprido com protocolo registrado, suspenso, sem "
                  "objeto ou — só por gestor, com motivo — perdido."),
        "INCIDENTE": ("Cliente que trocou de advogado",
                      "Detectado nos autos, notificado extrajudicialmente, honorários reservados no juízo, "
                      "e o desfecho: cliente recuperado, honorários recebidos ou perdido."),
    }
    for f in fluxos:
        titulo, texto = intro.get(f["codigo"], (f["nome"], ""))
        L += [f"## {titulo}", "", texto, "",
              "**As etapas, em ordem:** " +
              " → ".join(e[1] for e in f["etapas"] if e[3] != "FINAL") + ".", ""]
        finais = [e[1] for e in f["etapas"] if e[3] == "FINAL"]
        if finais:
            L += [f"**Como termina:** {', '.join(finais)}.", ""]
        L += [f"O diagrama completo está em [`{f['codigo'].lower()}.md`]({f['codigo'].lower()}.md).", ""]
    L += ["---", "",
          "## O que isso garante na prática", "",
          "- **Nada pula etapa.** A regra está no banco, não na tela.",
          "- **Toda mudança fica registrada** — quem moveu, quando, de onde para onde e por quê.",
          "- **Prazo é contado pela lei**: dias úteis (CLT art. 775), da publicação no DEJT, com os",
          "  feriados do TRT e o recesso de 20/12 a 20/01.",
          "- **Ação depois da prescrição bienal é barrada pelo banco**, salvo dispensa justificada.",
          "- **A máquina propõe, a pessoa decide.** Nenhuma automação protocola peça nem move etapa.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    db = abrir_do_banco() if "--banco" in sys.argv else abrir_do_sql()
    fluxos = ler(db)
    prazo_tipos = ler_prazo_tipos(db)
    erros = conferir(fluxos)
    if erros:
        print("MAPA INCONSISTENTE:")
        for e in erros:
            print("  -", e)
        sys.exit(1)
    os.makedirs(BPMN, exist_ok=True)
    open(os.path.join(DOCS, "governanca.md"), "w", encoding="utf-8").write(governanca(fluxos, prazo_tipos))
    for f in fluxos:
        open(os.path.join(BPMN, f"{f['codigo'].lower()}.md"), "w", encoding="utf-8").write(mermaid(f))
    open(os.path.join(BPMN, "README.md"), "w", encoding="utf-8").write(leigo(fluxos))
    e = sum(len(f["etapas"]) for f in fluxos)
    t = sum(len(f["trans"]) for f in fluxos)
    print(f"✓ docs/governanca.md · {len(fluxos)} fluxos, {e} etapas, {t} transições, {len(prazo_tipos)} tipos de prazo")
    print(f"✓ docs/bpmn/ · {len(fluxos)} diagramas + README")
    for f in fluxos:
        print(f"   {f['codigo']:<10} {len(f['etapas']):>2} etapas {len(f['trans']):>2} transições")
    db.close()
