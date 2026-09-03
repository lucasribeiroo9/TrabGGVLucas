# Auditoria das fases 3 e 4 — esquema, migração e portal

> Auditor, 03/09/2026. Banco auditado: a carga real em Postgres local (`trab_prova`,
> 3.855 processos). Para os testes de escrita pelo portal foi criada uma **cópia**
> (`createdb -T trab_prova trab_aud`), usada na porta 8771 e apagada no fim; `trab_prova`
> não foi alterado (toda prova de gatilho ali rodou dentro de transação revertida). O
> Supabase foi só lido. Nenhum nome, CPF, telefone, e-mail ou número CNJ aparece aqui.
>
> Legenda: **PASSOU** · **PARCIAL** (funciona com lacuna que precisa ser dita) · **FALHOU**.
> Nada foi consertado — este arquivo aponta arquivo, linha e prova.

## Veredito em uma tabela

| # | verificação | veredito |
|---|---|---|
| 1 | toda opção de select é etapa ou atributo declarado, e `normalizar.py` traduz | PARCIAL |
| 2 | 350 campos com linha no de/para, destino existe, valor chega onde se diz | PARCIAL |
| 3 | `conferir.py` termina em TUDO CONFERE — e o que ele não prova | PASSOU, com lacunas |
| 4 | número na tela sai de consulta; contador conta dentro do recorte | PARCIAL |
| 5 | nenhum dado pessoal ou CNJ no repositório e nos commits | PASSOU |
| 6 | RLS e política em toda tabela do Supabase; `anon`/`authenticated` não leem | PASSOU |
| 7 | escrita em SAVEPOINT, erro do banco tratado, recusa vira mensagem e não 500 | **FALHOU** |
| 8 | governança viva no PL/pgSQL; gates de `fluxo.py` = `exige` da governança | PASSOU |
| 9 | regras da casa: automação só cria tarefa; rastro; sem número no template; sem chute | PARCIAL |
| 10 | segurança: permissão no servidor, CSRF, segredo do cookie, portas | PARCIAL |
| 11 | as respostas do Lucas estão implementadas | PARCIAL |

---

## 1. Opções de select × governança × `normalizar.py` × banco — PARCIAL

**Prova.** Script que lê as opções de select das quatro tabelas em `docs/dicionario-dados.md`
(36 campos, 301 opções) e procura cada uma em `normalizar.TABELAS` (chave exata ou normalizada)
ou em `docs/etapa-ou-atributo.md`:

```
opcoes de select nas 4 tabelas: 301 campos: 36
opcoes sem cobertura por TABELA de normalizar ou linha de etapa-ou-atributo: 60
```

Os 60 são falsos negativos do meu critério, não falhas: TRT (21) e TURMA (35) são traduzidos por
**função** (`normalizar.trt()`, `normalizar.turma()`), não por tabela; STATUS_NOTIFICACAO_* (8)
está declarado por campo como log (`automacao_log`, provado: 45 + 58 linhas MIGRADO); os três
recados longos de AND. NECESSÁRIO viram tarefa com o texto inteiro (provado: 73 tarefas
ANDAMENTO = 73 registros na origem fora "Encerrado"/"ACORDO"). `python3 normalizar.py` termina em
TUDO CONFERE (15 valores sem tradução, todos declarados). Os `SELECT DISTINCT` nas colunas de
destino batem com os CHECKs do esquema (status 10 valores, fase 9, situacao_execucao 11, tipo de
audiência 6 + modalidade 2, rito 3, canal 4, rescisão 6).

**Onde falha: tabelas de/para que existem em `normalizar.py` e o `migrar.py` nunca chama.**
`docs/etapa-ou-atributo.md` e `docs/de-para.md` declaram o destino, o dicionário existe, e o
valor não chega:

| origem | declarado | no banco | onde |
|---|---|---|---|
| STATUS CumPrSe → `situacao_execucao` | `normalizar.STATUS_CUMPRSE` | 21 preenchidos, **13 com `situacao_execucao` NULL** | `STATUS_CUMPRSE` não aparece em `migrar.py` |
| STATUS PAGAMENTO = PARCELAMENTO CPC → `PARCELAMENTO_916` | `normalizar.STATUS_PAGAMENTO` | 4 na origem, 2 no banco (os 2 vieram por STATUS EXECUÇÃO) | idem |
| STATUS PAGAMENTO = CESSAO DE CREDITOS → `credito_cedido_em` | idem | 2 na origem, **0** no banco | idem |
| STATUS DO CALCULO = PENDENTE / JUNTADO → `situacao_execucao` | `normalizar.STATUS_CALCULO` | 13 PENDENTE (6 sem situação), 34 JUNTADO (16 sem) | `migrar.py:892` usa a tabela só para `homologado_em` |
| STATUS DO PROCESSO = REDISTRIBUIR → tarefa | `normalizar.STATUS_PROCESSO` (`TAREFA`) | 1 na origem, **0 tarefas** tipo REDISTRIBUICAO | `migrar.py:615-623` trata FASE, RESULTADO e INCIDENTE; ignora TAREFA |
| STATUS CONHECIMENTO = AUSÊNCIA → `resultado_final = ARQUIVADO_AUSENCIA` | `normalizar.STATUS_CONHECIMENTO` | 123 audiências NAO_REALIZADA gravadas, **0** processos com ARQUIVADO_AUSENCIA | `migrar.py:834-839` grava só a audiência |
| STATUS ACORDO = QUEBRA → `acordos.quebrado_em` | de-para linha STATUS ACORDO | 4 QUEBRADO, **0** com `quebrado_em` | `migrar.py:898-908` |
| COMPLEXIDADE fora da faixa → `complexidade_manual = true` | de-para linha COMPLEXIDADE | **0** marcados | não implementado |

Nenhum desses aparece no `conferir.py`, por isso TUDO CONFERE não os pega (ver 3).

## 2. Os 350 campos no de/para e no banco — PARCIAL

**Prova.** Script cruzando `docs/dicionario-dados.md` e `docs/de-para.md` pelo id `fld…`:

```
dicionario: 350 ids distintos · de-para: 350 ids distintos
no dicionario e NAO no de-para: 0 · no de-para e NAO no dicionario: 0
destinos tabela.coluna que não existem em esquema.sql/governanca.sql: 0
```

(As 13 "tabelas" que o parser acusou são `normalizar.xxx()`, `Migracao.xxx()` e `conferir.py`
citados na coluna de regra — referências a código, não a coluna.)

**Amostra de 46 valores** em 30 campos (PRÉ 17, CÓPIA 15, PROCESSUAL 4, PÓS 1, EMPRESAS 2,
TESTEMUNHAS 3, FUNCIONARIOS 1, Faltantes 2, FRAGILIDADES 1), lidos de `dados/*.json` e
comparados com a linha do banco pelo `airtable_record_id`: **45 iguais, 1 diferente.**

O diferente é sistemático. **`DATA REVOG` some em 648 processos** (origem tem a data; nem
`processos.revogacao_em` nem `incidentes.revogacao_nos_autos_em` a têm):

```
por valor de REVOGAÇÃO:  (vazio) 550 · NÃO 77 · SIM 19 · recado 2
dos 648, 136 têm incidente aberto
```

Causa em `migrar.py:917-944`: `revogacao()` devolve `(None, None, None)` quando REVOGAÇÃO
está vazia, e aí nenhum `elif` grava `DATA REVOG` (550 casos); quando há incidente
(`if incidente_situacao or notif or ... or prov`, linha 920), o `elif destino_rev == "PROCESSO"`
da linha 937 nunca roda, e o sentido 1 (nós juntamos a revogação: `revogou_patrono_anterior` +
`revogacao_em`) é descartado — **164 processos com REVOGAÇÃO = SIM/NÃO e incidente ficaram
com `revogou_patrono_anterior` NULL**. O valor está no `airtable_bruto` (perda zero vale), mas o
de/para promete coluna e a coluna está vazia.

Outras promessas do de/para sem coluna preenchida:
- `CNPJ RECLAMADA → … + empresas.cnpj` (linha da CÓPIA): `processos.cnpj_reclamada` tem 3.402;
  **`empresas.cnpj` tem 0**. `migrar.py:655` só grava no processo.
- `ASSINATURA / NASCIMENTO / TELEFONE (+ clientes.…)` para as 2.270 fichas criadas dos autos:
  `migrar.py:809-816` (`achar_cliente`) não copia — **1.556 clientes sem data de assinatura e
  1.934 sem nascimento** embora o processo tenha. O gate `contrato_assinado` e a prescrição
  (`v_pre_processual_atrasado`) leem a ficha, não o processo.
- `SITU. EMPRESA` "divergência com EMPRESAS → conferências": **283 processos** cujo lookup
  discorda de `empresas.situacao`, **0 conferências** (`migrar.py:963-978` usa `COALESCE` e cala).

## 3. `conferir.py` — PASSOU (TUDO CONFERE), com o que ele não prova

**Prova.** `python3 conferir.py --dsn …/trab_prova` → 182 linhas, `TUDO CONFERE`, em 1,2 s.

O que a prova **não** cobre (e por isso os itens de 1 e 2 passaram):

1. **Tabelas sem contagem contra a origem**: `decisoes` (3.668), `recursos` (2.470), `acordos`
   (1.393), `recebimentos` (linhas, não soma), `incidentes` (226), `tarefas` (202), `anotacoes`
   (990), `eventos` (3.432), `contatos` (164), `processo_alias` (653), `automacao_log` (1.629),
   `pendencias` de outro tipo. Só a soma em R$ e alguns selects são conferidos.
2. **Uma linha é circular**: "histórico de etapas (origem MIGRACAO)" compara o banco com o
   próprio banco (`conferir.py:138-141`), não com a origem.
3. **Campo que entra sem ninguém contar**: DATA REVOG, REVOGAÇÃO, CNPJ da reclamada, dados da
   parte na ficha criada dos autos, STATUS CumPrSe, STATUS PAGAMENTO, STATUS DO CALCULO, AUSÊNCIA
   → resultado, QUEBRA → `quebrado_em`, SITU. EMPRESA (todos em 1 e 2).
4. **Coerência que a contagem não vê**: 68 processos ENCERRADO sem `resultado_final`; 2.024
   audiências DESIGNADA em processos ENCERRADO; **2.649 audiências DESIGNADA com data no
   passado** (a migração grava toda audiência como DESIGNADA, `migrar.py:836-837`, salvo
   ausência) — isso polui `v_audiencias_sem_preparacao` (2.670 linhas, 2.649 no passado), a
   fila "abertas" de `/audiencias?janela=todas`, o item 1 de `agora.py` e a regra
   `AUDIENCIA_PREPARAR`, que abriria 2.670 tarefas na primeira rodada; 714 recursos "pendentes"
   (`julgado_em` NULL) em processos ENCERRADO.
5. **Datas inventadas pela carga** (regra 3, "nada de inventar"): `calculos.homologado_em` =
   ENCERRAMENTO em 411 linhas (`migrar.py:896`); `incidentes.notificacao_redigida_em` = DATA
   REVOG ou ENCERRAMENTO em 72 (`migrar.py:928`); `cliente_avisado_em` = ENCERRAMENTO
   (`migrar.py:924`, 0 casos hoje); `arquivado_em` = `encerrado_em` em 37 (`migrar.py:1012`).
   Campo em branco com conferência seria o caminho da casa.
6. **O relógio do SLA nasce zerado**: as 10.183 linhas de `historico_etapas` da migração têm
   `em = 2026-09-03` (`migrar.py:1134-1137` não passa a data de origem). `v_estagnados`
   (`governanca.sql:597-613`) devolve **0 linhas** para 3.855 processos e 3.067 clientes, e o
   item 5 de `agora.py` ("minuta esperando há N dias") vê 0 dias nos 54 casos que são o gargalo.
7. **`limpar()` apaga as contas de acesso.** `migrar.py:32-35` diz que preserva `usuarios`;
   `migrar.py:251-256` faz `TRUNCATE … pessoas … CASCADE`, e `usuarios.pessoa_id` referencia
   `pessoas`. Provado em transação revertida: `usuarios` 37 → **0** depois do TRUNCATE
   (`automacoes` sobrevive). Recarregar no Supabase depois de abrir os acessos apaga todos.

## 4. Número na tela e contador no recorte — PARCIAL

**Prova.** Nenhum número literal de negócio nos 22 templates (`grep`): os únicos são o
`setInterval` de 60 s, `403`/`500` em comentário e dois textos de ⓘ que repetem regra ("15 por
pessoa", "vermelha aos 15") — o valor real vem de `automacoes.config` e da view.

Dez filas com filtro, portal contra `SELECT COUNT(*)` com o mesmo WHERE, no banco de prova:

```
ok /clientes?status=PETICAO_PENDENTE                         tela=35   sql=35
ok /clientes?status=DOCUMENTACAO&vivos=1&setor=Documentação  tela=19   sql=19
ok /processos?fase=RECURSAL&trt=2                            tela=436  sql=436
ok /processos?falta=valor&fase=ENCERRADO                     tela=1    sql=1
ok /audiencias?situacao=NAO_REALIZADA&janela=todas           tela=123  sql=123
ok /audiencias (abertas, 30 dias)                            tela=102  sql=102
ok /tarefas?quem=sem_dono&tipo=ANDAMENTO                     tela=73   sql=73
ok /conferencias?tipo=SEM_NUMERO                             tela=106  sql=106
ok /empresas?situacao=ATIVA&pagamento=BOA                    tela=32   sql=32
ok /testemunhas?situacao=CONFIRMADA&origem=JURIDICO          tela=169  sql=169
```

**Onde falha: contadores secundários que contam o escritório inteiro numa tela filtrada.**
- `/processos?fase=RECURSAL` mostra o chip "sem reclamada · 11"; no recorte são **0**
  (`app.py:578-584`, `templates/processos.html:35-37`).
- `/audiencias?tipo=UNA` mostra "2670 nos próximos 7 dias sem nenhum item"; no recorte UNA são
  1.206 (`app.py:760`, `templates/audiencias.html:6`) — e o número inclui as 2.649 do passado.
- `/tarefas?grupo=…` diz "190 sem dono no escritório" — este ao menos diz que é global.

## 5. Dado pessoal e CNJ no repositório — PASSOU

**Prova.** `git grep` por CPF (`ddd.ddd.ddd-dd` e 11 dígitos), CNJ (20 dígitos e máscara),
telefone e e-mail sobre os arquivos versionados; `git log -p --all` com os mesmos padrões;
`git log --format=%B` nas 13 mensagens. Só aparecem o exemplo de máscara em `app.py:88`, os
dados sintéticos de `dados_exemplo.py` (telefone fictício, domínio `.test`) e o rodapé dos
commits. `dados/`, `*.log`, `*.db` e `servidor.pid` estão no `.gitignore` e nunca entraram no
histórico (`git log --all --name-only`). Nomes nos docs são de funcionários e de uma reclamada.

Atenção fora do git: `servidor.log` grava a linha inteira do registro em cada erro do Postgres
(`DETAIL: Failing row contains …` — nome, CPF, telefone, e-mail). Está ignorado pelo git; num
servidor precisa de rotação e permissão, ou o log vira cópia do cadastro.

## 6. RLS no Supabase — PASSOU

**Prova** (`execute_sql`, projeto `yzayjwlgjjnoxdxgruss`, só leitura):
- 35 tabelas em `public`, todas `rls=true` e `force=true`; política `p_app_trab` em cada uma.
- `set role anon; select count(*) from public.clientes` → `permission denied for table clientes`;
  `set role authenticated; select … from public.processos` → `permission denied`.
- `anon`/`authenticated` sem nenhum grant em `public`; `pg_default_acl` de `postgres` em
  `public` concede só a `postgres` e `service_role` — tabela nova não vaza.
- `postgres` é membro de `app_trab` e tem `bypassrls`: o app entra. Advisors: nada em `public`
  (os avisos são de `prev_2026_09` e do esquema `juridico`, fora do escopo).

Ressalva: o `public` do Supabase está **sem `governanca.sql`** — não há `fluxos`, `fluxo_etapas`,
`fluxo_transicoes`, `historico_etapas`, `prazo_tipos`, nenhum gatilho, nenhuma view `v_*`
(35 tabelas lá, 40 aqui). `docs/migracao-resultado.md` diz isso. Quem subir tem de rodar
`migrar.py --recriar`, que aplica os dois `.sql` e chama `ligar_rls()` de novo — e `conferir.py`
já cobra "tabela sem RLS = 0".

## 7. SAVEPOINT, `banco.Integridade`/`Operacional` e a recusa que vira mensagem — FALHOU

**O que passa.** Toda escrita passa por `Ponte._escrever` com `SAVEPOINT ggv_passo`
(`banco.py:355-370`). Os gates de `fluxo.py` e o mapa viram mensagem: 19 transições proibidas
testadas pelo portal com sessão de gestor e de advogado devolvem `302` com `?erro=` e a etapa não
muda (fora do mapa, documento faltando, papel GESTOR/DIRECAO, minuta, CNJ curto, sentença,
parcelas, repasse, nova audiência, petição de reserva, data da notificação, motivo em branco).

**O que falha — e é o centro desta auditoria.** O `except` de erro do banco está escrito como
tupla aninhada em cinco lugares:

```
app.py:480   except (banco.Integridade, banco.Operacional) as e:   pendencia_resolver
app.py:506   except (banco.Integridade, banco.Operacional) as e:   pendencia_nova
app.py:1154  except (banco.Integridade, banco.Operacional) as e:   conferencia_resolver
app.py:1233  except (banco.Integridade, banco.Operacional) as e:   tarefa_status
app.py:1361  except (banco.Integridade, banco.Operacional) as e:   mover
```

`banco.Integridade` e `banco.Operacional` **já são tuplas** (`banco.py:97`), e Python não aceita
tupla dentro de tupla em `except`. Reproduzido fora do portal:

```
>>> try: raise psycopg.errors.CheckViolation('x')
... except (banco.Integridade, banco.Operacional) as e: ...
TypeError: catching classes that do not inherit from BaseException is not allowed
```

Ou seja: **qualquer recusa do Postgres nessas rotas vira 500**, exatamente o que o cabeçalho de
`app.py:18-19` promete que não acontece. Provado pelo portal: encerrar processo com
`resultado_final` fora do CHECK → 500; registrar audiência com resultado fora do CHECK → 500;
pendência com tipo fora do CHECK → 500 (`servidor.log`: `TypeError … app.py, line 1361`). O
`app.py:846` (`audiencia_checklist`) escapa porque tem `ValueError` na frente — que também não
resolve, só muda a ordem.

O Prev escreve `except (ValueError, banco.Integridade)` e `except banco.Operacional` — nunca as
duas tuplas juntas. `automacao.py:96` (`except banco.Integridade:`) está certo.

**Consequência dois: a conexão vaza.** Em `mover` (`app.py:1355-1366`) e nas outras rotas,
`db.close()` fica fora de `finally`; com a exceção, a conexão nunca volta ao poço
(`max_size=6`, `banco.py:497`). Depois de seis recusas o portal para de responder **para todo
mundo** — `servidor.log:548-549`: `psycopg_pool.PoolTimeout: couldn't get a connection after
20.00 sec`, e 18 ocorrências na sequência. Foi o que travou a primeira rodada de testes.

**Rotas de escrita sem tratamento nenhum**: `cliente_responsavel` (`app.py:430-450`),
`processo_anotacao` (`app.py:685-699`), `prazo_responsavel` (`app.py:904-918`). Provado:
`POST /clientes/{id}/responsavel` com `pessoa_id` inexistente → 500; anotação em processo
inexistente → 500.

Menor: `fluxo.mover` grava o campo da janela sem validar tipo (`fluxo.py:436-441`): prazo
CUMPRIDO com `cumprido_em = "ontem"` foi aceito e gravado como texto; `date` no `<input>` é
conveniência, não trava.

## 8. Governança viva e os gates — PASSOU

**Prova no psql** (transação revertida sobre `trab_prova`), 14 recusas e 6 aceites:

```
recusado cliente ENTREVISTA→DISTRIBUIDO            transição de status fora do fluxo CLIENTE
ok       cliente ENTREVISTA→PETICAO_PENDENTE        + historico_etapas (de, para, origem SISTEMA)
recusado processo CONHECIMENTO→RECEBENDO            fora do fluxo PROCESSO
recusado audiência REALIZADA→DESIGNADA              fora do fluxo AUDIENCIA
recusado incidente DETECTADO→HONORARIOS_RECEBIDOS   fora do fluxo INCIDENTE
recusado nascer cliente em DOCUMENTACAO / processo em RECURSAL / prazo em CUMPRIDO
ok       nascer cliente em LEAD
recusado processo novo para cliente com bienal vencida (gov_prescricao_bienal)
ok       o mesmo com dispensa_prescricao_motivo · ok com contrato_vivo=true
recusado prazo CORRIDOS sem contagem_motivo · ok com motivo
recusado CUMPRIDO sem cumprido_em · recusado PERDIDO sem motivo · ok PERDIDO com motivo
recusado PERDIDO→ABERTO · recusado tipo fora de prazo_tipos (fk_prazo_tipo)
```

17 gatilhos ligados (`tgenabled = 'O'`), 6 funções com `search_path=public`, 40 políticas em
40 tabelas. `conferir.py` cobra "gatilho desligado = 0" depois da carga.

Gates: os 22 nomes em `fluxo_transicoes.exige` são exatamente os 22 tratados em
`fluxo._gate` (diferença vazia nos dois sentidos); 111 transições, 40 etapas. `texto_bloqueio`
cobre todos (o `LIKE 'numero_cnj%'` alcança `numero_cnj,prescricao_viva`).

Ressalva de desenho, não de defeito: o banco recusa o **mapa**, nascimento, prescrição e as
regras de prazo; os gates de negócio (resultado, sentença, repasse…) vivem só em `fluxo.py`.
Provado: `update processos set fase='ENCERRADO'` sem resultado passa no psql. É o contrato
escrito em `governanca.sql:56`; vale saber que "mão humana no psql" contorna os gates.

## 9. Regras da casa — PARCIAL

- **Automação só cria tarefa e rascunho**: PASSOU. `automacao.py` escreve em `tarefas`,
  `automacao_log` e `automacoes` (upsert das regras) e num `UPDATE tarefas SET responsavel_id`
  (a distribuição). Nenhuma regra toca `status`/`fase`/`situacao`.
- **Toda execução deixa rastro**: PARCIAL. `_uma_vez` grava uma linha por **ação**; uma rodada
  em que nenhuma regra tem o que fazer **não grava nada** — o silêncio que a regra 6 proíbe.
  `execucao.registrar` existe e `automacao.rodar()` não o chama; não há launchd/cron para
  `automacao.py` nem para `execucao.py --vigiar` no repositório (sem pasta `implantar/`). E a
  linha de `_uma_vez` é gravada **antes** de `abrir_tarefa` (`automacao.py:186-191`): quando a
  tarefa já existia, o log diz OK e nada aconteceu.
- **Primeira rodada de `AUDIENCIA_PREPARAR`** abriria 2.670 tarefas (item 4 da seção 3).
- **`DISTRIBUIR_FILA`** não entrega nada: `pessoas.setor` está NULL nos 72 (esperando a
  resposta 30). Documentado; continua sendo fila sem dono.
- **Número na tela sai de consulta**: PASSOU (seção 4).
- **Formulário não chuta**: PARCIAL. `pendencia_nova` assume `tipo = 'OUTRO'` quando o campo
  não vem (`app.py:494`); as datas inventadas da carga estão na seção 3, item 5.

## 10. Segurança — PARCIAL

- **Permissão no servidor**: PASSOU. Como ADVOGADO: `/painel`, `/equipe`, `/fluxos` → 403;
  aprovar a inicial → "esta ação exige papel GESTOR"; reabrir encerrado como GESTOR → "exige
  papel DIRECAO"; prazo PERDIDO como ADVOGADO → recusado. Sem sessão, toda tela → `302 /entrar`.
- **CSRF**: PASSOU. POST sem token → 403; POST com token de **outra** sessão → 403; login sem
  token → 403. Todo formulário é injetado pela trava; o único `fetch` é GET.
- **Segredo do cookie**: FALHOU. `app.py:1423` cai em `"trocar-em-producao"` quando
  `GGV_SEGREDO` não existe, e `rodar.sh:24-26` só avisa e sobe. Uma sessão assinada com esse
  valor vale em qualquer instalação. Deveria recusar subir.
- **Senha/token no repositório**: PASSOU (grep por `pat…`, `eyJ…`, `sk-ant-`, URIs com senha;
  nada). Contas de prova não estão escritas em lugar nenhum.
- **`rodar.sh`/`parar.sh`**: PASSOU. Só 8771, `lsof -tiTCP:8771`; nenhum `pkill -f`.
- Menores: `/saude` e `/api/agora` respondem sem sessão (`/saude` diz quantos processos há);
  cookie sem `https_only` (aceitável em 127.0.0.1); `servidor.log` com dado pessoal (seção 5).

## 11. O que o Lucas respondeu — PARCIAL

| resposta | está? | prova / onde falta |
|---|---|---|
| 5 · LEAD existe | sim, no mapa | `fluxo_etapas` LEAD, tipo INICIAL; `gov_nasce_na_inicial` aceita nascer em LEAD e recusa em DOCUMENTACAO. **0 fichas LEAD** porque não há rota de cadastro (`portal-telas.md` assume); a tela de Início diz isso |
| 7 · pendência tem tipo, só documento trava | sim | `pendencias.tipo` CHECK com 6 tipos; view `documentos_pendentes`; `fluxo.documentos_faltando` lê só DOCUMENTO. Provado no portal: DOCUMENTACAO→ENTREVISTA recusado por "falta: RG ou CNH, CTPS, TRCT". Falta rota para abrir pendência **de processo** (réplica, reunião) — `pendencia_nova` só aceita cliente |
| 7 · pedido sem recebimento continua pendente | sim | `solicitado_em` não fecha; `pendencias_abertas` calcula `espera_dias`; ação "solicitada" em `app.py:477` não marca recebimento |
| 8 · aprovação é da equipe de Petição Inicial | **não** | `governanca.sql:109` grupo `'Gestão'`; `governanca.sql:149` papel `'GESTOR'`. `equipe.py:GRUPO_DA_ETAPA` só **renomeia** Gestão→Petição Inicial na tela. Um membro da equipe de Petição Inicial com papel ADVOGADO não aprova (provado: "exige papel GESTOR"). O `texto_operador` da etapa ainda diz "A minuta espera quem aprova" sem dizer quem |
| 26 · repasse é referência ao financeiro | sim no gate | `fluxo.py` exige `entregue_ao_financeiro_em`; `repasses` tem `sem_valor_motivo`. Mas `texto_bloqueio` (`governanca.sql:439`) não fala em financeiro, e **não há rota para registrar repasse** — o único processo em RECEBENDO não pode ser encerrado pelo portal |

---

## O que precisa ser corrigido antes de subir ao Supabase, por gravidade

1. **`except (banco.Integridade, banco.Operacional)`** em `app.py:480, 506, 1154, 1233, 1361`:
   toda recusa do banco é 500 e prende uma conexão; seis recusas travam o portal
   (`PoolTimeout`). Junto: `db.close()` em `finally` nas rotas de escrita, e tratamento em
   `cliente_responsavel`, `processo_anotacao`, `prazo_responsavel`.
2. **`migrar.limpar()` apaga `usuarios`** (`migrar.py:251-256`, TRUNCATE CASCADE em `pessoas`)
   apesar de `migrar.py:32-35` prometer o contrário. Qualquer recarga depois de abrir os
   acessos derruba todo mundo.
3. **`GGV_SEGREDO` com valor fixo de fallback** (`app.py:1423`, `rodar.sh:24-26`).
4. **DATA REVOG e o sentido 1 da REVOGAÇÃO perdidos** em 648 / 164 processos
   (`migrar.py:917-944`) — e `conferir.py` não conta. Mesmo remédio de sempre: uma linha de
   prova por campo (`docs/migracao-resultado.md` já ensinou isso seis vezes).
5. **Audiências do passado gravadas como DESIGNADA** (2.649; `migrar.py:836-837`): polui
   `agora.py`, `v_audiencias_sem_preparacao`, `alertas.py` e faz `AUDIENCIA_PREPARAR` abrir
   2.670 tarefas na primeira rodada. Data anterior à carga sem resultado conhecido deveria
   entrar como REALIZADA com conferência, ou a view/regra excluir o passado.
6. **Resposta 8 não implementada**: quem aprova a inicial (`governanca.sql:109, 149`). É linha
   de tabela, mas o papel `GESTOR` exigido na transição é código de governança e trava a
   equipe certa.
7. **Histórico da migração com a data da carga** (`migrar.py:1134-1137`): SLA e "há quantos
   dias" nascem zerados para 10.183 registros.
8. **De/para declarado e não aplicado**: STATUS CumPrSe, STATUS PAGAMENTO (parcelamento,
   cessão), STATUS DO CALCULO, REDISTRIBUIR → tarefa, AUSÊNCIA → `ARQUIVADO_AUSENCIA`,
   QUEBRA → `quebrado_em`, `empresas.cnpj`, `complexidade_manual`, dados da parte na ficha
   criada dos autos, SITU. EMPRESA → conferência. Ou se implementa, ou o de/para passa a dizer
   `airtable_bruto`.
9. **Datas inventadas** (`homologado_em`, `notificacao_redigida_em`, `arquivado_em`,
   `cliente_avisado_em`): em branco com conferência, como manda a regra 3.
10. **Contadores globais em tela filtrada** (`app.py:578-584, 760`).

## O que pode esperar

- Rastro de rodada vazia e agendamento de `automacao.py`/`execucao.py` (seção 9).
- Rotas de cadastro: lead, repasse, pendência de processo, decisão, acordo, parcela — sem elas
  RECEBENDO→ENCERRADO, ACORDO→RECEBENDO e LEAD só existem no mapa.
- 68 ENCERRADO sem `resultado_final`; 714 recursos "pendentes" em processo encerrado.
- `pessoas.setor` (resposta 30) — sem ele a distribuição não distribui.
- Validação de tipo dos campos da janela (`cumprido_em = "ontem"`).
- `/saude` sem sessão; `servidor.log` com dado pessoal.
- Circularidade de "histórico de etapas" no `conferir.py`.

## Rastro desta auditoria

- Criado e apagado: banco `trab_aud` (cópia de `trab_prova`), duas contas de prova só nele.
- `trab_prova`: intocado (provas de gatilho em transação revertida; `conferir.py` só lê).
- Supabase: só `list_tables`, `get_advisors` e `execute_sql` de leitura (`set role` dentro da
  própria chamada). `prev_2026_09` não foi tocado.
- Portal: subiu duas vezes na 8771 e foi derrubado por `./parar.sh`; 8770 nunca foi alcançada.
- Nenhum arquivo do repositório alterado além deste. Sem commit.
