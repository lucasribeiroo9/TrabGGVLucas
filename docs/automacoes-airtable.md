# Automações do Airtable — as regras de negócio vivas

> Base **BASE GGV - TRAB V3** (`appMFTjWGygZ4ob5T`), lida em 03/09/2026 com `list_automations` +
> `get_automation` (inclusive o código dos nós de script). 14 automações: 11 ligadas, 3 desligadas ou
> vazias. Fora do Airtable há um **n8n** (`n8n.ggvadv.com`) que recebe webhooks daqui e escreve de volta
> nos campos `status_disparo`, `tipo_disparo`, `STATUS_NOTIFICACAO_*`, `notif_captador_*` — essas regras
> **não estão nesta base** e precisam ser lidas no n8n [CONFIRMAR: quem tem acesso ao n8n].

Convenção: **gatilho** → **condição** → **o que faz**. Os ids de opção foram resolvidos para o nome.

## Mapa rápido

| # | Automação | Tabela | Ligada? | Tipo de regra |
|---|---|---|---|---|
| 1 | PRÉ -> PROCESSUAL | PRE PROCESSUAL | sim | **transição de fase** (cria o processo) |
| 2 | PROCESSUAL -> PÓS PROCESSUAL | PROCESSUAL | sim | **transição de fase** (cria o pós) |
| 3 | DESISTENCIA | PRE PROCESSUAL | sim | propagação de saída |
| 4 | URGENCIA R.I | PRE PROCESSUAL | sim | marcação de urgência |
| 5 | URGENCIA ALTA | PRE PROCESSUAL | sim | marcação de urgência |
| 6 | 🟡 CLIENTE ASSINOU A 15 DIAS ATRÁS | PRE PROCESSUAL | sim | SLA / alerta |
| 7 | 🔴 CLIENTE ASSINOU A 20 DIAS ATRÁS | PRE PROCESSUAL | sim | SLA / alerta |
| 8 | PROCESSUAL \| AUTOPREENCHIMENTO | PROCESSUAL | sim | **derivação de fase/status a partir de fatos** (script) |
| 9 | COMPLEXIDADE POR VALOR \| CÓPIA PROCESSUAL | CÓPIA | sim | derivação de atributo (script) |
| 10 | ANIVERSARIO MENSAGEM | PRE + PROCESSUAL | sim | disparo diário ao n8n (script) |
| 11 | Automation 1 (testemunha nova → n8n) | TESTEMUNHAS | sim | webhook ao n8n (script) |
| 12 | TESTEMUNHAS \| Comercial vira ignorado | TESTEMUNHAS | sim | marcação de origem |
| 13 | ATUALIZAR | PROCESSUAL | **não** | classificação por valor |
| 14 | Automation 2 | — | **não** | vazia (cron sem nós) |

---

## 1. PRÉ -> PROCESSUAL — a passagem de fase

- **Gatilho**: registro da PRE PROCESSUAL passa a casar as condições.
- **Condição** (E): `ETAPA PRE PROCESSUAL` ∈ {PETIÇÃO INICIAL, CONCLUÍDO} **e** `PASSAR DE FASE?` marcado **e** `STATUS PETICAO INICIAL` = DISTRIBUIDA.
- **Faz**: (a) cria um registro na PROCESSUAL copiando **só** NOME, TELEFONE, EMPRESA, CAPTADOR, DRIVE, ASTREA, e os dois checkboxes de perícia (PERICIA INSALUB/PERIC → PERICIA TECNICA; PERICIA MEDICA → PERICIA MEDICA); (b) grava no registro PRÉ o link `PROCESSUAL` apontando para o recém-criado.
- **Leitura**: a decisão de "virar processo" é humana (o checkbox), mas só destrava quando a petição já foi **distribuída**. É a única transição entre tabelas com gate explícito.
- **O que se perde na passagem**: CPF, NASCIMENTO, DATA DE ASSINATURA, ENTREVISTADOR, RESPONSAVEL INICIAL, TESTEMUNHAS, RESUMO ENTREVISTA, DEMISSAO/RESCISAO **não são copiados**. O processo nasce **sem Nº PROCESSO** (a PRÉ não tem esse campo) — daí os 106 processos sem número, 40 deles ligados a um PRÉ. E nasce sem FASE/STATUS: é o script nº 8 que depois deduz CONHECIMENTO quando alguém preenche a DISTRIBUIÇAO.
- **Prova nos dados**: 431 PRÉs ligados a um processo; 393 dos 452 CONCLUÍDOS têm o checkbox e o link; 47 CONCLUÍDOS têm o checkbox e **não** têm link (a condição de DISTRIBUIDA não fechou ou a automação falhou) [CONFIRMAR].

## 2. PROCESSUAL -> PÓS PROCESSUAL

- **Gatilho**: registro da PROCESSUAL passa a casar.
- **Condição** (OU): `FASE PROCESSUAL` ∈ {DESISTENCIA, ENCERRADO} **ou** `STATUS DO PROCESSO` ∈ {ARQUIVADO, DESISTENCIA}.
- **Faz**: cria registro na PÓS PROCESSUAL com N° DO PROCESSO, link PROCESSUAL, RESPONSAVEL (= ADVOGADO), RESULTADO FINAL (= RESULTADO), VALOR RECEBIDO CLIENTE (= TOTAL RECEBIDO), VALOR HONORARIOS (= HONOR TOTAL), VALOR SUCUMBENCIA (= SUCUMB RECEBIDO), STATUS RECEBIMENTO (= nome do STATUS PAGAMENTO); e grava o link `POS PROCESSUAL` de volta.
- **Leitura**: encerrar/arquivar/desistir é o que abre a fase de "dinheiro e arquivo". Os valores são **copiados no instante da transição** — se TOTAL RECEBIDO mudar depois, o PÓS fica defasado. Não há regra para o repasse ao cliente (STATUS REPASSE está vazio em 556/556).
- **Risco**: gatilho "matches conditions" dispara de novo se o registro sair e voltar à condição → pós duplicado. 556 PÓS para 453 processos ligados; 99 PÓS sem link nenhum [CONFIRMAR: criados à mão?].

## 3. DESISTENCIA — a saída propaga

- **Condição** (OU): `STATUS DOCUMENTAÇÃO` = DESISTÊNCIA, ou `STATUS ENTREVISTA` = DESISTÊNCIA, ou `STATUS PETICAO INICIAL` = DESISTENCIA.
- **Faz**: grava DESISTÊNCIA nos **três** status e `ETAPA PRE PROCESSUAL` = CANCELAMENTO.
- **Leitura**: desistência em qualquer ponto cancela o pré-processual inteiro. É a única regra que escreve na ETAPA. Não pede motivo, não registra quando nem quem.

## 4. URGENCIA R.I — rescisão indireta é urgente

- **Condição**: `RESCISAO` (texto livre) **contém** "RESCISÃO INDIRETA".
- **Faz** (dois scripts em sequência, cada um acrescentando sem apagar o que já havia): adiciona `RI` ao multi-select `URGENCIA`; depois adiciona `URGENCIA ALTA`.
- **Leitura**: quem está pedindo rescisão indireta **ainda está empregado** — a ação precisa sair rápido, porque o contrato está correndo (e o n8n cobra o andamento em 5/10/12/15 dias via `STATUS_NOTIFICACAO_RI`). Depende do captador escrever exatamente "RESCISÃO INDIRETA" — os 2 registros com "RECISÃO INDIRETA" ficam de fora.

## 5. URGENCIA ALTA

- **Condição**: `URGENCIA` = exatamente [RI].
- **Faz**: **substitui** `URGENCIA` por [URGENCIA ALTA] (updateRecord com valor único, não acrescenta).
- **Leitura**: redundante com a nº 4 e potencialmente conflitante (uma acrescenta, a outra substitui). Nos dados, 83 registros têm RI + URGENCIA ALTA e 5 só URGENCIA ALTA — a nº 4 vence na prática.

## 6 e 7. 🟡 15 dias / 🔴 20 dias desde a assinatura

- **Condição**: `DATA DE ASSINATURA` = exatamente 15 (ou 20) dias atrás (fuso São Paulo).
- **Faz**: escreve o texto "🟡CLIENTE ASSINOU A 15 DIAS ATRÁS" / "🔴 CLIENTE ASSINOU A 20 DIAS ATRÁS" no campo `AVISOS`.
- **Leitura**: é o **SLA do pré-processual**: 15 dias da assinatura do contrato sem distribuir é amarelo, 20 é vermelho. Como escrevem no mesmo campo, o vermelho apaga o amarelo (166 registros com 🔴, 8 com 🟡). Dispara mesmo para quem já está CONCLUÍDO ou CANCELADO — não há condição de etapa. Não gera tarefa nem avisa ninguém; só marca.

## 8. PROCESSUAL | AUTOPREENCHIMENTO — o cérebro da PROCESSUAL

- **Gatilho**: qualquer mudança em um destes campos: COMPLEXIDADE, DISTRIBUIÇAO, DATA ACORDAO, DATA AUDIENCIA, AUDIENCIA, Nº CumPrSe, STATUS RECURSAL, STATUS CumPrSe, STATUS DO CALCULO, ENCERRAMENTO, DATA ADVIDEO, STATUS ACORDO, DATA PERÍCIA TECNICA, DATA PERÍCIA MÉDICA, VALOR.
- **Faz** (script; grava tudo de uma vez ao final; loga cada mudança "de → para | motivo"). Regras, na ordem em que rodam:
  1. **Complexidade por valor** — só se COMPLEXIDADE estiver vazia: C ≤ R$ 150.000; B ≤ R$ 500.000; A acima. Edição manual é preservada.
  2. **Perícias** — DATA PERÍCIA MÉDICA preenchida marca PERICIA MEDICA; DATA PERÍCIA TECNICA marca PERICIA TECNICA.
  3. **Ad video** — DATA ADVIDEO no futuro e processo não terminal → STATUS ADVIDEO = MARCADO (se estava vazio/PENDENTE).
  4. **Encerramento** — ENCERRAMENTO com data → FASE = ENCERRADO.
  5. **Acordo** — QUEBRA DE ACORDO → FASE = EXECUÇÃO (se não estava em execução) e STATUS = EXECUCAO. ACORDO EM ANDAMENTO / CUMPRIDO → FASE = ACORDO e STATUS = ACORDO (salvo se FASE = RECEBENDO).
  6. **Trânsito em julgado** — STATUS = TRÂNSITO EM JULGADO e decisão objetiva (ULTIMA DECISAO se for PROCEDENTE/IMPROCEDENTE, senão DECISAO SENTENCA): PROCEDENTE ou PARCIALMENTE → FASE = EXECUÇÃO DEFINITIVA; IMPROCEDENTE → FASE = ENCERRADO.
  7. **Cumprimento provisório** — Nº CumPrSe ou STATUS CumPrSe preenchido → FASE = EXECUÇÃO PROVISÓRIA (se não for já DEFINITIVA) e STATUS = EXECUCAO.
  8. **Cálculos** — STATUS DO CALCULO: PENDENTE → STATUS EXECUÇÃO = AGUARDANDO CÁLCULO; JUNTADO AOS AUTOS → FASE DE CÁLCULOS; HOMOLOGADO → HOMOLOGADO. Em todos, FASE vira EXECUÇÃO (se não estava numa execução) e STATUS = EXECUCAO. Só sobrescreve STATUS EXECUÇÃO se ele estiver vazio ou num dos valores "de cálculo" (inclusive as grafias poluídas, que o script lista uma a uma).
  9. **Recursal** — STATUS RECURSAL ou DATA ACORDAO preenchidos, e FASE vazia/CONHECIMENTO/RECURSAL → FASE = RECURSAL.
  10. **Sentença** — DECISAO SENTENCA ∈ {PROCEDENTE, IMPROCEDENTE, PARCIALMENTE PROCEDENTE} → STATUS CONHECIMENTO = SENTENCIADA; se FASE vazia → CONHECIMENTO.
  11. **Agenda do conhecimento** (só sem sentença, FASE vazia ou CONHECIMENTO): pega o **próximo evento futuro** entre ad video (prioridade 1), perícia médica/técnica (2) e audiência com tipo preenchido (3); FASE = CONHECIMENTO e STATUS CONHECIMENTO = ADVIDEO / AGUARDANDO PERICIA / AGUARDANDO AUDIÊNCIA conforme o evento; se for audiência, STATUS DO PROCESSO = AGUARDANDO AUDIÊNCIA (só se estava vazio ou já em AGUARDANDO AUDIÊNCIA/SENTENÇA). Sem evento futuro mas com DISTRIBUIÇAO → FASE = CONHECIMENTO.
- **Proteções**: nunca mexe em processo terminal (FASE ENCERRADO/DESISTENCIA ou STATUS ARQUIVADO/DESISTENCIA); nunca sobrescreve STATUS DO PROCESSO se ele for ARQUIVADO, DESISTENCIA, ROUBADO, RECUPERADO, RECEBIDO POR ELES, REDISTRIBUIR ou SOBRESTADO ("protegidos" = decididos por gente).
- **Leitura para o portal**: este script **é** a máquina de estados da PROCESSUAL, só que escrita como *inferência a partir de fatos* (datas e status auxiliares) em vez de transições declaradas. Ele nunca **volta** fase (só avança ou preenche vazio) e não registra histórico. Também mostra o que o escritório considera **fato-gatilho**: data de sentença/acórdão, número do CumPrSe, status do cálculo, data de encerramento.

## 9. COMPLEXIDADE POR VALOR | CÓPIA PROCESSUAL

- **Gatilho**: VALOR muda em registro da CÓPIA que esteja na view GERAL.
- **Faz**: parseia o valor (aceita texto com vírgula/ponto) e grava COMPLEXIDADE = C (≤150k) / B (≤500k) / A (>500k) — aqui **sempre**, sobrescrevendo manual.
- **Leitura**: mesma régua da nº 8, mas sem preservar edição humana. Confirma que a CÓPIA está viva e recebe VALOR de fora.

## 10. ANIVERSARIO MENSAGEM (script, todo dia 9h, fuso São Paulo)

- Varre PRE PROCESSUAL e PROCESSUAL procurando NASCIMENTO com dia/mês de hoje (ano ignorado; para PROCESSUAL sem NASCIMENTO, busca no PRÉ ligado).
- Deduplica por telefone normalizado (+55), nome e empresa; escolhe o melhor candidato (telefone válido pesa 100, nome 30, empresa 10, PRÉ 3, PROCESSUAL 2).
- Manda **um POST por pessoa** ao webhook `airtable-aniversario` do n8n com telefone, nome, tipo `aniversario`, tabela e id de origem.
- Grava de volta `status_disparo` = `aniversario_enviado` ou `aniversario_erro`, `data_solicitacao_disparo` = agora, `erro_disparo` = mensagem. Ignora quem já foi enviado hoje.
- **Nos dados**: PRÉ tem 88 `aniversario_erro` contra 15 enviados; PROCESSUAL 60 erros contra 10 enviados. **O disparo está falhando na maioria das vezes** e ninguém vê, porque o erro fica num campo de texto sem alarme.

## 11. "Automation 1" — testemunha nova avisa o n8n

- **Condição**: TESTEMUNHAS com NOME TESTEMUNHA **e** TELEFONE TESTEMUNHA preenchidos.
- **Faz**: POST `{recordId}` ao webhook `testemunhas-entrada-v3` do n8n. Lança erro se o n8n responder ≠ 2xx.
- **Leitura**: tudo o que acontece depois (avisar o captador, checar duplicidade, `notif_captador_status`) mora no n8n. Sem nome, a automação é anônima na lista.

## 12. TESTEMUNHAS | Comercial vira ignorado

- **Gatilho**: envio do formulário **Cadastro de Testemunha COMERCIAL**.
- **Faz**: `notif_captador_status` = IGNORADO e `origem_testemunha` = COMERCIAL.
- **Leitura**: testemunha trazida pelo próprio captador não gera aviso ao captador (seria avisar a si mesmo).

## 13. ATUALIZAR — desligada

- **Condição**: VALOR < 65.000 → CLASSIFICACAO = AT - SUMARÍSSIMO.
- **Leitura**: tentativa de derivar o rito pelo teto do sumaríssimo (40 salários mínimos, art. 852-A CLT; 40 × R$ 1.621 ≈ R$ 64.840 em 2026). Foi desligada — provavelmente porque o rito é o que a **vara** aplicou, não o que o valor sugere [CONFIRMAR]. Nos dados, 129 processos AT - ORDINÁRIO têm valor ≤ 65 mil e 252 sem classificação estão nessa faixa.

## 14. Automation 2 — vazia, desligada

Cron sem nós. Lixo.

---

## Botões "ENVIAR MENSAGEM" (PRE, PROCESSUAL, CÓPIA, TESTEMUNHAS)

Não são automações, são campos-botão: abrem uma URL do webhook `airtable-lailla-disparo` do n8n com os campos do registro como parâmetros (nome, telefone, empresa, CPF, status, data da entrevista…). "Lailla" é o disparador de WhatsApp do escritório. O n8n responde escrevendo `status_disparo`/`tipo_disparo`/`data_solicitacao_disparo`/`responsavel_interno`/`solicitante_disparo`. Tipos vistos: aviso_informativo, solicitacao, compromisso, aniversario, inicio_atendimento, inicio_testemunha, evento, lembrete.

## O que NÃO existe como automação (e a base sugere que existe)

- **Conferência de Faltantes → PROCESSUAL**: a descrição da tabela diz que marcar "✅ VALIDAR E SUBIR" promove o processo "via automação". **Não há automação** com esse gatilho, e ninguém marcou o checkbox (0/1.067).
- **Notificação de prescrição e de RI** (`STATUS_NOTIFICACAO_*`): escritas pelo n8n, não daqui.
- **Distribuição de tarefa, prazo, publicação de diário**: nada. O Airtable não tem noção de tarefa nem de prazo processual — só datas de audiência/perícia e a prescrição bienal.
- **Histórico de mudança de fase**: nenhuma regra grava quem/quando mudou FASE ou STATUS.
