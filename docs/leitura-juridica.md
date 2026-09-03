# Leitura jurídica da base — como o escritório trabalha, inferido dos dados

> Escritório trabalhista **pelo reclamante** (empregado). Base lida por inteiro em 03/09/2026: 797
> pré-processuais, 2.652 processos na PROCESSUAL, 3.722 na CÓPIA, 556 pós, 424 testemunhas, 1.103
> empresas, 1.067 "faltantes", 72 pessoas da equipe. Tudo o que está abaixo foi **inferido de campos,
> opções, views e automações**; o que não dá para provar está marcado `[CONFIRMAR: …]` e repetido em
> `perguntas-para-lucas.md`. Nenhum dado pessoal de cliente aparece aqui.

## 0. O desenho em uma frase

A pessoa entra como **PRÉ PROCESSUAL** quando assina o contrato (DATA DE ASSINATURA preenchida em 787/797),
percorre documentação → entrevista → petição inicial, e no dia em que a petição é **distribuída** e alguém marca
**PASSAR DE FASE?** nasce um registro **PROCESSUAL**. O processo anda por FASE PROCESSUAL (conhecimento →
recursal → execução provisória/definitiva → acordo/recebendo → encerrado) com um "status" por fase, e quando
encerra ou arquiva nasce um **PÓS PROCESSUAL** para o dinheiro e o arquivo. Ao lado: **EMPRESAS** (as
reclamadas), **TESTEMUNHAS**, **FUNCIONARIOS** (quem faz o quê), **FRAGILIDADES** (teses por empresa) e duas
tabelas de saneamento do passivo — **Conferência de Faltantes** e a **CÓPIA DA PROCESSUAL**.

Geografia: 89% dos processos são do **TRT-2 (Grande São Paulo)**, com as varas de Diadema em destaque; depois
TRT-15 (Campinas) e TRT-1 (RJ). O acervo vai de 2015 a 2026, com pico de distribuições em 2024 (522 na
PROCESSUAL, 607 na CÓPIA).

## 1. Três tabelas = três fases; e a mesma pessoa em três lugares

| Tabela | é | chave natural | dono da fase |
|---|---|---|---|
| PRE PROCESSUAL | a **pessoa/caso** antes de virar processo | nome + CPF | Documentação, Entrevistador, Responsável Inicial, Jurídico |
| PROCESSUAL | o **processo** | Nº PROCESSO (CNJ) | Advogado |
| PÓS PROCESSUAL | o **dinheiro e o arquivo** do processo | N° DO PROCESSO | Responsável (= advogado) |

Não há tabela de **cliente**: NOME, TELEFONE, CPF e NASCIMENTO estão repetidos na PRÉ e na PROCESSUAL (e
divergem: 260 nomes, 653 telefones e 1.291 nascimentos diferentes entre PROCESSUAL e CÓPIA para o mesmo
processo). Uma pessoa com dois processos é dois registros sem nada que os ligue além do nome. O script de
aniversário faz deduplicação por telefone justamente por isso. **Para o portal: cliente vira entidade**, o
processo aponta para ela, e a PRÉ vira a etapa inicial da mesma ficha (como no previdenciário: lead = mesma
ficha na etapa LEAD).

## 2. Captação

- **CAPTADOR** (link FUNCIONARIOS, 791/797): quem trouxe a pessoa. Há 20 captadores cadastrados, 10 ativos;
  os quatro maiores respondem por ~70% dos pré-processuais. É **atributo** (não muda) e é base de comissão
  [CONFIRMAR: a comissão do captador é calculada em algum lugar? não há campo de comissão].
- **RESPONSAVEL INICIAL** (597/797): quem cuida da pessoa no pré-processual. O dashboard conta casos por
  responsável inicial — é o "dono do atendimento" [CONFIRMAR].
- **FONTE** (77/797, só a partir de jun/2026): canal/campanha. Mistura canal (Site, Instagram, Indicação) com
  campanha ("PROJETO PUXADA", "DISP LAILLA" = disparo de WhatsApp). Precisa virar dois campos: canal e campanha.
- **DATA DE ASSINATURA**: a **assinatura do contrato de honorários e procuração** — está em 99% dos registros,
  então a pessoa só entra na base **depois** de assinar. Não há etapa de "lead que ainda não assinou"
  [CONFIRMAR: os leads não assinados ficam onde? no WhatsApp/Lailla?]. Ritmo: ~80–150 assinaturas/mês em 2026.
- **EMPRESA** (784/797): a reclamada, já ligada na captação. **FUNCAO**: o cargo do trabalhador (eletricista,
  motorista, atendente…) — texto livre, dá o perfil da carteira (transporte, energia, saúde, limpeza).
- **SLA de 15/20 dias** desde a assinatura (automações 🟡/🔴 em AVISOS): o escritório espera **distribuir em até
  15–20 dias da assinatura**. 166 registros levaram o 🔴 [CONFIRMAR: o prazo é mesmo 20 dias? e a partir da
  assinatura, não da documentação completa?].

## 3. Entrevista

- **STATUS ENTREVISTA**: opções previstas PENDENTE → PRIMEIRO/SEGUNDO/TERCEIRO CONTATO → ENTREVISTA AGENDADA
  → (REMARCAR) → ENTREVISTA-OK, com saídas STAND-BY, SEM RESPOSTA, DESISTÊNCIA. Na prática só ENTREVISTA-OK
  (448) e DESISTÊNCIA (113) são usados; os contatos intermediários quase nunca. É **etapa**.
- **ENTREVISTADOR** (link, 431), **DATA ENTREVISTA** (397, ~100/mês em jun–jul/2026), **RESUMO ENTREVISTA**
  (51 — o conteúdo da entrevista **não fica no Airtable**; provavelmente no Drive [CONFIRMAR]).
- **PERICIA MEDICA / PERICIA INSALUB/PERIC** (checkboxes, 0% preenchidos): a entrevista deveria marcar se o
  caso vai precisar de perícia médica (doença/acidente) ou de insalubridade/periculosidade — ninguém marca.
- A entrevista é presencial? O campo é dateTime e há "compromisso" no tipo de disparo do WhatsApp
  [CONFIRMAR: presencial, vídeo ou telefone].

## 4. Documentação

- **STATUS DOCUMENTAÇÃO**: PENDENTE → AGUARDANDO → PARCIAL → TRATAMENTO → COMPLETA, saída DESISTÊNCIA.
  Etapa. COMPLETA em 555. `TRATAMENTO` [CONFIRMAR: significa "documento em análise/organização"?].
- **PENDENCIAS** (multi): CNH/RG, CTPS, TRCT, DOCS. MÉDICOS, PROVAS, FGTS, HOLERITES, PIS. É a **lista de
  documentos do caso trabalhista**: TRCT (termo de rescisão), holerites, extrato do FGTS, CTPS, documentos
  médicos, provas (fotos, conversas, escalas). **Ambiguidade**: 172 fichas COMPLETA têm 4 itens marcados —
  ou o campo lista o que foi *pedido* e não o que *falta*, ou ninguém desmarca ao receber
  [CONFIRMAR: PENDENCIAS = o que falta ou o que foi solicitado?].
- **DRIVE** (795/797): a pasta do cliente. **ASTREA** (536): link no Astrea, sistema jurídico usado antes/em
  paralelo [CONFIRMAR: o Astrea continua sendo a fonte de prazos e publicações?].

## 5. Prescrição (o relógio do pré-processual)

- **DEMISSAO** (texto, 616/797): data da saída. **PRESCREVE** = DEMISSAO + 2 anos (fórmula): é a **prescrição
  bienal** do art. 7º, XXIX, da CF e art. 11 da CLT — o trabalhador tem **2 anos após o fim do contrato** para
  ajuizar, e quando ajuíza só alcança os **5 anos anteriores** (quinquenal). A base controla só a bienal, que é
  a que mata o caso.
- **prescrição próxima** = 🔴 se vence em ≤ 30 dias (49 hoje). Em 03/09/2026, **156 pré-processuais já
  passaram da data** (a maioria CONCLUÍDO — já distribuído, então o campo perdeu função) e 460 têm data futura.
- **URGENCIA = PRESCRIÇÃO** (130) e **STATUS_NOTIFICACAO_PRESCRICAO** (AVISO ENVIADO 29, VENCIDO NOTIFICADO
  16): o n8n avisa alguém quando está perto e quando venceu. Quem recebe [CONFIRMAR].
- Fragilidade: DEMISSAO em 6 formatos de texto; a fórmula quebra com hífen. Quem pede **rescisão indireta**
  não tem demissão — o contrato está vivo — então PRESCREVE fica vazio e o caso sai do radar da prescrição
  (correto juridicamente, mas o relógio dele é outro: ver §6).
- **RESCISAO** (texto, 666): a **modalidade de rescisão** — SEM JUSTA CAUSA (325 em várias grafias), RESCISÃO
  INDIRETA (100), PEDIDO DE DEMISSÃO (81), JUSTA CAUSA (40), "CONTRATO EM ABERTO" (2). É **atributo** do caso
  e muda os pedidos possíveis (aviso, multa de 40%, seguro-desemprego). Devia ser select.

## 6. Rescisão indireta (URGENCIA RI)

O empregado ainda está trabalhando e quer que a Justiça reconheça falta grave do empregador (art. 483 CLT).
Enquanto a ação não sai, ele continua exposto — por isso RESCISAO contendo "RESCISÃO INDIRETA" dispara
`URGENCIA = RI + URGENCIA ALTA` e o n8n cobra em **5, 10, 12 e 15 dias** (`STATUS_NOTIFICACAO_RI`: 45 já
chegaram ao "15D ENVIADO"). Ou seja, **a RI tem SLA próprio de 15 dias para distribuir** [CONFIRMAR: cobrar
quem — o advogado que redige? e o que acontece no 15º dia?]. 84 casos marcados RI.

## 7. Petição inicial

- **STATUS PETICAO INICIAL**: PENDENTE (41) → EM CRIAÇÃO (6) → AGUARDANDO APROVAÇÃO (54) → APROVADA (5) →
  DISTRIBUIDA (486); saídas DESISTENCIA (100) e PRESCRITO (2); `VALIDAÇÃO` prevista e nunca usada. É a
  etapa mais bem desenhada da base: tem **redação**, **aprovação** (por um sênior/sócio [CONFIRMAR quem
  aprova]) e **distribuição**. Gargalo visível: 54 aguardando aprovação contra 6 em criação.
- **ETAPA PRE PROCESSUAL** é a etapa-mãe: DOCUMENTAÇÃO (19) → ENTREVISTA (42) → PETIÇÃO INICIAL (147) →
  CONCLUÍDO (452); CANCELAMENTO (137) é a saída. Ninguém a preenche por automação exceto o CANCELAMENTO —
  é mão humana, e por isso há 40 registros em PETIÇÃO INICIAL com petição já DISTRIBUIDA (esqueceram de
  avançar) e 3 CONCLUÍDOS com petição só APROVADA.
- **TESTEMUNHAS** (link, 120): as testemunhas já são arroladas no pré-processual.
- **TESE PRINCIPAL**: 0/797. A matéria do caso não é registrada em lugar nenhum
  [CONFIRMAR: querem catálogo de teses? FRAGILIDADES sugere que sim].

## 8. A passagem PRÉ → PROCESSUAL

Automação nº 1: ETAPA ∈ {PETIÇÃO INICIAL, CONCLUÍDO} **e** PASSAR DE FASE? **e** STATUS PETICAO = DISTRIBUIDA
→ cria o processo copiando nome, telefone, empresa, captador, Drive, Astrea e perícias, e liga as duas
fichas. **Perde**: CPF, nascimento, assinatura, entrevistador, responsável inicial, testemunhas, resumo,
rescisão/demissão. O processo nasce **sem número, sem fase e sem status** — o número é digitado depois à mão
(106 processos ainda sem) e a FASE é deduzida pelo script quando alguém preenche a DISTRIBUIÇAO.
431 dos 797 PRÉs têm processo ligado; 444 processos apontam para um PRÉ. Os outros ~2.200 processos são o
**passivo**: entraram pelo formulário "Cadastro de Cliente - Processo Trabalhista" ou por importação
(Created em mai–jun/2026, quando a base V3 nasceu).

## 9. PROCESSUAL — três camadas de estado

A PROCESSUAL tem **uma fase macro**, **um status geral** e **um status por fase**. Isso é o que mais importa
para o desenho:

| camada | campo | opções | preenchido |
|---|---|---|---|
| fase macro (etapa) | FASE PROCESSUAL | CONHECIMENTO 1.343 · ENCERRADO 478 · RECURSAL 227 · EXECUÇÃO PROVISÓRIA 140 · EXECUÇÃO 125 · ACORDO 119 · EXECUÇÃO DEFINITIVA 74 · DESISTENCIA 28 · RECEBENDO 2 · vazio 116 | 96% |
| situação (mistura de etapa e evento) | STATUS DO PROCESSO | AGUARDANDO AUDIÊNCIA 469 · ARQUIVADO 444 · EXECUCAO 287 · ACORDO 78 · ROUBADO 66 · RECEBIDO POR ELES 38 · TRÂNSITO EM JULGADO 35 · AGUARDANDO SENTENÇA 28 · DESISTENCIA 27 · RECUPERADO 18 · SOBRESTADO 11 · REDISTRIBUIR 1 · **vazio 1.150** | 57% |
| status do conhecimento | STATUS CONHECIMENTO | AGUARDANDO AUDIÊNCIA → ADVIDEO → AGUARDANDO PERICIA → AGUARDANDO SENTENÇA → SENTENCIADA; saídas ACORDO EM ANDAMENTO, AUSÊNCIA, DESISTÊNCIA | 44% |
| status recursal | STATUS RECURSAL | AGUARDANDO JULGAMENTO (no TRT) → TST | 9% |
| status da execução | STATUS EXECUÇÃO | ver §12 | 23% |
| status do cumprimento provisório | STATUS CumPrSe | AGUARDANDO SENTENÇA → DECISÃO POSITIVA 1ª/2ª → PERICIA CONTÁBIL → FASE DE CÁLCULOS → RECEBIDO; ACORDO, SOBRESTADO | 1% |
| status do cálculo | STATUS DO CALCULO | PENDENTE → JUNTADO AOS AUTOS → HOMOLOGADO | 8% |
| status do acordo | STATUS ACORDO | ACORDO EM ANDAMENTO → ACORDO CUMPRIDO / QUEBRA DE ACORDO | 5% |
| status do pagamento | STATUS PAGAMENTO | PENDENTE → AGUARDANDO PAGAMENTO → PAGAMENTO EM DIA / ATRASADO / PAGO PARCIALMENTE / PARCELAMENTO CPC → CONCLUIDO; CESSAO DE CREDITOS | 9% |

**Leitura**: STATUS DO PROCESSO **não é uma máquina de estados** — mistura etapa (EXECUCAO, TRÂNSITO EM
JULGADO), espera (AGUARDANDO AUDIÊNCIA/SENTENÇA), saída (ARQUIVADO, DESISTENCIA) e **situação do cliente**
(ROUBADO, RECUPERADO, RECEBIDO POR ELES, REDISTRIBUIR, SOBRESTADO). O script de autopreenchimento trata esses
cinco últimos como "protegidos" — são decisão humana. O portal deve separar: **etapa** (FASE), **próximo
evento** (audiência/perícia/sentença), **incidentes** (roubado, sobrestado, redistribuir) e **saídas**.

A FASE também **não é confiável no acervo antigo**: para 757 processos que a PROCESSUAL diz CONHECIMENTO, a
CÓPIA diz ENCERRADO com data de encerramento (2023–2025 na maioria). A PROCESSUAL reflete o que a equipe
mexe; a CÓPIA reflete o que o pipeline leu dos autos. Ver §17.

## 10. Fase de conhecimento

- **DISTRIBUIÇAO** (data, 100%): quando a inicial foi protocolada/distribuída. **VARA** (texto, 74%),
  **TRT** (select), **TEL VARA**. **AÇÃO** (data, 7%) [CONFIRMAR: o que é — data do ajuizamento? do fato?].
- **CLASSIFICACAO**: o **rito**. `RT - ORDINÁRIO` = Reclamação Trabalhista (classe antiga do PJe, casos até
  ~2020); `AT - ORDINÁRIO` / `AT - SUMARÍSSIMO` / `AT - SUMÁRIO` = Ação Trabalhista (classe atual), no rito
  ordinário, sumaríssimo (até 40 salários mínimos, art. 852-A CLT — audiência una, sentença rápida, sem
  recurso de revista salvo violação constitucional) ou sumário (até 2 SM, art. 2º Lei 5.584/70 — não usado).
  Na CÓPIA a lista ganhou classes de **incidente/recurso** (EXECUCAO PROVISORIA, EXECUCAO DEFINITIVA, EMBARGOS DE
  TERCEIRO, RR, AIRR, RRAg, Emb) — outra natureza, misturada no mesmo campo. É **atributo**. 43% vazio.
- **VALOR** (97%): valor da causa (estimativa dos pedidos; média ~R$ 200 mil, mediana R$ 143 mil). Define o
  rito e a **COMPLEXIDADE** A/B/C (script: C ≤ 150 mil, B ≤ 500 mil, A > 500 mil). Complexidade é
  **atributo derivado** — hoje 99,6% coerente com o valor. [CONFIRMAR: A/B/C muda quem cuida do caso ou só
  o relatório?].
- **AUDIENCIA** + **DATA AUDIENCIA**: o tipo da próxima/última audiência — INICIAL (conciliação e defesa),
  INSTRUÇÃO (prova oral), UNA (tudo numa só; padrão no sumaríssimo e comum no TRT-2: 430 de 634), HOMOLOGAÇÃO
  (de acordo). Na CÓPIA aparecem as variantes `/VIDEO` (telepresencial), `UNA-RS` [CONFIRMAR: RS = rito
  sumaríssimo?], `CONCILIAÇÃO EM EXECUÇÃO`, `JULGAMENTO`. A base guarda **uma** audiência por processo — a
  anterior é sobrescrita. Hoje 186 audiências futuras (72 em setembro).
- **ADVIDEO** (DATA/RESP/STATUS ADVIDEO — FEITO/PENDENTE/MARCADO, view "AD VIDEOS"): um evento anterior à
  audiência, com responsável, que o script trata como prioridade 1 na agenda. Está **vazio** na base.
  [CONFIRMAR: "ad video" é a reunião de preparação do cliente/testemunhas por vídeo antes da audiência? quem faz?]
- **Perícias**: PERICIA MEDICA (doença ocupacional/acidente — nexo e incapacidade) e PERICIA TECNICA
  (insalubridade/periculosidade — adicionais). Checkbox + data. Quase vazias (7 e 11).
- **TESTEMUNHAS** (link, 239): as arroladas neste processo.
- **Sentença**: **DECISAO SENTENCA** (objetiva: PROCEDENTE 14 · PARCIALMENTE PROCEDENTE 384 · IMPROCEDENTE
  81; na CÓPIA também EXTINTO S/ RESOLUÇÃO DO MÉRITO 383), **SENTENCA** (nota do escritório: RUIM 250 · MÉDIA
  169 · ÓTIMA 95 — subjetiva, mede o resultado contra o pedido), **ULTIMA DECISAO** (mistura nota e
  resultado; é "a última decisão relevante", sentença ou acórdão). Na CÓPIA: **DATA SENTENCA** e
  **MAGISTRADO** (2.067 e 1.999 — extraídos dos autos; o MAGISTRADO é quem assinou a decisão terminativa,
  em ~45% o homologador do acordo). "Parcialmente procedente" é a regra (80%) — é assim que o trabalhista
  funciona: pedidos em cascata, ganha-se parte.
- **AUSÊNCIA** (STATUS CONHECIMENTO): o reclamante faltou à audiência → arquivamento (art. 844 CLT) e
  pagamento de custas se não justificar; a CÓPIA tem 126 e uma view "Ausencias". É perda evitável — vale
  medir por captador/entrevistador.

## 11. Fase recursal

- **STATUS RECURSAL**: AGUARDANDO JULGAMENTO (recurso ordinário no TRT) → TST (recurso de revista / agravo).
  Só dois estados; a CÓPIA tem 1.225 preenchidos contra 245 na PROCESSUAL.
- **TURMA** (a turma do TRT-2 que julgou; na PROCESSUAL é select poluído com 41 opções, na CÓPIA é texto
  limpo), **CADEIRA** e **RELATOR** (só na CÓPIA: desembargador relator e sua cadeira), **DATA ACORDAO**,
  **RESULTADO ACORDAO** (nota RUIM/MÉDIO/ÓTIMO) e, só na CÓPIA, **RESULTADO RECURSO** (objetivo: PROVIDO
  79 · PARCIALMENTE PROVIDO 527 · NEGADO PROVIMENTO 504 · NÃO CONHECIDO 134 — "provido" para quem? o campo
  não diz se o recurso era nosso ou da reclamada [CONFIRMAR]).
- **TST**: TURMA TST, RELATOR TST, ARQUIVO TST (só na CÓPIA, vindos de uma "Planilha Correspondente TST"
  — o escritório tem correspondente em Brasília [CONFIRMAR]).
- STATUS DO PROCESSO = **AGUARDANDO ACORDAO** (129 na CÓPIA, inexistente na PROCESSUAL) e **SOBRESTADO**
  (11/12: processo suspenso aguardando tema repetitivo/IRR ou outro processo).
- Enquanto o recurso corre, o reclamante pode pedir **execução provisória** (§12) — por isso 77 processos
  estão em EXECUÇÃO PROVISÓRIA na PROCESSUAL e RECURSAL na CÓPIA: as duas coisas ao mesmo tempo.

## 12. Execução

Duas portas de entrada:
- **Provisória** (antes do trânsito, art. 899 CLT / 520 CPC): abre-se um incidente com número próprio —
  **Nº CumPrSe** (Cumprimento Provisório de Sentença, classe do PJe; 326 preenchidos) e **STATUS CumPrSe**.
  Serve para adiantar cálculo e penhora enquanto a reclamada recorre.
- **Definitiva** (após o trânsito em julgado): FASE = EXECUÇÃO DEFINITIVA, que o script deduz de STATUS =
  TRÂNSITO EM JULGADO + decisão (parcialmente) procedente.
- `EXECUÇÃO` sem qualificação (125) é o que o script põe quando entra cálculo/quebra de acordo sem saber qual.

Dentro da execução, o caminho que os campos descrevem:

1. **AGUARDANDO TRANSITO** → **AGUARDANDO CÁLCULO** (237 — o maior grupo: sentença liquidável, ninguém
   apresentou conta) → **FASE DE CÁLCULOS** (as partes apresentam; STATUS DO CALCULO = JUNTADO AOS AUTOS)
   → **AGUARDANDO PERICIA** (contábil, quando divergem) → **HOMOLOGADO** (STATUS DO CALCULO = HOMOLOGADO; o
   juiz fixa o valor).
2. Valores: **CALCULO RCTE** = cálculo apresentado pelo **reclamante** (nós); **CALCULO RCDA** = pela
   **reclamada**; **VALOR HOM** = o **homologado** pelo juiz; **SUCUMB RCTE / RCDA / HOM** = os honorários
   de sucumbência embutidos em cada uma dessas contas (art. 791-A CLT: 5% a 15% — e a base confirma:
   mediana 8% do valor). Na prática **VALOR HOM ≈ CALCULO RCTE** (razão mediana 1,00) e o cálculo do
   reclamante é ~23% maior que o da reclamada. **SUCUMBENCIA %** (texto: 5%, 10%, 15%) é o percentual fixado.
3. **RECURSO EXECUÇÃO** (agravo de petição contra a homologação) · **PROCURANDO BENS** (pesquisa
   patrimonial — Sisbajud, Renajud, Infojud; BENS IDENTIFICADOS SIM/NÃO) · **AUDIÊNCIA CONCILIAÇÃO** /
   **NEGOCIANDO ACORDO** · **PARCELAMENTO 916 CPC** (executado deposita 30% e parcela o resto em até 6
   vezes) · **AGUARDANDO ALVARÁ** (o dinheiro está depositado, falta o juiz liberar) · **RECEBIDO** ·
   saídas **ARQUIVADO**, **EXTINTA S/ RESOLUÇÃO**, **SOBRESTADO**, **EXECUÇAO PROVISÓRIA**.
4. Atributos da **reclamada** que pesam aqui: SITU. EMPRESA (ATIVA / INATIVA / EM RECUPERACAO — recuperação
   judicial suspende a execução e manda para o juízo universal), HIST. PAGAMENTO (BOA/RUIM/PÉSSIMA) e BENS
   IDENTIFICADOS — estão duplicados no processo e na empresa.
5. **AND. NECESSÁRIO** ("andamento necessário") é a **próxima tarefa** da execução: PEDIR ANDAMENTO, EXPEDIÇÃO
   DE ALVARÁ, TENTAR ACORDO, PEDIR AUD CONCILIAÇÃO — virou caderno de recados. No portal é tarefa, não campo.

## 13. Acordo

Pode acontecer em qualquer fase (audiência inicial, instrução, recursal, execução — a CÓPIA tem "CONCILIAÇÃO EM
EXECUÇÃO"). Campos: **STATUS ACORDO** (EM ANDAMENTO → CUMPRIDO / QUEBRA), **VALOR ACORDO**, **PARCELAS**
(moda 2; até 12), **VALOR PARCELA** e **DATA DO ACORDO** (CÓPIA), **HONOR TOTAL ACORDO** (CÓPIA). FASE =
ACORDO enquanto paga; **QUEBRA DE ACORDO** manda para EXECUÇÃO (multa da cláusula penal + execução do saldo).
**STATUS PAGAMENTO** acompanha as parcelas (PAGAMENTO EM DIA / ATRASADO / PAGO PARCIALMENTE / CONCLUIDO;
**CESSAO DE CREDITOS** = o cliente vendeu o crédito a terceiro). Na CÓPIA, 1.317 acordos cumpridos — o acordo
é o **desfecho mais comum** do escritório (1.382 com status, contra 2.118 sentenças de mérito).

## 14. Dinheiro do processo

| campo | o que é | de quem é o dinheiro |
|---|---|---|
| VALOR | valor da causa (pedido) | ninguém — é estimativa |
| CALCULO RCTE / RCDA / VALOR HOM | liquidação: nossa conta, a deles, a do juiz | do cliente (bruto) |
| SUCUMB RCTE / RCDA / HOM | honorários sucumbenciais dentro de cada conta (5–15%) | **do escritório**, pagos pela reclamada |
| VALOR ACORDO | o acordo fechado | do cliente (bruto) |
| TOTAL RECEBIDO | o que **efetivamente entrou** no processo (acordo ou execução) | bruto; base do honorário |
| SUCUMB RECEBIDO | sucumbência efetivamente recebida | do escritório |
| HONOR TOTAL | **honorários contratuais** do escritório | do escritório, descontados do cliente |
| HONOR TOTAL ACORDO / HOMOL / CALCULO RCTE / RCDA (CÓPIA) | o honorário contratual **projetado** em cada cenário | simulação |

A razão HONOR TOTAL / TOTAL RECEBIDO é **exatamente 30% em metade dos casos** (603 de 687 acordos) e varia de
33% a 41% no restante — ou o contrato prevê 30% e sobe em cenários específicos, ou há mais de um modelo de
contrato [CONFIRMAR: percentual contratual padrão e quando muda]. Sucumbência **não** entra no HONOR TOTAL
(é campo separado). O **repasse ao cliente** (TOTAL RECEBIDO − HONOR TOTAL) não existe como campo e o STATUS
REPASSE do PÓS está vazio em 100% — **o escritório não registra quando pagou o cliente**
[CONFIRMAR: onde isso é controlado — planilha/financeiro?]. Qualidade: 15 acordos têm TOTAL RECEBIDO = 50×
VALOR ACORDO (erro de digitação em milhar/centavo).

## 15. Encerramento e pós-processual

- **ENCERRAMENTO** (data) → script põe FASE = ENCERRADO → automação cria o **PÓS PROCESSUAL** com N° DO
  PROCESSO, RESULTADO FINAL, VALOR RECEBIDO CLIENTE, VALOR HONORARIOS, VALOR SUCUMBENCIA e STATUS
  RECEBIMENTO copiados naquele instante. O PÓS tem STATUS RECEBIMENTO (14% preenchido), STATUS REPASSE (0%),
  STATUS ARQUIVAMENTO (Arquivado 37 / Em andamento 30), RESPONSAVEL (38%). É uma tabela **quase vazia**: o
  pós-processual está desenhado e não é praticado no Airtable — 99 dos 556 PÓS não apontam para processo nenhum.
- **ARQUIVADO** (STATUS DO PROCESSO, 444) é o arquivamento judicial (definitivo) — diferente de ENCERRADO
  (fase interna) e do STATUS ARQUIVAMENTO do PÓS (arquivo físico/Drive) [CONFIRMAR as três].

## 16. Casos laterais

- **ROUBADO** (66) / **RECEBIDO POR ELES** (38) / **RECUPERADO** (18): o cliente **constituiu outro advogado**
  no meio do processo (o "roubo" de cliente, frequente no trabalhista). RECEBIDO POR ELES = o outro
  escritório recebeu o dinheiro; RECUPERADO = o cliente voltou. O tratamento está nos campos:
  **REVOGAÇÃO** (SIM = a procuração nossa foi revogada nos autos; NÃO SE APLICA; recados "juntar
  revogação", "ver se colocaram a revogação acima"), **DATA REVOG**, **NOTIFICAÇÃO** (extrajudicial ao
  cliente cobrando os honorários pelo trabalho feito — REDIGIDA 61, quase todos ROUBADO), **PROVIDENCIAS**
  = "NOTIFICAR" (66) ou "TRAVAR O RECEBIMENTO" / "TRAVAR ULTIMA PARCELA" (pedir ao juízo a reserva dos
  honorários, art. 22, §4º, Lei 8.906/94). **CLIENTE AVISADO?** (9). Views ROUBADOS e RECUPERADOS. É um
  **sub-fluxo próprio**: detectar → revogação nos autos? → notificar → travar recebimento → recuperar ou
  cobrar. Note que REVOGAÇÃO = SIM em 529 processos **normais** (EXECUCAO/ARQUIVADO): ali significa que
  **nós** juntamos revogação do advogado **anterior** do cliente [CONFIRMAR: o mesmo campo tem os dois sentidos?].
- **REDISTRIBUIR** (1): processo a ser redistribuído (nova vara / nova ação após arquivamento).
- **SOBRESTADO** (11): suspenso por decisão superior.
- **DESISTENCIA** (FASE 28 / STATUS 27): o reclamante desistiu depois de ajuizar (homologação de desistência).
- **INAPLICÁVEL** (CÓPIA, 3): registro que não é processo trabalhista nosso.
- **AUSÊNCIA** (§10) e **EXTINTA S/ RESOLUÇÃO** (execução).
- **Conferência de Faltantes** (1.067, criada em 15/06/2026): processos do escritório encontrados no
  **Datajud** (e/ou no Drive) que não estavam na PROCESSUAL, com FASE/STATUS recomendados pela API pública do
  CNJ (CONHECIMENTO 446, EXECUÇÃO 326, ENCERRADO 73…) e último movimento ("Definitivo" = baixa definitiva
  em 641 — a maioria já acabou). Glauco deveria conferir e marcar "VALIDAR E SUBIR", mas **0 marcados e
  a automação prometida não existe**. Hoje 450 desses números já estão na PROCESSUAL e 986 na CÓPIA — a
  tabela ficou para trás; só **78 não estão em lugar nenhum**.

## 17. Qual PROCESSUAL é a fonte para a migração

Fatos (números de processo normalizados só com dígitos):

| | PROCESSUAL | CÓPIA |
|---|---|---|
| registros | 2.652 | 3.722 |
| números distintos | 2.538 (106 sem número, 8 duplicados) | 3.703 (0 sem número, 19 duplicados) |
| só nela | 22 números (criados mai–set/2026) + os 106 sem número | **1.187 números** |
| criação | mai 922 · jun 1.495 · jul 119 · ago 114 · set 2 | mai 794 · jun 1.898 · **ago 1.030** |
| quem criou | (campo "Created By" é lastModifiedTime) | Pedro 2.855 · Glauco 603 · Automations 200 · gerência 64 |
| FASE | CONHECIMENTO 51% · ENCERRADO 18% | **ENCERRADO 68%** · CONHECIMENTO 15% · RECURSAL 13% |
| ENCERRAMENTO | 15% | **71%** |
| DECISAO SENTENCA | 18% | **57%** |
| STATUS DO PROCESSO | 57% | **100%** |
| ASSINATURA | 4% | **58%** |
| campos só dela | — | DATA SENTENCA, MAGISTRADO, RESULTADO RECURSO, CPF (97%), E-MAIL (58%), CNPJ RECLAMADA (91%), CADEIRA, RELATOR, TURMA/RELATOR/ARQUIVO TST, HONOR TOTAL por base, VALOR PARCELA, DATA DO ACORDO |
| automações que a escrevem | PRÉ→PROC, PROC→PÓS, AUTOPREENCHIMENTO | COMPLEXIDADE POR VALOR |
| links vivos | PRE PROCESSUAL, TESTEMUNHAS, POS | POS (PRE e TESTEMUNHAS viraram texto) |

Os **1.187 processos só da CÓPIA**: 1.040 ENCERRADOS, com ENCERRAMENTO em 1.048, distribuídos sobretudo em
2017–2021 e 2025; 539 deles também estão na Conferência de Faltantes; criados em jun (631) e ago (540) de
2026. **São o passivo histórico** que alguém (Pedro/Glauco) carregou na cópia — em vez da PROCESSUAL — para o
pipeline de leitura dos autos enriquecer. Por isso a cópia tem 3.722.

**Conclusão**: a **CÓPIA é a fonte mais completa** (acervo inteiro + campos do pipeline + fase atualizada
pela leitura dos autos) e deve ser a **base da migração**; a **PROCESSUAL é a fonte do que está vivo**: os 22
+ 106 recentes, os links com PRÉ/TESTEMUNHAS/PÓS, e alguns campos preenchidos só nela para o mesmo processo
(DATA REVOG 509, SITU. EMPRESA 212, Nº CumPrSe 131, VALOR HOM 127, SUCUMB RECEBIDO 67, STATUS EXECUÇÃO 59,
TESTEMUNHAS 31). A migração deve **casar pelo número CNJ**, preferir a CÓPIA campo a campo e completar com a
PROCESSUAL onde a CÓPIA está vazia — e resolver as 1.403 divergências de FASE registrando as duas
[CONFIRMAR: a FASE da CÓPIA (lida dos autos) vale mais que a da PROCESSUAL (mão da equipe)?]. Nome, VARA,
NASCIMENTO e TELEFONE divergem em centenas — escolher a CÓPIA e guardar a outra grafia como alias.

## 18. Testemunhas

Entidade própria, com dois canais: **jurídico** (formulário interno, 330) e **comercial** (o captador cadastra,
36, e não é avisado de si mesmo). Campos: VINCULO com o cliente (COLEGA DE TRABALHO 254, EX-COLEGA, GESTOR,
TERCEIRO), EMPRESA, **TEM PROCESSO?** (testemunha que também litiga contra a mesma empresa — a Súmula 357 do
TST diz que isso **não** a torna suspeita, mas a reclamada sempre contradita; por isso se pergunta), **STATUS
TESTEMUNHA** (PENDENTE → A CONFIRMAR → CONFIRMADA; DESCARTADA / NAO USAR), **COBRANÇA** (1º–4º contato),
**DATA ULTIMO CONTATO**, link público para a própria testemunha atualizar dados, e a máquina do n8n para
**avisar o captador** que trouxe a testemunha (`notif_captador_status`) [CONFIRMAR: captador ganha por
testemunha?]. 323 ligadas a processo, 174 a pré-processual. AUDITORIA TESTEMUNHAS é um log append-only do
formulário interno com 2 eventos.

## 19. Empresas e fragilidades

EMPRESAS = as reclamadas (1.103; 655 sem processo ligado na PROCESSUAL, mas 786 ligadas à CÓPIA). Atributos de
**risco de recebimento**: STATUS EMPRESA, HIST. PAGAMENTO, BENS IDENTIFICADOS. **FRAGILIDADES** (17 registros,
uma empresa de transporte coletivo) é o começo de um **banco de teses por reclamada**: achado, eixo (jornada,
ponto, descontos, verbas normativas, FGTS…), força da prova, status nos julgados (inédita / acolhida /
rejeitada), fundamento, prova nos autos, como explorar, documentos a requerer (art. 400 CPC), valor estimado.
É o equivalente ao `teses/*.md` + `jurisprudencia/*.md` do previdenciário, só que por empresa — no trabalhista
a tese repete por **empregador** (mesma CCT, mesmo controle de ponto, mesmos holerites).

## 20. Equipe

FUNCIONARIOS: 72 pessoas, 35 ativas. Papéis (multi): Advogado, Captador, Juridico, Entrevistador, Responsável
Inicial, Gestor, TI, Administrativo, Documentação, Testemunhas, Financeiro, Atendimento, Publicação,
Correspondente. Ativos hoje, por papel: Gestores Glauco (sócio; advogado e captador), Alisson Leal, Diego Barbosa,
Dr. Vitor Esteves · Advogados ativos: Glauco, Alisson, Vitor, Letícia Sheu, Larissa Barbosa, Enzo Bonatto, Graziela
Branda, Correspondente · Jurídico: Amanda Rocha, Dra. Nilse, Emilly, Laiza, Letícia Rodrigues, Samuel ·
Captadores ativos: Diego Lameira, Kayo, Renan, Tiago Garrido, Frank, Erick Santana, Diego Barbosa, Vinicius
Rafael · Entrevistadores: Bruna, Bruno Torres, Cauane, Gabriella Varella, Julia Teixeira, Letícia Sheu ·
Responsáveis iniciais: Bruno Torres, Julia Teixeira, Késia, Maria Varella, Letícia Sheu · Documentação/Adm:
Larissa Batista · Testemunhas: Enzo Oliveira, Juliana Fonseca · TI: Kauê, Samuel, Vinicius · Atendimento:
Rayssa · Publicação: Thifani. **Setor** não existe como campo — sai do papel. [CONFIRMAR organograma e quem
aprova petição.] Cada pessoa tem `ntfy_topic` para push do n8n.

## 21. Etapa × atributo × evento (resumo para o arquiteto)

**Etapas (estado que se percorre; merecem máquina de estados com histórico):**
ETAPA PRE PROCESSUAL · STATUS DOCUMENTAÇÃO · STATUS ENTREVISTA · STATUS PETICAO INICIAL · FASE PROCESSUAL ·
STATUS CONHECIMENTO · STATUS RECURSAL · STATUS EXECUÇÃO (16 estados limpos da CÓPIA) · STATUS CumPrSe · STATUS
DO CALCULO · STATUS ACORDO · STATUS PAGAMENTO · STATUS TESTEMUNHA · notif_captador_status · STATUS RECEBIMENTO
/ REPASSE / ARQUIVAMENTO (PÓS).

**Incidentes/saídas (flags com data e motivo, não etapa):** ROUBADO / RECEBIDO POR ELES / RECUPERADO ·
REVOGAÇÃO + DATA REVOG · NOTIFICAÇÃO · SOBRESTADO · REDISTRIBUIR · DESISTÊNCIA · AUSÊNCIA · PRESCRITO ·
INAPLICÁVEL.

**Atributos (não mudam ou mudam raramente):** CAPTADOR · FONTE · RESCISAO (modalidade) · DEMISSAO · DATA DE
ASSINATURA · EMPRESA · FUNCAO · Nº PROCESSO · DISTRIBUIÇAO · VARA/TRT/TURMA/RELATOR · CLASSIFICACAO (rito) ·
VALOR · COMPLEXIDADE (derivada) · PERICIA MEDICA/TECNICA · DECISAO SENTENCA / RESULTADO RECURSO (fatos) ·
SENTENCA / RESULTADO ACORDAO / ULTIMA DECISAO (avaliações) · todos os valores em R$ · SUCUMBENCIA % · PARCELAS.

**Eventos (agenda):** DATA ENTREVISTA · DATA AUDIENCIA + AUDIENCIA · DATA ADVIDEO · DATA PERÍCIA MÉDICA/TÉCNICA
· DATA ACORDAO · DATA SENTENCA · ENCERRAMENTO · DATA DO ACORDO · vencimentos de parcela (não existem).

**Tarefas disfarçadas de campo:** AND. NECESSÁRIO · PROVIDENCIAS · AVISOS · PENDENCIAS · COBRANÇA.

**Prazos que a base conhece:** prescrição bienal (PRESCREVE), SLA 15/20 dias da assinatura, cadência RI
5/10/12/15 dias. **Não conhece**: prazo processual de publicação, prazo recursal, vencimento de parcela de acordo.

## 22. Números por fase (03/09/2026)

- PRÉ: DOCUMENTAÇÃO 19 · ENTREVISTA 42 · PETIÇÃO INICIAL 147 (54 aguardando aprovação) · CONCLUÍDO 452 ·
  CANCELAMENTO 137. Urgentes: RI 84, prescrição próxima 49, 🔴 20 dias 166.
- PROCESSUAL: CONHECIMENTO 1.343 (469 aguardando audiência, 186 audiências futuras) · RECURSAL 227 ·
  EXECUÇÃO 125 + PROVISÓRIA 140 + DEFINITIVA 74 · ACORDO 119 · ENCERRADO 478 · DESISTENCIA 28 · sem fase 116.
  Incidentes: ROUBADO 66, RECEBIDO POR ELES 38, RECUPERADO 18, SOBRESTADO 11.
- CÓPIA (acervo completo): ENCERRADO 2.541 · CONHECIMENTO 572 · RECURSAL 498 · EXECUÇÃO 72+10+10 · ACORDO 14.
  Resultados conhecidos: 2.118 sentenças (1.219 parcialmente procedentes, 446 improcedentes, 383 extintas, 70
  procedentes), 1.244 acórdãos, 1.382 acordos (1.317 cumpridos), R$ 35,6 milhões recebidos em 1.081 processos,
  R$ 16,0 milhões de honorários em 1.120.
- PÓS: 556, dos quais 80 com status de recebimento e 67 com arquivamento.
