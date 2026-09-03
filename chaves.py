#!/usr/bin/env python3
"""De onde vem cada segredo — Keychain no Mac, variável de ambiente no servidor.

O sistema nasceu num Mac e lia tudo do Keychain (`security find-generic-password`).
Isso não existe em Linux, e o sistema simplesmente morria ao subir: sem a ligação
do Supabase, `banco.py` chamava `sys.exit`.

A ordem aqui é **ambiente primeiro**. Não é detalhe: no servidor o Keychain nem
existe, e no Mac o ambiente só está preenchido quando alguém preencheu de
propósito — o que é justamente o caso de quem está testando o modo servidor sem
querer mexer no Keychain de verdade.

O nome do segredo vira o nome da variável de forma previsível, para não haver
uma tabela de-para que alguém esquece de atualizar:

    supabase-prev   →  GGV_SUPABASE_PREV
    anthropic-api   →  GGV_ANTHROPIC_API

    ./.venv/bin/python chaves.py      # o que está disponível, sem mostrar valor
"""
import os
import subprocess

# O que o sistema precisa, e para quê. Serve de checklist na hora de subir:
# `chaves.py` sozinho responde "o que falta configurar".
SEGREDOS = {
    "supabase-trab":       "ligação com o Postgres do trabalhista (a fonte de dados)",
    "anthropic-api":       "parecer da IA e o chat de operação",
    "airtable-trab":       "leitura da BASE GGV - TRAB V3 (somente leitura)",
    "zapsign-api":         "documentos assinados (o contrato que destrava LEAD → DOCUMENTAÇÃO)",
    "ggv-trab-cofre":      "chave do cofre (ainda sem uso no trabalhista)",
    "google-agenda":       "OAuth da agenda (ainda não criado)",
    "mistral-api":         "OCR fora do Mac (ainda não criado)",
    "ggv-backup":          "cifra do backup",
}


def variavel(nome):
    """'supabase-prev' → 'GGV_SUPABASE_PREV'; 'ggv-backup' → 'GGV_BACKUP'.

    O prefixo não se repete: 'GGV_GGV_BACKUP' é o tipo de nome que alguém
    digita errado às três da manhã.
    """
    limpo = nome[4:] if nome.startswith("ggv-") else nome
    return "GGV_" + limpo.upper().replace("-", "_")


def ler(nome, obrigatorio=False):
    """O valor do segredo, ou "" se não houver em lugar nenhum.

    Nunca levanta por falta de Keychain: em Linux o comando não existe, e o
    erro certo é "não configurado", não "sistema quebrado".
    """
    v = (os.environ.get(variavel(nome)) or "").strip()
    if v:
        return v
    try:
        v = subprocess.run(["security", "find-generic-password", "-s", nome, "-w"],
                           capture_output=True, text=True, timeout=10).stdout.strip()
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        v = ""          # não é Mac, ou o Keychain está trancado
    if not v and obrigatorio:
        raise RuntimeError(
            f"segredo '{nome}' não configurado. No Mac: tk {nome}. "
            f"No servidor: variável {variavel(nome)}.")
    return v


def no_servidor():
    """True quando não há Keychain — ou seja, quando não estamos no Mac.

    Vale para decidir o que NÃO tentar: OCR pelo Vision, transcrição pelo mlx,
    leitura da pasta local do Drive. São coisas que só existem naquela máquina,
    e tentar mesmo assim dá erro obscuro em vez de aviso claro.
    """
    if os.environ.get("GGV_SERVIDOR") == "1":
        return True
    try:
        subprocess.run(["security", "-h"], capture_output=True, timeout=5)
        return False
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return True


def conferir():
    """O que está e o que falta — sem mostrar valor nenhum."""
    saida = []
    for nome, para_que in SEGREDOS.items():
        v = ler(nome)
        onde = ("ambiente" if os.environ.get(variavel(nome)) else
                ("Keychain" if v else "—"))
        saida.append(dict(nome=nome, tem=bool(v), onde=onde, para_que=para_que))
    return saida


if __name__ == "__main__":
    print(f"\n{'no servidor' if no_servidor() else 'no Mac'}\n")
    print(f"{'segredo':22}{'onde':12}{'':4}{'para que'}")
    print("-" * 84)
    for s in conferir():
        marca = "ok" if s["tem"] else "FALTA"
        print(f"{s['nome']:22}{s['onde']:12}{marca:7}{s['para_que']}")
    faltam = [s["nome"] for s in conferir() if not s["tem"]]
    print()
    if faltam:
        print("Faltando:", ", ".join(faltam))
        print("No servidor, cada um vira uma variável:",
              ", ".join(variavel(n) for n in faltam))
    else:
        print("Tudo configurado.")
