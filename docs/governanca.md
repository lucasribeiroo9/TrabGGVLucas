# Governança — as cinco máquinas de estado do escritório trabalhista

> Gerado por `gerar_governanca.py` **a partir das tabelas** `fluxos`, `fluxo_etapas`,
> `fluxo_transicoes` e `prazo_tipos` (hoje lidas de `governanca.sql`). Não editar à mão:
> rode o script de novo depois de mexer no mapa. A prosa para o Lucas aprovar está em
> `governanca-para-confirmar.md`; o que cada opção do Airtable virou está em `etapa-ou-atributo.md`.

A regra não mora na tela nem no código. Mora no banco, e vale para qualquer caminho que
chegue até ele — sistema, script, migração ou mão humana no `psql`. Transição que não
estiver na tabela é recusada por gatilho, com `RAISE EXCEPTION`, não corrigida em silêncio.

**5 fluxos · 40 etapas · 111 transições · 18 tipos de prazo.**

---

## Funil do cliente (pré-processual) (`CLIENTE`)

Governa `clientes.status` · 12 etapas · 43 transições.

### 1. Lead (primeiro contato) — `LEAD`

| | |
|---|---|
| tipo | INICIAL |
| prazo interno (SLA) | 3 dias |
| setor responsável | Captação |

**O que fazer aqui:** Ligou ou veio pelo captador. Registre nome, telefone, empresa, função, data e modalidade da saída (ou se ainda trabalha). Sem contrato assinado não há caso.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Documentação** (`DOCUMENTACAO`) | Contrato assinado | qualquer | contrato_assinado | Falta o contrato de honorários e a procuração assinados, com data. Sem eles o escritório não representa ninguém. |
| **Sem resposta** (`SEM_RESPOSTA`) | Sem resposta | qualquer | — | — |
| **Stand by** (`STAND_BY`) | Colocar em stand by | qualquer | — | — |

### 2. Documentação — `DOCUMENTACAO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 7 dias |
| setor responsável | Documentação |

**O que fazer aqui:** Contrato e procuração assinados. Peça TRCT, CTPS, holerites, extrato do FGTS, RG/CNH e, se houver, documentos médicos e provas (conversas, fotos, escalas). Marque cada documento recebido.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Entrevista** (`ENTREVISTA`) | Documentação completa | qualquer | documentos_obrigatorios | Ainda falta documento obrigatório (TRCT, CTPS, RG/CNH). Marque cada um como recebido ou dispensado, com motivo. |
| **Prescrito** (`PRESCRITO`) | Prescrição consumada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Sem resposta** (`SEM_RESPOSTA`) | Sem resposta | qualquer | — | — |
| **Stand by** (`STAND_BY`) | Colocar em stand by | qualquer | — | — |

### 3. Entrevista — `ENTREVISTA`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 5 dias |
| setor responsável | Atendimento |

**O que fazer aqui:** Agende e realize a entrevista. Registre data, entrevistador e resumo; marque se o caso pede perícia médica ou técnica e arrole as testemunhas.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Documentação** (`DOCUMENTACAO`) | Voltar para documentação | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Petição a redigir** (`PETICAO_PENDENTE`) | Entrevista realizada | qualquer | entrevista_registrada | Registre a entrevista: data, entrevistador e resumo. É o que a petição vai usar. |
| **Prescrito** (`PRESCRITO`) | Prescrição consumada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Sem resposta** (`SEM_RESPOSTA`) | Sem resposta | qualquer | — | — |
| **Stand by** (`STAND_BY`) | Colocar em stand by | qualquer | — | — |

### 4. Petição a redigir — `PETICAO_PENDENTE`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 2 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Caso pronto para a inicial, ainda sem redator. Assuma ou distribua. Se a saída foi rescisão indireta, este caso tem prioridade: o contrato ainda está correndo.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Petição em redação** (`PETICAO_EM_CRIACAO`) | Começar a redigir | qualquer | — | — |
| **Prescrito** (`PRESCRITO`) | Prescrição consumada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Stand by** (`STAND_BY`) | Colocar em stand by | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 5. Petição em redação — `PETICAO_EM_CRIACAO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 3 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Redija a inicial. Se faltar informação, volte para entrevista; se faltar documento, para documentação — sem apagar o que já foi feito.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Documentação** (`DOCUMENTACAO`) | Falta documento | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Entrevista** (`ENTREVISTA`) | Falta informação: nova entrevista | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Petição aguardando aprovação** (`PETICAO_AGUARDANDO_APROVACAO`) | Enviar para aprovação | qualquer | minuta_anexada | Anexe a minuta da inicial na ficha. Não se aprova o que não está escrito. |
| **Prescrito** (`PRESCRITO`) | Prescrição consumada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 6. Petição aguardando aprovação — `PETICAO_AGUARDANDO_APROVACAO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 2 dias |
| setor responsável | Petição Inicial |

**O que fazer aqui:** A minuta espera o advogado da equipe de Petição Inicial (resposta 8 do Lucas: existe um setor próprio para cada etapa, e quem aprova a inicial é essa equipe — não a Gestão). Aprove ou devolva com o ajuste escrito. Este é o gargalo do funil hoje.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | ADVOGADO | setor_peticao_inicial,motivo | Aprovar, devolver ou cancelar a inicial é da equipe de Petição Inicial: só quem está nesse setor (pessoas.setor) tem a ação. Para aprovar, a minuta precisa estar anexada; para devolver ou cancelar, o motivo escrito. |
| **Petição aprovada, a distribuir** (`PETICAO_APROVADA`) | Aprovar a inicial | ADVOGADO | setor_peticao_inicial,minuta_anexada | Aprovar, devolver ou cancelar a inicial é da equipe de Petição Inicial: só quem está nesse setor (pessoas.setor) tem a ação. Para aprovar, a minuta precisa estar anexada; para devolver ou cancelar, o motivo escrito. |
| **Petição em redação** (`PETICAO_EM_CRIACAO`) | Devolver para ajuste | ADVOGADO | setor_peticao_inicial,motivo | Aprovar, devolver ou cancelar a inicial é da equipe de Petição Inicial: só quem está nesse setor (pessoas.setor) tem a ação. Para aprovar, a minuta precisa estar anexada; para devolver ou cancelar, o motivo escrito. |

### 7. Petição aprovada, a distribuir — `PETICAO_APROVADA`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 2 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Protocole no PJe e registre o número CNJ. É o registro do número que faz nascer o processo no sistema.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Distribuído (concluído)** (`DISTRIBUIDO`) | Registrar distribuição | ADVOGADO | numero_cnj,prescricao_viva | Informe o número CNJ com 20 dígitos. Se a prescrição bienal venceu, registre a dispensa justificada antes — sem isso o sistema não distribui. |
| **Petição em redação** (`PETICAO_EM_CRIACAO`) | Reabrir redação | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Prescrito** (`PRESCRITO`) | Prescrição consumada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 8. Stand by — `STAND_BY`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 60 dias |
| setor responsável | Atendimento |

**O que fazer aqui:** Parado por decisão da pessoa ou por fato que ainda vai amadurecer. Marque quando revisitar. A prescrição continua correndo.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Documentação** (`DOCUMENTACAO`) | Retomar documentação | qualquer | — | — |
| **Entrevista** (`ENTREVISTA`) | Retomar entrevista | qualquer | — | — |
| **Petição a redigir** (`PETICAO_PENDENTE`) | Retomar petição | qualquer | entrevista_registrada | Registre a entrevista: data, entrevistador e resumo. É o que a petição vai usar. |
| **Prescrito** (`PRESCRITO`) | Prescrição consumada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Sem resposta** (`SEM_RESPOSTA`) | Sem resposta | qualquer | — | — |

### 9. Distribuído (concluído) — `DISTRIBUIDO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** A inicial foi distribuída e o processo existe. O trabalho segue no ciclo do processo.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Documentação** (`DOCUMENTACAO`) | Novo caso da mesma pessoa | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 10. Cancelado — `CANCELADO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Atendimento |

**O que fazer aqui:** A pessoa desistiu ou o escritório não seguiu. O motivo fica registrado — é o que ensina a captação.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Documentação** (`DOCUMENTACAO`) | Reabrir o caso | GESTOR | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 11. Prescrito — `PRESCRITO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Passaram-se dois anos do fim do contrato sem ajuizar (CF art. 7º, XXIX; CLT art. 11). Registre o motivo — é perda evitável e precisa ser medida.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Petição a redigir** (`PETICAO_PENDENTE`) | Reanalisar prescrição | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 12. Sem resposta — `SEM_RESPOSTA`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Captação |

**O que fazer aqui:** Não retornou o contato. Pode ser reaberto se a pessoa procurar de novo.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cancelado** (`CANCELADO`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Entrevista** (`ENTREVISTA`) | Reabrir contato | qualquer | — | — |
| **Prescrito** (`PRESCRITO`) | Prescrição consumada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

---

## Ciclo do processo (`PROCESSO`)

Governa `processos.fase` · 9 etapas · 36 transições.

### 1. Conhecimento — `CONHECIMENTO`

| | |
|---|---|
| tipo | INICIAL |
| prazo interno (SLA) | 365 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Da distribuição à sentença. Acompanhe a pauta (audiência inicial, una ou de instrução), a defesa e a réplica, as perícias e as testemunhas. Registre a sentença assim que publicada: resultado, data e nota.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Acordo em cumprimento** (`ACORDO`) | Acordo homologado | qualquer | acordo_registrado | Registre o acordo: valor, número de parcelas, vencimentos e data da homologação. |
| **Desistência** (`DESISTENCIA`) | Desistência homologada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Encerrado** (`ENCERRADO`) | Encerrar | ADVOGADO | resultado | Informe o resultado final do processo antes de encerrar. |
| **Execução definitiva** (`EXECUCAO_DEFINITIVA`) | Trânsito em julgado favorável | ADVOGADO | sentenca_registrada,transito_registrado | Registre a sentença (resultado objetivo, data e nota) antes de mudar de fase — é isso que alimenta o mapa de onde estamos perdendo. |
| **Recursal** (`RECURSAL`) | Sentença publicada: recurso interposto | ADVOGADO | sentenca_registrada | Registre a sentença (resultado objetivo, data e nota) antes de mudar de fase — é isso que alimenta o mapa de onde estamos perdendo. |
| **Sobrestado** (`SOBRESTADO`) | Sobrestar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 2. Recursal — `RECURSAL`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 365 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Há recurso pendente — nosso, da reclamada ou de ambos. O grau (TRT ou TST) sai dos recursos registrados. Avalie o cumprimento provisório enquanto o recurso corre.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Acordo em cumprimento** (`ACORDO`) | Acordo homologado | qualquer | acordo_registrado | Registre o acordo: valor, número de parcelas, vencimentos e data da homologação. |
| **Conhecimento** (`CONHECIMENTO`) | Sentença anulada: volta à origem | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Desistência** (`DESISTENCIA`) | Desistência homologada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Encerrado** (`ENCERRADO`) | Trânsito desfavorável: encerrar | ADVOGADO | transito_registrado,resultado | Informe a data do trânsito em julgado e a decisão que transitou. |
| **Execução definitiva** (`EXECUCAO_DEFINITIVA`) | Trânsito em julgado favorável | ADVOGADO | transito_registrado | Informe a data do trânsito em julgado e a decisão que transitou. |
| **Execução provisória** (`EXECUCAO_PROVISORIA`) | Abrir cumprimento provisório | ADVOGADO | numero_cumprse | Informe o número do cumprimento provisório de sentença (CumPrSe). |
| **Sobrestado** (`SOBRESTADO`) | Sobrestar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 3. Execução provisória — `EXECUCAO_PROVISORIA`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 365 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Cumprimento provisório de sentença (CumPrSe) aberto enquanto a reclamada recorre: liquidação e penhora até a garantia do juízo (art. 899 CLT). Sem alvará antes do trânsito, salvo caução.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Acordo em cumprimento** (`ACORDO`) | Acordo homologado | qualquer | acordo_registrado | Registre o acordo: valor, número de parcelas, vencimentos e data da homologação. |
| **Desistência** (`DESISTENCIA`) | Desistência homologada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Encerrado** (`ENCERRADO`) | Encerrar | ADVOGADO | resultado | Informe o resultado final do processo antes de encerrar. |
| **Execução definitiva** (`EXECUCAO_DEFINITIVA`) | Trânsito em julgado | ADVOGADO | transito_registrado | Informe a data do trânsito em julgado e a decisão que transitou. |
| **Sobrestado** (`SOBRESTADO`) | Sobrestar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 4. Execução definitiva — `EXECUCAO_DEFINITIVA`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 365 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Trânsito em julgado favorável. Cálculo → impugnação (8 dias, art. 879 §2º) → homologação → bens (Sisbajud, Renajud, Infojud) → alvará. A situação interna está em situacao_execucao.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Acordo em cumprimento** (`ACORDO`) | Acordo na execução | qualquer | acordo_registrado | Registre o acordo: valor, número de parcelas, vencimentos e data da homologação. |
| **Desistência** (`DESISTENCIA`) | Desistência homologada | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Encerrado** (`ENCERRADO`) | Encerrar | ADVOGADO | resultado | Informe o resultado final do processo antes de encerrar. |
| **Recebendo** (`RECEBENDO`) | Valor liberado | qualquer | valor_recebido | Registre o valor efetivamente recebido, a data e o comprovante (alvará ou depósito). |
| **Sobrestado** (`SOBRESTADO`) | Sobrestar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 5. Acordo em cumprimento — `ACORDO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 365 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Acordo homologado, parcelas correndo. Acompanhe cada vencimento. Parcela atrasada é quebra: multa da cláusula penal e execução do saldo.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Encerrado** (`ENCERRADO`) | Encerrar | ADVOGADO | resultado | Informe o resultado final do processo antes de encerrar. |
| **Execução definitiva** (`EXECUCAO_DEFINITIVA`) | Quebra de acordo: executar | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Recebendo** (`RECEBENDO`) | Parcelas quitadas | qualquer | parcelas_quitadas | Há parcela do acordo sem pagamento registrado. Registre cada uma ou mude para quebra de acordo. |

### 6. Recebendo — `RECEBENDO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 30 dias |
| setor responsável | Financeiro |

**O que fazer aqui:** O dinheiro entrou (alvará ou última parcela). Separe honorários contratuais e sucumbência, registre o repasse ao cliente e o comprovante. Só depois se encerra.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Encerrado** (`ENCERRADO`) | Repasse feito: encerrar | qualquer | repasse_registrado | Registre o repasse ao cliente (valor, data, comprovante) ou marque que não há valor a repassar, com motivo. |
| **Execução definitiva** (`EXECUCAO_DEFINITIVA`) | Saldo a executar | ADVOGADO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 7. Sobrestado — `SOBRESTADO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Suspenso por decisão do juízo (tema repetitivo, IRR, recuperação judicial da reclamada). Registre o motivo e o que destrava; ao retomar, o processo volta à fase em que estava.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Conhecimento** (`CONHECIMENTO`) | Retomar | qualquer | retorna_fase_anterior | Sobrestado só volta para a fase em que estava antes. O histórico diz qual é. |
| **Encerrado** (`ENCERRADO`) | Encerrar | ADVOGADO | resultado | Informe o resultado final do processo antes de encerrar. |
| **Execução definitiva** (`EXECUCAO_DEFINITIVA`) | Retomar | qualquer | retorna_fase_anterior | Sobrestado só volta para a fase em que estava antes. O histórico diz qual é. |
| **Execução provisória** (`EXECUCAO_PROVISORIA`) | Retomar | qualquer | retorna_fase_anterior | Sobrestado só volta para a fase em que estava antes. O histórico diz qual é. |
| **Recursal** (`RECURSAL`) | Retomar | qualquer | retorna_fase_anterior | Sobrestado só volta para a fase em que estava antes. O histórico diz qual é. |

### 8. Encerrado — `ENCERRADO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Acabou: arquivamento definitivo, improcedência transitada, extinção, execução satisfeita. O resultado final fica registrado — é ele que mede onde o escritório ganha e perde.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Conhecimento** (`CONHECIMENTO`) | Reabrir | DIRECAO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Execução definitiva** (`EXECUCAO_DEFINITIVA`) | Reabrir execução | DIRECAO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 9. Desistência — `DESISTENCIA`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** O reclamante desistiu depois de ajuizar e o juízo homologou (art. 485, VIII, CPC; depois da defesa exige anuência da reclamada, art. 841 §3º CLT). Motivo obrigatório.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Conhecimento** (`CONHECIMENTO`) | Reabrir | DIRECAO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

---

## Audiência (`AUDIENCIA`)

Governa `audiencias.situacao` · 7 etapas · 12 transições.

### 1. Designada — `DESIGNADA`

| | |
|---|---|
| tipo | INICIAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Data marcada pelo juízo. Confira tipo e modalidade, avise o cliente e comece a preparação com pelo menos uma semana.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Adiada sem data** (`ADIADA`) | Adiada sem data | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Cancelada** (`CANCELADA`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Em preparação** (`EM_PREPARACAO`) | Iniciar preparação | qualquer | — | — |
| **Não realizada** (`NAO_REALIZADA`) | Não realizada | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Realizada** (`REALIZADA`) | Registrar realização | qualquer | resultado_audiencia | Registre o que aconteceu na audiência: acordo, defesa juntada, instrução encerrada, sentença designada. |
| **Redesignada** (`REDESIGNADA`) | Redesignada | qualquer | nova_audiencia | Cadastre primeiro a nova audiência com a data redesignada, ligada a esta. |

### 2. Em preparação — `EM_PREPARACAO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Checklist: cliente orientado, testemunhas confirmadas (e intimação pedida se alguma falhar), ad video feito, documentos e cálculo de proposta prontos. Na una, a defesa vem aqui: prepare a réplica.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Adiada sem data** (`ADIADA`) | Adiada sem data | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Cancelada** (`CANCELADA`) | Cancelar | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Não realizada** (`NAO_REALIZADA`) | Não realizada | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Realizada** (`REALIZADA`) | Registrar realização | qualquer | resultado_audiencia | Registre o que aconteceu na audiência: acordo, defesa juntada, instrução encerrada, sentença designada. |
| **Redesignada** (`REDESIGNADA`) | Redesignada | qualquer | nova_audiencia | Cadastre primeiro a nova audiência com a data redesignada, ligada a esta. |

### 3. Realizada — `REALIZADA`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Aconteceu. Registre o resultado (acordo, defesa juntada, instrução encerrada, sentença designada) e os prazos que a ata abriu.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Em preparação** (`EM_PREPARACAO`) | Registrada por engano | GESTOR | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 4. Redesignada — `REDESIGNADA`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** O juízo marcou nova data. A nova audiência é outra linha, ligada a esta.

*Etapa final: não há saída.*

### 5. Adiada sem data — `ADIADA`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Adiada sem nova data. Acompanhe o processo até a designação; aí nasce outra audiência.

*Etapa final: não há saída.*

### 6. Não realizada — `NAO_REALIZADA`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Não aconteceu por ausência ou outro motivo. Ausência do reclamante arquiva (art. 844 CLT) e pode custar custas — registre o motivo, é perda evitável.

*Etapa final: não há saída.*

### 7. Cancelada — `CANCELADA`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Perdeu o objeto: acordo antes da data, desistência, extinção.

*Etapa final: não há saída.*

---

## Prazo processual (`PRAZO`)

Governa `prazos.situacao` · 5 etapas · 8 transições.

### 1. Aberto — `ABERTO`

| | |
|---|---|
| tipo | INICIAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Prazo correndo. O vencimento está na própria linha, em dias úteis do TRT. Cumpra e registre o protocolo; o SLA aqui é o próprio vencimento.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Cumprido** (`CUMPRIDO`) | Cumprido: registrar protocolo | qualquer | protocolo_registrado | Informe a data do protocolo e junte a peça (ou o número do protocolo do PJe). |
| **Perdido** (`PERDIDO`) | Registrar prazo perdido | GESTOR | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Sem objeto** (`SEM_OBJETO`) | Sem objeto | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Suspenso** (`SUSPENSO`) | Suspender | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 2. Suspenso — `SUSPENSO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Suspenso por decisão do juízo, recesso ou força maior (art. 775 §1º CLT). Ao retomar, informe o novo vencimento recontado.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Aberto** (`ABERTO`) | Retomar contagem | qualquer | novo_vencimento | Informe o novo vencimento recontado em dias úteis a partir da retomada. |
| **Sem objeto** (`SEM_OBJETO`) | Sem objeto | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 3. Cumprido — `CUMPRIDO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Peça protocolada dentro do prazo. Fica o número do protocolo e a data.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Aberto** (`ABERTO`) | Reabrir (registro errado) | GESTOR | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 4. Perdido — `PERDIDO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Gestão |

**O que fazer aqui:** Venceu sem protocolo. Só gestor registra, com motivo — é o pior dia do escritório e precisa ser contado, não escondido.

*Etapa final: não há saída.*

### 5. Sem objeto — `SEM_OBJETO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** O prazo deixou de existir: acordo, desistência, decisão que o tornou desnecessário. Não é perda.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Aberto** (`ABERTO`) | Reabrir | GESTOR | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

---

## Incidente de representação (`INCIDENTE`)

Governa `incidentes.situacao` · 7 etapas · 12 transições.

### 1. Detectado — `DETECTADO`

| | |
|---|---|
| tipo | INICIAL |
| prazo interno (SLA) | 5 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Apareceu outro patrono nos autos ou o cliente avisou. Confirme nos autos (há revogação juntada?), avise o cliente e decida: notificar ou tentar trazer de volta.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Honorários reservados nos autos** (`HONORARIOS_RESERVADOS`) | Reserva pedida ao juízo | ADVOGADO | peticao_reserva | Anexe a petição de reserva de honorários protocolada nos autos (EOAB art. 22 §4º). |
| **Notificado** (`NOTIFICADO`) | Notificação enviada | qualquer | notificacao_enviada | Registre a data de envio da notificação extrajudicial e anexe a cópia. |
| **Cliente recuperado** (`RECUPERADO`) | Cliente voltou | qualquer | — | — |
| **Alarme falso** (`SEM_OBJETO`) | Alarme falso | qualquer | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 2. Notificado — `NOTIFICADO`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | 30 dias |
| setor responsável | Jurídico |

**O que fazer aqui:** Notificação extrajudicial enviada cobrando os honorários pelo trabalho feito. Registre recebimento e resposta. Sem resposta em 30 dias, peça a reserva nos autos.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Honorários recebidos** (`HONORARIOS_RECEBIDOS`) | Honorários recebidos | qualquer | valor_recebido | Registre o valor efetivamente recebido, a data e o comprovante (alvará ou depósito). |
| **Honorários reservados nos autos** (`HONORARIOS_RESERVADOS`) | Reserva pedida ao juízo | ADVOGADO | peticao_reserva | Anexe a petição de reserva de honorários protocolada nos autos (EOAB art. 22 §4º). |
| **Perdido** (`PERDIDO`) | Dar por perdido | DIRECAO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Cliente recuperado** (`RECUPERADO`) | Cliente voltou | qualquer | — | — |

### 3. Honorários reservados nos autos — `HONORARIOS_RESERVADOS`

| | |
|---|---|
| tipo | INTERMEDIARIA |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Pedido de reserva/destaque dos honorários protocolado (EOAB art. 22 §4º). O juízo trava a parcela; acompanhe o pagamento junto com a execução.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Honorários recebidos** (`HONORARIOS_RECEBIDOS`) | Honorários recebidos | qualquer | valor_recebido | Registre o valor efetivamente recebido, a data e o comprovante (alvará ou depósito). |
| **Perdido** (`PERDIDO`) | Dar por perdido | DIRECAO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |
| **Cliente recuperado** (`RECUPERADO`) | Cliente voltou | qualquer | — | — |

### 4. Cliente recuperado — `RECUPERADO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** O cliente voltou. Confira a procuração nova nos autos e a revogação do outro patrono.

*Etapa final: não há saída.*

### 5. Honorários recebidos — `HONORARIOS_RECEBIDOS`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Financeiro |

**O que fazer aqui:** O escritório recebeu o que lhe cabia pelo trabalho feito. Registre o valor.

*Etapa final: não há saída.*

### 6. Perdido — `PERDIDO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Direção |

**O que fazer aqui:** Cliente e honorários perdidos ("recebido por eles"). Só a direção fecha assim, com motivo — é o número que mede o roubo de cliente.

| vai para | ação | quem pode | exige | por que trava |
|---|---|---|---|---|
| **Notificado** (`NOTIFICADO`) | Reabrir cobrança | DIRECAO | motivo | Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois. |

### 7. Alarme falso — `SEM_OBJETO`

| | |
|---|---|
| tipo | FINAL |
| prazo interno (SLA) | — |
| setor responsável | Jurídico |

**O que fazer aqui:** Não houve troca: era substabelecimento nosso, homônimo ou erro de leitura.

*Etapa final: não há saída.*

---

## Tipos de prazo (`prazo_tipos`)

Contagem em **dias úteis** (CLT art. 775), a partir do primeiro dia útil depois da
publicação no DEJT (Lei 11.419/2006, art. 4º §§ 3º–4º). `dias` vazio = o juízo fixa;
`padrão` é o que o sistema propõe e a pessoa pode corrigir (a correção fica no histórico).

| código | prazo | dias | padrão | fundamento | fase usual | observação |
|---|---|---|---|---|---|---|
| `EMBARGOS_DECLARACAO` | Embargos de declaração | 5 | 5 | CLT art. 897-A; CPC art. 1.023 | CONHECIMENTO | Interrompem o prazo do recurso principal (CPC art. 1.026). Cabem contra sentença e acórdão. |
| `EMENDA_INICIAL` | Emenda à inicial | 15 | 15 | CPC art. 321 c/c CLT art. 769 | CONHECIMENTO | Sob pena de indeferimento. [CONFIRMAR: alguma vara fixa 10?] |
| `MANIFESTACAO_DOCUMENTOS` | Manifestação sobre documentos juntados | juízo fixa | 5 | CPC art. 437 §1º (15 dias) aplicado com a regra do juízo; CLT art. 769 | CONHECIMENTO | Na prática o juízo trabalhista fixa 5 ou 10. [CONFIRMAR o padrão do escritório] |
| `MANIFESTACAO_LAUDO` | Manifestação sobre laudo pericial | juízo fixa | 15 | CPC art. 477 §1º (15 dias) c/c CLT art. 769; o juízo pode fixar menos | CONHECIMENTO | Perícia médica (nexo/incapacidade) e técnica (insalubridade/periculosidade, NR-15/NR-16). [CONFIRMAR: vara costuma dar 5, 10 ou 15?] |
| `RAZOES_FINAIS` | Razões finais | juízo fixa | 5 | CLT art. 850: 10 minutos orais; memoriais escritos no prazo que o juízo fixar | CONHECIMENTO | Só existe como prazo quando o juízo converte em memoriais. |
| `RECURSO_ORDINARIO` | Recurso ordinário (RO) | 8 | 8 | CLT art. 895, I | CONHECIMENTO | Reclamante com justiça gratuita: sem depósito recursal (CLT art. 899 §10) e sem custas (art. 790 §3º). Embargos de declaração interrompem este prazo. [CONFIRMAR: a gratuidade é pedida como regra?] |
| `REPLICA` | Manifestação sobre a defesa (réplica) | juízo fixa | 5 | Fixado pelo juízo; CPC art. 218 §3º (5 dias no silêncio) c/c CLT art. 769 | CONHECIMENTO | No rito ordinário a defesa vem na audiência inicial (CLT art. 847) e a réplica costuma ser em audiência ou por despacho. [CONFIRMAR: o TRT-2 dá 5, 10 ou 15 dias como regra?] |
| `AGRAVO_PETICAO` | Agravo de petição (AP) | 8 | 8 | CLT art. 897, a | EXECUCAO_DEFINITIVA | Contra decisão na execução (homologação de cálculo, extinção). Exige delimitação de matéria e valores (§1º). |
| `IMPUGNACAO_CALCULOS` | Impugnação aos cálculos de liquidação | 8 | 8 | CLT art. 879 §2º | EXECUCAO_DEFINITIVA | Sob pena de preclusão; deve indicar item e valor. Também vale na execução provisória. |
| `IMPUGNACAO_SENTENCA_LIQUIDACAO` | Impugnação à sentença de liquidação (exequente) | 5 | 5 | CLT art. 884 §3º | EXECUCAO_DEFINITIVA | Mesmo prazo dos embargos do executado (5 dias da garantia do juízo). |
| `MANIFESTACAO_EXECUCAO` | Manifestação na execução (bens, alvará, andamento) | juízo fixa | 5 | Fixado pelo juízo; CPC art. 218 §3º | EXECUCAO_DEFINITIVA | Inclui manifestar sobre pesquisa patrimonial negativa e sobre proposta de parcelamento (CPC art. 916, se admitido). |
| `AGRAVO_INSTRUMENTO` | Agravo de instrumento (AIRR) | 8 | 8 | CLT art. 897, b | RECURSAL | Contra despacho que nega seguimento ao RR. Depósito de 50% do valor do recurso (art. 899 §7º) — não se aplica ao reclamante beneficiário da gratuidade. |
| `AGRAVO_INTERNO` | Agravo interno / regimental | 8 | 8 | CLT art. 896 §12 e regimento; Lei 5.584/70 art. 6º | RECURSAL | — |
| `CONTRARRAZOES` | Contrarrazões | 8 | 8 | CLT art. 900; Lei 5.584/70 art. 6º | RECURSAL | Abre quando a reclamada recorre. Prazo de recurso adesivo é o mesmo (Súmula 283 TST). |
| `EMBARGOS_TST` | Embargos à SDI (TST) | 8 | 8 | CLT art. 894, II | RECURSAL | — |
| `RECURSO_ADESIVO` | Recurso adesivo | 8 | 8 | CPC art. 997 §2º; Súmula 283 TST | RECURSAL | — |
| `RECURSO_REVISTA` | Recurso de revista (RR) | 8 | 8 | CLT art. 896; Lei 5.584/70 art. 6º | RECURSAL | No sumaríssimo só por contrariedade a súmula do TST/súmula vinculante ou violação direta da CF (art. 896 §9º). |
| `OUTRO` | Outro prazo fixado pelo juízo | juízo fixa | 5 | CPC art. 218 §3º | — | Use só quando nenhum tipo acima serve; o nome do ato vai na descrição. |
