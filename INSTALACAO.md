# Pôr o portal trabalhista no ar

Dois destinos, e eles não competem: o **Mac do escritório** é onde o sistema
vive (como o previdenciário vive hoje), e o **Fly** é para quando alguém
precisar abrir o portal de fora da rede do escritório.

O `Dockerfile` serve aos dois — no Mac ele é opcional, no Fly é o caminho.

---

## Antes de qualquer coisa: o banco precisa ter dado

O portal não cria ficha: ele lê e move. Quem enche o banco é a migração, e ela
roda de uma máquina que alcance **o Airtable e o Postgres do Supabase** — hoje,
o Mac do escritório. Sem este passo o portal sobe e mostra tudo zerado.

```bash
# 1. a cópia externa do previdenciário congelado, ANTES de escrever (regra do CLAUDE.md)
pg_dump "$(security find-generic-password -a "$USER" -s supabase-trab -w)" \
        -n prev_2026_09 -Fc -f ~/prev_2026_09_$(date +%F).dump

# 2. a carga: apaga o `public` e refaz esquema + governança + dado
./.venv/bin/python migrar.py --recriar

# 3. a prova. Só passa com TUDO CONFERE
./.venv/bin/python conferir.py

# 4. o organograma que o Lucas preencheu (ver dados_iniciais/LEIA-ME.md)
./.venv/bin/python equipe_setores.py dados_iniciais/equipe.csv \
       --aplicar --quem glauco@ggvadvocacia.com.br
```

**`migrar.py` lê a URI de `GGV_SUPABASE_TRAB`, não de `GGV_DSN`.** Isso importa:
quem exporta `GGV_DSN` para trabalhar contra um banco local — como o `rodar.sh`
e `docs/portal-prova.md` fazem — e depois roda `migrar.py` sem `--dsn` está
mirando **a produção**, e `--recriar` derruba o `public` de lá. Para carregar um
banco de teste, passe `--dsn` explícito.

---

## Destino 1 — o Mac do escritório, 24 horas

É o padrão do previdenciário: a máquina não dorme, o portal sobe no boot e o
launchd o reergue se ele cair.

### 1. Preparar a máquina

```bash
sudo zsh implantar/preparar_mac.sh
```

Ajusta energia (não dormir, voltar após queda de luz), liga o SSH e dá nome à
máquina na rede. Pede senha de administrador porque são ajustes do sistema.

Duas coisas o script não faz, porque não há como por linha de comando:

- **Ajustes › Usuários › Opções de início**: ligar o início automático de sessão.
  Só faz sentido com o FileVault **desligado** — com ele ligado, um reinício por
  queda de luz para na tela de senha do disco e o portal não sobe sozinho. É uma
  troca consciente: o disco fica sem cifra, e a máquina precisa estar fisicamente
  segura.
- **Ajustes › Geral › Compartilhamento**: ligar o Compartilhamento de Tela, para
  manutenção sem ir até a máquina.

### 2. Instalar o projeto

```bash
cd ~ && git clone https://github.com/lucasribeiroo9/TrabGGVLucas.git
cd TrabGGVLucas
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

### 3. Guardar os segredos no Keychain

```bash
# a ligação com o Postgres do Supabase (a URI inteira, ou só a senha)
security add-generic-password -a "$USER" -s supabase-trab -w 'postgresql://...' -U

# confere o que está configurado, sem mostrar valor nenhum
./.venv/bin/python chaves.py
```

`chaves.py` sozinho responde "o que falta configurar". O que o portal exige é
`supabase-trab`; o resto (`anthropic-api`, `airtable-trab`, `zapsign-api`) é
para os módulos que ainda não entraram.

### 4. Subir sozinho no boot

```bash
cp implantar/com.ggvtrab.portal.plist ~/Library/LaunchAgents/
# trocar SEU_USUARIO e TROCAR_POR_UM_SEGREDO_LONGO dentro do arquivo:
python3 -c "import secrets;print(secrets.token_urlsafe(48))"

launchctl load -w ~/Library/LaunchAgents/com.ggvtrab.portal.plist
```

Conferir: `curl -s http://127.0.0.1:8771/saude` → `{"ok":true,"processos":3855}`

### 5. Abrir para a rede do escritório

O plist prende o portal em `127.0.0.1` de propósito: assim ele não aparece na
rede antes de alguém decidir que deve aparecer. Para abrir aos outros
computadores, troque o `--host` para `0.0.0.0` no plist e recarregue:

```bash
launchctl unload ~/Library/LaunchAgents/com.ggvtrab.portal.plist
launchctl load -w ~/Library/LaunchAgents/com.ggvtrab.portal.plist
```

E aí o endereço é `http://ggv-servidor.local:8771` (o nome que o
`preparar_mac.sh` deu à máquina) para quem estiver na mesma rede.

**Isso é rede local, não internet.** Ninguém de fora alcança, e é essa a
proteção — o portal não tem HTTPS próprio.

### 6. As contas

```bash
./.venv/bin/python auth.py equipe
```

Abre acesso a quem está em `pessoas` e ainda não tem login. **A senha aparece
UMA vez**, na tabela que o comando imprime: anote e entregue. Na primeira
entrada o sistema obriga a trocar.

A conta de direção (Glauco) já existe no Supabase desde 04/09/2026 — ver
`docs/supabase-carga.md`. Falta a segunda, do Dr. Vitor.

---

## Destino 2 — o Fly, para acesso de fora

Dá uma URL `https://` de verdade. Duas decisões antes:

1. **O portal passa a ser alcançável da internet**, e ele guarda nome, CPF,
   telefone e processo de gente de verdade. A trava é a senha de cada conta, o
   CSRF e a RLS do banco. Se isso basta ou se falta um segundo fator é decisão
   do escritório, não do código.
2. **O segredo do cookie sai do Keychain** e passa a viver nos *secrets* do Fly.

```bash
fly launch --no-deploy --copy-config       # cria o app a partir do fly.toml

# a URI do POOLER (IPv4). A direta, db.<projeto>.supabase.co, só tem IPv6.
fly secrets set GGV_SUPABASE_TRAB='postgresql://postgres.yzayjwlgjjnoxdxgruss:SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres'
fly secrets set GGV_SEGREDO="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"

fly deploy
fly open                                   # https://ggv-trabalhista.fly.dev
```

Conferir depois do deploy:

```bash
curl -s https://ggv-trabalhista.fly.dev/saude     # {"ok":true,"processos":...}
fly logs
```

### Por que 6543 e não 5432

6543 é o pooler em modo **transação**; 5432 é sessão, e a direta é IPv6. No modo
transação não há sessão entre comandos, então `PREPARE` de um comando não existe
no `EXECUTE` seguinte — `banco.py` já sobe com `prepare_threshold=None` por isso.
E **um worker só** (é o que o `Dockerfile` faz): o pooler do Supabase tem um
disjuntor que bloqueia o projeto inteiro quando vê autenticação demais em pouco
tempo, e ele já disparou uma vez no previdenciário.

### O que NÃO vai para o Fly

`migrar.py`, `conferir.py` e `equipe_setores.py` continuam sendo coisa de quem
tem o Airtable — o container não tem token nem precisa ter. A imagem também não
leva `dados/`, `trabalhista.db` nem `*.log`: está no `.dockerignore`, e é ele
que impede dado de cliente de sair desta máquina dentro de uma imagem.

---

## Quando alguma coisa não sobe

| sintoma | o que é |
|---|---|
| `✗ GGV_SEGREDO não definido` | o portal recusa subir sem ele, de propósito. Gere um e ponha no plist ou nos secrets |
| `✗ sem a ligação do Postgres` | falta `supabase-trab` no Keychain (Mac) ou `GGV_SUPABASE_TRAB` (servidor). `chaves.py` diz o que falta |
| sobe, mas toda tela mostra zero | o banco está com o esquema e sem dado: falta a carga lá em cima |
| `connection timeout` no Fly | está usando a URI direta (IPv6). Troque pela do pooler |
| tela branca ou 500 depois de um `migrar.py` | o poço de conexões ficou com conexão morta; reinicie o portal |
| a porta 8771 não responde | `./parar.sh` mata **só** a 8771 — nunca `pkill -f uvicorn`, que derrubaria o previdenciário na 8770 e o financeiro na 8700 |
