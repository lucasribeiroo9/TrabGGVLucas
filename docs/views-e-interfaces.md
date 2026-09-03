# Views, interfaces e formulários — as telas que o escritório usa hoje

> Lido em 03/09/2026 com `list_views_for_table`, `list_pages_for_base` e `get_form_schema`. A API só
> devolve **nome e tipo** da view, não o filtro — o filtro abaixo é **inferido do nome** e do que os
> dados permitem; onde a inferência é fraca está marcado `[CONFIRMAR]`. Views são as telas de trabalho:
> o portal precisa dar um lugar para cada fila que elas representam.

## PRE PROCESSUAL — 15 views

| View | tipo | o que filtra (inferido) | é fila de trabalho? |
|---|---|---|---|
| LISTA GERAL | levels (lista agrupada) | tudo, agrupado — provavelmente por ETAPA ou RESPONSAVEL INICIAL | visão geral |
| GERAL | grid | tudo | — |
| DOCUMENTAÇÃO | grid | ETAPA = DOCUMENTAÇÃO ou STATUS DOCUMENTAÇÃO ≠ COMPLETA | **sim** — setor Documentação (19 hoje) |
| DOCs AGRUPADO | grid | idem, agrupado por PENDENCIAS ou por responsável | sim |
| DOCUMENTACAO V2 | grid | segunda versão da anterior | duplicada |
| ENTREVISTA | grid | ETAPA = ENTREVISTA ou STATUS ENTREVISTA pendente | **sim** — entrevistadores (42 hoje) |
| ENTREVISTA copy / copy 2 | grid | cópias de trabalho | duplicadas |
| PETIÇÃO INICIAL | grid | ETAPA = PETIÇÃO INICIAL (147 hoje: 54 aguardando aprovação, 35 pendentes, 6 em criação, 40 já distribuídas esperando o checkbox) | **sim** — jurídico |
| CONCLUIDAS/DISTRIBUIDAS | grid | ETAPA = CONCLUÍDO / STATUS PETICAO = DISTRIBUIDA | histórico |
| CANCELADOS | grid | ETAPA = CANCELAMENTO (137) | histórico |
| HISTORICO MENSAGENS | grid | registros com `status_disparo` preenchido | auditoria do WhatsApp |
| gerencia's List | levels | visão pessoal da gerência | pessoal |
| GridView_TableTEST | grid | teste | lixo |
| Kauê (Apagar depois) | grid | view de trabalho do TI | lixo (o nome pede) |

## PROCESSUAL — 27 views

| View | tipo | o que filtra (inferido) | fila? |
|---|---|---|---|
| GERAL PISCINA | levels | "piscina" = todos os processos agrupados [CONFIRMAR: por advogado?] | visão geral |
| GERAL | grid | tudo | — |
| CONHECIMENTO | grid | FASE = CONHECIMENTO (1.343) | **sim** |
| RECURSAL | grid | FASE = RECURSAL (227) | **sim** |
| EXECUÇÃO PROVISÓRIA | grid | FASE = EXECUÇÃO PROVISÓRIA (140) | **sim** |
| EXECUÇÃO DEFINITIVA | grid | FASE = EXECUÇÃO DEFINITIVA (74) | **sim** |
| EXECUÇÕES | grid | FASE ∈ {EXECUÇÃO, PROVISÓRIA, DEFINITIVA} ou STATUS = EXECUCAO | sim |
| AUDIENCIAS | grid | DATA AUDIENCIA ≥ hoje (186 futuras: 72 em set, 58 em out, 32 em nov) | **sim** — a pauta |
| PAUTA CALENDARIO | calendar | calendário sobre DATA AUDIENCIA (talvez perícias) | a pauta em calendário |
| AD VIDEOS | grid | STATUS ADVIDEO / DATA ADVIDEO — **hoje vazio** (0 datas, 1 status) | fila morta [CONFIRMAR o que é "ad video"] |
| DESISTÊNCIA | grid | FASE ou STATUS = DESISTENCIA | histórico |
| ARQUIVADOS | grid | STATUS = ARQUIVADO (444) | histórico |
| ROUBADOS | grid | STATUS = ROUBADO (66) | **sim** — notificar/revogar |
| RECUPERADOS | grid | STATUS = RECUPERADO (18) | acompanhamento |
| REDISTRIBUIR | grid | STATUS = REDISTRIBUIR (1) | fila |
| REVOGAÇÃO | grid | REVOGAÇÃO preenchido / pendente | fila do administrativo |
| SEM EMPRESA | grid | EMPRESA vazio (542) | **qualidade de cadastro** |
| SEM N PROCESSO | grid | Nº PROCESSO vazio (106) | qualidade |
| SEM VALORES | grid | VALOR vazio (71) | qualidade |
| sem data de nascimento | grid | NASCIMENTO vazio (1.331) | qualidade (alimenta o aniversário) |
| Kauê - Apagar (Verif Tel) | grid | verificação de telefones | lixo |
| CLASSIFICAÇÃO SUMARISSIMO | grid | CLASSIFICACAO = AT - SUMARÍSSIMO ou VALOR ≤ 65k | conferência do rito |
| PROCESSOS POR ANO | grid | agrupado pelo ano de DISTRIBUIÇAO | gestão |
| Distribuição | grid | ordenado/agrupado por DISTRIBUIÇAO | gestão |
| Acordos | grid | STATUS ACORDO ou FASE = ACORDO | **sim** — acompanhar parcelas |
| ACORDOS-privado | grid | idem, com colunas de dinheiro (visão restrita) | direção |
| Grid 17 | grid | sem nome | lixo |

## PÓS PROCESSUAL — 1 view (Grid view). FUNCIONARIOS — 3 (Grid view, Pedro's Grid, GERAL em levels). EMPRESAS — 1. FRAGILIDADES — 1. AUDITORIA — 1.

## TESTEMUNHAS — 3 views

PLANILHA GERAL, PLANILHA GERAL copy, **MENSAGENS ENVIADAS** (status_disparo preenchido).

## Conferência de Faltantes — 4 views

Grid view · **SEM EMPRESA** · **SEM DATA DE DISTRIBUIÇÃO** (478 sem data) · **COM DATA DE DISTRIBUIÇÃO** (589). É a mesa de conferência do Glauco, dividida pelo que falta.

## CÓPIA DA PROCESSUAL (NÃO MEXER) — 37 views

Tem **todas as views da PROCESSUAL** (mesmos nomes) mais estas, que só existem aqui: **ACORDOS**, **DISSOLUÇÃO** [CONFIRMAR: dissolução da sociedade / empresa?], **SEM NOME**, **GERAL-BOLINHO**, **sem data de distribuição**, **SEM VALOR DA CAUSA**, **Complexidade**, **Ausencias** (STATUS CONHECIMENTO = AUSÊNCIA — reclamante faltou), **gerencia's Grid / 2 / 3**, **nome e empresa**, **Sem Astrea**, **GGVeVC View**, **Classificação**, **DADOS ZAPSIGN** (colunas para o ZapSign — assinatura eletrônica), **Data Acordao**, **status execução**, **sem drive**, **Distribuição**. A quantidade e a especificidade dessas views (ZapSign, Ausências, Sem Astrea) dizem que **a CÓPIA é usada no dia a dia**, apesar do nome.

## Interfaces

Só uma: **Dashboard inicial** → página **Dashboard** (tipo dashboard), sobre a PRE PROCESSUAL:
- um número grande: contagem de registros da PRÉ;
- pizza por `STATUS PETICAO INICIAL`;
- barras por `RESPONSAVEL INICIAL` (quantos casos cada responsável inicial tem);
- uma grade com NOME, TELEFONE, PASSAR DE FASE?, E-MAIL, CPF, NASCIMENTO, EMPRESA, FUNCAO, RESPONSAVEL INICIAL (somente leitura).

É o painel do funil de entrada. Não há interface para PROCESSUAL, PÓS ou execução.

## Formulários (standalone, sem interface)

1. **Cadastro de Cliente - Processo Trabalhista** → cria na PROCESSUAL. Seções: Dados Básicos (NOME*, TELEFONE, EMPRESA*, CAPTADOR*, ADVOGADO) · Informações Processuais (Nº PROCESSO*, TRT, VARA, TURMA, AÇÃO, FASE PROCESSUAL*, STATUS DO PROCESSO*) · Valores e Acordos (VALOR, VALOR ACORDO, STATUS ACORDO, STATUS PAGAMENTO) · Audiência, Perícias e Testemunhas (DATA AUDIENCIA, AUDIENCIA, PERICIA MEDICA/TECNICA, TESTEMUNHAS) · Classificação e Observações (CLASSIFICACAO, COMPLEXIDADE, OBSERVACOES). Pede FASE e STATUS **obrigatórios** e mostra as opções poluídas de TURMA (inclusive os números de processo que viraram opção). É o caminho de entrada de processo **que não veio do PRÉ** (o passivo).
2. **Cadastro de Funcionários** → FUNCIONARIOS: NOME*, STATUS*, FUNCOES*, OBSERVACOES.
3. **Cadastro de Testemunha** (uso interno / jurídico) → TESTEMUNHAS: NOME*, CPF*, TELEFONE*, ENDEREÇO*, HORARIO DE TRABALHO, arquivos; VINCULO*, EMPRESA*; "NOSSO CLIENTE NA FASE PROCESSUAL" (link PROCESSUAL) e "NA PRÉ PROCESSUAL" (link PRÉ); TEM PROCESSO?*; STATUS TESTEMUNHA* (pré-preenchido PENDENTE), COBRANÇA*, DATA ULTIMO CONTATO*; OBSERVACOES.
4. **Cadastro de Testemunha COMERCIAL** (para o captador) → TESTEMUNHAS: NOME*, CPF, TELEFONE*, arquivos, origem_testemunha, origem_comercial_*; EMPRESA*, VINCULO*; "NOME DO NOSSO CLIENTE (ETAPA PROCESSUAL)" — **que na verdade é o link para a PRÉ** — e "ENCONTROU NOSSO CLIENTE NA ETAPA PROCESSUAL?"*; se NÃO, aparece "NOME DO NOSSO CLIENTE (PRE PROCESSUAL)" — **que na verdade é o link para a PROCESSUAL** (rótulos trocados); CAPTADOR*; STATUS TESTEMUNHA* (PENDENTE), DATA ULTIMO CONTATO*; OBSERVACOES* com modelo "NOME DO NOSSO CLIENTE / EMPRESA / OBSERVAÇÃO". Dispara a automação nº 12.

Fora do Airtable há ainda o **Formulário Interno Único de Testemunhas** (n8n), que grava CADASTRADO POR / ÚLTIMA ALTERAÇÃO e escreve a AUDITORIA — só 2 eventos até agora, ambos "copiar link público".

## O que o portal precisa cobrir (resumo das filas vivas)

Pré-processual: **Documentação** (pendências), **Entrevista** (agendar/realizar), **Petição inicial** (criar → aprovar → distribuir), **Cancelados**, **Prescrição próxima / RI** (não há view, há campos e alertas), **SLA 15/20 dias**.
Processual: **Conhecimento** com **pauta de audiências** e perícias, **Recursal**, **Execução provisória / definitiva** (cálculo → homologação → bens/alvará), **Acordos** (parcelas), **Roubados/Recuperados/Revogação**, **Redistribuir/Sobrestado**, e as **filas de qualidade** (sem empresa, sem número, sem valor, sem nascimento).
Pós: recebimento, honorários, arquivamento (e o repasse, que hoje ninguém registra).
Transversal: testemunhas (confirmar, cobrar, avisar captador), empresas (situação, bens, fragilidades), mensagens enviadas.
