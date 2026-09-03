#!/usr/bin/env python3
"""Sistema Operacional GGV Trabalhista — portal do escritório.

Roda local, na porta 8771 (o Prev usa a 8770 e não se toca nele). Escrito no
padrão do Prev, e pelos mesmos motivos:

  · **Toda restrição é conferida no servidor.** O botão que some da tela é
    conveniência; o que impede é `exige()` aqui e o gatilho no banco.
  · **Toda mudança de etapa passa por `fluxo.py`**, que por sua vez esbarra nos
    gatilhos de `governanca.sql`. Não há caminho que escape da regra — nem
    script, nem mão humana no psql.
  · **Número na tela sai de consulta**, nunca escrito no template, e todo
    contador conta DENTRO do recorte ativo. Contador global engana: dizer
    "3.722 processos" numa tela filtrada por TRT é oferecer uma fila que não
    existe.
  · **Nada de inventar.** Campo que o banco não tem sai em branco, com o
    porquê; o que depende do escritório sai marcado [CONFIRMAR].
  · **Escrita em SAVEPOINT**, sempre: no Postgres um erro derruba a transação
    inteira, e a recusa do gatilho tem de virar recado na tela, não 500.
"""
import os
import re
from datetime import date

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import agora as agora_mod
import alertas
import auth
import banco
import csrf
import equipe
import fluxo
import prazo_legal

AQUI = os.path.dirname(os.path.abspath(__file__))
tpl = Jinja2Templates(directory=os.path.join(AQUI, "templates"))


def conectar():
    return banco.conectar()


# ---------------------------------------------------------------- formato
def _centavos(v, cifrao=True):
    """Dinheiro é inteiro em centavos no banco e vira texto só aqui.

    Vazio devolve travessão, não "R$ 0,00": zero é um valor, ausência é outra
    coisa, e confundir os dois numa tela de dinheiro é o pior tipo de erro.
    """
    if v is None or v == "":
        return "—"
    try:
        n = int(v)
    except (TypeError, ValueError):
        return "—"
    txt = f"{abs(n) // 100:,}".replace(",", ".") + "," + f"{abs(n) % 100:02d}"
    return ("−" if n < 0 else "") + (f"R$ {txt}" if cifrao else txt)


def _data_br(v):
    if not v:
        return "—"
    s = str(v)[:10]
    try:
        return "/".join(reversed(s.split("-")))
    except Exception:
        return s


def _digitos(v):
    return re.sub(r"\D", "", str(v or ""))


def _para_centavos(v):
    """"1.234,56" → 123456. Vazio devolve None; o que não é dinheiro levanta.

    Dinheiro é inteiro em centavos no banco, e a conversão é aqui e não no
    JavaScript: quem escreve "1.234,56" e quem escreve "1234.56" tem de chegar
    ao mesmo inteiro, e o campo que não dá para ler tem de PARAR o pedido, não
    virar zero. Zero é um valor — "repassei R$ 0,00" é uma afirmação diferente
    de "não consegui ler o que você digitou".
    """
    s = str(v or "").strip().replace("R$", "").replace(" ", "").replace("\xa0", "")
    if not s:
        return None
    if "," in s:                       # 1.234,56 — o ponto é separador de milhar
        s = s.replace(".", "").replace(",", ".")
    try:
        return int(round(float(s) * 100))
    except ValueError:
        raise ValueError(f"não entendi o valor “{v}” — escreva como 1.234,56")


def _rotulo(v):
    """CODIGO_ASSIM vira 'codigo assim' — o vocabulário do banco na tela."""
    return (v or "").replace("_", " ").lower() if v else ""


def _cnj(v):
    """0001234-56.2024.5.02.0001, quando há 20 dígitos; senão, o que veio."""
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) != 20:
        return v or "—"
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"


tpl.env.filters["centavos"] = _centavos
tpl.env.filters["data_br"] = _data_br
tpl.env.filters["rotulo"] = _rotulo
tpl.env.filters["cnj"] = _cnj
tpl.env.filters["setor_etapa"] = equipe.setor_da_etapa


def _versao_css():
    """O minuto em que o estilo mudou. Vai no endereço da folha: sem isso o
    navegador guarda o arquivo por conta própria e o escritório continua vendo
    a tela velha depois de cada ajuste."""
    try:
        return int(os.path.getmtime(os.path.join(AQUI, "static", "estilo.css")))
    except OSError:
        return 0


tpl.env.globals["css_v"] = _versao_css


# ------------------------------------------------------------- permissão
def usuario(req):
    return req.session.get("usuario")


def exige(req, tela=None):
    """(usuário, resposta-de-desvio). Toda rota começa por aqui."""
    u = usuario(req)
    if not u:
        return None, RedirectResponse("/entrar", 302)
    # senha provisória não anda pelo sistema: troca primeiro
    if u.get("trocar_senha") and req.url.path not in ("/senha", "/sair"):
        return u, RedirectResponse("/senha", 302)
    if tela and tela not in auth.telas_de(u["papel"], u.get("setor")):
        return u, pagina(req, "negado.html", tela=tela, _http=403)
    return u, None


def pagina(req, nome, /, **ctx):
    # garante o token da sessão antes de a tela ser montada; quem o injeta nos
    # formulários é `csrf.Trava`, na volta
    try:
        csrf.token_da(req.session)
    except Exception:
        pass
    u = usuario(req)
    http = ctx.pop("_http", 200)
    return tpl.TemplateResponse(req, nome, {
        "u": u,
        "hoje_iso": date.today().isoformat(),
        "telas": auth.telas_de(u["papel"], u.get("setor")) if u else set(),
        "tema": (u or {}).get("tema") or "escuro",
        "fonte_pct": (u or {}).get("fonte_pct") or 100,
        **ctx}, status_code=http)


def _eu(db, u):
    """O `pessoas.id` de quem está logado — é ele que vai para o histórico."""
    if not u:
        return None
    if u.get("pessoa_id"):
        return u["pessoa_id"]
    r = db.execute("SELECT pessoa_id FROM usuarios WHERE id=?", (u["id"],)).fetchone()
    return r[0] if r else None


def _volta(req, padrao, ok=None, erro=None):
    """Volta para onde se estava, com o recado. O recado vai ESCAPADO: a
    recusa do gatilho vem com aspas e dois-pontos, e sem quote() o endereço
    quebra justo quando há algo a dizer."""
    from urllib.parse import quote
    junta = "&" if "?" in padrao else "?"
    if erro:
        return RedirectResponse(f"{padrao}{junta}erro={quote(str(erro)[:400])}", 302)
    return RedirectResponse(f"{padrao}{junta}ok={quote(str(ok or 1))}", 302)


class Recorte:
    """O filtro da tela, montado por dimensão — para todo contador contar DENTRO dele.

    A regra da casa diz que número na tela sai de consulta e conta dentro do
    recorte ativo. O chip é o caso difícil: em `/processos?fase=RECURSAL`, o
    chip "sem reclamada · 11" contava o escritório inteiro enquanto a fila
    embaixo dele tinha 0 — clicar entregava uma fila vazia. Contador global em
    tela filtrada não é imprecisão, é oferta de trabalho que não existe.

    E o chip conta o recorte **sem a sua própria dimensão**: os três chips de
    qualidade são alternativas entre si, e contá-los já com `falta=numero`
    aplicado daria a interseção — "sem reclamada" viraria "sem reclamada E sem
    número", que ninguém pediu. Por isso `onde(exceto=…)`.
    """

    def __init__(self):
        self.partes = []                      # (dimensão, sql, [args])

    def mais(self, dimensao, sql, *args):
        self.partes.append((dimensao, sql, list(args)))

    def onde(self, exceto=None):
        """(sql do WHERE, tupla de argumentos). `exceto` tira uma dimensão."""
        fora = {exceto} if isinstance(exceto, str) else set(exceto or ())
        sql, args = ["1=1"], []
        for dim, pedaco, vs in self.partes:
            if dim in fora:
                continue
            sql.append(pedaco)
            args += vs
        return " AND ".join(sql), tuple(args)


def _conta(db, molde, recorte, exceto=None, **fmt):
    """Um COUNT(*) dentro do recorte. `molde` traz {filtro} onde o WHERE entra."""
    filtro, args = recorte.onde(exceto)
    return db.execute(molde.format(filtro=filtro, **fmt), args).fetchone()[0]


# O que o Postgres recusa, dito em português de operador. A chave é o SQLSTATE.
# A mensagem crua ("new row for relation … violates check constraint
# …_tipo_check") é escrita para quem mantém o banco, não para quem clicou — e
# quem clicou é que precisa saber o que fazer agora.
_RECUSAS = {
    "23503": "esse campo aponta para um registro que não existe (pessoa, processo ou "
             "cliente apagado, ou escolhido fora da lista). Escolha um da lista",
    "23514": "o valor não está entre os que este campo aceita. Escolha um dos "
             "oferecidos na tela",
    "23505": "já existe um registro com esse valor, e este campo não aceita repetido",
    "23502": "falta preencher um campo obrigatório",
    "22P02": "o formato do que foi digitado não serve para este campo "
             "(data, número ou valor)",
    "22001": "o texto digitado é mais longo do que o campo aceita",
}


def _recado(e):
    """A recusa do banco escrita para quem clicou.

    Duas fontes, dois tratamentos. A recusa da GOVERNANÇA vem de um RAISE do
    PL/pgSQL e já é escrita para gente ler ("transição de status fora do fluxo
    CLIENTE: …") — dela só se tira o cabeçalho técnico. A recusa do ESQUEMA
    (CHECK, FK, UNIQUE) vem em inglês e citando o nome do constraint; essa vira
    frase, com o nome do constraint entre parênteses no fim para quem for
    investigar depois.

    Em nenhum dos dois casos passa mais que a primeira linha: as linhas de
    DETAIL de um erro do Postgres trazem **o registro inteiro** (`Failing row
    contains …`: nome, CPF, telefone), e isso iria parar na barra de endereço
    do navegador e no log do servidor. Erro não é lugar de vazar cadastro.
    """
    primeira = str(e).splitlines()[0].replace("ERROR:  ", "").strip()
    estado = getattr(e, "sqlstate", None) or ""
    if estado in _RECUSAS:
        alvo = getattr(getattr(e, "diag", None), "constraint_name", None)
        return _RECUSAS[estado] + (f" ({alvo})" if alvo else "")
    return primeira


def _qs(req, **mudar):
    """A mesma consulta com um filtro trocado — para os chips manterem o resto."""
    p = dict(req.query_params)
    for k, v in mudar.items():
        if v in (None, "", "todos"):
            p.pop(k, None)
        else:
            p[k] = v
    p.pop("pagina", None)
    from urllib.parse import urlencode
    return ("?" + urlencode(p)) if p else ""


tpl.env.globals["qs"] = _qs


# =========================================================== entrada
async def entrar(req: Request):
    if req.method == "POST":
        f = await req.form()
        db = conectar()
        u = auth.autenticar(db, f.get("email"), f.get("senha"))
        db.close()
        if not u:
            return pagina(req, "entrar.html", erro="e-mail ou senha não conferem")
        # o token gira ao entrar: um capturado antes do login valeria depois
        csrf.girar(req.session)
        req.session["usuario"] = u
        return RedirectResponse("/senha" if u["trocar_senha"] else "/", 302)
    return pagina(req, "entrar.html")


async def sair(req: Request):
    req.session.clear()
    csrf.girar(req.session)
    return RedirectResponse("/entrar", 302)


async def senha(req: Request):
    u = usuario(req)
    if not u:
        return RedirectResponse("/entrar", 302)
    if req.method == "POST":
        f = await req.form()
        db = conectar()
        ok, recado = auth.trocar(db, u["id"], f.get("atual"), f.get("nova"))
        db.close()
        if not ok:
            return pagina(req, "senha.html", erro=recado)
        u["trocar_senha"] = False
        req.session["usuario"] = u
        return RedirectResponse("/?ok=senha trocada", 302)
    return pagina(req, "senha.html")


async def saude(req: Request):
    """O healthcheck. Diz se o banco responde e quantas linhas ele tem."""
    try:
        db = conectar()
        n = db.execute("SELECT COUNT(*) FROM processos").fetchone()[0]
        db.close()
        return JSONResponse({"ok": True, "processos": n})
    except Exception as e:
        return JSONResponse({"ok": False, "erro": f"{type(e).__name__}: {e}"}, 503)


# =========================================================== início
async def inicio(req: Request):
    u, r = exige(req, "meu_dia")
    if r:
        return r
    db = conectar()
    eu = _eu(db, u)
    ctx = dict(
        fogo=agora_mod.listar(db, pessoa_id=eu, setor=u.get("setor"), papel=u["papel"]),
        minhas=db.execute("""SELECT t.*, c.nome cliente, p.numero_cnj
                             FROM tarefas t
                             LEFT JOIN clientes c ON c.id = t.cliente_id
                             LEFT JOIN processos p ON p.id = t.processo_id
                             WHERE t.responsavel_id=? AND t.status IN ('ABERTA','EM_ANDAMENTO')
                             ORDER BY (t.prazo IS NULL), t.prazo LIMIT 12""", (eu,)).fetchall(),
        # os contadores saem da visão da governança: o mapa e a contagem são
        # a mesma coisa, e nenhuma etapa aparece na tela sem existir no mapa
        funil_cliente=db.execute("""SELECT * FROM v_funil_etapas WHERE fluxo='CLIENTE'
                                    ORDER BY ordem""").fetchall(),
        funil_processo=db.execute("""SELECT * FROM v_funil_etapas WHERE fluxo='PROCESSO'
                                     ORDER BY ordem""").fetchall(),
        estagnados=db.execute("""SELECT entidade, COUNT(*) n FROM v_estagnados
                                 GROUP BY entidade""").fetchall(),
        atrasados=db.execute("""SELECT farol, COUNT(*) n FROM v_pre_processual_atrasado
                                WHERE farol IS NOT NULL GROUP BY farol""").fetchall(),
        prazos_abertos=db.execute("SELECT COUNT(*) FROM prazos WHERE situacao='ABERTO'").fetchone()[0],
        audiencias_semana=db.execute("""SELECT COUNT(*) FROM audiencias
             WHERE situacao IN ('DESIGNADA','EM_PREPARACAO') AND data_hora IS NOT NULL
               AND substr(data_hora,1,10)::date BETWEEN
                   (now() AT TIME ZONE 'America/Sao_Paulo')::date
               AND (now() AT TIME ZONE 'America/Sao_Paulo')::date + 7""").fetchone()[0],
        conferencias_abertas=db.execute("""SELECT COUNT(*) FROM conferencias
                                           WHERE situacao IN ('ABERTA','EM_ANALISE')""").fetchone()[0],
        # O funil nasce TRUNCADO: os registros migrados entraram já assinados,
        # e LEAD só passa a existir com a entrada pelo portal (resposta 5).
        # Sem dizer isso, a conversão do primeiro mês mente.
        leads=db.execute("SELECT COUNT(*) FROM clientes WHERE status='LEAD'").fetchone()[0],
        migrados=db.execute("""SELECT COUNT(*) FROM clientes
                               WHERE origem_cadastro <> 'PORTAL'""").fetchone()[0],
    )
    db.close()
    return pagina(req, "inicio.html", **ctx)


async def api_agora(req: Request):
    u = usuario(req)
    if not u:
        return JSONResponse({"n": 0, "itens": []})
    db = conectar()
    itens = agora_mod.listar(db, pessoa_id=_eu(db, u), setor=u.get("setor"), papel=u["papel"])
    db.close()
    return JSONResponse({"n": len(itens), "itens": itens})


# =========================================================== clientes
ETAPAS_CLIENTE_SQL = """SELECT e.codigo, e.nome, e.ordem, e.tipo, e.grupo
                        FROM fluxo_etapas e WHERE e.fluxo_id=1 ORDER BY e.ordem"""


async def clientes(req: Request):
    u, r = exige(req, "clientes")
    if r:
        return r
    p = req.query_params
    db = conectar()
    onde, args = ["1=1"], []
    if p.get("status"):
        onde.append("c.status = ?"); args.append(p["status"])
    if p.get("responsavel"):
        onde.append("c.responsavel_id = ?"); args.append(int(p["responsavel"]))
    if p.get("captador"):
        onde.append("c.captador_id = ?"); args.append(int(p["captador"]))
    if p.get("canal"):
        onde.append("c.canal = ?"); args.append(p["canal"])
    if p.get("setor"):
        onde.append("fe.grupo = ?"); args.append(p["setor"])
    if p.get("q"):
        onde.append("(c.nome ILIKE ? OR c.cpf ILIKE ?)")
        so_digitos = _digitos(p["q"])
        args += ["%" + p["q"] + "%", "%" + so_digitos + "%"]
    if p.get("vivos") == "1":
        onde.append("fe.tipo <> 'FINAL'")
    filtro = " AND ".join(onde)

    linhas = db.execute(f"""SELECT c.id, c.nome, c.status, c.canal, c.data_assinatura_contrato,
                c.data_demissao, c.contrato_vivo, fe.nome etapa_nome, fe.grupo,
                em.nome empresa, pe.nome responsavel, cap.nome captador,
                (SELECT COUNT(*) FROM pendencias pd WHERE pd.cliente_id=c.id
                   AND pd.recebido_em IS NULL AND pd.dispensado_motivo IS NULL) pendencias,
                (SELECT COUNT(*) FROM processos pr WHERE pr.cliente_id=c.id) processos
             FROM clientes c
             JOIN fluxo_etapas fe ON fe.fluxo_id=1 AND fe.codigo=c.status
             LEFT JOIN empresas em ON em.id = c.empresa_id
             LEFT JOIN pessoas pe ON pe.id = c.responsavel_id
             LEFT JOIN pessoas cap ON cap.id = c.captador_id
             WHERE {filtro}
             ORDER BY fe.ordem, c.nome LIMIT 300""", tuple(args)).fetchall()
    # o contador conta DENTRO do recorte: mesmo WHERE, sem o LIMIT
    total = db.execute(f"""SELECT COUNT(*) FROM clientes c
             JOIN fluxo_etapas fe ON fe.fluxo_id=1 AND fe.codigo=c.status
             WHERE {filtro}""", tuple(args)).fetchone()[0]
    ctx = dict(
        linhas=linhas, total=total, p=p,
        etapas=db.execute(ETAPAS_CLIENTE_SQL).fetchall(),
        por_etapa={r["codigo"]: r["registros"] for r in db.execute(
            "SELECT codigo, registros FROM v_funil_etapas WHERE fluxo='CLIENTE'")},
        equipe_l=db.execute("""SELECT id, nome, setor FROM pessoas
                               WHERE ativo = true ORDER BY nome""").fetchall(),
        canais=db.execute("""SELECT canal, COUNT(*) n FROM clientes
                             WHERE canal IS NOT NULL GROUP BY canal ORDER BY n DESC""").fetchall(),
        setores=db.execute("""SELECT DISTINCT grupo FROM fluxo_etapas
                              WHERE fluxo_id=1 AND grupo IS NOT NULL ORDER BY grupo""").fetchall(),
    )
    ctx["sinais"] = alertas.por_cliente(db, [l["id"] for l in linhas])
    db.close()
    return pagina(req, "clientes.html", **ctx)


async def cliente(req: Request):
    u, r = exige(req, "clientes")
    if r:
        return r
    cid = int(req.path_params["id"])
    db = conectar()
    c = db.execute("""SELECT c.*, em.nome empresa, em.id emp_id,
                             pe.nome responsavel, cap.nome captador, ent.nome entrevistador,
                             fe.nome etapa_nome, fe.grupo etapa_grupo, fe.texto_operador,
                             fe.sla_dias
                      FROM clientes c
                      LEFT JOIN empresas em ON em.id = c.empresa_id
                      LEFT JOIN pessoas pe ON pe.id = c.responsavel_id
                      LEFT JOIN pessoas cap ON cap.id = c.captador_id
                      LEFT JOIN pessoas ent ON ent.id = c.entrevistador_id
                      LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=1 AND fe.codigo=c.status
                      WHERE c.id=?""", (cid,)).fetchone()
    if not c:
        db.close()
        return RedirectResponse("/clientes", 302)
    ctx = dict(
        c=c,
        trilha=fluxo.trilha(db, "clientes"),
        etapa_agora=db.execute("""SELECT * FROM fluxo_etapas WHERE fluxo_id=1 AND codigo=?""",
                               (c["status"],)).fetchone(),
        transicoes=fluxo.transicoes(db, "clientes", cid, u["papel"], pessoa_id=_eu(db, u)),
        percorridas=fluxo.percorridas(db, "clientes", cid),
        pendencias=fluxo.pendencias_abertas(db, cliente_id=cid),
        resolvidas=db.execute("""SELECT p.*, pe.nome responsavel FROM pendencias p
             LEFT JOIN pessoas pe ON pe.id=p.responsavel_id
             WHERE p.cliente_id=? AND (p.recebido_em IS NOT NULL
                                    OR p.dispensado_motivo IS NOT NULL)
             ORDER BY COALESCE(p.recebido_em, p.criado_em) DESC LIMIT 20""", (cid,)).fetchall(),
        docs_faltando=fluxo.documentos_faltando(db, cid),
        processos=db.execute("""SELECT p.*, fe.nome fase_nome FROM processos p
             LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=2 AND fe.codigo=p.fase
             WHERE p.cliente_id=? ORDER BY p.id""", (cid,)).fetchall(),
        testemunhas=db.execute("""SELECT t.*, v.observacao vinculo_obs FROM testemunhas t
             JOIN testemunha_vinculos v ON v.testemunha_id = t.id
             WHERE v.cliente_id=? ORDER BY t.nome""", (cid,)).fetchall(),
        documentos=db.execute("""SELECT * FROM documentos WHERE cliente_id=?
             ORDER BY criado_em DESC LIMIT 40""", (cid,)).fetchall(),
        peticoes=db.execute("""SELECT pe.*, p.nome revisor FROM peticoes pe
             LEFT JOIN pessoas p ON p.id = pe.revisada_por
             WHERE pe.cliente_id=? ORDER BY pe.criado_em DESC""", (cid,)).fetchall(),
        contatos=db.execute("""SELECT ct.*, p.nome quem FROM contatos ct
             LEFT JOIN pessoas p ON p.id = ct.pessoa_id
             WHERE ct.cliente_id=? ORDER BY ct.em DESC LIMIT 20""", (cid,)).fetchall(),
        eventos=db.execute("""SELECT * FROM eventos WHERE cliente_id=?
             ORDER BY data_hora DESC LIMIT 20""", (cid,)).fetchall(),
        anotacoes=db.execute("""SELECT a.*, p.nome autor FROM anotacoes a
             LEFT JOIN pessoas p ON p.id = a.autor_id
             WHERE a.cliente_id=? ORDER BY a.em DESC LIMIT 30""", (cid,)).fetchall(),
        tarefas=db.execute("""SELECT t.*, p.nome responsavel FROM tarefas t
             LEFT JOIN pessoas p ON p.id = t.responsavel_id
             WHERE t.cliente_id=? AND t.status IN ('ABERTA','EM_ANDAMENTO')
             ORDER BY (t.prazo IS NULL), t.prazo""", (cid,)).fetchall(),
        historico=db.execute("""SELECT h.*, p.nome quem FROM historico_etapas h
             LEFT JOIN pessoas p ON p.id = h.pessoa_id
             WHERE h.entidade='clientes' AND h.entidade_id=?
             ORDER BY h.em DESC, h.id DESC""", (cid,)).fetchall(),
        equipe_l=db.execute("""SELECT id, nome, setor FROM pessoas
                               WHERE ativo = true ORDER BY nome""").fetchall(),
        prescreve=db.execute("""SELECT prescreve_em, dias_desde_assinatura, farol
             FROM v_pre_processual_atrasado WHERE id=?""", (cid,)).fetchone(),
        conferencias=db.execute("""SELECT * FROM conferencias
             WHERE entidade='clientes' AND entidade_id=?
               AND situacao IN ('ABERTA','EM_ANALISE')""", (cid,)).fetchall(),
    )
    ctx["sinais"] = alertas.por_processo(db, [p["id"] for p in ctx["processos"]])
    db.close()
    return pagina(req, "cliente.html", **ctx)


async def cliente_responsavel(req: Request):
    u, r = exige(req, "clientes")
    if r:
        return r
    cid = int(req.path_params["id"])
    f = await req.form()
    quem = f.get("pessoa_id")
    db = conectar()
    erro = None
    try:
        if quem == "eu":
            quem = _eu(db, u)
        antes = db.execute("SELECT responsavel_id FROM clientes WHERE id=?", (cid,)).fetchone()
        db.execute("UPDATE clientes SET responsavel_id=? WHERE id=?",
                   (int(quem) if quem else None, cid))
        db.execute("""INSERT INTO auditoria (tabela, registro_id, acao, campo, valor_antigo,
                        valor_novo, pessoa_id)
                      VALUES ('clientes',?,'UPDATE','responsavel_id',?,?,?)""",
                   (cid, str(antes[0]) if antes and antes[0] else None,
                    str(quem) if quem else None, _eu(db, u)))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, f"/clientes/{cid}", ok="dono do atendimento alterado", erro=erro)


async def pendencia_resolver(req: Request):
    """Recebida, ou dispensada com motivo. Não há terceira saída — e é isso
    que faz o gate `documentos_obrigatorios` poder confiar na tabela."""
    u, r = exige(req, "clientes")
    if r:
        return r
    pid = int(req.path_params["id"])
    f = await req.form()
    acao = f.get("acao")
    db = conectar()
    destino = "/clientes"
    erro = None
    try:
        dono = db.execute("SELECT cliente_id, processo_id FROM pendencias WHERE id=?",
                          (pid,)).fetchone()
        destino = (f"/clientes/{dono['cliente_id']}" if dono and dono["cliente_id"]
                   else f"/processos/{dono['processo_id']}" if dono else "/clientes")
        if acao == "recebida":
            db.execute("UPDATE pendencias SET recebido_em=date('now') WHERE id=?", (pid,))
        elif acao == "dispensada":
            motivo = (f.get("motivo") or "").strip()
            if not motivo:
                erro = "dispensar exige motivo escrito"
            else:
                db.execute("UPDATE pendencias SET dispensado_motivo=? WHERE id=?", (motivo, pid))
        elif acao == "solicitada":
            db.execute("UPDATE pendencias SET solicitado_em=date('now') WHERE id=?", (pid,))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, destino, ok="pendência atualizada", erro=erro)


async def pendencia_nova(req: Request):
    u, r = exige(req, "clientes")
    if r:
        return r
    f = await req.form()
    cid = int(req.path_params["id"])
    db = conectar()
    erro = None
    # o tipo vem do formulário e não se chuta: "OUTRO" no lugar do que a pessoa
    # quis dizer é o sistema inventando, e é o tipo DOCUMENTO que trava a etapa
    tipo = (f.get("tipo") or "").strip()
    if not tipo:
        db.close()
        return _volta(req, f"/clientes/{cid}", erro="escolha o tipo da pendência")
    try:
        db.execute("""INSERT INTO pendencias (cliente_id, tipo, documento_tipo, descricao,
                        obrigatorio, responsavel_id, prazo, solicitado_em, origem)
                      VALUES (?,?,?,?,?,?,?,?, 'MANUAL')""",
                   (cid, tipo, f.get("documento_tipo") or None,
                    (f.get("descricao") or "").strip() or None,
                    f.get("obrigatorio") == "1",
                    int(f["responsavel_id"]) if f.get("responsavel_id") else None,
                    f.get("prazo") or None,
                    date.today().isoformat() if f.get("ja_pedida") == "1" else None))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, f"/clientes/{cid}", ok="pendência aberta", erro=erro)


# =========================================================== processos
async def processos(req: Request):
    u, r = exige(req, "processos")
    if r:
        return r
    p = req.query_params
    db = conectar()
    rec = Recorte()
    for campo, coluna in (("fase", "pr.fase"), ("trt", "pr.trt"), ("vara", "pr.vara"),
                          ("rito", "pr.rito"), ("complexidade", "pr.complexidade"),
                          ("situacao_execucao", "pr.situacao_execucao")):
        if p.get(campo):
            rec.mais(campo, f"{coluna} = ?", p[campo])
    if p.get("advogado"):
        rec.mais("advogado", "pr.advogado_id = ?", int(p["advogado"]))
    if p.get("empresa"):
        rec.mais("empresa", "pr.empresa_id = ?", int(p["empresa"]))
    if p.get("q"):
        q = p["q"]
        rec.mais("q", "(pr.nome_parte ILIKE ? OR c.nome ILIKE ? OR pr.numero_cnj_digitos ILIKE ?)",
                 "%" + q + "%", "%" + q + "%", "%" + _digitos(q) + "%")
    if p.get("falta") == "empresa":
        rec.mais("falta", "pr.empresa_id IS NULL")
    if p.get("falta") == "numero":
        rec.mais("falta", "(pr.numero_cnj IS NULL OR pr.numero_cnj = '')")
    if p.get("falta") == "valor":
        rec.mais("falta", "pr.valor_causa_centavos IS NULL")
    filtro, args = rec.onde()

    linhas = db.execute(f"""SELECT pr.id, pr.numero_cnj, pr.fase, pr.trt, pr.vara, pr.rito,
                pr.complexidade, pr.valor_causa_centavos, pr.situacao_execucao,
                pr.distribuicao_em, pr.resultado_final,
                COALESCE(c.nome, pr.nome_parte) parte, c.id cliente_id,
                em.nome empresa, ad.nome advogado, fe.nome fase_nome
             FROM processos pr
             JOIN clientes c ON c.id = pr.cliente_id
             LEFT JOIN empresas em ON em.id = pr.empresa_id
             LEFT JOIN pessoas ad ON ad.id = pr.advogado_id
             LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=2 AND fe.codigo=pr.fase
             WHERE {filtro}
             ORDER BY fe.ordem, pr.distribuicao_em DESC NULLS LAST, pr.id
             LIMIT 300""", tuple(args)).fetchall()
    total = db.execute(f"""SELECT COUNT(*) FROM processos pr
             JOIN clientes c ON c.id = pr.cliente_id WHERE {filtro}""", tuple(args)).fetchone()[0]
    soma = db.execute(f"""SELECT COALESCE(SUM(pr.valor_causa_centavos),0) FROM processos pr
             JOIN clientes c ON c.id = pr.cliente_id WHERE {filtro}""", tuple(args)).fetchone()[0]

    # Cada chip e cada lista de filtro conta DENTRO do recorte, e sem a sua
    # própria dimensão — senão o chip da fase em que já se está mostraria o
    # total dele mesmo e os outros mostrariam zero, e ninguém sairia de lá.
    de, arg_de = rec.onde("fase")
    de_tr, arg_tr = rec.onde("trt")
    de_va, arg_va = rec.onde("vara")
    de_ad, arg_ad = rec.onde("advogado")
    de_em, arg_em = rec.onde("empresa")
    de_ex, arg_ex = rec.onde("situacao_execucao")
    # os três de qualidade são alternativas entre si: fora a dimensão `falta`
    de_q, arg_q = rec.onde("falta")
    conta = ("""SELECT COUNT(*) FROM processos pr
                JOIN clientes c ON c.id = pr.cliente_id
                WHERE """ + de_q + " AND ")
    ctx = dict(
        linhas=linhas, total=total, soma=soma, p=p,
        # a view chama a coluna de `etapa`; o alias deixa as três telas de fila
        # falarem a mesma língua (`.nome`) sem cada uma lembrar disso. O LEFT
        # JOIN é de propósito: a etapa com 0 no recorte continua na barra, ou
        # não haveria como navegar para fora do filtro atual.
        fases=db.execute(f"""SELECT v.codigo, v.etapa nome, v.ordem,
                    (SELECT COUNT(*) FROM processos pr JOIN clientes c ON c.id = pr.cliente_id
                     WHERE {de} AND pr.fase = v.codigo) registros
                 FROM v_funil_etapas v WHERE v.fluxo='PROCESSO' ORDER BY v.ordem""",
                         arg_de).fetchall(),
        trts=db.execute(f"""SELECT pr.trt, COUNT(*) n FROM processos pr
                 JOIN clientes c ON c.id = pr.cliente_id
                 WHERE {de_tr} AND pr.trt IS NOT NULL
                 GROUP BY pr.trt ORDER BY n DESC LIMIT 30""", arg_tr).fetchall(),
        varas=db.execute(f"""SELECT pr.vara, COUNT(*) n FROM processos pr
                 JOIN clientes c ON c.id = pr.cliente_id
                 WHERE {de_va} AND pr.vara IS NOT NULL
                 GROUP BY pr.vara ORDER BY n DESC LIMIT 40""", arg_va).fetchall(),
        advogados=db.execute(f"""SELECT ad.id, ad.nome, COUNT(pr.id) n FROM pessoas ad
                 JOIN processos pr ON pr.advogado_id = ad.id
                 JOIN clientes c ON c.id = pr.cliente_id
                 WHERE {de_ad} GROUP BY ad.id, ad.nome ORDER BY n DESC""", arg_ad).fetchall(),
        empresas_l=db.execute(f"""SELECT e.id, e.nome, COUNT(pr.id) n FROM empresas e
                 JOIN processos pr ON pr.empresa_id = e.id
                 JOIN clientes c ON c.id = pr.cliente_id
                 WHERE {de_em} GROUP BY e.id, e.nome ORDER BY n DESC LIMIT 40""",
                              arg_em).fetchall(),
        execucoes=db.execute(f"""SELECT pr.situacao_execucao s, COUNT(*) n FROM processos pr
                 JOIN clientes c ON c.id = pr.cliente_id
                 WHERE {de_ex} AND pr.situacao_execucao IS NOT NULL
                 GROUP BY pr.situacao_execucao ORDER BY n DESC""", arg_ex).fetchall(),
        qualidade=dict(
            sem_empresa=db.execute(conta + "pr.empresa_id IS NULL", arg_q).fetchone()[0],
            sem_numero=db.execute(
                conta + "(pr.numero_cnj IS NULL OR pr.numero_cnj='')", arg_q).fetchone()[0],
            sem_valor=db.execute(
                conta + "pr.valor_causa_centavos IS NULL", arg_q).fetchone()[0],
        ),
    )
    ctx["sinais"] = alertas.por_processo(db, [l["id"] for l in linhas])
    db.close()
    return pagina(req, "processos.html", **ctx)


async def processo(req: Request):
    u, r = exige(req, "processos")
    if r:
        return r
    pid = int(req.path_params["id"])
    db = conectar()
    pr = db.execute("""SELECT pr.*, c.nome cliente_nome, c.id cliente_id, c.telefone,
                              em.nome empresa, em.id emp_id, em.situacao emp_situacao,
                              em.hist_pagamento, em.bens_identificados,
                              ad.nome advogado, cap.nome captador, fe.nome fase_nome,
                              fe.texto_operador, fe.grupo fase_grupo, fe.sla_dias
                       FROM processos pr
                       JOIN clientes c ON c.id = pr.cliente_id
                       LEFT JOIN empresas em ON em.id = pr.empresa_id
                       LEFT JOIN pessoas ad ON ad.id = pr.advogado_id
                       LEFT JOIN pessoas cap ON cap.id = pr.captador_id
                       LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=2 AND fe.codigo=pr.fase
                       WHERE pr.id=?""", (pid,)).fetchone()
    if not pr:
        db.close()
        return RedirectResponse("/processos", 302)
    ctx = dict(
        p=pr,
        trilha=fluxo.trilha(db, "processos"),
        etapa_agora=db.execute("SELECT * FROM fluxo_etapas WHERE fluxo_id=2 AND codigo=?",
                               (pr["fase"],)).fetchone(),
        transicoes=fluxo.transicoes(db, "processos", pid, u["papel"], pessoa_id=_eu(db, u)),
        percorridas=fluxo.percorridas(db, "processos", pid),
        audiencias=db.execute("""SELECT a.*, fe.nome situacao_nome, pe.nome responsavel
             FROM audiencias a
             LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=3 AND fe.codigo=a.situacao
             LEFT JOIN pessoas pe ON pe.id = a.responsavel_id
             WHERE a.processo_id=? ORDER BY a.data_hora DESC NULLS LAST""", (pid,)).fetchall(),
        prazos=db.execute("""SELECT z.*, pt.nome tipo_nome, pt.fundamento, pe.nome responsavel
             FROM prazos z LEFT JOIN prazo_tipos pt ON pt.codigo = z.tipo
             LEFT JOIN pessoas pe ON pe.id = z.responsavel_id
             WHERE z.processo_id=?
             ORDER BY (z.situacao<>'ABERTO'), z.vencimento""", (pid,)).fetchall(),
        pericias=db.execute("SELECT * FROM pericias WHERE processo_id=? ORDER BY data_hora",
                            (pid,)).fetchall(),
        decisoes=db.execute("""SELECT * FROM decisoes WHERE processo_id=?
                               ORDER BY data DESC NULLS LAST, id DESC""", (pid,)).fetchall(),
        recursos=db.execute("""SELECT * FROM recursos WHERE processo_id=?
                               ORDER BY interposto_em DESC NULLS LAST""", (pid,)).fetchall(),
        calculos=db.execute("SELECT * FROM calculos WHERE processo_id=? ORDER BY base",
                            (pid,)).fetchall(),
        acordos=db.execute("SELECT * FROM acordos WHERE processo_id=? ORDER BY id",
                           (pid,)).fetchall(),
        parcelas=db.execute("""SELECT ap.* FROM acordo_parcelas ap
             JOIN acordos a ON a.id = ap.acordo_id WHERE a.processo_id=?
             ORDER BY ap.numero""", (pid,)).fetchall(),
        recebimentos=db.execute("SELECT * FROM recebimentos WHERE processo_id=? ORDER BY base",
                                (pid,)).fetchall(),
        repasses=db.execute("SELECT * FROM repasses WHERE processo_id=? ORDER BY id",
                            (pid,)).fetchall(),
        incidentes=db.execute("""SELECT i.*, fe.nome situacao_nome FROM incidentes i
             LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=5 AND fe.codigo=i.situacao
             WHERE i.processo_id=? ORDER BY i.id DESC""", (pid,)).fetchall(),
        pendencias=fluxo.pendencias_abertas(db, processo_id=pid),
        testemunhas=db.execute("""SELECT t.*, v.intimacao_pedida_em, v.audiencia_id
             FROM testemunhas t JOIN testemunha_vinculos v ON v.testemunha_id = t.id
             WHERE v.processo_id=? ORDER BY t.nome""", (pid,)).fetchall(),
        anotacoes=db.execute("""SELECT a.*, p.nome autor FROM anotacoes a
             LEFT JOIN pessoas p ON p.id = a.autor_id
             WHERE a.processo_id=? ORDER BY a.em DESC LIMIT 40""", (pid,)).fetchall(),
        peticoes=db.execute("""SELECT * FROM peticoes WHERE processo_id=?
                               ORDER BY criado_em DESC""", (pid,)).fetchall(),
        documentos=db.execute("""SELECT * FROM documentos WHERE processo_id=?
                                 ORDER BY criado_em DESC LIMIT 40""", (pid,)).fetchall(),
        tarefas=db.execute("""SELECT t.*, p.nome responsavel FROM tarefas t
             LEFT JOIN pessoas p ON p.id = t.responsavel_id
             WHERE t.processo_id=? AND t.status IN ('ABERTA','EM_ANDAMENTO')
             ORDER BY (t.prazo IS NULL), t.prazo""", (pid,)).fetchall(),
        alias=db.execute("SELECT * FROM processo_alias WHERE processo_id=? ORDER BY campo",
                         (pid,)).fetchall(),
        conferencias=db.execute("""SELECT * FROM conferencias
             WHERE entidade='processos' AND entidade_id=?
               AND situacao IN ('ABERTA','EM_ANALISE') ORDER BY campo""", (pid,)).fetchall(),
        fragilidades=db.execute("""SELECT * FROM fragilidades WHERE empresa_id=?
             ORDER BY (situacao='ACOLHIDA') DESC, achado LIMIT 20""",
                                (pr["empresa_id"],)).fetchall() if pr["empresa_id"] else [],
        historico=db.execute("""SELECT h.*, p.nome quem FROM historico_etapas h
             LEFT JOIN pessoas p ON p.id = h.pessoa_id
             WHERE h.entidade='processos' AND h.entidade_id=?
             ORDER BY h.em DESC, h.id DESC""", (pid,)).fetchall(),
        equipe_l=db.execute("SELECT id, nome, setor FROM pessoas WHERE ativo=true ORDER BY nome").fetchall(),
    )
    ctx["fogo"] = alertas.do_processo(db, pid)
    ctx["prazo_uteis"] = {z["id"]: prazo_legal.faltam(z["vencimento"])
                          for z in ctx["prazos"] if z["vencimento"]}
    db.close()
    return pagina(req, "processo.html", **ctx)


async def processo_anotacao(req: Request):
    u, r = exige(req, "processos")
    if r:
        return r
    pid = int(req.path_params["id"])
    f = await req.form()
    texto = (f.get("texto") or "").strip()
    if not texto:
        return _volta(req, f"/processos/{pid}", erro="escreva a anotação")
    db = conectar()
    erro = None
    try:
        db.execute("""INSERT INTO anotacoes (processo_id, texto, autor_id, origem)
                      VALUES (?,?,?, 'MANUAL')""", (pid, texto, _eu(db, u)))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, f"/processos/{pid}", ok="anotação gravada", erro=erro)


async def processo_repasse(req: Request):
    """Registra a REFERÊNCIA do repasse ao cliente — não o repasse.

    Resposta 26 do Lucas: o repasse é do financeiro. O que falta aqui, e é o
    que o gate `repasse_registrado` lê, é a referência: houve, quando, quanto
    (ou por que não havia o que repassar) e a data em que foi entregue ao
    financeiro. Sem esta rota o gate existia sem porta: o processo em RECEBENDO
    não podia ser encerrado por ninguém pelo portal.

    O dinheiro NÃO se move aqui, e é por isso que a tela pede a data da entrega
    ao financeiro em vez de um botão "repassar": quem paga é o financeiro, e o
    que este sistema guarda é a prova de que o caso terminou de verdade.

    Permissão: a mesma da tela de processos, conferida no servidor por
    `exige()` — igual à da transição RECEBENDO → ENCERRADO que esta referência
    destrava, que em `fluxo_transicoes` não exige papel nenhum. O CSRF é da
    trava (`csrf.Trava`), que injeta o token em todo formulário.
    """
    u, r = exige(req, "processos")
    if r:
        return r
    pid = int(req.path_params["id"])
    f = await req.form()
    db = conectar()
    erro = None
    try:
        motivo = (f.get("sem_valor_motivo") or "").strip() or None
        valor = None if motivo else _para_centavos(f.get("valor"))
        # o CHECK da tabela cobra o mesmo; dito aqui, quem clicou lê a razão em
        # vez do texto do constraint
        if valor is None and not motivo:
            raise ValueError("informe o valor repassado — ou, se não havia o que "
                             "repassar, escreva o motivo")
        if valor is not None and valor < 0:
            raise ValueError("valor de repasse não pode ser negativo")
        entregue = (f.get("entregue_ao_financeiro_em") or "").strip() or None
        if not entregue:
            raise ValueError("informe a data em que a referência foi entregue ao "
                             "financeiro — é ela que fecha o caso")
        cur = db.execute("""INSERT INTO repasses (processo_id, valor_centavos, data,
                              sem_valor_motivo, entregue_ao_financeiro_em, observacao)
                            VALUES (?,?,?,?,?,?)""",
                         (pid, valor, (f.get("data") or "").strip() or None, motivo, entregue,
                          (f.get("observacao") or "").strip() or None))
        # dinheiro tem dono: quem registrou fica na auditoria, não só na linha
        db.execute("""INSERT INTO auditoria (tabela, registro_id, acao, campo, valor_antigo,
                        valor_novo, pessoa_id)
                      VALUES ('repasses',?,'INSERT','processo_id',NULL,?,?)""",
                   (cur.lastrowid, str(pid), _eu(db, u)))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, f"/processos/{pid}", ok="repasse registrado", erro=erro)


# =========================================================== audiências
async def audiencias(req: Request):
    u, r = exige(req, "audiencias")
    if r:
        return r
    p = req.query_params
    db = conectar()
    rec = Recorte()
    situacao = p.get("situacao") or "abertas"
    if situacao == "abertas":
        rec.mais("situacao", "a.situacao IN ('DESIGNADA','EM_PREPARACAO')")
    elif situacao != "todas":
        rec.mais("situacao", "a.situacao = ?", situacao)
    janela = p.get("janela") or "30"
    if janela.isdigit():
        rec.mais("janela",
                 "substr(a.data_hora,1,10)::date BETWEEN "
                 "(now() AT TIME ZONE 'America/Sao_Paulo')::date "
                 "AND (now() AT TIME ZONE 'America/Sao_Paulo')::date + ?::int",
                 int(janela))
    if p.get("tipo"):
        rec.mais("tipo", "a.tipo = ?", p["tipo"])
    if p.get("responsavel"):
        rec.mais("responsavel", "a.responsavel_id = ?", int(p["responsavel"]))
    filtro, args = rec.onde()

    linhas = db.execute(f"""SELECT a.*, fe.nome situacao_nome, pr.numero_cnj, pr.trt, pr.vara,
                pr.id proc_id, c.nome cliente, c.id cliente_id, em.nome empresa,
                pe.nome responsavel,
                (substr(a.data_hora,1,10)::date
                 - (now() AT TIME ZONE 'America/Sao_Paulo')::date) dias,
                (a.cliente_orientado_em IS NOT NULL)::int
                + (a.testemunhas_confirmadas_em IS NOT NULL)::int
                + (a.advideo_em IS NOT NULL)::int
                + (a.documentos_conferidos_em IS NOT NULL)::int feitos
             FROM audiencias a
             JOIN processos pr ON pr.id = a.processo_id
             JOIN clientes c ON c.id = pr.cliente_id
             LEFT JOIN empresas em ON em.id = pr.empresa_id
             LEFT JOIN pessoas pe ON pe.id = a.responsavel_id
             LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=3 AND fe.codigo=a.situacao
             WHERE {filtro}
             ORDER BY a.data_hora NULLS LAST LIMIT 300""", tuple(args)).fetchall()
    total = db.execute(f"""SELECT COUNT(*) FROM audiencias a
             JOIN processos pr ON pr.id = a.processo_id WHERE {filtro}""",
                       tuple(args)).fetchone()[0]
    # a semana, agrupada por dia, dentro do MESMO recorte
    semana = {}
    for l in linhas:
        dia = (l["data_hora"] or "")[:10]
        if dia:
            semana.setdefault(dia, []).append(l)
    de_si, arg_si = rec.onde("situacao")
    de_ti, arg_ti = rec.onde("tipo")
    ctx = dict(
        linhas=linhas, total=total, p=p, semana=sorted(semana.items()),
        situacoes=db.execute(f"""SELECT v.codigo, v.etapa nome,
                    (SELECT COUNT(*) FROM audiencias a
                     WHERE {de_si} AND a.situacao = v.codigo) registros
                 FROM v_funil_etapas v WHERE v.fluxo='AUDIENCIA' ORDER BY v.ordem""",
                             arg_si).fetchall(),
        tipos=db.execute(f"""SELECT a.tipo, COUNT(*) n FROM audiencias a
                 WHERE {de_ti} AND a.tipo IS NOT NULL
                 GROUP BY a.tipo ORDER BY n DESC""", arg_ti).fetchall(),
        equipe_l=db.execute("SELECT id, nome FROM pessoas WHERE ativo=true ORDER BY nome").fetchall(),
        # "sem nenhum item do checklist" DENTRO do recorte, e só o que ainda vai
        # acontecer. A view `v_audiencias_sem_preparacao` não tem piso de data:
        # ela devolve as 2.649 audiências com data no passado que a migração
        # gravou como DESIGNADA, e contá-las aqui punha 2.670 numa tela onde a
        # fila era de 1.206. Audiência que já passou não se prepara.
        sem_preparacao=db.execute(f"""SELECT COUNT(*) FROM audiencias a
                 WHERE {filtro} AND a.id IN (SELECT id FROM v_audiencias_sem_preparacao)
                   AND substr(a.data_hora,1,10)::date
                       >= (now() AT TIME ZONE 'America/Sao_Paulo')::date""",
                                  args).fetchone()[0],
    )
    db.close()
    return pagina(req, "audiencias.html", **ctx)


async def audiencia(req: Request):
    u, r = exige(req, "audiencias")
    if r:
        return r
    aid = int(req.path_params["id"])
    db = conectar()
    a = db.execute("""SELECT a.*, fe.nome situacao_nome, fe.texto_operador,
                             pr.id proc_id, pr.numero_cnj, pr.trt, pr.vara, pr.rito,
                             c.nome cliente, c.id cliente_id, c.telefone,
                             em.nome empresa, pe.nome responsavel
                      FROM audiencias a
                      JOIN processos pr ON pr.id = a.processo_id
                      JOIN clientes c ON c.id = pr.cliente_id
                      LEFT JOIN empresas em ON em.id = pr.empresa_id
                      LEFT JOIN pessoas pe ON pe.id = a.responsavel_id
                      LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=3 AND fe.codigo=a.situacao
                      WHERE a.id=?""", (aid,)).fetchone()
    if not a:
        db.close()
        return RedirectResponse("/audiencias", 302)
    ctx = dict(
        a=a,
        trilha=fluxo.trilha(db, "audiencias"),
        etapa_agora=db.execute("SELECT * FROM fluxo_etapas WHERE fluxo_id=3 AND codigo=?",
                               (a["situacao"],)).fetchone(),
        transicoes=fluxo.transicoes(db, "audiencias", aid, u["papel"], pessoa_id=_eu(db, u)),
        percorridas=fluxo.percorridas(db, "audiencias", aid),
        testemunhas=db.execute("""SELECT t.*, v.intimacao_pedida_em FROM testemunhas t
             JOIN testemunha_vinculos v ON v.testemunha_id = t.id
             WHERE v.processo_id=? ORDER BY t.nome""", (a["proc_id"],)).fetchall(),
        pendencias=fluxo.pendencias_abertas(db, processo_id=a["proc_id"]),
        anterior=db.execute("SELECT id, data_hora, resultado FROM audiencias WHERE id=?",
                            (a["redesignada_de"],)).fetchone() if a["redesignada_de"] else None,
        seguinte=db.execute("""SELECT id, data_hora, situacao FROM audiencias
                               WHERE redesignada_de=?""", (aid,)).fetchall(),
        historico=db.execute("""SELECT h.*, p.nome quem FROM historico_etapas h
             LEFT JOIN pessoas p ON p.id = h.pessoa_id
             WHERE h.entidade='audiencias' AND h.entidade_id=?
             ORDER BY h.em DESC""", (aid,)).fetchall(),
        equipe_l=db.execute("SELECT id, nome FROM pessoas WHERE ativo=true ORDER BY nome").fetchall(),
    )
    db.close()
    return pagina(req, "audiencia.html", **ctx)


CHECKLIST = {
    "cliente_orientado_em": "cliente orientado",
    "testemunhas_confirmadas_em": "testemunhas confirmadas",
    "advideo_em": "ad video feito",
    "documentos_conferidos_em": "documentos conferidos",
}


async def audiencia_checklist(req: Request):
    """Marca (ou desmarca) um item da preparação.

    O primeiro item marcado leva a audiência de DESIGNADA para EM_PREPARACAO —
    e essa mudança passa por `fluxo.mover`, como qualquer outra. Escrever a
    coluna direto faria a etapa andar por fora do mapa.
    """
    u, r = exige(req, "audiencias")
    if r:
        return r
    aid = int(req.path_params["id"])
    f = await req.form()
    item = f.get("item")
    if item not in CHECKLIST:
        return _volta(req, f"/audiencias/{aid}", erro="item de preparação desconhecido")
    db = conectar()
    erro = None
    try:
        atual = db.execute(f"SELECT {item}, situacao FROM audiencias WHERE id=?", (aid,)).fetchone()
        if atual[0]:
            db.execute(f"UPDATE audiencias SET {item}=NULL WHERE id=?", (aid,))
        else:
            db.execute(f"UPDATE audiencias SET {item}=date('now') WHERE id=?", (aid,))
            if atual["situacao"] == "DESIGNADA":
                fluxo.mover(db, "audiencias", aid, "EM_PREPARACAO", _eu(db, u), u["papel"],
                            {"motivo": f"primeiro item da preparação: {CHECKLIST[item]}"})
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, f"/audiencias/{aid}", ok="preparação atualizada", erro=erro)


# =========================================================== prazos
async def prazos(req: Request):
    u, r = exige(req, "prazos")
    if r:
        return r
    p = req.query_params
    db = conectar()
    onde, args = ["1=1"], []
    situacao = p.get("situacao") or "ABERTO"
    if situacao != "todas":
        onde.append("z.situacao = ?"); args.append(situacao)
    if p.get("tipo"):
        onde.append("z.tipo = ?"); args.append(p["tipo"])
    if p.get("origem"):
        onde.append("z.origem = ?"); args.append(p["origem"])
    if p.get("responsavel"):
        onde.append("z.responsavel_id = ?"); args.append(int(p["responsavel"]))
    filtro = " AND ".join(onde)

    linhas = db.execute(f"""SELECT z.*, pt.nome tipo_nome, pt.fundamento, pt.dias dias_legais,
                pr.id proc_id, pr.numero_cnj, pr.trt, pr.vara, c.nome cliente,
                pe.nome responsavel, a.data_hora audiencia_em
             FROM prazos z
             JOIN processos pr ON pr.id = z.processo_id
             JOIN clientes c ON c.id = pr.cliente_id
             LEFT JOIN prazo_tipos pt ON pt.codigo = z.tipo
             LEFT JOIN pessoas pe ON pe.id = z.responsavel_id
             LEFT JOIN audiencias a ON a.id = z.audiencia_id
             WHERE {filtro}
             ORDER BY (z.vencimento IS NULL), z.vencimento LIMIT 300""", tuple(args)).fetchall()
    total = db.execute(f"""SELECT COUNT(*) FROM prazos z
             JOIN processos pr ON pr.id = z.processo_id
             JOIN clientes c ON c.id = pr.cliente_id WHERE {filtro}""",
                       tuple(args)).fetchone()[0]
    ctx = dict(
        linhas=linhas, total=total, p=p,
        # dias ÚTEIS, art. 775 CLT — a conta é de prazo_legal.py, não do banco
        uteis={l["id"]: prazo_legal.faltam(l["vencimento"]) for l in linhas if l["vencimento"]},
        situacoes=db.execute("""SELECT codigo, etapa nome, registros FROM v_funil_etapas
                                WHERE fluxo='PRAZO' ORDER BY ordem""").fetchall(),
        tipos=db.execute("""SELECT pt.codigo, pt.nome, pt.dias, pt.fundamento, pt.fase_usual,
                                   pt.observacao, COUNT(z.id) n
                            FROM prazo_tipos pt LEFT JOIN prazos z ON z.tipo = pt.codigo
                            GROUP BY pt.codigo, pt.nome, pt.dias, pt.fundamento, pt.fase_usual,
                                     pt.observacao
                            ORDER BY n DESC, pt.nome""").fetchall(),
        equipe_l=db.execute("SELECT id, nome FROM pessoas WHERE ativo=true ORDER BY nome").fetchall(),
    )
    db.close()
    return pagina(req, "prazos.html", **ctx)


async def prazo_responsavel(req: Request):
    u, r = exige(req, "prazos")
    if r:
        return r
    zid = int(req.path_params["id"])
    f = await req.form()
    db = conectar()
    erro = None
    try:
        quem = f.get("pessoa_id")
        if quem == "eu":
            quem = _eu(db, u)
        db.execute("UPDATE prazos SET responsavel_id=? WHERE id=?",
                   (int(quem) if quem else None, zid))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, f.get("voltar") or "/prazos", ok="responsável do prazo alterado",
                  erro=erro)


# =========================================================== empresas
async def empresas(req: Request):
    u, r = exige(req, "empresas")
    if r:
        return r
    p = req.query_params
    db = conectar()
    onde, args = ["1=1"], []
    if p.get("situacao"):
        onde.append("e.situacao = ?"); args.append(p["situacao"])
    if p.get("pagamento"):
        onde.append("e.hist_pagamento = ?"); args.append(p["pagamento"])
    if p.get("q"):
        onde.append("(e.nome ILIKE ? OR e.cnpj ILIKE ?)")
        args += ["%" + p["q"] + "%", "%" + _digitos(p["q"]) + "%"]
    filtro = " AND ".join(onde)
    linhas = db.execute(f"""SELECT e.*,
                (SELECT COUNT(*) FROM processos pr WHERE pr.empresa_id = e.id) processos,
                (SELECT COUNT(*) FROM processos pr JOIN fluxo_etapas fe
                   ON fe.fluxo_id=2 AND fe.codigo=pr.fase
                 WHERE pr.empresa_id = e.id AND fe.tipo <> 'FINAL') vivos,
                (SELECT COUNT(*) FROM fragilidades f WHERE f.empresa_id = e.id) teses
             FROM empresas e WHERE {filtro}
             ORDER BY processos DESC, e.nome LIMIT 300""", tuple(args)).fetchall()
    total = db.execute(f"SELECT COUNT(*) FROM empresas e WHERE {filtro}",
                       tuple(args)).fetchone()[0]
    db.close()
    return pagina(req, "empresas.html", linhas=linhas, total=total, p=p)


async def empresa(req: Request):
    u, r = exige(req, "empresas")
    if r:
        return r
    eid = int(req.path_params["id"])
    db = conectar()
    e = db.execute("SELECT * FROM empresas WHERE id=?", (eid,)).fetchone()
    if not e:
        db.close()
        return RedirectResponse("/empresas", 302)
    ctx = dict(
        e=e,
        processos=db.execute("""SELECT pr.id, pr.numero_cnj, pr.fase, pr.trt, pr.vara,
                    pr.valor_causa_centavos, pr.resultado_final, fe.nome fase_nome,
                    c.nome cliente, c.id cliente_id
                 FROM processos pr JOIN clientes c ON c.id = pr.cliente_id
                 LEFT JOIN fluxo_etapas fe ON fe.fluxo_id=2 AND fe.codigo=pr.fase
                 WHERE pr.empresa_id=? ORDER BY fe.ordem, pr.id LIMIT 200""", (eid,)).fetchall(),
        fragilidades=db.execute("""SELECT * FROM fragilidades WHERE empresa_id=?
                                   ORDER BY (situacao='ACOLHIDA') DESC, achado""",
                                (eid,)).fetchall(),
        testemunhas=db.execute("""SELECT * FROM testemunhas WHERE empresa_id=?
                                  ORDER BY situacao, nome LIMIT 100""", (eid,)).fetchall(),
        recebido=db.execute("""SELECT COALESCE(SUM(rb.valor_centavos),0) FROM recebimentos rb
                 JOIN processos pr ON pr.id = rb.processo_id
                 WHERE pr.empresa_id=? AND rb.base='TOTAL'""", (eid,)).fetchone()[0],
        anotacoes=db.execute("""SELECT a.*, p.nome autor FROM anotacoes a
                 LEFT JOIN pessoas p ON p.id = a.autor_id
                 WHERE a.empresa_id=? ORDER BY a.em DESC LIMIT 30""", (eid,)).fetchall(),
        por_fase=db.execute("""SELECT fe.nome, fe.ordem, COUNT(*) n FROM processos pr
                 JOIN fluxo_etapas fe ON fe.fluxo_id=2 AND fe.codigo=pr.fase
                 WHERE pr.empresa_id=? GROUP BY fe.nome, fe.ordem ORDER BY fe.ordem""",
                            (eid,)).fetchall(),
    )
    db.close()
    return pagina(req, "empresa.html", **ctx)


# =========================================================== testemunhas
async def testemunhas(req: Request):
    u, r = exige(req, "testemunhas")
    if r:
        return r
    p = req.query_params
    db = conectar()
    onde, args = ["1=1"], []
    if p.get("situacao"):
        onde.append("t.situacao = ?"); args.append(p["situacao"])
    if p.get("origem"):
        onde.append("t.origem = ?"); args.append(p["origem"])
    if p.get("empresa"):
        onde.append("t.empresa_id = ?"); args.append(int(p["empresa"]))
    if p.get("q"):
        onde.append("t.nome ILIKE ?"); args.append(f"%{p['q']}%")
    if p.get("processo"):
        onde.append("""EXISTS (SELECT 1 FROM testemunha_vinculos v
                               WHERE v.testemunha_id=t.id AND v.processo_id=?)""")
        args.append(int(p["processo"]))
    filtro = " AND ".join(onde)
    linhas = db.execute(f"""SELECT t.*, em.nome empresa, cap.nome captador,
                (SELECT COUNT(*) FROM testemunha_vinculos v WHERE v.testemunha_id=t.id) vinculos
             FROM testemunhas t
             LEFT JOIN empresas em ON em.id = t.empresa_id
             LEFT JOIN pessoas cap ON cap.id = t.captador_id
             WHERE {filtro} ORDER BY t.situacao, t.nome LIMIT 300""", tuple(args)).fetchall()
    total = db.execute(f"SELECT COUNT(*) FROM testemunhas t WHERE {filtro}",
                       tuple(args)).fetchone()[0]
    ctx = dict(
        linhas=linhas, total=total, p=p,
        situacoes=db.execute("""SELECT situacao, COUNT(*) n FROM testemunhas
                                GROUP BY situacao ORDER BY n DESC""").fetchall(),
        empresas_l=db.execute("""SELECT e.id, e.nome, COUNT(t.id) n FROM empresas e
                                 JOIN testemunhas t ON t.empresa_id = e.id
                                 GROUP BY e.id, e.nome ORDER BY n DESC LIMIT 40""").fetchall(),
    )
    db.close()
    return pagina(req, "testemunhas.html", **ctx)


async def testemunha(req: Request):
    u, r = exige(req, "testemunhas")
    if r:
        return r
    tid = int(req.path_params["id"])
    db = conectar()
    t = db.execute("""SELECT t.*, em.nome empresa, cap.nome captador
                      FROM testemunhas t
                      LEFT JOIN empresas em ON em.id = t.empresa_id
                      LEFT JOIN pessoas cap ON cap.id = t.captador_id
                      WHERE t.id=?""", (tid,)).fetchone()
    if not t:
        db.close()
        return RedirectResponse("/testemunhas", 302)
    ctx = dict(
        t=t,
        vinculos=db.execute("""SELECT v.*, pr.numero_cnj, pr.id proc_id, c.nome cliente,
                    c.id cliente_id, a.data_hora audiencia_em
                 FROM testemunha_vinculos v
                 LEFT JOIN processos pr ON pr.id = v.processo_id
                 LEFT JOIN clientes c ON c.id = COALESCE(v.cliente_id, pr.cliente_id)
                 LEFT JOIN audiencias a ON a.id = v.audiencia_id
                 WHERE v.testemunha_id=?""", (tid,)).fetchall(),
        contatos=db.execute("""SELECT ct.*, p.nome quem FROM contatos ct
                 LEFT JOIN pessoas p ON p.id = ct.pessoa_id
                 WHERE ct.testemunha_id=? ORDER BY ct.em DESC""", (tid,)).fetchall(),
        anotacoes=db.execute("""SELECT a.*, p.nome autor FROM anotacoes a
                 LEFT JOIN pessoas p ON p.id = a.autor_id
                 WHERE a.testemunha_id=? ORDER BY a.em DESC""", (tid,)).fetchall(),
        auditoria=db.execute("""SELECT * FROM testemunha_auditoria WHERE testemunha_id=?
                                ORDER BY em DESC LIMIT 30""", (tid,)).fetchall(),
    )
    db.close()
    return pagina(req, "testemunha.html", **ctx)


# =========================================================== conferências
async def conferencias(req: Request):
    u, r = exige(req, "conferencias")
    if r:
        return r
    p = req.query_params
    db = conectar()
    onde, args = ["1=1"], []
    situacao = p.get("situacao") or "abertas"
    if situacao == "abertas":
        onde.append("cf.situacao IN ('ABERTA','EM_ANALISE')")
    elif situacao != "todas":
        onde.append("cf.situacao = ?"); args.append(situacao)
    if p.get("tipo"):
        onde.append("cf.tipo = ?"); args.append(p["tipo"])
    if p.get("entidade"):
        onde.append("cf.entidade = ?"); args.append(p["entidade"])
    if p.get("dono") == "sem":
        onde.append("cf.dono_id IS NULL")
    elif p.get("dono"):
        onde.append("cf.dono_id = ?"); args.append(int(p["dono"]))
    filtro = " AND ".join(onde)
    linhas = db.execute(f"""SELECT cf.*, pe.nome dono FROM conferencias cf
             LEFT JOIN pessoas pe ON pe.id = cf.dono_id
             WHERE {filtro} ORDER BY cf.tipo, cf.id LIMIT 300""", tuple(args)).fetchall()
    total = db.execute(f"SELECT COUNT(*) FROM conferencias cf WHERE {filtro}",
                       tuple(args)).fetchone()[0]
    ctx = dict(
        linhas=linhas, total=total, p=p,
        tipos=db.execute("""SELECT tipo, COUNT(*) n FROM conferencias
                            WHERE situacao IN ('ABERTA','EM_ANALISE')
                            GROUP BY tipo ORDER BY n DESC""").fetchall(),
        entidades=db.execute("""SELECT entidade, COUNT(*) n FROM conferencias
                                WHERE situacao IN ('ABERTA','EM_ANALISE')
                                GROUP BY entidade ORDER BY n DESC""").fetchall(),
        equipe_l=db.execute("SELECT id, nome FROM pessoas WHERE ativo=true ORDER BY nome").fetchall(),
        faltantes=db.execute("""SELECT COUNT(*) FROM conferencia_faltantes
                                WHERE validar_e_subir = false""").fetchone()[0],
    )
    db.close()
    return pagina(req, "conferencias.html", **ctx)


async def conferencia_resolver(req: Request):
    """Resolver é escolher um lado, ou anotar por que nenhum serve.

    Não há botão "resolver" sozinho: sem dizer QUAL valor vale, a linha some da
    fila e a divergência continua no banco.
    """
    u, r = exige(req, "conferencias")
    if r:
        return r
    cid = int(req.path_params["id"])
    f = await req.form()
    db = conectar()
    erro = None
    acao = f.get("acao")
    try:
        eu = _eu(db, u)
        if acao == "dono":
            quem = f.get("pessoa_id")
            if quem == "eu":
                quem = eu
            db.execute("UPDATE conferencias SET dono_id=?, situacao='EM_ANALISE' WHERE id=?",
                       (int(quem) if quem else None, cid))
        elif acao in ("a", "b"):
            escolhido = db.execute(
                f"SELECT valor_{acao} FROM conferencias WHERE id=?", (cid,)).fetchone()[0]
            db.execute("""UPDATE conferencias SET escolhido=?, situacao='RESOLVIDA',
                            resolvido_em=datetime('now'), resolvido_por=?,
                            anotacao=COALESCE(?, anotacao) WHERE id=?""",
                       (escolhido, eu, (f.get("anotacao") or "").strip() or None, cid))
        elif acao == "anotar":
            texto = (f.get("anotacao") or "").strip()
            if not texto:
                erro = "escreva a anotação"
            else:
                db.execute("UPDATE conferencias SET anotacao=?, situacao='EM_ANALISE' WHERE id=?",
                           (texto, cid))
        elif acao == "ignorar":
            texto = (f.get("anotacao") or "").strip()
            if not texto:
                erro = "ignorar exige o motivo escrito"
            else:
                db.execute("""UPDATE conferencias SET situacao='IGNORADA', anotacao=?,
                                resolvido_em=datetime('now'), resolvido_por=? WHERE id=?""",
                           (texto, eu, cid))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, "/conferencias" + _qs(req), ok="conferência atualizada", erro=erro)


# =========================================================== equipe e tarefas
async def tarefas(req: Request):
    u, r = exige(req, "tarefas")
    if r:
        return r
    p = req.query_params
    db = conectar()
    eu = _eu(db, u)
    onde, args = ["1=1"], []
    quem = p.get("quem") or "minhas"
    if quem == "minhas":
        onde.append("t.responsavel_id = ?"); args.append(eu)
    elif quem == "sem_dono":
        onde.append("t.responsavel_id IS NULL")
    elif quem.isdigit():
        onde.append("t.responsavel_id = ?"); args.append(int(quem))
    situacao = p.get("situacao") or "abertas"
    if situacao == "abertas":
        onde.append("t.status IN ('ABERTA','EM_ANDAMENTO')")
    elif situacao != "todas":
        onde.append("t.status = ?"); args.append(situacao)
    if p.get("grupo"):
        onde.append("t.grupo = ?"); args.append(p["grupo"])
    if p.get("tipo"):
        onde.append("t.tipo = ?"); args.append(p["tipo"])
    filtro = " AND ".join(onde)
    linhas = db.execute(f"""SELECT t.*, pe.nome responsavel, c.nome cliente, c.id cliente_id,
                pr.numero_cnj, pr.id proc_id,
                (t.prazo IS NOT NULL AND t.prazo < date('now')) atrasada
             FROM tarefas t
             LEFT JOIN pessoas pe ON pe.id = t.responsavel_id
             LEFT JOIN clientes c ON c.id = t.cliente_id
             LEFT JOIN processos pr ON pr.id = t.processo_id
             WHERE {filtro}
             ORDER BY (t.prioridade<>'URGENTE'), (t.prazo IS NULL), t.prazo LIMIT 300""",
                        tuple(args)).fetchall()
    total = db.execute(f"SELECT COUNT(*) FROM tarefas t WHERE {filtro}",
                       tuple(args)).fetchone()[0]
    ctx = dict(
        linhas=linhas, total=total, p=p, quem=quem,
        grupos=db.execute("""SELECT grupo, COUNT(*) n FROM tarefas
                             WHERE status IN ('ABERTA','EM_ANDAMENTO') AND grupo IS NOT NULL
                             GROUP BY grupo ORDER BY n DESC""").fetchall(),
        tipos=db.execute("""SELECT tipo, COUNT(*) n FROM tarefas
                            WHERE status IN ('ABERTA','EM_ANDAMENTO')
                            GROUP BY tipo ORDER BY n DESC""").fetchall(),
        carga=equipe.carga(db),
        sem_dono=db.execute("""SELECT COUNT(*) FROM tarefas
                               WHERE responsavel_id IS NULL AND status='ABERTA'""").fetchone()[0],
    )
    db.close()
    return pagina(req, "tarefas.html", **ctx)


async def tarefa_status(req: Request):
    u, r = exige(req, "tarefas")
    if r:
        return r
    tid = int(req.path_params["id"])
    f = await req.form()
    novo = f.get("status")
    db = conectar()
    erro = None
    try:
        if novo == "CONCLUIDA":
            db.execute("""UPDATE tarefas SET status='CONCLUIDA', concluida_em=datetime('now'),
                            concluida_por=? WHERE id=?""", (_eu(db, u), tid))
        elif novo == "assumir":
            db.execute("UPDATE tarefas SET responsavel_id=?, status='EM_ANDAMENTO' WHERE id=?",
                       (_eu(db, u), tid))
        elif novo in ("ABERTA", "EM_ANDAMENTO", "CANCELADA"):
            db.execute("UPDATE tarefas SET status=?, concluida_em=NULL WHERE id=?", (novo, tid))
        db.commit()
    except (ValueError,) + banco.ErroBanco as e:
        erro = _recado(e)
    finally:
        db.close()
    return _volta(req, f.get("voltar") or "/tarefas", ok="tarefa atualizada", erro=erro)


async def equipe_tela(req: Request):
    u, r = exige(req, "equipe")
    if r:
        return r
    db = conectar()
    ctx = dict(
        pessoas=db.execute("""SELECT p.*, s.nome supervisor,
                    (SELECT COUNT(*) FROM tarefas t WHERE t.responsavel_id=p.id
                       AND t.status IN ('ABERTA','EM_ANDAMENTO')) abertas,
                    (SELECT COUNT(*) FROM processos pr WHERE pr.advogado_id=p.id) processos,
                    (SELECT string_agg(pp.papel, ', ') FROM pessoa_papeis pp
                       WHERE pp.pessoa_id=p.id) papeis,
                    (SELECT COUNT(*) FROM usuarios us WHERE us.pessoa_id=p.id) tem_acesso
                 FROM pessoas p LEFT JOIN pessoas s ON s.id = p.supervisor_id
                 ORDER BY (NOT p.ativo), p.setor NULLS LAST, p.nome""").fetchall(),
        carga=equipe.carga(db),
        setores=equipe.SETORES,
        setores_da_governanca=db.execute("""SELECT DISTINCT grupo FROM fluxo_etapas
                                            WHERE grupo IS NOT NULL ORDER BY grupo""").fetchall(),
        sem_setor=db.execute("""SELECT COUNT(*) FROM pessoas
                                WHERE ativo=true AND setor IS NULL""").fetchone()[0],
    )
    db.close()
    return pagina(req, "equipe.html", **ctx)


async def fluxos(req: Request):
    """O mapa de etapas, como o banco o guarda. Nada aqui é escrito no template."""
    u, r = exige(req, "fluxos")
    if r:
        return r
    db = conectar()
    ctx = dict(
        fluxos=db.execute("SELECT * FROM fluxos ORDER BY id").fetchall(),
        etapas=db.execute("""SELECT f.codigo fluxo, e.* FROM fluxo_etapas e
                             JOIN fluxos f ON f.id = e.fluxo_id
                             ORDER BY e.fluxo_id, e.ordem""").fetchall(),
        transicoes=db.execute("""SELECT f.codigo fluxo, t.*, de_e.nome de_nome,
                    para_e.nome para_nome, de_e.ordem de_ordem
                 FROM fluxo_transicoes t
                 JOIN fluxos f ON f.id = t.fluxo_id
                 LEFT JOIN fluxo_etapas de_e ON de_e.fluxo_id=t.fluxo_id AND de_e.codigo=t.de
                 LEFT JOIN fluxo_etapas para_e ON para_e.fluxo_id=t.fluxo_id AND para_e.codigo=t.para
                 ORDER BY t.fluxo_id, de_e.ordem, para_e.ordem""").fetchall(),
        contagem={r["codigo"]: r["registros"] for r in db.execute("SELECT * FROM v_funil_etapas")},
        prazo_tipos=db.execute("SELECT * FROM prazo_tipos ORDER BY fase_usual, nome").fetchall(),
        automacoes=db.execute("SELECT * FROM automacoes ORDER BY codigo").fetchall(),
        execucoes=db.execute("""SELECT automacao, resultado, COUNT(*) n, MAX(em) ultima
                                FROM automacao_log GROUP BY automacao, resultado
                                ORDER BY automacao""").fetchall(),
    )
    db.close()
    return pagina(req, "fluxos.html", **ctx)


async def painel(req: Request):
    u, r = exige(req, "painel")
    if r:
        return r
    db = conectar()
    ctx = dict(
        funil=db.execute("SELECT * FROM v_funil_etapas ORDER BY fluxo, ordem").fetchall(),
        estagnados=db.execute("""SELECT entidade, etapa, nome, grupo, sla_dias,
                    COUNT(*) n, MAX(dias_parado) pior
                 FROM v_estagnados GROUP BY entidade, etapa, nome, grupo, sla_dias
                 ORDER BY n DESC""").fetchall(),
        farol=db.execute("""SELECT farol, COUNT(*) n FROM v_pre_processual_atrasado
                            WHERE farol IS NOT NULL GROUP BY farol""").fetchall(),
        resultados=db.execute("""SELECT resultado_final, COUNT(*) n FROM processos
                                 WHERE resultado_final IS NOT NULL
                                 GROUP BY resultado_final ORDER BY n DESC""").fetchall(),
        dinheiro=db.execute("""SELECT base, COUNT(*) n, COALESCE(SUM(valor_centavos),0) total
                               FROM recebimentos GROUP BY base ORDER BY base""").fetchall(),
        acordos=db.execute("""SELECT situacao, COUNT(*) n,
                    COALESCE(SUM(valor_centavos),0) total FROM acordos
                 GROUP BY situacao ORDER BY n DESC""").fetchall(),
        por_trt=db.execute("""SELECT trt, COUNT(*) n FROM processos WHERE trt IS NOT NULL
                              GROUP BY trt ORDER BY n DESC LIMIT 12""").fetchall(),
        prazos_perdidos=db.execute("""SELECT COUNT(*) FROM prazos
                                      WHERE situacao='PERDIDO'""").fetchone()[0],
        ausencias=db.execute("""SELECT COUNT(*) FROM audiencias
                                WHERE motivo='AUSENCIA_RECLAMANTE'""").fetchone()[0],
        incidentes=db.execute("""SELECT situacao, COUNT(*) n FROM incidentes
                                 GROUP BY situacao ORDER BY n DESC""").fetchall(),
    )
    db.close()
    return pagina(req, "painel.html", **ctx)


# =========================================================== transição
TELA_DE = {"clientes": "clientes", "processos": "processos", "audiencias": "audiencias",
           "prazos": "prazos", "incidentes": "processos"}
DESTINO_DE = {"clientes": "/clientes/{}", "processos": "/processos/{}",
              "audiencias": "/audiencias/{}", "prazos": "/prazos",
              "incidentes": "/processos"}


async def mover(req: Request):
    """A única porta por onde a etapa muda, para as cinco máquinas.

    Uma função só, e não cinco: se a regra de "o que fazer ao mover" existir em
    cinco lugares, um dia elas discordam. O que varia — a tela de permissão e
    para onde voltar — está nas duas tabelas acima.
    """
    entidade = req.path_params["entidade"]
    if entidade not in fluxo.FLUXO_DE:
        return RedirectResponse("/", 302)
    u, r = exige(req, TELA_DE[entidade])
    if r:
        return r
    rid = int(req.path_params["id"])
    f = await req.form()
    dados = {k: v for k, v in f.items() if not k.startswith("_")}
    destino = f.get("voltar") or DESTINO_DE[entidade].format(rid)
    if not destino.startswith("/"):
        destino = DESTINO_DE[entidade].format(rid)
    db = conectar()
    erro = None
    try:
        fluxo.mover(db, entidade, rid, f.get("para"), _eu(db, u), u["papel"], dados)
    except ValueError as e:
        erro = str(e)
    except banco.ErroBanco as e:
        # a recusa do gatilho vira recado na tela, não 500. A mensagem do
        # PL/pgSQL já é escrita para gente ler — só se tira o cabeçalho técnico.
        erro = _recado(e)
    finally:
        # `close()` da Ponte dá rollback e DEVOLVE a conexão ao poço. Fora do
        # finally, a exceção pulava esta linha e a conexão nunca voltava: com
        # `max_size=6`, seis recusas paravam o portal inteiro (PoolTimeout).
        db.close()
    return _volta(req, destino, ok="etapa alterada e registrada no histórico", erro=erro)


# =========================================================== rotas
rotas = [
    Route("/entrar", entrar, methods=["GET", "POST"]),
    Route("/sair", sair),
    Route("/senha", senha, methods=["GET", "POST"]),
    Route("/saude", saude),
    Route("/", inicio),
    Route("/api/agora", api_agora),

    Route("/clientes", clientes),
    Route("/clientes/{id:int}", cliente),
    Route("/clientes/{id:int}/responsavel", cliente_responsavel, methods=["POST"]),
    Route("/clientes/{id:int}/pendencia", pendencia_nova, methods=["POST"]),
    Route("/pendencia/{id:int}/resolver", pendencia_resolver, methods=["POST"]),

    Route("/processos", processos),
    Route("/processos/{id:int}", processo),
    Route("/processos/{id:int}/anotacao", processo_anotacao, methods=["POST"]),
    Route("/processos/{id:int}/repasse", processo_repasse, methods=["POST"]),

    Route("/audiencias", audiencias),
    Route("/audiencias/{id:int}", audiencia),
    Route("/audiencias/{id:int}/checklist", audiencia_checklist, methods=["POST"]),

    Route("/prazos", prazos),
    Route("/prazo/{id:int}/responsavel", prazo_responsavel, methods=["POST"]),

    Route("/empresas", empresas),
    Route("/empresas/{id:int}", empresa),

    Route("/testemunhas", testemunhas),
    Route("/testemunhas/{id:int}", testemunha),

    Route("/conferencias", conferencias),
    Route("/conferencia/{id:int}/resolver", conferencia_resolver, methods=["POST"]),

    Route("/tarefas", tarefas),
    Route("/tarefa/{id:int}/status", tarefa_status, methods=["POST"]),
    Route("/equipe", equipe_tela),
    Route("/fluxos", fluxos),
    Route("/painel", painel),

    # a porta única da governança, para as cinco máquinas
    Route("/mover/{entidade}/{id:int}", mover, methods=["POST"]),

    Mount("/static", StaticFiles(directory=os.path.join(AQUI, "static")), name="static"),
]

#  A ordem importa: `SessionMiddleware` primeiro, `csrf.Trava` depois. O
#  Starlette aplica de fora para dentro, então a sessão já está montada em
#  `scope["session"]` quando a trava roda — e é de lá que sai o token.
#  Invertido, a trava veria sessão nenhuma e recusaria todo POST do sistema.
def _segredo():
    """O segredo que assina o cookie de sessão. Sem ele o portal NÃO sobe.

    Já houve aqui um valor fixo de reserva (`"trocar-em-producao"`), e reserva
    é o problema: quem esquece a variável não vê erro nenhum, sobe, e passa a
    assinar sessão com um segredo que está escrito no repositório — uma sessão
    forjada em qualquer cópia do código valeria nesta instalação, e o portal
    todo se apoia no cookie para saber quem é quem e qual é o papel.

    Recusar subir é barulhento de propósito: o modo de falha de segurança é o
    silêncio, e um portal que não sobe é problema de cinco segundos; um portal
    que sobe com o segredo de teste é problema de ninguém perceber.
    """
    import sys
    s = (os.environ.get("GGV_SEGREDO") or "").strip()
    if not s:
        sys.exit(
            "✗ GGV_SEGREDO não definido — o portal não sobe sem ele.\n"
            "  É o segredo que assina o cookie de sessão. Não há valor de\n"
            "  reserva: um segredo escrito no repositório valeria em qualquer\n"
            "  instalação e deixaria forjar sessão.\n"
            "  Gere um e guarde (Keychain, ou o gestor de segredos do servidor):\n"
            "      export GGV_SEGREDO=$(python3 -c \"import secrets;"
            "print(secrets.token_urlsafe(48))\")\n"
            "  Trocar o segredo derruba as sessões abertas — é só entrar de novo.")
    if len(s) < 32:
        sys.exit(f"✗ GGV_SEGREDO tem {len(s)} caracteres; use pelo menos 32 "
                 "(secrets.token_urlsafe(48)). Segredo curto é segredo adivinhável.")
    return s


app = Starlette(routes=rotas, middleware=[
    Middleware(SessionMiddleware, secret_key=_segredo(),
               session_cookie="ggvtrab", max_age=8 * 3600),
    Middleware(csrf.Trava),
])
