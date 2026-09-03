#!/usr/bin/env python3
"""A trava contra pedido forjado de outro site (CSRF).

O ataque: alguém do escritório está logado aqui e abre outra aba com uma
página maliciosa. Essa página tem um formulário escondido que dispara
`POST /financeiro/lancar` — e o navegador manda o cookie de sessão junto,
porque é assim que cookie funciona. Do lado do servidor, o pedido parece
legítimo: sessão válida, permissão válida, tudo certo.

O sistema não tinha proteção nenhuma contra isso. Deu para conviver enquanto
tudo aqui era leitura e escrita de processo; deixou de dar quando o sistema
passou a lançar dinheiro e dar baixa em título.

**Por que middleware, e não um campo em cada tela.** São 89 formulários POST
em 65 telas, e 18 delas são cópia gerada do portal financeiro — editar à mão
seria desfeito na próxima importação. Aqui o token entra na VOLTA, no HTML já
pronto, e é conferido na IDA. Nenhuma tela sabe que ele existe.

**O token é da sessão, não do formulário.** Um por sessão, guardado no cookie
assinado. Trocá-lo a cada tela obrigaria a guardar uma lista de tokens vivos —
mais peça para manter, e sem ganho real contra este ataque.

**Ele muda quando alguém entra.** Sem isso, um token capturado antes do login
continuaria valendo depois — a mesma sessão, agora com poderes.

**A conferência é `compare_digest`.** Comparar com `==` vaza o tamanho do
prefixo correto pelo tempo de resposta. É pouco, mas custa uma linha evitar.

O que fica de fora, e por quê:

  GET, HEAD, OPTIONS   não mudam nada. Se mudarem, o defeito é a rota.
  `/saude`             é o healthcheck do hospedeiro, que não tem sessão.
  `/entrar`            recebe token na tela de login (o GET já cria sessão),
                       porque login forjado também é ataque: põe a vítima
                       dentro da conta do atacante sem ela perceber.
"""
import re
import secrets
from urllib.parse import parse_qs

CAMPO = "_ggv"
CABECALHO = "x-ggv-token"
CHAVE_SESSAO = "_csrf"

#  Rotas que não passam pela trava. Curta de propósito: cada nome aqui é uma
#  porta, e portas se justificam uma a uma.
LIVRES = {"/saude"}

METODOS = {"POST", "PUT", "PATCH", "DELETE"}

#  `<form ...>` cujo method é post. O `[^>]*` não atravessa `>`, então não
#  há como casar dois formulários de uma vez.
_FORM = re.compile(rb'<form\b[^>]*\bmethod\s*=\s*["\']?post["\']?[^>]*>', re.I)
#  Formulário que aponta para fora: não recebe token. Mandar o nosso token a
#  outro site é entregar de graça o que este arquivo existe para proteger.
_EXTERNO = re.compile(rb'action\s*=\s*["\']https?://', re.I)
#  Do corpo multipart, onde `parse_qs` não serve.
_MULTIPART = re.compile(
    rb'name="' + CAMPO.encode() + rb'"\r?\n\r?\n([A-Za-z0-9_-]{16,64})')


def token_da(sessao):
    """O token desta sessão, criando na primeira vez."""
    t = sessao.get(CHAVE_SESSAO)
    if not t:
        t = secrets.token_urlsafe(32)
        sessao[CHAVE_SESSAO] = t
    return t


def girar(sessao):
    """Troca o token. Chamado ao entrar e ao sair.

    Sem isto, um token capturado antes do login continuaria válido depois —
    mesma sessão, agora com poderes.
    """
    sessao[CHAVE_SESSAO] = secrets.token_urlsafe(32)
    return sessao[CHAVE_SESSAO]


def _do_corpo(corpo, tipo):
    """Acha o token no corpo do POST. Devolve "" quando não há."""
    if not corpo:
        return ""
    if b"multipart/form-data" in tipo:
        #  `parse_qs` não lê multipart, e ler o corpo inteiro com um parser de
        #  verdade aqui gastaria memória com arquivo grande. O campo é curto e
        #  vem cedo; a expressão o acha sem montar o resto.
        m = _MULTIPART.search(corpo[:8192])
        return m.group(1).decode() if m else ""
    try:
        return (parse_qs(corpo.decode("utf-8", "replace")).get(CAMPO) or [""])[0]
    except ValueError:
        return ""


class Trava:
    """Middleware ASGI puro.

    ASGI puro e não `BaseHTTPMiddleware` porque é preciso LER o corpo do POST
    para achar o token e depois DEVOLVÊ-LO ao handler. Com o middleware de
    conveniência do Starlette, ler o corpo o consome, e a rota recebe um
    formulário vazio — um defeito que aparece só em produção, na primeira tela
    com upload.
    """

    def __init__(self, app, recusa=None):
        self.app = app
        self.recusa = recusa or _recusa_padrao

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        caminho = scope.get("path", "")
        metodo = scope.get("method", "GET").upper()

        if metodo in METODOS and caminho not in LIVRES:
            corpo = await _juntar(receive)
            cabecalhos = {k.decode().lower(): v.decode()
                          for k, v in scope.get("headers", [])}
            enviado = (_do_corpo(corpo, cabecalhos.get("content-type", "").encode())
                       or cabecalhos.get(CABECALHO, ""))
            esperado = (scope.get("session") or {}).get(CHAVE_SESSAO, "")

            if not esperado or not enviado or not secrets.compare_digest(
                    str(enviado), str(esperado)):
                return await self.recusa(scope, receive, send, bool(esperado))

            #  Devolve o corpo ao handler, que ainda não o leu.
            receive = _repor(corpo)

        #  Na volta: injeta o token nos formulários do HTML.
        pego = {"inicio": None, "html": False}

        async def enviar(msg):
            if msg["type"] == "http.response.start":
                tipo = ""
                for k, v in msg.get("headers", []):
                    if k.lower() == b"content-type":
                        tipo = v.decode().lower()
                pego["html"] = "text/html" in tipo
                if not pego["html"]:
                    return await send(msg)
                pego["inicio"] = msg          # segura: o tamanho vai mudar
                return
            if msg["type"] == "http.response.body" and pego["html"]:
                corpo = msg.get("body", b"")
                if msg.get("more_body"):
                    #  Resposta em pedaços com HTML é rara aqui (as telas são
                    #  renderizadas de uma vez). Injetar em pedaço exigiria
                    #  montar tudo em memória, então deixa passar sem token —
                    #  e a conferência de ida continua valendo.
                    if pego["inicio"]:
                        await send(pego["inicio"]); pego["inicio"] = None
                    return await send(msg)
                novo = _injetar(corpo, (scope.get("session") or {}).get(CHAVE_SESSAO, ""))
                inicio = pego["inicio"]
                if inicio is not None:
                    inicio = dict(inicio)
                    inicio["headers"] = [
                        (k, str(len(novo)).encode() if k.lower() == b"content-length" else v)
                        for k, v in inicio["headers"]]
                    await send(inicio); pego["inicio"] = None
                return await send({**msg, "body": novo})
            if pego["inicio"] is not None:
                await send(pego["inicio"]); pego["inicio"] = None
            return await send(msg)

        await self.app(scope, receive, enviar)


_HEAD = re.compile(rb"</head>", re.I)


def _injetar(html, token):
    if not token:
        return html
    baixo = html.lower()

    #  O token também vai num `<meta>`, para o JavaScript alcançá-lo. Sem
    #  isso, todo `fetch` com POST seria recusado — e o primeiro a quebrar
    #  seria arrastar tarefa entre colunas no Meu Dia, que não tem formulário
    #  nenhum para receber o campo escondido.
    if b"</head>" in baixo:
        meta = (f'<meta name="ggv-token" content="{token}"></head>').encode()
        html = _HEAD.sub(meta, html, count=1)

    if b"<form" not in baixo:
        return html
    campo = (f'<input type="hidden" name="{CAMPO}" value="{token}">').encode()

    def troca(m):
        tag = m.group(0)
        if _EXTERNO.search(tag):
            return tag              # formulário para fora não leva o nosso token
        return tag + campo

    return _FORM.sub(troca, html)


async def _juntar(receive):
    partes, mais = [], True
    while mais:
        msg = await receive()
        if msg["type"] == "http.disconnect":
            break
        partes.append(msg.get("body", b""))
        mais = msg.get("more_body", False)
    return b"".join(partes)


def _repor(corpo):
    entregue = {"feito": False}

    async def receive():
        if entregue["feito"]:
            return {"type": "http.disconnect"}
        entregue["feito"] = True
        return {"type": "http.request", "body": corpo, "more_body": False}

    return receive


async def _recusa_padrao(scope, receive, send, tinha_sessao):
    """A recusa explica, porque o caso mais comum não é ataque.

    É a aba que ficou aberta a noite inteira: a sessão expirou, o token
    morreu junto, e a pessoa clica em salvar. Dizer "403" e nada mais faz
    parecer defeito do sistema — e ela tenta de novo, e de novo.
    """
    from starlette.responses import HTMLResponse
    recado = ("A sua sessão expirou enquanto esta tela estava aberta."
              if not tinha_sessao else
              "Este pedido não veio de dentro do sistema.")
    corpo = f"""<!doctype html><meta charset="utf-8">
<title>Pedido não aceito · GGV Trabalhista</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:520px;margin:14vh auto;
padding:0 20px;background:#0f1216;color:#e6e9ee}}
a{{color:#7ab7e8}} .c{{background:#171b21;border:1px solid #232a33;
border-radius:10px;padding:18px 20px}}</style>
<div class="c"><h1 style="margin:0 0 8px;font-size:19px">Não gravei</h1>
<p>{recado}</p>
<p style="color:#98a2b0;font-size:13.5px">Nada foi alterado. Abra a tela de
novo e refaça — o que você digitou não foi perdido se ainda estiver na aba
anterior.</p>
<p><a href="/entrar">entrar de novo</a> · <a href="/">voltar ao início</a></p>
</div>"""
    await HTMLResponse(corpo, status_code=403)(scope, receive, send)
