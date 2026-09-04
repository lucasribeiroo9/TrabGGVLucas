# Como migrar — do Airtable para o Supabase, passo a passo

Este arquivo é para ser seguido de cima para baixo, no **Mac do escritório**.
Não dá para fazer de uma sessão do Claude Code na web: a política de rede de lá
bloqueia `api.airtable.com` e o Postgres do Supabase (403 no CONNECT, testado em
04/09/2026). O esquema subiu de lá porque o conector MCP roda fora daquela
máquina; o **dado** precisa de uma máquina que alcance os dois.

Tempo: **cerca de cinco minutos**, quase todo em espera.

---

## Antes: as duas chaves

A migração precisa de dois segredos, e é o único momento em que os dois são
usados juntos.

| segredo | o que é | onde achar |
|---|---|---|
| `airtable-trab` | token de **leitura** da BASE GGV - TRAB V3 | airtable.com → conta → *Builder hub* → *Personal access tokens* |
| `supabase-trab` | a URI do Postgres do projeto PrevGGVLucas | Supabase → projeto → *Connect* → *Session pooler* |

**O token do Airtable tem de ser só de leitura.** É regra da casa: `data.records:read`
e `schema.bases:read`, escopo na base `appMFTjWGygZ4ob5T`, e nada além disso. O
escritório trabalha nessa base todo dia; um token com escrita transforma um erro
de digitação num estrago.

Guardar os dois no Keychain (o valor não aparece na tela nem fica no histórico):

```bash
security add-generic-password -a "$USER" -s airtable-trab -w -U
security add-generic-password -a "$USER" -s supabase-trab -w -U
```

Cada comando pede o valor e não o mostra. Conferir sem revelar nada:

```bash
cd ~/TrabGGVLucas
./.venv/bin/python chaves.py
```

Ele responde o que está configurado e o que falta.

---

## Passo 0 — o repositório atualizado e as dependências

```bash
cd ~/TrabGGVLucas
git pull
python3 -m venv .venv                       # só na primeira vez
./.venv/bin/pip install -r requirements.txt
```

O `pip install` importa: `requests` entrou no `requirements.txt` só agora, e
`migrar.py --baixar` morre sem ele.

---

## Passo 1 — a cópia do previdenciário, antes de escrever

`migrar.py --recriar` apaga o esquema `public` do Supabase e o refaz. Ele **não
toca** em `prev_2026_09` (a cópia congelada do previdenciário) nem no esquema
`juridico` — mas a regra do `CLAUDE.md` é ter a cópia externa antes de escrever,
e ela ainda não existe.

```bash
pg_dump "$(security find-generic-password -a "$USER" -s supabase-trab -w)" \
        -n prev_2026_09 -Fc -f ~/prev_2026_09_$(date +%F).dump
ls -lh ~/prev_2026_09_*.dump
```

São 69 tabelas e ~123 mil linhas; espere alguns minutos e um arquivo de dezenas
de MB. **Se o arquivo sair com poucos KB, pare e me chame** — dump vazio é o tipo
de rede de segurança que só falha quando é preciso.

---

## Passo 2 — baixar a base

```bash
./.venv/bin/python migrar.py --baixar
```

Só GET: nenhuma chamada deste comando escreve no Airtable. Ele grava
`dados/*.json` e imprime uma linha por tabela. A saída esperada:

```
pre_processual              797 registros
processual                 2652 registros
copia                      3722 registros
pos_processual              556 registros
funcionarios                 72 registros
testemunhas                 424 registros
empresas                   1103 registros
faltantes                  1067 registros
auditoria_testemunhas         2 registros
fragilidades                 17 registros
```

**Se aparecer `⚠ esperava N`, não é erro** — é a base tendo crescido ou
encolhido desde 03/09/2026. Anote o número novo e siga; a conferência do passo 4
recalcula tudo da origem e vai bater com o que veio.

> Este passo é o único do roteiro que **nunca rodou contra a base real**: a
> primeira carga veio pelo conector MCP, sem token. O código é um GET paginado
> simples e respeita o limite de 5 requisições por segundo, mas se ele falhar,
> me mande a mensagem inteira.

---

## Passo 3 — a carga

```bash
./.venv/bin/python migrar.py --recriar
```

`--recriar` derruba o `public`, aplica `esquema.sql` e `governanca.sql`, liga as
chaves estrangeiras adiadas, religa a RLS e carrega. As contas de acesso
sobrevivem: são lidas antes de o esquema cair e devolvidas com o mesmo id, o
mesmo hash de senha e o mesmo papel.

Ao terminar, ele imprime uma tabela de contagens. Os números da última carga real:

```
clientes  3.067   ·  processos  3.855  ·  decisoes  3.668  ·  audiencias 3.035
recursos  2.470   ·  recebimentos 2.428 ·  pendencias 4.530 ·  conferencias 4.342
historico_etapas 10.183
```

**Atenção a uma armadilha:** `migrar.py` lê a ligação de `GGV_SUPABASE_TRAB` e
**ignora `GGV_DSN`**, ao contrário do `banco.py` e do `rodar.sh`. Quem exporta
`GGV_DSN` para trabalhar contra um banco local e roda `migrar.py --recriar` sem
`--dsn` está mirando **a produção**. Para carregar um banco de teste, passe
`--dsn` explícito.

---

## Passo 4 — a prova

```bash
./.venv/bin/python conferir.py
```

São 249 verificações que **recalculam da origem** e comparam com o que entrou:
contagem por tabela, contagem por opção de select, soma de cada campo em reais
ao centavo, cada ligação do Airtable, integridade e dez linhas que têm de dar
zero ("nada inventado").

A última linha tem de ser **`TUDO CONFERE`**. Se não for, **não siga** — a saída
diz exatamente qual verificação falhou e com quais números. Me mande essa parte.

---

## Passo 5 — o que a carga não traz

Três coisas nascem depois, porque não vêm do Airtable:

```bash
# o organograma que você preencheu (setor e chefia de cada pessoa)
./.venv/bin/python equipe_setores.py dados_iniciais/equipe.csv \
        --aplicar --quem glauco@ggvadvocacia.com.br

# a reclamada de cada processo, no eixo novo
./.venv/bin/python empresa_eixo.py --sincronizar

# os acessos de quem ainda não tem — a senha aparece UMA vez
./.venv/bin/python auth.py equipe
```

`auth.py equipe` imprime uma tabela com pessoa, e-mail, perfil e senha
provisória. **Anote e entregue**; ela não fica guardada em lugar nenhum, e na
primeira entrada o sistema obriga a trocar. A conta do Glauco já existe.

---

## Passo 6 — subir o portal

```bash
export GGV_SEGREDO=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
./rodar.sh
```

→ **http://127.0.0.1:8771**

Para o portal subir sozinho no boot e se reerguer se cair, veja `INSTALACAO.md`.

Conferir que ele está falando com o banco certo:

```bash
curl -s http://127.0.0.1:8771/saude
# {"ok":true,"processos":3855}
```

Se `processos` vier 0, o portal subiu contra outro banco — quase sempre um
`GGV_DSN` esquecido no ambiente.

---

## Quando alguma coisa der errado

| o que aparece | o que é |
|---|---|
| `ModuleNotFoundError: requests` | faltou o `pip install -r requirements.txt` do passo 0 |
| `falta GGV_AIRTABLE_TRAB` | o token não está no Keychain com o nome `airtable-trab` |
| `✗ sem a ligação do Postgres` | idem para `supabase-trab`. `chaves.py` diz o que falta |
| `401` ou `403` do Airtable | token vencido, ou sem escopo naquela base |
| `connection timeout` no Supabase | está usando a URI direta (`db.<projeto>.supabase.co`, só IPv6). Use a do **pooler** |
| `conferir.py` não diz TUDO CONFERE | pare. A saída nomeia a verificação e os dois números |
| o portal sobe e mostra tudo zerado | subiu contra outro banco — confira `GGV_DSN` no ambiente |

**Nada disso é irreversível enquanto o passo 1 estiver feito.** `--recriar`
apaga só o `public`, e a carga inteira roda de novo em minutos.
