#!/bin/bash
# Sobe o portal em http://127.0.0.1:8771 e mantém rodando em segundo plano.
#
# A porta é 8771 de propósito: 8770 é o sistema previdenciário e 8700 é o
# portal financeiro. Três sistemas na mesma máquina, três portas.
cd "$(dirname "$0")"
./parar.sh >/dev/null 2>&1

# De onde vem a ligação com o banco, na ordem em que se procura:
#   1. o primeiro argumento, se parecer uma URI de Postgres
#   2. GGV_DSN (é o que o modo de prova usa)
#   3. GGV_SUPABASE_TRAB, no servidor
#   4. o Keychain do Mac, na chave `supabase-trab`  (chaves.py)
if [ -n "${1:-}" ] && [[ "$1" == postgres* ]]; then
  export GGV_DSN="$1"
fi
if [ -n "${GGV_DSN:-}" ]; then
  echo "banco: $(echo "$GGV_DSN" | sed 's#://[^@]*@#://***@#')"
else
  echo "banco: o que chaves.py achar em GGV_SUPABASE_TRAB ou no Keychain (supabase-trab)"
fi

# O segredo que assina o cookie de sessão. NÃO há valor de reserva: `app.py`
# recusa subir sem ele, de propósito. Segredo fixo escrito no repositório
# valeria em toda instalação e deixaria forjar sessão — e é do cookie que o
# portal tira quem é quem e qual é o papel. Aqui se para antes, para o recado
# aparecer no terminal em vez de no fim do servidor.log.
if [ -z "${GGV_SEGREDO:-}" ]; then
  cat <<'FIM'
✗ GGV_SEGREDO não definido — o portal não sobe sem ele.

  Gere um (48 bytes, base64 url-safe):

      export GGV_SEGREDO=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
      ./rodar.sh

  Para não gerar um novo a cada vez, guarde no Keychain do Mac (ou no gestor de
  segredos do servidor). Trocar o segredo derruba as sessões abertas — quem
  estava dentro só precisa entrar de novo:

      security add-generic-password -a "$USER" -s ggv-trab-segredo -w "$GGV_SEGREDO" -U
      export GGV_SEGREDO=$(security find-generic-password -a "$USER" -s ggv-trab-segredo -w)
FIM
  exit 1
fi

PY=./.venv/bin/python
[ -x "$PY" ] || PY=$(command -v python3)
UVICORN=./.venv/bin/uvicorn
[ -x "$UVICORN" ] || UVICORN="$PY -m uvicorn"

nohup $UVICORN app:app --host 127.0.0.1 --port 8771 > servidor.log 2>&1 &
echo $! > servidor.pid
sleep 2
if curl -sf -o /dev/null http://127.0.0.1:8771/entrar; then
  echo "✓ no ar em http://127.0.0.1:8771  (pid $(cat servidor.pid))"
  echo "  para parar:  ./parar.sh"
else
  echo "✗ não subiu. Veja servidor.log:"; tail -20 servidor.log
  exit 1
fi
