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

# O segredo do cookie de sessão. Sem ele o Starlette usaria o valor de
# desenvolvimento e uma sessão assinada aqui valeria em qualquer instalação.
if [ -z "${GGV_SEGREDO:-}" ]; then
  echo "aviso: GGV_SEGREDO não definido — a sessão está assinada com a chave de teste."
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
