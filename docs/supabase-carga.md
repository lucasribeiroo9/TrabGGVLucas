# O banco no Supabase — o que subiu, e o que ainda falta

> 04/09/2026. Continuação de `docs/migracao-resultado.md`, que terminou dizendo: *"Não se
> conectou ao Supabase nesta rodada: a carga lá depende da URI que só o Lucas tem"*. A URI
> chegou (`GGV_SUPABASE_TRAB`) e esta rodada foi até onde o ambiente deixou ir.
> Nenhum nome de cliente, CPF, telefone, e-mail ou número de processo aparece aqui — só contagens.

## Em uma frase

**O esquema está lá, inteiro e provado: o `public` do Supabase é hoje byte a byte o que o
repositório descreve, com a governança viva e recusando o que tem de recusar.** O que não
subiu foi o DADO — e não por decisão de projeto, mas porque este ambiente não alcança o
Postgres nem o Airtable. O motivo está escrito abaixo, com o comando que resolve.

## O que estava lá antes, e o que mudou

O `public` tinha o esquema da rodada ANTERIOR do DBA: 35 tabelas, RLS ligada, zero linhas.
Faltava tudo o que a terceira rodada acrescentou. Quatro migrations fecharam a diferença.

| migration | o que fez |
|---|---|
| `trab_processos_arquivado_e_credito_cedido` | as 2 colunas que faltavam em `processos` (61 → 63) |
| `trab_governanca_01_mapa_de_etapas` | as 5 tabelas do mapa + 5 fluxos, 40 etapas, 111 transições, 18 tipos de prazo, e o texto de bloqueio de 96 transições |
| `trab_governanca_02_gatilhos_views_e_rls` | as 3 funções de gatilho, os 17 gatilhos, os 2 gates do banco, `pessoa_no_setor()`, as 5 views, as 2 FKs adiadas e `ligar_rls()` de novo |
| `trab_checks_da_terceira_rodada_do_dba` | três listas fechadas que ficaram na versão velha — ver abaixo, é o achado da rodada |

## O achado: três CHECKs que teriam recusado 2.574 linhas

O `public` foi criado antes de a terceira rodada do DBA existir, e três listas fechadas
ficaram congeladas na versão anterior. Nenhuma delas dá erro enquanto o banco está vazio.
Todas dariam erro **no meio da carga**, uma linha por vez, recusando dado que a migração
considera certo:

| CHECK | valor que faltava | linhas que a carga real traz |
|---|---|---:|
| `conferencias.tipo` | `AUDIENCIA_SEM_RESULTADO` | 279 |
| `pendencias.documento_tipo` | `CONTRATO` | 1.283 |
| `pendencias.tipo` | `CADASTRO` | 1.012 |
| | **total** | **2.574** |

São exatamente os três conceitos que a terceira rodada criou (audiência passada sem
resultado registrado; ficha sem contrato de honorários; dado de cadastro que a origem não
tinha). Comparar contagem de tabela não acharia isto — o banco está vazio dos dois lados.
Só a comparação de **definição** acha, e é por isso que ela virou parte da prova.

## A prova: o Supabase contra o repositório, hash a hash

Um Postgres 16 local recebeu `esquema.sql` + `governanca.sql` + as 2 FKs + `ligar_rls()`,
na ordem que `migrar.py --recriar` usa, e virou o banco de REFERÊNCIA. Os dois lados foram
reduzidos à mesma impressão digital e comparados.

| o que | referência | Supabase | |
|---|---|---|---|
| objetos com coluna (40 tabelas + 6 views) | 46 | 46 | **iguais, um a um** |
| md5 das colunas (nome, tipo, nulo, identidade, default) | — | — | **idêntico nos 46** |
| md5 de todas as constraints, com a definição | `3fcb9e1c…` | `3fcb9e1c…` | **idêntico** |
| md5 de todos os índices | `b6b53564…` | `b6b53564…` | **idêntico** |
| constraints / FKs / CHECKs / índices / políticas | 216 / 92 / 73 / 105 / 40 | 216 / 92 / 73 / 105 / 40 | iguais |
| gatilhos / funções | 17 / 7 | 17 / 7 | iguais |
| RLS ligada | 40 de 40 | 40 de 40 | iguais |
| fluxos / etapas / transições / tipos de prazo | 5 / 40 / 111 / 18 | 5 / 40 / 111 / 18 | iguais |

Uma diferença conhecida e sem efeito: em `processos`, `arquivado` e `credito_cedido`
entraram por `ALTER TABLE` e ficam no FIM da tabela, enquanto no `esquema.sql` estão no
meio. `ordinal_position` difere; nome, tipo, nulidade e default não. A carga escreve por
coluna nomeada, e o próximo `--recriar` normaliza.

## A governança está VIVA lá — nove provas, todas dentro de uma transação desfeita

Não basta a tabela existir. O que vale é o banco dizer não.

| # | o que se tentou | o banco |
|---|---|---|
| 1 | cliente nascer em `LEAD` (etapa inicial) | passou |
| 2 | cliente nascer em `DISTRIBUIDO` (etapa do meio) | **recusou** |
| 3 | `LEAD → DISTRIBUIDO` (fora do mapa) | **recusou** |
| 4 | `LEAD → DOCUMENTACAO` (no mapa) | passou **e gravou o histórico sozinho** |
| 5 | processo de cliente com prescrição bienal consumada | **recusou** |
| 5b | o mesmo, com `dispensa_prescricao_motivo` escrito | passou |
| 6 | prazo em dias `CORRIDOS` sem `contagem_motivo` (CLT art. 775) | **recusou** |
| 7 | prazo em dias `UTEIS` | passou |
| 8 | prazo com tipo fora de `prazo_tipos` (a FK nova) | **recusou** |

Tudo dentro de um bloco que termina em `RAISE`, então **nada ficou**: depois da prova o
`public` voltou a ter 174 linhas — 5 + 40 + 111 + 18, só o mapa.

## O que NÃO subiu: o dado

A carga (`migrar.py --recriar`, os 3.855 processos e o resto) **não rodou**, e não por
opção. Este ambiente é um container remoto do Claude Code, e faltam as duas pontas:

1. **Não há caminho até o Postgres.** A saída de rede passa por um proxy que só fala
   HTTPS. O `README` dele lista, entre o que não passa: *"non-443 HTTPS ports, raw-TCP
   databases"*, e manda reportar em vez de contornar. A conexão direta
   (`db.<projeto>.supabase.co:5432`) só tem endereço IPv6 e nem resolve; o pooler
   (`aws-0-sa-east-1.pooler.supabase.com`, portas 5432 e 6543) resolve em IPv4 e **estoura
   o tempo** — testado nas duas portas. O que funcionou o tempo todo foi o **MCP do
   Supabase**, que é HTTPS: é por ele que as quatro migrations subiram.
2. **Não há como ler o Airtable.** `GGV_AIRTABLE_TRAB` não está no ambiente, então
   `migrar.py --baixar` não tem token. Sobra o conector MCP (o caminho do
   `do_conector.py`), mas por ele os 10.412 registros teriam de atravessar a conversa —
   e depois os ~40 MB de SQL da carga atravessariam de volta, para entrar por
   `apply_migration`. São as duas travessias somadas que inviabilizam: dá mais que o
   orçamento inteiro da sessão, e um erro de transcrição em 51.489 `INSERT`s seria calado.

Nenhuma das duas é problema do projeto. Numa máquina com acesso ao Postgres — o Mac do
escritório — a carga leva os mesmos ~2 minutos de sempre.

## Para terminar, de uma máquina com rede até o Postgres

```bash
export GGV_SUPABASE_TRAB=...                 # a URI do Postgres do PrevGGVLucas
./.venv/bin/python migrar.py --do-conector --origem PASTA   # se for pelo conector MCP
./.venv/bin/python migrar.py --recriar       # apaga o public e refaz: esquema + governança + carga
./.venv/bin/python conferir.py               # 249 linhas, TUDO CONFERE
```

`--recriar` derruba o `public` e o reconstrói dos dois `.sql` — o que este documento acabou
de fazer à mão vira, ali, o passo normal. **Os três CHECKs corrigidos já estão em
`esquema.sql`**, então a recriação nasce certa; a migration `trab_checks_…` existe para o
caso de alguém carregar SEM `--recriar`, sobre o esquema que está lá agora.

Continua valendo o que o `CLAUDE.md` manda: **a cópia externa (`pg_dump`) do
`prev_2026_09` antes**. Ela não foi feita aqui — sem TCP não há `pg_dump` — e `--recriar`
não a dispensa, ainda que só derrube o `public`.

## A primeira conta de direção

O `portal-prova.md` fechava dizendo que **não havia nenhuma conta `DIRECAO` no cadastro**, e que
enquanto não houvesse, o campo de perfil de acesso ficava só de leitura para todo mundo — de
propósito, porque promover alguém a sócio não é ato de gestor. A conta agora existe no Supabase:

| | |
|---|---|
| pessoa | **Glauco Gimenez Varella**, setor `Direção` |
| entra com | `glauco@ggvadvocacia.com.br` — o padrão de `criar_para_equipe` (`{primeiro}@{domínio}`) |
| perfil | `DIRECAO` |
| senha | provisória, **troca obrigatória na primeira entrada** (`trocar_senha = true`) |

Quem é a direção não foi escolha desta rodada: está em `docs/respostas-do-lucas.md` — *"Apenas
Glauco é o sócio. Do trabalhista, Rai e Lucas não são sócios."* A senha **não está escrita em
lugar nenhum do repositório**, como manda a regra da casa: foi entregue uma vez, e o sistema
obriga a trocá-la antes de deixar abrir qualquer outra tela.

O hash é o do próprio sistema (`auth.cifrar`, scrypt n=16384 r=8 p=1), não uma reimplementação.
Provado contra o banco de referência, com o **mesmo `senha_hash` que está no Supabase**:
`auth.autenticar` devolve a sessão com papel `DIRECAO`, setor `Direção` e troca pendente; senha
errada é recusada; `auth.pode(papel,'DIRECAO')` é verdadeiro; o perfil abre 13 telas.

**Falta a segunda.** A decisão registrada é de **duas** contas de direção — o **Dr. Vitor
Esteves** responde quando o Glauco está fora, e são duas contas de verdade, não uma direção "de
plantão": o sistema não sabe quando alguém viajou. O que segura o uso indevido é o rastro.

Duas coisas a saber antes da carga:

1. **A conta sobrevive ao `--recriar`.** `Banco.guardar()` lê as contas antes de derrubar o
   schema e `restaurar_usuarios()` as devolve com o mesmo id, hash e papel, recasando a pessoa
   pelo record do Airtable **ou pelo `nome_norm`**. Esta pessoa foi criada à mão e não tem record,
   então o recasamento vai pelo nome: `GLAUCO GIMENEZ VARELLA`, gerado com o mesmo `normalizar.norm`
   que a migração usa, para casar com a linha que vier de FUNCIONARIOS.
2. **O setor NÃO sobrevive.** `migrar.py` recria `pessoas` do Airtable, e com elas o setor e a
   chefia se perdem — é a pendência que o `portal-prova.md` já registrava. A rede é
   `equipe_setores.py --exportar` antes da carga e `--aplicar` depois. Sem isso a conta continua
   `DIRECAO` (o papel está em `usuarios`), mas a ficha da pessoa volta sem setor.

## O que foi conferido para garantir que nada mais foi tocado

`prev_2026_09` (a cópia do previdenciário, 69 tabelas) e `juridico` (163 tabelas, extensão
`vector`) não foram tocados, como o `CLAUDE.md` manda. Contados depois de tudo:
`prev_2026_09.clientes` = 2.396 e `prev_2026_09.processos` = 2.369, os mesmos de antes.

Antes de escrever qualquer coisa, uma conferência valeu a pena: **nenhuma extensão vive no
`public`** (`pg_trgm` está em `prev_2026_09`, `vector` em `juridico`, o resto em
`extensions`). Fosse o contrário, o `DROP SCHEMA public CASCADE` do `--recriar` levaria
junto os índices do previdenciário. Fica registrado porque é a conferência que ninguém
lembra de fazer antes do primeiro `--recriar` no Supabase.

Os *advisors* de segurança do Supabase, depois das quatro migrations, não apontam **nada**
no `public`. O que eles listam é de `prev_2026_09` (RLS ligada sem política — que é o
desejado: esquema fora da API) e de `juridico` (funções com `search_path` mutável), e
nenhum dos dois é nosso.
