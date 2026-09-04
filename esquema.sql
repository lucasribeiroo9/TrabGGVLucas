-- =====================================================================
-- Sistema Operacional GGV Trabalhista — esquema relacional (Postgres)
--
-- Dialeto: Postgres direto (Supabase, projeto PrevGGVLucas, esquema `public`).
-- O Prev nasceu em SQLite e foi traduzido; aqui o banco já nasce onde vai
-- viver. O que se herda do Prev é a FORMA, não o dialeto:
--
--   1. Data em TEXT ISO ('YYYY-MM-DD' / 'YYYY-MM-DD HH:MM:SS'). É assim que
--      `banco.py` compara e é assim que a governança compara. Onde precisa de
--      conta de calendário, o SQL faz `coluna::date` na hora.
--   2. Dinheiro em CENTAVOS, inteiro. Nada de float para dinheiro: R$ 0,01
--      perdido por arredondamento em 3.722 processos é um erro que ninguém
--      encontra depois.
--   3. Vocabulário que cresce (empresa, pessoa, tipo de prazo) é TABELA.
--      Estado com semântica fixa é CHECK — assim não nasce opção nova por
--      digitação, que é exatamente a doença da base de origem (36 opções em
--      STATUS EXECUÇÃO, 41 em TURMA).
--   4. PERDA ZERO: toda tabela migrada guarda `airtable_record_id`,
--      `airtable_tabela` e `airtable_bruto jsonb` com o registro ORIGINAL
--      INTEIRO. Perder campo é falha, não simplificação.
--   5. Todo link do Airtable vira chave estrangeira de verdade.
--   6. O que a migração não soube traduzir não vira palpite: vira linha em
--      `conferencias`, com o valor de cada lado e o trecho de prova.
--
-- ORDEM DE APLICAÇÃO:  esquema.sql  →  governanca.sql
-- `governanca.sql` cria `fluxos`, `fluxo_etapas`, `fluxo_transicoes`,
-- `historico_etapas` e `prazo_tipos`, e pendura os gatilhos nas tabelas
-- daqui. Este arquivo NÃO recria nenhuma dessas cinco. A única exceção é a
-- FK `historico_etapas.pessoa_id → pessoas(id)`, que a governança deixou
-- anotada para o esquema fechar (ver o fim deste arquivo).
--
-- RLS: ligada em TODA tabela, com política única para o papel do app
-- (`app_trab`). Sem política para `anon`/`authenticated` — nada do escritório
-- é exposto pela API pública do Supabase.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. O papel do app. RLS sem papel é RLS que tranca todo mundo, inclusive
--    o sistema. `app_trab` é NOLOGIN: quem loga é o usuário do Postgres que
--    o `banco.py` usa, e é a esse usuário que se concede `app_trab`.
-- ---------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_trab') THEN
    CREATE ROLE app_trab NOLOGIN;
  END IF;
END $$;

-- ---------------------------------------------------------------------
-- 1. GENTE: a equipe (FUNCIONARIOS) e quem entra no sistema
-- ---------------------------------------------------------------------

-- Os 72 do Airtable, 35 ativos. `nome_norm` casa grafia ("Dr. Vitor Esteves"
-- e "Vitor Esteves" são a mesma pessoa quando o link do Airtable falha).
CREATE TABLE pessoas (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome              TEXT NOT NULL,
    nome_norm         TEXT NOT NULL,
    ativo             BOOLEAN NOT NULL DEFAULT true,
    -- Setor não existe na origem: sai dos papéis (pessoa_papeis) e do
    -- ajuste à mão em equipe.py. [CONFIRMAR pergunta 30: a lista fechada
    -- de setores e quem chefia cada um.]
    setor             TEXT,
    supervisor_id     BIGINT REFERENCES pessoas(id),
    -- teto de tarefas simultâneas em "Agora"; teto, não meta
    limite_agora      INTEGER NOT NULL DEFAULT 5 CHECK (limite_agora BETWEEN 1 AND 12),
    ntfy_topic        TEXT,                       -- push do n8n, um por pessoa
    ntfy_ativo        BOOLEAN,
    observacao        TEXT,
    airtable_record_id TEXT,
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE UNIQUE INDEX ix_pessoas_norm ON pessoas(nome_norm);
CREATE UNIQUE INDEX ix_pessoas_airtable ON pessoas(airtable_record_id) WHERE airtable_record_id IS NOT NULL;

-- FUNCOES é multipleSelects: uma pessoa é advogada E captadora. Vira linha.
CREATE TABLE pessoa_papeis (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pessoa_id   BIGINT NOT NULL REFERENCES pessoas(id) ON DELETE CASCADE,
    papel       TEXT NOT NULL CHECK (papel IN (
                  'ADVOGADO','CAPTADOR','ENTREVISTADOR','RESPONSAVEL_INICIAL','GESTOR',
                  'JURIDICO','ADMINISTRATIVO','DOCUMENTACAO','FINANCEIRO','TI',
                  'CORRESPONDENTE','TESTEMUNHAS','ATENDIMENTO','PUBLICACAO','CEO','OUTRO')),
    UNIQUE (pessoa_id, papel)
);

-- Quem entra no sistema. A senha nasce provisória e é mostrada uma vez só
-- (auth.py do Prev, reaproveitado). O papel aqui é o que a governança lê
-- em `fluxo_transicoes.papel`.
CREATE TABLE usuarios (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pessoa_id      BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    email          TEXT NOT NULL UNIQUE,
    senha_hash     TEXT NOT NULL,
    papel          TEXT NOT NULL DEFAULT 'ADVOGADO'
                   CHECK (papel IN ('ADVOGADO','GESTOR','DIRECAO')),
    ativo          BOOLEAN NOT NULL DEFAULT true,
    trocar_senha   BOOLEAN NOT NULL DEFAULT true,
    ultimo_acesso  TEXT,
    criado_em      TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);

-- ---------------------------------------------------------------------
-- 2. AS RECLAMADAS
-- ---------------------------------------------------------------------

-- 1.103 no Airtable. Os atributos de RISCO DE RECEBIMENTO (status, histórico
-- de pagamento, bens) moram aqui, não no processo — o processo só lê. Na
-- origem estavam nos dois lugares e divergiam; a migração escreve aqui e
-- abre `conferencias` quando os dois lados discordam.
CREATE TABLE empresas (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome              TEXT NOT NULL,
    nome_norm         TEXT NOT NULL,
    cnpj              TEXT,                       -- só dígitos
    razao_social      TEXT,
    segmento          TEXT,
    situacao          TEXT CHECK (situacao IS NULL OR situacao IN ('ATIVA','INATIVA','EM_RECUPERACAO')),
    hist_pagamento    TEXT CHECK (hist_pagamento IS NULL OR hist_pagamento IN ('BOA','RUIM','PESSIMA')),
    bens_identificados BOOLEAN,
    ggv_record_key    TEXT,                       -- chave do script de deduplicação da origem
    observacao        TEXT,
    airtable_record_id TEXT,
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_empresas_norm ON empresas(nome_norm);
CREATE INDEX ix_empresas_cnpj ON empresas(cnpj) WHERE cnpj IS NOT NULL;
CREATE UNIQUE INDEX ix_empresas_airtable ON empresas(airtable_record_id) WHERE airtable_record_id IS NOT NULL;

-- O banco de teses POR RECLAMADA. É o `teses/*.md` do Prev, só que no
-- trabalhista a tese repete por empregador: mesma CCT, mesmo controle de
-- ponto, mesmos holerites.
CREATE TABLE fragilidades (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    empresa_id        BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    achado            TEXT NOT NULL,
    eixo              TEXT,                       -- lista aberta: o eixo nasce da leitura dos autos
    forca             TEXT CHECK (forca IS NULL OR forca IN (
                        'PROVA_DOCUMENTAL_DA_RE','CONFISSAO_EM_DEPOIMENTO','ARITMETICA_VERIFICAVEL',
                        'TESE_A_CONSTRUIR','DEPENDE_DE_PROVA_ORAL')),
    situacao          TEXT CHECK (situacao IS NULL OR situacao IN (
                        'INEDITA','ACOLHIDA','ACOLHIDA_EM_PARTE','REJEITADA','EM_JULGAMENTO')),
    descricao         TEXT,
    fundamento        TEXT,
    prova             TEXT,
    como_explorar     TEXT,
    doc_a_requerer    TEXT,
    processos_texto   TEXT,                       -- os autos onde apareceu, como texto da origem
    periodo           TEXT,
    valor_estimado_centavos BIGINT,
    atualizado_em     TEXT,
    airtable_record_id TEXT,
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_fragilidades_empresa ON fragilidades(empresa_id);

-- ---------------------------------------------------------------------
-- 3. O CLIENTE — o funil pré-processual (fluxo 1)
--
-- Uma ficha desde o lead. O Airtable só recebe a pessoa DEPOIS de assinar
-- (99% com DATA DE ASSINATURA): a migração nasce com o funil truncado, e a
-- etapa LEAD só passa a existir com a entrada pelo portal (resposta 5 do
-- Lucas). A tela precisa dizer isso, senão a conversão do primeiro mês mente.
-- ---------------------------------------------------------------------
CREATE TABLE clientes (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status            TEXT NOT NULL DEFAULT 'LEAD',    -- fluxo CLIENTE (governanca.sql)
    nome              TEXT NOT NULL,
    nome_norm         TEXT NOT NULL,
    cpf               TEXT,                            -- só dígitos
    cpf_valido        BOOLEAN NOT NULL DEFAULT false,
    telefone          TEXT,
    email             TEXT,
    data_nascimento   TEXT,
    empresa_id        BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    funcao            TEXT,

    -- O contrato: é ele que separa lead de cliente (gate `contrato_assinado`)
    data_assinatura_contrato TEXT,
    contrato_assinado_doc_id BIGINT,                   -- FK para documentos, ligada no fim

    -- O relógio da prescrição bienal (CF art. 7º XXIX; CLT art. 11)
    contrato_vivo     BOOLEAN NOT NULL DEFAULT false,  -- ainda trabalha: não há prazo correndo
    data_demissao     TEXT,                            -- ISO, normalizada
    data_demissao_original TEXT,                       -- o texto como estava (6 formatos)
    dispensa_prescricao_motivo TEXT,                   -- sem isso o banco recusa abrir processo

    rescisao_modalidade TEXT CHECK (rescisao_modalidade IS NULL OR rescisao_modalidade IN (
                        'SEM_JUSTA_CAUSA','JUSTA_CAUSA','PEDIDO_DEMISSAO','RESCISAO_INDIRETA',
                        'CONTRATO_VIVO','ACORDO_484A','TERMINO_CONTRATO','OUTRA')),
    rescisao_original TEXT,                            -- texto livre da origem, sempre preservado

    -- De onde veio o lead: numerador e denominador da conversão que o
    -- escritório mede (resposta 5). Canal fechado, campanha aberta.
    canal             TEXT CHECK (canal IS NULL OR canal IN (
                        'INDICACAO','SITE','FACEBOOK','INSTAGRAM','DISPARO','PROJETO','OUTRO')),
    campanha          TEXT,
    fonte_original    TEXT,

    captador_id       BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    entrevistador_id  BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    responsavel_id    BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,  -- RESPONSAVEL INICIAL

    entrevista_em     TEXT,                            -- gate `entrevista_registrada`
    entrevista_resumo TEXT,
    contatos_entrevista INTEGER NOT NULL DEFAULT 0,    -- PRIMEIRO/SEGUNDO/TERCEIRO CONTATO virou contador

    pericia_medica    BOOLEAN NOT NULL DEFAULT false,
    pericia_tecnica   BOOLEAN NOT NULL DEFAULT false,
    -- STATUS DOCUMENTAÇÃO = TRATAMENTO: 5 registros, significado desconhecido
    -- [CONFIRMAR: é trabalho interno de tratamento de documento?]
    em_tratamento     BOOLEAN NOT NULL DEFAULT false,
    -- o checkbox humano que disparava a automação PRÉ → PROCESSUAL
    passar_de_fase    BOOLEAN NOT NULL DEFAULT false,

    drive_url         TEXT,
    astrea_url        TEXT,                            -- [CONFIRMAR: o Astrea continua em uso?]
    motivo            TEXT,                            -- por que cancelou / prescreveu
    origem_cadastro   TEXT NOT NULL DEFAULT 'PRE_PROCESSUAL'
                      CHECK (origem_cadastro IN ('PRE_PROCESSUAL','PROCESSO','PORTAL')),

    airtable_record_id TEXT,
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,
    atualizado_em     TEXT,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_clientes_nome   ON clientes(nome_norm);
CREATE INDEX ix_clientes_cpf    ON clientes(cpf) WHERE cpf IS NOT NULL;
CREATE INDEX ix_clientes_status ON clientes(status);
CREATE UNIQUE INDEX ix_clientes_airtable ON clientes(airtable_record_id) WHERE airtable_record_id IS NOT NULL;

-- ---------------------------------------------------------------------
-- 4. PENDÊNCIAS — uma tabela só, COM TIPO (resposta 7 do Lucas)
--
-- O escritório tem pendência de documento, de marcar entrevista, de fazer
-- petição, de marcar reunião pré-audiência e de fazer réplica. Não é um
-- campo de documentos: é uma lista de coisas que faltam, de naturezas
-- diferentes. Só o tipo DOCUMENTO trava etapa (gate
-- `documentos_obrigatorios`); os outros viram tarefa com dono, que é o que
-- já são na prática. Isso explica as 172 fichas "COMPLETA" com pendência
-- aberta: a pendência não era de documento.
--
-- A pendência pertence ao cliente OU ao processo (réplica e reunião
-- pré-audiência são do processo).
-- ---------------------------------------------------------------------
CREATE TABLE pendencias (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    processo_id       BIGINT,                          -- FK ligada depois de processos
    -- CADASTRO: um dado da ficha que a origem não tinha (data de nascimento da
    -- ficha criada dos autos, por exemplo). Não trava etapa; é o que falta
    -- preencher, com dono — e não uma conferência genérica.
    tipo              TEXT NOT NULL CHECK (tipo IN (
                        'DOCUMENTO','ENTREVISTA','PETICAO','REUNIAO_PRE_AUDIENCIA','REPLICA',
                        'CADASTRO','OUTRO')),
    -- quando tipo=DOCUMENTO: qual documento. Lista fechada porque é a lista
    -- que o gate lê; HOLERITE e HOLERITES eram a mesma coisa na origem.
    -- CONTRATO: a ficha existe e não há data de assinatura — o contrato de
    -- honorários não está registrado.
    documento_tipo    TEXT CHECK (documento_tipo IS NULL OR documento_tipo IN (
                        'CNH_RG','CTPS','TRCT','DOCS_MEDICOS','PROVAS','FGTS','HOLERITES','PIS',
                        'CONTRATO','OUTRO')),
    descricao         TEXT,
    obrigatorio       BOOLEAN NOT NULL DEFAULT true,
    responsavel_id    BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    grupo             TEXT,
    prazo             TEXT,
    solicitado_em     TEXT,
    recebido_em       TEXT,                            -- resolvida
    dispensado_motivo TEXT,                            -- dispensada, com motivo escrito
    documento_id      BIGINT,                          -- FK ligada depois de documentos
    -- A origem marcava PENDENCIAS sem dizer se era "pedido" ou "falta"
    -- [CONFIRMAR pergunta 7]. A migração grava o que leu e diz aqui de onde veio.
    origem            TEXT NOT NULL DEFAULT 'MIGRACAO'
                      CHECK (origem IN ('MIGRACAO','SISTEMA','MANUAL','AUTOMACAO')),
    airtable_record_id TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),
    CHECK (cliente_id IS NOT NULL OR processo_id IS NOT NULL)
);
CREATE INDEX ix_pend_cliente ON pendencias(cliente_id, tipo) WHERE recebido_em IS NULL AND dispensado_motivo IS NULL;
CREATE INDEX ix_pend_processo ON pendencias(processo_id, tipo) WHERE recebido_em IS NULL AND dispensado_motivo IS NULL;

-- O contrato com a governança fala em `documentos_pendentes(cliente_id,
-- tipo, obrigatorio, recebido_em, dispensado_motivo)`. A resposta 7 do Lucas
-- veio depois e vale mais: a tabela é `pendencias`, com tipo. A visão abaixo
-- entrega ao gate exatamente o que ele espera, sem duas tabelas para a mesma
-- coisa — e sem que o gate precise saber que os outros tipos existem.
CREATE VIEW documentos_pendentes AS
SELECT id, cliente_id, processo_id, documento_tipo AS tipo, obrigatorio,
       recebido_em, dispensado_motivo, prazo, responsavel_id
FROM pendencias WHERE tipo = 'DOCUMENTO';

-- ---------------------------------------------------------------------
-- 5. O PROCESSO (fluxo 2)
--
-- Base: a CÓPIA DA PROCESSUAL (3.722), que tem o acervo inteiro, os campos
-- do pipeline de leitura dos autos e a fase atualizada. Casado por número
-- CNJ com a PROCESSUAL (2.652), que VENCE nos campos que a equipe edita
-- hoje. Onde as duas divergem em campo relevante, ninguém escolhe em
-- silêncio: abre `conferencias`. Ver docs/de-para.md.
-- ---------------------------------------------------------------------
CREATE TABLE processos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id        BIGINT NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    fase              TEXT NOT NULL DEFAULT 'CONHECIMENTO',   -- fluxo PROCESSO

    -- O número. NÃO é único: a origem tem 8 duplicados na PROCESSUAL e 19 na
    -- CÓPIA, e 106 registros sem número nenhum. Um UNIQUE aqui faria a carga
    -- do passivo falhar em silêncio parcial; o duplicado vira `conferencias`.
    numero_cnj        TEXT,
    numero_cnj_digitos TEXT GENERATED ALWAYS AS (regexp_replace(COALESCE(numero_cnj,''), '\D', '', 'g')) STORED,

    -- A parte como consta nos autos. Fica aqui além de em `clientes` porque
    -- 3.278 processos do passivo não têm ficha pré-processual: o nome dos
    -- autos é o que se tem, e é ele que casa com a publicação do DEJT.
    nome_parte        TEXT,
    cpf_parte         TEXT,
    email_parte       TEXT,
    telefone_parte    TEXT,
    nascimento_parte  TEXT,

    empresa_id        BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    cnpj_reclamada    TEXT,
    razao_social_reclamada TEXT,

    -- Onde tramita
    trt               TEXT,                            -- '2' … normalizado sem 'ª'
    vara              TEXT,
    turma             TEXT,                            -- turma do TRT (texto limpo da CÓPIA)
    cadeira           TEXT,
    relator           TEXT,
    turma_tst         TEXT,
    relator_tst       TEXT,
    arquivo_tst_em    TEXT,                            -- [CONFIRMAR: é data de arquivamento no TST?]
    tel_vara          TEXT,

    -- O que é a ação
    rito              TEXT CHECK (rito IS NULL OR rito IN ('ORDINARIO','SUMARISSIMO','SUMARIO')),
    classe_cnj        TEXT CHECK (classe_cnj IS NULL OR classe_cnj IN ('RT','AT')),
    -- as classes de incidente que a CÓPIA misturou no mesmo campo do rito
    classe_incidente  TEXT CHECK (classe_incidente IS NULL OR classe_incidente IN (
                        'EXECUCAO_PROVISORIA','EXECUCAO_DEFINITIVA','EMBARGOS_DE_TERCEIRO',
                        'RR','AIRR','RRAg','EMBARGOS')),
    valor_causa_centavos BIGINT,
    complexidade      TEXT CHECK (complexidade IS NULL OR complexidade IN ('A','B','C')),
    -- A/B/C sai do valor (C ≤ 150 mil, B ≤ 500 mil, A acima). Quando alguém
    -- decide diferente, a decisão vence e fica escrita [CONFIRMAR pergunta 16].
    complexidade_manual BOOLEAN NOT NULL DEFAULT false,

    distribuicao_em   TEXT,
    ajuizamento_em    TEXT,                            -- campo AÇÃO [CONFIRMAR: difere de DISTRIBUIÇAO?]
    assinatura_em     TEXT,

    advogado_id       BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    captador_id       BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,

    -- A execução é ATRIBUTO com lista fechada, não sub-máquina: ela não é
    -- linear (bens, acordo, alvará e recurso se alternam) e uma máquina de
    -- 16 estados recusaria mudança legítima todo dia. A lista é a limpa da
    -- CÓPIA; a ordem é a de docs/etapa-ou-atributo.md.
    situacao_execucao TEXT CHECK (situacao_execucao IS NULL OR situacao_execucao IN (
                        'AGUARDANDO_TRANSITO','AGUARDANDO_CALCULO','CALCULOS_APRESENTADOS',
                        'AGUARDANDO_PERICIA_CONTABIL','HOMOLOGADO','EM_RECURSO_EXECUCAO',
                        'PESQUISA_PATRIMONIAL','NEGOCIANDO_ACORDO','PARCELAMENTO_916',
                        'AGUARDANDO_ALVARA','RECEBIDO')),
    situacao_execucao_original TEXT,                   -- o que estava escrito antes de traduzir
    numero_cumprse    TEXT,                            -- gate `numero_cumprse`
    transito_em       TEXT,                            -- gate `transito_registrado`

    resultado_final   TEXT CHECK (resultado_final IS NULL OR resultado_final IN (
                        'PROCEDENTE','PARCIALMENTE_PROCEDENTE','IMPROCEDENTE',
                        'ACORDO_CUMPRIDO','EXECUCAO_SATISFEITA','ARQUIVADO',
                        'ARQUIVADO_PROVISORIO','ARQUIVADO_AUSENCIA','EXTINTA_SEM_RESOLUCAO',
                        'DESISTENCIA','SEM_RECEBIMENTO','REDISTRIBUIDO','OUTRO')),
    resultado_texto   TEXT,                            -- o campo RESULTADO, em prosa
    encerrado_em      TEXT,
    -- O arquivo físico/Drive não é fase. A origem (PÓS, STATUS ARQUIVAMENTO)
    -- diz SE a pasta foi arquivada e não diz QUANDO: o fato fica no booleano
    -- e a data só entra quando alguém a registrar — a carga não a inventa.
    arquivado         BOOLEAN,
    arquivado_em      TEXT,

    sucumbencia_percent NUMERIC(6,2),                  -- art. 791-A CLT: 5 a 15%
    -- O cliente vendeu o crédito. STATUS PAGAMENTO = CESSAO DE CREDITOS diz o
    -- fato; a data e o cessionário a origem não tem, e ficam vazios.
    credito_cedido    BOOLEAN NOT NULL DEFAULT false,
    credito_cedido_em TEXT,
    cessionario       TEXT,

    -- Sentido 1 da REVOGAÇÃO: NÓS juntamos a revogação do patrono anterior
    -- do cliente. O sentido 2 (o cliente nos revogou) mora em `incidentes`.
    -- [CONFIRMAR pergunta 20.]
    revogou_patrono_anterior BOOLEAN,
    revogacao_em      TEXT,

    redistribuido_de  BIGINT REFERENCES processos(id) ON DELETE SET NULL,
    sobrestado_motivo TEXT,
    fase_anterior     TEXT,                            -- para onde SOBRESTADO volta

    pericia_medica    BOOLEAN NOT NULL DEFAULT false,
    pericia_tecnica   BOOLEAN NOT NULL DEFAULT false,

    ultima_movimentacao TEXT,                          -- texto do Datajud/AASP
    ultima_movimentacao_em TEXT,
    drive_url         TEXT,
    astrea_url        TEXT,

    -- De qual das duas tabelas veio cada lado, e se houve divergência
    airtable_record_id TEXT,                           -- o da CÓPIA quando existe
    airtable_record_id_processual TEXT,                -- o da PROCESSUAL
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,                          -- {"copia": {...}, "processual": {...}}
    atualizado_em     TEXT,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_processos_cliente ON processos(cliente_id);
CREATE INDEX ix_processos_fase    ON processos(fase);
CREATE INDEX ix_processos_cnj     ON processos(numero_cnj_digitos) WHERE numero_cnj_digitos <> '';
CREATE INDEX ix_processos_empresa ON processos(empresa_id);
CREATE UNIQUE INDEX ix_processos_airtable ON processos(airtable_record_id) WHERE airtable_record_id IS NOT NULL;
CREATE UNIQUE INDEX ix_processos_airtable_proc ON processos(airtable_record_id_processual) WHERE airtable_record_id_processual IS NOT NULL;

ALTER TABLE pendencias ADD CONSTRAINT fk_pend_processo
  FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE;

-- A outra grafia. Nome, VARA, NASCIMENTO e TELEFONE divergem em centenas de
-- casos entre a PROCESSUAL e a CÓPIA. Escolhe-se um valor e guarda-se o
-- outro — jogar fora seria perder o que talvez esteja certo.
CREATE TABLE processo_alias (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    campo       TEXT NOT NULL,
    valor       TEXT NOT NULL,
    origem      TEXT NOT NULL CHECK (origem IN ('PROCESSUAL','COPIA','FALTANTES','PRE_PROCESSUAL')),
    UNIQUE (processo_id, campo, valor)
);

-- ---------------------------------------------------------------------
-- 6. A AGENDA DO PROCESSO: audiência, prazo, perícia
-- ---------------------------------------------------------------------

-- Cada audiência é UMA LINHA. O Airtable guardava só a última e sobrescrevia
-- a anterior — a redesignação apagava a história. Aqui a nova data é linha
-- nova, ligada por `redesignada_de`. Tipo e modalidade são atributos: não
-- mudam o caminho (fluxo 3).
CREATE TABLE audiencias (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    situacao          TEXT NOT NULL DEFAULT 'DESIGNADA',    -- fluxo AUDIENCIA
    data_hora         TEXT,
    tipo              TEXT CHECK (tipo IS NULL OR tipo IN (
                        'INICIAL','INSTRUCAO','UNA','HOMOLOGACAO','CONCILIACAO_EXECUCAO','JULGAMENTO')),
    modalidade        TEXT CHECK (modalidade IS NULL OR modalidade IN ('PRESENCIAL','VIDEO')),
    redesignada_de    BIGINT REFERENCES audiencias(id) ON DELETE SET NULL,

    resultado         TEXT CHECK (resultado IS NULL OR resultado IN (
                        'ACORDO','DEFESA_JUNTADA','INSTRUCAO_ENCERRADA','SENTENCA_DESIGNADA',
                        'ADIADA','SEM_ACORDO','OUTRO')),
    resultado_texto   TEXT,
    -- Ausência do reclamante arquiva (art. 844 CLT) e pode custar custas.
    -- Fica no motivo, não escondida num status: é perda evitável e precisa
    -- ser medida por captador e entrevistador.
    motivo            TEXT CHECK (motivo IS NULL OR motivo IN (
                        'AUSENCIA_RECLAMANTE','AUSENCIA_RECLAMADA','AUSENCIA_ADVOGADO',
                        'JUIZO','ACORDO_PREVIO','DESISTENCIA','OUTRO')),
    motivo_texto      TEXT,

    -- O checklist da preparação. Entra-se em EM_PREPARACAO quando o primeiro
    -- item é feito; a view v_audiencias_sem_preparacao lê estas quatro colunas.
    cliente_orientado_em        TEXT,
    testemunhas_confirmadas_em  TEXT,
    advideo_previsto            BOOLEAN NOT NULL DEFAULT false,
    advideo_agendado_em         TEXT,
    advideo_em                  TEXT,
    advideo_responsavel_id      BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    documentos_conferidos_em    TEXT,

    responsavel_id    BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    observacao        TEXT,
    airtable_record_id TEXT,
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_audiencias_processo ON audiencias(processo_id, data_hora);
CREATE INDEX ix_audiencias_agenda   ON audiencias(data_hora) WHERE situacao IN ('DESIGNADA','EM_PREPARACAO');

-- O Airtable não sabia o que é prazo processual. Aqui ele nasce de uma
-- origem (DEJT, PJe, ata, despacho), tem tipo (prazo_tipos, em governanca.sql)
-- e conta em DIAS ÚTEIS (CLT art. 775). Dias corridos só com justificativa
-- escrita — o gatilho gov_prazo_regras recusa sem ela.
CREATE TABLE prazos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    situacao          TEXT NOT NULL DEFAULT 'ABERTO',       -- fluxo PRAZO
    tipo              TEXT,                                 -- FK prazo_tipos, ligada no fim
    descricao         TEXT,
    origem            TEXT NOT NULL DEFAULT 'MANUAL' CHECK (origem IN (
                        'DEJT','PJE','ATA_AUDIENCIA','DESPACHO','MANUAL','MIGRACAO')),
    disponibilizado_em TEXT,
    publicado_em      TEXT,                                 -- 1º dia útil após a disponibilização
    inicio            TEXT,                                 -- 1º dia útil após a publicação
    vencimento        TEXT,
    contagem          TEXT NOT NULL DEFAULT 'UTEIS' CHECK (contagem IN ('UTEIS','CORRIDOS')),
    contagem_motivo   TEXT,                                 -- obrigatório se contagem <> UTEIS
    cumprido_em       TEXT,                                 -- obrigatório em CUMPRIDO
    protocolo         TEXT,
    peca_id           BIGINT,                               -- FK documentos, ligada no fim
    motivo            TEXT,                                 -- obrigatório em PERDIDO
    responsavel_id    BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    audiencia_id      BIGINT REFERENCES audiencias(id) ON DELETE SET NULL,  -- Súmula 197 TST
    airtable_record_id TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_prazos_abertos ON prazos(vencimento) WHERE situacao = 'ABERTO';
CREATE INDEX ix_prazos_processo ON prazos(processo_id);

CREATE TABLE pericias (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    tipo              TEXT NOT NULL CHECK (tipo IN ('MEDICA','TECNICA','CONTABIL')),
    data_hora         TEXT,
    perito            TEXT,
    laudo_em          TEXT,
    laudo_documento_id BIGINT,                              -- FK documentos, ligada no fim
    prazo_id          BIGINT REFERENCES prazos(id) ON DELETE SET NULL,  -- manifestação sobre o laudo
    observacao        TEXT,
    airtable_bruto    JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_pericias_processo ON pericias(processo_id);

-- ---------------------------------------------------------------------
-- 7. O QUE O JUÍZO DECIDIU
--
-- Resultado OBJETIVO e NOTA são coisas diferentes e na origem dividiam
-- campo (ULTIMA DECISAO misturava RUIM/MÉDIA/ÓTIMA com PROCEDENTE/
-- IMPROCEDENTE). Aqui a nota é avaliação nossa e o resultado é o que está
-- escrito na decisão. [CONFIRMAR pergunta 24: quem dá a nota e quando.]
-- ---------------------------------------------------------------------
CREATE TABLE decisoes (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    tipo              TEXT NOT NULL CHECK (tipo IN ('SENTENCA','ACORDAO','DESPACHO')),
    data              TEXT,
    resultado_objetivo TEXT CHECK (resultado_objetivo IS NULL OR resultado_objetivo IN (
                        'PROCEDENTE','PARCIALMENTE_PROCEDENTE','IMPROCEDENTE',
                        'EXTINTO_SEM_RESOLUCAO',
                        'PROVIDO','PARCIALMENTE_PROVIDO','NEGADO_PROVIMENTO','NAO_CONHECIDO')),
    nota              TEXT CHECK (nota IS NULL OR nota IN ('RUIM','MEDIA','OTIMA')),
    magistrado        TEXT,
    orgao             TEXT,                                 -- vara, turma do TRT, turma do TST
    grau              TEXT CHECK (grau IS NULL OR grau IN ('PRIMEIRO','TRT','TST')),
    publicada_em      TEXT,
    observacao        TEXT,
    airtable_bruto    JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_decisoes_processo ON decisoes(processo_id, tipo, data);

-- Uma tabela de recursos responde ao que o Airtable não sabia dizer:
-- recurso DE QUEM (pergunta 22), em que grau, e como acabou.
CREATE TABLE recursos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    tipo              TEXT NOT NULL CHECK (tipo IN (
                        'RECURSO_ORDINARIO','CONTRARRAZOES','RECURSO_ADESIVO','RECURSO_REVISTA',
                        'AGRAVO_INSTRUMENTO','AGRAVO_INTERNO','EMBARGOS_TST','AGRAVO_PETICAO',
                        'EMBARGOS_DECLARACAO','EMBARGOS_DE_TERCEIRO','RRAg','OUTRO')),
    de_quem           TEXT CHECK (de_quem IS NULL OR de_quem IN ('RECLAMANTE','RECLAMADA','AMBOS')),
    grau              TEXT CHECK (grau IS NULL OR grau IN ('TRT','TST')),
    interposto_em     TEXT,
    julgado_em        TEXT,
    resultado         TEXT CHECK (resultado IS NULL OR resultado IN (
                        'PROVIDO','PARCIALMENTE_PROVIDO','NEGADO_PROVIMENTO','NAO_CONHECIDO')),
    decisao_id        BIGINT REFERENCES decisoes(id) ON DELETE SET NULL,
    relator           TEXT,
    orgao             TEXT,
    prazo_id          BIGINT REFERENCES prazos(id) ON DELETE SET NULL,
    observacao        TEXT,
    airtable_bruto    JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_recursos_processo ON recursos(processo_id);
CREATE INDEX ix_recursos_pendentes ON recursos(processo_id, grau) WHERE julgado_em IS NULL;

-- ---------------------------------------------------------------------
-- 8. DINHEIRO — tudo em centavos, inteiro
-- ---------------------------------------------------------------------

-- O cálculo não é sub-máquina; são fatos. Uma linha por base: o que o
-- reclamante apresentou, o que a reclamada apresentou, e o que o juízo
-- homologou. Juntar cálculo abre prazo (8 dias, art. 879 §2º) — o prazo é
-- linha em `prazos`, não status.
CREATE TABLE calculos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    base              TEXT NOT NULL CHECK (base IN ('RECLAMANTE','RECLAMADA','HOMOLOGADO')),
    valor_centavos    BIGINT,
    sucumbencia_centavos BIGINT,
    honorario_centavos   BIGINT,                        -- contratual projetado sobre esta base
    juntado_em        TEXT,
    homologado_em     TEXT,
    prazo_id          BIGINT REFERENCES prazos(id) ON DELETE SET NULL,
    observacao        TEXT,
    airtable_bruto    JSONB,
    UNIQUE (processo_id, base)
);

CREATE TABLE acordos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    valor_centavos    BIGINT,
    honorario_centavos BIGINT,
    parcelas          INTEGER,
    valor_parcela_centavos BIGINT,
    homologado_em     TEXT,
    situacao          TEXT NOT NULL DEFAULT 'EM_ANDAMENTO'
                      CHECK (situacao IN ('EM_ANDAMENTO','CUMPRIDO','QUEBRADO')),
    quebrado_em       TEXT,
    quebra_motivo     TEXT,
    observacao        TEXT,
    airtable_bruto    JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_acordos_processo ON acordos(processo_id);

-- Parcela atrasada é quebra: multa da cláusula penal e execução do saldo.
-- A origem não guardava vencimento de parcela — só quantas eram. A migração
-- NÃO inventa datas: as parcelas nascem no portal, e o que veio do Airtable
-- fica em `acordos.parcelas` / `valor_parcela_centavos`.
CREATE TABLE acordo_parcelas (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    acordo_id         BIGINT NOT NULL REFERENCES acordos(id) ON DELETE CASCADE,
    numero            INTEGER NOT NULL,
    vencimento        TEXT,
    valor_centavos    BIGINT,
    pago_em           TEXT,
    valor_pago_centavos BIGINT,
    comprovante_id    BIGINT,                           -- FK documentos, ligada no fim
    UNIQUE (acordo_id, numero)
);

-- O que entrou. Uma linha por base porque é assim que a origem guardava
-- (TOTAL RECEBIDO, SUCUMB RECEBIDO, HONOR TOTAL, e no PÓS o que foi do
-- cliente) — e é assim que `conferir.py` consegue somar os dois lados.
CREATE TABLE recebimentos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    base              TEXT NOT NULL CHECK (base IN ('TOTAL','SUCUMBENCIA','HONORARIOS','CLIENTE')),
    valor_centavos    BIGINT NOT NULL,
    data              TEXT,
    forma             TEXT CHECK (forma IS NULL OR forma IN ('ALVARA','DEPOSITO','ACORDO','OUTRO')),
    comprovante_id    BIGINT,                           -- FK documentos, ligada no fim
    observacao        TEXT,
    airtable_bruto    JSONB,
    UNIQUE (processo_id, base)
);

-- O repasse ao cliente é DO FINANCEIRO (resposta 26). Aqui fica a
-- REFERÊNCIA — houve, quando, quanto — para o sistema poder dizer que o
-- processo terminou de verdade. O gate `repasse_registrado` lê esta tabela.
CREATE TABLE repasses (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT NOT NULL REFERENCES processos(id) ON DELETE CASCADE,
    valor_centavos    BIGINT,
    data              TEXT,
    comprovante_id    BIGINT,                           -- FK documentos, ligada no fim
    sem_valor_motivo  TEXT,                             -- não havia o que repassar, e por quê
    entregue_ao_financeiro_em TEXT,
    observacao        TEXT,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),
    CHECK (valor_centavos IS NOT NULL OR sem_valor_motivo IS NOT NULL)
);
CREATE INDEX ix_repasses_processo ON repasses(processo_id);

-- ---------------------------------------------------------------------
-- 9. O INCIDENTE DE REPRESENTAÇÃO (fluxo 5)
--
-- ROUBADO / RECEBIDO POR ELES / RECUPERADO / REVOGAÇÃO / NOTIFICAÇÃO /
-- PROVIDENCIAS viviam em STATUS DO PROCESSO e em campos soltos. Não são
-- fase: o processo continua em juízo, com outro patrono. O objetivo é
-- receber os honorários pelo trabalho feito (EOAB art. 22 §4º) ou trazer o
-- cliente de volta.
-- ---------------------------------------------------------------------
CREATE TABLE incidentes (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE CASCADE,
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    situacao          TEXT NOT NULL DEFAULT 'DETECTADO',    -- fluxo INCIDENTE
    tipo              TEXT NOT NULL DEFAULT 'TROCA_DE_ADVOGADO'
                      CHECK (tipo IN ('TROCA_DE_ADVOGADO','REVOGACAO_PELO_CLIENTE','OUTRO')),
    detectado_em      TEXT,
    revogacao_nos_autos_em   TEXT,
    notificacao_redigida_em  TEXT,
    notificacao_enviada_em   TEXT,                        -- gate `notificacao_enviada`
    notificacao_recebida_em  TEXT,
    resposta_em              TEXT,
    cliente_avisado_em       TEXT,
    peticao_reserva_id BIGINT,                            -- FK peticoes, ligada no fim
    valor_recebido_centavos BIGINT,
    providencia_texto TEXT,                               -- o texto original do campo PROVIDENCIAS
    motivo            TEXT,
    responsavel_id    BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    airtable_bruto    JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),
    CHECK (processo_id IS NOT NULL OR cliente_id IS NOT NULL)
);
CREATE INDEX ix_incidentes_processo ON incidentes(processo_id);
CREATE INDEX ix_incidentes_abertos  ON incidentes(situacao) WHERE situacao IN ('DETECTADO','NOTIFICADO','HONORARIOS_RESERVADOS');

-- ---------------------------------------------------------------------
-- 10. TESTEMUNHAS
--
-- Entidade própria, com dois canais: jurídico (formulário interno, 330) e
-- comercial (o captador cadastra, 36). TEM PROCESSO? existe porque a
-- reclamada sempre contradita a testemunha que também litiga contra a mesma
-- empresa — a Súmula 357 do TST diz que isso NÃO a torna suspeita, mas é
-- preciso saber antes da audiência.
-- ---------------------------------------------------------------------
CREATE TABLE testemunhas (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome              TEXT NOT NULL,
    nome_norm         TEXT NOT NULL,
    telefone          TEXT,
    cpf               TEXT,
    endereco          TEXT,
    empresa_id        BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    captador_id       BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    vinculo           TEXT CHECK (vinculo IS NULL OR vinculo IN (
                        'COLEGA_DE_TRABALHO','EX_COLEGA','GESTOR_SUPERVISOR','TERCEIRO','NAO_INFORMADO')),
    admissao_em       TEXT,
    horario_trabalho  TEXT,
    ainda_trabalha    BOOLEAN,
    demissao_em       TEXT,
    tem_processo      BOOLEAN,                            -- Súmula 357 TST
    situacao          TEXT NOT NULL DEFAULT 'PENDENTE'
                      CHECK (situacao IN ('PENDENTE','A_CONFIRMAR','CONFIRMADA','DESCARTADA','NAO_USAR')),
    confirmada_em     TEXT,                               -- o que o checklist da audiência lê
    cobrancas         INTEGER NOT NULL DEFAULT 0,
    ultimo_contato_em TEXT,
    duplicado         BOOLEAN,
    origem            TEXT CHECK (origem IS NULL OR origem IN ('JURIDICO','COMERCIAL')),
    origem_registro_id TEXT,                              -- o registro do formulário comercial
    observacao        TEXT,
    airtable_record_id TEXT,
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_testemunhas_norm ON testemunhas(nome_norm);
CREATE UNIQUE INDEX ix_testemunhas_airtable ON testemunhas(airtable_record_id) WHERE airtable_record_id IS NOT NULL;

-- Uma testemunha serve a mais de um caso, e na origem havia dois campos de
-- link (um para PROCESSUAL, outro para PRE PROCESSUAL) com rótulos trocados
-- no formulário comercial. Aqui é uma tabela de ligação só.
CREATE TABLE testemunha_vinculos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    testemunha_id     BIGINT NOT NULL REFERENCES testemunhas(id) ON DELETE CASCADE,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE CASCADE,
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    audiencia_id      BIGINT REFERENCES audiencias(id) ON DELETE SET NULL,
    intimacao_pedida_em TEXT,                             -- art. 825 CLT: se falhar, pede-se intimação
    observacao        TEXT,
    CHECK (processo_id IS NOT NULL OR cliente_id IS NOT NULL)
);
CREATE UNIQUE INDEX ix_tvinc_proc ON testemunha_vinculos(testemunha_id, processo_id) WHERE processo_id IS NOT NULL;
CREATE UNIQUE INDEX ix_tvinc_cli  ON testemunha_vinculos(testemunha_id, cliente_id)  WHERE cliente_id IS NOT NULL;

-- O log append-only do formulário interno de testemunhas. Migra como está:
-- é auditoria de outro sistema e não se reescreve auditoria.
CREATE TABLE testemunha_auditoria (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    evento_id         TEXT,
    em                TEXT,
    ator_record_id    TEXT,
    ator_nome         TEXT,
    setor             TEXT,
    acao              TEXT,
    testemunha_record_id TEXT,
    testemunha_id     BIGINT REFERENCES testemunhas(id) ON DELETE SET NULL,
    testemunha_nome   TEXT,
    contexto          TEXT,
    campos_alterados  TEXT,
    antes             TEXT,
    depois            TEXT,
    operation_id      TEXT,
    resultado         TEXT,
    origem_sistema    TEXT,
    airtable_record_id TEXT,
    airtable_bruto     JSONB
);

-- ---------------------------------------------------------------------
-- 11. DOCUMENTO, PETIÇÃO, ANOTAÇÃO
--
-- Anexo: SÓ METADADO (nome, url, tamanho). Cópia de arquivo não entra no
-- repositório nem no banco.
-- ---------------------------------------------------------------------
CREATE TABLE documentos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE CASCADE,
    testemunha_id     BIGINT REFERENCES testemunhas(id) ON DELETE CASCADE,
    fragilidade_id    BIGINT REFERENCES fragilidades(id) ON DELETE CASCADE,
    tipo              TEXT CHECK (tipo IS NULL OR tipo IN (
                        'CNH_RG','CTPS','TRCT','DOCS_MEDICOS','PROVAS','FGTS','HOLERITES','PIS',
                        'CONTRATO','PROCURACAO','PETICAO','DECISAO','LAUDO','CALCULO',
                        'COMPROVANTE','DOSSIE','OUTRO')),
    nome_arquivo      TEXT NOT NULL,
    mime              TEXT,
    tamanho_bytes     BIGINT,
    url_origem        TEXT,                               -- expira; serve ao download inicial
    drive_url         TEXT,
    fonte             TEXT NOT NULL DEFAULT 'ANEXO_AIRTABLE' CHECK (fonte IN (
                        'ANEXO_AIRTABLE','DRIVE','UPLOAD','GERADO','PJE','ZAPSIGN')),
    airtable_attachment_id TEXT,
    airtable_record_id TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_documentos_cliente ON documentos(cliente_id);
CREATE INDEX ix_documentos_processo ON documentos(processo_id);
CREATE UNIQUE INDEX ix_documentos_attach ON documentos(airtable_attachment_id) WHERE airtable_attachment_id IS NOT NULL;

CREATE TABLE peticoes (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE CASCADE,
    tipo              TEXT NOT NULL CHECK (tipo IN (
                        'INICIAL','REPLICA','RAZOES_FINAIS','RECURSO_ORDINARIO','CONTRARRAZOES',
                        'RECURSO_REVISTA','AGRAVO_PETICAO','IMPUGNACAO_CALCULOS',
                        'NOTIFICACAO_EXTRAJUDICIAL','RESERVA_HONORARIOS','OUTRA')),
    titulo            TEXT,
    texto             TEXT,
    arquivo_id        BIGINT REFERENCES documentos(id) ON DELETE SET NULL,   -- gate `minuta_anexada`
    versao            INTEGER NOT NULL DEFAULT 1,
    status            TEXT NOT NULL DEFAULT 'RASCUNHO'
                      CHECK (status IN ('RASCUNHO','EM_REVISAO','APROVADA','PROTOCOLADA','DESCARTADA')),
    origem            TEXT NOT NULL DEFAULT 'MANUAL' CHECK (origem IN ('MANUAL','AUTOMACAO','MIGRACAO')),
    revisada_por      BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    protocolada_em    TEXT,
    observacao        TEXT,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),
    CHECK (cliente_id IS NOT NULL OR processo_id IS NOT NULL)
);
CREATE INDEX ix_peticoes_cliente ON peticoes(cliente_id);
CREATE INDEX ix_peticoes_processo ON peticoes(processo_id);

CREATE TABLE anotacoes (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE CASCADE,
    testemunha_id     BIGINT REFERENCES testemunhas(id) ON DELETE CASCADE,
    empresa_id        BIGINT REFERENCES empresas(id) ON DELETE CASCADE,
    texto             TEXT NOT NULL,
    autor_id          BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    origem            TEXT NOT NULL DEFAULT 'MANUAL' CHECK (origem IN ('MANUAL','MIGRACAO','AUTOMACAO')),
    campo_origem      TEXT,                               -- de qual campo do Airtable veio
    em                TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_anotacoes_cliente ON anotacoes(cliente_id);
CREATE INDEX ix_anotacoes_processo ON anotacoes(processo_id);

-- ---------------------------------------------------------------------
-- 12. TRABALHO: tarefa, evento, contato
-- ---------------------------------------------------------------------

-- Etapa sem dono é etapa parada. AND. NECESSÁRIO e PROVIDENCIAS eram
-- tarefas disfarçadas de select — chegam aqui com o texto original inteiro.
CREATE TABLE tarefas (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    titulo            TEXT NOT NULL,
    detalhe           TEXT,
    tipo              TEXT NOT NULL DEFAULT 'ETAPA' CHECK (tipo IN (
                        'ETAPA','DOCUMENTO','PETICAO','PRAZO','AUDIENCIA','CONTATO','ANDAMENTO',
                        'NOTIFICACAO','ARQUIVAMENTO','REDISTRIBUICAO','CONFERENCIA','OUTRO')),
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE CASCADE,
    pendencia_id      BIGINT REFERENCES pendencias(id) ON DELETE CASCADE,
    incidente_id      BIGINT REFERENCES incidentes(id) ON DELETE CASCADE,
    responsavel_id    BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    grupo             TEXT,                               -- setor, quando não há dono
    etapa             TEXT,
    prazo             TEXT,
    prioridade        TEXT NOT NULL DEFAULT 'NORMAL'
                      CHECK (prioridade IN ('BAIXA','NORMAL','ALTA','URGENTE')),
    status            TEXT NOT NULL DEFAULT 'ABERTA'
                      CHECK (status IN ('ABERTA','EM_ANDAMENTO','CONCLUIDA','CANCELADA')),
    origem            TEXT NOT NULL DEFAULT 'SISTEMA'
                      CHECK (origem IN ('SISTEMA','MANUAL','AUTOMACAO','MIGRACAO')),
    texto_original    TEXT,                               -- o recado como estava na origem
    agora             BOOLEAN NOT NULL DEFAULT false,
    agora_em          TEXT,
    concluida_em      TEXT,
    concluida_por     BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    criada_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),
    CHECK (status <> 'CONCLUIDA' OR concluida_em IS NOT NULL)
);
CREATE INDEX ix_tarefas_resp   ON tarefas(responsavel_id, status);
CREATE INDEX ix_tarefas_grupo  ON tarefas(grupo, status);
CREATE INDEX ix_tarefas_abertas ON tarefas(status, prazo) WHERE status IN ('ABERTA','EM_ANDAMENTO');

CREATE TABLE eventos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo              TEXT NOT NULL CHECK (tipo IN (
                        'ENTREVISTA','VISITA','AUDIENCIA','PERICIA','REUNIAO_PRE_AUDIENCIA',
                        'ADVIDEO','PRAZO','OUTRO')),
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE CASCADE,
    audiencia_id      BIGINT REFERENCES audiencias(id) ON DELETE CASCADE,
    data_hora         TEXT,
    situacao          TEXT NOT NULL DEFAULT 'AGENDADO'
                      CHECK (situacao IN ('AGENDADO','REMARCADO','REALIZADO','CANCELADO')),
    responsavel_id    BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    local             TEXT,
    observacao        TEXT,
    google_event_id   TEXT,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_eventos_data ON eventos(data_hora);
CREATE INDEX ix_eventos_cliente ON eventos(cliente_id);

-- Ligou, mandou mensagem, foi. O contador de contatos da entrevista e as
-- cobranças da testemunha (1º–4º) viram linhas com data — assim o alerta
-- "3 contatos sem resposta" continua possível e ainda ganha quando foi.
CREATE TABLE contatos (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id        BIGINT REFERENCES clientes(id) ON DELETE CASCADE,
    testemunha_id     BIGINT REFERENCES testemunhas(id) ON DELETE CASCADE,
    em                TEXT,
    canal             TEXT CHECK (canal IS NULL OR canal IN (
                        'TELEFONE','WHATSAPP','EMAIL','PRESENCIAL','DISPARO','OUTRO')),
    pessoa_id         BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    resultado         TEXT,
    observacao        TEXT,
    origem            TEXT NOT NULL DEFAULT 'MANUAL' CHECK (origem IN ('MANUAL','MIGRACAO','AUTOMACAO')),
    CHECK (cliente_id IS NOT NULL OR testemunha_id IS NOT NULL)
);
CREATE INDEX ix_contatos_cliente ON contatos(cliente_id, em);

-- ---------------------------------------------------------------------
-- 13. CONFERÊNCIAS — onde ninguém escolhe em silêncio
--
-- A migração casa a CÓPIA com a PROCESSUAL. Onde as duas discordam em campo
-- relevante (as 1.403 divergências de FASE incluídas), onde um valor
-- poluído não tem tradução óbvia, onde há CNJ duplicado ou cliente que não
-- casou: nasce linha aqui, com o valor de CADA LADO e o trecho de prova.
-- Conferir é abrir o registro — como no Prev.
-- ---------------------------------------------------------------------
CREATE TABLE conferencias (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- chave natural: a mesma divergência não vira duas linhas a cada carga
    chave             TEXT NOT NULL UNIQUE,
    tipo              TEXT NOT NULL CHECK (tipo IN (
                        'DIVERGENCIA_FONTE','VALOR_SEM_TRADUCAO','CNJ_DUPLICADO','SEM_NUMERO',
                        'CLIENTE_AMBIGUO','CLIENTE_SEM_PAR','EMPRESA_AMBIGUA','LINK_QUEBRADO',
                        'FORA_DO_ESCOPO','DATA_ILEGIVEL','AUDIENCIA_SEM_RESULTADO','OUTRO')),
    entidade          TEXT NOT NULL,                      -- 'processos', 'clientes', ...
    entidade_id       BIGINT,                             -- pode ser NULL: a linha nem entrou
    campo             TEXT,
    valor_a           TEXT,
    origem_a          TEXT,                               -- 'COPIA', 'PROCESSUAL', 'PRE_PROCESSUAL'…
    valor_b           TEXT,
    origem_b          TEXT,
    escolhido         TEXT,                               -- o que a migração gravou, se gravou
    prova             TEXT,                               -- o trecho que sustenta a divergência
    airtable_record_id TEXT,
    situacao          TEXT NOT NULL DEFAULT 'ABERTA'
                      CHECK (situacao IN ('ABERTA','EM_ANALISE','RESOLVIDA','IGNORADA')),
    dono_id           BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    grupo             TEXT,
    anotacao          TEXT,
    resolvido_em      TEXT,
    resolvido_por     BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_conferencias_abertas ON conferencias(tipo, situacao) WHERE situacao IN ('ABERTA','EM_ANALISE');
CREATE INDEX ix_conferencias_entidade ON conferencias(entidade, entidade_id);

-- ---------------------------------------------------------------------
-- 14. RASTRO: auditoria, automação, migração
-- ---------------------------------------------------------------------
CREATE TABLE auditoria (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tabela            TEXT NOT NULL,
    registro_id       BIGINT NOT NULL,
    acao              TEXT NOT NULL CHECK (acao IN ('INSERT','UPDATE','DELETE')),
    campo             TEXT,
    valor_antigo      TEXT,
    valor_novo        TEXT,
    pessoa_id         BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    em                TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_auditoria_reg ON auditoria(tabela, registro_id, em);

CREATE TABLE automacoes (
    codigo      TEXT PRIMARY KEY,
    nome        TEXT NOT NULL,
    descricao   TEXT,
    ativa       BOOLEAN NOT NULL DEFAULT true,
    config      JSONB
);

-- O modo de falha da automação é o SILÊNCIO: rodada que falhou tem de ser
-- distinguível de dia sem nada a fazer. Por isso `resultado` é obrigatório.
CREATE TABLE automacao_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    automacao   TEXT NOT NULL,
    chave       TEXT NOT NULL,
    resultado   TEXT NOT NULL CHECK (resultado IN ('OK','SEM_ACAO','ERRO','MIGRADO')),
    detalhe     TEXT,
    cliente_id  BIGINT REFERENCES clientes(id) ON DELETE SET NULL,
    processo_id BIGINT REFERENCES processos(id) ON DELETE SET NULL,
    testemunha_id BIGINT REFERENCES testemunhas(id) ON DELETE SET NULL,
    origem      TEXT NOT NULL DEFAULT 'SISTEMA' CHECK (origem IN ('SISTEMA','N8N','MIGRACAO')),
    em          TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),
    UNIQUE (automacao, chave)
);
CREATE INDEX ix_automacao_log_em ON automacao_log(automacao, em);

-- Processos do escritório que ainda NÃO estavam na PROCESSUAL. 1.067 linhas,
-- 539 delas já presentes na CÓPIA. Entram como tabela própria porque são uma
-- LISTA DE CONFERÊNCIA, não processos: o Glauco valida e sobe. Quando o CNJ
-- casa com um processo migrado, `processo_id` aponta para ele.
CREATE TABLE conferencia_faltantes (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome              TEXT,
    numero_cnj        TEXT,
    numero_cnj_digitos TEXT GENERATED ALWAYS AS (regexp_replace(COALESCE(numero_cnj,''), '\D', '', 'g')) STORED,
    empresa_id        BIGINT REFERENCES empresas(id) ON DELETE SET NULL,
    processo_id       BIGINT REFERENCES processos(id) ON DELETE SET NULL,
    valor_causa_centavos BIGINT,
    trt               TEXT,
    vara              TEXT,
    distribuicao_em   TEXT,
    fase_recomendada  TEXT,                               -- Datajud, texto
    status_recomendado TEXT,                              -- Datajud, texto
    ultimo_movimento  TEXT,
    status_processo   TEXT,
    validar_e_subir   BOOLEAN NOT NULL DEFAULT false,     -- 0/1067 marcados; a automação nunca existiu
    observacoes       TEXT,
    airtable_record_id TEXT,
    airtable_tabela    TEXT,
    airtable_bruto     JSONB,
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_faltantes_cnj ON conferencia_faltantes(numero_cnj_digitos);
CREATE UNIQUE INDEX ix_faltantes_airtable ON conferencia_faltantes(airtable_record_id) WHERE airtable_record_id IS NOT NULL;

-- Cada carga deixa rastro: quando, de qual dump, o que entrou, o que sobrou.
CREATE TABLE migracao_execucoes (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    iniciada_em   TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),
    terminada_em  TEXT,
    fonte         TEXT,
    versao        TEXT,
    resumo        JSONB,
    resultado     TEXT CHECK (resultado IS NULL OR resultado IN ('OK','ERRO'))
);

-- ---------------------------------------------------------------------
-- 14b. PUBLICAÇÕES: o que o diário disse, antes de virar trabalho.
--
-- No Prev o equivalente é `aasp.py`, e lá a publicação vira log. Aqui não pode
-- ser só log: no trabalhista é a publicação que FAZ O PRAZO NASCER, e prazo
-- perdido é o pior dia do escritório. Por isso a linha guarda as duas datas
-- que a lei separa e que todo mundo confunde:
--
--   `disponibilizado_em` — o dia em que o ato saiu no DEJT;
--   `publicado_em`       — o PRIMEIRO DIA ÚTIL SEGUINTE (Lei 11.419/2006,
--                          art. 4º, §§ 3º e 4º), de onde o prazo começa a correr.
--
-- Daí para a frente a contagem é em DIAS ÚTEIS (CLT art. 775), com o recesso
-- de 20/12 a 20/01 suspendendo (art. 775-A). Quem faz essa conta é
-- `prazo_legal.py` — esta tabela só guarda o resultado.
--
-- A máquina PROPÕE e não decide: `prazo_tipo_sugerido` e `vencimento_sugerido`
-- são leitura de máquina, e `prazo_id` só é preenchido quando alguém do
-- Jurídico leu e mandou criar. É a regra 5 da casa, e é a mesma decisão que o
-- Lucas tomou no Prev em 23/08/2026 para as decisões do diário: o trabalho só
-- nasce quando gente lê.
-- ---------------------------------------------------------------------
CREATE TABLE publicacoes (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- De onde veio. `fonte_id` é o identificador NA ORIGEM (no DJEN, o id da
    -- comunicação; na AASP, o hash do bloco do e-mail). Com a fonte, forma a
    -- chave que impede a mesma publicação de entrar duas vezes — e ela é lida
    -- de novo o tempo todo, por retry e por janela de datas sobreposta.
    fonte             TEXT NOT NULL CHECK (fonte IN ('DJEN','AASP','PJE','MANUAL')),
    fonte_id          TEXT NOT NULL,

    numero_cnj        TEXT,
    numero_cnj_digitos TEXT GENERATED ALWAYS AS (regexp_replace(COALESCE(numero_cnj,''), '\D', '', 'g')) STORED,
    tribunal          TEXT,
    orgao             TEXT,                                 -- vara, turma, gabinete
    tipo_ato          TEXT,                                 -- Sentença, Despacho, Intimação…
    disponibilizado_em TEXT NOT NULL,
    publicado_em      TEXT,
    texto             TEXT NOT NULL,

    -- O casamento com o processo. `casou_por` diz a FORÇA da ligação: CNJ é
    -- exato; ALIAS é a outra grafia que a migração guardou; MANUAL é gente.
    processo_id       BIGINT REFERENCES processos(id) ON DELETE SET NULL,
    casou_por         TEXT CHECK (casou_por IN ('CNJ','ALIAS','MANUAL')),

    -- A leitura de máquina, que é PROPOSTA. `prazo_tipo_sugerido` aponta para
    -- prazo_tipos, e a FK é ligada depois: aquela tabela nasce em governanca.sql.
    prazo_tipo_sugerido TEXT,
    vencimento_sugerido TEXT,
    sugestao_motivo   TEXT,                                 -- por que a máquina achou isso

    situacao          TEXT NOT NULL DEFAULT 'NOVA' CHECK (situacao IN (
                        'NOVA','LIDA','VIROU_PRAZO','SEM_PRAZO','NAO_E_NOSSA')),
    lida_em           TEXT,
    lida_por          BIGINT REFERENCES pessoas(id) ON DELETE SET NULL,
    prazo_id          BIGINT REFERENCES prazos(id) ON DELETE SET NULL,
    tarefa_id         BIGINT REFERENCES tarefas(id) ON DELETE SET NULL,

    bruto             JSONB,                                -- a comunicação inteira, como veio
    criado_em         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS'),

    UNIQUE (fonte, fonte_id)
);

-- A fila de trabalho: o que chegou e ninguém leu, mais recente primeiro.
CREATE INDEX ix_publicacoes_novas ON publicacoes(disponibilizado_em DESC) WHERE situacao = 'NOVA';
CREATE INDEX ix_publicacoes_processo ON publicacoes(processo_id);
-- O casamento por CNJ é a operação quente da leitura diária.
CREATE INDEX ix_publicacoes_cnj ON publicacoes(numero_cnj_digitos) WHERE numero_cnj_digitos <> '';
-- A que não casou com processo nenhum: é a fila de conferência do cadastro.
CREATE INDEX ix_publicacoes_orfas ON publicacoes(disponibilizado_em DESC) WHERE processo_id IS NULL;

-- ---------------------------------------------------------------------
-- 15. As FKs que só podem existir agora (referências para frente)
-- ---------------------------------------------------------------------
ALTER TABLE clientes        ADD CONSTRAINT fk_cli_contrato   FOREIGN KEY (contrato_assinado_doc_id) REFERENCES documentos(id) ON DELETE SET NULL;
ALTER TABLE pendencias      ADD CONSTRAINT fk_pend_doc       FOREIGN KEY (documento_id)     REFERENCES documentos(id) ON DELETE SET NULL;
ALTER TABLE prazos          ADD CONSTRAINT fk_prazo_peca     FOREIGN KEY (peca_id)          REFERENCES documentos(id) ON DELETE SET NULL;
ALTER TABLE pericias        ADD CONSTRAINT fk_pericia_laudo  FOREIGN KEY (laudo_documento_id) REFERENCES documentos(id) ON DELETE SET NULL;
ALTER TABLE acordo_parcelas ADD CONSTRAINT fk_parcela_comp   FOREIGN KEY (comprovante_id)   REFERENCES documentos(id) ON DELETE SET NULL;
ALTER TABLE recebimentos    ADD CONSTRAINT fk_receb_comp     FOREIGN KEY (comprovante_id)   REFERENCES documentos(id) ON DELETE SET NULL;
ALTER TABLE repasses        ADD CONSTRAINT fk_repasse_comp   FOREIGN KEY (comprovante_id)   REFERENCES documentos(id) ON DELETE SET NULL;
ALTER TABLE incidentes      ADD CONSTRAINT fk_inc_reserva    FOREIGN KEY (peticao_reserva_id) REFERENCES peticoes(id) ON DELETE SET NULL;

-- ---------------------------------------------------------------------
-- 16. RLS — ligada em TODA tabela, política única para o papel do app.
--
-- Sem política para `anon`/`authenticated`: nada do escritório sai pela API
-- pública do Supabase. Quem lê e escreve é o sistema, pelo Postgres, com o
-- papel `app_trab` concedido ao usuário da conexão.
--
-- O bloco é um laço sobre `information_schema` de propósito: tabela nova
-- criada por migration futura entra na mesma regra quando este bloco for
-- reexecutado, e ninguém precisa lembrar de escrever a política à mão.
-- ---------------------------------------------------------------------
-- Vira FUNÇÃO, e não um bloco solto, por um motivo que a conferência achou:
-- `governanca.sql` roda DEPOIS deste arquivo e cria mais cinco tabelas
-- (fluxos, fluxo_etapas, fluxo_transicoes, historico_etapas, prazo_tipos).
-- Um bloco executado uma vez deixaria essas cinco sem RLS — e o mapa de etapas
-- é justamente o que não pode ficar aberto na API pública. Como função, ela é
-- chamada de novo no fim da montagem e a cada migration que criar tabela.
CREATE OR REPLACE FUNCTION ligar_rls() RETURNS integer
LANGUAGE plpgsql SET search_path = public AS $fn$
DECLARE t TEXT; n INTEGER := 0;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS p_app_trab ON public.%I', t);
    EXECUTE format('CREATE POLICY p_app_trab ON public.%I FOR ALL TO app_trab USING (true) WITH CHECK (true)', t);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO app_trab', t);
    n := n + 1;
  END LOOP;
  EXECUTE 'GRANT USAGE ON SCHEMA public TO app_trab';
  EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_trab';
  -- e revoga o que o Supabase concede por padrão aos papéis da API pública.
  -- Num Postgres qualquer (o cluster de teste, por exemplo) esses papéis não
  -- existem: a falta deles não é erro, é sinal de que não há API pública.
  BEGIN
    EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated';
    EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated';
  EXCEPTION WHEN undefined_object THEN
    RAISE NOTICE 'sem anon/authenticated: este Postgres não serve API pública';
  END;
  RETURN n;
END $fn$;

SELECT ligar_rls();

-- ---------------------------------------------------------------------
-- 17. O que a governança deixou anotado para o esquema fechar.
--     Rode DEPOIS de governanca.sql.
--
--   ALTER TABLE historico_etapas ADD CONSTRAINT fk_hist_pessoa
--     FOREIGN KEY (pessoa_id) REFERENCES pessoas(id) ON DELETE SET NULL;
--   ALTER TABLE prazos ADD CONSTRAINT fk_prazo_tipo
--     FOREIGN KEY (tipo) REFERENCES prazo_tipos(codigo);
--
-- Estão em migrar.py (passo final), porque as tabelas do outro lado só
-- existem depois de governanca.sql.
-- ---------------------------------------------------------------------
