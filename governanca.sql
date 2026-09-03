-- =====================================================================
-- GOVERNANÇA DO TRABALHISTA: o mapa de etapas e o que é permitido entre elas.
--
-- A regra não mora na tela. Mora aqui, e vale para qualquer caminho que
-- chegue ao banco: sistema, script, migração ou mão humana no psql.
--
-- Todo fluxo tem UMA etapa inicial e pelo menos uma final. Transição que
-- não estiver no mapa é recusada com RAISE EXCEPTION, não corrigida em
-- silêncio. Dialeto: Postgres (Supabase). Data fica TEXT ISO, como no Prev,
-- porque é assim que o app compara.
--
-- Cinco máquinas:
--   1 CLIENTE    clientes.status       o pré-processual, do primeiro contato à distribuição
--   2 PROCESSO   processos.fase        conhecimento → recursal → execução → recebendo → encerrado
--   3 AUDIENCIA  audiencias.situacao   designada → preparação → realizada / adiada / redesignada
--   4 PRAZO      prazos.situacao       aberto → cumprido / perdido / suspenso / sem objeto
--   5 INCIDENTE  incidentes.situacao   cliente que trocou de advogado: detectado → notificado → ...
--
-- O que é [CONFIRMAR] está em docs/governanca-para-confirmar.md. Este arquivo
-- é a proposta; vira migration só depois do OK do Lucas.
--
-- A parte de baixo (da linha "SÓ POSTGRES DAQUI PARA BAIXO" em diante) tem os gatilhos em PL/pgSQL
-- e depende das tabelas do esquema (clientes, processos, audiencias, prazos,
-- incidentes). gerar_governanca.py carrega só a parte de cima num SQLite em
-- memória para escrever docs/governanca.md — por isso a divisão.
-- =====================================================================

CREATE TABLE fluxos (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      TEXT NOT NULL UNIQUE,   -- CLIENTE, PROCESSO, AUDIENCIA, PRAZO, INCIDENTE
    nome        TEXT NOT NULL,
    entidade    TEXT NOT NULL,          -- tabela governada
    coluna      TEXT NOT NULL           -- coluna de etapa
);

CREATE TABLE fluxo_etapas (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fluxo_id    BIGINT NOT NULL REFERENCES fluxos(id) ON DELETE CASCADE,
    codigo      TEXT NOT NULL,
    nome        TEXT NOT NULL,
    ordem       INTEGER NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('INICIAL','INTERMEDIARIA','FINAL')),
    sla_dias    INTEGER,                -- quanto tempo é aceitável ficar aqui (corridos)
    grupo       TEXT,                   -- setor que toca a etapa no dia a dia
    texto_operador TEXT,                -- o que fazer aqui, em linguagem simples; aparece na ficha
    UNIQUE (fluxo_id, codigo)
);

CREATE TABLE fluxo_transicoes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fluxo_id    BIGINT NOT NULL REFERENCES fluxos(id) ON DELETE CASCADE,
    de          TEXT NOT NULL,
    para        TEXT NOT NULL,
    acao        TEXT NOT NULL,          -- o verbo que a pessoa vê no botão
    papel       TEXT CHECK (papel IN ('ADVOGADO','GESTOR','DIRECAO')),  -- NULL = qualquer papel
    exige       TEXT,                   -- gates, separados por vírgula; só o que o banco consegue checar
    texto_bloqueio TEXT,                -- por que a ação está indisponível quando `exige` falha
    UNIQUE (fluxo_id, de, para)
);

-- Toda mudança de etapa vira linha aqui. É o histórico que o Airtable nunca
-- teve: quando mudou, de onde para onde, por quem e por quê.
CREATE TABLE historico_etapas (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entidade    TEXT NOT NULL,
    entidade_id BIGINT NOT NULL,
    de          TEXT,
    para        TEXT NOT NULL,
    pessoa_id   BIGINT,                 -- REFERENCES pessoas(id): a FK entra no esquema, quando a tabela existir
    motivo      TEXT,
    origem      TEXT NOT NULL DEFAULT 'SISTEMA'
                CHECK (origem IN ('SISTEMA','MIGRACAO','AUTOMACAO','CORRECAO')),
    em          TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'America/Sao_Paulo','YYYY-MM-DD HH24:MI:SS')
);
CREATE INDEX ix_hist_ent ON historico_etapas(entidade, entidade_id, em);

INSERT INTO fluxos (codigo, nome, entidade, coluna) VALUES
 ('CLIENTE',  'Funil do cliente (pré-processual)', 'clientes',   'status'),
 ('PROCESSO', 'Ciclo do processo',                 'processos',  'fase'),
 ('AUDIENCIA','Audiência',                         'audiencias', 'situacao'),
 ('PRAZO',    'Prazo processual',                  'prazos',     'situacao'),
 ('INCIDENTE','Incidente de representação',        'incidentes', 'situacao');

-- ---------------------------------------------------------------------
-- 1. FLUXO DO CLIENTE: do primeiro contato à distribuição da inicial
--
-- A pessoa é UMA ficha desde o lead. O Airtable só a recebe depois de
-- assinar (99% com DATA DE ASSINATURA); o LEAD é a fase anterior, que hoje
-- vive no WhatsApp [CONFIRMAR pergunta 5]. A ordem DOCUMENTAÇÃO → ENTREVISTA
-- é a inferida da ETAPA PRE PROCESSUAL [CONFIRMAR se a entrevista vem antes].
-- A petição inicial ganhou quatro etapas porque é onde o funil engasga
-- (54 aguardando aprovação contra 6 em redação) e cada uma tem dono diferente.
-- Soma dos SLAs da assinatura à distribuição: 7+5+2+3+2+2 = 21 dias, que é
-- o 🟡15/🔴20 das automações [CONFIRMAR pergunta 6]. Rescisão indireta tem
-- SLA de 15 dias no total (n8n cobra em 5/10/12/15) — não é etapa, é alerta
-- pela urgência do caso (v_pre_processual_atrasado).
-- ---------------------------------------------------------------------
INSERT INTO fluxo_etapas (fluxo_id, codigo, nome, ordem, tipo, sla_dias, grupo, texto_operador) VALUES
 (1,'LEAD','Lead (primeiro contato)',1,'INICIAL',3,'Captação',
  'Ligou ou veio pelo captador. Registre nome, telefone, empresa, função, data e modalidade da saída (ou se ainda trabalha). Sem contrato assinado não há caso.'),
 (1,'DOCUMENTACAO','Documentação',2,'INTERMEDIARIA',7,'Documentação',
  'Contrato e procuração assinados. Peça TRCT, CTPS, holerites, extrato do FGTS, RG/CNH e, se houver, documentos médicos e provas (conversas, fotos, escalas). Marque cada documento recebido.'),
 (1,'ENTREVISTA','Entrevista',3,'INTERMEDIARIA',5,'Atendimento',
  'Agende e realize a entrevista. Registre data, entrevistador e resumo; marque se o caso pede perícia médica ou técnica e arrole as testemunhas.'),
 (1,'PETICAO_PENDENTE','Petição a redigir',4,'INTERMEDIARIA',2,'Jurídico',
  'Caso pronto para a inicial, ainda sem redator. Assuma ou distribua. Se a saída foi rescisão indireta, este caso tem prioridade: o contrato ainda está correndo.'),
 (1,'PETICAO_EM_CRIACAO','Petição em redação',5,'INTERMEDIARIA',3,'Jurídico',
  'Redija a inicial. Se faltar informação, volte para entrevista; se faltar documento, para documentação — sem apagar o que já foi feito.'),
 (1,'PETICAO_AGUARDANDO_APROVACAO','Petição aguardando aprovação',6,'INTERMEDIARIA',2,'Gestão',
  'A minuta espera quem aprova. Aprove ou devolva com o ajuste escrito. Este é o gargalo do funil hoje.'),
 (1,'PETICAO_APROVADA','Petição aprovada, a distribuir',7,'INTERMEDIARIA',2,'Jurídico',
  'Protocole no PJe e registre o número CNJ. É o registro do número que faz nascer o processo no sistema.'),
 (1,'STAND_BY','Stand by',8,'INTERMEDIARIA',60,'Atendimento',
  'Parado por decisão da pessoa ou por fato que ainda vai amadurecer. Marque quando revisitar. A prescrição continua correndo.'),
 (1,'DISTRIBUIDO','Distribuído (concluído)',9,'FINAL',NULL,'Jurídico',
  'A inicial foi distribuída e o processo existe. O trabalho segue no ciclo do processo.'),
 (1,'CANCELADO','Cancelado',10,'FINAL',NULL,'Atendimento',
  'A pessoa desistiu ou o escritório não seguiu. O motivo fica registrado — é o que ensina a captação.'),
 (1,'PRESCRITO','Prescrito',11,'FINAL',NULL,'Jurídico',
  'Passaram-se dois anos do fim do contrato sem ajuizar (CF art. 7º, XXIX; CLT art. 11). Registre o motivo — é perda evitável e precisa ser medida.'),
 (1,'SEM_RESPOSTA','Sem resposta',12,'FINAL',NULL,'Captação',
  'Não retornou o contato. Pode ser reaberto se a pessoa procurar de novo.');

INSERT INTO fluxo_transicoes (fluxo_id, de, para, acao, papel, exige) VALUES
 (1,'LEAD','DOCUMENTACAO','Contrato assinado',NULL,'contrato_assinado'),
 (1,'LEAD','STAND_BY','Colocar em stand by',NULL,NULL),
 (1,'LEAD','SEM_RESPOSTA','Sem resposta',NULL,NULL),
 (1,'LEAD','CANCELADO','Cancelar',NULL,'motivo'),
 (1,'DOCUMENTACAO','ENTREVISTA','Documentação completa',NULL,'documentos_obrigatorios'),
 (1,'DOCUMENTACAO','STAND_BY','Colocar em stand by',NULL,NULL),
 (1,'DOCUMENTACAO','SEM_RESPOSTA','Sem resposta',NULL,NULL),
 (1,'DOCUMENTACAO','CANCELADO','Cancelar',NULL,'motivo'),
 (1,'DOCUMENTACAO','PRESCRITO','Prescrição consumada','ADVOGADO','motivo'),
 (1,'ENTREVISTA','PETICAO_PENDENTE','Entrevista realizada',NULL,'entrevista_registrada'),
 (1,'ENTREVISTA','DOCUMENTACAO','Voltar para documentação',NULL,'motivo'),
 (1,'ENTREVISTA','STAND_BY','Colocar em stand by',NULL,NULL),
 (1,'ENTREVISTA','SEM_RESPOSTA','Sem resposta',NULL,NULL),
 (1,'ENTREVISTA','CANCELADO','Cancelar',NULL,'motivo'),
 (1,'ENTREVISTA','PRESCRITO','Prescrição consumada','ADVOGADO','motivo'),
 (1,'PETICAO_PENDENTE','PETICAO_EM_CRIACAO','Começar a redigir',NULL,NULL),
 (1,'PETICAO_PENDENTE','STAND_BY','Colocar em stand by',NULL,'motivo'),
 (1,'PETICAO_PENDENTE','CANCELADO','Cancelar',NULL,'motivo'),
 (1,'PETICAO_PENDENTE','PRESCRITO','Prescrição consumada','ADVOGADO','motivo'),
 (1,'PETICAO_EM_CRIACAO','PETICAO_AGUARDANDO_APROVACAO','Enviar para aprovação',NULL,'minuta_anexada'),
 (1,'PETICAO_EM_CRIACAO','ENTREVISTA','Falta informação: nova entrevista',NULL,'motivo'),
 (1,'PETICAO_EM_CRIACAO','DOCUMENTACAO','Falta documento',NULL,'motivo'),
 (1,'PETICAO_EM_CRIACAO','CANCELADO','Cancelar',NULL,'motivo'),
 (1,'PETICAO_EM_CRIACAO','PRESCRITO','Prescrição consumada','ADVOGADO','motivo'),
 (1,'PETICAO_AGUARDANDO_APROVACAO','PETICAO_APROVADA','Aprovar a inicial','GESTOR','minuta_anexada'),
 (1,'PETICAO_AGUARDANDO_APROVACAO','PETICAO_EM_CRIACAO','Devolver para ajuste','GESTOR','motivo'),
 (1,'PETICAO_AGUARDANDO_APROVACAO','CANCELADO','Cancelar','GESTOR','motivo'),
 (1,'PETICAO_APROVADA','DISTRIBUIDO','Registrar distribuição','ADVOGADO','numero_cnj,prescricao_viva'),
 (1,'PETICAO_APROVADA','PETICAO_EM_CRIACAO','Reabrir redação','ADVOGADO','motivo'),
 (1,'PETICAO_APROVADA','CANCELADO','Cancelar','ADVOGADO','motivo'),
 (1,'PETICAO_APROVADA','PRESCRITO','Prescrição consumada','ADVOGADO','motivo'),
 (1,'STAND_BY','DOCUMENTACAO','Retomar documentação',NULL,NULL),
 (1,'STAND_BY','ENTREVISTA','Retomar entrevista',NULL,NULL),
 (1,'STAND_BY','PETICAO_PENDENTE','Retomar petição',NULL,'entrevista_registrada'),
 (1,'STAND_BY','SEM_RESPOSTA','Sem resposta',NULL,NULL),
 (1,'STAND_BY','CANCELADO','Cancelar',NULL,'motivo'),
 (1,'STAND_BY','PRESCRITO','Prescrição consumada','ADVOGADO','motivo'),
 (1,'SEM_RESPOSTA','ENTREVISTA','Reabrir contato',NULL,NULL),
 (1,'SEM_RESPOSTA','CANCELADO','Cancelar',NULL,'motivo'),
 (1,'SEM_RESPOSTA','PRESCRITO','Prescrição consumada','ADVOGADO','motivo'),
 (1,'CANCELADO','DOCUMENTACAO','Reabrir o caso','GESTOR','motivo'),
 (1,'PRESCRITO','PETICAO_PENDENTE','Reanalisar prescrição','ADVOGADO','motivo'),
 (1,'DISTRIBUIDO','DOCUMENTACAO','Novo caso da mesma pessoa','ADVOGADO','motivo');

-- ---------------------------------------------------------------------
-- 2. FLUXO DO PROCESSO: da distribuição ao arquivo
--
-- É a FASE PROCESSUAL do Airtable, limpa. `EXECUÇÃO` sem qualificação não
-- existe mais: é provisória (antes do trânsito, art. 899 CLT, com número
-- próprio de CumPrSe) ou definitiva (depois dele). Quando o processo está
-- em recurso E em cumprimento provisório ao mesmo tempo (77 casos), a fase
-- é EXECUCAO_PROVISORIA: é onde o escritório trabalha; o recurso pendente
-- fica visível pelos prazos e pela tabela de recursos, não pela fase.
-- Os status internos (conhecimento, recursal, execução, cálculo, acordo,
-- pagamento) NÃO são etapa — são atributo derivado de fato registrado
-- (data de sentença, número do CumPrSe, cálculo homologado, parcela paga).
-- Ver docs/etapa-ou-atributo.md. Incidente de cliente (roubado, recuperado,
-- recebido por eles) é o fluxo 5, ligado ao processo por incidentes.processo_id.
-- SLA de 365 nas fases judiciais é o tempo além do qual vale perguntar "e
-- este?" — não é meta: o ritmo é do juízo. RECEBENDO tem 30 porque ali o
-- tempo é nosso: dinheiro na conta e cliente esperando o repasse.
-- ---------------------------------------------------------------------
INSERT INTO fluxo_etapas (fluxo_id, codigo, nome, ordem, tipo, sla_dias, grupo, texto_operador) VALUES
 (2,'CONHECIMENTO','Conhecimento',1,'INICIAL',365,'Jurídico',
  'Da distribuição à sentença. Acompanhe a pauta (audiência inicial, una ou de instrução), a defesa e a réplica, as perícias e as testemunhas. Registre a sentença assim que publicada: resultado, data e nota.'),
 (2,'RECURSAL','Recursal',2,'INTERMEDIARIA',365,'Jurídico',
  'Há recurso pendente — nosso, da reclamada ou de ambos. O grau (TRT ou TST) sai dos recursos registrados. Avalie o cumprimento provisório enquanto o recurso corre.'),
 (2,'EXECUCAO_PROVISORIA','Execução provisória',3,'INTERMEDIARIA',365,'Jurídico',
  'Cumprimento provisório de sentença (CumPrSe) aberto enquanto a reclamada recorre: liquidação e penhora até a garantia do juízo (art. 899 CLT). Sem alvará antes do trânsito, salvo caução.'),
 (2,'EXECUCAO_DEFINITIVA','Execução definitiva',4,'INTERMEDIARIA',365,'Jurídico',
  'Trânsito em julgado favorável. Cálculo → impugnação (8 dias, art. 879 §2º) → homologação → bens (Sisbajud, Renajud, Infojud) → alvará. A situação interna está em situacao_execucao.'),
 (2,'ACORDO','Acordo em cumprimento',5,'INTERMEDIARIA',365,'Jurídico',
  'Acordo homologado, parcelas correndo. Acompanhe cada vencimento. Parcela atrasada é quebra: multa da cláusula penal e execução do saldo.'),
 (2,'RECEBENDO','Recebendo',6,'INTERMEDIARIA',30,'Financeiro',
  'O dinheiro entrou (alvará ou última parcela). Separe honorários contratuais e sucumbência, registre o repasse ao cliente e o comprovante. Só depois se encerra.'),
 (2,'SOBRESTADO','Sobrestado',7,'INTERMEDIARIA',NULL,'Jurídico',
  'Suspenso por decisão do juízo (tema repetitivo, IRR, recuperação judicial da reclamada). Registre o motivo e o que destrava; ao retomar, o processo volta à fase em que estava.'),
 (2,'ENCERRADO','Encerrado',8,'FINAL',NULL,'Jurídico',
  'Acabou: arquivamento definitivo, improcedência transitada, extinção, execução satisfeita. O resultado final fica registrado — é ele que mede onde o escritório ganha e perde.'),
 (2,'DESISTENCIA','Desistência',9,'FINAL',NULL,'Jurídico',
  'O reclamante desistiu depois de ajuizar e o juízo homologou (art. 485, VIII, CPC; depois da defesa exige anuência da reclamada, art. 841 §3º CLT). Motivo obrigatório.');

INSERT INTO fluxo_transicoes (fluxo_id, de, para, acao, papel, exige) VALUES
 (2,'CONHECIMENTO','RECURSAL','Sentença publicada: recurso interposto','ADVOGADO','sentenca_registrada'),
 (2,'CONHECIMENTO','EXECUCAO_DEFINITIVA','Trânsito em julgado favorável','ADVOGADO','sentenca_registrada,transito_registrado'),
 (2,'CONHECIMENTO','ACORDO','Acordo homologado',NULL,'acordo_registrado'),
 (2,'CONHECIMENTO','SOBRESTADO','Sobrestar',NULL,'motivo'),
 (2,'CONHECIMENTO','ENCERRADO','Encerrar','ADVOGADO','resultado'),
 (2,'CONHECIMENTO','DESISTENCIA','Desistência homologada','ADVOGADO','motivo'),
 (2,'RECURSAL','EXECUCAO_PROVISORIA','Abrir cumprimento provisório','ADVOGADO','numero_cumprse'),
 (2,'RECURSAL','EXECUCAO_DEFINITIVA','Trânsito em julgado favorável','ADVOGADO','transito_registrado'),
 (2,'RECURSAL','ACORDO','Acordo homologado',NULL,'acordo_registrado'),
 (2,'RECURSAL','CONHECIMENTO','Sentença anulada: volta à origem','ADVOGADO','motivo'),
 (2,'RECURSAL','SOBRESTADO','Sobrestar',NULL,'motivo'),
 (2,'RECURSAL','ENCERRADO','Trânsito desfavorável: encerrar','ADVOGADO','transito_registrado,resultado'),
 (2,'RECURSAL','DESISTENCIA','Desistência homologada','ADVOGADO','motivo'),
 (2,'EXECUCAO_PROVISORIA','EXECUCAO_DEFINITIVA','Trânsito em julgado','ADVOGADO','transito_registrado'),
 (2,'EXECUCAO_PROVISORIA','ACORDO','Acordo homologado',NULL,'acordo_registrado'),
 (2,'EXECUCAO_PROVISORIA','SOBRESTADO','Sobrestar',NULL,'motivo'),
 (2,'EXECUCAO_PROVISORIA','ENCERRADO','Encerrar','ADVOGADO','resultado'),
 (2,'EXECUCAO_PROVISORIA','DESISTENCIA','Desistência homologada','ADVOGADO','motivo'),
 (2,'EXECUCAO_DEFINITIVA','RECEBENDO','Valor liberado',NULL,'valor_recebido'),
 (2,'EXECUCAO_DEFINITIVA','ACORDO','Acordo na execução',NULL,'acordo_registrado'),
 (2,'EXECUCAO_DEFINITIVA','SOBRESTADO','Sobrestar',NULL,'motivo'),
 (2,'EXECUCAO_DEFINITIVA','ENCERRADO','Encerrar','ADVOGADO','resultado'),
 (2,'EXECUCAO_DEFINITIVA','DESISTENCIA','Desistência homologada','ADVOGADO','motivo'),
 (2,'ACORDO','RECEBENDO','Parcelas quitadas',NULL,'parcelas_quitadas'),
 (2,'ACORDO','EXECUCAO_DEFINITIVA','Quebra de acordo: executar','ADVOGADO','motivo'),
 (2,'ACORDO','ENCERRADO','Encerrar','ADVOGADO','resultado'),
 (2,'RECEBENDO','ENCERRADO','Repasse feito: encerrar',NULL,'repasse_registrado'),
 (2,'RECEBENDO','EXECUCAO_DEFINITIVA','Saldo a executar','ADVOGADO','motivo'),
 (2,'SOBRESTADO','CONHECIMENTO','Retomar',NULL,'retorna_fase_anterior'),
 (2,'SOBRESTADO','RECURSAL','Retomar',NULL,'retorna_fase_anterior'),
 (2,'SOBRESTADO','EXECUCAO_PROVISORIA','Retomar',NULL,'retorna_fase_anterior'),
 (2,'SOBRESTADO','EXECUCAO_DEFINITIVA','Retomar',NULL,'retorna_fase_anterior'),
 (2,'SOBRESTADO','ENCERRADO','Encerrar','ADVOGADO','resultado'),
 (2,'ENCERRADO','CONHECIMENTO','Reabrir','DIRECAO','motivo'),
 (2,'ENCERRADO','EXECUCAO_DEFINITIVA','Reabrir execução','DIRECAO','motivo'),
 (2,'DESISTENCIA','CONHECIMENTO','Reabrir','DIRECAO','motivo');

-- ---------------------------------------------------------------------
-- 3. FLUXO DA AUDIÊNCIA: cada audiência é uma linha; o Airtable guardava
-- só a última e sobrescrevia a anterior. Tipo (INICIAL, INSTRUCAO, UNA,
-- HOMOLOGACAO, CONCILIACAO_EXECUCAO, JULGAMENTO) e modalidade (PRESENCIAL,
-- VIDEO) são atributos — não mudam o caminho. A preparação é um checklist
-- na própria linha (cliente_orientado_em, testemunhas_confirmadas_em,
-- advideo_em, documentos_conferidos_em); entra-se em EM_PREPARACAO quando
-- o primeiro item é feito. O alerta "audiência em menos de N dias sem
-- preparação" está em v_audiencias_sem_preparacao, com N = 7 corridos
-- [CONFIRMAR]: é o que leva confirmar testemunha (que comparece sem intimação,
-- art. 825 CLT — se falhar, pede-se intimação e é preciso tempo) e fazer o
-- ad video. Redesignada e adiada são finais: a nova data é uma linha nova,
-- ligada por redesignada_de.
-- ---------------------------------------------------------------------
INSERT INTO fluxo_etapas (fluxo_id, codigo, nome, ordem, tipo, sla_dias, grupo, texto_operador) VALUES
 (3,'DESIGNADA','Designada',1,'INICIAL',NULL,'Jurídico',
  'Data marcada pelo juízo. Confira tipo e modalidade, avise o cliente e comece a preparação com pelo menos uma semana.'),
 (3,'EM_PREPARACAO','Em preparação',2,'INTERMEDIARIA',NULL,'Jurídico',
  'Checklist: cliente orientado, testemunhas confirmadas (e intimação pedida se alguma falhar), ad video feito, documentos e cálculo de proposta prontos. Na una, a defesa vem aqui: prepare a réplica.'),
 (3,'REALIZADA','Realizada',3,'FINAL',NULL,'Jurídico',
  'Aconteceu. Registre o resultado (acordo, defesa juntada, instrução encerrada, sentença designada) e os prazos que a ata abriu.'),
 (3,'REDESIGNADA','Redesignada',4,'FINAL',NULL,'Jurídico',
  'O juízo marcou nova data. A nova audiência é outra linha, ligada a esta.'),
 (3,'ADIADA','Adiada sem data',5,'FINAL',NULL,'Jurídico',
  'Adiada sem nova data. Acompanhe o processo até a designação; aí nasce outra audiência.'),
 (3,'NAO_REALIZADA','Não realizada',6,'FINAL',NULL,'Jurídico',
  'Não aconteceu por ausência ou outro motivo. Ausência do reclamante arquiva (art. 844 CLT) e pode custar custas — registre o motivo, é perda evitável.'),
 (3,'CANCELADA','Cancelada',7,'FINAL',NULL,'Jurídico',
  'Perdeu o objeto: acordo antes da data, desistência, extinção.');

INSERT INTO fluxo_transicoes (fluxo_id, de, para, acao, papel, exige) VALUES
 (3,'DESIGNADA','EM_PREPARACAO','Iniciar preparação',NULL,NULL),
 (3,'DESIGNADA','REALIZADA','Registrar realização',NULL,'resultado_audiencia'),
 (3,'DESIGNADA','REDESIGNADA','Redesignada',NULL,'nova_audiencia'),
 (3,'DESIGNADA','ADIADA','Adiada sem data',NULL,'motivo'),
 (3,'DESIGNADA','NAO_REALIZADA','Não realizada',NULL,'motivo'),
 (3,'DESIGNADA','CANCELADA','Cancelar',NULL,'motivo'),
 (3,'EM_PREPARACAO','REALIZADA','Registrar realização',NULL,'resultado_audiencia'),
 (3,'EM_PREPARACAO','REDESIGNADA','Redesignada',NULL,'nova_audiencia'),
 (3,'EM_PREPARACAO','ADIADA','Adiada sem data',NULL,'motivo'),
 (3,'EM_PREPARACAO','NAO_REALIZADA','Não realizada',NULL,'motivo'),
 (3,'EM_PREPARACAO','CANCELADA','Cancelar',NULL,'motivo'),
 (3,'REALIZADA','EM_PREPARACAO','Registrada por engano','GESTOR','motivo');

-- ---------------------------------------------------------------------
-- 4. FLUXO DO PRAZO: o Airtable não sabia o que é prazo processual.
--
-- Um prazo nasce de uma origem (publicação no DEJT, intimação no PJe, ata
-- de audiência, despacho) e tem tipo, contagem e vencimento como atributos.
-- Contagem em DIAS ÚTEIS (art. 775 CLT), começando no primeiro dia útil
-- depois da publicação; publicação = primeiro dia útil seguinte à
-- disponibilização no DEJT (Lei 11.419/2006, art. 4º §§ 3º e 4º). Feriados:
-- nacionais + do TRT (portarias) + recesso de 20/12 a 20/01, que SUSPENDE
-- prazo (art. 775-A CLT). Intimação em audiência conta da audiência (Súmula
-- 197 TST). Tipos e dias na tabela prazo_tipos, logo abaixo.
-- SEM_OBJETO existe porque prazo que morreu por acordo ou desistência não é
-- perdido — e "perdido" é a estatística que ninguém pode sujar.
-- ---------------------------------------------------------------------
INSERT INTO fluxo_etapas (fluxo_id, codigo, nome, ordem, tipo, sla_dias, grupo, texto_operador) VALUES
 (4,'ABERTO','Aberto',1,'INICIAL',NULL,'Jurídico',
  'Prazo correndo. O vencimento está na própria linha, em dias úteis do TRT. Cumpra e registre o protocolo; o SLA aqui é o próprio vencimento.'),
 (4,'SUSPENSO','Suspenso',2,'INTERMEDIARIA',NULL,'Jurídico',
  'Suspenso por decisão do juízo, recesso ou força maior (art. 775 §1º CLT). Ao retomar, informe o novo vencimento recontado.'),
 (4,'CUMPRIDO','Cumprido',3,'FINAL',NULL,'Jurídico',
  'Peça protocolada dentro do prazo. Fica o número do protocolo e a data.'),
 (4,'PERDIDO','Perdido',4,'FINAL',NULL,'Gestão',
  'Venceu sem protocolo. Só gestor registra, com motivo — é o pior dia do escritório e precisa ser contado, não escondido.'),
 (4,'SEM_OBJETO','Sem objeto',5,'FINAL',NULL,'Jurídico',
  'O prazo deixou de existir: acordo, desistência, decisão que o tornou desnecessário. Não é perda.');

INSERT INTO fluxo_transicoes (fluxo_id, de, para, acao, papel, exige) VALUES
 (4,'ABERTO','CUMPRIDO','Cumprido: registrar protocolo',NULL,'protocolo_registrado'),
 (4,'ABERTO','SUSPENSO','Suspender',NULL,'motivo'),
 (4,'ABERTO','SEM_OBJETO','Sem objeto',NULL,'motivo'),
 (4,'ABERTO','PERDIDO','Registrar prazo perdido','GESTOR','motivo'),
 (4,'SUSPENSO','ABERTO','Retomar contagem',NULL,'novo_vencimento'),
 (4,'SUSPENSO','SEM_OBJETO','Sem objeto',NULL,'motivo'),
 (4,'CUMPRIDO','ABERTO','Reabrir (registro errado)','GESTOR','motivo'),
 (4,'SEM_OBJETO','ABERTO','Reabrir','GESTOR','motivo');

-- Os tipos de prazo que o escritório vive, com o prazo legal em dias ÚTEIS.
-- `dias` NULL = o juízo fixa; `dias_padrao` é o que o sistema sugere quando a
-- publicação não diz (CPC art. 218 §3º: 5 dias quando a lei e o juiz calam).
-- A pessoa pode corrigir o vencimento na tela; a correção fica no histórico.
CREATE TABLE prazo_tipos (
    codigo       TEXT PRIMARY KEY,
    nome         TEXT NOT NULL,
    dias         INTEGER,               -- prazo legal em dias úteis; NULL = fixado pelo juízo
    dias_padrao  INTEGER NOT NULL,      -- o que o sistema propõe
    fundamento   TEXT NOT NULL,
    fase_usual   TEXT,                  -- em que fase do processo costuma aparecer
    observacao   TEXT
);
INSERT INTO prazo_tipos (codigo, nome, dias, dias_padrao, fundamento, fase_usual, observacao) VALUES
 ('REPLICA','Manifestação sobre a defesa (réplica)',NULL,5,'Fixado pelo juízo; CPC art. 218 §3º (5 dias no silêncio) c/c CLT art. 769','CONHECIMENTO',
  'No rito ordinário a defesa vem na audiência inicial (CLT art. 847) e a réplica costuma ser em audiência ou por despacho. [CONFIRMAR: o TRT-2 dá 5, 10 ou 15 dias como regra?]'),
 ('MANIFESTACAO_DOCUMENTOS','Manifestação sobre documentos juntados',NULL,5,'CPC art. 437 §1º (15 dias) aplicado com a regra do juízo; CLT art. 769','CONHECIMENTO',
  'Na prática o juízo trabalhista fixa 5 ou 10. [CONFIRMAR o padrão do escritório]'),
 ('RAZOES_FINAIS','Razões finais',NULL,5,'CLT art. 850: 10 minutos orais; memoriais escritos no prazo que o juízo fixar','CONHECIMENTO',
  'Só existe como prazo quando o juízo converte em memoriais.'),
 ('MANIFESTACAO_LAUDO','Manifestação sobre laudo pericial',NULL,15,'CPC art. 477 §1º (15 dias) c/c CLT art. 769; o juízo pode fixar menos','CONHECIMENTO',
  'Perícia médica (nexo/incapacidade) e técnica (insalubridade/periculosidade, NR-15/NR-16). [CONFIRMAR: vara costuma dar 5, 10 ou 15?]'),
 ('EMBARGOS_DECLARACAO','Embargos de declaração',5,5,'CLT art. 897-A; CPC art. 1.023','CONHECIMENTO',
  'Interrompem o prazo do recurso principal (CPC art. 1.026). Cabem contra sentença e acórdão.'),
 ('RECURSO_ORDINARIO','Recurso ordinário (RO)',8,8,'CLT art. 895, I','CONHECIMENTO',
  'Reclamante com justiça gratuita: sem depósito recursal (CLT art. 899 §10) e sem custas (art. 790 §3º). Embargos de declaração interrompem este prazo. [CONFIRMAR: a gratuidade é pedida como regra?]'),
 ('CONTRARRAZOES','Contrarrazões',8,8,'CLT art. 900; Lei 5.584/70 art. 6º','RECURSAL',
  'Abre quando a reclamada recorre. Prazo de recurso adesivo é o mesmo (Súmula 283 TST).'),
 ('RECURSO_ADESIVO','Recurso adesivo',8,8,'CPC art. 997 §2º; Súmula 283 TST','RECURSAL',NULL),
 ('RECURSO_REVISTA','Recurso de revista (RR)',8,8,'CLT art. 896; Lei 5.584/70 art. 6º','RECURSAL',
  'No sumaríssimo só por contrariedade a súmula do TST/súmula vinculante ou violação direta da CF (art. 896 §9º).'),
 ('AGRAVO_INSTRUMENTO','Agravo de instrumento (AIRR)',8,8,'CLT art. 897, b','RECURSAL',
  'Contra despacho que nega seguimento ao RR. Depósito de 50% do valor do recurso (art. 899 §7º) — não se aplica ao reclamante beneficiário da gratuidade.'),
 ('AGRAVO_INTERNO','Agravo interno / regimental',8,8,'CLT art. 896 §12 e regimento; Lei 5.584/70 art. 6º','RECURSAL',NULL),
 ('EMBARGOS_TST','Embargos à SDI (TST)',8,8,'CLT art. 894, II','RECURSAL',NULL),
 ('IMPUGNACAO_CALCULOS','Impugnação aos cálculos de liquidação',8,8,'CLT art. 879 §2º','EXECUCAO_DEFINITIVA',
  'Sob pena de preclusão; deve indicar item e valor. Também vale na execução provisória.'),
 ('IMPUGNACAO_SENTENCA_LIQUIDACAO','Impugnação à sentença de liquidação (exequente)',5,5,'CLT art. 884 §3º','EXECUCAO_DEFINITIVA',
  'Mesmo prazo dos embargos do executado (5 dias da garantia do juízo).'),
 ('AGRAVO_PETICAO','Agravo de petição (AP)',8,8,'CLT art. 897, a','EXECUCAO_DEFINITIVA',
  'Contra decisão na execução (homologação de cálculo, extinção). Exige delimitação de matéria e valores (§1º).'),
 ('MANIFESTACAO_EXECUCAO','Manifestação na execução (bens, alvará, andamento)',NULL,5,'Fixado pelo juízo; CPC art. 218 §3º','EXECUCAO_DEFINITIVA',
  'Inclui manifestar sobre pesquisa patrimonial negativa e sobre proposta de parcelamento (CPC art. 916, se admitido).'),
 ('EMENDA_INICIAL','Emenda à inicial',15,15,'CPC art. 321 c/c CLT art. 769','CONHECIMENTO',
  'Sob pena de indeferimento. [CONFIRMAR: alguma vara fixa 10?]'),
 ('OUTRO','Outro prazo fixado pelo juízo',NULL,5,'CPC art. 218 §3º',NULL,
  'Use só quando nenhum tipo acima serve; o nome do ato vai na descrição.');

-- ---------------------------------------------------------------------
-- 5. FLUXO DO INCIDENTE DE REPRESENTAÇÃO: o cliente trocou de advogado.
--
-- ROUBADO / RECEBIDO POR ELES / RECUPERADO / REVOGAÇÃO / NOTIFICAÇÃO /
-- PROVIDENCIAS ("NOTIFICAR", "TRAVAR O RECEBIMENTO") viviam em STATUS DO
-- PROCESSO e em campos soltos. Não são fase: o processo continua em juízo
-- com outro patrono. É um ciclo à parte, ligado por incidentes.processo_id,
-- com tipo (TROCA_DE_ADVOGADO, REVOGACAO_PELO_CLIENTE, [CONFIRMAR outros])
-- e as datas como atributos (revogacao_nos_autos_em, notificacao_redigida_em,
-- notificacao_recebida_em, resposta_em, cliente_avisado_em). O objetivo é
-- receber os honorários pelo trabalho feito (EOAB art. 22 §4º: reserva nos
-- autos) ou trazer o cliente de volta. Enquanto há incidente aberto, a ficha
-- do processo mostra o sinal — e o RECEBENDO do processo alerta antes de
-- repassar. [CONFIRMAR pergunta 21: quem faz cada passo; pergunta 20: os dois
-- sentidos de REVOGAÇÃO.]
-- ---------------------------------------------------------------------
INSERT INTO fluxo_etapas (fluxo_id, codigo, nome, ordem, tipo, sla_dias, grupo, texto_operador) VALUES
 (5,'DETECTADO','Detectado',1,'INICIAL',5,'Jurídico',
  'Apareceu outro patrono nos autos ou o cliente avisou. Confirme nos autos (há revogação juntada?), avise o cliente e decida: notificar ou tentar trazer de volta.'),
 (5,'NOTIFICADO','Notificado',2,'INTERMEDIARIA',30,'Jurídico',
  'Notificação extrajudicial enviada cobrando os honorários pelo trabalho feito. Registre recebimento e resposta. Sem resposta em 30 dias, peça a reserva nos autos.'),
 (5,'HONORARIOS_RESERVADOS','Honorários reservados nos autos',3,'INTERMEDIARIA',NULL,'Jurídico',
  'Pedido de reserva/destaque dos honorários protocolado (EOAB art. 22 §4º). O juízo trava a parcela; acompanhe o pagamento junto com a execução.'),
 (5,'RECUPERADO','Cliente recuperado',4,'FINAL',NULL,'Jurídico',
  'O cliente voltou. Confira a procuração nova nos autos e a revogação do outro patrono.'),
 (5,'HONORARIOS_RECEBIDOS','Honorários recebidos',5,'FINAL',NULL,'Financeiro',
  'O escritório recebeu o que lhe cabia pelo trabalho feito. Registre o valor.'),
 (5,'PERDIDO','Perdido',6,'FINAL',NULL,'Direção',
  'Cliente e honorários perdidos ("recebido por eles"). Só a direção fecha assim, com motivo — é o número que mede o roubo de cliente.'),
 (5,'SEM_OBJETO','Alarme falso',7,'FINAL',NULL,'Jurídico',
  'Não houve troca: era substabelecimento nosso, homônimo ou erro de leitura.');

INSERT INTO fluxo_transicoes (fluxo_id, de, para, acao, papel, exige) VALUES
 (5,'DETECTADO','NOTIFICADO','Notificação enviada',NULL,'notificacao_enviada'),
 (5,'DETECTADO','HONORARIOS_RESERVADOS','Reserva pedida ao juízo','ADVOGADO','peticao_reserva'),
 (5,'DETECTADO','RECUPERADO','Cliente voltou',NULL,NULL),
 (5,'DETECTADO','SEM_OBJETO','Alarme falso',NULL,'motivo'),
 (5,'NOTIFICADO','HONORARIOS_RESERVADOS','Reserva pedida ao juízo','ADVOGADO','peticao_reserva'),
 (5,'NOTIFICADO','HONORARIOS_RECEBIDOS','Honorários recebidos',NULL,'valor_recebido'),
 (5,'NOTIFICADO','RECUPERADO','Cliente voltou',NULL,NULL),
 (5,'NOTIFICADO','PERDIDO','Dar por perdido','DIRECAO','motivo'),
 (5,'HONORARIOS_RESERVADOS','HONORARIOS_RECEBIDOS','Honorários recebidos',NULL,'valor_recebido'),
 (5,'HONORARIOS_RESERVADOS','RECUPERADO','Cliente voltou',NULL,NULL),
 (5,'HONORARIOS_RESERVADOS','PERDIDO','Dar por perdido','DIRECAO','motivo'),
 (5,'PERDIDO','NOTIFICADO','Reabrir cobrança','DIRECAO','motivo');

-- ---------------------------------------------------------------------
-- O TEXTO QUE A PESSOA LÊ quando a ação está travada. Um por gate, aplicado
-- a toda transição que o exige — a chave natural já é a transição, não
-- precisa de tabela à parte. Transição com dois gates recebe o primeiro; a
-- tela junta as razões técnicas (fluxo.py) de qualquer jeito.
-- ---------------------------------------------------------------------
UPDATE fluxo_transicoes SET texto_bloqueio = CASE
  WHEN exige = 'motivo' THEN 'Escreva o motivo no campo desta janela. Mudança sem motivo não deixa rastro para quem vier depois.'
  WHEN exige = 'contrato_assinado' THEN 'Falta o contrato de honorários e a procuração assinados, com data. Sem eles o escritório não representa ninguém.'
  WHEN exige = 'documentos_obrigatorios' THEN 'Ainda falta documento obrigatório (TRCT, CTPS, RG/CNH). Marque cada um como recebido ou dispensado, com motivo.'
  WHEN exige = 'entrevista_registrada' THEN 'Registre a entrevista: data, entrevistador e resumo. É o que a petição vai usar.'
  WHEN exige = 'minuta_anexada' THEN 'Anexe a minuta da inicial na ficha. Não se aprova o que não está escrito.'
  WHEN exige LIKE 'numero_cnj%' THEN 'Informe o número CNJ com 20 dígitos. Se a prescrição bienal venceu, registre a dispensa justificada antes — sem isso o sistema não distribui.'
  WHEN exige LIKE 'sentenca_registrada%' THEN 'Registre a sentença (resultado objetivo, data e nota) antes de mudar de fase — é isso que alimenta o mapa de onde estamos perdendo.'
  WHEN exige LIKE 'transito_registrado%' THEN 'Informe a data do trânsito em julgado e a decisão que transitou.'
  WHEN exige = 'acordo_registrado' THEN 'Registre o acordo: valor, número de parcelas, vencimentos e data da homologação.'
  WHEN exige = 'numero_cumprse' THEN 'Informe o número do cumprimento provisório de sentença (CumPrSe).'
  WHEN exige = 'resultado' THEN 'Informe o resultado final do processo antes de encerrar.'
  WHEN exige = 'valor_recebido' THEN 'Registre o valor efetivamente recebido, a data e o comprovante (alvará ou depósito).'
  WHEN exige = 'parcelas_quitadas' THEN 'Há parcela do acordo sem pagamento registrado. Registre cada uma ou mude para quebra de acordo.'
  WHEN exige = 'repasse_registrado' THEN 'Registre o repasse ao cliente (valor, data, comprovante) ou marque que não há valor a repassar, com motivo.'
  WHEN exige = 'retorna_fase_anterior' THEN 'Sobrestado só volta para a fase em que estava antes. O histórico diz qual é.'
  WHEN exige = 'resultado_audiencia' THEN 'Registre o que aconteceu na audiência: acordo, defesa juntada, instrução encerrada, sentença designada.'
  WHEN exige = 'nova_audiencia' THEN 'Cadastre primeiro a nova audiência com a data redesignada, ligada a esta.'
  WHEN exige = 'protocolo_registrado' THEN 'Informe a data do protocolo e junte a peça (ou o número do protocolo do PJe).'
  WHEN exige = 'novo_vencimento' THEN 'Informe o novo vencimento recontado em dias úteis a partir da retomada.'
  WHEN exige = 'notificacao_enviada' THEN 'Registre a data de envio da notificação extrajudicial e anexe a cópia.'
  WHEN exige = 'peticao_reserva' THEN 'Anexe a petição de reserva de honorários protocolada nos autos (EOAB art. 22 §4º).'
END
WHERE exige IS NOT NULL;

-- =====================================================================
-- >>> SÓ POSTGRES DAQUI PARA BAIXO. Depende do esquema (dba-migracao).
--
-- Contrato com o esquema — as colunas que os gates de fluxo.py leem:
--   clientes:   status, data_assinatura_contrato, data_demissao, contrato_vivo (bool),
--               dispensa_prescricao_motivo, entrevista_em, entrevista_resumo
--   documentos_pendentes(cliente_id, tipo, obrigatorio, recebido_em, dispensado_motivo)
--   peticoes(cliente_id, tipo='INICIAL', arquivo_id, versao)
--   processos:  fase, numero_cnj, cliente_id, resultado_final, fase_anterior (via histórico),
--               numero_cumprse, transito_em, situacao_execucao
--   decisoes(processo_id, tipo IN ('SENTENCA','ACORDAO','DESPACHO'), data, resultado_objetivo, nota)
--   acordos(processo_id, valor_centavos, parcelas, homologado_em) + acordo_parcelas(vencimento, pago_em)
--   recebimentos(processo_id, valor_centavos, data, comprovante_id)
--   repasses(processo_id, valor_centavos, data, comprovante_id, sem_valor_motivo)
--   audiencias: situacao, processo_id, data_hora, tipo, modalidade, resultado, redesignada_de,
--               cliente_orientado_em, testemunhas_confirmadas_em, advideo_em, documentos_conferidos_em
--   prazos:     situacao, processo_id, tipo (FK prazo_tipos), origem, disponibilizado_em,
--               publicado_em, inicio, vencimento, cumprido_em, protocolo, motivo
--   incidentes: situacao, processo_id, tipo, notificacao_enviada_em, peticao_reserva_id,
--               valor_recebido_centavos
-- =====================================================================

CREATE OR REPLACE FUNCTION gov_transicao() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE
  fluxo_codigo TEXT := TG_ARGV[0];
  campo        TEXT := TG_ARGV[1];
  antes TEXT; depois TEXT;
BEGIN
  EXECUTE format('SELECT ($1).%I, ($2).%I', campo, campo) INTO antes, depois USING OLD, NEW;
  IF antes IS DISTINCT FROM depois THEN
    IF NOT EXISTS (SELECT 1 FROM fluxo_transicoes t JOIN fluxos f ON f.id = t.fluxo_id
                   WHERE f.codigo = fluxo_codigo AND t.de = antes AND t.para = depois) THEN
      RAISE EXCEPTION 'transição de % fora do fluxo %: % → %', campo, fluxo_codigo, antes, depois;
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION gov_historico() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE
  entidade TEXT := TG_ARGV[0];
  campo    TEXT := TG_ARGV[1];
  antes TEXT; depois TEXT;
BEGIN
  EXECUTE format('SELECT ($1).%I, ($2).%I', campo, campo) INTO antes, depois USING OLD, NEW;
  IF antes IS DISTINCT FROM depois THEN
    INSERT INTO historico_etapas (entidade, entidade_id, de, para) VALUES (entidade, NEW.id, antes, depois);
  END IF;
  RETURN NULL;
END $$;

-- Etapa inicial é a única porta de entrada: um INSERT já numa etapa do meio
-- é a migração pulando o mapa. A migração desliga o gatilho de propósito
-- (ALTER TABLE ... DISABLE TRIGGER) e religa no fim, como o Prev faz no --baixar.
CREATE OR REPLACE FUNCTION gov_nasce_na_inicial() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE
  fluxo_codigo TEXT := TG_ARGV[0];
  campo        TEXT := TG_ARGV[1];
  valor TEXT;
BEGIN
  EXECUTE format('SELECT ($1).%I', campo) INTO valor USING NEW;
  IF valor IS NULL THEN
    RAISE EXCEPTION '% precisa nascer com % preenchido (etapa inicial do fluxo %)', TG_TABLE_NAME, campo, fluxo_codigo;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM fluxo_etapas e JOIN fluxos f ON f.id = e.fluxo_id
                 WHERE f.codigo = fluxo_codigo AND e.codigo = valor AND e.tipo = 'INICIAL') THEN
    RAISE EXCEPTION '% não pode nascer em %: só na etapa inicial do fluxo %', TG_TABLE_NAME, valor, fluxo_codigo;
  END IF;
  RETURN NEW;
END $$;

-- Cinco tabelas, três gatilhos cada: recusa, histórico, nascimento.
DROP TRIGGER IF EXISTS tg_gov_cliente   ON clientes;   CREATE TRIGGER tg_gov_cliente   BEFORE UPDATE OF status   ON clientes   FOR EACH ROW EXECUTE FUNCTION gov_transicao('CLIENTE','status');
DROP TRIGGER IF EXISTS tg_gov_processo  ON processos;  CREATE TRIGGER tg_gov_processo  BEFORE UPDATE OF fase     ON processos  FOR EACH ROW EXECUTE FUNCTION gov_transicao('PROCESSO','fase');
DROP TRIGGER IF EXISTS tg_gov_audiencia ON audiencias; CREATE TRIGGER tg_gov_audiencia BEFORE UPDATE OF situacao ON audiencias FOR EACH ROW EXECUTE FUNCTION gov_transicao('AUDIENCIA','situacao');
DROP TRIGGER IF EXISTS tg_gov_prazo     ON prazos;     CREATE TRIGGER tg_gov_prazo     BEFORE UPDATE OF situacao ON prazos     FOR EACH ROW EXECUTE FUNCTION gov_transicao('PRAZO','situacao');
DROP TRIGGER IF EXISTS tg_gov_incidente ON incidentes; CREATE TRIGGER tg_gov_incidente BEFORE UPDATE OF situacao ON incidentes FOR EACH ROW EXECUTE FUNCTION gov_transicao('INCIDENTE','situacao');

DROP TRIGGER IF EXISTS tg_hist_cliente   ON clientes;   CREATE TRIGGER tg_hist_cliente   AFTER UPDATE OF status   ON clientes   FOR EACH ROW EXECUTE FUNCTION gov_historico('clientes','status');
DROP TRIGGER IF EXISTS tg_hist_processo  ON processos;  CREATE TRIGGER tg_hist_processo  AFTER UPDATE OF fase     ON processos  FOR EACH ROW EXECUTE FUNCTION gov_historico('processos','fase');
DROP TRIGGER IF EXISTS tg_hist_audiencia ON audiencias; CREATE TRIGGER tg_hist_audiencia AFTER UPDATE OF situacao ON audiencias FOR EACH ROW EXECUTE FUNCTION gov_historico('audiencias','situacao');
DROP TRIGGER IF EXISTS tg_hist_prazo     ON prazos;     CREATE TRIGGER tg_hist_prazo     AFTER UPDATE OF situacao ON prazos     FOR EACH ROW EXECUTE FUNCTION gov_historico('prazos','situacao');
DROP TRIGGER IF EXISTS tg_hist_incidente ON incidentes; CREATE TRIGGER tg_hist_incidente AFTER UPDATE OF situacao ON incidentes FOR EACH ROW EXECUTE FUNCTION gov_historico('incidentes','situacao');

DROP TRIGGER IF EXISTS tg_nasce_cliente   ON clientes;   CREATE TRIGGER tg_nasce_cliente   BEFORE INSERT ON clientes   FOR EACH ROW EXECUTE FUNCTION gov_nasce_na_inicial('CLIENTE','status');
DROP TRIGGER IF EXISTS tg_nasce_processo  ON processos;  CREATE TRIGGER tg_nasce_processo  BEFORE INSERT ON processos  FOR EACH ROW EXECUTE FUNCTION gov_nasce_na_inicial('PROCESSO','fase');
DROP TRIGGER IF EXISTS tg_nasce_audiencia ON audiencias; CREATE TRIGGER tg_nasce_audiencia BEFORE INSERT ON audiencias FOR EACH ROW EXECUTE FUNCTION gov_nasce_na_inicial('AUDIENCIA','situacao');
DROP TRIGGER IF EXISTS tg_nasce_prazo     ON prazos;     CREATE TRIGGER tg_nasce_prazo     BEFORE INSERT ON prazos     FOR EACH ROW EXECUTE FUNCTION gov_nasce_na_inicial('PRAZO','situacao');
DROP TRIGGER IF EXISTS tg_nasce_incidente ON incidentes; CREATE TRIGGER tg_nasce_incidente BEFORE INSERT ON incidentes FOR EACH ROW EXECUTE FUNCTION gov_nasce_na_inicial('INCIDENTE','situacao');

-- Os dois gates que o BANCO garante sozinho (o equivalente ao Tema 350 do Prev).
-- 1. Prazo processual conta em dias úteis (CLT art. 775). Prazo em dias
--    corridos só com justificativa escrita — é o erro que faz descartar prazo vivo.
-- 2. Prazo não fecha sem registro: CUMPRIDO exige cumprido_em; PERDIDO exige motivo.
CREATE OR REPLACE FUNCTION gov_prazo_regras() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
  IF NEW.contagem IS DISTINCT FROM 'UTEIS' AND COALESCE(NEW.contagem_motivo,'') = '' THEN
    RAISE EXCEPTION 'prazo trabalhista conta em dias úteis (CLT art. 775); contagem % exige contagem_motivo', NEW.contagem;
  END IF;
  IF NEW.situacao = 'CUMPRIDO' AND NEW.cumprido_em IS NULL THEN
    RAISE EXCEPTION 'prazo CUMPRIDO exige cumprido_em';
  END IF;
  IF NEW.situacao = 'PERDIDO' AND COALESCE(NEW.motivo,'') = '' THEN
    RAISE EXCEPTION 'prazo PERDIDO exige motivo';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS tg_gov_prazo_regras ON prazos;
CREATE TRIGGER tg_gov_prazo_regras BEFORE INSERT OR UPDATE ON prazos FOR EACH ROW EXECUTE FUNCTION gov_prazo_regras();

-- Ação trabalhista depois da prescrição bienal: recusada no nascimento do
-- processo, salvo dispensa justificada na ficha do cliente (contrato vivo,
-- causa interruptiva, decisão de assumir o risco). Espelho do Tema 350 do Prev.
CREATE OR REPLACE FUNCTION gov_prescricao_bienal() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE c RECORD;
BEGIN
  SELECT data_demissao, contrato_vivo, dispensa_prescricao_motivo INTO c FROM clientes WHERE id = NEW.cliente_id;
  IF c.data_demissao IS NOT NULL AND NOT COALESCE(c.contrato_vivo, false)
     AND (c.data_demissao::date + INTERVAL '2 years') < (now() AT TIME ZONE 'America/Sao_Paulo')::date
     AND COALESCE(c.dispensa_prescricao_motivo,'') = '' THEN
    RAISE EXCEPTION 'prescrição bienal consumada (CF art. 7º XXIX; CLT art. 11): registre dispensa_prescricao_motivo na ficha do cliente antes de abrir o processo';
  END IF;
  RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS tg_gov_prescricao_bienal ON processos;
CREATE TRIGGER tg_gov_prescricao_bienal BEFORE INSERT ON processos FOR EACH ROW EXECUTE FUNCTION gov_prescricao_bienal();

-- ---------------------------------------------------------------------
-- VISÕES DE GOVERNANÇA (o número na tela sai daqui, nunca do template)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_funil_etapas AS
SELECT f.codigo AS fluxo, fe.ordem, fe.codigo, fe.nome AS etapa, fe.tipo, fe.grupo, fe.sla_dias,
       CASE f.codigo
         WHEN 'CLIENTE'   THEN (SELECT COUNT(*) FROM clientes   x WHERE x.status   = fe.codigo)
         WHEN 'PROCESSO'  THEN (SELECT COUNT(*) FROM processos  x WHERE x.fase     = fe.codigo)
         WHEN 'AUDIENCIA' THEN (SELECT COUNT(*) FROM audiencias x WHERE x.situacao = fe.codigo)
         WHEN 'PRAZO'     THEN (SELECT COUNT(*) FROM prazos     x WHERE x.situacao = fe.codigo)
         WHEN 'INCIDENTE' THEN (SELECT COUNT(*) FROM incidentes x WHERE x.situacao = fe.codigo)
       END AS registros
FROM fluxos f JOIN fluxo_etapas fe ON fe.fluxo_id = f.id;

-- Parado além do SLA da etapa, em qualquer fluxo com sla_dias.
CREATE OR REPLACE VIEW v_estagnados AS
WITH alvo AS (
  SELECT 'clientes' AS entidade, id, status AS etapa, criado_em FROM clientes
  UNION ALL SELECT 'processos', id, fase, criado_em FROM processos
  UNION ALL SELECT 'incidentes', id, situacao, criado_em FROM incidentes
)
SELECT a.entidade, a.id, a.etapa, fe.nome, fe.sla_dias, fe.grupo,
       ((now() AT TIME ZONE 'America/Sao_Paulo')::date
        - (substr(COALESCE((SELECT MAX(h.em) FROM historico_etapas h
                            WHERE h.entidade = a.entidade AND h.entidade_id = a.id), a.criado_em),1,10))::date) AS dias_parado
FROM alvo a
JOIN fluxos f ON f.entidade = a.entidade
JOIN fluxo_etapas fe ON fe.fluxo_id = f.id AND fe.codigo = a.etapa
WHERE fe.tipo <> 'FINAL' AND fe.sla_dias IS NOT NULL
  AND ((now() AT TIME ZONE 'America/Sao_Paulo')::date
       - (substr(COALESCE((SELECT MAX(h.em) FROM historico_etapas h
                           WHERE h.entidade = a.entidade AND h.entidade_id = a.id), a.criado_em),1,10))::date) > fe.sla_dias;

-- O SLA do pré-processual inteiro: dias desde a assinatura, ainda sem distribuir.
-- 15 amarelo, 20 vermelho [CONFIRMAR 6]; rescisão indireta: 15 já é vermelho.
CREATE OR REPLACE VIEW v_pre_processual_atrasado AS
SELECT c.id, c.status, c.rescisao_modalidade,
       ((now() AT TIME ZONE 'America/Sao_Paulo')::date - c.data_assinatura_contrato::date) AS dias_desde_assinatura,
       CASE
         WHEN c.rescisao_modalidade = 'RESCISAO_INDIRETA'
              AND (now() AT TIME ZONE 'America/Sao_Paulo')::date - c.data_assinatura_contrato::date >= 15 THEN 'VERMELHO'
         WHEN (now() AT TIME ZONE 'America/Sao_Paulo')::date - c.data_assinatura_contrato::date >= 20 THEN 'VERMELHO'
         WHEN (now() AT TIME ZONE 'America/Sao_Paulo')::date - c.data_assinatura_contrato::date >= 15 THEN 'AMARELO'
       END AS farol,
       CASE WHEN c.data_demissao IS NOT NULL AND NOT COALESCE(c.contrato_vivo,false)
            THEN (c.data_demissao::date + INTERVAL '2 years')::date END AS prescreve_em
FROM clientes c
JOIN fluxo_etapas fe ON fe.fluxo_id = 1 AND fe.codigo = c.status
WHERE fe.tipo <> 'FINAL' AND c.data_assinatura_contrato IS NOT NULL;

-- Audiência em menos de N dias sem nenhum item do checklist. N = 7 [CONFIRMAR].
CREATE OR REPLACE VIEW v_audiencias_sem_preparacao AS
SELECT a.id, a.processo_id, a.tipo, a.modalidade, a.data_hora,
       (substr(a.data_hora,1,10)::date - (now() AT TIME ZONE 'America/Sao_Paulo')::date) AS dias_para_audiencia
FROM audiencias a
WHERE a.situacao IN ('DESIGNADA','EM_PREPARACAO')
  AND substr(a.data_hora,1,10)::date <= (now() AT TIME ZONE 'America/Sao_Paulo')::date + 7
  AND a.cliente_orientado_em IS NULL AND a.testemunhas_confirmadas_em IS NULL
  AND a.advideo_em IS NULL AND a.documentos_conferidos_em IS NULL;

-- Prazos abertos por vencimento, o mais perto primeiro.
CREATE OR REPLACE VIEW v_prazos_criticos AS
SELECT pz.id, pz.processo_id, pz.tipo, pt.nome AS tipo_nome, pz.vencimento,
       (pz.vencimento::date - (now() AT TIME ZONE 'America/Sao_Paulo')::date) AS dias,
       pz.responsavel_id
FROM prazos pz LEFT JOIN prazo_tipos pt ON pt.codigo = pz.tipo
WHERE pz.situacao = 'ABERTO'
ORDER BY pz.vencimento;
