#  A imagem do PORTAL TRABALHISTA. Só o portal.
#
#  Aqui é mais simples que no Prev: este sistema não tem OCR pelo Vision, nem
#  transcrição pelo mlx, nem leitura da pasta local do Drive — nada que dependa
#  de macOS. O que ele precisa é do Postgres do Supabase e de um segredo para
#  assinar o cookie. Por isso a imagem é pequena e o build não tem etapa nativa.
#
#  slim e não a completa: a diferença é ~700 MB por deploy, e nada do que a
#  imagem completa traz a mais é usado aqui.
FROM python:3.13-slim

#  GGV_SERVIDOR=1 é o que `chaves.no_servidor()` lê para saber que não há
#  Keychain: os segredos vêm de variável de ambiente, e `banco.py` monta a
#  ligação pelo *pooler* (IPv4) em vez da conexão direta, que só tem IPv6.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GGV_SERVIDOR=1

WORKDIR /app

#  As dependências primeiro, em camada própria: mudar código não reinstala
#  nada, e o deploy passa de minutos para segundos. O `requirements.txt` daqui
#  já É o subconjunto web — o Prev precisou de um arquivo à parte, este não.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

#  Não roda como root. Se algum dia uma falha permitir escrever no disco do
#  container, que seja com o mínimo de poder possível.
RUN useradd --create-home --uid 10001 ggv && chown -R ggv:ggv /app
USER ggv

#  A porta vem do hospedeiro. Fixar 8771 aqui quebraria em qualquer serviço
#  que decide a porta em tempo de execução — que é o que quase todos fazem.
ENV PORT=8771
EXPOSE 8771

#  `sh -c` porque $PORT precisa ser expandido; e UM worker, com o poço de
#  conexões do `banco.py` cuidando do resto. Vários workers multiplicariam o
#  número de conexões, e o pooler do Supabase tem um disjuntor que bloqueia o
#  projeto inteiro quando vê autenticação demais em pouco tempo — foi o que
#  derrubou o Prev uma vez.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
