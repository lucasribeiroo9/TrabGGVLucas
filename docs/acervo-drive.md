# Acervo do Drive — GGV Trabalhista

Varredura de leitura feita em 04/09/2026. Escritório atua **pelo reclamante** (empregado).

**Sobre as duas raízes.** A raiz `0ANLgSgN6Di2lUk9PVA` (título "Drive") abriu normalmente e é
a base deste relatório. A raiz `0AANamNIiO33PUk9PVA` **não abriu**: `search_files` com
`parentId` devolveu resultado vazio e `get_file_metadata` devolveu *"Requested entity was not
found"*. Não é pasta vazia — é falta de acesso ou ID inválido para esta conta.
`[CONFIRMAR: a segunda raiz existe e está compartilhada com a conta que o sistema usa?]`
Tudo abaixo vem, portanto, de **uma** raiz só.

**Sobre dados pessoais.** Nenhum nome de cliente, CPF, telefone, e-mail, endereço ou número
CNJ entrou neste arquivo. Nomes de **empresas reclamadas** entram (são pessoas jurídicas e
são o eixo de organização do acervo). Nomes de **advogados que deixaram a banca** foram
omitidos de propósito.

---

## 1. Estrutura das pastas

A raiz tem quatro pastas numeradas, mais avulsos jogados na raiz (planilhas de controle,
modelos de entrevista, termos de revogação, um CRRR, um MP4 de gravação de tela).
**A raiz é usada como área de trabalho**, não só como índice — o que já diz que não há
disciplina de arquivamento imposta por ferramenta.

### `#1-JURIDICO` — o coração da operação (~55 subpastas)

Divide-se em três famílias:

**(a) O acervo de casos — `PROCESSOS`.** Esta é a pasta que mais importa.
A hierarquia é de **três níveis**:

```
#1-JURIDICO / PROCESSOS / [EMPRESA RECLAMADA] / [CLIENTE X RECLAMADA] / ...
```

Ou seja: **o eixo primário de organização é a EMPRESA RECLAMADA, não o cliente e não o ano.**
A pasta do caso vem depois, nomeada no padrão `NOME DO CLIENTE X NOME DA RECLAMADA`.
Isso é confirmado pelo procedimento escrito (`#2-ADMINISTRATIVO/PROCEDIMENTOS/PROCEDIMENTO
PARA DOCUMENTAÇÃO DE CLIENTES`), que manda:

> "Criar pasta do cliente dentro do GDrive **com o nome igual está no RG**. Criar pasta neste
> caminho: `\TRABALHISTA – GGV\#1 JURIDICO\PROCESSOS\[NOME DA EMPRESA]`. Caso for o primeiro
> cadastro da empresa, criar pasta para a empresa. Senão procurar a pasta da empresa."

São dezenas de pastas de empresa (transporte urbano, elétrica/telecom, saúde/hospitais,
varejo/supermercado, facilities, segurança patrimonial, call center). Sinais de desordem
visíveis: **6+ pastas literalmente chamadas `Untitled`**, duplicatas exatas de empresa
(a mesma reclamada aparecendo duas vezes com pastas separadas), variantes de nome da mesma
empresa (nome fantasia vs. razão social vs. grupo econômico), e erros de digitação no nome
da empresa. Duas empresas homônimas aparecem desambiguadas **pelo CNPJ escrito no nome da
pasta** — a prova de que o eixo "empresa" precisa de chave, e hoje a chave é texto.

Dentro da pasta do caso, o padrão observado (dois casos abertos, de reclamadas diferentes):

| Item | Natureza |
|---|---|
| `Entrevista - [cliente] x [reclamada].docx` | o roteiro preenchido |
| `INICIAL - [cliente] x [reclamada].docx` | a petição inicial |
| `Juntada Substabelecimento com reserva de poderes - GGV Advogados.docx` | recorrente em todo caso |
| `Manifestação - [assunto].docx` | peça avulsa (ex.: local de trabalho) |
| subpasta `Kit Procuração` | Contrato de Honorários + demais partes |
| subpasta `Protocolo` | tudo que vai instruir os autos |
| subpasta `AUDIENCIA` | relatório de audiência + informações de testemunhas |
| PDFs soltos | Contrato Original / Contrato Assinado, atestado médico, carta de oferta |
| **áudio `.mp3`** | gravação usada como prova (ex.: preposto da reclamada admitindo tempo ocioso) |

O `Protocolo` de um caso trazia: **Declaração de Hipossuficiência**, **Procuração**,
**Relatório de Assinatura** (o log de auditoria do ZapSign), **RG**, **CTPS**,
**CCT 2023/2024 e CCT 2024/2025** (duas vigências), **JUCESP** da reclamada **e** da
co-ré, e **Cartão CNPJ** do tomador de serviço. Os arquivos vêm **numerados no nome**
(`1. JUCESP ...`, `2. JUCESP ...`, `3. Cartão CNPJ ...`) — a ordem de juntada é parte do
trabalho e hoje mora no nome do arquivo.

**(b) Bibliotecas e modelos** (o que se reaproveita):
`MODELOS E PESQUISAS`, `MODELOS - MANIFESTAÇÕES`, `MODELOS DE PETIÇÃO`,
`MODELOS DE ENTREVISTA`, `ENTREVISTA MODELO`, `PROVISÓRIA ENTREVISTA`,
`BANCO DE TESES - INICIAL`, `ACÓRDÃOS`, `DECISÕES` (subdividida em `SENTENÇA`,
`ACÓRDÃO`, `CONCILIAÇÕES/ACORDOS`), `Checklist de Réplica trabalhista`,
`SUBSTABELECIMENTO (MODELOS)` (com `INDIVIDUAIS - ADV. INTERNOS` e
`INDIVIDUAIS - CORRESPONDENTES`), `CONVENÇÕES COLETIVAS`, `CCT - ELETRICISTAS`,
`CCT - MOTORISTA DE ÔNIBUS`, `JUÍZES E DESEMBARGADORES`, `PROMPTS`,
`TACTIQ MODELOS INICIAIS PRONTOS`, `Banco de Jurisprudências`, `TREINAMENTO`.

**(c) Frentes de operação** (pastas que são projeto, não biblioteca):
`REVOGAÇÕES / PROCURAÇÃO`, `TERMOS DE REVOGAÇÃO PARA SUBIR`, `DESISTÊNCIAS`,
`SETOR DE TESTEMUNHAS`, `EXECUÇÃO` (com `RECURSOS` e `MANIFESTAÇÕES`),
`EXECUÇÕES PROVISÓRIAS`, `ESTUDO DE EXECUÇÕES`, `ESTUDOS DE EMPRESAS`,
`CONTROLE INICIAIS - PRESCRIÇÃO`, `AUDIÊNCIAS`, `PREP. AUDIÊNCIAS`,
`MUTIRÃO DAS INICIAIS`, `FLUXO DO PROCESSO PERFEITO`, `ARQUIVO MORTO`,
`CAP. PROJETO RJ`, `CAP - Recuperação Judicial`, `PARCERIA FINAZZI`,
`FOTOS CLIENTES P/ MURAL`.

Também na raiz do `#1-JURIDICO`, **soltos**, há `RELATÓRIO ...` em Google Docs — um por
caso, criados nos últimos dias, com o padrão `RELATÓRIO [conciliação|AUDIENCIA]: CLIENTE x
RECLAMADA - CNJ` no título. É produto de trabalho recente que **ainda não foi arquivado
na pasta do caso**.

### `#2-ADMINISTRATIVO` — gestão do escritório

`EQUIPE JURÍDICO` (uma pasta por colaborador, ~20, incluindo `EX - COLABORADORES`),
`ARQUIVOS AIRTABLE - KIT PROCURAÇÃO` (os 4 PDFs-modelo do kit),
`PROCEDIMENTOS` / `PASSO A PASSO` (SOPs escritos), `DATABASE PETIÇÕES`,
`DATABASE RÉPLICAS`, `ADVBOX`, `ESTAGIOS`, `META ALVO`, `ORGANIZAÇÃO GGV`,
`PROCURAÇÃO, DECLARAÇÃO E SUBS`, `CARTÕES E PASTAS`, `LOGO GGV`,
`VIDEO PREPARATIVO AUDIÊNCIA`. Planilhas: `CONTROLE SUSTENTAÇÃO ORAL` (2 versões),
`DIVISÃO DAS EMPRESAS / ADVS`, `CONTROLE HOME OFFICE`.

### `#3-COMERCIAL` — captação

Contém **uma única** subpasta, `CAPTAÇÃO TRABALHISTA`, e dentro dela:
`CONTROLE CAPTAÇÃO` (formulários Google `[2023]`/`[2025] Controle Captação` + planilhas
`[2026] Controle Captação Trabalhista`, `OPERAÇÃO CAPTAÇÃO`, `Controle trabalhista 2024`),
`CAPTADORES`, `RECIBOS PAGAMENTOS` (o pagamento do captador),
`FABRICA DE LEADS` → `EMPRESAS - LEADS / GERAL`, `PROJETO VAGAS`, `PIPE DRIVE`,
`RESGATE WHATSAPP`, `Gerentes a Utilizar`, `EMPRESAS CNPJ`, `Cálculos de processos`,
`ANTIGOS`. Há exportações automatizadas de listas de processos por empresa
(arquivos com nome `...-processos-<uuid>`).

### `#4-TI` — o projeto de sistema (recente, 2026)

`AIRTABLE` (com `BACKUPS AIRTABLE`, `Cancelados AirTable`,
`AIRTABLE ATUALIZAÇÕES ACORDOS`, `CALCULOS CONTADOR`, `handoff`, `pje para pesquisa`),
`CLAUDE CODE - EMPRESAS` (com um `ggv-kit-inteligencia-empresas.zip`),
`PROCESSOS TODOS`, `processos faltantes TRT2-Claude`, `INVENTARIO SISTEMAS`,
`INVENTARIO DE DISPOSITIVOS ELETRONICOS`, `GERENCIADORES DE SENHAS`,
`DOCUMENTAÇÃO DE ATIVIDADES`, `PÓS MUDANÇA`, planilhas
`auditoria_provisionada_<data>` (3 dias seguidos) e `AUDITORIA - ORGANIZACAO`.

---

## 2. Tipos de documento — quais existem de fato e como se chamam

Confirmados por leitura direta ou por nome de arquivo no acervo:

| O que é | Nome real na casa | Onde vive | Papel no fluxo |
|---|---|---|---|
| Contrato de honorários | **`Contrato de Honorários`** (às vezes `Honorários 1` + `Honorários 2`, duas partes) | `Kit Procuração` | fecha o cliente |
| Procuração | **`Procuração`** | `Kit Procuração` / `Protocolo` | instrui a inicial |
| Declaração de hipossuficiência | **`Declaração de Hipossuficiência`** / `Hipossuficiência` | `Protocolo` | justiça gratuita |
| Log de assinatura eletrônica | **`Relatório de Assinatura - [cliente]`** | `Protocolo` | prova a assinatura (ZapSign) |
| Roteiro de entrevista | **`ENTREVISTA [cliente] x [reclamada].docx`** / `MODELO DE ENTREVISTA ATUALIZADO` / `Modelo - ENTREVISTA - ELETRICISTA` | pasta do caso | levanta os pedidos |
| Petição inicial | **`INICIAL - [cliente] x [reclamada].docx`** | pasta do caso | — |
| Réplica | **`Checklist para réplica trabalhista.docx`** + `DATABASE RÉPLICAS`, `replica apresentação.pdf` | biblioteca | responde à contestação |
| Manifestação | **`Manifestação - [assunto].docx`** | `MODELOS - MANIFESTAÇÕES` | peça curta de saneamento |
| Relatório de audiência | **`RELATÓRIO AUDIÊNCIA - MODELO.docx`** (e MODELO 2) | biblioteca + pasta do caso | prepara e registra a audiência |
| Relatório de conciliação | **`RELATÓRIO conciliação [caso]`** | raiz do `#1-JURIDICO` | registra o acordo |
| Relatório de desistência | **`RELATÓRIO DE DESISTÊNCIA`** | `DESISTÊNCIAS` | encerra sem mérito |
| Substabelecimento | **`Juntada Substabelecimento com reserva de poderes - GGV Advogados.docx`** | em quase todo caso | passa o caso a interno ou correspondente |
| Termo de revogação | **`Termo Revogação.docx`** / **`Apenas Revogação.docx`** (modelos) e `Revogação - [cliente].pdf` (assinados) | raiz + `REVOGAÇÕES / PROCURAÇÃO` | troca de advogado |
| Petição que junta a revogação | **`Pet. Termo de Revogação de Poderes - [cliente] x [reclamada]`** | `TERMOS DE REVOGAÇÃO PARA SUBIR` | leva a revogação aos autos |
| Recurso de revista | **`CRRR - [cliente] x [reclamada].docx`** | raiz | 3ª instância |
| Rol / intimação de testemunha | **`ROL DE TESTEMUNHAS - PRESENCIAL`**, **`... COM PEDIDO DE LINK`**, **`CARTA DE INTIMAÇÃO DE TESTEMUNHA`** | `SETOR DE TESTEMUNHAS` | prova oral |
| Sentença / acórdão | `Sentença (n).pdf`, `ROT_<cnj>_2grau.pdf`, `ATOrd_<cnj>_1grau.pdf` | `DECISÕES`, `ESTUDOS DE EMPRESAS` | resultado |
| Convenção coletiva | **`CCT AAAA.AAAA.pdf`**, uma por vigência | `Protocolo` + `CONVENÇÕES COLETIVAS` | base do pedido |
| Prova documental do cliente | `CTPS`, `RG`, `CNH`, `Holerites/Recibos`, `TRCT`, `Cartão de ponto`, `Extrato de FGTS`, atestado médico | `Protocolo` | — |
| Prova sobre a reclamada | **`JUCESP [empresa] ATUALIZADA.pdf`**, **`Cartão CNPJ [ente]`** | `Protocolo` | grupo econômico / subsidiária |
| Prova em mídia | `.mp3` de conversa, prints e vídeos de WhatsApp | pasta do caso | jornada, assédio |
| Foto do cliente | `FOTOS CLIENTES P/ MURAL` | — | ritual de fechamento (ver §5) |

**Não encontrei, como tipo próprio e nomeado, no acervo aberto:**
- **defesa/contestação da reclamada** arquivada como documento do caso (o checklist de
  réplica pressupõe que ela existe, mas ela é lida no PJe, não guardada aqui);
- **laudo pericial** como arquivo; existe o campo "HOMOLOGADO OU PERICIAL" nas planilhas e
  uma `Manifestação - E-mail (Perícia)`, mas laudo em si não apareceu;
- **cálculo** como documento; existe `Cálculos de processos`, `CALCULOS CONTADOR`,
  `Passo a Passo Pje Calc Cidadão.docx` e colunas de cálculo nas planilhas — o cálculo é
  **planilha e coluna**, não peça arquivada;
- **alvará** — nenhuma ocorrência. O dinheiro aparece como "acordo cumprido",
  "valor líquido do reclamante", "sucumbência", nunca como alvará;
- **notificação** — só aparece na frase "Ramon se habilitou e após enviou a notificação",
  ou seja, notificação **recebida da parte adversa/ex-patrono**, não emitida.

---

## 3. As planilhas de controle, coluna a coluna

### 3.1 `LEVANTAMENTO TOTAL - 2025/2026` — o registro de captação

Três abas.

**Aba 1 — o cadastro (18 colunas):**

`NOME_CLIENTE` · `EMPRESA_RECLAMADA` · **`EMPRESA_NORMALIZADA`** · `SEGMENTO` ·
`FUNCAO` · `TIPO_RESCISAO` · `DATA_ASSINATURA_CONTRATO` · `ANO_CAPTACAO` ·
`MES_CAPTACAO` · **`CAPTADOR`** · `TELEFONE` · `EMAIL` · `DATA_NASCIMENTO` ·
`DATA_ADMISSAO` · `DATA_DEMISSAO` · `TEMPO_EMPRESA` · **`FORMA_ASSINATURA`** ·
**`FONTE_CAPTACAO`**

Vocabulários observados:
- `SEGMENTO`: Transporte, Saúde, Eletricidade, Serviços
- `TIPO_RESCISAO`: Sem Justa Causa, Pedido de Demissão, Rescisão Indireta, Acordo,
  Não informado
- `FORMA_ASSINATURA`: ZapSign (praticamente universal)
- `FONTE_CAPTACAO`: **Projeto Puxada**, **Projeto Currículos**, **Indicação**,
  **Testemunha** ← a testemunha de um caso vira cliente de outro

**Aba 2 — a qualidade do cadastro (5 colunas):**
`NOME_CLIENTE` · **`CAMPOS_FALTANDO`** · **`FONTES_USADAS`** · **`LINK_PASTA_DRIVE`** ·
**`PASTA_LOCAL_ENCONTRADA`**

**Aba 3 — as métricas:** `METRICA` / `VALOR`, com
`TOTAL_CLIENTES 872` · `COM_EMPRESA 872` · `COM_CAPTADOR 872` · `COM_SEGMENTO 764` ·
`COM_FUNCAO 613` · **`COM_LINK_DRIVE 511`** · `COM_PASTA_LOCAL 781`.

Ou seja: **361 dos 872 clientes captados não têm link de pasta no Drive** e 91 nem pasta
local. Alguém já fez esse levantamento à mão e o mediu — é um projeto de conciliação
cadastro↔Drive que já existe fora do sistema.

### 3.2 `OPERAÇÃO REVOGAÇÃO` — a guerra de clientes

11 abas, esquemas ligeiramente diferentes entre elas (mesma operação recortada por lote).
O esquema mais completo:

`NOME` · `RESPONSÁVEL` · `EMPRESA` · **`FOTO`** · `CONTATO` · `N° PROCESSO` ·
**`cumprimento de sentença`** · **`CALCULO RECLAMADA`** · **`VALOR DO CALCULO`** ·
**`RÉSPONSÁVEL PELO CONTATO`** · **`REVOGAÇÃO / PROCURAÇÃO`** · `DATA DO CONTATO` ·
**`FASE DO PROCESSO`** · **`STATUS PROCESSUAL`** · **`QUANDO HABILITOU`** · `OBS:` ·
**`CALCULO RECLAMANTE`** · **`SUCUMBENCIA`** (×3) · **`PERITO`** · `ENDEREÇO` ·
`SITUAÇÃO ZAPSIGN` · `RETORNO` · `SEPARAÇÃO` · `link` · `STATUS DA OPERAÇÃO:`

Vocabulários apurados:

- **`REVOGAÇÃO / PROCURAÇÃO`** (o funil da operação):
  `PROTOCOLADO` (97) · `ARQUIVADO` (97) · **`ROUBADO`** (47) · `MENSAGEM ENVIADA` ·
  `LINK ENVIADO` · `LINK EM CURSO` · `ASSINADO` · `AGUARDANDO` · **`RECUPERADO`** ·
  `VOLTOU` · `NÃO ATENDEU` · `NÃO CHAMAR` · `SIM`
- **`FASE DO PROCESSO`**: `Fase Recursal` (70) · `Execução Provisória` (64) ·
  `Fase de Conhecimento` (55) · `Execução Definitiva` (16) · `Processo Arquivado`
- **`STATUS PROCESSUAL`**: `2º GRAU` (56) · `AGUARDANDO AUDIÊNCIA` (51) ·
  `ACORDO CUMPRIDO` (31) · `TST` (16) · `ACORDO` (14) · `FINALIZADO COM SUCESSO` (9) ·
  `ARQUIVADO DEFINITIVAMENTE` · `EXTINTA A EXECUÇÃO` · `AGUARDANDO SENTENÇA` ·
  `PARCELAMENTO CPC` · `DECISÃO POSITIVA EM 2ª INSTÂNCIA`
- **`FOTO`**: `RG` (33) · `CNH` (27) — não é foto, é **qual documento de identidade o
  escritório tem em mãos** para montar o kit
- **`SEPARAÇÃO`**: um número 1–4, sem legenda. `[CONFIRMAR: 1–4 é prioridade, lote ou
  instância?]`
- **`RÉSPONSÁVEL PELO CONTATO`**: 12+ pessoas, com uma dominante (81 registros);
  distinto de `RESPONSÁVEL`, que é o advogado dono do caso

**A coluna que não tem equivalente no sistema:** `FASE DO PROCESSO` e `STATUS PROCESSUAL`
são **duas dimensões independentes** que o escritório mantém lado a lado. Fase é a etapa
processual formal; status é onde o trabalho efetivamente está parado. Elas discordam de
propósito: existe linha com fase `Fase Recursal` e status `AGUARDANDO AUDIÊNCIA`.

Há ainda evidência de **contradição interna registrada na própria planilha** — células com
`RECUPERADO` e observação `"???? nao foi recuperado"`, ou `MENSAGEM ENVIADA` com a nota
`"pq roubado?"`. A planilha é o único lugar onde a divergência é anotada, e não há
mecanismo que a resolva.

### 3.3 `EXECUÇÕES` — o mesmo funil, ordenado por dinheiro

3 abas. Colunas:
`RECLAMANTE` · `RECLAMADA` · `Nº DO PROCESSO` · `RESPONSÁVEL` ·
**`REVOGAÇÃO/PROCURAÇÃO`** · `CONTATO` · `DATA CONTATO` · `QUEM ENTROU EM CONTATO` ·
**`HOMOLOGADO OU PERICIAL`** · `OBSERVAÇÕES` · **`Quem se habilitou`** · **`Quando`** ·
`HONORARIOS` · `VALOR LIQUIDO RECLAMANTE`

**`HOMOLOGADO OU PERICIAL` guarda um valor em R$**, não um sim/não — é o valor
homologado/apurado da execução, e as abas estão **ordenadas por ele em ordem decrescente**.
A operação é explicitamente priorizada por valor: os casos de maior execução são chamados
primeiro. Uma aba inteira só tem `ROUBADO` — é o registro de perdas, com `Quem se habilitou`
e `Quando`.

### 3.4 `Acompanhamento Iniciais - Prescrição` (em `CONTROLE INICIAIS - PRESCRIÇÃO`)

`CLIENTE` · **`VIGÊNCIA CONTRATUAL`** (admissão–demissão) · **`PRESCRIÇÃO`** (a data
limite) · **`STATUS`** · `DATA DISTRIBUIÇÃO` · `Nº processo` · **`Audiência`**

`STATUS`: `Protocolado` · `Pendente` · `Correção` · `Fazendo` · `Aguardar documentos` ·
`Cancelado` · `Dr. [nome] que fará` · `Esperando a dispensa`

O campo `Audiência` guarda **data + hora + modalidade** em texto livre:
`Presencial`, `Telepresencial`, `Videoconferência`, `Ainda não designada`,
**`Ainda não designada - Juízo 100% Digital`**.

Quando o contrato ainda está aberto, a coluna `PRESCRIÇÃO` recebe **um motivo em vez de
uma data**: `Rescisão Indireta`, `Esperando a dispensa`. Esse é o caso em que o relógio
ainda não começou a correr — e é uma regra de negócio, não um campo vazio.

### 3.5 Outras planilhas que apareceram

`DIVISÃO DAS EMPRESAS / ADVS` — mapa `ADVOGADO(A) → EMPRESAS`, ~65 linhas, com o aviso
"AS EMPRESAS ESTÃO EM ORDEM ALFABÉTICA". **A carteira é dividida por reclamada, não por
cliente.** Quatro advogados/duplas cobrem todas as empresas.
`CONTROLE SUSTENTAÇÃO ORAL` (2022 e 2025), `PROCESSOS ANDREIA`, `EXECUÇÕES BRUNA`,
`Raphael Controle de Clientes.xlsx`, `CONTROLE HOME OFFICE` — controles pessoais,
um por pessoa, com o nome da pessoa no título.

---

## 4. O roteiro de entrevista

Existem **duas** versões vivas, e elas não são iguais.

### 4.1 A versão .docx (`MODELO DE ENTREVISTA ATUALIZADO`) — a completa

**Cabeçalho:** ENTREVISTADOR · DATA · CLIENTE · RECLAMADA · DATA ADMISSÃO ·
DATA DEMISSÃO · FUNÇÃO · REMUNERAÇÃO · **ÚLTIMO LOCAL DE TRABALHO**

**Motivo do desligamento** (radio): Sem justa causa · Pedido de Demissão · Acordo ·
Rescisão Indireta · Justa Causa (+ campo Motivo)

**As 29 perguntas numeradas:**

1. Salário por fora? → Valor · Forma de pgto. · **Tem extratos?**
2. Trabalhou sem registro? → Período
3. Desvio/acúmulo de funções? → *"MOTORISTA (qual carro costumava dirigir?)"* · Quais
4. Escala: `6x1` `12x36` `5x2` `Outras` → Horários · Sábados/Domingos/Feriados
   (`TODOS`/`ALGUNS`/`NÃO` cada) · **Tem fotos e vídeos das horas extras?** ·
   **Tem prints de grupos de WhatsApp com superiores fazendo cobranças?** ·
   Horário de trabalho
5. Registrava o início corretamente? → Motivo
6. Registrava a saída corretamente? → Motivo
   — **bloco EXCLUSIVO PARA ELETRICISTAS**: atividades na base/ponto de encontro?
   tinha que ir à base na entrada? e na saída?
10. Realizava horário de almoço/janta? → Tempo
10*. Tinha fiscalização do intervalo? → Como? *(numeração duplicada no original)*
11. Tinha controle de ponto?
12. Tipo: `BIOMETRIA` `APP` `MANUAL` `FACIAL`
13. Conferia e assinava todo mês? → Motivo de não assinar
14/15. Tinha banco de horas? / Usufruía do banco de horas?
15*. Empresa forneceu uniforme/EPI? → uso `OBRIGATÓRIO`/`FACULTATIVO` · O que forneciam?
16. Adicional de insalubridade?
17. Adicional de periculosidade?
18. Adicional noturno?
19. Equiparação salarial? → Desde ___ · **PARADIGMA** · Salário do paradigma ·
    **Paradigma possui curso superior?**
20. Férias vencidas? → Períodos
21. Trabalhou (vendeu) nas férias? → Períodos
22. Recebeu todas as verbas rescisórias?
23. FGTS depositado corretamente?
24. Descontos em holerites e/ou TRCT? → Quais?
25. **Danos morais** (humilhações, acusações, xingamentos, condições de trabalho,
    assédios) → Quem fazia · Setor · Fatos
26. Doença do trabalho ou acidente? → Tem exames? · **Abriu CAT?** · Estabilidade? ·
    Afastamento?
27. Estava protegido por estabilidade? (gestação; licença-maternidade; vias de
    aposentadoria; afastamento por acidente/doença ocupacional) → Motivo · Período
29. Tem algo que não foi perguntado? → Observações gerais

**Bloco aprofundado DOENÇA OCUPACIONAL / ACIDENTE DE TRABALHO** (perguntas abertas):
- *Doença*: diagnóstico · quando começaram os sintomas · surgiram/pioraram no trabalho ·
  o médico relacionou com o trabalho · já tinha antes · atividades exigiam esforço,
  repetição ou postura forçada · houve afastamento e por quanto tempo
- *Acidente*: houve acidente de trabalho ou de trajeto e em que data · como ocorreu ·
  havia testemunhas · a empresa emitiu CAT · houve atendimento médico imediato e onde
- *INSS e contrato*: afastamento maior que 15 dias · benefício **`B31`** ou **`B91`** ·
  após o afastamento a empresa `Readaptou` / `Manteve na mesma função` / `Demitiu`
- *Consequências*: ficou com sequela ou limitação permanente · consegue exercer a mesma
  função hoje

**Bloco TESTEMUNHAS, repetido 2×** (Testemunha 1 e 2), cada uma com:
Nome · Tel. · CPF · RG · Endereço · Admissão · Demissão · Função · **Jornada** ·
**Processo nº** · **Depoimento**

### 4.2 A versão Google Forms (`ENTREVISTA - Universal` → `ENTREVISTA-(respostas)`)

Mais curta, autoatendida pelo cliente, com **upload de documentos** e **automação**.
Colunas da planilha de respostas (= campos do formulário):

Carimbo de data/hora · Nome Completo · Nome da Empresa · Data de Admissão ·
Data de Demissão · Qual sua Função? · **Setor** · Valor do último salário informado na
CTPS/Holerite · **Endereço da Empresa** · Motivo do Desligamento · Explique o motivo da
sua saída · Trabalhou sem registro? / qual período · Recebia salário por fora? / qual valor
/ tem extratos bancários · Tinha controle de ponto? / qual tipo · **Descreva os problemas
no seu cartão de ponto** · **Era chamado para trabalhar fora do expediente?** ·
Qual sua escala · **Qual horário você realmente fazia (NÃO O DO CONTRATO)** ·
Conseguia fazer horário de almoço · Sábados/Domingos/Feriados + horários ·
A empresa forneceu EPI · adicional de insalubridade / noturno / periculosidade ·
Tem algo que não foi perguntado · Endereço de e-mail

**Uploads:** Carteira de trabalho · TRCT · Holerites/Recibos · Cartão de ponto ·
**Provas (Vídeos; Fotos; Prints)** · Extrato de FGTS · CNH ou RG

**Colunas de processamento acrescentadas depois:**
**`Pontuação`** · **`STATUS`** (`Concluído`) · **`Link do Documento formatado`**
(aponta para o Google Doc `ENTREVISTA | [cliente]` gerado) · **`Inicial`** (`Feita`) ·
**`AUTOMACAO`** (`PASSOU`)

Já existe, portanto, um pipeline: **formulário → documento formatado → triagem com nota →
inicial**. `[CONFIRMAR: como a "Pontuação" é calculada, e o que "PASSOU" reprova.]`

Há também um roteiro especializado (`Modelo - ENTREVISTA - ELETRICISTA`) e uma pasta
`INFORMAÇÕES MOTORISTA DE ÔNIBUS` — **o roteiro varia por categoria profissional**, e as
duas categorias que já ganharam variante própria são eletricista e motorista de ônibus
(exatamente as duas que também têm pasta de CCT própria).

---

## 5. A operação de revogação

**O que é.** O escritório passou por uma cisão. A planilha `DIVISÃO DAS EMPRESAS / ADVS`
mostra a carteira dividida entre quatro advogados/duplas; hoje três desses nomes aparecem
nas planilhas de revogação como **a parte adversa que se habilita nos processos**. A
operação de revogação é a disputa por essa carteira, **nos dois sentidos**.

**O documento central.** `Termo Revogação.docx` é um template com merge fields
(`{{Nome}}`, `{{cpf}}`, `{{rg}}`, `{{estado civil}}`, `{{cidade}}`, `{{data assinatura}}`)
e contém **duas peças no mesmo arquivo**:

1. **TERMO DE REVOGAÇÃO DE PODERES** — revoga nominalmente os poderes de dois advogados
   (nomes e números de OAB fixos no template), transcreve a cláusula de poderes revogada,
   e lista **até três números de processo** (`{{n° do processo_1..3}}`).
2. **PROCURAÇÃO** nova, outorgando ao sócio GGV, com endereço e OAB.

`Apenas Revogação.docx` é a variante **sem** a procuração — para o cliente que quer sair do
outro escritório mas ainda não decidiu ficar com a GGV.

**A ordem observada:**

1. **Selecionar** — a lista sai ordenada por valor da execução (`EXECUÇÕES`), não por
   ordem cronológica.
2. **Levantar** — antes de ligar, preenche-se fase, status, valor do cálculo (da reclamada
   e do reclamante), sucumbência, honorários periciais e endereço.
3. **Atribuir** — `RESPONSÁVEL` (o advogado) e `RÉSPONSÁVEL PELO CONTATO` (quem liga) são
   pessoas diferentes.
4. **Contatar** — por WhatsApp, com `DATA DO CONTATO`. Cada tentativa vira uma linha de
   texto no `OBS:` com data e as iniciais de quem tentou. Casos com 4–6 tentativas
   registradas ao longo de meses são comuns.
5. **Enviar o link** — ZapSign. Estados: `LINK ENVIADO` → `LINK EM CURSO` → `ASSINADO`.
6. **Confirmar identidade** — a coluna `FOTO` registra se se tem `RG` ou `CNH`.
7. **Protocolar** — o termo assinado vira `Pet. Termo de Revogação de Poderes -
   [cliente] x [reclamada]`, guardada em `TERMOS DE REVOGAÇÃO PARA SUBIR`; o estado
   passa a `PROTOCOLADO`.
8. **Perder** — se o outro lado se habilitou primeiro, o estado vira `ROUBADO` e
   registra-se `Quem se habilitou` e `Quando`. Existe o caminho inverso (`RECUPERADO`,
   `VOLTOU`), e existe `NÃO CHAMAR` para o cliente que já disse não.

**Motivos observados para NÃO chamar** (regras de negócio implícitas): honorários já
recebidos; última parcela do acordo já paga; caso em recuperação judicial onde a
habilitação não compensa; cliente que declarou que segue com o outro advogado.

**Um ritual que o Drive registra:** o procedimento manda, após o contrato assinado
presencialmente, **tirar foto do cliente com o advogado e/ou captador** — uma cópia
instantânea fica com o cliente, e a digital vai para `FOTOS CLIENTES P/ MURAL`. É um
mecanismo de vínculo, e provavelmente uma resposta à mesma disputa.

---

## 6. O que isso muda ou acrescenta ao modelo do sistema

O modelo atual (`clientes, processos, audiencias, prazos, decisoes, recursos, calculos,
acordos, recebimentos, repasses, incidentes, testemunhas, empresas, pendencias, documentos`)
cobre bem a espinha judicial. O que o acervo mostra e o modelo ainda não tem:

**Acrescentar**

1. **`empresas` precisa ser o eixo, não um apêndice.** O Drive inteiro é indexado por
   reclamada; a carteira dos advogados é dividida por reclamada; as CCTs, os estudos e as
   provas societárias (JUCESP, cartão CNPJ) são por reclamada. `empresas` deve ter CNPJ
   como chave (há duas empresas homônimas desambiguadas por CNPJ no nome da pasta),
   `nome_normalizado` além do nome bruto, `segmento`, e **relação empresa↔empresa** para
   grupo econômico / tomador de serviço / consórcio — a inicial pede solidariedade e
   subsidiariedade, então a co-ré é dado, não texto.

2. **Uma tabela de `revogacoes` (ou `disputa_patrocinio`).** Não cabe em `processos`:
   tem funil próprio (`MENSAGEM ENVIADA → LINK ENVIADO → LINK EM CURSO → ASSINADO →
   PROTOCOLADO`, com saídas `ROUBADO`, `RECUPERADO`, `VOLTOU`, `NÃO CHAMAR`, `ARQUIVADO`),
   dono próprio (`responsavel_contato` ≠ `responsavel_processo`), histórico de tentativas
   de contato, e um resultado adverso (`quem_se_habilitou`, `quando_habilitou`) que é
   informação sobre a **parte contrária**, não sobre o processo.

3. **`contatos` / tentativas de contato como linhas, não como texto.** Hoje 4–6 tentativas
   viram um parágrafo numa célula `OBS:`, com data e iniciais soltas. É o dado mais
   apagável do acervo e o mais usado na operação.

4. **`prescricao` no processo, com motivo.** A planilha de iniciais guarda
   `VIGÊNCIA CONTRATUAL` → `PRESCRIÇÃO`, e quando o contrato está aberto guarda um
   **motivo** no lugar da data (`Rescisão Indireta`, `Esperando a dispensa`). O sistema
   precisa de `data_limite` **e** `motivo_sem_data` — vazio não distingue "não calculei"
   de "o relógio ainda não começou".

5. **Duas dimensões de andamento, não uma.** `fase_processual` (Conhecimento · Recursal ·
   Execução Provisória · Execução Definitiva · Arquivado) **e** `status_trabalho`
   (Aguardando audiência · Aguardando sentença · 2º Grau · TST · Acordo · Acordo cumprido ·
   Execução · Extinta a execução · Parcelamento CPC · Finalizado com sucesso ·
   Arquivado definitivamente). Elas discordam legitimamente na planilha.

6. **`audiencias.modalidade`** com o vocabulário real: `Presencial`, `Telepresencial`,
   `Videoconferência`, `Juízo 100% Digital`, `Ainda não designada`. E note que
   "Ainda não designada - Juízo 100% Digital" é uma **combinação**, não um valor —
   modalidade e designação são campos separados.

7. **`entrevistas` como entidade, com variante por categoria.** O roteiro varia
   (universal / eletricista / motorista de ônibus) e tem blocos condicionais
   (equiparação → paradigma; doença ocupacional → CAT, B31/B91, sequela). Ver §7 abaixo.

8. **`documentos` precisa de um `tipo` fechado e de `ordem_juntada`.** Os arquivos do
   `Protocolo` vêm numerados no nome porque a ordem importa. E vale ter
   `documento.origem`: `cliente` (CTPS, RG, holerite) · `reclamada` (JUCESP, cartão CNPJ) ·
   `sindical` (CCT, por **vigência**, e um caso costuma precisar de duas ou três) ·
   `gerado` (inicial, manifestação, relatório).

9. **`provas` separado de `documentos`.** Áudio de conversa, print de grupo de WhatsApp,
   foto/vídeo de hora extra são o que sustenta jornada e assédio, e a entrevista já pergunta
   por eles explicitamente. Merecem `tipo_prova` e `pedido_que_sustenta`.

10. **Captação como parte do modelo, não do CRM externo.** `captador`, `fonte_captacao`
    (`Projeto Puxada`, `Projeto Currículos`, `Indicação`, `Testemunha`),
    `forma_assinatura`, `data_assinatura_contrato`. E há `RECIBOS PAGAMENTOS` de captador —
    ou seja, **repasse a captador**, que é diferente de repasse a sócio.

11. **`testemunhas` já existe — mas o acervo pede mais.** O roteiro guarda por testemunha:
    admissão, demissão, função, **jornada**, **processo nº próprio** e depoimento.
    Uma testemunha **tem processo dela** e às vezes **vira cliente** (`FONTE_CAPTACAO:
    Testemunha`). São dois vínculos distintos ao mesmo indivíduo. Há um `SETOR DE
    TESTEMUNHAS` com modelos de rol e carta de intimação, e o relatório de audiência traz
    a **modalidade de intimação** como escolha jurídica (art. 825 CLT · art. 852-H §3º ·
    Provimento GP/CR 13/2006 · art. 455 CPC).

12. **`pedidos` do processo como lista fechada.** O modelo de relatório de audiência traz
    18 pedidos nomeados (reversão do pedido de demissão/rescisão indireta ·
    responsabilidade solidária — grupo econômico · responsabilidade subsidiária ·
    unicidade contratual · multas dos arts. 467 e 477 · obrigação de fazer — seguro-
    desemprego e FGTS · domingos e feriados · intervalo intrajornada · interjornada ·
    acúmulo de função · dano moral/assédio · descontos indevidos · doença ocupacional/
    acidente · danos morais por doença ocupacional · indenização por estabilidade ·
    dano estético · vale-refeição). Isso é vocabulário pronto, e é o que liga entrevista →
    inicial → réplica → sentença.

13. **`substabelecimentos`.** Aparece em quase toda pasta de caso, com distinção entre
    **advogado interno** e **correspondente**. Quem esteve na audiência é uma pergunta que
    a operação faz.

14. **`desistencias`** — existe `RELATÓRIO DE DESISTÊNCIA` como tipo próprio; é um
    encerramento diferente de "perdido" e diferente de "roubado".

15. **Checklist de réplica como dado.** As 31 linhas do `Checklist para réplica trabalhista`
    são uma tabela `Nº · item · conferido · observações` — é uma **pendência estruturada
    por processo**, não um documento. Casa direto com `pendencias`.

**Corrigir / vigiar**

16. **A conciliação Drive↔cadastro já é um problema medido**, não hipotético:
    361 de 872 clientes captados sem `LINK_PASTA_DRIVE`. O sistema deve guardar o
    `link_pasta_drive` no cliente/processo e ter uma tela de divergência, no espírito de
    `/conferencias`.

17. **Nome de pasta é a chave hoje, e ela quebra.** Existem pastas `Untitled`, duplicatas
    exatas de empresa, variantes de grafia da mesma reclamada e erros de digitação.
    Qualquer indexador que case por nome vai errar; casar por **CNPJ da reclamada + CPF do
    cliente + CNJ** é o caminho, com o nome como rótulo.

18. **O trabalho recém-feito fica solto na raiz.** Os relatórios de audiência/conciliação
    dos últimos dias estão na raiz do `#1-JURIDICO`, fora da pasta do caso, com o CNJ no
    título. Um leitor que só varra `PROCESSOS/` perde os documentos mais recentes.

19. **`ARQUIVO MORTO` existe e não é "encerrado".** É outra dimensão (onde o papel está),
    e há `PROCESSOS GERAIS`, `PROCESSOS CIVIL` e `NILSE` convivendo com `PROCESSOS` —
    mais de um lugar legítimo para um caso.

20. **A carteira é por empresa.** A distribuição automática de tarefa por carga (a regra
    `DISTRIBUIR_FILA` do sistema previdenciário) contraria o que existe aqui: quem pega o
    caso é quem tem aquela reclamada. Se a distribuição for portada, precisa respeitar
    `empresa → responsável` antes de olhar carga.

---

## Resumo — os 5 pontos mais acionáveis para o portal

1. **Ponha a reclamada no centro.** `empresas` com CNPJ, nome normalizado, segmento e
   relação empresa↔empresa (grupo econômico / tomador / consórcio); a carteira dos
   advogados e o acervo inteiro do Drive já são indexados por ela, e o caso vive em
   `PROCESSOS/[EMPRESA]/[CLIENTE X RECLAMADA]/`.
2. **Modele a revogação como operação própria**, com funil
   (`mensagem → link → assinado → protocolado`), saídas `ROUBADO`/`RECUPERADO`/`NÃO CHAMAR`,
   dono do contato separado do dono do caso, e **cada tentativa de contato como linha** —
   hoje isso é um parágrafo dentro de uma célula.
3. **A tela de entrevista já tem esquema pronto**: 29 perguntas + blocos condicionais
   (equiparação → paradigma; doença/acidente → CAT, B31/B91, sequela), variantes por
   categoria (universal, eletricista, motorista de ônibus), 7 uploads de documento e 2
   blocos de testemunha com jornada e processo próprio. O formulário Google já gera doc
   formatado, `Pontuação` e flag de automação — vale portar o pipeline inteiro, não só o
   formulário.
4. **Guarde duas dimensões de andamento** (`fase_processual` × `status_trabalho`) e a
   **prescrição com motivo** — quando o contrato está aberto o campo não é vazio, é
   `Rescisão Indireta` ou `Esperando a dispensa`.
5. **Comece pela conciliação Drive↔cadastro**, que o escritório já mediu e não resolveu:
   361 dos 872 clientes captados não têm pasta ligada. Guarde `link_pasta_drive`, case por
   CNPJ/CPF/CNJ em vez de por nome de pasta, e trate `Untitled` e as duplicatas de empresa
   como divergência a resolver, não como ruído.
