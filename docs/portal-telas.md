# As telas do portal — o que cada view do Airtable virou, e o que ainda falta

> Escrito pelo DEV do portal em 03/09/2026, contra `docs/views-e-interfaces.md`.
> A regra de leitura: **view do Airtable é fila de trabalho**, e cada fila viva
> precisa de um lugar aqui. View que é cópia, teste ou lixo (o nome diz:
> "Kauê (Apagar depois)", "GridView_TableTEST", "Grid 17") não vira tela —
> vira nota de rodapé.
>
> O que o portal faz hoje: **lê e move**. Criar ficha nova pelo portal é a
> próxima rodada, e a tela de Início diz isso em voz alta, porque sem dizer a
> taxa de conversão do primeiro mês mentiria.

## As telas que existem

| Rota | O que é | Recorte e contadores |
|---|---|---|
| `/entrar`, `/senha` | Entrada e troca de senha. A senha nasce provisória e o sistema não deixa andar para outra tela antes da troca | — |
| `/` **Início** | O que faz parar hoje (`agora.py`, teto 6) + os contadores por fase, cada um link para a fila | tudo conta dentro do recorte de quem está logado |
| `/clientes` **Funil do cliente** | A fila por etapa da máquina CLIENTE | filtros: etapa, setor da etapa, quem cuida, captador, origem do lead, só em aberto, busca por nome/CPF |
| `/clientes/{id}` **Ficha do cliente** | Uma coluna: identidade, trilha de etapas com `<dialog>`, pendências, entrevista, processos, testemunhas, documentos e peças, trabalho, anotações, histórico | — |
| `/processos` **Processos** | A fila por fase da máquina PROCESSO | filtros: fase, TRT, vara, advogado, reclamada, rito, complexidade, situação da execução, e as filas de qualidade |
| `/processos/{id}` **Ficha do processo** | Trilha, audiências, prazos, perícias, decisões, recursos, dinheiro, pendências, testemunhas, fragilidades da reclamada, alias e divergências, histórico | — |
| `/audiencias` **Pauta** | Lista e semana lado a lado, do mesmo recorte | filtros: janela de dias, situação, tipo, responsável |
| `/audiencias/{id}` | Ficha da audiência com o **checklist de preparação** e a trilha da máquina AUDIÊNCIA | — |
| `/prazos` **Prazos** | Abertos por vencimento, com os dias **úteis** que faltam | filtros: situação, tipo, origem, responsável |
| `/empresas` **Reclamadas** | Lista com processos, em aberto e teses | filtros: situação, histórico de pagamento, busca |
| `/empresas/{id}` | Ficha: onde estão os processos, fragilidades, testemunhas, recebido | — |
| `/testemunhas` | Por situação, reclamada e canal (jurídico / comercial) | filtros: situação, reclamada, canal, busca |
| `/testemunhas/{id}` | Em que casos serve, contatos, auditoria do formulário interno | — |
| `/conferencias` | A fila de divergências, com **os dois valores lado a lado**, o trecho de prova, dono e situação | filtros: tipo, entidade, dono, situação |
| `/tarefas` | As tarefas, com a carga da equipe | filtros: minhas / sem dono / do escritório, setor, tipo, situação |
| `/equipe` | Quem é quem, papéis da origem, chefia, carga, quem tem acesso | — |
| `/fluxos` **Governança** | O mapa como o banco o guarda: etapas, transições, gates, textos de bloqueio, tipos de prazo, automações e o rastro de execução | — |
| `/painel` | Onde estão os casos, o que passou do SLA, onde se ganha e perde, dinheiro, TRTs, incidentes | — |
| `/mover/{entidade}/{id}` | **A porta única** por onde a etapa muda, para as cinco máquinas | — |
| `/saude`, `/api/agora` | Healthcheck e o contador do topo | — |

## View do Airtable → onde ela vive agora

### PRE PROCESSUAL (15 views)

| View | Onde está agora |
|---|---|
| LISTA GERAL, GERAL | `/clientes` sem filtro |
| DOCUMENTAÇÃO, DOCs AGRUPADO, DOCUMENTACAO V2 | `/clientes?status=DOCUMENTACAO`, e as pendências abertas na ficha. As três eram a mesma fila em três versões |
| ENTREVISTA (+ copy, copy 2) | `/clientes?status=ENTREVISTA` |
| PETIÇÃO INICIAL | quatro filas separadas, que é o que o Airtable misturava numa: `?status=PETICAO_PENDENTE`, `PETICAO_EM_CRIACAO`, `PETICAO_AGUARDANDO_APROVACAO`, `PETICAO_APROVADA`. O gargalo (54 esperando aprovação contra 6 em redação) fica visível sem contar à mão |
| CONCLUIDAS/DISTRIBUIDAS | `/clientes?status=DISTRIBUIDO` |
| CANCELADOS | `/clientes?status=CANCELADO` |
| Dashboard inicial (a única interface) | `/` e `/painel`. O número grande, a pizza por status da inicial e as barras por responsável viraram os contadores por etapa e por dono, cada um clicável para a fila — porque contador que não leva à fila é enfeite |
| HISTORICO MENSAGENS | **falta** — ver abaixo |
| gerencia's List | `/tarefas?quem=...`, `/clientes?responsavel=...` |
| GridView_TableTEST, Kauê (Apagar depois) | não viraram tela. O nome delas pede |

### PROCESSUAL e CÓPIA DA PROCESSUAL (27 + 37 views)

| View | Onde está agora |
|---|---|
| GERAL, GERAL PISCINA | `/processos` sem filtro |
| CONHECIMENTO, RECURSAL, EXECUÇÃO PROVISÓRIA, EXECUÇÃO DEFINITIVA, EXECUÇÕES | `/processos?fase=…` — e "EXECUÇÃO" sem qualificação deixou de existir, como o arquiteto decidiu |
| AUDIENCIAS, PAUTA CALENDARIO | `/audiencias` (a lista e a semana, na mesma tela e no mesmo recorte) |
| Acordos, ACORDOS-privado | `/processos?fase=ACORDO`, e as parcelas na ficha. A visão "privada" era o mesmo dado com colunas de dinheiro: aqui o dinheiro está na ficha, e quem vê a ficha vê |
| ARQUIVADOS, DESISTÊNCIA | `/processos?fase=ENCERRADO`, `?fase=DESISTENCIA`, e `resultado_final` no painel |
| ROUBADOS, RECUPERADOS, REVOGAÇÃO, RECEBIDO POR ELES | o bloco **Incidente de representação** na ficha do processo, e a contagem no painel. Deixou de ser status do processo: o processo continua em juízo, com outro patrono |
| REDISTRIBUIR, sobrestado | `/processos?fase=SOBRESTADO`; redistribuição fica em `processos.redistribuido_de` |
| SEM EMPRESA, SEM N PROCESSO, SEM VALORES | os três chips de **qualidade do cadastro** em `/processos` |
| sem data de nascimento | **falta** — não há tela de aniversário ainda |
| CLASSIFICAÇÃO SUMARISSIMO | `/processos?rito=SUMARISSIMO` e o chip de complexidade |
| PROCESSOS POR ANO, Distribuição | **falta** — o painel mostra por TRT e por fase, não por ano |
| AD VIDEOS | o item do checklist na ficha da audiência. A view está morta na origem (0 datas) e o que é "ad video" é [CONFIRMAR] |
| Ausencias | `audiencias.motivo = AUSENCIA_RECLAMANTE`, contado no painel — é perda evitável (CLT art. 844) e precisa ser medida |
| DADOS ZAPSIGN | **falta** — o contrato assinado é o gate `contrato_assinado`, mas a integração não entrou |
| Sem Astrea, sem drive, nome e empresa, GERAL-BOLINHO, GGVeVC View, Grid 17, gerencia's Grid 1/2/3 | não viraram tela. São recortes de trabalho de uma pessoa ou lixo |

### As outras tabelas

| View | Onde está agora |
|---|---|
| EMPRESAS | `/empresas` e `/empresas/{id}` |
| FRAGILIDADES | dentro da ficha da reclamada, e no processo (a tese repete por empregador) |
| TESTEMUNHAS: PLANILHA GERAL (+copy) | `/testemunhas` |
| TESTEMUNHAS: MENSAGENS ENVIADAS | **falta** |
| AUDITORIA (testemunhas) | dentro da ficha da testemunha |
| FUNCIONARIOS (3 views) | `/equipe` |
| PÓS PROCESSUAL | o bloco **Dinheiro** na ficha do processo (recebimentos, repasse) e o painel. A tabela é quase vazia na origem: o pós-processual está desenhado e não é praticado |
| Conferência de Faltantes (4 views) | **parcial**: `/conferencias` diz quantos são; a mesa de validação em si falta |

### Os formulários da origem

| Formulário | Onde está agora |
|---|---|
| Cadastro de Cliente - Processo Trabalhista | **falta**. É o caminho de entrada do passivo, e ele pede FASE e STATUS obrigatórios com as opções poluídas — reproduzi-lo como está seria reproduzir o problema |
| Cadastro de Funcionários | **falta** (o cadastro de pessoa é por `equipe.py` e `auth.py equipe`) |
| Cadastro de Testemunha (jurídico) e COMERCIAL | **faltam**. O comercial tem os rótulos trocados na origem (o campo "etapa processual" é o link para a PRÉ e vice-versa); refazer aqui é a chance de acertar |

## O que falta, em ordem de quem sente a falta primeiro

1. **Criar ficha** — lead, cliente, processo, audiência, prazo, testemunha,
   pendência de processo, decisão, acordo, recebimento. Hoje o portal lê e move;
   quem cadastra é a migração. Sem isso a etapa `LEAD` não passa a existir e a
   conversão continua sem numerador.
2. **A mesa de faltantes do Datajud** (1.067 linhas, 0 validadas, e a automação
   prometida na origem nunca existiu).
3. **Publicações do DEJT** — a entrada dos prazos. Hoje `prazos.origem` já
   prevê `DEJT`, `prazo_legal.py` sabe contar, e não há quem leia o diário.
   É o buraco mais fundo: publicação não lida é prazo correndo sem ninguém saber.
4. **Mensagens enviadas** (WhatsApp/Lailla): as views HISTORICO MENSAGENS e
   MENSAGENS ENVIADAS não têm equivalente. `contatos` já é a tabela certa.
5. **Aniversário e qualidade de cadastro do cliente** (a view "sem data de
   nascimento" alimentava isso).
6. **Gestão por período**: processos por ano, distribuição por mês, conversão
   por captador e por campanha.
7. **A agenda no Google** — o módulo está copiado e faltam duas colunas.
