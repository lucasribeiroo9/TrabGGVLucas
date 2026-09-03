# De-para da migração — os 350 campos do Airtable, um por um

> Base **BASE GGV - TRAB V3** (`appMFTjWGygZ4ob5T`), lida somente leitura. Destino: o esquema de
> `esquema.sql` no `public` do Supabase. Cada campo tem UMA linha aqui — os 350 conferidos por
> script, não a olho. Nenhum nome de cliente, CPF, telefone, e-mail ou número de processo
> aparece neste arquivo.

## De onde vem o dump

`migrar.py --baixar` lê a API REST e precisa do token `GGV_AIRTABLE_TRAB`. Sem token, o caminho
é o **conector MCP do Airtable** (somente leitura): o Leitor baixa as dez tabelas e
`do_conector.py` converte para a forma que `migrar.py` lê — id de campo vira NOME (pelo mapa de
`list_tables_for_base`), select `{id,name,color}` vira `name`, link `[{id,name}]` vira `[rec…]`,
lookup `{linkedRecordIds, valuesByLinkedRecordId}` vira a lista de valores, colaborador perde
`permissionLevel`/`profilePicUrl`. Campo sem nome no mapa ou forma desconhecida **derruba a
conversão**: converter "do jeito que der" é perder calado. Provado com os 10.412 registros reais
em 03/09/2026: nenhum campo sem nome, nenhuma forma desconhecida. Ver o cabeçalho do arquivo.

## A regra que decide de onde vem cada valor

A base da migração é a **CÓPIA DA PROCESSUAL**: ela tem 1.187 processos a mais (1.048 deles
encerrados — o passivo histórico que nunca entrou na PROCESSUAL), os campos que o pipeline de
leitura dos autos escreveu em 31/08/2026 (data da sentença, magistrado, resultado objetivo do
recurso, CPF, CNPJ, relator, honorários por base) e a fase atualizada por essa leitura. Migrar
pela PROCESSUAL seria começar o sistema sem dois terços do acervo.

A **PROCESSUAL vence** nos campos que a equipe edita **hoje**: os links vivos com pré-processual,
testemunhas e pós-processual (que a duplicação de tabela transformou em texto na cópia), e os
campos onde ela está preenchida e a cópia não — data de revogação, número do CumPrSe, valor
homologado, sucumbência recebida, situação da execução, e os campos do incidente de
representação. A lista está na coluna **vence** de cada linha.

**Onde as duas discordam, ninguém escolhe em silêncio.** Nasce linha em `conferencias` com o
valor de cada lado, de qual tabela veio cada um e o trecho de prova — inclusive para as **1.403
divergências de FASE**. Os **22 processos só na PROCESSUAL** e os **106 sem número** entram
também: sem número não há como casar, então entram pela PROCESSUAL com uma conferência
`SEM_NUMERO` aberta.

## Como ler a tabela

- **destino**: `tabela.coluna` do esquema, ou **derivado** (não se grava: sai de consulta), ou
  **descartado** (com o motivo), ou `airtable_bruto` (fica guardado inteiro, sem coluna própria).
- **regra**: como o valor é convertido. Data vira TEXT ISO; dinheiro vira centavos inteiros;
  link vira chave estrangeira.
- **vence**: só para os campos que existem na PROCESSUAL e na CÓPIA.

Três coisas valem para TODA linha migrada e não se repetem campo a campo:

1. `airtable_record_id` guarda o record de origem, e `airtable_tabela` diz de qual tabela.
2. `airtable_bruto jsonb` guarda o **registro original inteiro** — inclusive o que já tem coluna
   própria. Assim "descartado" nunca quer dizer "perdido": quer dizer "sem coluna na tela".
   Nos processos o bruto é `{"copia": {...}, "processual": {...}}`, os dois lados inteiros.
3. Valor de select poluido que a normalização não soube traduzir vai para uma coluna `_original`
   (quando ela existe) e para `conferencias`. Nunca vira palpite.


## PRE PROCESSUAL — `tblucQ0Cz5MEQEdCR` (797 registros)

O funil. Vira `clientes` (fluxo 1).

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| NOME | `fldMgzsOWTG83RRHM` | singleLineText | clientes.nome + clientes.nome_norm | texto; nome_norm = maiúscula sem acento, para casar grafia | — |
| TELEFONE | `fldf7EJVSHV2xnyvq` | phoneNumber | clientes.telefone | só dígitos, com DDD | — |
| PASSAR DE FASE? | `fldIpom79mvFB9va3` | checkbox | clientes.passar_de_fase | checkbox -> boolean. Era o gatilho humano da automação PRE->PROCESSUAL; guardado porque explica por que a ficha subiu | — |
| E-MAIL | `fldAbboJKxYQo1KSP` | singleLineText | clientes.email | texto minusculo | — |
| CPF | `fldoHdB4li1b6LkI6` | singleLineText | clientes.cpf + clientes.cpf_valido | só dígitos; dígito verificador conferido, e o resultado gravado | — |
| NASCIMENTO | `fldM4AGasbrB33qim` | date | clientes.data_nascimento | date -> TEXT ISO | — |
| EMPRESA | `fld67uX200O7VqCle` | multipleRecordLinks | clientes.empresa_id | link -> FK empresas(id) pelo airtable_record_id | — |
| FUNCAO | `fld5Or0RJXmcRN71K` | singleLineText | clientes.função | texto | — |
| DATA DE ASSINATURA | `fldk5NSJtkJs581As` | date | clientes.data_assinatura_contrato | date -> TEXT ISO. É o gate contrato_assinado | — |
| CAPTADOR | `fldINYulF0zjgLugU` | multipleRecordLinks | clientes.captador_id | link -> FK pessoas(id) | — |
| STATUS DOCUMENTAÇÃO | `fldNJ5XYezXj83I8x` | singleSelect | derivado de pendências + clientes.em_tratamento | COMPLETA/PENDENTE/AGUARDANDO/PARCIAL viram contagem de pendências tipo DOCUMENTO; TRATAMENTO -> em_tratamento [CONFIRMAR]; DESISTENCIA -> status CANCELADO com motivo | — |
| STATUS ENTREVISTA | `fldMbfgFK4APJJL7F` | singleSelect | clientes.status + clientes.contatos_entrevista + eventos + contatos | normalizar.STATUS_ENTREVISTA; 0/ok/ag/SEM sem tradução -> conferências | — |
| STATUS PETICAO INICIAL | `fldCXIpACRak8hyQA` | singleSelect | clientes.status | normalizar.STATUS_PETICAO -> as quatro etapas PETICAO_* + DISTRIBUIDO/CANCELADO/PRESCRITO. VALIDACAO (0 usos) descartada | — |
| ETAPA PRE PROCESSUAL | `fldZWcb1qmuSnOzib` | singleSelect | clientes.status | etapa-mae; combinada com STATUS PETICAO INICIAL (ver normalizar.etapa_cliente). Divergencia entre as duas -> conferências | — |
| FONTE | `fldB8Dg9doxUwm15P` | singleSelect | clientes.canal + clientes.campanha + clientes.fonte_original | normalizar.FONTE separa canal (fechado) de campanha (texto). O original NUNCA se perde | — |
| STATUS_NOTIFICACAO_PRESCRICAO | `fldB35aEzRYRSRa7M` | singleSelect | automacao_log (origem N8N) | rastro de automação, não estado da pessoa: uma linha por aviso enviado | — |
| STATUS_NOTIFICACAO_RI | `fldGARfirwAPLcFU0` | singleSelect | automacao_log (origem N8N) | idem; a cadência 5/10/12/15 dias da rescisão indireta | — |
| RESCISAO | `fldiMRutGPhxhciRS` | singleLineText | clientes.rescisao_modalidade + clientes.rescisao_original | normalizar.rescisao(): texto livre -> lista fechada por TRECHO exato sobre o texto sem acento (trecho com acento nunca casa — foi um trecho assim que deixou 98 rescisões indiretas em branco na primeira carga real, e o conferir.py agora prova a distribuição). Carga real (666 preenchidos): 330 SEM_JUSTA_CAUSA, 101 RESCISAO_INDIRETA, 86 PEDIDO_DEMISSAO, 40 JUSTA_CAUSA, 7 CONTRATO_VIVO ("ATIVO", "ATUAL", "AINDA NÃO SAÍ" casam só o texto exato/trecho), 1 TERMINO_CONTRATO; 101 sem tradução (75 trazem data ou telefone, 26 texto livre: "DEMISSÃO" sozinho, "SIM", "N/A", "NAO LEMBRO", um nome de pessoa…) -> só no original + conferências | — |
| DEMISSAO | `fldj37usp7C6okYE1` | singleLineText | clientes.data_demissao + clientes.data_demissao_original | normalizar.data_br: 6 formatos -> ISO. O que não parseia fica só no original + conferências DATA_ILEGIVEL | — |
| PRESCREVE | `fldcAJEHaeJiV3Acg` | fórmula | derivado | fórmula DEMISSAO + 2 anos. Recalculada pela view v_pre_processual_atrasado: número na tela sai de consulta | — |
| AVISOS | `fldG6n6zOWaS7qeVr` | multilineText | anotações (campo_origem=AVISOS) | o texto das automações 15/20 dias e os 3 recados humanos. O farol em si e derivado | — |
| URGENCIA | `fldIYbZyJQurMCRfG` | multipleSelects | derivado | RI = rescisao_modalidade; PRESCRIÇÃO e URGENCIA ALTA = conta de data. "checked" (4) é lixo de importação | — |
| PENDENCIAS | `fldBooALabWsmeeOP` | multipleSelects | pendências (tipo=DOCUMENTO) | uma linha por documento marcado. HOLERITE funde com HOLERITES; OK e DOCUMENTACAO OK não são documento -> conferências | — |
| DRIVE | `fld1vyxG8x6W6g9Mk` | url | clientes.drive_url | url | — |
| ASTREA | `fldGotjWCRp1MqC41` | url | clientes.astrea_url | url [CONFIRMAR: o Astrea continua em uso?] | — |
| ENTREVISTADOR | `fldJZktWI7lBRUXVd` | multipleRecordLinks | clientes.entrevistador_id | link -> FK pessoas(id) | — |
| DATA ENTREVISTA | `fldzAzEK2Bd9df8Ly` | dateTime | clientes.entrevista_em + eventos(tipo=ENTREVISTA) | dateTime -> TEXT ISO; também vira evento de agenda | — |
| RESUMO ENTREVISTA | `fldVezNGzkGhlsnzM` | multilineText | clientes.entrevista_resumo | texto; junto com entrevista_em e o gate entrevista_registrada | — |
| RESPONSAVEL INICIAL | `fldoSAxQw8Qbr7vhF` | multipleRecordLinks | clientes.responsavel_id | link -> FK pessoas(id). É o dono do atendimento | — |
| TESE PRINCIPAL | `fldc9EKTY8zh1Zjmg` | singleLineText | airtable_bruto | vazio em 100% dos 797. Não vira coluna: campo que ninguém preencheu não ganha lugar na tela | — |
| PROCESSUAL | `fldyG90IE0htBpVEo` | multipleRecordLinks | processos.cliente_id | link -> a ligação passa a viver na FK do processo | — |
| TESTEMUNHAS | `fldDh5FCEddcsnBf1` | multipleRecordLinks | testemunha_vinculos.cliente_id | link -> tabela de ligação | — |
| Created | `fldyBsUVlqH0ulTnE` | createdTime | clientes.criado_em (+ historico_etapas.em como último recurso) | createdTime -> TEXT ISO. É a data do histórico quando a etapa não tem data própria (ver "O histórico da carga") | — |
| PERICIA MEDICA | `fldRofbAsutD06eAB` | checkbox | clientes.pericia_medica | checkbox -> boolean (0 marcados hoje) | — |
| PERICIA INSALUB/PERIC | `fldzDiAk4UZpiKLy5` | checkbox | clientes.pericia_tecnica | checkbox -> boolean (0 marcados hoje) | — |
| ENVIAR MENSAGEM | `fldSHOr0gls9z5rUn` | button | descartado | botao: monta uma URL a partir dos outros campos. Não e dado | — |
| status_disparo | `fld3pVGPa59DBAZMp` | singleLineText | automacao_log (origem N8N) | uma linha por disparo, com resultado. 88 aniversario_erro viram resultado=ERRO | — |
| tipo_disparo | `fldIFX1oNfUlUFG0c` | singleLineText | automacao_log.detalhe | idem | — |
| data_solicitacao_disparo | `fldO2ZTWv7QhV5Rc0` | singleLineText | automacao_log.em | idem | — |
| responsavel_interno | `fldTqXb9QWzWxM3Ar` | singleLineText | automacao_log.detalhe | idem | — |
| solicitante_disparo | `flduFmWE4Ka5bwKrr` | singleLineText | automacao_log.detalhe | idem | — |
| erro_disparo | `fldKJn522iGXk8hHu` | singleLineText | automacao_log.detalhe (resultado=ERRO) | idem | — |
| EMPRESA PROCESSADA | `fldNgwihIj6mu6TnS` | multipleLookupValues | derivado | lookup do nome da EMPRESA; sai de JOIN | — |
| prescrição próxima | `flddOmzVQJ2IJn9Us` | fórmula | derivado | fórmula: PRESCREVE entre hoje e +30 dias. View v_pre_processual_atrasado | — |

## PROCESSUAL — `tbl6rDaSPCQRbbzjq` (2.652 registros)

A fonte do que está **vivo**: os 22 números recentes, os 106 sem número, os links com PRE/TESTEMUNHAS/PÓS e os campos que a equipe edita hoje. **Vence** a CÓPIA nesses campos.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| NOME | `fldNfuluuw5gCEHr4` | singleLineText | processos.nome_parte (+ clientes.nome) | CÓPIA vence; a outra grafia vai para processo_alias | CÓPIA |
| Nº PROCESSO | `fld6Ij9BXuOr9PSYg` | singleLineText | processos.numero_cnj | texto; numero_cnj_digitos é coluna gerada. É a CHAVE do casamento CÓPIA × PROCESSUAL. Duplicado -> conferências CNJ_DUPLICADO; vazio (106) -> SEM_NUMERO | CÓPIA |
| EMPRESA | `fldrknqdvK5yrinq8` | multipleRecordLinks | processos.empresa_id | link -> FK empresas(id) | CÓPIA |
| COMPLEXIDADE | `fld2Vbn86hkcHjRZU` | singleSelect | processos.complexidade | A/B/C; derivada do valor (normalizar.complexidade_da_faixa: C<=150k, B<=500k). Letra diferente da faixa -> complexidade_manual=true — aplicado e provado (carga real: 0 casos, todas na faixa) [CONFIRMAR 16] | CÓPIA |
| VALOR | `fld4ixpIddlOdip3a` | currency | processos.valor_causa_centavos | normalizar.dinheiro(): currency -> centavos; acima de R$ 1 bilhão não é dinheiro (é número de processo digitado no campo de moeda) -> NULL + conferência, original no bruto. Carga real: 0 casos aqui | CÓPIA |
| ADVOGADO | `fldgmBAFmw9vew8XV` | multipleRecordLinks | processos.advogado_id | link -> FK pessoas(id) | CÓPIA |
| VARA | `fldB6EhDR53tG0bqT` | singleLineText | processos.vara | texto; CÓPIA vence, a outra grafia vai para processo_alias | CÓPIA |
| TRT | `fldoc8fTWo0JH0b0T` | singleSelect | processos.trt | normalizar.TRT: 21 opções poluidas -> número (1..24). "85ª" e os vazios -> conferências | CÓPIA |
| FASE PROCESSUAL | `fld0SuRbQk9jJa19n` | singleSelect | processos.fase | normalizar.FASE; EXECUÇÃO sem qualificação decidida por numero_cumprse/transito. As 1.403 divergências CÓPIA × PROCESSUAL -> conferências, uma por processo | CÓPIA |
| STATUS DO PROCESSO | `fldqubv8Cbd8u9yPr` | singleSelect | processos.fase | incidentes | derivado | normalizar.STATUS_PROCESSO: AGUARDANDO_* são derivados; ROUBADO/RECEBIDO POR ELES/RECUPERADO viram incidentes; ARQUIVADO vira resultado_final; REDISTRIBUIR vira tarefa tipo REDISTRIBUICAO (1); TRÂNSITO EM JULGADO decide a fase da execução e vira ANOTAÇÃO — `transito_em` fica NULL porque a origem não tem a data (a da sentença não é ela); sem FASE PROCESSUAL e sem status -> CONHECIMENTO com conferência (58) | CÓPIA |
| ENVIAR MENSAGEM | `fldV1cOA4tEfnjKPW` | button | descartado | botao | CÓPIA |
| DISTRIBUIÇAO | `fldrcjw0h3MDTuaod` | date | processos.distribuicao_em | date -> TEXT ISO | CÓPIA |
| STATUS CONHECIMENTO | `fldFI8DlSCAoPpjJO` | singleSelect | decisões | audiências | derivado | SENTENCIADA -> decisões(SENTENCA); AUSENCIA -> audiência NAO_REALIZADA com motivo AUSENCIA_RECLAMANTE + resultado_final ARQUIVADO_AUSENCIA quando a fase é ENCERRADO e o resultado era ARQUIVADO ou vazio (126), senão conferência; SENTENCIADA / AGUARDANDO SENTENÇA também são EVIDÊNCIA de que a audiência passada aconteceu (ver DATA AUDIENCIA) | CÓPIA |
| SENTENCA | `fldjHSryziAOOISbv` | singleSelect | decisões.nota (tipo=SENTENCA) | RUIM/MEDIA/OTIMA -> nota. E avaliação, não resultado | CÓPIA |
| DECISAO SENTENCA | `fld2NZ9Zi35931gge` | singleSelect | decisões.resultado_objetivo (tipo=SENTENCA) | PROCEDENTE / PARCIALMENTE PROCEDENTE / IMPROCEDENTE / EXTINTO S/ RESOLUCAO | CÓPIA |
| RESULTADO ACORDAO | `fldyhUJRHPLAsghKj` | singleSelect | decisões.nota (tipo=ACORDAO) | RUIM/MEDIO/OTIMO -> nota | CÓPIA |
| ULTIMA DECISAO | `fld5XeIVLrec9DCu0` | singleSelect | decisões.resultado_objetivo da decisão mais recente | airtable_bruto | campo com duas naturezas. PROCEDENTE/IMPROCEDENTE completam a decisão quando DECISAO SENTENCA está vazio e existe sentença (nota ou data) — regra em `Migracao.resultado_sentenca()`, que o conferir.py recalcula (foi 1 IMPROCEDENTE a mais no banco que a denunciou); RUIM/MEDIA/OTIMA são a nota; SEM DECISAO não vira nada | CÓPIA |
| DATA ACORDAO | `fldezorfyCie9kmB1` | date | decisões.data (tipo=ACORDAO) | date -> TEXT ISO. NAO confundir com DATA DO ACORDO (o acordo entre as partes) | CÓPIA |
| CLASSIFICACAO | `fldwA5XRRCLLusZhu` | singleSelect | processos.rito + processos.classe_cnj + processos.classe_incidente | RT/AT = classe; ORDINÁRIO/SUMARÍSSIMO/SUMÁRIO = rito; as classes de incidente da CÓPIA (RR, AIRR, RRAg, Emb, EMBARGOS DE TERCEIRO, EXECUÇÃO *) vão para classe_incidente e para recursos [CONFIRMAR 17] | CÓPIA |
| DATA AUDIENCIA | `fldYTqFftgpvtxHCb` | dateTime | audiências.data_hora + eventos | dateTime -> TEXT ISO. UMA LINHA por audiência: a origem sobrescrevia. A SITUAÇÃO nasce pela evidência (Migracao.situacao_audiencia): ausência -> NAO_REALIZADA; sem data ou data >= leitura da origem -> DESIGNADA; data passada com sentença/acórdão/acordo/encerramento posterior, ou instrução encerrada, ou processo além do conhecimento -> REALIZADA com a evidência em `observacao`; data passada sem nada disso -> REALIZADA + conferência AUDIENCIA_SEM_RESULTADO (279). `historico_etapas.em` = a data da audiência | CÓPIA |
| AUDIENCIA | `fldQgm6veivaP9A7v` | singleSelect | audiências.tipo + audiências.modalidade | normalizar.AUDIENCIA separa tipo de modalidade (INSTRUCAO/VIDEO -> INSTRUCAO + VIDEO). UNA-RS também grava processos.rito=SUMARÍSSIMO [CONFIRMAR 17] | CÓPIA |
| Nº  CumPrSe | `fldC5VgP5KIXGqoDM` | singleLineText | processos.numero_cumprse | texto; é o gate numero_cumprse e decide EXECUÇÃO -> PROVISORIA | PROCESSUAL |
| RESULTADO | `fldifEVxbZJJnrYRN` | multilineText | processos.resultado_texto | multiline; o resultado em prosa | CÓPIA |
| STATUS RECURSAL | `fldfWIWmtbQX9n29c` | singleSelect | recursos (grau TRT/TST) | TST -> recurso pendente grau TST; AGUARDANDO JULGAMENTO -> grau TRT. O tipo do recurso [CONFIRMAR 22] nasce OUTRO quando a origem não diz | CÓPIA |
| STATUS CumPrSe | `fldnjIz7be8iZqjqS` | singleSelect | processos.situacao_execucao | normalizar.STATUS_CUMPRSE, aplicado em Migracao.completar_execucao: preenche situacao_execucao só onde STATUS EXECUÇÃO calou (12); discordância com STATUS EXECUÇÃO ou com a fase -> conferência DIVERGENCIA_FONTE (9). O texto vai para situacao_execucao_original | CÓPIA |
| STATUS DO CALCULO | `fldzNusdLtfqC2EhS` | singleSelect | processos.situacao_execucao + cálculos | normalizar.STATUS_CALCULO -> situacao_execucao (AGUARDANDO_CALCULO / CALCULOS_APRESENTADOS / HOMOLOGADO) só onde STATUS EXECUÇÃO e CumPrSe calaram (471); em `calculos` fica `observacao` com o status — `homologado_em` fica NULL porque a origem NÃO tem a data (a carga anterior punha o ENCERRAMENTO: inventado) | CÓPIA |
| CALCULO RCTE | `fldIoDBuntoHRD8M4` | currency | cálculos.valor_centavos (base=RECLAMANTE) | currency -> centavos | CÓPIA |
| SUCUMB RCTE | `fldQwD6wl9Rp1OdvN` | currency | cálculos.sucumbencia_centavos (base=RECLAMANTE) | currency -> centavos | CÓPIA |
| CALCULO RCDA | `fldBXmceSOIGmB6Qi` | currency | cálculos.valor_centavos (base=RECLAMADA) | currency -> centavos | CÓPIA |
| SUCUMB RCDA | `fldzP9PLO36pB8GkB` | currency | cálculos.sucumbencia_centavos (base=RECLAMADA) | currency -> centavos | CÓPIA |
| SUCUMB HOM | `fldn7DL7nwIB1wXCi` | currency | cálculos.sucumbencia_centavos (base=HOMOLOGADO) | currency -> centavos | CÓPIA |
| VALOR HOM | `fldQwZD5A9GhAGG52` | currency | cálculos.valor_centavos (base=HOMOLOGADO) | currency -> centavos. PROCESSUAL vence: 127 preenchidos só nela | PROCESSUAL |
| STATUS PAGAMENTO | `fldMJyeDxmi4D7qLI` | singleSelect | derivado de acordo_parcelas + recebimentos | seis rotulos para "quantas parcelas pagas e alguma atrasada" (derivados). PARCELAMENTO CPC -> situacao_execucao = PARCELAMENTO_916 onde vazio; CESSAO DE CREDITOS -> processos.credito_cedido = true (3) — `credito_cedido_em` e `cessionario` ficam NULL: a origem não os tem | CÓPIA |
| ENCERRAMENTO | `fldrtiBvNP0bBmB7p` | date | processos.encerrado_em | date -> TEXT ISO | CÓPIA |
| DRIVE | `fldHaNBnpjhyTvUzY` | url | processos.drive_url | url | CÓPIA |
| ASTREA | `fldpc4dSNT3fuoQQS` | url | processos.astrea_url | url | CÓPIA |
| OBSERVACOES | `fldKtWPFUUDgf6wAO` | multilineText | anotações (campo_origem=OBSERVACOES) | multiline -> anotação com autor desconhecido e origem MIGRACAO | CÓPIA |
| PRE PROCESSUAL | `fldjVtWlmftDbeNOR` | multipleRecordLinks | processos.cliente_id | link (na CÓPIA virou texto: casado pelo nome + número, e o que não casar -> conferências) | PROCESSUAL |
| PÓS PROCESSUAL | `fldVZQSDtQeDlN8JN` | multipleRecordLinks | recebimentos + repasses + processos.arquivado_em | link; o PÓS não é entidade própria (ver seção PÓS PROCESSUAL) | PROCESSUAL |
| TURMA | `fldwUFdtsipXQpkZc` | singleSelect | processos.turma | CÓPIA vence; na PROCESSUAL são 41 opções com espaco sobrando, "18ª turma" e sete números de processo digitados como opção -> conferências. Um "11" sozinho não vira turma: fica NULL + conferência [CONFIRMAR: é a 11ª Turma?] | CÓPIA |
| TESTEMUNHAS | `fld2M1cDAzzIsY9Ju` | multipleRecordLinks | testemunha_vinculos.processo_id | link (texto na CÓPIA) | PROCESSUAL |
| DATA ADVIDEO | `fldapqeXrdSg96USR` | dateTime | audiências.advideo_em | vazio em 100%; sem audiência para pendurar fica em airtable_bruto | CÓPIA |
| RESP ADVIDEO | `fldT17XSmaZwyeFEb` | multipleRecordLinks | audiências.advideo_responsavel_id | vazio em 100% | CÓPIA |
| STATUS ADVIDEO | `fldIOGYMaqOMyWhld` | singleSelect | audiências.advideo_previsto / advideo_em | PENDENTE/MARCADO/FEITO viram o checklist da audiência. 1 registro [CONFIRMAR 14: o que e ad video] | CÓPIA |
| PERICIA MEDICA | `fldBuY7IbnUaLKDVL` | checkbox | processos.pericia_medica + pericias(tipo=MEDICA) | checkbox -> boolean; com DATA PERICIA MEDICA vira linha em pericias | CÓPIA |
| PERICIA TECNICA | `fldhyoWgzBcBUXIy4` | checkbox | processos.pericia_tecnica + pericias(tipo=TECNICA) | idem | CÓPIA |
| STATUS EXECUÇÃO | `fldOaKzigKAjCeIB7` | singleSelect | processos.situacao_execucao + situacao_execucao_original (+ processos.resultado_final) | normalizar.STATUS_EXECUCAO: 36 opções -> 16 estados. SIM/NAO/EXECUCAO/RECURSAL viram NULL + conferências (45 na carga real). O valor que estava na COLUNA ERRADA (198 processos: ARQUIVADO 153, EXTINTA S/ RESOLUÇÃO 24, EXECUÇÃO PROVISÓRIA 16, SOBRESTADO 2, AUDIÊNCIA CONCILIAÇÃO 3) é tratado por `Migracao.situacao_execucao()`: ARQUIVADO/EXTINTA em processo ENCERRADO completam `resultado_final`; a mesma fase é coerente e nada há a fazer; o que DISCORDA da fase gravada (24) abre conferência. O texto original fica sempre | PROCESSUAL |
| AND. NECESSÁRIO | `fldg1Bd6mkVrcTYQn` | singleSelect | tarefas (tipo=ANDAMENTO, texto_original) | "andamento necessário" é tarefa por definição. Encerrado/ACORDO são redundantes com a fase e não viram tarefa [CONFIRMAR 19] | PROCESSUAL |
| AÇÃO | `fldMGJEtU1xwQgN44` | date | processos.ajuizamento_em | date -> TEXT ISO [CONFIRMAR: difere de DISTRIBUICAO em que?] | CÓPIA |
| TEL VARA | `fldawy6eAxOG7SOAk` | phoneNumber | processos.tel_vara | telefone | CÓPIA |
| STATUS ACORDO | `fldXIXmprptmmddgZ` | singleSelect | acordos.situação | EM ANDAMENTO / CUMPRIDO / QUEBRA -> acordos.situacao; `quebrado_em` fica NULL — a origem só tem o status, não a data da quebra. Acordo com VALOR ou DATA e sem status nasce EM_ANDAMENTO com conferência (9) | CÓPIA |
| VALOR ACORDO | `fld3QiKc0ZWvhGOAY` | currency | acordos.valor_centavos | currency -> centavos | CÓPIA |
| TOTAL RECEBIDO | `fld5ozVpHgQkmILn6` | currency | recebimentos.valor_centavos (base=TOTAL) | currency -> centavos | CÓPIA |
| SUCUMB RECEBIDO | `fldPo7TA7Vf1sGDle` | currency | recebimentos.valor_centavos (base=SUCUMBENCIA) | currency -> centavos. PROCESSUAL vence: 67 só nela | PROCESSUAL |
| HONOR TOTAL | `fldHre22MxIFJBkst` | currency | recebimentos.valor_centavos (base=HONORARIOS) | currency -> centavos | CÓPIA |
| SITU. EMPRESA | `fldKg8pjqh6Xx93f6` | multipleLookupValues | empresas.situação | lookup: o atributo e da empresa (JOIN). A divergência de verdade é do LINK: 423 processos apontam para reclamadas diferentes na CÓPIA e na PROCESSUAL -> conferência DIVERGENCIA_FONTE campo EMPRESA, com o nome de cada lado; o lookup só vira conferência própria quando o link é o mesmo e ainda discorda do cadastro (14) | PROCESSUAL |
| BENS IDENTIFICADOS | `fldfNjKnnKr11GGcL` | multipleSelects | empresas.bens_identificados | atributo da empresa, estava nos dois lugares | CÓPIA |
| HIST. PAGAMENTO | `fldRa9KGSydy8BCmD` | multipleSelects | empresas.hist_pagamento | idem | CÓPIA |
| ULTIMA MOV | `fldvOXdS10SVyA10U` | singleLineText | processos.ultima_movimentacao + ultima_movimentacao_em | texto "aaaa-mm-dd - descrição": a data é separada do texto | CÓPIA |
| REVOGAÇÃO | `fldWEiwaScW2AZjlC` | singleSelect | processos.revogou_patrono_anterior | incidentes.revogacao_nos_autos_em | tarefas | normalizar.REVOGACAO + Migracao.revogacao_destino. O SENTIDO depende do STATUS DO PROCESSO: ROUBADO/RECEBIDO POR ELES/RECUPERADO (ou REVOGAÇÃO = ROUBADO) e o cliente que nos revogou (incidente); em qualquer outro caso somos nos que juntamos a revogação do patrono anterior -> revogou_patrono_anterior SIM/NÃO (794/66), haja ou não incidente por notificação/providência [CONFIRMAR 20]. Os recados viram tarefa (5). Provado em conferir.py | PROCESSUAL |
| DATA REVOG | `fldmQNnSSPgwmjrfU` | date | processos.revogacao_em | incidentes.revogacao_nos_autos_em | date -> TEXT ISO. PROCESSUAL vence. A data NUNCA fica sem coluna: sentido 2 -> incidentes.revogacao_nos_autos_em (101); qualquer outro caso, com REVOGAÇÃO preenchida ou não -> processos.revogacao_em (1.326). REVOGAÇÃO = NÃO com data é contradição: grava-se e abre conferência (79). conferir.py prova 1.427 = 1.326 + 101 | PROCESSUAL |
| NOTIFICAÇÃO | `fldIX6EOFBawzAWUK` | singleSelect | incidentes.situação + as datas da notificação | REDIGIDA -> DETECTADO; ENVIADA/RECEBIDA/RESPONDIDA -> NOTIFICADO. As DATAS (redigida, enviada, recebida, resposta) ficam NULL: a origem não as tem, e a carga anterior punha DATA REVOG ou ENCERRAMENTO nelas (72 inventadas). O valor original vai para incidentes.airtable_bruto | PROCESSUAL |
| PROVIDENCIAS | `fld0Do0Zk6nGI8kNO` | singleLineText | incidentes.providencia_texto + tarefas | NOTIFICAR -> tarefa "enviar notificação"; TRAVAR O RECEBIMENTO -> tarefa "pedir reserva de honorários (EOAB art. 22 §4º)" | PROCESSUAL |
| SUCUMBÊNCIA % | `fldVloHxj2m98LYxt` | singleLineText | processos.sucumbencia_percent | texto "5%" -> número. O "2500%" é erro: vai para conferências | CÓPIA |
| CLIENTE AVISADO? | `fldgSW5GHxJI2c8Y5` | checkbox | incidentes.cliente_avisado_em | checkbox -> incidentes.airtable_bruto. `cliente_avisado_em` fica NULL: a origem não tem a data (0 usos hoje) [CONFIRMAR] | PROCESSUAL |
| CAPTADOR | `fldn2UE1d7hIltlEL` | multipleRecordLinks | processos.captador_id | link -> FK pessoas(id) | CÓPIA |
| TELEFONE | `fldM8NaPLZgRl8xYO` | singleLineText | processos.telefone_parte (+ clientes.telefone na ficha criada dos autos) | CÓPIA vence; a outra grafia vai para processo_alias | CÓPIA |
| ASSINATURA | `fldfX0YrunL0RcS8B` | date | processos.assinatura_em (+ clientes.data_assinatura_contrato) | date -> TEXT ISO. CÓPIA vence: 58% contra 4%. Completa a ficha do cliente onde ela não tinha (ficha criada dos autos ou PRÉ sem DATA DE ASSINATURA); ficha que continua sem -> pendência DOCUMENTO/CONTRATO obrigatória (1.283) | CÓPIA |
| status_disparo | `fld7ybzbPpxSUuz7S` | singleLineText | automacao_log (origem N8N) | idem PRE | CÓPIA |
| tipo_disparo | `fldilA0CkqowpHrwU` | singleLineText | automacao_log.detalhe | idem | CÓPIA |
| data_solicitacao_disparo | `flddnHA8qxPagMTVL` | singleLineText | automacao_log.em | idem | CÓPIA |
| responsavel_interno | `fldpy6hzz9JmvGF52` | singleLineText | automacao_log.detalhe | idem | CÓPIA |
| solicitante_disparo | `fldngD5lXI6tVGcSq` | singleLineText | automacao_log.detalhe | idem | CÓPIA |
| Created By | `fldt1iwzwXFOe7Eiz` | lastModifiedTime | processos.atualizado_em (PROCESSUAL) | processos.airtable_bruto (CÓPIA) | na PROCESSUAL o tipo é lastModifiedTime apesar do nome e vai para processos.atualizado_em (2.652); na CÓPIA é createdBy de verdade e o nome de quem criou fica no bruto. O createdTime do record vai para processos.criado_em / clientes.criado_em da ficha dos autos, e é o último recurso do histórico | CÓPIA |
| DATA PERÍCIA TECNICA | `fldvmVtg1ynyvyMW5` | dateTime | pericias.data_hora (tipo=TECNICA) | dateTime -> TEXT ISO | CÓPIA |
| DATA PERÍCIA MÉDICA | `fldrXrmogGDUotQoh` | dateTime | pericias.data_hora (tipo=MEDICA) | dateTime -> TEXT ISO | CÓPIA |
| NASCIMENTO | `flda88gB2QLJzqX5d` | date | processos.nascimento_parte (+ clientes.data_nascimento) | date na PROCESSUAL, texto na CÓPIA: normalizar.data_br. Completa clientes.data_nascimento onde vazio; ficha que continua sem -> pendência CADASTRO (1.012). Divergencia -> processo_alias | CÓPIA |
| MOTIVO | `fld2sglKUtrY89Qye` | singleLineText | airtable_bruto | 1 registro na PROCESSUAL ("SEM TESTEMUNHA") e quatro na CÓPIA, sem função clara | CÓPIA |
| _BACKUP_VALOR_ANTES_SCRIPT | `fld6Ob4Iz67W5SOjB` | singleLineText | airtable_bruto | lixo técnico: backup de 03-06/07/2026 antes de um script reescrever VALOR. Não vira coluna | só na PROCESSUAL |
| _BACKUP_COMPLEXIDADE_ANTES_SCRIPT | `fldImV7gyBd4pCLvd` | singleLineText | airtable_bruto | idem | só na PROCESSUAL |
| _BACKUP_FEITO_EM_SCRIPT | `fldQBABT58Z5thviS` | singleLineText | airtable_bruto | idem (a data do backup) | só na PROCESSUAL |
| PARCELAS | `fldKuQ5Nk3oDJKgrs` | number | acordos.parcelas | number -> inteiro | CÓPIA |

## CÓPIA DA PROCESSUAL — `tblvyoun2V0CQKmxF` (3.722 registros)

**A base da migração**: 1.187 processos a mais (o passivo histórico), o enriquecimento do pipeline de 31/08/2026 e a fase atualizada pela leitura dos autos. Vence em tudo o que não está na lista da PROCESSUAL.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| NOME | `fldcmfFZHPf1hduFj` | singleLineText | processos.nome_parte (+ clientes.nome) | CÓPIA vence; a outra grafia vai para processo_alias | CÓPIA |
| Nº PROCESSO | `fldvP4t6aNYcOoFcv` | singleLineText | processos.numero_cnj | texto; numero_cnj_digitos é coluna gerada. É a CHAVE do casamento CÓPIA × PROCESSUAL. Duplicado -> conferências CNJ_DUPLICADO; vazio (106) -> SEM_NUMERO | CÓPIA |
| DISTRIBUIÇAO | `fldQj4QvumWoy3XCs` | date | processos.distribuicao_em | date -> TEXT ISO | CÓPIA |
| VARA | `fld0dpB84odelzYE8` | singleLineText | processos.vara | texto; CÓPIA vence, a outra grafia vai para processo_alias | CÓPIA |
| TRT | `fldNjTzo9HaumzYe8` | singleSelect | processos.trt | normalizar.TRT: 21 opções poluidas -> número (1..24). "85ª" e os vazios -> conferências | CÓPIA |
| VALOR | `fldtpiJdqwvzSRchp` | currency | processos.valor_causa_centavos | normalizar.dinheiro(): idem PROCESSUAL. Carga real: 3.722 preenchidos, soma conferida ao centavo | CÓPIA |
| EMPRESA | `fldQr8KII3fj6RaEn` | multipleRecordLinks | processos.empresa_id | link -> FK empresas(id) | CÓPIA |
| COMPLEXIDADE | `fldr2WHDjAuXmSEd9` | singleSelect | processos.complexidade | A/B/C; derivada do valor (normalizar.complexidade_da_faixa: C<=150k, B<=500k). Letra diferente da faixa -> complexidade_manual=true — aplicado e provado (carga real: 0 casos, todas na faixa) [CONFIRMAR 16] | CÓPIA |
| ADVOGADO | `fldFtmUazPjgT5Vba` | multipleRecordLinks | processos.advogado_id | link -> FK pessoas(id) | CÓPIA |
| FASE PROCESSUAL | `fldpZfbG3Dj4oJOnC` | singleSelect | processos.fase | normalizar.FASE; EXECUÇÃO sem qualificação decidida por numero_cumprse/transito. As 1.403 divergências CÓPIA × PROCESSUAL -> conferências, uma por processo | CÓPIA |
| STATUS DO PROCESSO | `fldPBWPDPunT9Il3G` | singleSelect | processos.fase | incidentes | derivado | normalizar.STATUS_PROCESSO: AGUARDANDO_* são derivados; ROUBADO/RECEBIDO POR ELES/RECUPERADO viram incidentes; ARQUIVADO vira resultado_final; REDISTRIBUIR vira tarefa tipo REDISTRIBUICAO (1); TRÂNSITO EM JULGADO decide a fase da execução e vira ANOTAÇÃO — `transito_em` fica NULL porque a origem não tem a data (a da sentença não é ela); sem FASE PROCESSUAL e sem status -> CONHECIMENTO com conferência (58) | CÓPIA |
| ENVIAR MENSAGEM | `fldk8X85hMO02Sx3b` | button | descartado | botao | CÓPIA |
| STATUS CONHECIMENTO | `fld4PTXQ5VK9uY6X3` | singleSelect | decisões | audiências | derivado | SENTENCIADA -> decisões(SENTENCA); AUSENCIA -> audiência NAO_REALIZADA com motivo AUSENCIA_RECLAMANTE + resultado_final ARQUIVADO_AUSENCIA quando a fase é ENCERRADO e o resultado era ARQUIVADO ou vazio (126), senão conferência; SENTENCIADA / AGUARDANDO SENTENÇA também são EVIDÊNCIA de que a audiência passada aconteceu (ver DATA AUDIENCIA) | CÓPIA |
| MOTIVO | `fldYEwcnX5KDpfgop` | singleLineText | airtable_bruto | 1 registro na PROCESSUAL ("SEM TESTEMUNHA") e quatro na CÓPIA, sem função clara | CÓPIA |
| SENTENCA | `fldIODL3MBKzthFpK` | singleSelect | decisões.nota (tipo=SENTENCA) | RUIM/MEDIA/OTIMA -> nota. E avaliação, não resultado | CÓPIA |
| DECISAO SENTENCA | `fldrUKtuvmfUIA3ut` | singleSelect | decisões.resultado_objetivo (tipo=SENTENCA) | PROCEDENTE / PARCIALMENTE PROCEDENTE / IMPROCEDENTE / EXTINTO S/ RESOLUCAO | CÓPIA |
| RESULTADO ACORDAO | `fldXoF3mU8Vl7P4Yy` | singleSelect | decisões.nota (tipo=ACORDAO) | RUIM/MEDIO/OTIMO -> nota | CÓPIA |
| ULTIMA DECISAO | `fldu4Z2qYKoXOcpIf` | singleSelect | decisões.resultado_objetivo da decisão mais recente | airtable_bruto | campo com duas naturezas. PROCEDENTE/IMPROCEDENTE completam a decisão quando DECISAO SENTENCA está vazio e existe sentença (nota ou data) — regra em `Migracao.resultado_sentenca()`, que o conferir.py recalcula (foi 1 IMPROCEDENTE a mais no banco que a denunciou); RUIM/MEDIA/OTIMA são a nota; SEM DECISAO não vira nada | CÓPIA |
| DATA SENTENCA | `fldVyWVyQoo9SDuaE` | date | decisões.data (tipo=SENTENCA) | date -> TEXT ISO. Extraída da intimação AASP; só existe na CÓPIA | só na CÓPIA |
| DATA ACORDAO | `fldDG9LKLVsZOT9Pg` | date | decisões.data (tipo=ACORDAO) | date -> TEXT ISO. NAO confundir com DATA DO ACORDO (o acordo entre as partes) | CÓPIA |
| MAGISTRADO | `fld6mw1fPKilW87WA` | singleLineText | decisões.magistrado (tipo=SENTENCA) | texto. Em ~45% e quem homologou acordo, não quem julgou o merito: a análise por magistrado filtra por DECISAO SENTENCA preenchida | só na CÓPIA |
| CLASSIFICACAO | `fldVHQhm4VVw91MvJ` | singleSelect | processos.rito + processos.classe_cnj + processos.classe_incidente | RT/AT = classe; ORDINÁRIO/SUMARÍSSIMO/SUMÁRIO = rito; as classes de incidente da CÓPIA (RR, AIRR, RRAg, Emb, EMBARGOS DE TERCEIRO, EXECUÇÃO *) vão para classe_incidente e para recursos [CONFIRMAR 17] | CÓPIA |
| DATA AUDIENCIA | `fldn0bZKGzzg86uQq` | dateTime | audiências.data_hora + eventos | dateTime -> TEXT ISO. UMA LINHA por audiência: a origem sobrescrevia. A SITUAÇÃO nasce pela evidência (Migracao.situacao_audiencia): ausência -> NAO_REALIZADA; sem data ou data >= leitura da origem -> DESIGNADA; data passada com sentença/acórdão/acordo/encerramento posterior, ou instrução encerrada, ou processo além do conhecimento -> REALIZADA com a evidência em `observacao`; data passada sem nada disso -> REALIZADA + conferência AUDIENCIA_SEM_RESULTADO (279). `historico_etapas.em` = a data da audiência | CÓPIA |
| AUDIENCIA | `fldfn7q0rBFVuInlK` | singleSelect | audiências.tipo + audiências.modalidade | normalizar.AUDIENCIA separa tipo de modalidade (INSTRUCAO/VIDEO -> INSTRUCAO + VIDEO). UNA-RS também grava processos.rito=SUMARÍSSIMO [CONFIRMAR 17] | CÓPIA |
| Nº  CumPrSe | `fld1cGAki3SIlZbR1` | singleLineText | processos.numero_cumprse | texto; é o gate numero_cumprse e decide EXECUÇÃO -> PROVISORIA | PROCESSUAL |
| RESULTADO | `fldHmpf2oiTu20L52` | multilineText | processos.resultado_texto | multiline; o resultado em prosa | CÓPIA |
| STATUS RECURSAL | `fldE3tgRGu0IOWPnr` | singleSelect | recursos (grau TRT/TST) | TST -> recurso pendente grau TST; AGUARDANDO JULGAMENTO -> grau TRT. O tipo do recurso [CONFIRMAR 22] nasce OUTRO quando a origem não diz | CÓPIA |
| STATUS CumPrSe | `fldMqtTCoxi3EZ6E7` | singleSelect | processos.situacao_execucao | normalizar.STATUS_CUMPRSE, aplicado em Migracao.completar_execucao: preenche situacao_execucao só onde STATUS EXECUÇÃO calou (12); discordância com STATUS EXECUÇÃO ou com a fase -> conferência DIVERGENCIA_FONTE (9). O texto vai para situacao_execucao_original | CÓPIA |
| STATUS DO CALCULO | `fldYUfMIYMpbhBrv7` | singleSelect | processos.situacao_execucao + cálculos | normalizar.STATUS_CALCULO -> situacao_execucao (AGUARDANDO_CALCULO / CALCULOS_APRESENTADOS / HOMOLOGADO) só onde STATUS EXECUÇÃO e CumPrSe calaram (471); em `calculos` fica `observacao` com o status — `homologado_em` fica NULL porque a origem NÃO tem a data (a carga anterior punha o ENCERRAMENTO: inventado) | CÓPIA |
| CALCULO RCTE | `fld7voVZAMyswcV0j` | currency | cálculos.valor_centavos (base=RECLAMANTE) | currency -> centavos | CÓPIA |
| SUCUMB RCTE | `fldfDoq1ys1aGn0J2` | currency | cálculos.sucumbencia_centavos (base=RECLAMANTE) | currency -> centavos | CÓPIA |
| CALCULO RCDA | `fld047wJ57Sr1aT4x` | currency | cálculos.valor_centavos (base=RECLAMADA) | currency -> centavos | CÓPIA |
| SUCUMB RCDA | `fldYWU9g1mgagHtyQ` | currency | cálculos.sucumbencia_centavos (base=RECLAMADA) | currency -> centavos | CÓPIA |
| SUCUMB HOM | `fldMeo5CAPSmG5KQx` | currency | cálculos.sucumbencia_centavos (base=HOMOLOGADO) | currency -> centavos | CÓPIA |
| VALOR HOM | `fldfDKXANsQ2fftjh` | currency | cálculos.valor_centavos (base=HOMOLOGADO) | currency -> centavos. PROCESSUAL vence: 127 preenchidos só nela | PROCESSUAL |
| STATUS PAGAMENTO | `fldbQjy8KFsPiGdZX` | singleSelect | derivado de acordo_parcelas + recebimentos | seis rotulos para "quantas parcelas pagas e alguma atrasada" (derivados). PARCELAMENTO CPC -> situacao_execucao = PARCELAMENTO_916 onde vazio; CESSAO DE CREDITOS -> processos.credito_cedido = true (3) — `credito_cedido_em` e `cessionario` ficam NULL: a origem não os tem | CÓPIA |
| ENCERRAMENTO | `fldQA3V008aWgVolE` | date | processos.encerrado_em | date -> TEXT ISO | CÓPIA |
| DRIVE | `fld6hyVSCCrjy4HNd` | url | processos.drive_url | url | CÓPIA |
| ASTREA | `fldOjPxn0cd09XD47` | url | processos.astrea_url | url | CÓPIA |
| OBSERVACOES | `fld9AH9a7dN1UFjO3` | multilineText | anotações (campo_origem=OBSERVACOES) | multiline -> anotação com autor desconhecido e origem MIGRACAO | CÓPIA |
| PRE PROCESSUAL | `fldI2egQzyDoQNA26` | singleLineText (era link; virou texto na cópia) | processos.cliente_id | link (na CÓPIA virou texto: casado pelo nome + número, e o que não casar -> conferências) | PROCESSUAL |
| PÓS PROCESSUAL | `fldk6Bc8G9oo0mVX2` | multipleRecordLinks | recebimentos + repasses + processos.arquivado_em | link; o PÓS não é entidade própria (ver seção PÓS PROCESSUAL) | PROCESSUAL |
| TURMA | `fldV1qxYFBzIvY7dr` | singleLineText | processos.turma | normalizar.turma(): "Nª TURMA"/"Nª CÂMARA" normalizados, órgãos por nome. A duplicação da tabela cortou o texto em 24 caracteres: 270 registros dizem "VICE-PRESIDÊNCIA JUDICIA" e só um órgão começa assim — vira VICE-PRESIDÊNCIA JUDICIAL por PREFIXO (não é semelhança). "SDI" (1) é órgão. Carga real: 1.411 preenchidos, 1.411 traduzidos | CÓPIA |
| CADEIRA | `fldTn11UpgYqChRNJ` | singleLineText | processos.cadeira | texto (cadeira do desembargador na turma) | só na CÓPIA |
| RELATOR | `fldcRZsg4HYSgn666` | singleLineText | processos.relator | texto (desembargador do TRT-2) | só na CÓPIA |
| TESTEMUNHAS | `fldrTMw8NSJt7xWXJ` | singleLineText (era link; virou texto na cópia) | testemunha_vinculos.processo_id | link (texto na CÓPIA) | PROCESSUAL |
| DATA ADVIDEO | `fldzwbysEw21OFH66` | dateTime | audiências.advideo_em | vazio em 100%; sem audiência para pendurar fica em airtable_bruto | CÓPIA |
| RESP ADVIDEO | `fldi8Shnzt9hdNsSq` | singleLineText | audiências.advideo_responsavel_id | vazio em 100% | CÓPIA |
| STATUS ADVIDEO | `fld7VrihnJYxdv4zs` | singleSelect | audiências.advideo_previsto / advideo_em | PENDENTE/MARCADO/FEITO viram o checklist da audiência. 1 registro [CONFIRMAR 14: o que e ad video] | CÓPIA |
| PERICIA MEDICA | `fld0BJrdoG4Vqjq90` | checkbox | processos.pericia_medica + pericias(tipo=MEDICA) | checkbox -> boolean; com DATA PERICIA MEDICA vira linha em pericias | CÓPIA |
| PERICIA TECNICA | `fldGF9gLMUmmzwvMj` | checkbox | processos.pericia_tecnica + pericias(tipo=TECNICA) | idem | CÓPIA |
| STATUS EXECUÇÃO | `flddhvTNt3K4hNvPm` | singleSelect | processos.situacao_execucao + situacao_execucao_original (+ processos.resultado_final) | normalizar.STATUS_EXECUCAO: 36 opções -> 16 estados. SIM/NAO/EXECUCAO/RECURSAL viram NULL + conferências (45 na carga real). O valor que estava na COLUNA ERRADA (198 processos: ARQUIVADO 153, EXTINTA S/ RESOLUÇÃO 24, EXECUÇÃO PROVISÓRIA 16, SOBRESTADO 2, AUDIÊNCIA CONCILIAÇÃO 3) é tratado por `Migracao.situacao_execucao()`: ARQUIVADO/EXTINTA em processo ENCERRADO completam `resultado_final`; a mesma fase é coerente e nada há a fazer; o que DISCORDA da fase gravada (24) abre conferência. O texto original fica sempre | PROCESSUAL |
| AND. NECESSÁRIO | `fldF8mxBzD5cRsL4C` | singleSelect | tarefas (tipo=ANDAMENTO, texto_original) | "andamento necessário" é tarefa por definição. Encerrado/ACORDO são redundantes com a fase e não viram tarefa [CONFIRMAR 19] | PROCESSUAL |
| AÇÃO | `fldbNuYY7kHhvPAij` | date | processos.ajuizamento_em | date -> TEXT ISO [CONFIRMAR: difere de DISTRIBUICAO em que?] | CÓPIA |
| TEL VARA | `fldzDjqJNQYrMrBOz` | phoneNumber | processos.tel_vara | telefone | CÓPIA |
| STATUS ACORDO | `fldmPIGUEID71M0ue` | singleSelect | acordos.situação | EM ANDAMENTO / CUMPRIDO / QUEBRA -> acordos.situacao; `quebrado_em` fica NULL — a origem só tem o status, não a data da quebra. Acordo com VALOR ou DATA e sem status nasce EM_ANDAMENTO com conferência (9) | CÓPIA |
| VALOR ACORDO | `fldsX34Hdi6gWfBOd` | currency | acordos.valor_centavos | currency -> centavos | CÓPIA |
| TOTAL RECEBIDO | `flduvkfUUz051hyBl` | currency | recebimentos.valor_centavos (base=TOTAL) | currency -> centavos | CÓPIA |
| SUCUMB RECEBIDO | `fldevSd5kepM7fqzt` | currency | recebimentos.valor_centavos (base=SUCUMBENCIA) | currency -> centavos. PROCESSUAL vence: 67 só nela | PROCESSUAL |
| HONOR TOTAL | `fld6yZmxZQSqoa7GI` | currency | recebimentos.valor_centavos (base=HONORARIOS) | currency -> centavos | CÓPIA |
| SITU. EMPRESA | `fld9nTJODAgIcIQtl` | multipleLookupValues (EMPRESA→STATUS EMPRESA) | empresas.situação | lookup: o atributo e da empresa (JOIN). A divergência de verdade é do LINK: 423 processos apontam para reclamadas diferentes na CÓPIA e na PROCESSUAL -> conferência DIVERGENCIA_FONTE campo EMPRESA, com o nome de cada lado; o lookup só vira conferência própria quando o link é o mesmo e ainda discorda do cadastro (14) | PROCESSUAL |
| BENS IDENTIFICADOS | `fldEU44SA3BMGftq0` | multipleSelects | empresas.bens_identificados | atributo da empresa, estava nos dois lugares | CÓPIA |
| HIST. PAGAMENTO | `fldghU4b5RnjNapAS` | multipleSelects | empresas.hist_pagamento | idem | CÓPIA |
| ULTIMA MOV | `fldUVIxnej2Gd9Oe9` | singleLineText | processos.ultima_movimentacao + ultima_movimentacao_em | texto "aaaa-mm-dd - descrição": a data é separada do texto | CÓPIA |
| REVOGAÇÃO | `fldlL3QF5v6Nfy6zR` | singleSelect | processos.revogou_patrono_anterior | incidentes.revogacao_nos_autos_em | tarefas | normalizar.REVOGACAO + Migracao.revogacao_destino. O SENTIDO depende do STATUS DO PROCESSO: ROUBADO/RECEBIDO POR ELES/RECUPERADO (ou REVOGAÇÃO = ROUBADO) e o cliente que nos revogou (incidente); em qualquer outro caso somos nos que juntamos a revogação do patrono anterior -> revogou_patrono_anterior SIM/NÃO (794/66), haja ou não incidente por notificação/providência [CONFIRMAR 20]. Os recados viram tarefa (5). Provado em conferir.py | PROCESSUAL |
| DATA REVOG | `fldLXyHn58qh1Set9` | date | processos.revogacao_em | incidentes.revogacao_nos_autos_em | date -> TEXT ISO. PROCESSUAL vence. A data NUNCA fica sem coluna: sentido 2 -> incidentes.revogacao_nos_autos_em (101); qualquer outro caso, com REVOGAÇÃO preenchida ou não -> processos.revogacao_em (1.326). REVOGAÇÃO = NÃO com data é contradição: grava-se e abre conferência (79). conferir.py prova 1.427 = 1.326 + 101 | PROCESSUAL |
| NOTIFICAÇÃO | `fld74RYjSUkhe9J8Z` | singleSelect | incidentes.situação + as datas da notificação | REDIGIDA -> DETECTADO; ENVIADA/RECEBIDA/RESPONDIDA -> NOTIFICADO. As DATAS (redigida, enviada, recebida, resposta) ficam NULL: a origem não as tem, e a carga anterior punha DATA REVOG ou ENCERRAMENTO nelas (72 inventadas). O valor original vai para incidentes.airtable_bruto | PROCESSUAL |
| PROVIDENCIAS | `fldpK9kuxpxrnH713` | singleLineText | incidentes.providencia_texto + tarefas | NOTIFICAR -> tarefa "enviar notificação"; TRAVAR O RECEBIMENTO -> tarefa "pedir reserva de honorários (EOAB art. 22 §4º)" | PROCESSUAL |
| SUCUMBÊNCIA % | `fldks912wlwUNkLLI` | singleLineText | processos.sucumbencia_percent | texto "5%" -> número. O "2500%" é erro: vai para conferências | CÓPIA |
| CLIENTE AVISADO? | `fldFZHpbUQTtHLVck` | checkbox | incidentes.cliente_avisado_em | checkbox -> incidentes.airtable_bruto. `cliente_avisado_em` fica NULL: a origem não tem a data (0 usos hoje) [CONFIRMAR] | PROCESSUAL |
| CAPTADOR | `fldM9FYwqqrt028S0` | multipleRecordLinks | processos.captador_id | link -> FK pessoas(id) | CÓPIA |
| TELEFONE | `fldbfyukYiqC0Hkc3` | phoneNumber | processos.telefone_parte (+ clientes.telefone na ficha criada dos autos) | CÓPIA vence; a outra grafia vai para processo_alias | CÓPIA |
| ASSINATURA | `fldE4LiWHGVLwLFmQ` | date | processos.assinatura_em (+ clientes.data_assinatura_contrato) | date -> TEXT ISO. CÓPIA vence: 58% contra 4%. Completa a ficha do cliente onde ela não tinha (ficha criada dos autos ou PRÉ sem DATA DE ASSINATURA); ficha que continua sem -> pendência DOCUMENTO/CONTRATO obrigatória (1.283) | CÓPIA |
| status_disparo | `fldwFWTG2IHDz3ml7` | singleLineText | automacao_log (origem N8N) | idem PRE | CÓPIA |
| tipo_disparo | `fldHslk7xJyh4geK9` | singleLineText | automacao_log.detalhe | idem | CÓPIA |
| data_solicitacao_disparo | `fldCusUDDQZVVlG90` | singleLineText | automacao_log.em | idem | CÓPIA |
| responsavel_interno | `fldOFRB4MsT7afsjh` | singleLineText | automacao_log.detalhe | idem | CÓPIA |
| solicitante_disparo | `fldMnopQa1geAfZ6F` | singleLineText | automacao_log.detalhe | idem | CÓPIA |
| Created By | `fldS83Q4JgPzTGrwO` | createdBy | processos.atualizado_em (PROCESSUAL) | processos.airtable_bruto (CÓPIA) | na PROCESSUAL o tipo é lastModifiedTime apesar do nome e vai para processos.atualizado_em (2.652); na CÓPIA é createdBy de verdade e o nome de quem criou fica no bruto. O createdTime do record vai para processos.criado_em / clientes.criado_em da ficha dos autos, e é o último recurso do histórico | CÓPIA |
| DATA PERÍCIA TECNICA | `fldUtGNLeRxja7zak` | dateTime | pericias.data_hora (tipo=TECNICA) | dateTime -> TEXT ISO | CÓPIA |
| DATA PERÍCIA MÉDICA | `fldQ4cGTtZNF32DCw` | dateTime | pericias.data_hora (tipo=MEDICA) | dateTime -> TEXT ISO | CÓPIA |
| NASCIMENTO | `fldzfTA6f9VueZKjs` | singleLineText (na PROCESSUAL é date) | processos.nascimento_parte (+ clientes.data_nascimento) | date na PROCESSUAL, texto na CÓPIA: normalizar.data_br. Completa clientes.data_nascimento onde vazio; ficha que continua sem -> pendência CADASTRO (1.012). O que não é data (1 registro com ano 2977) fica NULL + conferência DATA_ILEGIVEL. Divergencia -> processo_alias | CÓPIA |
| RESULTADO RECURSO | `fldZkL74gu3iQgXcg` | singleSelect | decisões.resultado_objetivo (tipo=ACORDAO) + recursos.resultado | PROVIDO / PARCIALMENTE PROVIDO / NEGADO PROVIMENTO / NAO CONHECIDO. É o resultado OBJETIVO, que não existe na PROCESSUAL | só na CÓPIA |
| E-MAIL | `fldgG8Hd7zpleuQ1e` | email | processos.email_parte (+ clientes.email) | extraído da qualificação da inicial | só na CÓPIA |
| CPF | `fldjR2BqXLKic3bLi` | singleLineText | processos.cpf_parte (+ clientes.cpf) | só dígitos; é a chave que casa o processo com a ficha do cliente | só na CÓPIA |
| CNPJ RECLAMADA | `fldzoCBbwPimGJ8TO` | singleLineText | processos.cnpj_reclamada + razao_social_reclamada + empresas.cnpj | o campo traz CNPJ e razao social juntos: normalizar.cnpj_razao separa. Sobe para empresas.cnpj só quando INEQUÍVOCO — todos os processos da empresa com o mesmo CNPJ (518); mais de um CNPJ na mesma empresa (112) ou o mesmo CNPJ em mais de um cadastro (59) -> conferência EMPRESA_AMBIGUA. A razão social só sobe quando é uma só (187) | só na CÓPIA |
| TURMA TST | `fldtI4VOrmuR4lmfB` | singleLineText | processos.turma_tst | texto; não confundir com TURMA (TRT-2) | só na CÓPIA |
| RELATOR TST | `fld0D2Xe2qPSYoFHE` | singleLineText | processos.relator_tst | texto (ministro relator) | só na CÓPIA |
| ARQUIVO TST | `fldnDFmHWlZ2mIRau` | date | processos.arquivo_tst_em | date -> TEXT ISO. A descrição na origem e cópia errada da de RELATOR TST [CONFIRMAR: e a data do arquivamento no TST?] | só na CÓPIA |
| HONOR  TOTAL HOMOL | `fldjTxAsINi06RGAC` | currency ($) | cálculos.honorario_centavos (base=HOMOLOGADO) | currency -> centavos | só na CÓPIA |
| HONOR TOTAL CALCULO RCDA | `fldlaGkINPddsXb6v` | currency ($) | cálculos.honorario_centavos (base=RECLAMADA) | currency -> centavos | só na CÓPIA |
| HONOR TOTAL CALCULO RCTE | `flde0ZJbihjoOHrWN` | currency ($) | cálculos.honorario_centavos (base=RECLAMANTE) | currency -> centavos | só na CÓPIA |
| PARCELAS | `fldBn7cBdNVgFNyjF` | number | acordos.parcelas | number -> inteiro | CÓPIA |
| VALOR PARCELA | `fldfesN5ruhEAWoAd` | currency ($) | acordos.valor_parcela_centavos | currency -> centavos | só na CÓPIA |
| HONOR TOTAL ACORDO | `fldY0QwVVHGlnOuIc` | currency ($) | acordos.honorario_centavos | currency -> centavos (30% em 603 de 687 casos) | só na CÓPIA |
| DATA DO ACORDO | `fldANF4EoWZgUQ265` | date | acordos.homologado_em | date -> TEXT ISO. NAO confundir com DATA ACORDAO (o acordao) | só na CÓPIA |

## PÓS PROCESSUAL — `tblEInHoBmUuuShxk` (556 registros)

Não e entidade própria: vira `recebimentos`, `repasses` e `processos.arquivado_em`.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| N° DO PROCESSO | `fld9mP0tgsxUskRUk` | singleLineText | casamento por numero_cnj | é a chave para achar o processo quando o link está vazio (101 casos) | — |
| PROCESSUAL | `fldU96KT0xLEKEqTR` | multipleRecordLinks | recebimentos.processo_id / repasses.processo_id | link -> FK processos(id) | — |
| RESULTADO FINAL | `fldsprvUfBAJvkn5v` | multilineText | processos.resultado_texto | copiado de PROCESSUAL.RESULTADO pela automação; só preenche se o processo estiver vazio | — |
| VALOR RECEBIDO CLIENTE | `fldffOZ2m1k24WKmv` | currency | recebimentos.valor_centavos (base=CLIENTE) | currency -> centavos | — |
| VALOR HONORARIOS | `fldQ8CSjqZKxNs1zN` | currency | recebimentos.valor_centavos (base=HONORARIOS) | currency -> centavos; divergência com PROCESSUAL.HONOR TOTAL -> conferências | — |
| VALOR SUCUMBÊNCIA | `fld5bNSeZULhtm1z6` | currency | recebimentos.valor_centavos (base=SUCUMBENCIA) | idem | — |
| STATUS RECEBIMENTO | `fldjVs3BRdXuZ1ous` | singleSelect | derivado de recebimentos + acordo_parcelas | duas familias de opções (Title Case nunca usada e as copiadas de STATUS PAGAMENTO). Nenhuma vira coluna | — |
| STATUS REPASSE | `fldH73Oe7hXIVU8gn` | singleSelect | derivado de repasses | vazio em 100%. O gate repasse_registrado obriga daqui em diante [CONFIRMAR 26] | — |
| STATUS ARQUIVAMENTO | `fldRXQMrAUjP7XTFb` | singleSelect | processos.arquivado (bool) + tarefas(tipo=ARQUIVAMENTO) | Arquivado -> arquivado = true (37); Não arquivado -> false; Em andamento -> tarefa aberta (30). `arquivado_em` fica NULL: a origem não tem a data (a carga anterior copiava o encerramento). O registro do PÓS inteiro vai para processos.airtable_bruto.pos. Arquivo físico é providência, não fase [CONFIRMAR 28] | — |
| RESPONSAVEL | `flduzeLbJpPQfDsRb` | multipleRecordLinks | tarefas.responsavel_id | link -> FK pessoas(id): quem responde pelo pós-processo | — |
| EVENTOS | `fldXAKlcH7qnnDtnN` | singleLineText | descartado | vazio em 100% | — |
| DATA DE ASSINATURA | `fldoIShmhcL6p50mf` | date | descartado | vazio em 100% | — |
| PROCESSUAL copy | `fldjgR4odQVppdd76` | multipleRecordLinks | airtable_bruto | legado: link para a CÓPIA. A ligação útil é a do número CNJ | — |

## EMPRESAS — `tblkfWQhjp2F1dK0y` (1.103 registros)

As reclamadas. Vira `empresas`.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| EMPRESA | `fld8PWuRCXVfhxTym` | singleLineText | empresas.nome + empresas.nome_norm | texto | — |
| SEGMENTO | `fldFIha0DxiXkcTnz` | singleLineText | empresas.segmento | texto (1% preenchido) | — |
| STATUS EMPRESA | `fld1oC98eM8PyYXnj` | singleSelect | empresas.situação | ATIVA/INATIVA/EM RECUPERACAO -> lista fechada | — |
| HIST. PAGAMENTO | `fldZFSd2f9WKgXmAX` | singleSelect | empresas.hist_pagamento | BOA/RUIM/PESSIMA | — |
| BENS IDENTIFICADOS | `fld5RoWyzrwCrlyhF` | singleSelect | empresas.bens_identificados | SIM/NAO -> boolean | — |
| QTD PRE PROCESSUAIS | `fld5kiPkQs0NgUmHR` | count | derivado | count | — |
| QTD PROCESSOS | `fldvQDr03ufTK6Rox` | count | derivado | count | — |
| PRE PROCESSUAL | `fldD5vMVGmZWK8kV9` | multipleRecordLinks | clientes.empresa_id (inverso) | link inverso | — |
| PROCESSUAL | `fldoLaOZc58DQTQYK` | multipleRecordLinks | processos.empresa_id (inverso) | idem | — |
| TESTEMUNHAS | `fldTSCNT3dxkNcOwd` | multipleRecordLinks | testemunhas.empresa_id (inverso) | idem | — |
| Conferência de Faltantes | `fldv9zdBAoyq6l1pk` | multipleRecordLinks | conferencia_faltantes.empresa_id (inverso) | idem | — |
| PROCESSUAL copy | `fldNSV8upoiovsDcZ` | multipleRecordLinks | processos.empresa_id (inverso) | idem, pelo lado da CÓPIA | — |
| TEMP_RECORD_ID | `fldsJ6npBmOeQEmBf` | fórmula | empresas.airtable_record_id | fórmula RECORD_ID(); temporário de importação | — |
| GGV_RECORD_KEY | `fld5PYHnY54f43Bn6` | multilineText | empresas.ggv_record_key | chave de 17 caracteres do script de deduplicação [CONFIRMAR uso] | — |
| FRAGILIDADES | `fldwMi9cllR7nByNy` | multipleRecordLinks | fragilidades.empresa_id (inverso) | link inverso | — |

## FUNCIONARIOS — `tblisgqzJvF0EUFr1` (72 registros)

Vira `pessoas` + `pessoa_papeis`.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| NOME | `fld4vMwXvl02w9SKT` | singleLineText | pessoas.nome + pessoas.nome_norm | texto | — |
| FUNCOES | `fldFrbKtMbkw22Xkw` | multipleSelects | pessoa_papeis.papel | multipleSelects -> uma linha por papel; normalizar.PAPEL | — |
| STATUS | `fldshQnOdcryOtSSG` | singleSelect | pessoas.ativo | ATIVO/INATIVO -> boolean | — |
| OBSERVACOES | `fldiYwZR5carDh1Fa` | multilineText | pessoas.observação | texto | — |
| VINCULADOS EM PRÉ PROCESSUAIS | `fld45ySggxcVGXtqE` | count | derivado | count: sai de COUNT(*) | — |
| VINCULADOS EM PROCESSUAL | `fldsU7vtvEiEYCI49` | count | derivado | count | — |
| Vinculados Pós Processual | `fldGY57cOYsiSSjXz` | count | derivado | count | — |
| PRE PROCESSUAL | `fldbtWNLkdEYNr7sM` | multipleRecordLinks | clientes.captador_id (inverso) | link inverso: a FK já existe do outro lado | — |
| PROCESSUAL | `fld312t1O55vdmsTO` | multipleRecordLinks | processos.captador_id (inverso) | idem | — |
| PÓS PROCESSUAL | `fldjm90NmYClUZSAe` | multipleRecordLinks | tarefas.responsavel_id (inverso) | idem | — |
| PRE PROCESSUAL (ENTREVISTADOR) | `fldeMPgdqUz3V6NFx` | multipleRecordLinks | clientes.entrevistador_id (inverso) | idem | — |
| PRE PROCESSUAL (RESPONSAVEL INICIAL) | `fld2pGLJ6wS9nAiiO` | multipleRecordLinks | clientes.responsavel_id (inverso) | idem | — |
| PROCESSUAL (ADVOGADO) | `fldogyJ0qD1QOHmgr` | multipleRecordLinks | processos.advogado_id (inverso) | idem | — |
| PROCESSUAL 2 | `fldgszRDyGpSCT531` | multipleRecordLinks | descartado | inverso de RESP ADVIDEO; vazio em 100% | — |
| PROCESSUAL copy | `flds8NNw1ofgSVf73` | multipleRecordLinks | processos.captador_id / advogado_id (inverso) | dois campos com o mesmo nome: inversos de CÓPIA.CAPTADOR e CÓPIA.ADVOGADO | — |
| PROCESSUAL copy | `fldNnj3vDWbBtg9uG` | multipleRecordLinks | processos.captador_id / advogado_id (inverso) | dois campos com o mesmo nome: inversos de CÓPIA.CAPTADOR e CÓPIA.ADVOGADO | — |
| TESTEMUNHAS | `fldUOTBlsE2Q5YSZu` | multipleRecordLinks | testemunhas.captador_id (inverso) | idem | — |
| ntfy_topic | `fldEQpbSqdZy2Oxqq` | singleLineText | pessoas.ntfy_topic | texto | — |
| ntfy_ativo | `fldcLfpwxzdL9IZmu` | singleSelect | pessoas.ntfy_ativo | ATIVO/INATIVO -> boolean | — |
| rec_id | `fld8J8UwoHuFSIeeo` | fórmula | pessoas.airtable_record_id | fórmula RECORD_ID(): é o mesmo record id que já se guarda | — |

## TESTEMUNHAS — `tbl9nZjfmxqVy60NM` (424 registros)

Vira `testemunhas` + `testemunha_vinculos`.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| NOME TESTEMUNHA | `fldrHyp7RMyfHsWGS` | singleLineText | testemunhas.nome + nome_norm | texto. Os 2 registros SEM nome da base real entram como "(sem nome na origem)" + conferência: um deles tem link com processo, e pular seria perder linha e vínculo | — |
| TELEFONE TESTEMUNHA | `fldEQLHWzqOnwZBrA` | phoneNumber | testemunhas.telefone | só dígitos | — |
| CPF | `fldzAzyQWU6CVmIMc` | singleLineText | testemunhas.cpf | só dígitos | — |
| VINCULO | `fldrxRtZFJi3UuXpH` | singleSelect | testemunhas.vinculo | lista fechada; NAO INFORMADO preservado | — |
| CAPTADOR | `fldDYCfV1rMBFPKcd` | multipleRecordLinks | testemunhas.captador_id | link -> FK pessoas(id) | — |
| EMPRESA | `fld4PE2tWssCXwqgo` | multipleRecordLinks | testemunhas.empresa_id | link -> FK empresas(id) | — |
| ENDEREÇO | `fldK3eRkTTQAsZ7Zy` | singleLineText | testemunhas.endereco | texto | — |
| ARQUIVOS ENVIADOS PELA TESTEMUNHA | `fldqV2SomcjvHG84r` | multipleAttachments | documentos (fonte=ANEXO_AIRTABLE, testemunha_id) | SO METADADO: nome, url, tamanho. Nenhuma cópia de arquivo | — |
| DATA DE ADMISSÃO | `fldw9M4F91aiLnb4p` | date | testemunhas.admissao_em | date -> TEXT ISO | — |
| HORARIO DE TRABALHO | `fld6TKjssQyjxuV6p` | singleLineText | testemunhas.horario_trabalho | texto | — |
| TEM PROCESSO? | `fldAqPD3ogsosM3PD` | singleSelect | testemunhas.tem_processo | SIM/NAO -> boolean. Súmula 357 TST: não a torna suspeita, mas a reclamada contradita | — |
| STATUS TESTEMUNHA | `fldkwGHMugckeWh7j` | singleSelect | testemunhas.situação + confirmada_em | lista fechada com CHECK, sem gatilho: caminho óbvio e o que importa é confirmada_em | — |
| COBRANÇA | `fld7u0W3vbAk3vOIY` | singleSelect | testemunhas.cobrancas + contatos | 1º..4º -> contador; é uma linha em contatos com DATA ULTIMO CONTATO | — |
| DATA ULTIMO CONTATO | `fldeil2kdiLHeVTs5` | date | testemunhas.ultimo_contato_em | date -> TEXT ISO | — |
| OBSERVACOES | `fldMmEx19k0nHEaj3` | multilineText | anotações (testemunha_id) | texto | — |
| TESTEMUNHA DE: | `fld0YIS1gw5thKMXl` | multipleRecordLinks | testemunha_vinculos.processo_id | link -> PROCESSUAL | — |
| TESTEMUNHA DE | `fld8Ju3YQHmrg9H9U` | multipleRecordLinks | testemunha_vinculos.cliente_id | link -> PRE PROCESSUAL. No formulário COMERCIAL os rotulos estão trocados: a migração usa o campo, não o rotulo | — |
| ENVIAR MENSAGEM | `fldbdxC9rd85oPaa2` | button | descartado | botao | — |
| DUPLICADO? | `fldowrtPW27eUtbuR` | singleSelect | testemunhas.duplicado | SIM/NAO -> boolean | — |
| ENCONTROU NOSSO CLIENTE NA ETAPA PROCESSUAL | `fldNribYFmmGfLh9K` | singleSelect | testemunha_vinculos.observação | resposta do formulário; não e estado da testemunha | — |
| origem_testemunha | `fldSkTfJWuY8F6KgI` | singleSelect | testemunhas.origem | JURIDICO/COMERCIAL | — |
| status_disparo | `fldWvBPCjQg8b7U04` | singleLineText | automacao_log (origem N8N) | idem PRE | — |
| tipo_disparo | `fld3UuiNQyV8IMcJc` | singleLineText | automacao_log.detalhe | idem | — |
| data_solicitacao_disparo | `fldANhrX8JEGGx0Cf` | singleLineText | automacao_log.em | idem | — |
| responsavel_interno | `fldHkFricEmDUZq7G` | singleLineText | automacao_log.detalhe | idem | — |
| solicitante_disparo | `fldBu4DURpSoRMhT1` | singleLineText | automacao_log.detalhe | idem | — |
| Created By | `fldLJM2Ul23O6hUtr` | createdBy | testemunhas.criado_em | createdBy -> a data; o nome vai para o bruto | — |
| origem_comercial_tabela_id | `fldhQcu6eQAm7fhcP` | singleLineText | airtable_bruto | vazio em 100% | — |
| origem_comercial_registro_id | `fldR5XpQnKUDPrgiO` | singleLineText | testemunhas.origem_registro_id | texto | — |
| notif_captador_status | `fldO1rJSSpWyDd4i1` | singleSelect | automacao_log (origem N8N) | máquina de estados do n8n para avisar o captador; é rastro de automação | — |
| notif_captador_ultimo_envio | `fldg5OgxicfYCFNMp` | dateTime | automacao_log.em | idem | — |
| AINDA TRABALHA NA EMPRESA? | `fldQyw23638IeGoSU` | singleSelect | testemunhas.ainda_trabalha | SIM/NAO -> boolean | — |
| DATA DE DEMISSÃO | `fldFsISkknfBG2uCk` | date | testemunhas.demissao_em | date -> TEXT ISO | — |
| LINK DA TESTEMUNHA | `fldR3LD4dY3w2wtof` | fórmula | derivado | fórmula: URL pública do n8n com o RECORD_ID() | — |
| CADASTRADO POR | `fldiJxmCEeuxTtcS4` | singleLineText | airtable_bruto | vazio em 100% (previsto para o Formulário Interno Único) | — |
| ÚLTIMA ALTERAÇÃO POR | `fldBKvxASKPHrRRnP` | singleLineText | airtable_bruto | vazio em 100% | — |
| ÚLTIMA ALTERAÇÃO EM | `fldsKOswTUpLC2mEr` | singleLineText | airtable_bruto | vazio em 100% | — |

## Conferência de Faltantes — `tblnQHm5yTj2EPscB` (1.067 registros)

Lista de conferência, não processos: vira `conferencia_faltantes`, ligada a `processos` quando o CNJ casa.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| NOME | `fldiXouLVt5bEmWQV` | singleLineText | conferencia_faltantes.nome | texto | — |
| Nº PROCESSO | `fldTdMHygimECEwsK` | singleLineText | conferencia_faltantes.numero_cnj | texto; casa com processos por numero_cnj_digitos (539 já estão na CÓPIA) | — |
| EMPRESA | `fldRDowg9rI1KpNFA` | multipleRecordLinks | conferencia_faltantes.empresa_id | link -> FK empresas(id) | — |
| VALOR | `fldeG3B32zeCC2WPi` | currency | conferencia_faltantes.valor_causa_centavos | normalizar.dinheiro(): currency -> centavos. A carga real achou aqui UM registro com vinte dígitos no lugar do valor — um número de processo; em centavos estourava o bigint e derrubava a carga inteira. Fica NULL, o original no bruto, e abre conferência VALOR_SEM_TRADUCAO | — |
| TRT | `fldnL40KBxnjAeqNN` | singleLineText | conferencia_faltantes.trt | texto (aqui não é select) | — |
| VARA | `fldtiCR5qTUWTaUn0` | singleLineText | conferencia_faltantes.vara | texto | — |
| DISTRIBUIÇÃO | `fldB7NroOPiW7QA9R` | date | conferencia_faltantes.distribuicao_em | date -> TEXT ISO | — |
| FASE RECOMENDADA (DATAJUD) | `fldzmstT8o14h8nzN` | singleLineText | conferencia_faltantes.fase_recomendada | texto do Datajud; NAO vira processos.fase sem alguém validar | — |
| STATUS RECOMENDADO (DATAJUD) | `fldenynnXu7l80Moi` | singleLineText | conferencia_faltantes.status_recomendado | idem | — |
| ÚLTIMO MOVIMENTO (DATAJUD) | `fldsfbRUpv15Qf5kX` | singleLineText | conferencia_faltantes.ultimo_movimento | texto | — |
| OBSERVAÇÕES | `fldsLUyWvVvrTpWRO` | multilineText | conferencia_faltantes.observações | texto | — |
| ✅ VALIDAR E SUBIR | `fld4U33RUENZEmE55` | checkbox | conferencia_faltantes.validar_e_subir | checkbox -> boolean. 0/1067 marcados e a automação prometida nunca existiu | — |
| STATUS PROCESSO | `fldas5l0gp8vqKyXv` | singleLineText | conferencia_faltantes.status_processo | texto; só ARQUIVADO (326) | — |

## AUDITORIA TESTEMUNHAS — `tblKp6rhoOGL2ChrO` (2 registros)

Log append-only. Migra como está: não se reescreve auditoria.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| EVENTO ID | `fldx5Jbz799lWEpmU` | singleLineText | testemunha_auditoria.evento_id | texto | — |
| DATA/HORA | `fldXDNL9mN1dhmg6R` | singleLineText | testemunha_auditoria.em | ISO 8601 UTC -> TEXT | — |
| ATOR RECORD ID | `fld99aghkSNZanSqh` | singleLineText | testemunha_auditoria.ator_record_id | texto | — |
| ATOR NOME SNAPSHOT | `fldbuUHc90qKwRdZe` | singleLineText | testemunha_auditoria.ator_nome | texto | — |
| SETOR SNAPSHOT | `fldXWLhYf8gt0Jc8l` | singleLineText | testemunha_auditoria.setor | texto | — |
| AÇÃO | `fldzPUtO3DQGRiICO` | singleLineText | testemunha_auditoria.ação | texto | — |
| TESTEMUNHA RECORD ID | `fldiWGDSICPKfqemf` | singleLineText | testemunha_auditoria.testemunha_record_id + testemunha_id | texto + FK | — |
| TESTEMUNHA NOME SNAPSHOT | `fldiXicuaU25o9Wie` | singleLineText | testemunha_auditoria.testemunha_nome | texto | — |
| CONTEXTO | `fldvS9AQJX6ijETP0` | multilineText | testemunha_auditoria.contexto | texto | — |
| CAMPÓS ALTERADOS | `fldU7V6fUlyXfqNq8` | multilineText | testemunha_auditoria.campos_alterados | texto (JSON como veio) | — |
| ANTES | `fld0bei6vj61qmf4a` | multilineText | testemunha_auditoria.antes | idem | — |
| DEPOIS | `fldggIM5PoCNdX7cE` | multilineText | testemunha_auditoria.depois | idem | — |
| OPERATION ID | `fldUGaOLMg8R2xsNf` | singleLineText | testemunha_auditoria.operation_id | texto | — |
| RESULTADO | `fldQMmrpCSpJ5ewns` | singleLineText | testemunha_auditoria.resultado | texto | — |
| ORIGEM/SISTEMA | `flds8Ktz2DrXxHdLB` | singleLineText | testemunha_auditoria.origem_sistema | texto | — |

## FRAGILIDADES — `tblmxkxgQEbc0KwvV` (17 registros)

O banco de teses por reclamada. Vira `fragilidades`.

| campo | id | tipo | destino | regra de conversão | vence |
|---|---|---|---|---|---|
| ACHADO | `fldhiPzMOkwrNlPRc` | singleLineText | fragilidades.achado | texto | — |
| EMPRESA | `fldCYcTOQQv1m6lNH` | multipleRecordLinks | fragilidades.empresa_id | link -> FK empresas(id) | — |
| EIXO | `fldCf0uKDUvbIBVGp` | singleSelect | fragilidades.eixo | texto: a lista fica ABERTA de propósito: o eixo nasce da leitura dos autos | — |
| FORCA | `fldAzf4jY99QJigyP` | singleSelect | fragilidades.forca | lista fechada | — |
| STATUS | `fldJWq7j3CkqlJfYM` | singleSelect | fragilidades.situação | lista fechada (Inedita / Acolhida / Acolhida em parte / Rejeitada / Em julgamento) | — |
| DESCRICAO | `fldEe2BlzvU2hdHh5` | multilineText | fragilidades.descrição | texto | — |
| FUNDAMENTO | `fldoyTu3RO667EPmR` | multilineText | fragilidades.fundamento | texto | — |
| PROVA | `fldCphzgJNuG3OTsA` | multilineText | fragilidades.prova | texto | — |
| COMO EXPLORAR | `fldHXZBfEOSmW31D0` | multilineText | fragilidades.como_explorar | texto | — |
| DOC A REQUERER | `fldGqbdkJEh2h2N0T` | multilineText | fragilidades.doc_a_requerer | texto | — |
| PROCESSOS | `fldaz2RuxYdnAhbtW` | multilineText | fragilidades.processos_texto | texto livre com os autos; não vira FK porque não é lista de números | — |
| PERIODO | `fldRaDUyyxThY1L5o` | singleLineText | fragilidades.periodo | texto | — |
| VALOR ESTIMADO | `fldoWQoTv1bJkdvHk` | currency | fragilidades.valor_estimado_centavos | currency -> centavos | — |
| DOSSIE | `fldqhiuYK1foxVj4o` | multipleAttachments | documentos (fragilidade_id) | SO METADADO (0 anexos hoje) | — |
| ATUALIZADO EM | `fldZ2sZUFg6QdJYNQ` | date | fragilidades.atualizado_em | date -> TEXT ISO | — |

## O que fica só no `airtable_bruto`, e por que

| o que | quantos | por que não vira coluna |
|---|---|---|
| `_BACKUP_VALOR_ANTES_SCRIPT`, `_BACKUP_COMPLEXIDADE_ANTES_SCRIPT`, `_BACKUP_FEITO_EM_SCRIPT` | 233 / 181 / 233 | Lixo técnico: backup que um script fez antes de reescrever VALOR e COMPLEXIDADE em julho/2026. Guardar como coluna é dar status de dado a um rascunho. |
| `TESE PRINCIPAL` (PRE) | 0/797 | Vazio em 100%. Campo que ninguém preencheu não ganha lugar na tela. |
| `CADASTRADO POR`, `ULTIMA ALTERACAO POR`, `ULTIMA ALTERACAO EM` (TESTEMUNHAS) | 0/424 | Previstos para o Formulário Interno Único, que ainda não está em uso. |
| `origem_comercial_tabela_id` (TESTEMUNHAS) | 0/424 | Vazio em 100%. |
| `MOTIVO` (PROCESSUAL 1, CÓPIA 4) | 5 | Sem função clara; um deles diz "SEM TESTEMUNHA". |
| `PROCESSUAL copy` (PÓS) | 436 | Link legado para a CÓPIA. A ligação útil é a do número CNJ. |
| `Created By` (PROCESSUAL 2.652, CÓPIA 3.722, TESTEMUNHAS 424) | 6.798 | Na PROCESSUAL é `lastModifiedTime` com nome errado; nas outras é colaborador (id, e-mail, nome). Quem criou o registro no Airtable não é dado do processo. |
| `ENVIAR MENSAGEM` (botão, 4 tabelas) e `LINK DA TESTEMUNHA` | 7.595 + 424 | URL montada a partir dos outros campos: se recalcula, não se guarda. |
| links inversos e contadores (`QTD *`, `VINCULADOS *`, `rec_id`, `TEMP_RECORD_ID`, `PROCESSUAL copy` em FUNCIONARIOS/EMPRESAS) | — | O lado inverso de uma FK e o COUNT sobre ela. Número na tela sai de consulta. |
| `SITU. EMPRESA` (lookup, PROCESSUAL 1.804, CÓPIA 2.665) e `EMPRESA PROCESSADA` (PRE, 784) | 5.253 | Lookup do STATUS EMPRESA / nome da reclamada: é JOIN. |
| opções poluidas sem tradução obvia | 45 + 26 | `SIM `, `NAO `, `EXECUCAO`, `RECURSAL` em STATUS EXECUÇÃO (45 processos); 26 RESCISAO em texto livre sem modalidade. Cada uma abre `conferencias`. Os 7 números de processo digitados como TURMA na PROCESSUAL nunca vencem a CÓPIA na carga real: 0 conferências. |
| `STATUS RECEBIMENTO` (PÓS, 80) | 80 | Derivado de `recebimentos`; `STATUS REPASSE`, `EVENTOS` e `DATA DE ASSINATURA` do PÓS estão vazios em 100%. |
| `INAPLICAVEL` (CÓPIA, 3 processos) | 3 | Não são processos trabalhistas nossos: entram com conferência `FORA_DO_ESCOPO` e não viram `processos`. |

## O que e **derivado** (não se grava) e de onde sai

| campo da origem | de onde o sistema tira |
|---|---|
| `PRESCREVE`, `prescricao proxima`, `AVISOS` (o farol) | `v_pre_processual_atrasado`: data de demissão + 2 anos, e dias desde a assinatura |
| `URGENCIA` (RI, PRESCRIÇÃO, URGENCIA ALTA) | `clientes.rescisao_modalidade` e a conta da prescrição |
| `STATUS DOCUMENTACAO` | contagem de `pendencias` tipo DOCUMENTO em aberto |
| `STATUS DO PROCESSO` = AGUARDANDO AUDIÊNCIA / SENTENÇA / ACORDÃO | `audiencias` futura, instrução encerrada sem `decisoes`, fase RECURSAL sem acordao |
| `STATUS RECURSAL` (TST, AGUARDANDO JULGAMENTO) | `recursos` pendente, pelo grau |
| `STATUS PAGAMENTO`, `STATUS RECEBIMENTO` | `acordo_parcelas` + `recebimentos` |
| `STATUS REPASSE` | `repasses` |
| `QTD *`, `VINCULADOS *`, `SITU. EMPRESA`, `EMPRESA PROCESSADA` | COUNT e JOIN. Número na tela sai de consulta, nunca escrito no template |
| `LINK DA TESTEMUNHA`, `ENVIAR MENSAGEM` | URL montada na hora a partir do record |

## O que depende do Lucas

As linhas marcadas `[CONFIRMAR ...]` acima. As que mudam **dado gravado** (e não só a tela):

1. **`ACAO` x `DISTRIBUICAO`** — são a mesma data? Hoje entram em colunas diferentes
   (`ajuizamento_em` e `distribuicao_em`); se forem a mesma coisa, uma some.
2. **`REVOGACAO`, os dois sentidos** (pergunta 20) — a migração decide pelo STATUS DO PROCESSO:
   em processo ROUBADO e o cliente que nos revogou (vai para `incidentes`); nos demais somos nos
   que juntamos a revogação do patrono anterior (vai para `processos`). Se a leitura for outra,
   529 + 839 registros mudam de lugar.
3. **`PENDENCIAS`: pedido ou falta?** (pergunta 7) — hoje a migração grava cada item marcado como
   pendência ABERTA. Se a marca significava "já recebido", 551 fichas nascem com pendência que
   não existe.
4. **`UNA-RS` = rito sumaríssimo?** (pergunta 17) — se sim, 167 audiências também gravam
   `processos.rito`.
5. **`TRATAMENTO`** em STATUS DOCUMENTAÇÃO (5 registros) — e etapa de trabalho interno? Hoje vira
   a flag `em_tratamento`.
6. **`ARQUIVO TST`** — e a data do arquivamento no TST? A descrição na origem e cópia errada da
   de outro campo.
7. **`TURMA` = "11"** (1 processo da PROCESSUAL) — é a 11ª Turma do TRT-2? Hoje fica NULL com
   conferência aberta; se for, vira `11ª TURMA`.
8. **`RESCISAO` = "DEMISSÃO"** sozinho (9 fichas) — sem justa causa, a pedido? Hoje fica sem
   modalidade, com conferência; a prescrição e a urgência RI dependem disso.

## O histórico da carga tem data — e nunca a da carga

`historico_etapas` recebe, para cada entidade migrada, uma linha `origem = MIGRACAO` cuja data
`em` é a MELHOR que a origem oferece para a etapa ATUAL (`Migracao.quando`), com o campo de
onde saiu escrito no `motivo`:

| entidade / etapa | candidatos, na ordem |
|---|---|
| cliente em LEAD, DOCUMENTACAO, ENTREVISTA | DATA DE ASSINATURA |
| cliente em PETICAO_* e DISTRIBUIDO | DISTRIBUIÇAO do processo dele (só DISTRIBUIDO), DATA ENTREVISTA, DATA DE ASSINATURA |
| cliente cancelado, prescrito, stand by, sem resposta | (a origem não diz quando) |
| ficha criada dos autos | DISTRIBUIÇAO, AÇÃO, ASSINATURA |
| processo em CONHECIMENTO | DISTRIBUIÇAO, AÇÃO |
| RECURSAL, EXECUCAO_PROVISORIA | DATA SENTENCA, DISTRIBUIÇAO, AÇÃO |
| EXECUCAO_DEFINITIVA | DATA ACORDAO, DATA SENTENCA, DISTRIBUIÇAO, AÇÃO |
| ACORDO / RECEBENDO | DATA DO ACORDO, (DATA ACORDAO), DATA SENTENCA, DISTRIBUIÇAO, AÇÃO |
| ENCERRADO, DESISTENCIA | ENCERRAMENTO, ARQUIVO TST, DATA ACORDAO, DATA SENTENCA, DATA DO ACORDO, DISTRIBUIÇAO, AÇÃO |
| SOBRESTADO | ULTIMA MOV, DATA ACORDAO, DATA SENTENCA, DISTRIBUIÇAO, AÇÃO |
| audiência REALIZADA / NAO_REALIZADA | DATA AUDIENCIA |
| audiência DESIGNADA | (a designação não tem data na origem) |
| incidente | DATA REVOG, quando é do incidente |

Sem candidato válido (entre 1990 e a data em que a origem foi lida), vale o `createdTime` do
registro no Airtable, e o motivo diz isso. A data da carga nunca entra — foi ela que zerou o SLA
de 10.183 registros. `conferir.py` prova: nenhuma linha datada da carga, e o histórico dos
processos por ano bate com a regra recalculada da origem.

## O que a carga não inventa (regra 3)

Campo cuja data a origem não tem fica NULL; o fato vai para onde cabe:

| fato | onde fica | o que a carga anterior fazia |
|---|---|---|
| cálculo homologado | `processos.situacao_execucao = HOMOLOGADO` + `calculos.observacao` | `homologado_em = ENCERRAMENTO` (411) |
| notificação redigida/enviada/recebida/respondida | `incidentes.situacao` + `airtable_bruto` | as datas = DATA REVOG ou ENCERRAMENTO (72) |
| cliente avisado | `incidentes.airtable_bruto` | `cliente_avisado_em = ENCERRAMENTO` |
| trânsito em julgado | fase EXECUCAO_DEFINITIVA + anotação `[CONFIRMAR: data do trânsito]` (25) | `transito_em = DATA SENTENCA` |
| pasta arquivada | `processos.arquivado = true` (37) | `arquivado_em = encerrado_em` |
| testemunha confirmada | `testemunhas.situacao = CONFIRMADA` | `confirmada_em = DATA ULTIMO CONTATO` (180) |
| cobranças da testemunha | só a última leva DATA ULTIMO CONTATO | todas com a mesma data |
| crédito cedido | `processos.credito_cedido = true` (3) | nada (de/para prometia data) |
| acordo quebrado | `acordos.situacao = QUEBRADO` (4) | nada (de/para prometia `quebrado_em`) |

