# O que veio do Prev, e o que precisou mudar

> Escrito pelo DEV do portal em 03/09/2026. O princípio é o do CLAUDE.md: **quem
> se adapta é o ambiente, não o código copiado**. Reescrever à mão o que já
> funciona foi o erro que, no Prev, fez a primeira importação do Financeiro
> entregar 9 telas de 22 sem erro nenhum aparecer. Então: copia-se o arquivo, e
> a diferença fica escrita aqui.

## Copiados sem mudar uma linha

| Arquivo | O que é |
|---|---|
| `csrf.py` | A trava contra pedido forjado. Middleware ASGI puro: o token entra na VOLTA, no HTML já pronto, e é conferido na IDA. Nenhuma das telas sabe que ele existe. Único ajuste: o título da página de recusa diz "GGV Trabalhista". |
| `chaves.py` | De onde vem cada segredo — ambiente primeiro, Keychain depois. Ajustado só o **dicionário** de segredos (nomes do trabalhista). |
| `cofre.py` | O cofre Fernet. Copiado e **não usado**: aqui não há senha de terceiro para guardar. Fica pronto para quando houver. |
| `agenda_google.py` | A agenda. Copiado e **não ligado** — ver "o que ficou de fora". |
| `static/estilo.css` | O CSS inteiro do Prev. O portal acrescenta um bloco NO FIM (`.colunas`, `.grade-ficha`, `.linha-acoes`, `.campo-janela`, `.num`, `.fim`, `.atrasado`, `.destaque`). Fica no fim de propósito: quando o Prev mudar o estilo, copiar o arquivo por cima e recolocar o bloco é o movimento inteiro. |
| `templates/base.html` | A casca. O miolo do JavaScript é o mesmo — o embrulho do `fetch` que põe o token de CSRF em todo POST, o encaixe da trilha, o balão do ⓘ, o contador do "agora". O que mudou foi o **menu** (as telas são outras) e o que saiu: clima, busca global, personificação e o seletor de tema, que dependem de rotas e colunas que este sistema ainda não tem. |

## Copiados e adaptados — o mínimo, e por quê

### `banco.py` — a ponte
- **Não há SQLite aqui.** No Prev o SQLite é a cópia local; aqui o banco já
  nasce no Postgres. `em_postgres()` devolve sempre `True`, `SQLITE` é `None` e
  `conectar()` só entrega a `Ponte`. **A tradução continua inteira** — é ela
  que deixa o código das telas escrito no dialeto simples (`?`, `date('now')`,
  `LIKE`, `julianday`), e é o mesmo arquivo do Prev: divergir na tradução
  seria manter duas pontes.
- **A ligação é outra**: `GGV_DSN` (o que `--dsn` e `rodar.sh` usam), depois
  `GGV_SUPABASE_TRAB`, depois a chave `supabase-trab` do Keychain.
- `FALTA_TRADUZIR` esvaziou: a busca FTS5 do acervo é coisa do Prev.
- Um defeito corrigido de passagem: o `atexit` do poço chamava
  `_POCO.close()` mesmo depois de `fechar_poco()` já ter zerado a variável, e
  todo script terminava cuspindo um `AttributeError` sobre uma saída limpa.
  Agora registra `fechar_poco`, que já trata.

**Armadilha herdada, que vale repetir:** `julianday(...)` só é traduzido com
UM nível de parênteses dentro. `julianday(COALESCE((SELECT …), col))` passa
reto e estoura no Postgres. Onde precisou, a subconsulta saiu com nome
(`agora.py`, item 5).

### `auth.py` — usuários e permissão
Reescrito, não copiado, e por três razões de esquema:
1. **Os papéis são três**, não cinco: `usuarios.papel` tem
   `CHECK ('ADVOGADO','GESTOR','DIRECAO')`, e é esse mesmo vocabulário que
   `fluxo_transicoes.papel` cobra. Um quarto papel na tela faria a tela
   oferecer o que o banco recusa.
2. **A conta não guarda o nome.** `usuarios` aqui é
   `(pessoa_id, email, senha_hash, papel, ativo, trocar_senha)`; o nome vem de
   `pessoas`. Nome escrito em dois lugares diverge no primeiro dia em que
   alguém casa.
3. **`ativo` e `trocar_senha` são BOOLEAN**, não `INTEGER 0/1`.

O que ficou igual: `scrypt` com sal por senha, `compare_digest` na conferência,
senha provisória mostrada **uma vez** e troca obrigatória na primeira entrada.

**Um defeito do Prev corrigido aqui:** `criar_para_equipe` derivava o e-mail do
primeiro nome e **pulava em silêncio** quem colidisse — dois "Marcelo" no
escritório e o segundo simplesmente ficava sem acesso, sem ninguém perceber.
Agora tenta primeiro nome, depois `primeiro.sobrenome`, depois um número.
Ninguém fica de fora.

### `fluxo.py` — o motor de governança
Reescrito para as colunas deste esquema. A divisão de trabalho é a mesma (o
banco recusa o que está fora do mapa; aqui ficam os **gates** de negócio), e a
lista de gates é a de `governanca.sql`: `contrato_assinado`,
`documentos_obrigatorios`, `entrevista_registrada`, `minuta_anexada`,
`numero_cnj`, `prescricao_viva`, `sentenca_registrada`, `transito_registrado`,
`acordo_registrado`, `numero_cumprse`, `resultado`, `valor_recebido`,
`parcelas_quitadas`, `repasse_registrado`, `retorna_fase_anterior`,
`resultado_audiencia`, `nova_audiencia`, `protocolo_registrado`,
`novo_vencimento`, `notificacao_enviada`, `peticao_reserva`, `motivo`.

Duas coisas novas em relação ao Prev:

- **Gate que vira CAMPO na janela.** No Prev só o `motivo` tinha esse
  tratamento (`so_falta_motivo`). Aqui a ideia foi generalizada: o que a pessoa
  vai digitar naquele instante — motivo, número CNJ, protocolo e data do
  protocolo, número do CumPrSe, data do trânsito, resultado final, resultado da
  audiência, novo vencimento — aparece como campo dentro do `<dialog>`, e o
  botão não trava. Travar por causa de um campo que está logo ali em cima é o
  tipo de tela que ensina a pessoa a desconfiar do sistema.
- **`MOTIVO_COLUNA`.** O motivo vai para o histórico E para a coluna da
  entidade, porque `gov_prazo_regras` **recusa** um prazo `PERDIDO` sem
  `prazos.motivo` — e o gatilho não lê o histórico. Sem isto, registrar prazo
  perdido dava erro do banco na cara de quem clicou, no pior dia do escritório.
  Está provado nos dois sentidos em `portal-prova.md`.

### `agora.py` e `alertas.py`
Regra igual, conteúdo novo: só entra o que tem **gente parada** ou **relógio
externo correndo**, e o teto continua sendo 6 itens. O que muda é o domínio —
audiência sem preparação, prazo em dias úteis, prescrição bienal, pendência de
documento sem resposta, minuta esperando aprovação. `alertas.por_processo`
responde a lista inteira em poucas consultas, uma por sinal, não uma por
processo: com 3.722 processos o contrário seria a tela.

### `execucao.py`
Copiado; adaptado só onde o esquema difere. O `automacao_log` daqui tem
`(automacao, chave, resultado, detalhe, origem, cliente_id, processo_id,
testemunha_id)` e **não tem** `itens`, `erro` nem `tentativa`. Nada se perde: os
três vão no `detalhe`, e `resultado` continua sendo o que distingue rodada que
falhou de dia sem nada a fazer — que é o ponto inteiro do arquivo. `PARCIAL`
virou `SEM_ACAO`, que é o que o CHECK aceita. O vigia passou a se chamar
`DEJT_LEITURA` (aqui a publicação é do DEJT, não da AASP).

### `automacao.py`
O **motor** veio inteiro — registro das regras, `config`, `ativa`, `_uma_vez`
com a chave natural `(automacao, chave)`, `abrir_tarefa` e o `Distribuidor`
com peso (urgente 3, atrasada 2, resto 1) e teto de 15. As **regras** não
vieram: as do Prev falam de INSS, CNIS, exigência e Tema 350, e não há tradução
honesta disso. As seis daqui são novas e todas param no mesmo lugar — abrem
tarefa com dono e prazo. Nenhuma protocola nem move etapa.

### `equipe.py`
`AJUSTES` e `CHEFIA` estão **vazios de propósito** — ver a pendência 1 abaixo.

## Correções depois da auditoria (03/09/2026)

O Auditor cruzou as fases 3 e 4 (`docs/auditoria-fase-3-4.md`). O que era do
portal foi corrigido nesta rodada; a prova está em `docs/portal-prova.md`.

### `banco.py` — `ErroBanco`, a tupla plana

O Prev escreve `except (ValueError, banco.Integridade)` ou
`except banco.Operacional` — **nunca as duas tuplas juntas**. Aqui cinco rotas
escreveram `except (banco.Integridade, banco.Operacional)`, e isso não é um
`except` mais abrangente: é um `TypeError`. Os dois nomes já são tuplas, Python
não aceita tupla aninhada ali, e o resultado é o tratamento sumir sem avisar —
toda recusa do gatilho virando 500, que é exatamente o que o cabeçalho do
`app.py` promete que não acontece.

`banco.ErroBanco = Integridade + Operacional` é a tupla plana, com o comentário
do porquê logo acima dela. Onde o `ValueError` também precisa ser pego, a forma
é `except (ValueError,) + banco.ErroBanco` — soma de tuplas, nunca aninhamento.

**Consequência dois, e a mais cara:** `db.close()` estava fora de `finally`. Com
a exceção, a conexão nunca voltava ao poço (`max_size=6`), e seis recusas
paravam o portal para todo mundo com `PoolTimeout`. Agora toda rota de escrita
fecha em `finally` — `Ponte.close()` dá rollback e devolve ao poço, então uma
linha só resolve as duas coisas.

### `app.py` — `_recado()`, a recusa em português

Duas fontes de recusa, dois tratamentos. A **governança** fala por `RAISE` do
PL/pgSQL e já escreve para gente ler; dela só se tira o cabeçalho. O **esquema**
(CHECK, FK, UNIQUE, NOT NULL) fala em inglês e cita o nome do constraint —
correto e inútil na tela. `_recado()` traduz por SQLSTATE e guarda o nome do
constraint entre parênteses, para quem for investigar depois.

E passa **só a primeira linha** do erro, sempre. As linhas de `DETAIL` do
Postgres trazem o registro inteiro (`Failing row contains …`: nome, CPF,
telefone) e iriam para a barra de endereço do navegador e para o
`servidor.log`. Erro não é lugar de vazar cadastro.

### `app.py` — `Recorte`, o filtro montado por dimensão

A regra da casa diz que todo contador conta dentro do recorte ativo. O chip é o
caso difícil: em `/processos?fase=RECURSAL`, "sem reclamada · 11" contava o
escritório inteiro enquanto a fila embaixo tinha 0 — contador global em tela
filtrada não é imprecisão, é oferecer trabalho que não existe.

`Recorte` guarda o filtro como lista de `(dimensão, sql, args)`, e
`onde(exceto=…)` devolve o WHERE sem uma delas. É isso que deixa cada chip
contar o recorte **menos a sua própria dimensão** — os três chips de qualidade
são alternativas entre si, e contá-los já com `falta=numero` aplicado daria a
interseção. Os chips de fase e de situação da execução seguiram o mesmo
caminho, com `LEFT JOIN`/subconsulta para a etapa com 0 continuar listada: sem
isso não haveria como navegar para fora do filtro atual.

O link do chip mudou junto — era `/processos?falta=empresa` fixo, que largava o
recorte. Número dentro do recorte com link que sai dele seria trocar um engano
por outro.

### `app.py` — `_segredo()`: sem `GGV_SEGREDO`, o portal não sobe

Havia `os.environ.get("GGV_SEGREDO", "trocar-em-producao")`. Reserva é o
problema: quem esquece a variável não vê erro nenhum, sobe, e passa a assinar
sessão com um segredo escrito no repositório — uma sessão forjada em qualquer
cópia do código valeria nesta instalação, e o portal inteiro se apoia no cookie
para saber quem é quem e qual é o papel.

Agora recusa subir, com o comando para gerar um. A recusa está no `app.py` e
não só no `rodar.sh` porque quem sobe por launchd, systemd ou `uvicorn` na mão
não passa pelo script. Segredo com menos de 32 caracteres também é recusado.
Barulhento de propósito: portal que não sobe é problema de cinco segundos;
portal que sobe com o segredo de teste é problema de ninguém perceber.

### `app.py` — `POST /processos/{id}/repasse`

O gate `repasse_registrado` existia sem porta: o único processo em RECEBENDO
não podia ser encerrado por ninguém pelo portal. A rota registra a
**referência** — houve, quando, quanto (ou por que não havia) e a data de
entrega ao financeiro —, não o repasse: resposta 26 do Lucas, quem paga é o
financeiro. Por isso a tela pede "entregue ao financeiro em" e não tem botão
"repassar".

Permissão no servidor por `exige(req, "processos")`, a mesma da transição que a
referência destrava (que em `fluxo_transicoes` não exige papel — herdar a
exigência da tabela em vez de inventar uma). CSRF pela trava, como todo
formulário. O `INSERT` deixa linha na `auditoria`: dinheiro tem dono, ainda que
aqui seja só a referência dele.

`_para_centavos()` aceita "1.234,56" e "1234.56" e **levanta** no que não é
dinheiro. Vazio devolve `None`; o que não dá para ler PARA o pedido em vez de
virar zero — zero é um valor, e "repassei R$ 0,00" é afirmação diferente de
"não consegui ler o que você digitou".

### `automacao.py` — fila viva e rastro de rodada vazia

`AUDIENCIA_PREPARAR` ganhou `WHERE v.dias_para_audiencia >= 0`. A view
`v_audiencias_sem_preparacao` não tem piso de data e devolve as 2.649
audiências passadas que a migração gravou como DESIGNADA: a primeira rodada
abriria 2.670 tarefas de uma vez (agora são 21), e a fila de verdade sumiria
dentro do passivo. É o princípio da `DISTRIBUIR_FILA` do Prev — regra nova
trabalha para a frente; o passivo é decisão de gestão, resolvida caso a caso
em `/audiencias?janela=todas`.

A correção é na REGRA e não na view: `governanca.sql` é do arquiteto, e a view
serve também à tela, onde ver o passivo tem uso. Quem conta o passivo escolhe
contá-lo; quem abre tarefa, não.

`rodar()` passou a correr dentro de `execucao.registrar("AUTOMACAO_RODADA")` —
`OK` com a contagem, `SEM_ACAO` na rodada vazia, `ERRO` com a mensagem. Sem
essa linha, uma automação que parou de rodar e um dia sem trabalho são a mesma
coisa vista do banco, que é o modo de falha que a regra 6 da casa proíbe.
`--seco` continua sem escrever nada, nem o rastro.

### `app.py` — `pendencia_nova` não chuta mais o tipo

Assumia `tipo = 'OUTRO'` quando o campo não vinha. É o tipo `DOCUMENTO` que
trava a etapa (gate `documentos_obrigatorios`), então chutar aqui é decidir por
alguém se aquela pendência segura o processo ou não. Agora o formulário pede.

### `rodar.sh`

Para antes de subir quando falta `GGV_SEGREDO`, com o comando para gerar um e
como guardá-lo no Keychain — o recado sai no terminal em vez do fim do
`servidor.log`. `parar.sh` não mudou: continua matando só a 8771.

## O que ficou de fora desta rodada, e por quê

- **`agenda_google.py`** está copiado mas não ligado: ele lê
  `usuarios.google_sync_em`, `google_sync_erro` e `eventos.google_event_id`.
  A última existe; as duas primeiras não. São duas colunas e uma migration —
  fica para quando a agenda entrar de verdade (o segredo `google-agenda` ainda
  nem foi criado, nem no Prev).
- **`cofre.py`** depende de `cryptography` e não tem uso aqui. Fora do
  `requirements.txt` de propósito: dependência que não se usa é dependência que
  quebra a instalação da máquina nova sem motivo.
- **Tela da lista de faltantes do Datajud** (`conferencia_faltantes`, 1.067
  linhas). A tela de Conferências já diz quantas são e que a fila existe.
- **Cadastro pelo portal**: `/novo-lead` e `/novo-cliente` do Prev não têm
  equivalente ainda. O portal desta rodada **lê e move**; criar ficha nova é a
  próxima. Consequência prática, que a tela de Início diz em voz alta: a etapa
  `LEAD` só passa a existir quando a entrada pelo portal existir.

## Divergências encontradas, que dependem do Lucas

1. **[CONFIRMAR — pergunta 30] Os setores não batem.** A resposta 8 diz "existe
   um setor próprio para cada etapa". `equipe.SETORES` traz os doze que o
   diretor passou (Captação, Atendimento/Entrevista, Documentação, Petição
   Inicial, Jurídico/Processual, Audiências, Execução, Testemunhas, Financeiro,
   TI, Publicação, Direção). Mas `fluxo_etapas.grupo`, em `governanca.sql`, usa
   **sete** nomes: Captação, Documentação, Atendimento, Jurídico, Gestão,
   Financeiro, Direção. Enquanto as duas listas não forem a mesma, o portal
   mostra o **grupo da etapa** (que é dado, vindo da tabela) e traduz pela
   tabela `GRUPO_DA_ETAPA`; a lista de doze serve só ao cadastro de pessoa.
   Onde a tradução é palpite, está marcado: `Gestão → Petição Inicial`, porque
   a resposta 8 diz que quem aprova a inicial é a equipe de Petição Inicial, e
   não a Gestão como o arquiteto supôs.

   **Efeito visível hoje:** com `pessoas.setor` vazio, a regra `DISTRIBUIR_FILA`
   não entrega tarefa a ninguém — ela procura gente no setor da tarefa e não
   acha. As tarefas ficam na fila "sem dono", que é o comportamento certo para
   um organograma que ainda não existe, mas não é o comportamento útil.

2. **[CONFIRMAR] O domínio de e-mail** do escritório trabalhista. Está
   `ggvadvocacia.com.br` em `auth.criar_para_equipe`, por falta de resposta.
   O e-mail é só identificador de entrada, não precisa ser caixa postal — mas
   é o que a pessoa digita, e trocar depois é mexer em todas as contas.

3. **[CONFIRMAR] Os feriados do TRT.** `prazo_legal.py` conta dias úteis com os
   feriados **nacionais** e o recesso de 20/12 a 20/01 (CLT art. 775-A). Faltam
   os do TRT (portarias anuais, que variam por região e por ano) e os
   municipais da sede da vara. Sem eles a conta erra **para o lado curto**: o
   prazo aparece vencendo antes, nunca depois. É o lado seguro do erro — o
   outro lado é perder prazo —, mas é erro.

4. **[CONFIRMAR] O que é "ad video"**, item do checklist da audiência. A origem
   tem os campos (STATUS ADVIDEO / DATA ADVIDEO) e eles estão vazios em todos
   os registros. A tela mostra o item e diz que não sabe o que ele é.

5. **[CONFIRMAR] A janela de 7 dias** da preparação da audiência
   (`v_audiencias_sem_preparacao`) e o farol 15/20 do pré-processual continuam
   como o arquiteto propôs. O portal usa os dois; se o escritório trabalha com
   outra folga, muda-se a view, não o código.

## Achados da auditoria de fechamento que NÃO são do portal (para o DBA)

> Anotados pelo DEV em 03/09/2026, ao corrigir o §7 e o §9 do laudo
> `docs/auditoria-fechamento.md`. Não toquei em `migrar.py`, `normalizar.py`,
> `conferir.py`, `governanca.sql` nem `esquema.sql` — o combinado é que quem
> mexe neles é o DBA e o arquiteto.

1. **`conferir.py`, precedência `AND … OR`** (laudo §3, defeito 5). A linha de
   prova de CumPrSe/cálculo escreve
   `WHERE tipo='DIVERGENCIA_FONTE' AND valor_a LIKE 'STATUS CumPrSe%' OR valor_a LIKE …`.
   Em SQL, `AND` liga mais forte que `OR`: o `tipo=` prende só ao primeiro
   `LIKE`, e os demais valem para qualquer tipo. Hoje passa porque nenhum outro
   tipo tem `valor_a` com esses prefixos — ou seja, a prova está certa por
   coincidência de dado, não por construção. Cabe um par de parênteses.

2. **`governanca.sql` cria `pessoa_no_setor()` e nenhum gatilho a chama**
   (laudo §8 e defeito 6). O gate de setor da aprovação da inicial vive só em
   `fluxo.py`, como os outros gates de negócio, e isso é coerente com o
   contrato escrito em `governanca.sql:56` — mas a mensagem do commit `bc19fd8`
   promete "gate de setor verificado no banco", e no banco um
   `UPDATE clientes SET status='PETICAO_EM_CRIACAO'` passa por qualquer pessoa.
   Ou o gatilho passa a chamar a função, ou a função sai e a promessa muda.
   **Decisão do arquiteto**, não do portal.

3. **`Banco.guardar()` devolve vazio em `--sql-saida`** (defeito 8): o plano B
   `dados/carga_real.sql` nasce sem as contas de acesso. É coerente com "a
   carga é para antes do portal", mas não está no `--help` de `migrar.py`.

4. **[CONFIRMAR pergunta 30] `equipe.GRUPO_DA_ETAPA["Gestão"]`** hoje aponta
   para `Direção` (antes apontava para `Petição Inicial`). Depois da resposta 8
   a aprovação da inicial passou a ser da etapa de grupo `Petição Inicial` no
   próprio mapa, e "Gestão" só sobra em `PRAZO → PERDIDO`, que é registro de
   quem gere o escritório. É **rótulo de tela**, não regra — mas quem responde
   qual setor é esse é o Lucas. Fica como está, marcado no código.
