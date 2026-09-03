# Resultado da migração — o que entrou, o que ficou para gente decidir

> 03/09/2026. Escrito pelo DBA de migração. Nenhum nome de cliente, CPF, telefone, e-mail ou
> número de processo aparece aqui.

## Onde a coisa está, em uma frase

**O esquema está aplicado no Supabase e a carga está escrita e provada — mas a carga completa
ainda não rodou**, porque nesta máquina não há o token de leitura do Airtable nem a senha do
Postgres da produção. O caminho inteiro foi provado num Postgres 16 local contra uma amostra
sintética que reproduz todos os casos difíceis da base real, e terminou em **TUDO CONFERE**.
Rodar a carga de verdade é um comando (ver "O que falta", no fim).

## O banco, como está no Supabase agora

Projeto **PrevGGVLucas** (`yzayjwlgjjnoxdxgruss`), esquema `public` — que estava vazio desde que o
Prev foi congelado em `prev_2026_09`. Não se tocou em `prev_2026_09` nem em `juridico`.

| | |
|---|---|
| migrations aplicadas | 4 (`trab_esquema_01` … `trab_esquema_04`) |
| tabelas | 35 |
| visão | 1 (`documentos_pendentes`, sobre `pendencias`) |
| chaves estrangeiras | 88 |
| CHECKs | 229 |
| RLS ligada | 35 de 35, com `FORCE` |
| política do app | `p_app_trab` em 35 de 35 |
| alertas de segurança no `public` | **nenhum** |

Os alertas que o linter do Supabase mostra são todos de `prev_2026_09` (congelado, fora da API) e
de `juridico` — nenhum é do trabalhista.

**A RLS é deny-by-default para a API pública.** Não existe política para `anon` nem para
`authenticated`, e o `GRANT` desses papéis foi revogado: pela API REST do Supabase não se lê nada.
Quem lê e escreve é o sistema, pelo Postgres, com o papel `app_trab`. `ligar_rls()` é função, e
não script solto, para que toda migration futura que criar tabela consiga religá-la numa linha.

## Como a base foi lida: a CÓPIA como base, a PROCESSUAL por cima

A decisão que o Lucas delegou, e a justificativa:

**A base é a CÓPIA DA PROCESSUAL.** Ela tem 3.722 registros contra 2.652 da PROCESSUAL — 1.187
processos a mais, 1.048 deles encerrados, distribuídos sobretudo entre 2017 e 2021. É o passivo
histórico do escritório, que alguém carregou na cópia (e não na PROCESSUAL) para o pipeline de
leitura dos autos enriquecer em 31/08/2026. É lá que estão a data da sentença, o magistrado, o
resultado objetivo do recurso, o CPF, o CNPJ da reclamada, o relator e os honorários por base — e
é lá que a fase está atualizada pela leitura dos autos (68% de encerrados contra 18%). Migrar pela
PROCESSUAL seria começar o sistema sem dois terços do acervo e sem nenhum resultado medido.

**A PROCESSUAL vence campo a campo no que a equipe edita hoje.** Os links vivos com pré-processual,
testemunhas e pós-processual (que a duplicação de tabela transformou em texto na cópia), e os
campos onde ela está preenchida e a cópia não: DATA REVOG (509 só nela), Nº CumPrSe (131), VALOR
HOM (127), SUCUMB RECEBIDO (67), STATUS EXECUÇÃO (59), e os campos do incidente de representação.
A lista está na coluna **vence** de `docs/de-para.md`, campo a campo.

**Os 22 processos só na PROCESSUAL e os 106 sem número entram.** Sem número não há como casar:
entram pela PROCESSUAL, cada um com uma conferência `SEM_NUMERO` aberta.

**Onde as duas discordam, ninguém escolhe em silêncio.** As 1.403 divergências de FASE incluídas.
Nasce linha em `conferencias` com o valor de cada lado, de qual tabela veio cada um, o que a
migração gravou e o trecho de prova. Em nome, vara, nascimento e telefone a grafia perdida ainda
vai para `processo_alias` — jogar fora seria perder o que talvez esteja certo.

## O que vai entrar na carga completa

Os números da origem em 03/09/2026 e para onde vão. O número exato de cada tabela sai do
`conferir.py` depois da carga — aqui está a aritmética, não uma estimativa disfarçada de fato.

| origem | registros | vira |
|---|---|---|
| FUNCIONARIOS | 72 | `pessoas` + `pessoa_papeis` (um papel por linha) |
| EMPRESAS | 1.103 | `empresas` |
| FRAGILIDADES | 17 | `fragilidades` (o banco de teses por reclamada) |
| PRE PROCESSUAL | 797 | `clientes` + `pendencias` + `eventos` + `contatos` + `anotacoes` |
| CÓPIA DA PROCESSUAL | 3.722 | `processos` (menos os 3 `INAPLICÁVEL`) |
| PROCESSUAL | 2.652 | completa os processos; os que não casam entram como processo próprio |
| PÓS PROCESSUAL | 556 | `recebimentos`, `repasses`, `processos.arquivado_em`, `tarefas` |
| TESTEMUNHAS | 424 | `testemunhas` + `testemunha_vinculos` (497 ligações) |
| AUDITORIA TESTEMUNHAS | 2 | `testemunha_auditoria`, como está |
| Conferência de Faltantes | 1.067 | `conferencia_faltantes`, ligada a `processos` quando o CNJ casa |

Contas: os processos são 3.722 da CÓPIA, menos 3 inaplicáveis, mais os registros da PROCESSUAL que
não casaram (os 22 números só dela, os 106 sem número e os 8 duplicados).

**Todo processo tem cliente.** As 797 fichas da pré-processual não cobrem 3.722 processos: para o
resto, a migração casa pelo link vivo da PROCESSUAL, depois pelo CPF dos autos (97% preenchido na
cópia), depois pelo nome quando ele é único no cadastro. O que não é seguro **não vira palpite**:
nasce ficha com `origem_cadastro = 'PROCESSO'` e uma conferência `CLIENTE_AMBIGUO` aberta, porque
cliente errado é pior que cliente novo. Nada de casar por semelhança — no Prev, semelhança casou
*Marina* com *Marize*.

## O que vai para `conferencias`, e por quê

Sete tipos. Cada linha tem o valor de cada lado, o que a migração gravou e o trecho de prova; a
tela de conferências dá dono, situação e anotação, como no Prev.

| tipo | quando nasce |
|---|---|
| `DIVERGENCIA_FONTE` | a CÓPIA e a PROCESSUAL discordam em campo relevante (fase, status, nome, vara, valor, decisão, encerramento, acordo) — as 1.403 de FASE aqui |
| `VALOR_SEM_TRADUCAO` | opção poluída sem tradução óbvia: `SIM `/`NÃO `/`EXECUÇÃO`/`RECURSAL` em STATUS EXECUÇÃO, rescisão em texto que não diz modalidade, TRT que não existe, `2500%` de sucumbência, papel que não está na lista |
| `CNJ_DUPLICADO` | o mesmo número em mais de um registro (8 na PROCESSUAL, 19 na CÓPIA). Cada um vira um processo: perder linha seria pior |
| `SEM_NUMERO` | os 106 da PROCESSUAL sem número — não há como casar |
| `CLIENTE_AMBIGUO` | mais de uma ficha com o mesmo nome e sem CPF que decida |
| `LINK_QUEBRADO` | registro do PÓS PROCESSUAL sem link e sem número que case |
| `FORA_DO_ESCOPO` | os 3 `INAPLICÁVEL` da CÓPIA: não são processos trabalhistas nossos e não viram processo |
| `DATA_ILEGIVEL` | DEMISSAO com telefone, "SIM" ou texto no lugar da data |

A conferência **preserva o trabalho humano**: recarregar não apaga dono, situação nem anotação —
elas voltam recasadas pela `chave`. Está provado em teste.

## O que fica só em `airtable_bruto`, e por quê

`airtable_bruto jsonb` guarda o **registro original inteiro** em toda linha migrada — inclusive o
que já tem coluna própria. Nos processos são os dois lados: `{"copia": {...}, "processual": {...}}`.
Assim "descartado" nunca quer dizer "perdido": quer dizer "sem coluna na tela".

| o que | por que não virou coluna |
|---|---|
| `_BACKUP_VALOR/COMPLEXIDADE/FEITO_EM_SCRIPT` (233/181/233) | backup que um script fez antes de reescrever campos em julho/2026. Dar coluna a um rascunho é dar-lhe status de dado |
| `TESE PRINCIPAL` (0/797) | vazio em 100%: campo que ninguém preencheu não ganha lugar na tela |
| `CADASTRADO POR`, `ÚLTIMA ALTERAÇÃO POR/EM` (0/424) | previstos para o Formulário Interno Único, que ainda não está em uso |
| `origem_comercial_tabela_id` (0/424) | vazio em 100% |
| `MOTIVO` (5 registros nas duas tabelas) | sem função clara; um deles diz "SEM TESTEMUNHA" |
| `PROCESSUAL copy` no PÓS (436) | link legado para a CÓPIA; a ligação útil é a do número CNJ |
| as ~40 opções poluídas sem tradução | ficam no `_original` da coluna e abrem conferência |

Dezesseis das 35 tabelas **não** têm `airtable_bruto`, e é de propósito: `tarefas`, `eventos`,
`contatos`, `acordo_parcelas`, `repasses`, `peticoes`, `anotacoes`, `conferencias`, `auditoria`,
`automacoes`, `usuarios`, `processo_alias`, `pessoa_papeis`, `testemunha_vinculos`,
`automacao_log` e `migracao_execucoes` não vêm de um registro do Airtable — são derivadas dele ou
nascem no sistema. O bruto do registro que as originou está na linha-mãe.

## O que a prova achou (e por que ela existe)

A carga rodou contra um Postgres 16 local com a amostra sintética de `dados_exemplo.py`. Três
defeitos apareceram, e nenhum deles apareceria numa conferência de contagem:

1. **A sequência de identidade ficava para trás.** A carga grava id explícito
   (`OVERRIDING SYSTEM VALUE`) para ser determinística, e isso **não** adianta a sequência. A
   contagem batia, o `conferir.py` dizia TUDO CONFERE — e o **primeiro cadastro feito na tela**
   estouraria com "duplicate key". Quem denunciou foi um gatilho de histórico ao gravar a primeira
   transição de fase. Agora a carga acerta todas as sequências no fim, e o `conferir.py` prova isso.
2. **Cinco tabelas ficavam sem RLS.** O bloco que liga a RLS rodava no fim de `esquema.sql`, e
   `governanca.sql` roda **depois**, criando `fluxos`, `fluxo_etapas`, `fluxo_transicoes`,
   `historico_etapas` e `prazo_tipos`. O mapa de etapas ficaria aberto na API pública. Virou
   função (`ligar_rls()`), chamada de novo no fim da montagem.
3. **CNJ repetido grudava o mesmo registro em duas linhas.** Cada registro da PROCESSUAL agora casa
   com um da CÓPIA e só um; o segundo vira processo próprio com conferência aberta. Sem isso o
   índice único do record de origem derrubava a carga no meio — e derrubar no meio é melhor que
   passar, mas nenhum dos dois é o certo.

Os gatilhos foram testados depois da carga, com a governança religada: transição fora do mapa
recusada, transição do mapa aceita e histórico gravado sozinho, ação depois da prescrição bienal
recusada, prazo em dias corridos sem justificativa recusada. A carga do passivo passa por fora
(gatilhos desligados) e a regra volta inteira no fim — como o `--baixar` do Prev faz.

Recarregar duas vezes seguidas dá o mesmo resultado, e a segunda carga preserva as conferências
já resolvidas. Provado.

## O que falta para rodar a carga completa

Dois segredos e três comandos. Nada mais.

```bash
export GGV_AIRTABLE_TRAB=...      # token de LEITURA da base (o script só faz GET)
export GGV_SUPABASE_TRAB=...      # a ligação com o Postgres do PrevGGVLucas

./.venv/bin/python migrar.py --baixar    # Airtable → dados/*.json
./.venv/bin/python migrar.py --recriar   # esquema + governança + carga
./.venv/bin/python conferir.py           # só passa com TUDO CONFERE
```

`--recriar` apaga o `public` e o refaz de `esquema.sql` + `governanca.sql`. Para carregar sem
mexer no esquema (o caso normal, depois da primeira vez), rode `migrar.py` sem a opção: ele apaga
o que a migração escreve e preserva contas de acesso, automações e conferências resolvidas.

**`governanca.sql` ainda não foi aplicada no Supabase.** É o arquivo do arquiteto e ainda é
proposta; `migrar.py --recriar` a aplica junto com o esquema, e a partir daí os 15 gatilhos e as
4 visões passam a valer. Antes de rodar a carga completa, confira a cópia externa (pg_dump) do
Prev, como manda o `CLAUDE.md`.

## O que depende do Lucas

As seis que mudam **dado gravado**, não só a tela. As demais estão marcadas `[CONFIRMAR]` no
`esquema.sql` e no `de-para.md`.

1. **`PENDENCIAS`: pedido ou falta?** (pergunta 7) — hoje cada item marcado vira pendência
   **aberta**. Se a marca significava "já recebido", 551 fichas nascem cobrando documento que já
   chegou. É a decisão de maior impacto na tela do dia seguinte.
2. **`REVOGAÇÃO`, os dois sentidos** (pergunta 20) — a migração decide pelo STATUS DO PROCESSO: em
   processo ROUBADO é o cliente que nos revogou (vai para `incidentes`); nos demais somos nós que
   juntamos a revogação do patrono anterior (vai para `processos`). Se a leitura for outra, 529 +
   839 registros mudam de lugar.
3. **`AÇÃO` × `DISTRIBUIÇAO`** — são a mesma data? Hoje entram em colunas diferentes
   (`ajuizamento_em` e `distribuicao_em`). Se forem a mesma coisa, uma some.
4. **`UNA-RS` = rito sumaríssimo?** (pergunta 17) — se sim, 167 audiências também gravam
   `processos.rito`.
5. **`TRATAMENTO`** em STATUS DOCUMENTAÇÃO (5 registros) — é etapa de trabalho interno? Hoje vira
   a flag `em_tratamento`.
6. **`ARQUIVO TST`** — é a data do arquivamento no TST? A descrição na origem é cópia errada da de
   outro campo, e 254 registros dependem disso.

E uma que não é do banco, mas trava a tela: **a lista fechada de setores e quem chefia cada um**
(pergunta 30). `pessoas.setor` está lá, vazio, esperando.
