#!/usr/bin/env python3
"""Manda a agenda do sistema para o Google Calendar de cada pessoa.

**Mão única, e isso não é detalhe: é a regra que impede a agenda de mentir.**
O sistema escreve no Google; nada que a pessoa mexer no celular volta. Se
voltasse, um arrasto sem querer no telefone mudaria a data de uma perícia
médica — e a perícia continuaria marcada no dia certo lá no INSS. A agenda do
escritório é a que vale; o Google é uma cópia para o bolso.

Por isso aqui não existe leitura do calendário nem webhook de entrada. Só saída.

    ./.venv/bin/python agenda_google.py            # o que SERIA enviado (seco)
    ./.venv/bin/python agenda_google.py --pessoa 7 # só de uma pessoa
    ./.venv/bin/python agenda_google.py --enviar   # envia de verdade

O modo seco é o padrão de propósito: dá para conferir o que sairia antes de
qualquer coisa chegar ao telefone de alguém.

FALTA PARA FUNCIONAR (só o Lucas pode fazer, ver docs/agenda-google.md):
  1. um projeto no Google Cloud com a Calendar API ligada;
  2. credencial OAuth de aplicativo instalado;
  3. `tk google-agenda` guardando o client_id e o client_secret no Keychain.
Sem isso o módulo roda seco e diz exatamente o que falta — não quebra.
"""
import json
import os
import subprocess
import sys
from datetime import datetime

import banco

# o que sincroniza: compromisso que ainda vai acontecer e não foi desmarcado
STATUS_SINCRONIZA = ("AGENDADO", "CONFIRMADO", "AVISADO", "REMARCADO")

# como cada tipo aparece no calendário da pessoa
TITULO = {
    "PERICIA_MEDICA":   "Perícia médica",
    "AVALIACAO_SOCIAL": "Avaliação social",
    "AUDIENCIA":        "Audiência",
    "VISITA":           "Entrevista no escritório",
    "REUNIAO":          "Reunião",
    "FOLLOW_UP":        "Retomar contato",
    "ENTREGA_DOCUMENTO": "Entrega de documento",
    "ENTRADA_PREVISTA": "Entrada prevista",
    "AGUARDANDO_REQUISITO": "Aguardando requisito",
}
BASE = "http://127.0.0.1:8770"


def credenciais():
    """client_id e client_secret, do Keychain. None quando ainda não existem."""
    import chaves
    guardado = chaves.ler("google-agenda")
    if not guardado:
        return None
    r = type("R", (), {"stdout": guardado})()
    try:
        d = json.loads(r.stdout.strip())
        return d if d.get("client_id") and d.get("client_secret") else None
    except ValueError:
        return None


def conectados(db):
    """Quem já autorizou. A referência mora no banco; o token, no cofre."""
    return db.execute("""SELECT u.id, u.email, u.pessoa_id, p.nome,
                                u.google_token_ref, u.google_sync_em, u.google_sync_erro
                         FROM usuarios u JOIN pessoas p ON p.id = u.pessoa_id
                         WHERE u.ativo=1 AND u.google_token_ref IS NOT NULL""").fetchall()


def a_enviar(db, pessoa_id=None):
    """Os eventos que iriam para o calendário — de hoje em diante, só isso.

    Histórico não sobe: encheria o calendário de coisa passada e não ajuda
    ninguém. O corte é a data de hoje, no fuso de São Paulo.
    """
    onde, args = [], []
    onde.append("substr(e.data_hora,1,10) >= date('now','localtime')")
    onde.append("e.status IN (" + ",".join("?" * len(STATUS_SINCRONIZA)) + ")")
    args += list(STATUS_SINCRONIZA)
    if pessoa_id:
        onde.append("e.responsavel_id = ?")
        args.append(pessoa_id)
    else:
        onde.append("e.responsavel_id IS NOT NULL")
    return db.execute(f"""
        SELECT e.id, e.tipo, e.data_hora, e.dia_inteiro, e.local, e.status,
               e.responsavel_id, e.observacao,
               c.nome cliente, c.id cliente_id, p.codigo processo, p.id processo_id,
               ps.nome quem
        FROM eventos e
        JOIN clientes c ON c.id = e.cliente_id
        LEFT JOIN processos p ON p.id = e.processo_id
        LEFT JOIN pessoas ps ON ps.id = e.responsavel_id
        WHERE {' AND '.join(onde)}
        ORDER BY e.data_hora""", args).fetchall()


def montar(e):
    """O evento como o Google vai receber.

    O corpo leva o link de volta para o sistema: quem abre o compromisso no
    celular e precisa do contexto chega na ficha com um toque, em vez de
    procurar o nome depois.
    """
    titulo = TITULO.get(e["tipo"], (e["tipo"] or "").replace("_", " ").title())
    alvo = (f"{BASE}/processo/{e['processo_id']}" if e["processo_id"]
            else f"{BASE}/cliente/{e['cliente_id']}")
    linhas = [f"{titulo} — {e['cliente']}", ""]
    if e["processo"]:
        linhas.append(f"Processo {e['processo']}")
    if e["local"]:
        linhas.append(f"Local: {e['local']}")
    if e["observacao"]:
        linhas.append(str(e["observacao"]))
    linhas += ["", f"Abrir no sistema: {alvo}", "",
               "Criado pelo sistema da GGV Prev. Mudança feita aqui NÃO volta para o "
               "escritório — para remarcar, use o sistema."]
    corpo = dict(
        summary=f"{titulo} · {e['cliente']}",
        description="\n".join(linhas),
        location=e["local"] or None,
        # a pessoa não deve poder convidar nem editar: a fonte é o sistema
        guestsCanModify=False, guestsCanInviteOthers=False,
        # a chave de idempotência: o mesmo evento do sistema sempre atualiza o
        # mesmo evento do Google, em vez de criar um segundo a cada rodada
        extendedProperties=dict(private=dict(ggv_evento=str(e["id"]))),
    )
    dia = (e["data_hora"] or "")[:10]
    if e["dia_inteiro"]:
        corpo["start"] = dict(date=dia)
        corpo["end"] = dict(date=dia)
    else:
        hora = (e["data_hora"] or "")[11:19] or "09:00:00"
        corpo["start"] = dict(dateTime=f"{dia}T{hora}", timeZone="America/Sao_Paulo")
        corpo["end"] = dict(dateTime=f"{dia}T{hora}", timeZone="America/Sao_Paulo")
    return corpo


def a_remover(db, pessoa_id=None):
    """Cancelado sai do calendário. Ficar lá é pior que nunca ter entrado:
    a pessoa se organiza para um compromisso que não existe mais."""
    args = list(("CANCELADO",))
    onde = "e.status='CANCELADO' AND substr(e.data_hora,1,10) >= date('now','localtime')"
    if pessoa_id:
        onde += " AND e.responsavel_id=?"
        args.append(pessoa_id)
    return db.execute(f"SELECT e.id, e.data_hora FROM eventos e WHERE {onde}",
                      args[1:] if not pessoa_id else args[1:]).fetchall()


def sincronizar(db, enviar=False, pessoa_id=None):
    """Devolve o que foi (ou seria) enviado, por pessoa."""
    import execucao
    cred = credenciais()
    gente = conectados(db)
    saida = dict(credencial=bool(cred), conectados=len(gente), por_pessoa=[], enviados=0)

    if pessoa_id:
        gente = [g for g in gente if g["pessoa_id"] == pessoa_id]

    for g in gente:
        eventos = a_enviar(db, g["pessoa_id"])
        remover = a_remover(db, g["pessoa_id"])
        saida["por_pessoa"].append(dict(pessoa=g["nome"], email=g["email"],
                                        eventos=len(eventos), remover=len(remover)))
        if not enviar:
            continue
        if not cred:
            continue
        try:
            _enviar_de_verdade(db, g, eventos, remover, cred)
            db.execute("""UPDATE usuarios SET google_sync_em=datetime('now','localtime'),
                            google_sync_erro=NULL WHERE id=?""", (g["id"],))
            saida["enviados"] += len(eventos)
        except Exception as ex:
            motivo = f"{type(ex).__name__}: {ex}"[:400]
            db.rollback()
            db.execute("""UPDATE usuarios SET google_sync_erro=?,
                            google_sync_em=datetime('now','localtime') WHERE id=?""",
                       (motivo, g["id"]))
            # token vencido é problema DA PESSOA, e ela precisa saber: vira
            # tarefa para ela mesma, e não um erro em log que ninguém lê
            if "invalid_grant" in motivo or "401" in motivo:
                db.execute("""INSERT INTO tarefas (titulo, detalhe, tipo, grupo,
                                responsavel_id, prioridade, status, origem)
                              VALUES (?,?, 'CONTATO', ?, ?, 'NORMAL', 'ABERTA', 'SISTEMA')""",
                           ("Reconectar a Google Agenda",
                            "A autorização da sua agenda venceu e os compromissos pararam de "
                            "chegar ao seu telefone. Reconecte em Perfil → Conectar Google Agenda.",
                            None, g["pessoa_id"]))
        db.commit()

    if enviar:
        with execucao.registrar("AGENDA_GOOGLE", db=db) as ex_:
            ex_.itens = saida["enviados"]
            ex_.detalhe = f"{len(gente)} pessoa(s) conectada(s)"
    return saida


def _enviar_de_verdade(db, usuario, eventos, remover, cred):
    """A chamada à Calendar API. Só roda quando há credencial E token."""
    import urllib.request
    import cofre as C
    ref = usuario["google_token_ref"]
    refresh = C.Cofre().abrir(ref, quem=usuario["email"], motivo="sincronizar agenda")
    if not refresh:
        raise RuntimeError("token de atualização não está no cofre")

    # 1. troca o refresh token por um de acesso, que dura uma hora
    import urllib.parse
    dados = urllib.parse.urlencode(dict(
        client_id=cred["client_id"], client_secret=cred["client_secret"],
        refresh_token=refresh, grant_type="refresh_token")).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=dados)
    with urllib.request.urlopen(req, timeout=30) as r:
        acesso = json.loads(r.read())["access_token"]

    cab = {"Authorization": f"Bearer {acesso}", "Content-Type": "application/json"}
    api = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

    for e in eventos:
        corpo = montar(e)
        # id determinístico: o mesmo evento do sistema é sempre o mesmo do
        # Google. Sem isso, cada rodada criaria uma cópia nova.
        gid = f"ggv{e['id']}"
        corpo["id"] = gid
        try:
            req = urllib.request.Request(f"{api}/{gid}", data=json.dumps(corpo).encode(),
                                         headers=cab, method="PUT")
            urllib.request.urlopen(req, timeout=30)
        except Exception:
            req = urllib.request.Request(api, data=json.dumps(corpo).encode(),
                                         headers=cab, method="POST")
            urllib.request.urlopen(req, timeout=30)

    for e in remover:
        try:
            req = urllib.request.Request(f"{api}/ggv{e['id']}", headers=cab, method="DELETE")
            urllib.request.urlopen(req, timeout=30)
        except Exception:
            pass          # já não estava lá; remover o que não existe não é erro


if __name__ == "__main__":
    db = banco.conectar()
    pid = None
    if "--pessoa" in sys.argv:
        pid = int(sys.argv[sys.argv.index("--pessoa") + 1])
    enviar = "--enviar" in sys.argv
    r = sincronizar(db, enviar=enviar, pessoa_id=pid)

    if not r["credencial"]:
        print("✗ sem credencial do Google no Keychain (serviço 'google-agenda').")
        print("  O que falta está em docs/agenda-google.md — precisa de um projeto no")
        print("  Google Cloud, e só o Lucas pode criar.\n")
    print(f"{r['conectados']} pessoa(s) com a agenda conectada")
    for p in r["por_pessoa"]:
        print(f"   {p['pessoa'][:30]:32} {p['eventos']:>4} evento(s)"
              + (f" · {p['remover']} a remover" if p["remover"] else ""))

    # o quadro geral, que é o que mais interessa hoje
    total = db.execute(f"""SELECT count(*) FROM eventos e
        WHERE substr(e.data_hora,1,10) >= date('now','localtime')
          AND e.status IN ({','.join('?' * len(STATUS_SINCRONIZA))})""",
        STATUS_SINCRONIZA).fetchone()[0]
    com_dono = db.execute(f"""SELECT count(*) FROM eventos e
        WHERE substr(e.data_hora,1,10) >= date('now','localtime')
          AND e.status IN ({','.join('?' * len(STATUS_SINCRONIZA))})
          AND e.responsavel_id IS NOT NULL""", STATUS_SINCRONIZA).fetchone()[0]
    print(f"\n{total} compromisso(s) futuro(s) no sistema · {com_dono} com responsável")
    if com_dono < total:
        print(f"   {total - com_dono} não têm dono e por isso NÃO sincronizam com ninguém.")
        print("   Vieram da migração, que não trazia esse campo. Ver docs/agenda-google.md.")
    if not enviar:
        print("\n(nada enviado — rode com --enviar)")
    db.close()
