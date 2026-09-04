#!/usr/bin/env python3
"""Setor e organograma — o que a base de origem não guarda, editado na TELA.

A origem (FUNCIONARIOS, 72 registros) tem FUNÇÕES — advogado, captador,
entrevistador, responsável inicial — e não tem setor nem organograma. Até
03/09/2026 o buraco era tapado por duas constantes escritas aqui (AJUSTES e
CHEFIA), deixadas vazias de propósito porque organograma inventado manda tarefa
para a pessoa errada.

**Resposta 30 do Lucas mudou o lugar disso.** Os oito setores estão fechados e
são os mesmos que a governança já usa; a hierarquia muda com o tempo e não pode
depender de programador. Então:

  · a lista de setores sai do BANCO (`fluxo_etapas.grupo`), nunca escrita aqui
    nem no template — se um dia o mapa ganhar um setor, a tela ganha junto;
  · `pessoas.setor` e `pessoas.supervisor_id` se editam na ficha da pessoa
    (`/equipe/{id}`), e toda alteração deixa linha em `auditoria`;
  · AJUSTES e CHEFIA deixaram de existir. Organograma em código é organograma
    que só um programador conserta, que é justamente o que o Lucas pediu para
    acabar. O preenchimento em lote dos 72 é `equipe_setores.py`, que lê a
    planilha uma vez — depois dela, a fonte é a tela.

Este módulo é o que as rotas usam: ele valida contra o banco e escreve o rastro.
Nenhuma regra daqui vive no template.
"""
import auth
import banco
from normalizar import norm


# --------------------------------------------------------------- os setores
def setores(db):
    """Os setores do escritório, LIDOS DO BANCO.

    São os grupos de `fluxo_etapas.grupo`: os oito que o Lucas fechou na
    resposta 30 (Captação, Atendimento, Documentação, Petição Inicial,
    Jurídico, Financeiro, Gestão, Direção) e os mesmos por onde o mapa diz qual
    setor responde por qual etapa. Ler daqui é o que garante que a tela nunca
    ofereça um setor que a governança não conhece — e o contrário, que um setor
    novo no mapa apareça no cadastro sem ninguém tocar em código.
    """
    return [r[0] for r in db.execute(
        """SELECT DISTINCT grupo FROM fluxo_etapas
           WHERE grupo IS NOT NULL AND grupo <> '' ORDER BY grupo""").fetchall()]


def setor_da_etapa(grupo):
    """O setor do escritório que responde por uma etapa do mapa.

    Antes da resposta 30 havia DUAS listas — a de doze que o diretor passou e a
    de oito de `fluxo_etapas.grupo` — e esta função traduzia uma na outra. O
    Lucas fechou a lista nos oito da governança, então as duas viraram a mesma
    e aqui não há mais o que traduzir. A função fica porque sete telas a usam
    como filtro: tirá-la seria mexer em sete templates para não mudar nada.
    """
    return grupo


def _chave(s):
    """'Petição Inicial' → 'peticao_inicial'. Só para casar nome de gate."""
    return norm(s).lower().replace(" ", "_").replace("/", "_")


def setor_do_gate(db, gate):
    """Qual setor o gate `setor_...` de `fluxo.py` exige — descoberto, não escrito.

    `setor_peticao_inicial` casa com 'Petição Inicial' porque os nomes
    normalizados batem. Assim a explicação da ficha ("pertence a Petição
    Inicial, então pode aprovar minuta") nasce do MAPA: se amanhã existir um
    gate `setor_financeiro`, a ficha o explica sem alteração nenhuma aqui.
    """
    if not gate or not gate.startswith("setor_"):
        return None
    alvo = gate[len("setor_"):]
    for s in setores(db):
        if _chave(s) == alvo:
            return s
    return None


# ----------------------------------------------------------------- a pessoa
def pessoa(db, pid):
    """A ficha: a pessoa, quem é o chefe dela, e a conta de acesso, se houver."""
    return db.execute("""SELECT p.*, s.nome supervisor, s.setor supervisor_setor,
                                u.id usuario_id, u.email, u.papel, u.ativo conta_ativa,
                                u.trocar_senha, u.ultimo_acesso
                         FROM pessoas p
                         LEFT JOIN pessoas s ON s.id = p.supervisor_id
                         LEFT JOIN usuarios u ON u.pessoa_id = p.id
                         WHERE p.id=?""", (pid,)).fetchone()


def papeis(db, pid):
    """Os papéis que vieram do Airtable. Só leitura: a origem é que os diz."""
    return [r[0] for r in db.execute(
        "SELECT papel FROM pessoa_papeis WHERE pessoa_id=? ORDER BY papel", (pid,)).fetchall()]


def subordinados(db, pid):
    """Quem responde a esta pessoa, direto. Com a carga de cada um ao lado."""
    return db.execute("""SELECT p.id, p.nome, p.setor, p.ativo,
                (SELECT COUNT(*) FROM tarefas t WHERE t.responsavel_id=p.id
                   AND t.status IN ('ABERTA','EM_ANDAMENTO')) abertas
             FROM pessoas p WHERE p.supervisor_id=?
             ORDER BY (NOT p.ativo), p.nome""", (pid,)).fetchall()


def cadeia_acima(db, pid, teto=60):
    """Os chefes, subindo. Para sozinha em ciclo já gravado — não roda para sempre.

    O ciclo não deveria existir (é o que a validação impede), mas dado velho
    entra por carga, e uma tela que trava é pior que uma tela que mostra a
    volta.
    """
    caminho, atual = [], pid
    while len(caminho) < teto:
        r = db.execute("SELECT supervisor_id FROM pessoas WHERE id=?", (atual,)).fetchone()
        atual = r[0] if r else None
        if not atual or atual == pid or atual in caminho:
            break
        caminho.append(atual)
    return caminho


def descendentes(db, pid):
    """Todo mundo que está ABAIXO desta pessoa, direto ou não.

    Serve para a lista de chefes possíveis não oferecer quem a escolha
    recusaria: pendurar A embaixo de alguém que já responde a A fecha o laço.
    `UNION` (e não `UNION ALL`) é de propósito — se um ciclo já existir no dado
    velho, a recursão para sozinha em vez de rodar para sempre.
    """
    return [r[0] for r in db.execute(
        """WITH RECURSIVE abaixo AS (
             SELECT id FROM pessoas WHERE supervisor_id = ?
             UNION
             SELECT p.id FROM pessoas p JOIN abaixo a ON p.supervisor_id = a.id)
           SELECT id FROM abaixo""", (pid,)).fetchall()]


def criaria_ciclo(db, pid, chefe_id):
    """A responde a B e B a A é organograma que não fecha — e trava a leitura.

    Vale para a volta curta (A→B→A) e para a longa (A→B→C→A): a pergunta é se
    `pid` já está ACIMA de `chefe_id`. Se estiver, pendurar `pid` embaixo dele
    fecha o laço.
    """
    if not chefe_id:
        return False
    if int(chefe_id) == int(pid):
        return True
    return int(pid) in [int(x) for x in cadeia_acima(db, chefe_id)]


def carga_de(db, pid):
    """O trabalho que está com a pessoa. Cada número sai de uma consulta.

    São três coisas diferentes e a ficha não as soma: tarefa é o que ela tem de
    fazer, processo é onde ela assina, cliente é de quem ela cuida. Um total
    único esconderia justamente a diferença que importa para decidir setor.
    """
    return db.execute("""SELECT
        (SELECT COUNT(*) FROM tarefas t WHERE t.responsavel_id=?
           AND t.status IN ('ABERTA','EM_ANDAMENTO')) tarefas_abertas,
        (SELECT COUNT(*) FROM tarefas t WHERE t.responsavel_id=?
           AND t.status IN ('ABERTA','EM_ANDAMENTO')
           AND t.prazo IS NOT NULL AND t.prazo < date('now')) tarefas_atrasadas,
        (SELECT COUNT(*) FROM processos p WHERE p.advogado_id=?) processos,
        (SELECT COUNT(*) FROM clientes c WHERE c.responsavel_id=?) clientes,
        (SELECT COUNT(*) FROM audiencias a JOIN processos p ON p.id=a.processo_id
           WHERE a.responsavel_id=? AND a.situacao NOT IN ('REALIZADA','CANCELADA')) audiencias,
        (SELECT COUNT(*) FROM prazos z WHERE z.responsavel_id=?
           AND z.situacao='ABERTO') prazos
        """, (pid, pid, pid, pid, pid, pid)).fetchone()


def etapas_do_setor(db, setor):
    """As etapas que o mapa põe na mão deste setor, com quantos registros estão nelas.

    É a resposta a "o que muda por eu ser da Documentação": muda a fila que cai
    no seu colo. O número vem de `v_funil_etapas`, que é consulta — não conta
    do template.
    """
    if not setor:
        return []
    return db.execute("""SELECT f.codigo fluxo, e.codigo, e.nome, e.ordem, e.sla_dias,
                                v.registros
                         FROM fluxo_etapas e
                         JOIN fluxos f ON f.id = e.fluxo_id
                         LEFT JOIN v_funil_etapas v
                                ON v.fluxo = f.codigo AND v.codigo = e.codigo
                         WHERE e.grupo=? ORDER BY f.id, e.ordem""", (setor,)).fetchall()


def poderes(db, papel, setor):
    """O que a pessoa pode e não pode MOVER no sistema, lido de `fluxo_transicoes`.

    Nada disto é escrito no template. Cada linha do mapa traz o papel exigido
    (`fluxo_transicoes.papel`, hierarquia de `auth.py`) e os gates
    (`fluxo_transicoes.exige`); os gates que começam por `setor_` são os que
    dependem de a pessoa PERTENCER a um setor — hoje só a aprovação da inicial,
    amanhã o que o arquiteto escrever.

    Os gates de DADO (minuta anexada, motivo escrito) não entram: eles não
    falam da pessoa, falam do caso. Dizer "você não pode aprovar" a quem só
    precisa anexar a minuta seria mentir sobre a permissão.

    Devolve três listas: o que pode mover, o que não pode (com o porquê), e —
    separada — a curta lista das ações que dependem de SETOR. É essa terceira
    que responde à pergunta do Lucas ("o que muda se eu puser esta pessoa em
    Petição Inicial?"), e ela se perde no meio de cem transições.
    """
    linhas = db.execute("""SELECT f.codigo fluxo, f.nome fluxo_nome, t.acao, t.papel,
                                  t.exige, de.nome de_nome, pa.nome para_nome,
                                  de.ordem de_ordem, pa.ordem pa_ordem
                           FROM fluxo_transicoes t
                           JOIN fluxos f ON f.id = t.fluxo_id
                           LEFT JOIN fluxo_etapas de
                                  ON de.fluxo_id=t.fluxo_id AND de.codigo=t.de
                           LEFT JOIN fluxo_etapas pa
                                  ON pa.fluxo_id=t.fluxo_id AND pa.codigo=t.para
                           ORDER BY f.id, de.ordem, pa.ordem""").fetchall()
    pode, nao, pelo_setor = [], [], []
    for t in linhas:
        exigidos = [e.strip() for e in (t["exige"] or "").split(",") if e.strip()]
        setores_exigidos = [s for s in (setor_do_gate(db, e) for e in exigidos) if s]
        porques = []
        if not papel:
            porques.append("esta pessoa não tem conta de acesso")
        elif not auth.pode(papel, t["papel"]):
            porques.append(f"a ação é de {(t['papel'] or '').lower()} e o perfil aqui "
                           f"é {papel.lower()}")
        for s in setores_exigidos:
            if setor != s:
                porques.append(f"a ação é do setor {s}" +
                               (f", e o setor aqui é {setor}" if setor else ", e esta pessoa "
                                "ainda não tem setor"))
        item = dict(fluxo=t["fluxo_nome"], acao=t["acao"], de=t["de_nome"],
                    para=t["para_nome"], papel=t["papel"],
                    setor_exigido=setores_exigidos[0] if setores_exigidos else None,
                    porque="; ".join(porques) or None)
        item["pode"] = not porques
        (nao if porques else pode).append(item)
        if setores_exigidos:
            pelo_setor.append(item)
    return pode, nao, pelo_setor


# ------------------------------------------------------------------ escrita
def _auditar(db, tabela, rid, campo, antigo, novo, quem):
    """A linha de rastro. Sempre a mesma forma: de que para que, e quem mudou.

    `valor_antigo`/`valor_novo` guardam TEXTO, inclusive para o id do chefe:
    quem lê a auditoria seis meses depois quer o nome, e o nome não estava lá.
    Por isso quem chama passa o texto já resolvido.
    """
    db.execute("""INSERT INTO auditoria (tabela, registro_id, acao, campo,
                    valor_antigo, valor_novo, pessoa_id)
                  VALUES (?,?, 'UPDATE', ?,?,?,?)""",
               (tabela, rid, campo, antigo, novo, quem))


def _nome(db, pid):
    if not pid:
        return None
    r = db.execute("SELECT nome FROM pessoas WHERE id=?", (pid,)).fetchone()
    return r[0] if r else None


def mudar_setor(db, pid, novo, quem):
    """Grava o setor. Levanta ValueError com a frase de quem clicou.

    O valor é conferido contra a lista DO BANCO, não contra o `<select>`: o
    POST não vem só do `<select>`, e um setor que a governança não conhece
    deixaria a pessoa fora de toda fila sem ninguém perceber.
    """
    novo = (novo or "").strip() or None
    if novo and novo not in setores(db):
        raise ValueError(f"“{novo[:40]}” não é um setor do escritório — escolha um da lista")
    antes = db.execute("SELECT setor FROM pessoas WHERE id=?", (pid,)).fetchone()
    if not antes:
        raise ValueError("esta pessoa não está no cadastro")
    if (antes[0] or None) == novo:
        return False, "o setor já era esse"
    db.execute("UPDATE pessoas SET setor=? WHERE id=?", (novo, pid))
    _auditar(db, "pessoas", pid, "setor", antes[0], novo, quem)
    db.commit()
    return True, f"setor: {antes[0] or 'sem setor'} → {novo or 'sem setor'}"


def mudar_chefe(db, pid, chefe_id, quem):
    """Grava a quem a pessoa responde. Recusa a si mesma e recusa ciclo."""
    chefe_id = int(chefe_id) if chefe_id else None
    if chefe_id == int(pid):
        raise ValueError("ninguém responde a si mesmo — escolha outra pessoa, "
                         "ou deixe em branco")
    if chefe_id:
        alvo = db.execute("SELECT nome, ativo FROM pessoas WHERE id=?", (chefe_id,)).fetchone()
        if not alvo:
            raise ValueError("escolha a pessoa na lista — o valor recebido não é um "
                             "cadastro do escritório")
        if not alvo["ativo"]:
            raise ValueError(f"{alvo['nome']} está inativa e não pode chefiar ninguém")
        if criaria_ciclo(db, pid, chefe_id):
            # a volta é lida de quem foi escolhido para cima, até esbarrar em
            # `pid`: é assim que ela conta a história ("ela já responde a você")
            acima, volta = cadeia_acima(db, chefe_id), [chefe_id]
            for x in acima:
                volta.append(x)
                if int(x) == int(pid):
                    break
            volta = " → ".join([_nome(db, x) or "?" for x in volta[:6]])
            raise ValueError("isso fecharia um laço na chefia (" + volta + "): a pessoa "
                             "escolhida já responde, direta ou indiretamente, a esta. "
                             "Desfaça o outro lado primeiro")
    antes = db.execute("SELECT supervisor_id FROM pessoas WHERE id=?", (pid,)).fetchone()
    if not antes:
        raise ValueError("esta pessoa não está no cadastro")
    if (antes[0] or None) == chefe_id:
        return False, "a chefia já era essa"
    db.execute("UPDATE pessoas SET supervisor_id=? WHERE id=?", (chefe_id, pid))
    _auditar(db, "pessoas", pid, "supervisor_id",
             _nome(db, antes[0]), _nome(db, chefe_id), quem)
    db.commit()
    return True, (f"responde a: {_nome(db, antes[0]) or 'ninguém'} → "
                  f"{_nome(db, chefe_id) or 'ninguém'}")


def perfis(db):
    """Os perfis que a conta aceita — lidos do CHECK da coluna `usuarios.papel`.

    A lista mora no esquema, e é ela que `fluxo_transicoes.papel` cobra. Ler do
    banco em vez de repetir aqui evita a tela oferecer um perfil que o INSERT
    recusaria — e evita o inverso, mais silencioso: um perfil novo no esquema
    que a tela nunca mostra.
    """
    import re
    r = db.execute("""SELECT pg_get_constraintdef(c.oid) d
                      FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
                      WHERE t.relname='usuarios' AND c.contype='c'
                        AND pg_get_constraintdef(c.oid) LIKE '%papel%'""").fetchone()
    achados = re.findall(r"'([A-Z_]+)'", r[0]) if r else []
    # a ordem do CHECK é a do esquema; a de auth.PERFIS é a de menos para mais
    # poder, que é como se lê numa lista de escolha
    ordem = list(auth.PERFIS)
    return sorted(set(achados) or set(ordem),
                  key=lambda p: ordem.index(p) if p in ordem else 99)


def mudar_perfil(db, pid, papel, quem):
    """Troca o perfil de acesso. Só a Direção chega aqui — a rota confere isso.

    A pessoa sem conta não tem perfil para trocar: abrir acesso é outro ato
    (`auth.py equipe`), que gera senha provisória e a mostra uma vez.
    """
    papel = (papel or "").strip()
    if papel not in perfis(db):
        raise ValueError(f"“{papel[:30]}” não é um perfil de acesso — escolha um da lista")
    conta = db.execute("SELECT id, papel FROM usuarios WHERE pessoa_id=?", (pid,)).fetchone()
    if not conta:
        raise ValueError("esta pessoa ainda não tem conta de acesso; abrir acesso é outro "
                         "ato (auth.py equipe), que gera a senha provisória")
    if conta["papel"] == papel:
        return False, "o perfil já era esse"
    #  A última conta de direção não sai por aqui. Tirá-la deixaria o sistema
    #  sem ninguém para reabrir processo encerrado E sem ninguém para devolver
    #  este mesmo perfil — um beco sem saída que só se desfaz no psql. É o modo
    #  de falha silencioso de sempre: nada quebra na hora, e falta na hora certa.
    if conta["papel"] == "DIRECAO" and papel != "DIRECAO":
        sobram = db.execute("""SELECT COUNT(*) FROM usuarios
                               WHERE papel='DIRECAO' AND ativo = true AND id <> ?""",
                            (conta["id"],)).fetchone()[0]
        if not sobram:
            raise ValueError("esta é a última conta com perfil de direção. Tirá-la deixaria o "
                             "sistema sem quem reabre processo encerrado — e sem quem devolva "
                             "este perfil a alguém. Promova outra pessoa antes")
    db.execute("UPDATE usuarios SET papel=? WHERE id=?", (papel, conta["id"]))
    _auditar(db, "usuarios", conta["id"], "papel", conta["papel"], papel, quem)
    db.commit()
    return True, f"perfil: {conta['papel'].lower()} → {papel.lower()}"


def rastro(db, pid, usuario_id=None, limite=30):
    """O que já mudou nesta ficha, com quem mudou. Vem de `auditoria`."""
    return db.execute("""SELECT a.*, q.nome quem FROM auditoria a
                         LEFT JOIN pessoas q ON q.id = a.pessoa_id
                         WHERE (a.tabela='pessoas' AND a.registro_id=?)
                            OR (a.tabela='usuarios' AND a.registro_id=?)
                         ORDER BY a.em DESC, a.id DESC LIMIT ?""",
                      (pid, usuario_id or -1, limite)).fetchall()


# ------------------------------------------------------------------ a lista
def por_setor(db):
    """A equipe agrupada por setor, com a contagem de cada um.

    Quem não tem setor vem primeiro, com a chave None: é essa a fila que trava
    a aprovação da inicial, e enterrá-la no fim da tabela é o mesmo que
    escondê-la.
    """
    linhas = db.execute("""SELECT p.id, p.nome, p.setor, p.ativo, p.supervisor_id,
                s.nome supervisor,
                (SELECT COUNT(*) FROM tarefas t WHERE t.responsavel_id=p.id
                   AND t.status IN ('ABERTA','EM_ANDAMENTO')) abertas,
                (SELECT COUNT(*) FROM processos pr WHERE pr.advogado_id=p.id) processos,
                (SELECT COUNT(*) FROM pessoas d WHERE d.supervisor_id=p.id) equipe_dele,
                (SELECT string_agg(pp.papel, ', ' ORDER BY pp.papel) FROM pessoa_papeis pp
                   WHERE pp.pessoa_id=p.id) papeis,
                u.papel perfil
             FROM pessoas p
             LEFT JOIN pessoas s ON s.id = p.supervisor_id
             LEFT JOIN usuarios u ON u.pessoa_id = p.id
             ORDER BY (NOT p.ativo), p.nome""").fetchall()
    grupos = {}
    for l in linhas:
        grupos.setdefault(l["setor"] or None, []).append(l)
    # todo setor do banco aparece, mesmo vazio: setor sem ninguém é informação
    for s in setores(db):
        grupos.setdefault(s, [])
    return grupos


def carga(db, setor=None):
    """Quantas tarefas abertas cada pessoa tem. Urgente pesa 3, atrasada 2.

    É a conta que a distribuição automática usa, e é a mesma que a tela de
    Equipe mostra — se fossem duas contas, a tela explicaria uma distribuição
    que não aconteceu.
    """
    return db.execute("""SELECT p.id, p.nome, p.setor,
                COUNT(t.id) FILTER (WHERE t.status IN ('ABERTA','EM_ANDAMENTO')) abertas,
                COALESCE(SUM(CASE
                    WHEN t.status NOT IN ('ABERTA','EM_ANDAMENTO') THEN 0
                    WHEN t.prioridade='URGENTE' THEN 3
                    WHEN t.prazo IS NOT NULL AND t.prazo < date('now') THEN 2
                    ELSE 1 END), 0) peso
             FROM pessoas p
             LEFT JOIN tarefas t ON t.responsavel_id = p.id
             WHERE p.ativo = true AND (? IS NULL OR p.setor = ?)
             GROUP BY p.id, p.nome, p.setor
             ORDER BY peso DESC, p.nome""", (setor, setor)).fetchall()


if __name__ == "__main__":
    db = banco.conectar()
    print("setores (de fluxo_etapas.grupo):")
    for s in setores(db):
        n = db.execute("SELECT COUNT(*) FROM pessoas WHERE setor=?", (s,)).fetchone()[0]
        print(f"  {s:<20} {n:>3} pessoa(s)")
    sem = db.execute("SELECT COUNT(*) FROM pessoas WHERE ativo AND setor IS NULL").fetchone()[0]
    print(f"  {'(sem setor, ativas)':<20} {sem:>3}")
    print()
    print(f"{'pessoa':<34}{'setor':<26}{'abertas':>8}{'peso':>7}")
    print("-" * 76)
    for r in carga(db):
        print(f"{(r['nome'] or '')[:32]:<34}{(r['setor'] or '—')[:24]:<26}"
              f"{r['abertas']:>8}{r['peso']:>7}")
    db.close()
