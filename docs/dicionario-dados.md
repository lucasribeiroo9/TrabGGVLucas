# Dicionário de dados — BASE GGV - TRAB V3 (`appMFTjWGygZ4ob5T`)

> Lido em 03/09/2026, somente leitura. Nomes dos campos vêm de `list_tables_for_base`; tipos, opções, ligações e fórmulas vêm do esquema bruto (`.airtable_schema_raw.json`, que não cobre a CÓPIA nem a AUDITORIA — para essas, `get_table_schema`). A **taxa de preenchimento** e a **distribuição das opções** foram contadas sobre TODOS os registros de cada tabela (download completo, 03/09/2026). Nenhum dado pessoal de cliente aparece aqui — só contagens.

Legenda das marcas: **[legado]** campo que sobrou de cópia/importação, **[lixo]** não migrar, **[poluído]** select com texto livre digitado como opção, **[n8n]** escrito por automação externa, não por gente.

## Visão geral

| Tabela | id | registros | campos | o que é |
|---|---|---|---|---|
| PRE PROCESSUAL | `tblucQ0Cz5MEQEdCR` | 797 | 44 | Gestão completa de potenciais clientes e das fases pré-processuais. |
| PROCESSUAL | `tbl6rDaSPCQRbbzjq` | 2652 | 82 | Acompanhe detalhadamente fases, partes e finanças de processos trabalhistas. |
| PÓS PROCESSUAL | `tblEInHoBmUuuShxk` | 556 | 13 | Controle o pós-processo: repasses, recebimentos e arquivamento dos casos. |
| FUNCIONARIOS | `tblisgqzJvF0EUFr1` | 72 | 20 | Centralize os dados de todos os funcionários e seus papéis nos casos. |
| TESTEMUNHAS | `tbl9nZjfmxqVy60NM` | 424 | 37 | Centraliza e organiza dados completos e status das testemunhas vinculadas a processos e empresas. |
| EMPRESAS | `tblkfWQhjp2F1dK0y` | 1103 | 15 | Registre empresas envolvidas em litígios e seus vínculos processuais. |
| Conferência de Faltantes | `tblnQHm5yTj2EPscB` | 1067 | 13 | Processos do escritório que ainda NÃO estão na PROCESSUAL. Glauco confere os dados + fase recomendada (Datajud) e marca "VALIDAR E SUBIR" pra promover (via automação) pra PROCESSUAL. |
| CÓPIA DA PROCESSUAL (NÃO MEXER) | `tblvyoun2V0CQKmxF` | 3722 | 96 | (mesma descrição da PROCESSUAL) Acompanhe detalhadamente fases, partes e finanças de processos trabalhistas. |
| AUDITORIA TESTEMUNHAS | `tblKp6rhoOGL2ChrO` | 2 | 15 | Log permanente e append-only das operações autenticadas realizadas no formulário interno de testemunhas. |
| FRAGILIDADES | `tblmxkxgQEbc0KwvV` | 17 | 15 | Achados de fragilidade trabalhista por empresa, extraídos da análise dos autos. Cada registro é uma tese acionável, com fundamento, prova documental e situação nos julgados. |

Ligações entre tabelas (setas = campo link → tabela): PRE PROCESSUAL → EMPRESA, CAPTADOR/ENTREVISTADOR/RESPONSAVEL INICIAL (FUNCIONARIOS), PROCESSUAL, TESTEMUNHAS · PROCESSUAL → EMPRESA, ADVOGADO/CAPTADOR/RESP ADVIDEO (FUNCIONARIOS), PRE PROCESSUAL, POS PROCESSUAL, TESTEMUNHAS · PÓS PROCESSUAL → PROCESSUAL, RESPONSAVEL, e o legado PROCESSUAL copy → CÓPIA · TESTEMUNHAS → EMPRESA, CAPTADOR, PROCESSUAL (`TESTEMUNHA DE:`), PRE PROCESSUAL (`TESTEMUNHA DE`) · EMPRESAS ← tudo, inclusive Conferência de Faltantes, CÓPIA e FRAGILIDADES · CÓPIA → EMPRESA, ADVOGADO, CAPTADOR, POS PROCESSUAL (os links para PRE e TESTEMUNHAS viraram texto).


## PRE PROCESSUAL — `tblucQ0Cz5MEQEdCR` (797 registros)

Gestão completa de potenciais clientes e das fases pré-processuais.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| NOME | `fldMgzsOWTG83RRHM` | singleLineText |  |  | 797/797 (100%) |  |
| TELEFONE | `fldf7EJVSHV2xnyvq` | phoneNumber |  |  | 791/797 (99%) |  |
| PASSAR DE FASE? | `fldIpom79mvFB9va3` | checkbox | marcados: 478 | GATILHO PARA PROCESSUAL | 478/797 (60%) | **Gatilho humano** da automação PRÉ → PROCESSUAL (junto com ETAPA e STATUS PETICAO = DISTRIBUIDA). |
| E-MAIL | `fldAbboJKxYQo1KSP` | singleLineText |  |  | 40/797 (5%) |  |
| CPF | `fldoHdB4li1b6LkI6` | singleLineText |  |  | 651/797 (82%) |  |
| NASCIMENTO | `fldM4AGasbrB33qim` | date | l |  | 635/797 (80%) |  |
| EMPRESA | `fld67uX200O7VqCle` | multipleRecordLinks | → EMPRESAS (inverso: `PRE PROCESSUAL`) · 1 só |  | 784/797 (98%) |  |
| FUNCAO | `fld5Or0RJXmcRN71K` | singleLineText |  |  | 683/797 (86%) |  |
| DATA DE ASSINATURA | `fldk5NSJtkJs581As` | date | l |  | 787/797 (99%) |  |
| CAPTADOR | `fldINYulF0zjgLugU` | multipleRecordLinks | → FUNCIONARIOS (inverso: `PRE PROCESSUAL`) · 1 só |  | 791/797 (99%) |  |
| STATUS DOCUMENTAÇÃO | `fldNJ5XYezXj83I8x` | singleSelect | `COMPLETA` 555, `PENDENTE` 32, `DESISTÊNCIA` 92, `AGUARDANDO` 9, `TRATAMENTO` 5, `PARCIAL` 4 |  | 697/797 (87%) |  |
| STATUS ENTREVISTA | `fldMbfgFK4APJJL7F` | singleSelect | `PENDENTE` 3, `REMARCAR`, `ENTREVISTA AGENDADA` 7, `PRIMEIRO CONTATO` 2, `SEGUNDO CONTATO`, `TERCEIRO CONTATO`, `STAND-BY` 2, `ENTREVISTA-OK` 448, `DESISTÊNCIA ` 113, `SEM RESPOSTA` 17, `0`, `ok`, `ag`, `SEM` |  | 592/797 (74%) | **[poluído]** **Poluído**: as opções `0`, `ok`, `ag`, `SEM` e `DESISTÊNCIA ` (com espaço) são digitação livre que virou opção. Nenhum registro usa `0/ok/ag/SEM/REMARCAR/SEGUNDO/TERCEIRO CONTATO` hoje. |
| STATUS PETICAO INICIAL | `fldCXIpACRak8hyQA` | singleSelect | `PENDENTE` 41, `EM CRIAÇÃO` 6, `AGUARDANDO APROVAÇÃO` 54, `APROVADA` 5, `DISTRIBUIDA` 486, `DESISTENCIA` 100, `PRESCRITO` 2, `VALIDAÇÃO` |  | 694/797 (87%) | É a **etapa de verdade** da petição inicial: PENDENTE → EM CRIAÇÃO → AGUARDANDO APROVAÇÃO → APROVADA → DISTRIBUIDA. `VALIDAÇÃO` existe como opção e não é usada; `PRESCRITO` e `DESISTENCIA` são saídas. |
| ETAPA PRE PROCESSUAL | `fldZWcb1qmuSnOzib` | singleSelect | `DOCUMENTAÇÃO` 19, `ENTREVISTA` 42, `PETIÇÃO INICIAL` 147, `CONCLUÍDO` 452, `CANCELAMENTO` 137 |  | 797/797 (100%) | A **etapa-mãe** do pré-processual. Ordem inferida: DOCUMENTAÇÃO → ENTREVISTA → PETIÇÃO INICIAL → CONCLUÍDO; CANCELAMENTO é a saída (a automação DESISTENCIA grava aqui). |
| FONTE | `fldB8Dg9doxUwm15P` | singleSelect | `Indicação`, `Site`, `Facebook`, `Instagram`, `DISP LAILLA` 9, `PROJETO PUXADA` 55, `PXD`, `INDICAÇÃO` 2, `ENTRADA DE LEAD` 1, `PROJETO BENEFICIO E ERROS DE CÁLCULO` 1, `INDICAÇAO` 1, `PROJETO PUXADA 17/06` 3, `PROJETO JUXADA` 4, `PROJETO CLIENTE ATIVO` 1 |  | 77/797 (10%) | **[poluído]** **Poluído e quase vazio** (10%): mistura canal (Site, Instagram) com campanha (PROJETO PUXADA, PXD, PROJETO JUXADA = erro de digitação, PROJETO PUXADA 17/06) e três grafias de INDICAÇÃO. Só passou a ser preenchido a partir de jun/2026. |
| STATUS_NOTIFICACAO_PRESCRICAO | `fldB35aEzRYRSRa7M` | singleSelect | `NENHUM`, `AVISO ENVIADO` 29, `VENCIDO NOTIFICADO` 16 |  | 45/797 (6%) | **[n8n]** Escrito pelo n8n (nome em snake_case). Marca que o aviso de prescrição saiu. |
| STATUS_NOTIFICACAO_RI | `fldGARfirwAPLcFU0` | singleSelect | `NENHUM`, `RI 5D ENVIADO` 5, `RI 10D ENVIADO` 4, `RI 12D ENVIADO` 4, `RI 15D ENVIADO` 45 |  | 58/797 (7%) | **[n8n]** Escrito pelo n8n. Cadência de cobrança da rescisão indireta: 5, 10, 12 e 15 dias. |
| RESCISAO | `fldiMRutGPhxhciRS` | singleLineText |  |  | 666/797 (84%) | **Texto livre que devia ser select**: 241 "DEMISSÃO SEM JUSTA CAUSA", 84 "SEM JUSTA CAUSA", 98+2 "RESCISÃO INDIRETA"/"RECISÃO", 81 "PEDIDO DE DEMISSÃO", 34+6 "JUSTA CAUSA", e lixo (datas, telefone, "SIM", "NÃO SEI O CERTO AINDA"). A automação URGENCIA R.I faz `contains "RESCISÃO INDIRETA"` aqui. |
| DEMISSAO | `fldj37usp7C6okYE1` | singleLineText |  |  | 616/797 (77%) | **Data guardada como texto**, em 6 formatos (`d/m/aaaa`, `dd/mm/aaaa`, `dd-mm-aaaa`, com ponto final…). A fórmula PRESCREVE parseia com `D/M/YYYY` — os 5 com hífen quebram. |
| PRESCREVE | `fldcAJEHaeJiV3Acg` | formula | `IF(   {fldj37usp7C6okYE1},   DATETIME_FORMAT(     DATEADD(DATETIME_PARSE({fldj37usp7C6okYE1}, 'D/M/YYYY'), 2, 'years'),     'DD/MM/YYYY'   ),   BLANK() )` | Calcula a data de prescrição (2 anos após demissão) no formato DD/MM/YYYY. | 616/797 (77%) | Fórmula: DEMISSAO + 2 anos (prescrição bienal, art. 7º, XXIX, CF / art. 11 CLT), formatada dd/mm/aaaa. Em 03/09/2026: 156 já vencidas, 460 futuras. |
| AVISOS | `fldG6n6zOWaS7qeVr` | multilineText |  |  | 179/797 (22%) | Escrito pelas automações 🟡 15 dias / 🔴 20 dias (mesmo campo — o de 20 sobrescreve o de 15). Também recebe texto humano em 3 casos. |
| URGENCIA | `fldIYbZyJQurMCRfG` | multipleSelects | `checked` 4, `RI` 84, `PRESCRIÇÃO` 130, `URGENCIA ALTA` 133 |  | 226/797 (28%) | Opção `checked` (4 registros) é lixo de importação. `RI` e `URGENCIA ALTA` são gravadas por automação; `PRESCRIÇÃO` [CONFIRMAR: gravada pelo n8n ou à mão?]. |
| PENDENCIAS | `fldBooALabWsmeeOP` | multipleSelects | `CNH/RG` 98, `CTPS` 113, `TRCT` 472, `DOCS. MÉDICOS` 388, `PROVAS` 465, `FGTS` 244, `HOLERITES` 405, `HOLERITE` 36, `PIS` 14, `DOCUMENTAÇÃO OK` 2, `OK` 2 |  | 551/797 (69%) | Lista de documentos. **Ambíguo**: 172 fichas COMPLETA têm 4 itens marcados — parece ser a lista do que foi *pedido/recebido*, não do que *falta* [CONFIRMAR]. `HOLERITE`/`HOLERITES` duplicadas; `OK` e `DOCUMENTAÇÃO OK` não são documento. |
| DRIVE | `fld1vyxG8x6W6g9Mk` | url |  |  | 795/797 (100%) |  |
| ASTREA | `fldGotjWCRp1MqC41` | url |  |  | 536/797 (67%) | Link para o Astrea (software jurídico anterior/paralelo). [CONFIRMAR: o Astrea continua em uso?] |
| ENTREVISTADOR | `fldJZktWI7lBRUXVd` | multipleRecordLinks | → FUNCIONARIOS (inverso: `PRE PROCESSUAL (ENTREVISTADOR)`) · 1 só |  | 431/797 (54%) |  |
| DATA ENTREVISTA | `fldzAzEK2Bd9df8Ly` | dateTime | l |  | 397/797 (50%) |  |
| RESUMO ENTREVISTA | `fldVezNGzkGhlsnzM` | multilineText |  |  | 51/797 (6%) |  |
| RESPONSAVEL INICIAL | `fldoSAxQw8Qbr7vhF` | multipleRecordLinks | → FUNCIONARIOS (inverso: `PRE PROCESSUAL (RESPONSAVEL INICIAL)`) · 1 só |  | 597/797 (75%) |  |
| TESE PRINCIPAL | `fldc9EKTY8zh1Zjmg` | singleLineText |  |  | 0/797 (0%) | **Vazio em 100%**. Candidato a remover ou a virar select de matéria. |
| PROCESSUAL | `fldyG90IE0htBpVEo` | multipleRecordLinks | → PROCESSUAL (inverso: `PRE PROCESSUAL`) |  | 431/797 (54%) |  |
| TESTEMUNHAS | `fldDh5FCEddcsnBf1` | multipleRecordLinks | → TESTEMUNHAS (inverso: `TESTEMUNHA DE`) |  | 120/797 (15%) |  |
| Created | `fldyBsUVlqH0ulTnE` | createdTime |  |  | 797/797 (100%) |  |
| PERICIA MEDICA | `fldRofbAsutD06eAB` | checkbox | marcados: 0 |  | 0/797 (0%) | Vazio em 100%, mas é copiado para a PROCESSUAL pela automação PRÉ → PROCESSUAL. |
| PERICIA INSALUB/PERIC | `fldzDiAk4UZpiKLy5` | checkbox | marcados: 0 |  | 0/797 (0%) | Vazio em 100%; vira `PERICIA TECNICA` na PROCESSUAL. |
| ENVIAR MENSAGEM | `fldSHOr0gls9z5rUn` | button |  | Gera URL de disparo com data da entrevista formatada como DD/MM/AA HH:MM. | 797/797 (100%) | Botão que abre URL do webhook n8n `airtable-lailla-disparo` com nome, telefone, empresa, CPF, status e data da entrevista como parâmetros. Lailla é o disparador de WhatsApp. |
| status_disparo | `fld3pVGPa59DBAZMp` | singleLineText |  |  | 196/797 (25%) | **[n8n]** **Escrito pelo n8n/script**, não por gente: `enviada`, `aniversario_enviado`, `aniversario_erro` (88!), `revisao_manual`. |
| tipo_disparo | `fldIFX1oNfUlUFG0c` | singleLineText |  |  | 119/797 (15%) | **[n8n]** Idem: aviso_informativo, solicitacao, compromisso, aniversario, inicio_atendimento, inicio_testemunha. |
| data_solicitacao_disparo | `fldO2ZTWv7QhV5Rc0` | singleLineText |  |  | 196/797 (25%) | **[n8n]** Idem (timestamp ISO em texto). |
| responsavel_interno | `fldTqXb9QWzWxM3Ar` | singleLineText |  |  | 103/797 (13%) | **[n8n]** Idem. |
| solicitante_disparo | `flduFmWE4Ka5bwKrr` | singleLineText |  |  | 103/797 (13%) | **[n8n]** Idem. |
| erro_disparo | `fldKJn522iGXk8hHu` | singleLineText |  |  | 90/797 (11%) | **[n8n]** Idem — mensagem de erro do webhook. |
| EMPRESA PROCESSADA | `fldNgwihIj6mu6TnS` | multipleLookupValues | lookup via `EMPRESA` → EMPRESAS.`EMPRESA` |  | 784/797 (98%) | Lookup redundante do nome da EMPRESA (serve ao botão). |
| prescrição próxima | `flddOmzVQJ2IJn9Us` | formula | `IF(   AND(     {fldcAJEHaeJiV3Acg},     DATETIME_DIFF(DATETIME_PARSE({fldcAJEHaeJiV3Acg}, 'DD/MM/YYYY'), TODAY(), 'days') >= 0,     DATETIME_DIFF(DATETIME_PARSE({fldcAJEHaeJiV3Acg}, 'DD/MM/YYYY'), TODAY(), 'days') <= 30 ` |  | 49/797 (6%) | Fórmula: "🔴" quando PRESCREVE está entre hoje e +30 dias. |

## PROCESSUAL — `tbl6rDaSPCQRbbzjq` (2652 registros)

Acompanhe detalhadamente fases, partes e finanças de processos trabalhistas.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| NOME | `fldNfuluuw5gCEHr4` | singleLineText |  |  | 2652/2652 (100%) |  |
| Nº PROCESSO | `fld6Ij9BXuOr9PSYg` | singleLineText |  |  | 2546/2652 (96%) |  |
| EMPRESA | `fldrknqdvK5yrinq8` | multipleRecordLinks | → EMPRESAS (inverso: `PROCESSUAL`) |  | 2110/2652 (80%) |  |
| COMPLEXIDADE | `fld2Vbn86hkcHjRZU` | singleSelect | `A` 143, `B` 1098, `C` 1341 |  | 2582/2652 (97%) | A/B/C **derivada do VALOR** pelo script (C ≤ 150 mil; B ≤ 500 mil; A > 500 mil). 99,6% bate com a faixa. É atributo, não etapa. |
| VALOR | `fld4ixpIddlOdip3a` | currency | R$ 2 casas |  | 2581/2652 (97%) |  |
| ADVOGADO | `fldgmBAFmw9vew8XV` | multipleRecordLinks | → FUNCIONARIOS (inverso: `PROCESSUAL (ADVOGADO)`) · 1 só |  | 763/2652 (29%) |  |
| VARA | `fldB6EhDR53tG0bqT` | singleLineText |  |  | 1972/2652 (74%) |  |
| TRT | `fldoc8fTWo0JH0b0T` | singleSelect | `1ª` 32, `2ª` 2352, `3ª` 8, `4ª` 15, `7ª` 2, `12ª` 8, `15ª` 68, `17ª` 2, `18ª` 17, `5ª` 3, `8ª` 1, `85ª`, `1ª` 32, `6ª` 2, `9`, `10`, `19ª` 1, `21ª` 2, `14ª`, `9ª` 1, `10ª` 2 |  | 2516/2652 (95%) | **[poluído]** 21 opções com duplicatas (`1ª` duas vezes, `9`/`9ª`, `10`/`10ª`, `85ª`). 89% é TRT-2. |
| FASE PROCESSUAL | `fld0SuRbQk9jJa19n` | singleSelect | `ACORDO` 119, `CONHECIMENTO` 1343, `DESISTENCIA` 28, `RECURSAL` 227, `ENCERRADO` 478, `EXECUÇÃO` 125, `EXECUÇÃO DEFINITIVA` 74, `EXECUÇÃO PROVISÓRIA` 140, `RECEBENDO` 2 |  | 2536/2652 (96%) |  |
| STATUS DO PROCESSO | `fldqubv8Cbd8u9yPr` | singleSelect | `ACORDO` 78, `AGUARDANDO AUDIÊNCIA` 469, `AGUARDANDO SENTENÇA` 28, `ARQUIVADO` 444, `DESISTENCIA` 27, `EXECUCAO` 287, `RECEBIDO POR ELES` 38, `RECUPERADO` 18, `REDISTRIBUIR` 1, `ROUBADO` 66, `TRÂNSITO EM JULGADO` 35, `SOBRESTADO` 11 |  | 1502/2652 (57%) |  |
| ENVIAR MENSAGEM | `fldV1cOA4tEfnjKPW` | button |  | Gera uma URL com todos os campos da tabela como parâmetros codificados. | 2652/2652 (100%) | Botão → webhook n8n com todos os campos como parâmetros. |
| DISTRIBUIÇAO | `fldrcjw0h3MDTuaod` | date | l |  | 2647/2652 (100%) |  |
| STATUS CONHECIMENTO | `fldFI8DlSCAoPpjJO` | singleSelect | `AGUARDANDO AUDIÊNCIA` 521, `ADVIDEO`, `AGUARDANDO PERICIA` 5, `ACORDO EM ANDAMENTO` 15, `AGUARDANDO SENTENÇA` 28, `AUSÊNCIA` 17, `DESISTÊNCIA` 36, `SENTENCIADA` 545 |  | 1167/2652 (44%) |  |
| SENTENCA | `fldjHSryziAOOISbv` | singleSelect | `RUIM` 250, `ÓTIMA` 95, `MÉDIA` 169 |  | 514/2652 (19%) | **Nota subjetiva** (RUIM/MÉDIA/ÓTIMA) da sentença. Não confundir com DECISAO SENTENCA (objetiva). |
| DECISAO SENTENCA | `fld2NZ9Zi35931gge` | singleSelect | `PARCIALMENTE PROCEDENTE` 384, `IMPROCEDENTE` 81, `PROCEDENTE` 14 |  | 479/2652 (18%) |  |
| RESULTADO ACORDAO | `fldyhUJRHPLAsghKj` | singleSelect | `RUIM` 206, `MÉDIO` 176, `ÓTIMO` 76 |  | 458/2652 (17%) | **Nota subjetiva** do acórdão. O resultado objetivo (PROVIDO/NEGADO…) só existe na CÓPIA (`RESULTADO RECURSO`). |
| ULTIMA DECISAO | `fld5XeIVLrec9DCu0` | singleSelect | `RUIM` 275, `ÓTIMA` 132, `MÉDIA` 167, `SEM DECISÃO` 34, `IMPROCEDENTE` 11, `PROCEDENTE` 7 |  | 626/2652 (24%) | Mistura nota (RUIM/MÉDIA/ÓTIMA) com resultado (PROCEDENTE/IMPROCEDENTE) e SEM DECISÃO. Duas naturezas no mesmo campo. |
| DATA ACORDAO | `fldezorfyCie9kmB1` | date | l |  | 367/2652 (14%) |  |
| CLASSIFICACAO | `fldwA5XRRCLLusZhu` | singleSelect | `RT - ORDINÁRIO` 479, `AT - SUMARÍSSIMO` 140, `AT - ORDINÁRIO` 886, `AT - SUMÁRIO` |  | 1505/2652 (57%) | Rito: RT = Reclamação Trabalhista (antiga classe), AT = Ação Trabalhista (classe atual do PJe) — ORDINÁRIO, SUMARÍSSIMO (≤ 40 SM), SUMÁRIO (≤ 2 SM, raro; 0 registros). Vazio em 43%. |
| DATA AUDIENCIA | `fldYTqFftgpvtxHCb` | dateTime | l |  | 583/2652 (22%) |  |
| AUDIENCIA | `fldQgm6veivaP9A7v` | singleSelect | `INICIAL` 90, `INSTRUÇÃO` 110, `HOMOLOGAÇÃO` 4, `UNA` 430 |  | 634/2652 (24%) |  |
| Nº  CumPrSe | `fldC5VgP5KIXGqoDM` | singleLineText |  |  | 326/2652 (12%) |  |
| RESULTADO | `fldifEVxbZJJnrYRN` | multilineText |  |  | 109/2652 (4%) |  |
| STATUS RECURSAL | `fldfWIWmtbQX9n29c` | singleSelect | `TST` 154, `AGUARDANDO JULGAMENTO` 91 |  | 245/2652 (9%) |  |
| STATUS CumPrSe | `fldnjIz7be8iZqjqS` | singleSelect | `ACORDO`, `AGUARDANDO SENTENÇA` 1, `DECISÃO POSITIVA EM 1ª INSTÂNCIA` 1, `DECISÃO POSITIVA EM 2ª INSTÂNCIA` 1, `FASE DE CÁLCULOS` 9, `PERICIA CONTÁBIL` 1, `RECEBIDO` 5, `SOBRESTADO` 1 |  | 19/2652 (1%) |  |
| STATUS DO CALCULO | `fldzNusdLtfqC2EhS` | singleSelect | `HOMOLOGADO` 178, `JUNTADO AOS AUTOS` 13, `PENDENTE` 10 |  | 201/2652 (8%) |  |
| CALCULO RCTE | `fldIoDBuntoHRD8M4` | currency | R$ 2 casas |  | 118/2652 (4%) |  |
| SUCUMB RCTE | `fldQwD6wl9Rp1OdvN` | currency | R$ 2 casas |  | 164/2652 (6%) |  |
| CALCULO RCDA | `fldBXmceSOIGmB6Qi` | currency | R$ 2 casas |  | 95/2652 (4%) |  |
| SUCUMB RCDA | `fldzP9PLO36pB8GkB` | currency | R$ 2 casas |  | 93/2652 (4%) |  |
| SUCUMB HOM | `fldn7DL7nwIB1wXCi` | currency | R$ 2 casas |  | 182/2652 (7%) |  |
| VALOR HOM | `fldQwZD5A9GhAGG52` | currency | R$ 2 casas |  | 400/2652 (15%) |  |
| STATUS PAGAMENTO | `fldMJyeDxmi4D7qLI` | singleSelect | `PENDENTE` 55, `CONCLUIDO` 165, `PAGO PARCIALMENTE` 4, `AGUARDANDO PAGAMENTO` 3, `PARCELAMENTO CPC` 4, `PAGAMENTO EM DIA` 13, `PAGAMENTO ATRASADO` 2 |  | 246/2652 (9%) |  |
| ENCERRAMENTO | `fldrtiBvNP0bBmB7p` | date | l |  | 399/2652 (15%) |  |
| DRIVE | `fldHaNBnpjhyTvUzY` | url |  |  | 1412/2652 (53%) |  |
| ASTREA | `fldpc4dSNT3fuoQQS` | url |  |  | 856/2652 (32%) |  |
| OBSERVACOES | `fldKtWPFUUDgf6wAO` | multilineText |  |  | 257/2652 (10%) |  |
| PRE PROCESSUAL | `fldjVtWlmftDbeNOR` | multipleRecordLinks | → PRE PROCESSUAL (inverso: `PROCESSUAL`) |  | 444/2652 (17%) |  |
| POS PROCESSUAL | `fldVZQSDtQeDlN8JN` | multipleRecordLinks | → PÓS PROCESSUAL (inverso: `PROCESSUAL`) |  | 453/2652 (17%) |  |
| TURMA | `fldwUFdtsipXQpkZc` | singleSelect | `11` 1, `6ª TURMA` 16, `9ª TURMA` 2, `8ª TURMA` 20, `2ª TURMA` 26, `5ª TURMA` 17, `4ª TURMA` 14, `7ª TURMA` 1, `12ª TURMA` 1, `3ª TURMA` 19, `1ª TURMA` 15, `18ª TURMA` 26, `10ª TURMA` 25, `16ª TURMA` 2, `11ª TURMA` 4, `11ª TURMA ` 25, `12ª TURMA ` 17, `15ª TURMA`, `17ª TURMA` 1, `14ª TURMA` 19, `17ª TURMA ` 25, `13ª TURMA` 3, `16ª TURMA ` 19, `18ª turma` 2, `7ª TURMA ` 17, `9ª TURMA ` 26, `15ª TURMA ` 15, `13ª TURMA ` 19, `Análise de Recursos` 2, `Análise de Recursos/Vice-Presidência Judicial` 44, `(nº CNJ digitado como opção)` `Vice-Presidência Judicial` 1, `Presidência` 1, `(nº CNJ digitado como opção)` `(nº CNJ digitado como opção)` `(nº CNJ digitado como opção)` `(nº CNJ digitado como opção)` `(nº CNJ digitado como opção)` `(nº CNJ digitado como opção)` `7ª Câmara` 2, `Órgão Especial - Análise de Recurso` 1 |  | 428/2652 (16%) | **[poluído]** **Poluído**: 41 opções — turmas do TRT-2 com e sem espaço final (`11ª TURMA` e `11ª TURMA `), `18ª turma`, `11`, `7ª Câmara`, órgãos (Vice-Presidência, Presidência, Análise de Recursos, Órgão Especial) e **7 números de processo digitados como opção**. |
| TESTEMUNHAS | `fld2M1cDAzzIsY9Ju` | multipleRecordLinks | → TESTEMUNHAS (inverso: `TESTEMUNHA DE:`) |  | 239/2652 (9%) |  |
| DATA ADVIDEO | `fldapqeXrdSg96USR` | dateTime | l |  | 0/2652 (0%) | Vazio em 100%, embora o script AUTOPREENCHIMENTO dependa dele. O fluxo de ad video não é registrado aqui hoje [CONFIRMAR onde]. |
| RESP ADVIDEO | `fldT17XSmaZwyeFEb` | multipleRecordLinks | → FUNCIONARIOS (inverso: `PROCESSUAL 2`) · 1 só | RESPONSAVEL PELO ADVIDEO | 0/2652 (0%) | Vazio em 100%. |
| STATUS ADVIDEO | `fldIOGYMaqOMyWhld` | singleSelect | `FEITO` 1, `PENDENTE`, `MARCADO` |  | 1/2652 (0%) | 1 registro. |
| PERICIA MEDICA | `fldBuY7IbnUaLKDVL` | checkbox | marcados: 7 |  | 7/2652 (0%) |  |
| PERICIA TECNICA | `fldhyoWgzBcBUXIy4` | checkbox | marcados: 11 |  | 11/2652 (0%) |  |
| STATUS EXECUÇÃO | `fldOaKzigKAjCeIB7` | singleSelect | `AGUARDANDO ALVARÁ` 16, `AGUARDANDO CÁLCULO` 237, `AGUARDANDO PERICIA` 2, `AGUARDANDO TRANSITO ` 1, `ARQUIVADO` 120, `AUDIÊNCIA CONCILIAÇÃO` 2, `EXTINTA S/ RESOLUÇAO` 21, `FASE DE CÁLCULOS` 9, `HOMOLOGADO` 45, `NEGOCIANDO ACORDO` 1, `PARCELAMENTO 916 CPC` 4, `PROCURANDO BENS` 9, `SOBRESTADO` 1, `RECEBIDO` 10, `NÃO` 1, `LIQUIDAÇAO` 1, `FASE DE CALCULOS`, `CALCULOS`, `SIM` 2, `SIM ` 23, `Discutindo cálculos. ` 6, `AGUARDANDO CÁLCULOS`, `Aguardando homologação` 1, `FASE DE CALCULO` 1, `Homologado. ` 1, `EXECUÇÃO` 8, `RECURSAL` 2, `ALVARA` 1, `PESQUISA ` 14, `NÃO ` 9, `AGUARDANDO TRANSITO` 49, `Aguardando perícia contabil ` 1, `RECURSO EXECUÇÃO` 14, `EXECUÇAO PROVISÓRIA` 2, `Designado a pericia contabil ` 1, `Aguardando laudo contabil ` |  | 615/2652 (23%) | **[poluído]** **Muito poluído**: 36 opções, das quais só ~16 são estados (as mesmas que a CÓPIA manteve). O resto é texto digitado que virou opção: `SIM `, `NÃO `, `PESQUISA `, `Discutindo cálculos. `, `Designado a pericia contabil `, `Aguardando laudo contabil `, `LIQUIDAÇAO`, três grafias de FASE DE CÁLCULO(S), `Homologado. `… |
| AND. NECESSÁRIO | `fldg1Bd6mkVrcTYQn` | singleSelect | `PEDIR ANDAMENTO` 13, `EXPEDIÇAO DE ALVARÁ`, `TENTAR ACORDO`, `PEDIR AUD CONCILIAÇÃO`, `Alvará `, `ACORDO` 1, `Alvará` 11, `Aguardar a empresa realizar o pagamento e começar a impulsionar.` 4, `Solicitar andamento processual para que a enel realize o pagamento. ` 2, `Alvara ` 3, `Juiza dificil em Glauco, o atendente felipe disse que tentaria apressar. ` 1, `Prosseguimento` 28, `Encerrado` 64 |  | 127/2652 (5%) | **[poluído]** **Poluído**: "andamento necessário" virou caderno de recado — `Juiza dificil em Glauco, o atendente felipe disse que tentaria apressar. `, `Solicitar andamento processual para que a enel realize o pagamento. `, três grafias de Alvará. Devia ser tarefa, não select. |
| AÇÃO | `fldMGJEtU1xwQgN44` | date | l |  | 180/2652 (7%) | Data. [CONFIRMAR: data do ajuizamento? difere de DISTRIBUIÇAO em quê?] 7% preenchido. |
| TEL VARA | `fldawy6eAxOG7SOAk` | phoneNumber |  |  | 154/2652 (6%) |  |
| STATUS ACORDO | `fldXIXmprptmmddgZ` | singleSelect | `ACORDO EM ANDAMENTO` 21, `ACORDO CUMPRIDO` 102, `QUEBRA DE ACORDO` 3 |  | 126/2652 (5%) |  |
| VALOR ACORDO | `fld3QiKc0ZWvhGOAY` | currency | R$ 2 casas |  | 132/2652 (5%) |  |
| TOTAL RECEBIDO | `fld5ozVpHgQkmILn6` | currency | R$ 2 casas |  | 262/2652 (10%) |  |
| SUCUMB RECEBIDO | `fldPo7TA7Vf1sGDle` | currency | R$ 2 casas |  | 206/2652 (8%) |  |
| HONOR TOTAL | `fldHre22MxIFJBkst` | currency | R$ 2 casas |  | 217/2652 (8%) |  |
| SITU. EMPRESA | `fldKg8pjqh6Xx93f6` | multipleLookupValues | lookup via `EMPRESA` → EMPRESAS.`STATUS EMPRESA` |  | 1804/2652 (68%) | Lookup de EMPRESAS.STATUS EMPRESA (ATIVA/INATIVA/EM RECUPERACAO). |
| BENS IDENTIFICADOS | `fldfNjKnnKr11GGcL` | multipleSelects | `NÃO` 146, `SIM` 12 |  | 158/2652 (6%) | Idem: bens da reclamada. Duplica EMPRESAS.BENS IDENTIFICADOS. |
| HIST. PAGAMENTO | `fldRa9KGSydy8BCmD` | multipleSelects | `BOA` 242, `PÉSSIMA` 27, `RUIM` 9 |  | 278/2652 (10%) | Histórico de pagamento **da empresa reclamada** (BOA/RUIM/PÉSSIMA), embora esteja na ficha do processo. Duplica EMPRESAS.HIST. PAGAMENTO. |
| ULTIMA MOV | `fldvOXdS10SVyA10U` | singleLineText |  |  | 1699/2652 (64%) | Texto `aaaa-mm-dd - descrição`, alimentado por pipeline (Datajud/AASP) — 64% preenchido; a última data é jul/2026. |
| REVOGAÇÃO | `fldWEiwaScW2AZjlC` | singleSelect | `SIM ` 529, `NÃO` 113, `BRUNO - juntar revogaçao nestes autos `, `BRUNO - ver se colocaram a revogaçao acima` 1, `ROUBADO`, `fazer revogaçao`, `fazer revogaçao ` 2, `SEM REVOGAÇAO - RENAN QUE ASSINOU PROCURAÇAO` 3, `ver se colocaram a revogaçao acima` 1, `BRUNO -tem revogaçao nos autos abaixo`, `VERIFICAR` 1, `NÃO SE APLICA` 46 |  | 696/2652 (26%) | **[poluído]** **Poluído**: SIM /NÃO/NÃO SE APLICA mais 9 recados (`BRUNO - juntar revogaçao nestes autos `, `fazer revogaçao`, `VERIFICAR`, `ROUBADO`…). Revogação = o cliente revogou a procuração do advogado anterior (caso ROUBADO/RECUPERADO). |
| DATA REVOG | `fldmQNnSSPgwmjrfU` | date | D/M/YYYY |  | 647/2652 (24%) |  |
| NOTIFICAÇÃO | `fldIX6EOFBawzAWUK` | singleSelect | `PENDENTE`, `ENVIADA`, `RECEBIDA`, `RESPONDIDA`, `REDIGIDA` 61, `EM AVALIAÇÃO` 4 |  | 65/2652 (2%) | Notificação extrajudicial ao cliente que foi "roubado": REDIGIDA em 61 casos (56 ROUBADO). Opções PENDENTE/ENVIADA/RECEBIDA/RESPONDIDA nunca usadas. |
| PROVIDENCIAS | `fld0Do0Zk6nGI8kNO` | singleLineText |  |  | 104/2652 (4%) | Texto livre usado como to-do: `NOTIFICAR` (66, quase todos ROUBADO/RECEBIDO POR ELES), `TRAVAR O RECEBIMENTO`, `TRAVAR ULTIMA PARCELA`… |
| SUCUMBENCIA % | `fldVloHxj2m98LYxt` | singleLineText |  |  | 259/2652 (10%) | Texto: `5%`, `10%`, `15%` e um `2500%` (erro). Percentual de honorários sucumbenciais fixado na sentença (art. 791-A CLT: 5 a 15%). |
| CLIENTE AVISADO? | `fldgSW5GHxJI2c8Y5` | checkbox | marcados: 9 |  | 9/2652 (0%) |  |
| CAPTADOR | `fldn2UE1d7hIltlEL` | multipleRecordLinks | → FUNCIONARIOS (inverso: `PROCESSUAL`) · 1 só |  | 1388/2652 (52%) |  |
| TELEFONE | `fldM8NaPLZgRl8xYO` | singleLineText |  |  | 2229/2652 (84%) | Texto (na PRÉ é phoneNumber). |
| ASSINATURA | `fldfX0YrunL0RcS8B` | date | l |  | 114/2652 (4%) | Data de assinatura do contrato — 4% aqui, 58% na CÓPIA. |
| status_disparo | `fld7ybzbPpxSUuz7S` | singleLineText |  |  | 612/2652 (23%) | **[n8n]** Escrito pelo n8n/script (ver PRE). 60 `aniversario_erro`. |
| tipo_disparo | `fldilA0CkqowpHrwU` | singleLineText |  |  | 559/2652 (21%) | **[n8n]** Idem. |
| data_solicitacao_disparo | `flddnHA8qxPagMTVL` | singleLineText |  |  | 612/2652 (23%) | **[n8n]** Idem. |
| responsavel_interno | `fldpy6hzz9JmvGF52` | singleLineText |  |  | 550/2652 (21%) | **[n8n]** Idem. |
| solicitante_disparo | `fldngD5lXI6tVGcSq` | singleLineText |  |  | 550/2652 (21%) | **[n8n]** Idem. |
| Created By | `fldt1iwzwXFOe7Eiz` | lastModifiedTime |  |  | 2652/2652 (100%) | **Nome enganoso**: o tipo é `lastModifiedTime`, não createdBy. |
| DATA PERÍCIA TECNICA | `fldvmVtg1ynyvyMW5` | dateTime | l |  | 10/2652 (0%) |  |
| DATA PERÍCIA MÉDICA | `fldrXrmogGDUotQoh` | dateTime | l |  | 5/2652 (0%) |  |
| NASCIMENTO | `flda88gB2QLJzqX5d` | date | D/M/YYYY |  | 1321/2652 (50%) | 50% preenchido; o script de aniversário busca também no PRÉ ligado. |
| MOTIVO | `fld2sglKUtrY89Qye` | singleLineText |  |  | 1/2652 (0%) | 1 registro ("SEM TESTEMUNHA"). Sem função clara. |
| _BACKUP_VALOR_ANTES_SCRIPT | `fld6Ob4Iz67W5SOjB` | singleLineText |  |  | 233/2652 (9%) | **[lixo]** **Lixo técnico**: backup feito em 03 e 06/07/2026 antes de um script reescrever VALOR/COMPLEXIDADE em 233 registros. Não migrar. |
| _BACKUP_COMPLEXIDADE_ANTES_SCRIPT | `fldImV7gyBd4pCLvd` | singleLineText |  |  | 181/2652 (7%) | **[lixo]** Idem. |
| _BACKUP_FEITO_EM_SCRIPT | `fldQBABT58Z5thviS` | singleLineText |  |  | 233/2652 (9%) | **[lixo]** Idem (data do backup). |
| PARCELAS | `fldKuQ5Nk3oDJKgrs` | number |  |  | 108/2652 (4%) | Nº de parcelas do acordo/pagamento. |

## PÓS PROCESSUAL — `tblEInHoBmUuuShxk` (556 registros)

Controle o pós-processo: repasses, recebimentos e arquivamento dos casos.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| N° DO PROCESSO | `fld9mP0tgsxUskRUk` | singleLineText |  |  | 544/556 (98%) |  |
| PROCESSUAL | `fldU96KT0xLEKEqTR` | multipleRecordLinks | → PROCESSUAL (inverso: `POS PROCESSUAL`) · 1 só |  | 455/556 (82%) |  |
| RESULTADO FINAL | `fldsprvUfBAJvkn5v` | multilineText |  |  | 87/556 (16%) | Copiado de PROCESSUAL.RESULTADO pela automação; 16% preenchido. |
| VALOR RECEBIDO CLIENTE | `fldffOZ2m1k24WKmv` | currency | R$ 2 casas |  | 99/556 (18%) |  |
| VALOR HONORARIOS | `fldQ8CSjqZKxNs1zN` | currency | R$ 2 casas |  | 66/556 (12%) |  |
| VALOR SUCUMBENCIA | `fld5bNSeZULhtm1z6` | currency | R$ 2 casas |  | 67/556 (12%) |  |
| STATUS RECEBIMENTO | `fldjVs3BRdXuZ1ous` | singleSelect | `Aguardando`, `Pago parcial` 1, `Pago total`, `Recebido`, `Parcialmente Recebido`, `Não Recebido`, `Aguardando Recebimento`, `CONCLUIDO` 47, `PENDENTE` 11, `PARCELAMENTO CPC` 2, `PAGO PARCIALMENTE` 1, `PAGAMENTO EM DIA` 15, `PAGAMENTO ATRASADO` 1, `AGUARDANDO PAGAMENTO` 2 |  | 80/556 (14%) | **Duas famílias de opções**: as originais em Title Case (Aguardando, Pago total, Recebido, Não Recebido…) nunca usadas, e as copiadas de PROCESSUAL.STATUS PAGAMENTO (CONCLUIDO, PENDENTE…) que a automação grava. `Pago parcial` e `PAGO PARCIALMENTE` coexistem. |
| STATUS REPASSE | `fldH73Oe7hXIVU8gn` | singleSelect | `Aguardando`, `Efetuado`, `Repassado`, `Parcialmente Repassado`, `Não Repassado`, `Aguardando Repasse` |  | 0/556 (0%) | **Vazio em 100%** — o repasse ao cliente não é controlado aqui. |
| STATUS ARQUIVAMENTO | `fldRXQMrAUjP7XTFb` | singleSelect | `Não arquivado`, `Arquivado` 37, `Em andamento` 30 |  | 67/556 (12%) | 12% preenchido. `Não arquivado` nunca usado. |
| RESPONSAVEL | `flduzeLbJpPQfDsRb` | multipleRecordLinks | → FUNCIONARIOS (inverso: `POS PROCESSUAL`) · 1 só |  | 211/556 (38%) |  |
| EVENTOS | `fldXAKlcH7qnnDtnN` | singleLineText |  |  | 0/556 (0%) | Vazio em 100%. |
| DATA DE ASSINATURA | `fldoIShmhcL6p50mf` | date | l |  | 0/556 (0%) | Vazio em 100%. |
| PROCESSUAL copy | `fldjgR4odQVppdd76` | multipleRecordLinks | → CÓPIA DA PROCESSUAL (NÃO MEXER) (inverso: `POS PROCESSUAL`) |  | 436/556 (78%) | **[legado]** **Legado**: link para a CÓPIA DA PROCESSUAL (inverso de CÓPIA.POS PROCESSUAL). 434 registros têm os dois links; 99 não têm nenhum. |

## FUNCIONARIOS — `tblisgqzJvF0EUFr1` (72 registros)

Centralize os dados de todos os funcionários e seus papéis nos casos.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| NOME | `fld4vMwXvl02w9SKT` | singleLineText |  |  | 72/72 (100%) |  |
| FUNCOES | `fldFrbKtMbkw22Xkw` | multipleSelects | `Captador` 20, `Entrevistador` 7, `Advogado` 23, `Responsável Inicial` 7, `Outro` 1, `Administrativo` 3, `Financeiro` 1, `TI` 4, `Gestor` 5, `Juridico` 13, `Correspondente` 1, `Testemunhas` 3, `CEO`, `Documentação` 2, `Atendimento` 1, `Publicação` 1 |  | 66/72 (92%) | Papéis (multi): Advogado 23, Captador 20, Juridico 13, Entrevistador 7, Responsável Inicial 7, Gestor 5, TI 4… `CEO` existe e não é usado. 36 dos 72 estão INATIVO. |
| STATUS | `fldshQnOdcryOtSSG` | singleSelect | `ATIVO` 35, `INATIVO` 36 |  | 71/72 (99%) |  |
| OBSERVACOES | `fldiYwZR5carDh1Fa` | multilineText |  |  | 5/72 (7%) |  |
| VINCULADOS EM PRÉ PROCESSUAIS | `fld45ySggxcVGXtqE` | count | conta `PRE PROCESSUAL` |  | 72/72 (100%) |  |
| VINCULADOS EM PROCESSUAL | `fldsU7vtvEiEYCI49` | count | conta `PROCESSUAL` |  | 72/72 (100%) |  |
| Vinculados Pós Processual | `fldGY57cOYsiSSjXz` | count | conta `POS PROCESSUAL` |  | 72/72 (100%) |  |
| PRE PROCESSUAL | `fldbtWNLkdEYNr7sM` | multipleRecordLinks | → PRE PROCESSUAL (inverso: `CAPTADOR`) |  | 15/72 (21%) |  |
| PROCESSUAL | `fld312t1O55vdmsTO` | multipleRecordLinks | → PROCESSUAL (inverso: `CAPTADOR`) |  | 16/72 (22%) |  |
| POS PROCESSUAL | `fldjm90NmYClUZSAe` | multipleRecordLinks | → PÓS PROCESSUAL (inverso: `RESPONSAVEL`) |  | 18/72 (25%) |  |
| PRE PROCESSUAL (ENTREVISTADOR) | `fldeMPgdqUz3V6NFx` | multipleRecordLinks | → PRE PROCESSUAL (inverso: `ENTREVISTADOR`) |  | 17/72 (24%) |  |
| PRE PROCESSUAL (RESPONSAVEL INICIAL) | `fld2pGLJ6wS9nAiiO` | multipleRecordLinks | → PRE PROCESSUAL (inverso: `RESPONSAVEL INICIAL`) |  | 11/72 (15%) |  |
| PROCESSUAL (ADVOGADO) | `fldogyJ0qD1QOHmgr` | multipleRecordLinks | → PROCESSUAL (inverso: `ADVOGADO`) |  | 25/72 (35%) |  |
| PROCESSUAL 2 | `fldgszRDyGpSCT531` | multipleRecordLinks | → PROCESSUAL (inverso: `RESP ADVIDEO`) |  | 0/72 (0%) | **[legado]** Vazio em 100%; link sem uso. |
| PROCESSUAL copy | `flds8NNw1ofgSVf73` | multipleRecordLinks | → CÓPIA DA PROCESSUAL (NÃO MEXER) (inverso: `CAPTADOR`) |  | 29/72 (40%) | **[legado]** **Legado** (dois campos com o mesmo nome): inversos de CÓPIA.CAPTADOR e CÓPIA.ADVOGADO. |
| PROCESSUAL copy | `fldNnj3vDWbBtg9uG` | multipleRecordLinks | → CÓPIA DA PROCESSUAL (NÃO MEXER) (inverso: `ADVOGADO`) |  | 23/72 (32%) | **[legado]** **Legado** (dois campos com o mesmo nome): inversos de CÓPIA.CAPTADOR e CÓPIA.ADVOGADO. |
| TESTEMUNHAS | `fldUOTBlsE2Q5YSZu` | multipleRecordLinks | → TESTEMUNHAS (inverso: `CAPTADOR`) |  | 10/72 (14%) |  |
| ntfy_topic | `fldEQpbSqdZy2Oxqq` | singleLineText |  |  | 35/72 (49%) | Tópico do ntfy (push) de cada colaborador — usado pelo n8n para avisar. 35 preenchidos. |
| ntfy_ativo | `fldcLfpwxzdL9IZmu` | singleSelect | `ATIVO` 19, `INATIVO` 9 |  | 28/72 (39%) | Liga/desliga o push. |
| rec_id | `fld8J8UwoHuFSIeeo` | formula | `RECORD_ID()` | Displays the unique Airtable record ID for each row. | 72/72 (100%) | Fórmula RECORD_ID(), para o n8n. |

## TESTEMUNHAS — `tbl9nZjfmxqVy60NM` (424 registros)

Centraliza e organiza dados completos e status das testemunhas vinculadas a processos e empresas.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| NOME TESTEMUNHA | `fldrHyp7RMyfHsWGS` | singleLineText |  |  | 422/424 (100%) |  |
| TELEFONE TESTEMUNHA | `fldEQLHWzqOnwZBrA` | phoneNumber |  |  | 415/424 (98%) |  |
| CPF | `fldzAzyQWU6CVmIMc` | singleLineText |  |  | 381/424 (90%) |  |
| VINCULO | `fldrxRtZFJi3UuXpH` | singleSelect | `COLEGA DE TRABALHO` 254, `EX-COLEGA` 18, `GESTOR/SUPERVISOR`, `TERCEIRO`, `NAO INFORMADO` 8 |  | 280/424 (66%) |  |
| CAPTADOR | `fldDYCfV1rMBFPKcd` | multipleRecordLinks | → FUNCIONARIOS (inverso: `TESTEMUNHAS`) · 1 só |  | 84/424 (20%) |  |
| EMPRESA | `fld4PE2tWssCXwqgo` | multipleRecordLinks | → EMPRESAS (inverso: `TESTEMUNHAS`) · 1 só |  | 224/424 (53%) |  |
| ENDEREÇO | `fldK3eRkTTQAsZ7Zy` | singleLineText |  |  | 305/424 (72%) |  |
| ARQUIVOS ENVIADOS PELA TESTEMUNHA | `fldqV2SomcjvHG84r` | multipleAttachments |  |  | 7/424 (2%) |  |
| DATA DE ADMISSÃO | `fldw9M4F91aiLnb4p` | date | l |  | 18/424 (4%) |  |
| HORARIO DE TRABALHO | `fld6TKjssQyjxuV6p` | singleLineText |  |  | 45/424 (11%) |  |
| TEM PROCESSO? | `fldAqPD3ogsosM3PD` | singleSelect | `SIM` 29, `NÃO` 139 |  | 168/424 (40%) |  |
| STATUS TESTEMUNHA | `fldkwGHMugckeWh7j` | singleSelect | `A CONFIRMAR` 73, `CONFIRMADA` 196, `DESCARTADA`, `NAO USAR`, `PENDENTE` 155 |  | 424/424 (100%) |  |
| COBRANÇA | `fld7u0W3vbAk3vOIY` | singleSelect | `1º` 162, `2º`, `3º`, `4º` |  | 162/424 (38%) | Contador de cobranças (1º..4º); só `1º` usado. Os ids das opções 1º/2º/4º são **os mesmos ids** de A CONFIRMAR/CONFIRMADA/DESCARTADA de STATUS TESTEMUNHA — campo duplicado por cópia. |
| DATA ULTIMO CONTATO | `fldeil2kdiLHeVTs5` | date | l |  | 212/424 (50%) |  |
| OBSERVACOES | `fldMmEx19k0nHEaj3` | multilineText |  |  | 54/424 (13%) |  |
| TESTEMUNHA DE: | `fld0YIS1gw5thKMXl` | multipleRecordLinks | → PROCESSUAL (inverso: `TESTEMUNHAS`) |  | 323/424 (76%) | Link para PROCESSUAL (o rótulo do formulário diz "NOSSO CLIENTE NA FASE PROCESSUAL"). Dois pontos no nome distinguem do campo irmão. |
| TESTEMUNHA DE | `fld8Ju3YQHmrg9H9U` | multipleRecordLinks | → PRE PROCESSUAL (inverso: `TESTEMUNHAS`) |  | 174/424 (41%) | Link para PRE PROCESSUAL. **Atenção**: no formulário COMERCIAL os rótulos estão trocados (chama este de "ETAPA PROCESSUAL"). |
| ENVIAR MENSAGEM | `fldbdxC9rd85oPaa2` | button |  | Gera uma URL para disparo de mensagem incluindo todos os campos desta tabela. | 424/424 (100%) |  |
| DUPLICADO? | `fldowrtPW27eUtbuR` | singleSelect | `SIM` 1, `NAO` 8 |  | 9/424 (2%) |  |
| ENCONTROU NOSSO CLIENTE NA ETAPA PROCESSUAL | `fldNribYFmmGfLh9K` | singleSelect | `SIM ACHEI O CLIENTE NA PROCESSUAL` 43, `NÃO ACHEI O CLIENTE NA PROCESSUAL` 1 |  | 44/424 (10%) |  |
| origem_testemunha | `fldSkTfJWuY8F6KgI` | singleSelect | `COMERCIAL` 36, `JURIDICO` 330 |  | 366/424 (86%) | JURIDICO (cadastro interno) × COMERCIAL (formulário do captador). A automação marca COMERCIAL ao submeter o form comercial. |
| status_disparo | `fldWvBPCjQg8b7U04` | singleLineText |  |  | 332/424 (78%) | **[n8n]** Escrito pelo n8n (PENDENTE/enviada/BLOQUEADO/EM PROCESSAMENTO). |
| tipo_disparo | `fld3UuiNQyV8IMcJc` | singleLineText |  |  | 332/424 (78%) | **[n8n]** Idem (evento, compromisso, lembrete…). |
| data_solicitacao_disparo | `fldANhrX8JEGGx0Cf` | singleLineText |  |  | 332/424 (78%) | **[n8n]** Idem. |
| responsavel_interno | `fldHkFricEmDUZq7G` | singleLineText |  |  | 162/424 (38%) | **[n8n]** Idem. |
| solicitante_disparo | `fldBu4DURpSoRMhT1` | singleLineText |  |  | 135/424 (32%) | **[n8n]** Idem. |
| Created By | `fldLJM2Ul23O6hUtr` | createdBy |  |  | 424/424 (100%) |  |
| origem_comercial_tabela_id | `fldhQcu6eQAm7fhcP` | singleLineText |  |  | 0/424 (0%) | Vazio em 100%. |
| origem_comercial_registro_id | `fldR5XpQnKUDPrgiO` | singleLineText |  |  | 36/424 (8%) |  |
| notif_captador_status | `fldO1rJSSpWyDd4i1` | singleSelect | `NOTIFICADO` 3, `PENDENTE` 83, `ERRO AO ENVIAR`, `IGNORADO` 19, `ENVIANDO` 4, `PENDENTE DE DADOS` 260, `BLOQUEADO DUPLICIDADE` 5 |  | 374/424 (88%) | **[n8n]** Máquina de estados do n8n para avisar o captador: PENDENTE DE DADOS → PENDENTE → ENVIANDO → NOTIFICADO / ERRO AO ENVIAR / IGNORADO / BLOQUEADO DUPLICIDADE. |
| notif_captador_ultimo_envio | `fldg5OgxicfYCFNMp` | dateTime | YYYY-MM-DD |  | 28/424 (7%) | **[n8n]**  |
| AINDA TRABALHA NA EMPRESA? | `fldQyw23638IeGoSU` | singleSelect | `SIM`, `NÃO` 1 | Resposta informada pela própria testemunha no formulário público. | 1/424 (0%) |  |
| DATA DE DEMISSÃO | `fldFsISkknfBG2uCk` | date | l | Data informada pela própria testemunha quando não trabalha mais na empresa. | 1/424 (0%) |  |
| LINK DA TESTEMUNHA | `fldR3LD4dY3w2wtof` | formula | `IF(COUNTA({fld4PE2tWssCXwqgo}) = 0, "Cadastre a empresa antes de gerar o link da testemunha.", "https://n8n.ggvadv.com/webhook/testemunha-atualizar-dados?rid=" & RECORD_ID())` | Link público individual para a própria testemunha revisar e atualizar seus dados. Exibe aviso quando EMPRESA estiver vazia. | 424/424 (100%) | Fórmula: URL pública do n8n `testemunha-atualizar-dados?rid=` para a própria testemunha atualizar dados; avisa se EMPRESA vazia. |
| CADASTRADO POR | `fldiJxmCEeuxTtcS4` | singleLineText |  | Nome canônico do colaborador humano que realizou o cadastro no Formulário Interno Único de Testemunhas. O valor é revalidado server-side pelo n8n. | 0/424 (0%) | Vazio em 100% (previsto para o Formulário Interno Único, ainda não em uso). |
| ÚLTIMA ALTERAÇÃO POR | `fldBKvxASKPHrRRnP` | singleLineText |  | Nome canônico do colaborador autenticado que realizou a última alteração pelo formulário interno. | 0/424 (0%) | Vazio em 100%. |
| ÚLTIMA ALTERAÇÃO EM | `fldsKOswTUpLC2mEr` | singleLineText |  | Timestamp ISO 8601 da última alteração realizada pelo formulário interno. | 0/424 (0%) | Vazio em 100%. |

## EMPRESAS — `tblkfWQhjp2F1dK0y` (1103 registros)

Registre empresas envolvidas em litígios e seus vínculos processuais.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| EMPRESA | `fld8PWuRCXVfhxTym` | singleLineText |  |  | 1103/1103 (100%) |  |
| SEGMENTO | `fldFIha0DxiXkcTnz` | singleLineText |  |  | 11/1103 (1%) | 1% preenchido. |
| STATUS EMPRESA | `fld1oC98eM8PyYXnj` | singleSelect | `ATIVA` 285, `INATIVA`, `EM RECUPERACAO` 9 |  | 294/1103 (27%) | 27% preenchido (ATIVA 285, EM RECUPERACAO 9; INATIVA nunca usada). |
| HIST. PAGAMENTO | `fldZFSd2f9WKgXmAX` | singleSelect | `BOA` 5, `RUIM` 1, `PÉSSIMA` 1 |  | 7/1103 (1%) |  |
| BENS IDENTIFICADOS | `fld5RoWyzrwCrlyhF` | singleSelect | `SIM` 1, `NÃO` 14 |  | 15/1103 (1%) |  |
| QTD PRE PROCESSUAIS | `fld5kiPkQs0NgUmHR` | count | conta `PRE PROCESSUAL` |  | 1103/1103 (100%) |  |
| QTD PROCESSOS | `fldvQDr03ufTK6Rox` | count | conta `PROCESSUAL` |  | 1103/1103 (100%) |  |
| PRE PROCESSUAL | `fldD5vMVGmZWK8kV9` | multipleRecordLinks | → PRE PROCESSUAL (inverso: `EMPRESA`) |  | 268/1103 (24%) |  |
| PROCESSUAL | `fldoLaOZc58DQTQYK` | multipleRecordLinks | → PROCESSUAL (inverso: `EMPRESA`) |  | 448/1103 (41%) |  |
| TESTEMUNHAS | `fldTSCNT3dxkNcOwd` | multipleRecordLinks | → TESTEMUNHAS (inverso: `EMPRESA`) |  | 77/1103 (7%) |  |
| Conferência de Faltantes | `fldv9zdBAoyq6l1pk` | multipleRecordLinks | → Conferência de Faltantes (inverso: `EMPRESA`) |  | 273/1103 (25%) |  |
| PROCESSUAL copy | `fldNSV8upoiovsDcZ` | multipleRecordLinks | → CÓPIA DA PROCESSUAL (NÃO MEXER) (inverso: `EMPRESA`) |  | 786/1103 (71%) | **[legado]** **Legado**: inverso de CÓPIA.EMPRESA — 786 empresas ligadas à cópia contra 448 à PROCESSUAL. |
| TEMP_RECORD_ID | `fldsJ6npBmOeQEmBf` | formula | `RECORD_ID()` |  | 1103/1103 (100%) | **[legado]** Fórmula RECORD_ID(); temporário de importação. |
| GGV_RECORD_KEY | `fld5PYHnY54f43Bn6` | multilineText |  |  | 586/1103 (53%) | Chave de 17 caracteres gravada em 586 empresas por script de deduplicação [CONFIRMAR uso]. |
| FRAGILIDADES | `fldwMi9cllR7nByNy` | multipleRecordLinks | → FRAGILIDADES (inverso: `EMPRESA`) |  | 1/1103 (0%) |  |

## Conferência de Faltantes — `tblnQHm5yTj2EPscB` (1067 registros)

Processos do escritório que ainda NÃO estão na PROCESSUAL. Glauco confere os dados + fase recomendada (Datajud) e marca "VALIDAR E SUBIR" pra promover (via automação) pra PROCESSUAL.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| NOME | `fldiXouLVt5bEmWQV` | singleLineText |  |  | 1067/1067 (100%) |  |
| Nº PROCESSO | `fldTdMHygimECEwsK` | singleLineText |  |  | 1067/1067 (100%) |  |
| EMPRESA | `fldRDowg9rI1KpNFA` | multipleRecordLinks | → EMPRESAS (inverso: `Conferência de Faltantes`) |  | 1020/1067 (96%) |  |
| VALOR | `fldeG3B32zeCC2WPi` | currency | R$ 2 casas |  | 600/1067 (56%) |  |
| TRT | `fldnL40KBxnjAeqNN` | singleLineText |  |  | 1067/1067 (100%) |  |
| VARA | `fldtiCR5qTUWTaUn0` | singleLineText |  |  | 1067/1067 (100%) |  |
| DISTRIBUIÇÃO | `fldB7NroOPiW7QA9R` | date | D/M/YYYY |  | 589/1067 (55%) |  |
| FASE RECOMENDADA (DATAJUD) | `fldzmstT8o14h8nzN` | singleLineText |  |  | 907/1067 (85%) | Texto vindo do Datajud: CONHECIMENTO 446, EXECUÇÃO 326, ENCERRADO 73, DESISTENCIA 43, ACORDO 17, RECURSAL 2; 160 vazios. |
| STATUS RECOMENDADO (DATAJUD) | `fldenynnXu7l80Moi` | singleLineText |  |  | 644/1067 (60%) | EXECUCAO 326, TRÂNSITO EM JULGADO 185, ARQUIVADO 73, DESISTENCIA 43, ACORDO 17. |
| ÚLTIMO MOVIMENTO (DATAJUD) | `fldsfbRUpv15Qf5kX` | singleLineText |  |  | 908/1067 (85%) |  |
| OBSERVAÇÕES | `fldsLUyWvVvrTpWRO` | multilineText |  |  | 402/1067 (38%) |  |
| ✅ VALIDAR E SUBIR | `fld4U33RUENZEmE55` | checkbox | marcados: 0 |  | 0/1067 (0%) | **Ninguém marcou** (0/1067) e **não existe automação** ligada a ele — a descrição da tabela promete uma que não foi criada. |
| STATUS PROCESSO | `fldas5l0gp8vqKyXv` | singleLineText |  |  | 326/1067 (31%) | Só `ARQUIVADO` (326). |

## CÓPIA DA PROCESSUAL (NÃO MEXER) — `tblvyoun2V0CQKmxF` (3722 registros)

(mesma descrição da PROCESSUAL) Acompanhe detalhadamente fases, partes e finanças de processos trabalhistas.

**Por que existe e por que tem 3.722 registros (a PROCESSUAL tem 2.652)** — ver `leitura-juridica.md`, seção "Qual PROCESSUAL é a fonte". Em resumo: é uma duplicação da PROCESSUAL feita em maio/jun/ago de 2026 (Created By: Pedro 2.855, Glauco 603) que recebeu (a) 1.187 processos a mais — 1.048 deles ENCERRADOS e 539 também listados na Conferência de Faltantes, ou seja, o **passivo histórico** que nunca entrou na PROCESSUAL — e (b) o enriquecimento do pipeline de 31/08/2026 (DATA SENTENCA, MAGISTRADO, RESULTADO RECURSO, CPF, CNPJ, TST, honorários por base). Dos 2.538 números da PROCESSUAL, 2.516 estão na cópia; só 22 (criados de mai a set/2026) e os 106 sem número não estão.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| NOME | `fldcmfFZHPf1hduFj` | singleLineText |  |  | 3722/3722 (100%) |  |
| Nº PROCESSO | `fldvP4t6aNYcOoFcv` | singleLineText |  |  | 3722/3722 (100%) |  |
| DISTRIBUIÇAO | `fldQj4QvumWoy3XCs` | date |  |  | 3722/3722 (100%) |  |
| VARA | `fld0dpB84odelzYE8` | singleLineText |  |  | 3722/3722 (100%) |  |
| TRT | `fldNjTzo9HaumzYe8` | singleSelect | `(vazio)`, `(vazio)`, `1ª` 42, `2ª` 3502, `3ª` 11, `4ª` 18, `5ª` 3, `6ª` 2, `7ª` 3, `8ª` 4, `9ª` 2, `10ª` 2, `11ª`, `12ª` 10, `13ª`, `14ª` 2, `15ª` 97, `16ª` 1, `17ª` 3, `18ª` 16, `19ª` 1, `20ª`, `21ª` 2, `22ª`, `23ª`, `24ª` 1 |  | 3722/3722 (100%) | Duas opções com nome vazio. |
| VALOR | `fldtpiJdqwvzSRchp` | currency |  |  | 3722/3722 (100%) |  |
| EMPRESA | `fldQr8KII3fj6RaEn` | multipleRecordLinks | EMPRESAS |  | 3722/3722 (100%) |  |
| COMPLEXIDADE | `fldr2WHDjAuXmSEd9` | singleSelect | `A` 179, `B` 1399, `C` 2144 |  | 3722/3722 (100%) |  |
| ADVOGADO | `fldFtmUazPjgT5Vba` | multipleRecordLinks | FUNCIONARIOS |  | 1812/3722 (49%) |  |
| FASE PROCESSUAL | `fldpZfbG3Dj4oJOnC` | singleSelect | `ACORDO` 14, `CONHECIMENTO` 572, `DESISTENCIA` 1, `RECURSAL` 498, `ENCERRADO` 2541, `EXECUÇÃO` 72, `EXECUÇÃO DEFINITIVA` 10, `EXECUÇÃO PROVISÓRIA` 10, `RECEBENDO` 1, `INAPLICÁVEL ` 3 |  | 3722/3722 (100%) | Ganhou `INAPLICÁVEL ` (3). ENCERRADO em 68% (contra 18% na PROCESSUAL) — a cópia foi atualizada pelo pipeline. |
| STATUS DO PROCESSO | `fldPBWPDPunT9Il3G` | singleSelect | `ACORDO` 30, `AGUARDANDO AUDIÊNCIA` 472, `AGUARDANDO SENTENÇA` 24, `ARQUIVADO` 2549, `DESISTENCIA`, `EXECUCAO` 303, `RECEBIDO POR ELES` 29, `RECUPERADO` 21, `REDISTRIBUIR` 1, `ROUBADO` 124, `TRÂNSITO EM JULGADO` 25, `SOBRESTADO` 12, `AGUARDANDO ACORDAO` 129, `INAPLICÁVEL` 3 |  | 3722/3722 (100%) | Ganhou `AGUARDANDO ACORDAO` (129) e `INAPLICÁVEL`. |
| ENVIAR MENSAGEM | `fldk8X85hMO02Sx3b` | button |  |  | 3722/3722 (100%) |  |
| STATUS CONHECIMENTO | `fld4PTXQ5VK9uY6X3` | singleSelect | `AGUARDANDO AUDIÊNCIA` 624, `ADVIDEO`, `AGUARDANDO PERICIA` 3, `ACORDO EM ANDAMENTO` 32, `AGUARDANDO SENTENÇA` 10, `AUSÊNCIA` 126, `DESISTÊNCIA` 219, `SENTENCIADA` 1687, `ARQUIVADO` 46 |  | 2747/3722 (74%) |  |
| MOTIVO | `fldYEwcnX5KDpfgop` | singleLineText |  |  | 4/3722 (0%) |  |
| SENTENCA | `fldIODL3MBKzthFpK` | singleSelect | `RUIM` 1028, `ÓTIMA` 111, `MÉDIA` 178 |  | 1317/3722 (35%) |  |
| DECISAO SENTENCA | `fldrUKtuvmfUIA3ut` | singleSelect | `PARCIALMENTE PROCEDENTE` 1219, `IMPROCEDENTE` 446, `PROCEDENTE` 70, `EXTINTO S/ RESOLUCAO DO MERITO` 383 |  | 2118/3722 (57%) | Ganhou `EXTINTO S/ RESOLUCAO DO MERITO` (383). 57% preenchido contra 18% na PROCESSUAL. |
| RESULTADO ACORDAO | `fldXoF3mU8Vl7P4Yy` | singleSelect | `RUIM` 238, `MÉDIO` 203, `ÓTIMO` 84 |  | 525/3722 (14%) |  |
| ULTIMA DECISAO | `fldu4Z2qYKoXOcpIf` | singleSelect | `RUIM` 582, `ÓTIMA` 159, `MÉDIA` 190, `SEM DECISÃO` 36, `IMPROCEDENTE` 5, `PROCEDENTE` 53 |  | 1025/3722 (28%) |  |
| DATA SENTENCA | `fldVyWVyQoo9SDuaE` | date |  | Data da sentença de mérito, extraída da intimação AASP. Preenchida automaticamente. | 2067/3722 (56%) |  |
| DATA ACORDAO | `fldDG9LKLVsZOT9Pg` | date |  |  | 1489/3722 (40%) |  |
| MAGISTRADO | `fld6mw1fPKilW87WA` | singleLineText |  | Magistrado(a) que assinou a DECISÃO TERMINATIVA de 1º grau encontrada nos autos: sentença de mérito OU homologação de acordo/desistência — em ~45% dos casos é o juiz que homologou a conciliação (às vezes de mutirão/CEJUSC), NÃO o julgador de mérito. Para análise de êxito por magistrado, filtrar pelos registros cuja DECISAO SENTENCA esteja preenchida (mérito). Fonte: varredura do acervo (juizes_sentencas v2, 31/08/2026), filtro de sanidade aplicado; onde a extração não identificou o nome, ficou vazio. Preenchimento automático, só em campo vazio. | 1999/3722 (54%) |  |
| CLASSIFICACAO | `fldVHQhm4VVw91MvJ` | singleSelect | `RT - ORDINÁRIO` 297, `AT - SUMARÍSSIMO` 377, `AT - ORDINÁRIO` 2695, `AT - SUMÁRIO`, `EXECUCAO PROVISORIA` 194, `EMBARGOS DE TERCEIRO` 6, `RRAg`, `AIRR`, `RR`, `Emb`, `EXECUCAO DEFINITIVA` 105 |  | 3674/3722 (99%) | Ganhou classes de execução e recursais (EXECUCAO PROVISORIA/DEFINITIVA, EMBARGOS DE TERCEIRO, RR, AIRR, RRAg, Emb) — mistura rito com classe do incidente. |
| DATA AUDIENCIA | `fldn0bZKGzzg86uQq` | dateTime |  |  | 3007/3722 (81%) |  |
| AUDIENCIA | `fldfn7q0rBFVuInlK` | singleSelect | `INICIAL` 216, `INSTRUÇÃO` 867, `HOMOLOGAÇÃO`, `UNA` 1210, `INSTRUCAO/VIDEO` 144, `CONCILIAÇÃO EM EXECUÇÃO` 118, `UNA-RS/VIDEO` 26, `UNA-RS` 141, `INICIAL/VIDEO` 64, `UNA/VIDEO` 90, `JULGAMENTO` 22 |  | 2898/3722 (78%) | Ganhou variantes /VIDEO, UNA-RS, CONCILIAÇÃO EM EXECUÇÃO, JULGAMENTO — modalidade e tipo no mesmo campo. |
| Nº  CumPrSe | `fld1cGAki3SIlZbR1` | singleLineText |  |  | 381/3722 (10%) |  |
| RESULTADO | `fldHmpf2oiTu20L52` | multilineText |  |  | 106/3722 (3%) |  |
| STATUS RECURSAL | `fldE3tgRGu0IOWPnr` | singleSelect | `TST` 811, `AGUARDANDO JULGAMENTO` 414 |  | 1225/3722 (33%) |  |
| STATUS CumPrSe | `fldMqtTCoxi3EZ6E7` | singleSelect | `ACORDO`, `AGUARDANDO SENTENÇA` 2, `DECISÃO POSITIVA EM 1ª INSTÂNCIA` 1, `DECISÃO POSITIVA EM 2ª INSTÂNCIA` 2, `FASE DE CÁLCULOS` 9, `PERICIA CONTÁBIL` 1, `RECEBIDO` 5, `SOBRESTADO` 1 |  | 21/3722 (1%) |  |
| STATUS DO CALCULO | `fldYUfMIYMpbhBrv7` | singleSelect | `HOMOLOGADO` 616, `JUNTADO AOS AUTOS` 37, `PENDENTE` 11 |  | 664/3722 (18%) |  |
| CALCULO RCTE | `fld7voVZAMyswcV0j` | currency |  |  | 628/3722 (17%) |  |
| SUCUMB RCTE | `fldfDoq1ys1aGn0J2` | currency |  |  | 341/3722 (9%) |  |
| CALCULO RCDA | `fld047wJ57Sr1aT4x` | currency |  |  | 268/3722 (7%) |  |
| SUCUMB RCDA | `fldYWU9g1mgagHtyQ` | currency |  |  | 249/3722 (7%) |  |
| SUCUMB HOM | `fldMeo5CAPSmG5KQx` | currency |  |  | 390/3722 (10%) |  |
| VALOR HOM | `fldfDKXANsQ2fftjh` | currency |  |  | 582/3722 (16%) |  |
| STATUS PAGAMENTO | `fldbQjy8KFsPiGdZX` | singleSelect | `PENDENTE` 53, `CONCLUIDO` 1282, `PAGO PARCIALMENTE` 4, `AGUARDANDO PAGAMENTO` 1, `PARCELAMENTO CPC` 1, `PAGAMENTO EM DIA` 1, `PAGAMENTO ATRASADO` 1, `CESSAO DE CREDITOS` 3 |  | 1346/3722 (36%) |  |
| ENCERRAMENTO | `fldQA3V008aWgVolE` | date |  |  | 2652/3722 (71%) |  |
| DRIVE | `fld6hyVSCCrjy4HNd` | url |  |  | 3247/3722 (87%) |  |
| ASTREA | `fldOjPxn0cd09XD47` | url |  |  | 3462/3722 (93%) |  |
| OBSERVACOES | `fld9AH9a7dN1UFjO3` | multilineText |  |  | 758/3722 (20%) |  |
| PRE PROCESSUAL | `fldI2egQzyDoQNA26` | singleLineText (era link; virou texto na cópia) |  |  | 410/3722 (11%) | Virou texto na cópia (o link não sobrevive à duplicação de tabela). |
| POS PROCESSUAL | `fldk6Bc8G9oo0mVX2` | multipleRecordLinks | PÓS PROCESSUAL |  | 440/3722 (12%) |  |
| TURMA | `fldV1qxYFBzIvY7dr` | singleLineText |  |  | 1411/3722 (38%) | Aqui é **texto** (na PROCESSUAL é select poluído): 1.411 preenchidos, padronizado `Nª TURMA` + `VICE-PRESIDÊNCIA JUDICIAL`. |
| CADEIRA | `fldTn11UpgYqChRNJ` | singleLineText |  |  | 1133/3722 (30%) | Cadeira do desembargador na turma (CADEIRA 1..5). Só existe na cópia. |
| RELATOR | `fldcRZsg4HYSgn666` | singleLineText |  |  | 1339/3722 (36%) | Desembargador relator no TRT-2. Só na cópia. |
| TESTEMUNHAS | `fldrTMw8NSJt7xWXJ` | singleLineText (era link; virou texto na cópia) |  |  | 199/3722 (5%) | Idem: texto. |
| DATA ADVIDEO | `fldzwbysEw21OFH66` | dateTime |  |  | 0/3722 (0%) |  |
| RESP ADVIDEO | `fldi8Shnzt9hdNsSq` | singleLineText |  |  | 0/3722 (0%) |  |
| STATUS ADVIDEO | `fld7VrihnJYxdv4zs` | singleSelect | `FEITO` 1, `PENDENTE`, `MARCADO` |  | 1/3722 (0%) |  |
| PERICIA MEDICA | `fld0BJrdoG4Vqjq90` | checkbox |  |  | 6/3722 (0%) |  |
| PERICIA TECNICA | `fldGF9gLMUmmzwvMj` | checkbox |  |  | 11/3722 (0%) |  |
| STATUS EXECUÇÃO | `flddhvTNt3K4hNvPm` | singleSelect | `AGUARDANDO ALVARÁ` 22, `AGUARDANDO CÁLCULO` 302, `AGUARDANDO PERICIA` 6, `AGUARDANDO TRANSITO ` 47, `ARQUIVADO` 144, `AUDIÊNCIA CONCILIAÇÃO` 3, `EXTINTA S/ RESOLUÇAO` 23, `FASE DE CÁLCULOS` 50, `HOMOLOGADO` 57, `NEGOCIANDO ACORDO` 1, `PARCELAMENTO 916 CPC` 9, `PROCURANDO BENS` 29, `SOBRESTADO` 4, `RECEBIDO` 14, `RECURSO EXECUÇÃO` 82, `EXECUÇAO PROVISÓRIA` 17 |  | 810/3722 (22%) | Aqui a lista está **limpa** (16 estados) — é a lista de referência para a migração. |
| AND. NECESSÁRIO | `fldF8mxBzD5cRsL4C` | singleSelect | `PEDIR ANDAMENTO` 15, `EXPEDIÇAO DE ALVARÁ`, `TENTAR ACORDO`, `PEDIR AUD CONCILIAÇÃO`, `Alvará `, `ACORDO` 1, `Alvará` 15, `Aguardar a empresa realizar o pagamento e começar a impulsionar.` 5, `Solicitar andamento processual para que a enel realize o pagamento. ` 3, `Alvara ` 3, `Juiza dificil em Glauco, o atendente felipe disse que tentaria apressar. ` 2, `Prosseguimento` 31, `Encerrado` 63 |  | 138/3722 (4%) |  |
| AÇÃO | `fldbNuYY7kHhvPAij` | date |  |  | 192/3722 (5%) |  |
| TEL VARA | `fldzDjqJNQYrMrBOz` | phoneNumber |  |  | 167/3722 (4%) |  |
| STATUS ACORDO | `fldmPIGUEID71M0ue` | singleSelect | `ACORDO EM ANDAMENTO` 61, `ACORDO CUMPRIDO` 1317, `QUEBRA DE ACORDO` 4 |  | 1382/3722 (37%) |  |
| VALOR ACORDO | `fldsX34Hdi6gWfBOd` | currency |  |  | 918/3722 (25%) |  |
| TOTAL RECEBIDO | `flduvkfUUz051hyBl` | currency |  |  | 1081/3722 (29%) |  |
| SUCUMB RECEBIDO | `fldevSd5kepM7fqzt` | currency |  |  | 172/3722 (5%) |  |
| HONOR TOTAL | `fld6yZmxZQSqoa7GI` | currency |  |  | 1120/3722 (30%) |  |
| SITU. EMPRESA | `fld9nTJODAgIcIQtl` | multipleLookupValues (EMPRESA→STATUS EMPRESA) |  |  | 2665/3722 (72%) |  |
| BENS IDENTIFICADOS | `fldEU44SA3BMGftq0` | multipleSelects | `NÃO` 158, `SIM` 12 |  | 170/3722 (5%) |  |
| HIST. PAGAMENTO | `fldghU4b5RnjNapAS` | multipleSelects | `BOA` 275, `PÉSSIMA` 24, `RUIM` 9 |  | 308/3722 (8%) |  |
| ULTIMA MOV | `fldUVIxnej2Gd9Oe9` | singleLineText |  |  | 3412/3722 (92%) |  |
| REVOGAÇÃO | `fldlL3QF5v6Nfy6zR` | singleSelect | `SIM ` 839, `NÃO` 139, `BRUNO - juntar revogaçao nestes autos `, `BRUNO - ver se colocaram a revogaçao acima`, `ROUBADO` 1, `fazer revogaçao`, `fazer revogaçao ` 2, `SEM REVOGAÇAO - RENAN QUE ASSINOU PROCURAÇAO` 4, `ver se colocaram a revogaçao acima`, `BRUNO -tem revogaçao nos autos abaixo`, `VERIFICAR` 2, `NÃO SE APLICA` 42 |  | 1029/3722 (28%) |  |
| DATA REVOG | `fldLXyHn58qh1Set9` | date |  |  | 799/3722 (21%) |  |
| NOTIFICAÇÃO | `fld74RYjSUkhe9J8Z` | singleSelect | `PENDENTE`, `ENVIADA`, `RECEBIDA`, `RESPONDIDA`, `REDIGIDA` 76, `EM AVALIAÇÃO` 6 |  | 82/3722 (2%) |  |
| PROVIDENCIAS | `fldpK9kuxpxrnH713` | singleLineText |  |  | 127/3722 (3%) |  |
| SUCUMBENCIA % | `fldks912wlwUNkLLI` | singleLineText |  |  | 558/3722 (15%) |  |
| CLIENTE AVISADO? | `fldFZHpbUQTtHLVck` | checkbox |  |  | 9/3722 (0%) |  |
| CAPTADOR | `fldM9FYwqqrt028S0` | multipleRecordLinks | FUNCIONARIOS |  | 2218/3722 (60%) |  |
| TELEFONE | `fldbfyukYiqC0Hkc3` | phoneNumber |  |  | 2582/3722 (69%) |  |
| ASSINATURA | `fldE4LiWHGVLwLFmQ` | date |  |  | 2164/3722 (58%) |  |
| status_disparo | `fldwFWTG2IHDz3ml7` | singleLineText |  |  | 586/3722 (16%) | **[n8n]**  |
| tipo_disparo | `fldHslk7xJyh4geK9` | singleLineText |  |  | 535/3722 (14%) | **[n8n]**  |
| data_solicitacao_disparo | `fldCusUDDQZVVlG90` | singleLineText |  |  | 586/3722 (16%) | **[n8n]**  |
| responsavel_interno | `fldOFRB4MsT7afsjh` | singleLineText |  |  | 533/3722 (14%) | **[n8n]**  |
| solicitante_disparo | `fldMnopQa1geAfZ6F` | singleLineText |  |  | 533/3722 (14%) | **[n8n]**  |
| Created By | `fldS83Q4JgPzTGrwO` | createdBy |  |  | 3722/3722 (100%) | Aqui é createdBy de verdade: Pedro 2.855, Glauco 603, Automations 200, gerência 64. |
| DATA PERÍCIA TECNICA | `fldUtGNLeRxja7zak` | dateTime |  |  | 10/3722 (0%) |  |
| DATA PERÍCIA MÉDICA | `fldQ4cGTtZNF32DCw` | dateTime |  |  | 4/3722 (0%) |  |
| NASCIMENTO | `fldzfTA6f9VueZKjs` | singleLineText (na PROCESSUAL é date) |  |  | 2509/3722 (67%) | Texto (na PROCESSUAL é date). |
| RESULTADO RECURSO | `fldZkL74gu3iQgXcg` | singleSelect | `PROVIDO` 79, `PARCIALMENTE PROVIDO` 527, `NEGADO PROVIMENTO` 504, `NÃO CONHECIDO` 134 | Resultado objetivo do acórdão/recurso, extraído da intimação AASP. Não confundir com RESULTADO ACORDAO, que é nota subjetiva de qualidade. | 1244/3722 (33%) | Resultado **objetivo** do acórdão (PROVIDO / PARCIALMENTE / NEGADO / NÃO CONHECIDO) — não existe na PROCESSUAL. |
| E-MAIL | `fldgG8Hd7zpleuQ1e` | email |  | E-mail do reclamante, extraído da qualificação na petição inicial dos autos em PDF. Preenchido automaticamente. | 2165/3722 (58%) |  |
| CPF | `fldjR2BqXLKic3bLi` | singleLineText |  | CPF do reclamante, extraído da qualificação na petição inicial dos autos em PDF. Preenchido automaticamente pelo pipeline, só em campo vazio. | 3610/3722 (97%) |  |
| CNPJ RECLAMADA | `fldzoCBbwPimGJ8TO` | singleLineText |  | CNPJ e razão social da reclamada como constam na qualificação da inicial. Preenchido automaticamente pelo pipeline, só em campo vazio. | 3403/3722 (91%) |  |
| TURMA TST | `fldtI4VOrmuR4lmfB` | singleLineText |  | Turma/órgão do TST onde o recurso tramita. Preenchido a partir da Planilha Correspondente TST. Não confundir com TURMA, que é a turma do TRT-2. | 381/3722 (10%) |  |
| RELATOR TST | `fld0D2Xe2qPSYoFHE` | singleLineText |  | Ministro relator no TST. Preenchido a partir da Planilha Correspondente TST. Não confundir com RELATOR, que é o desembargador do TRT-2. | 379/3722 (10%) |  |
| ARQUIVO TST | `fldnDFmHWlZ2mIRau` | date |  | (descrição copiada de RELATOR TST — provavelmente errada) Ministro relator no TST. Preenchido a partir da Planilha Correspondente TST. | 254/3722 (7%) | Data; a descrição é cópia errada da de RELATOR TST [CONFIRMAR: data do arquivamento no TST?]. |
| HONOR  TOTAL HOMOL | `fldjTxAsINi06RGAC` | currency ($) |  |  | 601/3722 (16%) | Honorário contratual sobre o VALOR HOM (mediana 33%; moda 30%). Símbolo `$`, não `R$`. |
| HONOR TOTAL CALCULO RCDA | `fldlaGkINPddsXb6v` | currency ($) |  |  | 268/3722 (7%) | Honorário projetado sobre o cálculo da reclamada. |
| HONOR TOTAL CALCULO RCTE | `flde0ZJbihjoOHrWN` | currency ($) |  |  | 560/3722 (15%) | Honorário projetado sobre o cálculo do reclamante (moda 30%). |
| PARCELAS | `fldBn7cBdNVgFNyjF` | number |  |  | 425/3722 (11%) |  |
| VALOR PARCELA | `fldfesN5ruhEAWoAd` | currency ($) |  |  | 120/3722 (3%) |  |
| HONOR TOTAL ACORDO | `fldY0QwVVHGlnOuIc` | currency ($) |  |  | 751/3722 (20%) | Honorário sobre o acordo — **30% em 603 de 687** casos. |
| DATA DO ACORDO | `fldANF4EoWZgUQ265` | date |  |  | 951/3722 (26%) |  |

## AUDITORIA TESTEMUNHAS — `tblKp6rhoOGL2ChrO` (2 registros)

Log permanente e append-only das operações autenticadas realizadas no formulário interno de testemunhas.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| EVENTO ID | `fldx5Jbz799lWEpmU` | singleLineText |  | Chave canônica ação:operationId:registro. | 2/2 |  |
| DATA/HORA | `fldXDNL9mN1dhmg6R` | singleLineText |  | Timestamp ISO 8601 em UTC. | 2/2 |  |
| ATOR RECORD ID | `fld99aghkSNZanSqh` | singleLineText |  |  | 2/2 |  |
| ATOR NOME SNAPSHOT | `fldbuUHc90qKwRdZe` | singleLineText |  |  | 2/2 |  |
| SETOR SNAPSHOT | `fldXWLhYf8gt0Jc8l` | singleLineText |  |  | 2/2 |  |
| AÇÃO | `fldzPUtO3DQGRiICO` | singleLineText |  |  | 2/2 |  |
| TESTEMUNHA RECORD ID | `fldiWGDSICPKfqemf` | singleLineText |  |  | 2/2 |  |
| TESTEMUNHA NOME SNAPSHOT | `fldiXicuaU25o9Wie` | singleLineText |  |  | 2/2 |  |
| CONTEXTO | `fldvS9AQJX6ijETP0` | multilineText |  |  | 2/2 |  |
| CAMPOS ALTERADOS | `fldU7V6fUlyXfqNq8` | multilineText |  |  | 2/2 |  |
| ANTES | `fld0bei6vj61qmf4a` | multilineText |  |  | 2/2 |  |
| DEPOIS | `fldggIM5PoCNdX7cE` | multilineText |  |  | 2/2 |  |
| OPERATION ID | `fldUGaOLMg8R2xsNf` | singleLineText |  |  | 2/2 |  |
| RESULTADO | `fldQMmrpCSpJ5ewns` | singleLineText |  |  | 2/2 |  |
| ORIGEM/SISTEMA | `flds8Ktz2DrXxHdLB` | singleLineText |  |  | 2/2 |  |

Os 2 registros (24/08 e 01/09/2026) são ambos `COPY_PUBLIC_LINK` feitos pelo setor Jurídico via `FORM_TESTEMUNHAS`, com ANTES/DEPOIS `{}` e CAMPOS ALTERADOS `[]` — o log funciona, mas quase nada passou por ele ainda.

## FRAGILIDADES — `tblmxkxgQEbc0KwvV` (17 registros)

Achados de fragilidade trabalhista por empresa, extraídos da análise dos autos. Cada registro é uma tese acionável, com fundamento, prova documental e situação nos julgados.

| campo | id | tipo | opções / ligação / fórmula | descrição no Airtable | preench. | observação |
|---|---|---|---|---|---|---|
| ACHADO | `fldhiPzMOkwrNlPRc` | singleLineText |  | Título curto e específico da fragilidade. | 17 (ver nota) |  |
| EMPRESA | `fldCYcTOQQv1m6lNH` | multipleRecordLinks | → EMPRESAS (inverso: `FRAGILIDADES`) | Empresa a que o achado se refere. | 17 (ver nota) |  |
| EIXO | `fldCf0uKDUvbIBVGp` | singleSelect | `Jornada / horas extras`, `Intervalo intrajornada`, `Controle de ponto`, `Norma coletiva (validade/vigência)`, `Folha de pagamento`, `Descontos indevidos`, `FGTS`, `Adicional noturno`, `Verbas normativas não pagas`, `Meio ambiente / dano moral`, `Rescisão indireta`, `Processual / conduta` | Categoria da fragilidade. | 17 (ver nota) |  |
| FORCA | `fldAzf4jY99QJigyP` | singleSelect | `Prova documental própria da ré`, `Confissão em depoimento`, `Aritmética verificável`, `Tese a construir`, `Depende de prova oral` | Quão sólido é o achado. | 17 (ver nota) |  |
| STATUS | `fldJWq7j3CkqlJfYM` | singleSelect | `Inédita — nunca enfrentada`, `Acolhida`, `Acolhida em parte`, `Rejeitada`, `Em julgamento` | Situação da tese nos julgados. | 17 (ver nota) |  |
| DESCRICAO | `fldEe2BlzvU2hdHh5` | multilineText |  | O que é a fragilidade, em prosa, com os números. | 17 (ver nota) |  |
| FUNDAMENTO | `fldoyTu3RO667EPmR` | multilineText |  | Base legal, normativa e jurisprudencial: artigos da CLT, cláusulas da CCT/ACT, súmulas e OJs. | 17 (ver nota) |  |
| PROVA | `fldCphzgJNuG3OTsA` | multilineText |  | Onde está a prova nos autos: documento, Id do PJe, folha, rubrica de holerite. | 17 (ver nota) |  |
| COMO EXPLORAR | `fldHXZBfEOSmW31D0` | multilineText |  | O que pedir na inicial, o que apontar na réplica, o que perguntar em audiência. | 17 (ver nota) |  |
| DOC A REQUERER | `fldGqbdkJEh2h2N0T` | multilineText |  | Documentos a requerer sob art. 400 do CPC ligados a este achado. | 17 (ver nota) |  |
| PROCESSOS | `fldaz2RuxYdnAhbtW` | multilineText |  | Processos em que o achado foi identificado ou discutido, e o resultado em cada um. | 17 (ver nota) |  |
| PERIODO | `fldRaDUyyxThY1L5o` | singleLineText |  | Período contratual/normativo a que o achado se aplica. | 17 (ver nota) |  |
| VALOR ESTIMADO | `fldoWQoTv1bJkdvHk` | currency | R$ 2 casas | Estimativa do impacto por empregado, quando calculável. | 17 (ver nota) |  |
| DOSSIE | `fldqhiuYK1foxVj4o` | multipleAttachments |  | Dossiê ou anexo de apoio. | 17 (ver nota) |  |
| ATUALIZADO EM | `fldZ2sZUFg6QdJYNQ` | date | D/M/YYYY |  | 17 (ver nota) |  |

Preenchimento (17 registros, todos da mesma empresa de transporte coletivo, criados em 24–25/08/2026): ACHADO, EMPRESA, EIXO, FORCA, STATUS, DESCRICAO, FUNDAMENTO, PROVA, COMO EXPLORAR, PERIODO, ATUALIZADO EM = 17/17; PROCESSOS 13/17; DOC A REQUERER 12/17; VALOR ESTIMADO 2/17; DOSSIE 0/17. EIXO usados: Jornada/horas extras 4, Controle de ponto 4, Descontos indevidos 3, Verbas normativas 2, Norma coletiva 2, Folha 1, FGTS 1, Adicional noturno 1. FORCA: Prova documental própria da ré 14, Aritmética verificável 2, Confissão em depoimento 1. STATUS: Inédita 12, Acolhida 3, Acolhida em parte 2.
