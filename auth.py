#!/usr/bin/env python3
"""Usuários, senha e permissão. Toda restrição é conferida no servidor.

Vem do `auth.py` do Prev. O que mudou, e por quê (docs/portal-adaptacoes.md):

  · **Os papéis são três**, não cinco: `usuarios.papel` tem CHECK
    ('ADVOGADO','GESTOR','DIRECAO') no esquema.sql daqui, e é esse mesmo
    vocabulário que `fluxo_transicoes.papel` cobra. Inventar um quarto papel
    na tela faria a tela oferecer o que o banco recusa.
  · **A conta não guarda o nome.** `usuarios` aqui é (pessoa_id, email,
    senha_hash, papel, ativo, trocar_senha) — o nome vem de `pessoas`, que é
    a tabela dos funcionários migrados. Nome escrito em dois lugares diverge
    no primeiro dia em que alguém casa.
  · **O setor é `pessoas.setor`** e vale ao lado do papel: quem é da Direção vê
    o escritório inteiro seja qual for o papel escrito na conta.

A senha nasce provisória e é mostrada UMA vez:

    python3 auth.py equipe          # abre acesso para quem ainda não tem
"""
import hashlib
import secrets
import sys

import banco

PERFIS = {
    "DIRECAO":  "Direção: vê tudo, reabre processo encerrado e dá caso por perdido",
    "GESTOR":   "Gestão: aprova a inicial, registra prazo perdido, reabre registro errado",
    "ADVOGADO": "Advogado: move o processo, distribui, registra sentença, trânsito e acordo",
}

# Hierarquia dos papéis. É a mesma que `fluxo.py` usa para ler
# `fluxo_transicoes.papel`: quem é DIRECAO pode o que o GESTOR pode.
HIERARQUIA = {"DIRECAO": 3, "GESTOR": 2, "ADVOGADO": 1}

# ---------------------------------------------------------------------------
# O que cada um vê. Uma chave por tela, não por grupo de telas: no Prev
# "equipe" cobria a ficha de RH E as tarefas, e tirar a aba Equipe de alguém
# tirava junto o trabalho dele.
BASE = {"meu_dia", "tarefas", "perfil"}

# o caso, do lead ao arquivamento
DO_CASO = {"clientes", "processos", "audiencias", "prazos", "empresas",
           "testemunhas", "conferencias", "publicacoes"}

# olhar de gestão: o escritório inteiro, a equipe e o mapa de etapas
GESTAO = {"painel", "equipe", "fluxos"}

TELAS = {
    "DIRECAO":  BASE | DO_CASO | GESTAO,
    "GESTOR":   BASE | DO_CASO | GESTAO,
    "ADVOGADO": BASE | DO_CASO,
}


def telas_de(papel, setor=None):
    """Quem é da Direção vê tudo, seja qual for o papel escrito na conta."""
    if setor == "Direção":
        return TELAS["DIRECAO"]
    return TELAS.get(papel, set())


def pode(papel, exigido):
    """O papel de quem está logado alcança o papel que a ação exige?"""
    if not exigido:
        return True
    return HIERARQUIA.get(papel, 0) >= HIERARQUIA.get(exigido, 9)


# ------------------------------------------------------------------ senha
def cifrar(senha, sal=None):
    sal = sal or secrets.token_hex(16)
    h = hashlib.scrypt(senha.encode(), salt=sal.encode(), n=16384, r=8, p=1, dklen=32)
    return f"{sal}${h.hex()}"


def conferir(senha, guardado):
    try:
        sal, _ = guardado.split("$", 1)
    except (ValueError, AttributeError):
        return False
    return secrets.compare_digest(cifrar(senha, sal), guardado)


def trocar(db, usuario_id, senha_atual, nova):
    """Troca a senha de quem está logado. Devolve (ok, recado)."""
    u = db.execute("SELECT senha_hash FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    if not u or not conferir(senha_atual, u[0]):
        return False, "a senha atual não confere"
    if len((nova or "").strip()) < 8:
        return False, "a senha nova precisa de pelo menos 8 caracteres"
    if conferir(nova, u[0]):
        return False, "a senha nova precisa ser diferente da atual"
    db.execute("UPDATE usuarios SET senha_hash=?, trocar_senha=false WHERE id=?",
               (cifrar(nova), usuario_id))
    db.commit()
    return True, "senha trocada"


def autenticar(db, email, senha):
    """Devolve o dicionário da sessão, ou None. O SETOR vem junto: é ele que,
    ao lado do papel, decide o que a pessoa vê."""
    u = db.execute("""SELECT u.id, u.email, u.senha_hash, u.papel, u.ativo,
                             u.trocar_senha, u.pessoa_id,
                             COALESCE(p.nome, u.email) nome, p.setor
                      FROM usuarios u LEFT JOIN pessoas p ON p.id = u.pessoa_id
                      WHERE lower(u.email) = ?""",
                   ((email or "").strip().lower(),)).fetchone()
    if not u or not u["ativo"] or not conferir(senha, u["senha_hash"]):
        return None
    db.execute("UPDATE usuarios SET ultimo_acesso=datetime('now') WHERE id=?", (u["id"],))
    db.commit()
    return {"id": u["id"], "nome": u["nome"], "email": u["email"], "papel": u["papel"],
            "trocar_senha": bool(u["trocar_senha"]), "setor": u["setor"],
            "pessoa_id": u["pessoa_id"]}


# ------------------------------------------------------- abrir acesso
def _ascii(s):
    """"Nathália" → "nathalia". O e-mail é identificador de entrada e tem de
    ser digitável em qualquer teclado."""
    import re
    import unicodedata
    limpo = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", limpo)


def _papel_de(db, pessoa_id, setor):
    """O papel da conta sai dos PAPÉIS da pessoa (`pessoa_papeis`) e do setor.

    A base de origem não tem nível de acesso: tem FUNCOES (multipleSelects).
    CEO e quem é da Direção entram como DIRECAO; GESTOR entra como GESTOR; o
    resto entra como ADVOGADO, que é o piso — nenhum papel abaixo dele existe
    no CHECK do esquema.
    """
    papeis = {r[0] for r in db.execute(
        "SELECT papel FROM pessoa_papeis WHERE pessoa_id=?", (pessoa_id,))}
    if "CEO" in papeis or setor == "Direção":
        return "DIRECAO"
    if "GESTOR" in papeis:
        return "GESTOR"
    return "ADVOGADO"


def criar_para_equipe(db, dominio="ggvadvocacia.com.br"):
    """Abre acesso para quem trabalha no escritório e ainda não tem login.

    O e-mail é o identificador de entrada, não precisa ser caixa postal de
    verdade. [CONFIRMAR: o domínio de e-mail do escritório trabalhista.]
    A senha sai provisória: na primeira entrada o sistema obriga a trocar.
    """
    novos = []
    for r in db.execute("""SELECT id, nome, setor FROM pessoas
                           WHERE ativo = true ORDER BY nome""").fetchall():
        primeiro = _ascii((r["nome"] or "").split(" ")[0])
        if not primeiro.isalnum():
            continue
        if db.execute("SELECT 1 FROM usuarios WHERE pessoa_id=?", (r["id"],)).fetchone():
            continue
        # Dois "Marcelo" no escritório dão o mesmo e-mail, e o segundo era
        # PULADO em silêncio — a pessoa simplesmente ficava sem acesso e
        # ninguém percebia. Quando o primeiro nome já está tomado, entra o
        # sobrenome; se ainda colidir, um número. Ninguém fica de fora.
        sobrenomes = [_ascii(x) for x in (r["nome"] or "").split(" ")[1:] if len(x) > 2]
        candidatos = [primeiro] + [f"{primeiro}.{s}" for s in sobrenomes] + \
                     [f"{primeiro}{n}" for n in range(2, 40)]
        email = None
        for c in candidatos:
            tentativa = f"{c}@{dominio}"
            if not db.execute("SELECT 1 FROM usuarios WHERE email=?", (tentativa,)).fetchone():
                email = tentativa
                break
        if not email:
            continue
        senha = secrets.token_urlsafe(9)
        papel = _papel_de(db, r["id"], r["setor"])
        db.execute("""INSERT INTO usuarios (pessoa_id, email, senha_hash, papel, trocar_senha)
                      VALUES (?,?,?,?, true)""", (r["id"], email, cifrar(senha), papel))
        novos.append((r["nome"], email, papel, senha))
    db.commit()
    return novos


if __name__ == "__main__":
    db = banco.conectar()
    if "equipe" in sys.argv:
        novos = criar_para_equipe(db)
        if not novos:
            print("todo mundo do escritório já tem acesso.")
        else:
            print(f"\n{len(novos)} acesso(s) criado(s). A senha aparece UMA vez — "
                  f"anote e entregue:\n")
            # A largura sai do CONTEÚDO, não de um número escolhido a olho: com
            # colunas fixas de 34, e-mail de 34 caracteres ou mais saía colado
            # no papel (`…com.brADVOGADO`) e duas contas boas pareciam
            # recusadas na leitura. Quem entrega senha lê esta tabela uma vez e
            # não pode ficar em dúvida sobre onde acaba o e-mail.
            larg = lambda titulo, i: max(len(titulo), *(len(str(l[i])) for l in novos)) + 2
            w_n, w_e, w_p = larg("pessoa", 0), larg("entra com", 1), larg("perfil", 2)
            print(f"{'pessoa':<{w_n}}{'entra com':<{w_e}}{'perfil':<{w_p}}senha provisória")
            print("-" * (w_n + w_e + w_p + 20))
            for nome, email, papel, senha in novos:
                print(f"{nome:<{w_n}}{email:<{w_e}}{papel:<{w_p}}{senha}")
            print("\nNa primeira entrada o sistema obriga a trocar a senha.")
    else:
        print("uso: python3 auth.py equipe")
    db.close()
