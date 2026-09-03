#!/bin/bash
# Mata SÓ quem estiver na porta 8771.
#
# NUNCA use pkill -f "uvicorn app:app": esse padrão casa também com o sistema
# previdenciário do Lucas (~/ggv-juridico, porta 8770) e com o portal
# financeiro (~/ggv-portal, porta 8700). Derrubar o sistema em que o escritório
# está trabalhando para parar o nosso é o pior desfecho possível.
PORTA=8771
PID=$(lsof -nP -tiTCP:$PORTA -sTCP:LISTEN 2>/dev/null)
if [ -z "$PID" ] && command -v fuser >/dev/null 2>&1; then
  PID=$(fuser -n tcp $PORTA 2>/dev/null | tr -d ' ')
fi
if [ -n "$PID" ]; then
  kill $PID && echo "parado (pid $PID)"
else
  echo "nada rodando na $PORTA"
fi
