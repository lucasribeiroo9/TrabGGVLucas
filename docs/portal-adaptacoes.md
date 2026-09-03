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
