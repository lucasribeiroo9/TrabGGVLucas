# Etapa ou atributo — o destino de cada opção de select do Airtable

> Regra do arquiteto: **toda opção que é etapa no Airtable aparece no mapa (`governanca.sql`) ou é
> declarada atributo aqui**, com o porquê. Cobre os selects de PRE PROCESSUAL, PROCESSUAL (com o que a
> CÓPIA acrescentou) e PÓS PROCESSUAL. Opções poluídas (texto digitado que virou opção) estão agrupadas
> na linha "lixo" de cada campo e vão para `airtable_bruto` na migração, nunca para uma etapa.
> Contagens são as de `dicionario-dados.md` (03/09/2026).

Legenda do destino: **etapa** = valor de uma coluna governada (`clientes.status`, `processos.fase`,
`audiencias.situacao`, `prazos.situacao`, `incidentes.situacao`) · **atributo** = coluna com CHECK, sem
gatilho de transição · **derivado** = não se grava, calcula-se de um fato registrado · **evento** =
linha em tabela filha com data · **tarefa** = vira tarefa com dono e prazo · **lixo** = não migra como
valor (fica em `airtable_bruto`).

## PRE PROCESSUAL

### ETAPA PRE PROCESSUAL (a etapa-mãe)

| opção | destino | justificativa |
|---|---|---|
| DOCUMENTAÇÃO (19) | **etapa** `DOCUMENTACAO` | Mesma coisa, mesmo dono (Documentação). |
| ENTREVISTA (42) | **etapa** `ENTREVISTA` | Idem. |
| PETIÇÃO INICIAL (147) | **etapa** — uma das quatro `PETICAO_*`, escolhida pelo STATUS PETICAO INICIAL | A petição é o gargalo (54 aguardando aprovação); uma etapa só escondia isso. Os 40 registros com petição DISTRIBUIDA e etapa ainda em PETIÇÃO INICIAL vão para `DISTRIBUIDO`. |
| CONCLUÍDO (452) | **etapa** `DISTRIBUIDO` | "Concluído" não diz o que aconteceu; "distribuído" diz. Os 3 CONCLUÍDOS com petição só APROVADA ficam em `PETICAO_APROVADA` e a migração anota a divergência. |
| CANCELAMENTO (137) | **etapa** `CANCELADO` (+ `motivo`) | O motivo vem do status que tinha DESISTÊNCIA (ver abaixo). |
| *(não existe)* | **etapa** `LEAD` | O Airtable só recebe a pessoa depois de assinar; o portal precisa da fase anterior [CONFIRMAR pergunta 5]. |
| *(não existe)* | **etapa** `STAND_BY`, `SEM_RESPOSTA`, `PRESCRITO` | Saídas que hoje estão espalhadas em STATUS ENTREVISTA e STATUS PETICAO e viram etapa da ficha inteira. |

### STATUS DOCUMENTAÇÃO

| opção | destino | justificativa |
|---|---|---|
| PENDENTE (32) · AGUARDANDO (9) · PARCIAL (4) · TRATAMENTO (5) · COMPLETA (555) | **derivado** de `documentos_pendentes` (quantos obrigatórios recebidos/dispensados) | Cinco graus de "quanto falta" não são caminho, são contagem. Quem cobra documento precisa da lista, não do rótulo. COMPLETA = gate `documentos_obrigatorios` da transição DOCUMENTACAO → ENTREVISTA. TRATAMENTO [CONFIRMAR o que significa] entra como flag `em_tratamento` se for etapa de trabalho interno. |
| DESISTÊNCIA (92) | **etapa** `CANCELADO` com `motivo = DESISTENCIA` | A automação nº 3 já fazia isso (desistência em qualquer status → CANCELAMENTO). |

### STATUS ENTREVISTA

| opção | destino | justificativa |
|---|---|---|
| PENDENTE (3) | **etapa** `ENTREVISTA` sem evento agendado | É a etapa recém-aberta. |
| PRIMEIRO / SEGUNDO / TERCEIRO CONTATO (2/0/0) | **atributo** `clientes.contatos_entrevista` (contador) + **evento** em `contatos` (data, canal, quem) | Três estados que só dizem "quantas vezes liguei" e que ninguém usa (2 registros). Como contador, o alerta "3 contatos sem resposta" continua possível e ainda ganha data. |
| ENTREVISTA AGENDADA (7) · REMARCAR (0) | **evento** `VISITA`/`ENTREVISTA` na agenda (`eventos`, com `status AGENDADO/REMARCADO/REALIZADO`) | Agendar não muda a etapa da pessoa; muda a agenda. Remarcar é o mesmo evento com nova data. |
| ENTREVISTA-OK (448) | **transição** ENTREVISTA → PETICAO_PENDENTE (gate `entrevista_registrada`) | "OK" é o fato que destrava a petição, não um lugar onde se fica. |
| STAND-BY (2) | **etapa** `STAND_BY` | Promovida a etapa da ficha, porque a pessoa toda para, não só a entrevista. |
| SEM RESPOSTA (17) | **etapa** `SEM_RESPOSTA` | Idem. |
| DESISTÊNCIA (113, com espaço) | **etapa** `CANCELADO` com motivo DESISTENCIA | Idem à documentação. |
| `0`, `ok`, `ag`, `SEM` | **lixo** | Digitação livre; nenhum registro usa. |

### STATUS PETICAO INICIAL

| opção | destino | justificativa |
|---|---|---|
| PENDENTE (41) | **etapa** `PETICAO_PENDENTE` | Sem redator ainda. |
| EM CRIAÇÃO (6) | **etapa** `PETICAO_EM_CRIACAO` | |
| AGUARDANDO APROVAÇÃO (54) | **etapa** `PETICAO_AGUARDANDO_APROVACAO` (grupo Gestão) | O gargalo ganha dono e SLA (2 dias). [CONFIRMAR pergunta 8: quem aprova.] |
| APROVADA (5) | **etapa** `PETICAO_APROVADA` | |
| VALIDAÇÃO (0) | **descartada** | Nunca usada; se for "revisão antes de aprovar", é a própria AGUARDANDO_APROVACAO. |
| DISTRIBUIDA (486) | **etapa** `DISTRIBUIDO` (gate `numero_cnj`) | Distribuir é o fim do funil e o nascimento do processo. |
| DESISTENCIA (100) | **etapa** `CANCELADO` com motivo | |
| PRESCRITO (2) | **etapa** `PRESCRITO` | Saída própria, porque é a perda que precisa ser contada à parte. |

### Demais selects da PRÉ

| campo / opção | destino | justificativa |
|---|---|---|
| URGENCIA = RI (84) | **derivado** de `rescisao_modalidade = RESCISAO_INDIRETA` | Marcar duas vezes o mesmo fato é o que fez as automações 4 e 5 brigarem. A urgência sai da modalidade. |
| URGENCIA = PRESCRIÇÃO (130) | **derivado** de `data_demissao + 2 anos − hoje ≤ 30` (view `v_pre_processual_atrasado`) | A fórmula "prescrição próxima" já fazia isso. |
| URGENCIA = URGENCIA ALTA (133) | **derivado** (RI ou prescrição ≤ 30 dias) | Idem. |
| URGENCIA = checked (4) | **lixo** | Resto de importação. |
| STATUS_NOTIFICACAO_PRESCRICAO / _RI | **log** em `automacao_log` (o que o n8n avisou, quando) | É rastro de automação, não estado da pessoa. Migra para o log com a data que tiver. |
| FONTE (14 opções) | **atributos** `canal` (Indicação, Site, Facebook, Instagram, Disparo) + `campanha` (texto: PROJETO PUXADA…) | Canal e campanha misturados; três grafias de Indicação [CONFIRMAR pergunta 12]. |
| PENDENCIAS (CNH/RG, CTPS, TRCT, DOCS. MÉDICOS, PROVAS, FGTS, HOLERITES, PIS) | **linhas** em `documentos_pendentes` (tipo, obrigatório, recebido_em, dispensado_motivo) | A lista de documentos do caso trabalhista vira tabela: é o que o gate lê. HOLERITE/HOLERITES fundem; OK e DOCUMENTAÇÃO OK são lixo. [CONFIRMAR pergunta 7: a marca hoje é "pedido" ou "falta".] |
| RESCISAO (texto livre) | **atributo** `rescisao_modalidade` CHECK (SEM_JUSTA_CAUSA, JUSTA_CAUSA, PEDIDO_DEMISSAO, RESCISAO_INDIRETA, CONTRATO_VIVO, ACORDO_484A, OUTRA) | Muda os pedidos possíveis e a urgência; não muda o caminho. `CONTRATO_VIVO` cobre "contrato em aberto" e a RI: sem data de demissão não há prescrição correndo. |
| PERICIA MEDICA / PERICIA INSALUB-PERIC | **atributos** booleanos do caso | Marcados na entrevista; viram perícia no processo. |
| AVISOS (🟡/🔴) | **derivado** (`v_pre_processual_atrasado.farol`) | Número na tela sai de consulta. |

## PROCESSUAL (e o que a CÓPIA acrescentou)

### FASE PROCESSUAL

| opção | destino | justificativa |
|---|---|---|
| CONHECIMENTO (1.343 / CÓPIA 572) | **etapa** `CONHECIMENTO` | |
| RECURSAL (227 / 498) | **etapa** `RECURSAL` | |
| EXECUÇÃO PROVISÓRIA (140 / 10) | **etapa** `EXECUCAO_PROVISORIA` | Quem tem Nº CumPrSe. Quando também está RECURSAL, a fase é esta (ver `governanca.sql`, fluxo 2). |
| EXECUÇÃO DEFINITIVA (74 / 10) | **etapa** `EXECUCAO_DEFINITIVA` | |
| EXECUÇÃO (125 / 72) | **migração decide**: `EXECUCAO_PROVISORIA` se há Nº CumPrSe e não há trânsito; senão `EXECUCAO_DEFINITIVA` | "Execução" sem qualificação é o que o script punha sem saber qual. O sistema não tem etapa "não sei". Casos sem nenhum dos dois fatos ficam DEFINITIVA com `conferencia` aberta. |
| ACORDO (119 / 14) | **etapa** `ACORDO` | |
| RECEBENDO (2 / 1) | **etapa** `RECEBENDO` | Quase não usada no Airtable porque o dinheiro não era acompanhado; aqui é a fase do repasse. |
| ENCERRADO (478 / 2.541) | **etapa** `ENCERRADO` (+ `resultado_final`) | |
| DESISTENCIA (28 / 1) | **etapa** `DESISTENCIA` | Saída própria: é homologação de desistência, não arquivamento. |
| INAPLICÁVEL (CÓPIA, 3) | **não migra como processo** — fica em `airtable_bruto` com marca | Não é processo trabalhista nosso. |
| *(não existe)* | **etapa** `SOBRESTADO` | Promovido de STATUS DO PROCESSO, porque suspende tudo e precisa saber para onde volta. |

### STATUS DO PROCESSO (o campo que misturava tudo)

| opção | destino | justificativa |
|---|---|---|
| AGUARDANDO AUDIÊNCIA (469) | **derivado**: existe `audiencias` DESIGNADA/EM_PREPARACAO futura | Espera não é etapa; é o próximo evento da agenda. |
| AGUARDANDO SENTENÇA (28) | **derivado**: instrução encerrada (audiência REALIZADA com `resultado = INSTRUCAO_ENCERRADA`) e sem `decisoes.SENTENCA` | Idem. |
| AGUARDANDO ACORDAO (CÓPIA, 129) | **derivado**: fase RECURSAL sem `decisoes.ACORDAO` | Idem. |
| TRÂNSITO EM JULGADO (35) | **fato** `processos.transito_em` (gate `transito_registrado`) | É uma data, e é ela que abre a execução definitiva. |
| EXECUCAO (287) | **etapa** `EXECUCAO_*` | Redundante com a fase. |
| ACORDO (78) | **etapa** `ACORDO` | Idem. |
| ARQUIVADO (444 / 2.549) | **etapa** `ENCERRADO` com `resultado_final = ARQUIVADO` | Arquivamento definitivo judicial é um dos jeitos de encerrar [CONFIRMAR pergunta 28]. |
| DESISTENCIA (27) | **etapa** `DESISTENCIA` | |
| ROUBADO (66 / 124) | **incidente** tipo `TROCA_DE_ADVOGADO`, situação `DETECTADO` (ou `NOTIFICADO` se NOTIFICAÇÃO = REDIGIDA/ENVIADA) | O processo continua em juízo; o que muda é a nossa representação. Fluxo 5. |
| RECEBIDO POR ELES (38 / 29) | **incidente** situação `PERDIDO` | O outro escritório recebeu; honorários perdidos, salvo cobrança. |
| RECUPERADO (18 / 21) | **incidente** situação `RECUPERADO` | |
| REDISTRIBUIR (1) | **tarefa** "redistribuir" no processo ENCERRADO, que ao ser feita cria processo novo com `redistribuido_de` | Redistribuir é uma ação, não um lugar. O processo velho fica encerrado (arquivado); o novo nasce em CONHECIMENTO. |
| SOBRESTADO (11 / 12) | **etapa** `SOBRESTADO` | |
| INAPLICÁVEL (CÓPIA, 3) | **não migra** | |

### STATUS CONHECIMENTO

| opção | destino | justificativa |
|---|---|---|
| AGUARDANDO AUDIÊNCIA (521) | **derivado** da agenda de audiências | Como acima. |
| ADVIDEO (0) | **derivado**: audiência futura com `advideo_em` vazio e `advideo_previsto` | Ad video é item do checklist da audiência [CONFIRMAR pergunta 14: o que é]. |
| AGUARDANDO PERICIA (5) | **derivado**: `pericias` com `data` futura e sem `laudo_em` | Perícia vira tabela (tipo MEDICA/TECNICA/CONTABIL, data, laudo, prazo de manifestação). |
| AGUARDANDO SENTENÇA (28) | **derivado** | Como acima. |
| SENTENCIADA (545 / 1.687) | **fato** `decisoes` tipo SENTENCA (data, resultado objetivo, nota) — gate `sentenca_registrada` | A sentença é o fato que destrava recurso e execução. |
| ACORDO EM ANDAMENTO (15 / 32) | **etapa** `ACORDO` | |
| AUSÊNCIA (17 / 126) | **evento**: audiência `NAO_REALIZADA` com `motivo = AUSENCIA_RECLAMANTE` + processo `ENCERRADO` com `resultado_final = ARQUIVADO_AUSENCIA` (art. 844 CLT) | É perda evitável e precisa ser medida por captador/entrevistador — por isso fica no motivo da audiência, não escondida num status. |
| DESISTÊNCIA (36 / 219) | **etapa** `DESISTENCIA` | |
| ARQUIVADO (CÓPIA, 46) | **etapa** `ENCERRADO` resultado ARQUIVADO | |

### STATUS RECURSAL

| opção | destino | justificativa |
|---|---|---|
| AGUARDANDO JULGAMENTO (91 / 414) | **derivado**: há `recursos` pendente com `grau = TRT` | O grau sai do recurso registrado (RO/contrarrazões → TRT). |
| TST (154 / 811) | **derivado**: `recursos` pendente com `grau = TST` (RR, AIRR, embargos) | Idem. Uma tabela `recursos` (tipo, de quem, interposto_em, resultado, julgado_em) responde também à pergunta 22 (recurso de quem). |

### STATUS CumPrSe

| opção | destino | justificativa |
|---|---|---|
| AGUARDANDO SENTENÇA (1) · DECISÃO POSITIVA EM 1ª / 2ª INSTÂNCIA (1/1) | **atributo** `situacao_execucao` = `AGUARDANDO_TRANSITO` + fatos em `decisoes` | O cumprimento provisório espera o recurso; a decisão positiva é o acórdão registrado. |
| PERICIA CONTÁBIL (1) | **atributo** `situacao_execucao = AGUARDANDO_PERICIA_CONTABIL` | |
| FASE DE CÁLCULOS (9) | **atributo** `situacao_execucao = CALCULOS_APRESENTADOS` | |
| RECEBIDO (5) | **atributo** `situacao_execucao = RECEBIDO` → transição para `RECEBENDO` | |
| ACORDO (0) | **etapa** `ACORDO` | |
| SOBRESTADO (1) | **etapa** `SOBRESTADO` | |

Decisão: **STATUS CumPrSe não é sub-máquina própria.** Tem 19 registros e repete os estados da execução; a execução provisória usa a mesma `situacao_execucao` da definitiva. O que a distingue é a fase (`EXECUCAO_PROVISORIA`) e o `numero_cumprse`.

### STATUS DO CALCULO

| opção | destino | justificativa |
|---|---|---|
| PENDENTE (10 / 11) | **atributo** `situacao_execucao = AGUARDANDO_CALCULO` | |
| JUNTADO AOS AUTOS (13 / 37) | **atributo** `situacao_execucao = CALCULOS_APRESENTADOS` + fato `calculos` (RCTE, RCDA, data) e prazo `IMPUGNACAO_CALCULOS` (8 dias, art. 879 §2º) | Juntar cálculo abre prazo — é prazo, não status. |
| HOMOLOGADO (178 / 616) | **atributo** `situacao_execucao = HOMOLOGADO` + fato `calculos.homologado_em` e `valor_hom` | |

Decisão: **o cálculo não é sub-máquina; é a tabela `calculos`** (quem apresentou, valor, sucumbência embutida, homologado em, valor homologado). Os três estados são a presença de três fatos.

### STATUS EXECUÇÃO — a lista limpa da CÓPIA (16) vira o CHECK de `processos.situacao_execucao`

Decisão de desenho: **atributo com lista fechada e ordenada, não sub-máquina governada.** A execução não é linear — bens, acordo, alvará e recurso se alternam — e uma máquina com 16 estados e ~60 transições seria recusar mudança legítima todo dia. O que precisa de gatilho está nas transições da fase (`valor_recebido`, `acordo_registrado`) e nos prazos. A ordem sugerida (pergunta 18) está na coluna "ordem".

| opção (CÓPIA) | ordem | destino | justificativa |
|---|---|---|---|
| AGUARDANDO TRANSITO (47) | 1 | **atributo** `AGUARDANDO_TRANSITO` | Só faz sentido na provisória. |
| AGUARDANDO CÁLCULO (302) | 2 | **atributo** `AGUARDANDO_CALCULO` | O maior grupo: sentença liquidável, ninguém apresentou conta. |
| FASE DE CÁLCULOS (50) | 3 | **atributo** `CALCULOS_APRESENTADOS` | |
| AGUARDANDO PERICIA (6) | 4 | **atributo** `AGUARDANDO_PERICIA_CONTABIL` | |
| HOMOLOGADO (57) | 5 | **atributo** `HOMOLOGADO` | |
| RECURSO EXECUÇÃO (82) | 6 | **prazo/recurso** tipo `AGRAVO_PETICAO` + atributo `EM_RECURSO_EXECUCAO` | O agravo de petição é um recurso com prazo (8 dias, art. 897, a). O atributo diz "parado esperando o AP". |
| PROCURANDO BENS (29) | 7 | **atributo** `PESQUISA_PATRIMONIAL` | Sisbajud, Renajud, Infojud. |
| NEGOCIANDO ACORDO (1) | 8 | **atributo** `NEGOCIANDO_ACORDO` | Se fechar, a fase vira ACORDO. |
| AUDIÊNCIA CONCILIAÇÃO (3) | 9 | **evento**: audiência tipo `CONCILIACAO_EXECUCAO` | É audiência; entra no fluxo 3. |
| PARCELAMENTO 916 CPC (9) | 10 | **atributo** `PARCELAMENTO_916` + parcelas em `acordo_parcelas` | 30% à vista e até 6 parcelas (CPC art. 916) — controverso na Justiça do Trabalho [CONFIRMAR se o escritório aceita]. |
| AGUARDANDO ALVARÁ (22) | 11 | **atributo** `AGUARDANDO_ALVARA` | Dinheiro depositado, falta liberar. |
| RECEBIDO (14) | 12 | **transição** → fase `RECEBENDO` (gate `valor_recebido`) | Receber muda de fase, não de status interno. |
| ARQUIVADO (144) | — | **etapa** `ENCERRADO` com resultado `ARQUIVADO` (definitivo) ou `ARQUIVADO_PROVISORIO` (art. 11-A CLT, prescrição intercorrente correndo) | Arquivamento provisório sem bens não é fim: em 2 anos prescreve (art. 11-A). Por isso o resultado distingue. |
| EXTINTA S/ RESOLUÇAO (23) | — | **etapa** `ENCERRADO` com resultado `EXTINTA_SEM_RESOLUCAO` | |
| SOBRESTADO (4) | — | **etapa** `SOBRESTADO` | |
| EXECUÇAO PROVISÓRIA (17) | — | **etapa** `EXECUCAO_PROVISORIA` | É fase, estava no lugar errado. |
| as 20 opções poluídas da PROCESSUAL (`SIM `, `NÃO `, `PESQUISA `, `Discutindo cálculos. `, três grafias de FASE DE CÁLCULO(S), `LIQUIDAÇAO`, `Homologado. `, `ALVARA`, `EXECUÇÃO`, `RECURSAL`, `Aguardando laudo contabil `…) | — | **migração traduz** para o estado limpo mais próximo quando é óbvio (PESQUISA → PESQUISA_PATRIMONIAL, Discutindo cálculos → CALCULOS_APRESENTADOS, ALVARA → AGUARDANDO_ALVARA, laudo contábil → AGUARDANDO_PERICIA_CONTABIL); `SIM`/`NÃO`/`EXECUÇÃO`/`RECURSAL` viram NULL + `conferencia` | Nada de inventar: o que não dá para traduzir fica em branco com conferência aberta e o texto original em `airtable_bruto`. |

### STATUS ACORDO

| opção | destino | justificativa |
|---|---|---|
| ACORDO EM ANDAMENTO (21 / 61) | **etapa** `ACORDO` | |
| ACORDO CUMPRIDO (102 / 1.317) | **transição** ACORDO → RECEBENDO (gate `parcelas_quitadas`) e depois ENCERRADO | Cumprido é fato: última parcela paga. |
| QUEBRA DE ACORDO (3 / 4) | **transição** ACORDO → EXECUCAO_DEFINITIVA ("Quebra de acordo: executar") + `acordos.quebrado_em` | O script já fazia; aqui fica com motivo e data. |

### STATUS PAGAMENTO

| opção | destino | justificativa |
|---|---|---|
| PENDENTE · AGUARDANDO PAGAMENTO · PAGAMENTO EM DIA · PAGAMENTO ATRASADO · PAGO PARCIALMENTE · CONCLUIDO | **derivado** de `acordo_parcelas` (vencimento, pago_em, valor) e `recebimentos` | Seis rótulos para "quantas parcelas pagas e alguma atrasada?". Derivar da tabela de parcelas dá o alerta de atraso no dia certo, coisa que o select nunca deu. |
| PARCELAMENTO CPC (4 / 1) | **atributo** `situacao_execucao = PARCELAMENTO_916` | |
| CESSAO DE CREDITOS (CÓPIA, 3) | **atributo** `processos.credito_cedido_em` + `cessionario` | O cliente vendeu o crédito a terceiro: quem recebe muda, a fase não. Afeta o repasse. |

### AUDIENCIA (tipo) — vira `audiencias.tipo` + `audiencias.modalidade`

| opção | destino | justificativa |
|---|---|---|
| INICIAL (90 / 216) · INICIAL/VIDEO (64) | **atributo** `tipo = INICIAL`, `modalidade = PRESENCIAL / VIDEO` | Tipo e modalidade separados. |
| INSTRUÇÃO (110 / 867) · INSTRUCAO/VIDEO (144) | `tipo = INSTRUCAO` (+ modalidade) | |
| UNA (430 / 1.210) · UNA/VIDEO (90) | `tipo = UNA` (+ modalidade) | |
| UNA-RS (141) · UNA-RS/VIDEO (26) | `tipo = UNA` + `processos.rito = SUMARISSIMO` [CONFIRMAR pergunta 17: RS = rito sumaríssimo] | O rito é do processo, não da audiência. |
| HOMOLOGAÇÃO (4 / 0) | `tipo = HOMOLOGACAO` | |
| CONCILIAÇÃO EM EXECUÇÃO (118) | `tipo = CONCILIACAO_EXECUCAO` | |
| JULGAMENTO (22) | `tipo = JULGAMENTO` | Audiência de publicação de sentença; abre o prazo de RO na data (Súmula 197 TST). |
| DATA AUDIENCIA (uma por processo) | **linhas** em `audiencias` — a atual e as anteriores | O Airtable sobrescrevia; a redesignação vira linha nova ligada por `redesignada_de`. |

### STATUS ADVIDEO

| opção | destino | justificativa |
|---|---|---|
| PENDENTE · MARCADO · FEITO (1 uso) | **checklist** da audiência: `advideo_previsto` (bool), `advideo_agendado_em`, `advideo_em`, `advideo_responsavel_id` | Está vazio na base e o script dependia dele; como item da preparação, aparece no alerta de "audiência sem preparação" [CONFIRMAR pergunta 14]. |

### NOTIFICAÇÃO, REVOGAÇÃO, PROVIDENCIAS, CLIENTE AVISADO? (o incidente)

| opção | destino | justificativa |
|---|---|---|
| NOTIFICAÇÃO = PENDENTE · EM AVALIAÇÃO (4) | **incidente** `DETECTADO` | Ainda decidindo se notifica. |
| NOTIFICAÇÃO = REDIGIDA (61) | **incidente** `DETECTADO` + `notificacao_redigida_em` | Redigida e não enviada ainda é detectado. |
| NOTIFICAÇÃO = ENVIADA · RECEBIDA · RESPONDIDA (0) | **incidente** `NOTIFICADO` + datas `notificacao_enviada_em / recebida_em / resposta_em` | Enviar é a transição; receber e responder são datas. |
| REVOGAÇÃO = SIM (529 / 839) em processo normal | **atributo** `processos.revogou_patrono_anterior` (bool) + `data_revog` | Sentido 1: nós juntamos revogação do advogado anterior do cliente [CONFIRMAR pergunta 20]. |
| REVOGAÇÃO = SIM em processo ROUBADO | **atributo** `incidentes.revogacao_nos_autos_em` | Sentido 2: o cliente nos revogou. A migração usa o STATUS DO PROCESSO para decidir o sentido. |
| REVOGAÇÃO = NÃO (113) · NÃO SE APLICA (46) | **atributo** `revogou_patrono_anterior = false` / NULL | |
| REVOGAÇÃO = recados (`BRUNO - juntar revogaçao…`, `fazer revogaçao`, `VERIFICAR`, `ROUBADO`…) | **tarefa** ("juntar revogação nestes autos", dono Bruno quando o texto diz) + texto em `airtable_bruto` | Recado é tarefa. |
| PROVIDENCIAS = NOTIFICAR (66) | **transição** pendente do incidente (`DETECTADO → NOTIFICADO`) = **tarefa** "enviar notificação" | |
| PROVIDENCIAS = TRAVAR O RECEBIMENTO / TRAVAR ULTIMA PARCELA | **transição** → `HONORARIOS_RESERVADOS` = **tarefa** "pedir reserva de honorários (EOAB art. 22 §4º)" | |
| CLIENTE AVISADO? (9) | **atributo** `incidentes.cliente_avisado_em` | |

### AND. NECESSÁRIO

| opção | destino | justificativa |
|---|---|---|
| PEDIR ANDAMENTO · EXPEDIÇAO DE ALVARÁ · Alvará (3 grafias) · TENTAR ACORDO · PEDIR AUD CONCILIAÇÃO · Prosseguimento · os recados longos | **tarefa** com dono e prazo, texto original preservado | "Andamento necessário" é o próximo passo — é tarefa por definição. [CONFIRMAR pergunta 19.] |
| Encerrado (64) · ACORDO (1) | **nada** (redundante com a fase) | |

### Atributos que nunca foram etapa (só para constar)

| campo | destino |
|---|---|
| COMPLEXIDADE A/B/C | **derivado** do valor (C ≤ 150 mil, B ≤ 500 mil, A acima), com `complexidade_manual` que vence [CONFIRMAR pergunta 16] |
| CLASSIFICACAO (RT/AT ORDINÁRIO, SUMARÍSSIMO, SUMÁRIO) | **atributo** `processos.rito` (ORDINARIO, SUMARISSIMO, SUMARIO) + `classe_cnj` (RT/AT). As classes de incidente da CÓPIA (EXECUCAO PROVISORIA/DEFINITIVA, EMBARGOS DE TERCEIRO, RR, AIRR, RRAg, Emb) vão para `recursos.tipo` / `incidentes_processuais` — não são rito [CONFIRMAR pergunta 17] |
| TRT · TURMA · CADEIRA · RELATOR · TURMA TST · RELATOR TST | **atributos** do processo (`trt`, `turma`, `relator`) e do recurso no TST; a TURMA poluída da PROCESSUAL é lida da CÓPIA (texto limpo); número de processo digitado como turma é lixo |
| DECISAO SENTENCA (PROCEDENTE / PARCIALMENTE / IMPROCEDENTE / EXTINTO S-RES) · RESULTADO RECURSO (PROVIDO / PARCIALMENTE / NEGADO / NÃO CONHECIDO) | **fatos** em `decisoes.resultado_objetivo` |
| SENTENCA · RESULTADO ACORDAO · ULTIMA DECISAO (RUIM / MÉDIA / ÓTIMA) | **atributo** `decisoes.nota` — avaliação separada do resultado [CONFIRMAR pergunta 24]; ULTIMA DECISAO desaparece (é a decisão mais recente) e seus PROCEDENTE/IMPROCEDENTE vão para `resultado_objetivo` |
| BENS IDENTIFICADOS · HIST. PAGAMENTO · SITU. EMPRESA | **atributos da empresa** (`empresas`), não do processo — o processo só lê |
| SUCUMBENCIA % · CALCULO RCTE/RCDA · VALOR HOM · SUCUMB * · HONOR TOTAL · TOTAL RECEBIDO · VALOR ACORDO · PARCELAS | **valores** em `calculos`, `acordos`, `recebimentos` (centavos) |
| MOTIVO (1: "SEM TESTEMUNHA") | **lixo** → `airtable_bruto` |

## PÓS PROCESSUAL

Decisão: **o pós-processual não é máquina própria.** RECEBENDO e ENCERRADO do PROCESSO já cobrem recebimento e arquivo; o repasse é dinheiro e vira linha em `repasses`, exigida pelo gate `repasse_registrado` antes de encerrar. O arquivamento físico/Drive é tarefa que nasce ao encerrar. A tabela PÓS (556, 99 sem processo) migra para essas colunas do processo; os 99 órfãos ficam em `airtable_bruto` [CONFIRMAR pergunta 3].

| opção | destino | justificativa |
|---|---|---|
| STATUS RECEBIMENTO = Aguardando / Aguardando Recebimento / PENDENTE / AGUARDANDO PAGAMENTO | **derivado**: fase `EXECUCAO_*` ou `ACORDO` sem `recebimentos` | |
| Pago parcial / PAGO PARCIALMENTE / Parcialmente Recebido / PAGAMENTO EM DIA / PAGAMENTO ATRASADO | **derivado** de `acordo_parcelas` + `recebimentos` | |
| Pago total / Recebido / CONCLUIDO | **etapa** `RECEBENDO` (ou ENCERRADO, se o repasse já foi) | |
| Não Recebido | **etapa** `ENCERRADO` com resultado `SEM_RECEBIMENTO` (arquivado sem bens, improcedente…) | |
| PARCELAMENTO CPC | **atributo** `situacao_execucao = PARCELAMENTO_916` | |
| STATUS REPASSE (Aguardando / Aguardando Repasse / Efetuado / Repassado / Parcialmente Repassado / Não Repassado — 0 usos) | **derivado** de `repasses` (valor, data, comprovante, `sem_valor_motivo`) | Nunca foi preenchido; o gate `repasse_registrado` obriga daqui em diante [CONFIRMAR pergunta 26: aqui ou no financeiro]. |
| STATUS ARQUIVAMENTO = Em andamento (30) · Arquivado (37) · Não arquivado (0) | **tarefa** "arquivar pasta" criada ao entrar em ENCERRADO + `processos.arquivado_em` | Arquivo físico/Drive é providência, não fase [CONFIRMAR pergunta 28]. |
| EVENTOS · DATA DE ASSINATURA (0 usos) | **descartados** | Vazios em 100%. |

## Fora das três tabelas, mas com opções que viram estado em outro lugar

| campo | destino |
|---|---|
| TESTEMUNHAS.STATUS TESTEMUNHA (PENDENTE → A CONFIRMAR → CONFIRMADA; DESCARTADA, NAO USAR) | **atributo** `testemunhas.situacao` com CHECK — sem gatilho: cinco valores, caminho óbvio, e o que importa é `confirmada_em` para o checklist da audiência |
| TESTEMUNHAS.COBRANÇA (1º–4º) | **contador** `cobrancas` + evento `contatos` |
| TESTEMUNHAS.notif_captador_status | **log** de automação (é do n8n) |
| EMPRESAS.STATUS EMPRESA (ATIVA / INATIVA / EM RECUPERACAO) | **atributo** da empresa; EM RECUPERACAO alimenta o alerta de SOBRESTADO na execução |
| FRAGILIDADES.STATUS (Inédita / Acolhida / Acolhida em parte / Rejeitada / Em julgamento) | **atributo** da tese — é o `teses/*.md` do trabalhista, por empresa |
