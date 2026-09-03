# Auditoria de fechamento — segunda passagem sobre as fases 3 e 4

> Auditor, 03/09/2026, depois dos commits `bc19fd8` (portal) e `b79d4bc` (migração). Cada item
> do primeiro laudo (`docs/auditoria-fase-3-4.md`) que não era PASSOU foi **reproduzido por mim**,
> não aceito pelo relato do DEV ou do DBA. Banco de prova `trab_prova` (só leitura; a única escrita
> que uma prova deixou lá — um repasse — foi apagada, ver "Rastro"). As provas destrutivas rodaram
> em `trab_aud`, criado por mim do zero pelo `migrar.py --recriar` e apagado no fim. Supabase não
> foi tocado; `prev_2026_09` intocado. Nenhum nome, CPF, telefone, e-mail ou CNJ aparece aqui.

## Veredito, antes e depois

| # | verificação | antes | depois | prova |
|---|---|---|---|---|
| 1 | opção de select é etapa/atributo; de/para aplicado (CumPrSe, cessão, AUSÊNCIA, REDISTRIBUIR, `empresas.cnpj`…) | PARCIAL | **PASSOU** | §1-2 |
| 2 | 350 campos com destino; DATA REVOG e sentido 1 da REVOGAÇÃO; ficha dos autos com assinatura/nascimento | PARCIAL | **PASSOU** | §1-2 |
| 3 | `conferir.py` em TUDO CONFERE, cobre toda tabela carregada e **acusa** sabotagem | PASSOU c/ lacunas | **PASSOU** | §3 |
| 4 | contador conta dentro do recorte | PARCIAL | **PARCIAL** — processos e audiências corrigidos; clientes, tarefas e conferências ainda contam o escritório inteiro | §4 |
| 5 | sem dado pessoal/CNJ no repositório e nos dois commits novos | PASSOU | **PASSOU** | §5 |
| 6 | RLS no Supabase | PASSOU | não re-verificado lá (nada mudou no Supabase nesta rodada); `conferir.py` cobra "tabela sem RLS = 0" e acusou quando desliguei uma | §3 |
| 7 | recusa do banco vira recado, nunca 500; conexão volta ao poço | FALHOU | **PARCIAL** — as rotas de ESCRITA passaram (15 recusas, 0 × 500, 25 seguidas, poço vivo); as rotas de LEITURA com filtro não numérico dão 500, vazam a conexão e **sete GETs derrubam o portal para todo mundo** | §7 |
| 8 | governança viva no PL/pgSQL; gates = `exige` | PASSOU | **PASSOU** (17 gatilhos ligados, 0 desligados; `pessoa_no_setor()` existe no banco mas nenhum gatilho a usa — o gate de setor vive só em `fluxo.py`, como os outros gates de negócio) | §11 |
| 9 | automação só cria tarefa; rastro da rodada vazia; `AUDIENCIA_PREPARAR` só no futuro | PARCIAL | **PARCIAL** — 21 tarefas, todas de audiência futura; SEM_ACAO gravado; mas **duas rodadas no mesmo segundo colidem na chave do rastro e a segunda estoura** (regressão) | §9 |
| 10 | segredo do cookie sem valor de reserva; nenhum segredo fixo | PARCIAL | **PASSOU** | §10 |
| 11 | respostas do Lucas (5, 7, 8, 26) | PARCIAL | **PASSOU no mapa e no portal**, com a ressalva de que `pessoas.setor` está vazio e por isso hoje ninguém aprova | §11 |

---

## 7. Recusas sem 500 — PARCIAL (escrita passou; leitura ainda derruba o portal)

**Como.** Portal subido com `GGV_DSN=…/trab_prova GGV_SEGREDO=<48 chars> ./rodar.sh` (porta 8771),
sessão da conta GESTOR de prova, token de CSRF lido do `<meta>` da página. Quinze recusas seguidas,
cada uma por um caminho diferente:

```
 1 fora do mapa: CONHECIMENTO → RECEBENDO            302 · não existe caminho da etapa atual para RECEBENDO
 2 gate motivo em branco: → SOBRESTADO               302 · escreva o motivo da mudança
 3 CHECK: resultado_final fora da lista              302 · o valor não está entre os que este campo aceita … (processos_resultado_final_check)
 4 FK: dono do atendimento inexistente               302 · esse campo aponta para um registro que não existe … (clientes_responsavel_id_fkey)
 5 FK: anotação em processo inexistente              302 · … (anotacoes_processo_id_fkey)
 6 CHECK: pendência com tipo fora da lista           302 · … (pendencias_tipo_check)
 7 gate de setor: GESTOR sem setor aprovando         302 · esta ação é da equipe de Petição Inicial …; e anexe a minuta …
 8 FK: dono de conferência inexistente               302 · … (conferencias_dono_id_fkey)
 9 mover processo inexistente (id 999999)            302 · não existe caminho da etapa atual para RECURSAL
10 repasse com "uns mil reais"                       302 · não entendi o valor … — escreva como 1.234,56
11 pessoa_id não numérico no prazo                   302 · invalid literal for int() with base 10: 'abc'
12 gate: audiência realizada sem resultado           302 · registre o que aconteceu: acordo, defesa juntada …
13 entidade fora do mapa (/mover/tarefas/1)          302 · volta para /
14 repasse com data 31/02/2026                       302 · ok: repasse registrado   ← ACEITO (ver abaixo)
15 POST sem token de CSRF                            403
500 encontrados: 0
```

Depois delas: `/processos /clientes /audiencias /prazos /tarefas /conferencias /saude` → 200.
**25 recusas seguidas em 0,3 s, todas 302**, e `/processos` responde 200 em seguida. O processo de
prova continuou em CONHECIMENTO. `servidor.log` da rodada: 0 tracebacks, 0 respostas 500,
0 ocorrências de `DETAIL`/`Failing row` — nem no log nem nas URLs de retorno.

**UNIQUE não é alcançável por nenhum POST do portal** (as chaves únicas estão em `usuarios.email`,
`recebimentos`, `acordo_parcelas`, `automacao_log`… sem rota de escrita). Provei `_recado()` por
fora, com o erro real do Postgres em `trab_aud`, dentro de SAVEPOINT (nada ficou gravado):

```
UNIQUE   23505 → já existe um registro com esse valor … (usuarios_email_key)
CHECK    23514 → o valor não está entre os que este campo aceita … (pendencias_tipo_check)
FK       23503 → esse campo aponta para um registro que não existe … (anotacoes_processo_id_fkey)
NOT NULL 23502 → falta preencher um campo obrigatório
GATILHO  P0001 → transição de fase fora do fluxo PROCESSO: CONHECIMENTO → RECEBENDO
```

Em todos, `str(e)` tem 2 linhas e a segunda carrega `DETAIL`/`Key (…)`; só a primeira passa.
`banco.ErroBanco` é tupla plana de 11 classes, todas `BaseException`.

**Onde ainda falha — e derruba o portal.** As telas de fila fazem `db = conectar()` e só depois
`int(p["advogado"])`, `int(p["responsavel"])`, `int(p["dono"])`, `?::int` da janela — sem `try`,
sem `finally`. Um filtro não numérico na URL (bookmark velho, URL editada à mão) dá 500 **e prende a
conexão**; com `max_size=6`, o sétimo pedido para tudo:

```
GET /processos?advogado=abc            500   (app.py:638, ValueError)
GET /clientes?responsavel=x            500   (app.py:406)
GET /audiencias?responsavel=x          500   (app.py:926)
GET /audiencias?janela=99999999999     500   (app.py:929, NumericValueOutOfRange 22003)
GET /conferencias?dono=abc             500   (app.py:1310)
GET /prazos?responsavel=abc            500   (app.py:1086)
GET /processos?empresa=1e3             500   (app.py:630)
… e a seguir:  POST /entrar → 500  ·  GET /processos → 500 em 20,0 s
servidor.log: psycopg_pool.PoolTimeout: couldn't get a connection after 20.00 sec  (6 vezes)
```

Reproduzido duas vezes (a segunda com 7 × `/processos?advogado=abc` num portal recém-subido:
`/processos` → 500 em 20 s, 4 `PoolTimeout` no log). Exige sessão, mas é o mesmo modo de falha que
o primeiro laudo apontou nas rotas de escrita, agora pelo lado da leitura. Não é regressão — o código
já era assim —, mas o primeiro laudo não o tinha visto, e a promessa do cabeçalho de `app.py`
("recusa vira recado") continua descumprida em 7 rotas. Correção: `int()` dentro do `try`, ou antes
do `conectar()`, e `db.close()` em `finally` também nas leituras.

**Menores, no mesmo tema:**
- `_RECUSAS` traduz 22P02 e 22001, mas `banco.ErroBanco` não inclui `psycopg.errors.DataError`
  (só `IntegrityError`, `RaiseException` e a família operacional): um erro de formato vindo do banco
  não é pego por nenhum `except` — as duas entradas são código morto. Provado: `SELECT 'abc'::int`
  passa reto pelo `except banco.ErroBanco`.
- Caso 14: `POST /processos/{id}/repasse` aceitou `entregue_ao_financeiro_em = 31/02/2026` (data
  impossível, gravada como texto) num processo em **CONHECIMENTO** — a rota não confere formato de
  data nem se o processo está em RECEBENDO. Foi a única escrita que uma recusa não recusou, e foi
  apagada de `trab_prova` (ver "Rastro").
- Caso 11: o recado é a mensagem crua do Python (`invalid literal for int()`), não uma frase.

## 10. Segredo do cookie — PASSOU

```
GGV_SEGREDO ausente         → "✗ GGV_SEGREDO não definido — o portal não sobe sem ele."  rc=1
GGV_SEGREDO = "   "         → idem (o strip pega)                                        rc=1
GGV_SEGREDO com 10 chars    → "tem 10 caracteres; use pelo menos 32"                    rc=1
GGV_SEGREDO com 31 chars    → recusado                                                   rc=1
GGV_SEGREDO com 32 chars    → subiu                                                      rc=0
./rodar.sh sem a variável   → para antes do uvicorn, rc=1
```

A recusa está em `app.py:_segredo()` (vale para launchd/uvicorn na mão) e em `rodar.sh`. `grep`
por `trocar-em`, `secret_key=`, `senha=`/`segredo=`/`secret=`/`password=`/`token=` com valor
literal em `*.py *.sh *.html *.sql`: só o comentário de `app.py` que conta a história do valor
antigo. Nenhum segredo fixo sobrou.

## 3. `conferir.py` — PASSOU

- `trab_prova`: **249 linhas, TUDO CONFERE**, 1,9 s. `trab_aud` (recriado por mim do zero:
  `migrar.py --do-conector --origem …` e depois `migrar.py --recriar --dsn …`, 17 s — os dois
  passos são separados: `--do-conector` converte e **retorna** sem carregar): **249 linhas, TUDO
  CONFERE**.
- **Tabelas com linhas que `conferir.py` não cita: `fluxo_transicoes` (111) e `prazo_tipos` (18)** —
  as duas são semente de `governanca.sql`, não carga do Airtable. Tabela carregada da origem sem
  linha de prova: **zero**. Vazias de propósito: `acordo_parcelas auditoria automacoes peticoes
  prazos repasses usuarios`.
- **Sabotagem em `trab_aud`** (6 alterações à mão: uma `revogacao_em` apagada, uma sentença a menos,
  uma audiência passada devolvida a DESIGNADA, um histórico datado da carga, um `homologado_em`
  inventado, RLS desligada em `repasses`) → `conferir.py` **rc=1, "9 divergência(s) — a migração
  NÃO está boa"**, acusando exatamente as seis: `decisões · sentenças 2.148 ≠ 2.147`, `situação da
  audiência DESIGNADA 263 ≠ 264 / REALIZADA 2.649 ≠ 2.648`, `DATA REVOG 1.427 ≠ 1.426`, `resultado
  da sentença`, `tabela sem RLS 0 ≠ 1`, `histórico datado da carga 0 ≠ 1`, `audiência DESIGNADA no
  passado 0 ≠ 1`, `cálculo com data de homologação 0 ≠ 1`.
- Detalhe: a recarga **sem** `--recriar` não religa RLS (só `--recriar` chama `ligar_rls()`), e o
  `conferir.py` acusou isso depois da recarga (1 divergência) — comportamento correto, vale saber.
- Vício de escrita, sem efeito hoje: `conferir.py` (linha da prova "CumPrSe/cálculo discordando…")
  escreve `WHERE tipo='DIVERGENCIA_FONTE' AND valor_a LIKE 'STATUS CumPrSe%' OR valor_a LIKE …` —
  `AND` prende só ao primeiro `OR`. Passa porque nenhum outro tipo tem `valor_a` com esses prefixos.

## 1 e 2. As provas de dado — PASSOU

Recontagem **independente** (meu script sobre `dados/copia.json` e `dados/processual.json`, casando
por dígitos do CNJ, PROCESSUAL vence, 3 INAPLICÁVEL fora): **1.427 registros vivos com DATA REVOG**;
no banco `1.326 processos.revogacao_em + 101 incidentes.revogacao_nos_autos_em = 1.427`. Sentido 1:
794 SIM / 66 NÃO / 2.995 NULL; 79 contradições (NÃO com data) em conferência.

Em `trab_prova`, pelas minhas consultas:

```
audiências DESIGNADA com data no passado ........ 0     (era 2.649)
histórico MIGRACAO datado da carga (≥ 2026-09-03)  0     (era 10.183)   v_estagnados: 674 (era 0)
calculos.homologado_em ........................... 0     (era 411)
incidentes: notificação/aviso com data ........... 0     (era 72)
processos.transito_em / arquivado_em ............. 0 / 0 (era 25 / 37)
acordos.quebrado_em / testemunhas.confirmada_em .. 0 / 0
processo ou cliente criado com a data da carga ... 0
v_audiencias_sem_preparacao ...................... 21    (era 2.670)
```

**Contas sobrevivem à recarga** (`trab_aud`): `auth.py equipe` criou 36 contas; marquei uma
conferência RESOLVIDA com dono e anotação; recarga **sem** `--recriar` → `usuarios (preservados) 36`,
dump de `usuarios` (id, e-mail, hash, papel, ativo, trocar_senha, pessoa por nome) **igual byte a
byte** (`cmp`), a conferência decidida voltou com dono e resolvedor; recarga **com** `--recriar` →
igual de novo; `conferir.py` TUDO CONFERE nas duas. Autenticação pelo `auth.autenticar` com a senha
provisória mostrada uma vez: **36 de 36 entram** depois das duas recargas. A sequência de `usuarios`
anda depois do `OVERRIDING SYSTEM VALUE` (INSERT sem id → ok). `auth.py equipe` de novo: "todo mundo
do escritório já tem acesso". Menor: a tabela que `auth.py` imprime tem colunas de largura fixa
(`auth.py:197`) e, quando o e-mail tem 34+ caracteres, sai **colado ao papel** (`…com.brADVOGADO`),
o que fez 2 das 36 parecerem recusadas na primeira leitura — é só a impressão, a conta está certa.

## 4. Contador no recorte — PARCIAL

Tela × `SELECT COUNT(*)` com o mesmo WHERE, em `trab_prova`, 20 comparações:

```
ok  /processos?fase=RECURSAL&trt=2   total 436 · sem reclamada 0 · sem número 0 · chip Conhecimento 407
ok  /processos?falta=numero&fase=RECURSAL   total 5 · chip sem valor 0
ok  /audiencias?tipo=UNA&janela=todas   total 192 · "destas, 14 nos próximos 7 dias sem checklist" · chip Designada 192
ok  /audiencias?situacao=NAO_REALIZADA&janela=todas   total 123
ok  /clientes?vivos=1&setor=Jurídico   total 46
DIV   chip "Documentação · 19"  no recorte: 0        (clientes: por_etapa vem de v_funil_etapas, global)
DIV   chip "Cancelado · 169"    no recorte vivos: 0
DIV /tarefas?tipo=ANDAMENTO  chip "sem dono · 191"   no recorte: 73   (app.py:1432, global; o texto diz "no escritório")
ok    chip "notificacao · 94"  (a tela abre em quem=minhas; o chip de tipo bate com abertas)
ok  /conferencias?entidade=empresas   total 171 · chip "empresa ambigua" 171
DIV   chip "sem numero · 106"  no recorte entidade=empresas: 0   (app.py:1319, global)
```

Os dois casos do primeiro laudo (chip de qualidade em `/processos`, "sem preparação" em
`/audiencias`) estão corrigidos e o link do chip mantém o recorte. O mesmo defeito continua em
`/clientes` (`por_etapa`, `canais`), `/tarefas` (`grupos`, `tipos`, `sem_dono`) e `/conferencias`
(`tipos`, `entidades`) — o `Recorte` foi aplicado só em duas telas. `/prazos` está vazio (0 prazos),
não dá para provar.

## 5. Dado pessoal nos dois commits — PASSOU

`git show bc19fd8 b79d4bc` filtrado pelas linhas adicionadas: 0 CPF (máscara ou 11 dígitos), 0 CNJ
(máscara ou 20 dígitos), 0 telefone, 0 e-mail; nas duas mensagens de commit só o rodapé de
co-autoria. `dados/`, `*.log` e `servidor.pid` continuam no `.gitignore`. Este arquivo é o único
não versionado no fim da auditoria.

## 9. Automação — PARCIAL (fila viva e rastro certos; a chave do rastro colide)

Em `trab_aud`, com `GGV_DSN` apontando para lá:

```
--seco                    → "nada a fazer (modo seco)"; automacao_log inalterado (1.629)
rodada 1                  → AUDIENCIA_PREPARAR 21 · PRESCRICAO_BIENAL 11; 32 tarefas, origem ≠ MIGRACAO
  chaves de AUDIENCIA_PREPARAR × data da audiência:  futura 21 · passada 0
  nenhuma fase/status/situação mudou (dump antes = dump depois)
rodada 2, no MESMO segundo → psycopg.errors.UniqueViolation: automacao_log_automacao_chave_key
                             Key (automacao, chave)=(AUTOMACAO_RODADA, exec:2026-09-03T20:08:38:1)
rodada 3, 2 s depois       → DISTRIBUIR_FILA tarefa:233 (distribuiu, porque eu tinha dado setor a 2 pessoas)
rodada 4, colada na 3      → a mesma UniqueViolation (exec:…20:09:32:1)
rodada 5, 1 s depois       → "nada a fazer" · linha AUTOMACAO_RODADA SEM_ACAO gravada
```

A chave do rastro é `exec:<segundo>:<tentativa>` (`execucao.py:103`); duas rodadas dentro do mesmo
segundo colidem e a segunda **estoura com traceback antes de gravar qualquer coisa** — nem a linha
ERRO que `registrar` promete, porque é o INSERT dela que falha. Regressão introduzida por
`bc19fd8` ao embrulhar `rodar()` em `execucao.registrar`: com launchd 3×/dia não acontece; num
retry, num `--vigiar` que dispara a rodada, ou em dois operadores rodando à mão, acontece. E fica a
observação do laudo anterior: `_uma_vez` grava antes de `abrir_tarefa`.

## 11. Respostas do Lucas — PASSOU (com o setor vazio como ressalva)

**Resposta 8, no mapa** (`trab_prova`): as três transições de PETICAO_AGUARDANDO_APROVACAO exigem
`ADVOGADO` + `setor_peticao_inicial` (+ minuta ou motivo). **Pelo `fluxo.mover`** em `trab_aud`,
com `pessoas.setor` ajustado à mão em duas pessoas:

```
ADVOGADO do Jurídico devolve para ajuste        → recusado: esta ação é da equipe de Petição Inicial …; seu setor é Jurídico
GESTOR sem setor                                → recusado: … seu setor é não cadastrado
DIRECAO sem setor                               → recusado (é setor, não hierarquia)
conta sem pessoa (pessoa_id=None)               → recusado: … esta conta não está ligada a uma pessoa
ADVOGADO da Petição Inicial devolve para ajuste → MOVEU (PETICAO_EM_CRIACAO)
pessoa_no_setor(id, 'Petição Inicial') no banco → true só para a pessoa do setor
```

**Pelo portal** (subido contra `trab_aud`, duas contas com senha provisória trocada em `/senha`):
ADVOGADO do Jurídico abre a ficha (a ação aparece travada com o motivo), tenta devolver e aprovar →
302, status continua PETICAO_AGUARDANDO_APROVACAO; ADVOGADO da Petição Inicial → aprovar sem minuta
recusado, devolver com motivo **moveu**, `historico_etapas` com `pessoa_id` = a pessoa e o motivo.
0 × 500 no log.

**A ressalva:** `pessoas.setor` está NULL nos 72 em `trab_prova` e volta a NULL a cada recarga
(`equipe.AJUSTES` vazio, esperando a pergunta 30). Hoje **ninguém** — nem GESTOR, nem DIRECAO —
aprova, devolve ou cancela as 54 fichas em PETICAO_AGUARDANDO_APROVACAO, o gargalo do funil; e
`DISTRIBUIR_FILA` só distribuiu quando dei setor às pessoas. O mapa está certo; a fila fica travada
até alguém preencher o setor. Não há tela para isso — é `equipe.py`.

Resposta 26 (repasse): rota e formulário existem e RECEBENDO → ENCERRADO destrava (provado pelo DEV
numa cópia; eu provei só a recusa e o caso 14). Respostas 5 e 7: sem mudança desde o laudo anterior.

## Regressões e defeitos novos vistos no diff (olho adversarial)

1. **`execucao.registrar` colide no mesmo segundo** e a rodada estoura sem rastro (§9) — regressão.
2. `banco.ErroBanco` não cobre `DataError` (22P02/22001/22003): `_RECUSAS` tem entradas mortas e o
   overflow de `?janela=` é 500 (§7).
3. Leitura sem `finally`: 7 rotas GET prendem conexão e derrubam o portal (§7) — pré-existente,
   não visto no primeiro laudo.
4. `POST /processos/{id}/repasse` não valida data nem fase (§7, caso 14).
5. `conferir.py`: precedência `AND … OR … OR` na linha de CumPrSe (§3).
6. `governanca.sql` cria `pessoa_no_setor()` mas nenhum gatilho a chama: o commit diz "gate de setor
   verificado no banco"; no banco, `UPDATE clientes SET status='PETICAO_EM_CRIACAO'` por qualquer
   pessoa passa (é o contrato de `governanca.sql:56`, mas a mensagem do commit promete mais).
7. `equipe.GRUPO_DA_ETAPA` passou a traduzir "Gestão" → "Direção" (era → "Petição Inicial"): a única
   etapa com grupo Gestão é PRAZO → PERDIDO; mudança de rótulo, [CONFIRMAR pergunta 30].
8. `Banco.guardar()` devolve vazio em modo `--sql-saida`: o plano B (`dados/carga_real.sql`) nasce
   sem contas — coerente com "carga é para antes do portal", mas não está no `--help`.
9. `auth.py:197` cola e-mail e papel na tabela impressa quando o e-mail tem 34+ caracteres (§1-2).

## Pode subir ao Supabase?

**SIM, com estas ressalvas** — a carga está provada; o que falta é do portal e do organograma:

1. **Antes de abrir o portal para a equipe**: fechar as 7 rotas de leitura que dão 500 e prendem
   conexão com filtro não numérico (§7) — sete cliques em URL errada param o sistema para todos.
2. Corrigir a chave de `execucao.registrar` (§9) antes de agendar a automação — ou garantir uma
   rodada por vez.
3. Preencher `pessoas.setor` (pergunta 30) ou ninguém aprova a inicial (§11).
4. Chips de `/clientes`, `/tarefas`, `/conferencias` ainda contam o escritório inteiro (§4).
5. Validar data e fase no repasse (§7, caso 14).
6. Subir com `migrar.py --recriar` (não a recarga simples): só ele religa RLS e aplica
   `governanca.sql`; depois `conferir.py`, que cobra RLS em toda tabela. Fazer antes o `pg_dump` do
   `prev_2026_09`, como manda o `CLAUDE.md`.

O que **não** foi re-verificado nesta passagem: RLS e políticas no Supabase (item 6 — nada mudou lá)
e o caminho de sucesso do repasse pelo portal (item 11/26 — provado pelo DEV em cópia).

## Rastro desta auditoria

- `trab_prova`: uma escrita indevida (repasse do caso 14 e a linha de `auditoria` que o acompanhou)
  — apagada; `repasses`, `auditoria` e `anotacoes MANUAL` em 0, `usuarios` 36, `processos` 3.855.
- `trab_aud`: criado, sabotado, recarregado duas vezes, 36 contas de prova (senhas só no scratchpad,
  fora do repositório), apagado no fim.
- Portal: subiu na 8771 quatro vezes (uma para provar a queda por `PoolTimeout`, uma contra
  `trab_aud`), derrubado por `./parar.sh`. 8770 nunca alcançada.
- `dados/*.json` reescritos pelo `do_conector` com o mesmo conteúdo (só `baixado_em` mudou, mesmo dia).
- Supabase: nenhuma chamada. Nenhum commit, nenhum push; nenhum arquivo do repositório alterado
  além deste.
