#!/usr/bin/env python3
"""Cofre das credenciais gov.br.

A senha do cliente NAO entra no banco do sistema. Fica aqui, cifrada com
Fernet (AES-128-CBC + HMAC), num arquivo separado com permissao 0600, e a
chave vive no Keychain do macOS, nunca no disco em claro.

    from cofre import Cofre
    c = Cofre()
    ref = c.guardar("cliente-42", "senha123")   # devolve a referencia
    c.abrir(ref, quem="lucas", motivo="peticao") # devolve a senha e registra
"""
import os
import sqlite3
import subprocess
import sys

from cryptography.fernet import Fernet

AQUI = os.path.dirname(os.path.abspath(__file__))
CAMINHO = os.path.join(AQUI, "segredos.db")
SERVICO = "ggv-juridico-cofre"


def _chave():
    import chaves
    guardado = chaves.ler(SERVICO)
    if guardado:
        return guardado.encode()
    nova = Fernet.generate_key()
    subprocess.run(["security", "add-generic-password", "-s", SERVICO,
                    "-a", "ggv-juridico", "-U", "-w", nova.decode()],
                   capture_output=True, check=True)
    print(f"✓ chave do cofre criada no Keychain ({SERVICO})", file=sys.stderr)
    return nova


class Cofre:
    def __init__(self):
        self.f = Fernet(_chave())
        novo = not os.path.exists(CAMINHO)
        self.db = sqlite3.connect(CAMINHO)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS segredos (
                ref       TEXT PRIMARY KEY,
                valor     BLOB NOT NULL,
                criado_em TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS aberturas (
                id     INTEGER PRIMARY KEY,
                ref    TEXT NOT NULL,
                quem   TEXT,
                motivo TEXT,
                em     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
        """)
        if novo:
            os.chmod(CAMINHO, 0o600)

    def guardar(self, ref, valor):
        if valor is None or str(valor).strip() == "":
            return None
        self.db.execute("INSERT OR REPLACE INTO segredos(ref, valor) VALUES (?,?)",
                        (ref, self.f.encrypt(str(valor).encode())))
        self.db.commit()
        return ref

    def abrir(self, ref, quem=None, motivo=None):
        r = self.db.execute("SELECT valor FROM segredos WHERE ref = ?", (ref,)).fetchone()
        if not r:
            return None
        self.db.execute("INSERT INTO aberturas(ref, quem, motivo) VALUES (?,?,?)",
                        (ref, quem, motivo))
        self.db.commit()
        return self.f.decrypt(r[0]).decode()

    def total(self):
        return self.db.execute("SELECT COUNT(*) FROM segredos").fetchone()[0]


if __name__ == "__main__":
    c = Cofre()
    print(f"cofre em {CAMINHO} · {c.total()} segredo(s) · permissão {oct(os.stat(CAMINHO).st_mode)[-3:]}")
