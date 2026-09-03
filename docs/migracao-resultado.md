# Resultado da migração — a carga REAL, provada

> 03/09/2026, segunda rodada do DBA de migração. Nenhum nome de cliente, CPF, telefone, e-mail ou
> número de processo aparece aqui — só contagens.

## Onde a coisa está, em uma frase

**A carga completa da base real rodou num Postgres 16 local e terminou em TUDO CONFERE** — pela
carga direta (psycopg) e pelo plano B (o SQL gerado, aplicado num banco vazio), com os dois bancos
iguais linha a linha. Não se conectou ao Supabase nesta rodada: a carga lá depende da URI que só o
Lucas tem, e o esquema `public` de lá continua como a rodada anterior deixou (35 tabelas, RLS em
todas, sem `governanca.sql` aplicada). Rodar lá é o comando do fim deste arquivo.

## Como os dados chegaram sem o token do Airtable

O agente Leitor baixou as dez tabelas pelo **conector MCP do Airtable** (somente leitura). O
conector devolve outra forma que a API REST — `records[].cellValuesByFieldId` com o id do campo
como chave, select como objeto `{id,name,color}`, link como `[{id,name}]`, lookup como
`{linkedRecordIds, valuesByLinkedRecordId}`, colaborador com `permissionLevel` e foto. `do_conector.py`
converte para a forma que `migrar.py` já lia (`fields` por NOME, select como texto, link como
lista de `rec…`), e **recusa** duas coisas: id de campo sem nome no mapa e forma de valor que não
conhece. Nas duas o resultado seria perda calada.

```bash
./.venv/bin/python migrar.py --do-conector --origem PASTA   # ou: do_conector.py --origem PASTA
./.venv/bin/python migrar.py --recriar                      # esquema + governança + carga
./.venv/bin/python conferir.py                              # só passa com TUDO CONFERE
```

A conversão real: **10.412 registros em 10 tabelas, 350 campos, nenhum sem nome, nenhuma forma
desconhecida**. As formas convertidas: 137.921 escalares, 59.823 selects, 21.704 links, 7.595
botões, 5.253 lookups, 4.146 colaboradores, 1.757 multi-selects, 7 anexos. Um único aviso:
FUNCIONARIOS tem dois campos chamados "PROCESSUAL copy" (links inversos); o segundo recebeu o
sufixo `[fld…]` para nenhum dos dois sumir. A conferência cruzada com o schema bruto (que cobre
8 das 10 tabelas — CÓPIA e AUDITORIA não estão nele) não achou discordância de tipo.

## O que entrou — linhas por tabela

| tabela | linhas | | tabela | linhas |
|---|---:|---|---|---:|
| pessoas | 72 | | decisoes | 3.668 |
| pessoa_papeis | 92 | | recursos | 2.470 |
| empresas | 1.103 | | calculos | 1.755 |
| fragilidades | 17 | | acordos | 1.393 |
| clientes | **3.067** (797 da PRÉ + 2.270 criados dos autos) | | recebimentos | 2.428 |
| pendencias | 2.235 | | incidentes | 226 |
| processos | **3.855** | | tarefas | 202 |
| processo_alias | 653 | | eventos | 3.432 |
| audiencias | 3.035 | | contatos | 164 |
| pericias | 15 | | anotacoes | 990 |
| testemunhas | 424 | | documentos (metadado de anexo) | 8 (4.320.523 bytes) |
| testemunha_vinculos | 510 | | automacao_log | 1.629 |
| testemunha_auditoria | 2 | | historico_etapas | 10.183 |
| conferencia_faltantes | 1.067 | | conferencias | **3.300** |

Zero, de propósito: `acordo_parcelas`, `repasses`, `prazos`, `peticoes`, `usuarios`,
`automacoes`, `auditoria` — nascem no sistema, não na origem. `fluxos`, `fluxo_etapas`,
`fluxo_transicoes` e `prazo_tipos` vêm de `governanca.sql` (5 / 40 / 111 / 18).

Contas que fecham: 3.855 processos = 3.722 da CÓPIA − 3 `INAPLICÁVEL` + 136 da PROCESSUAL que
não casaram por CNJ (106 sem número, 22 só nela, 8 duplicados). Dos 3.719 vindos da CÓPIA, 2.516
casaram com um registro da PROCESSUAL e trazem os dois lados no `airtable_bruto`.

## A prova, por tipo — o que `conferir.py` recalcula da origem e compara

| tipo de conferência | linhas | resultado |
|---|---:|---|
| contagem por tabela (inclui anexos, bytes de anexo, pendências, audiências, perícias, histórico, testemunhas sem nome) | 19 | ok |
| contagem por opção de select (papel, situação de empresa/testemunha, modalidade da rescisão, canal/campanha, documento pendente, turma/órgão, etapa do cliente, fase, situação da execução, tipo de audiência, resultado da sentença e do acórdão, situação do acordo) | 112 | ok |
| soma de cada campo em R$, ao centavo (valor da causa, 9 campos de cálculo, acordo, honorário, parcela, 4 bases de recebimento, fragilidades, faltantes) + valor implausível → conferência | 20 | ok |
| cada ligação do Airtable (13 FKs: clientes, processos, testemunhas, fragilidades, faltantes; testemunha×processo 336, testemunha×cliente 174) | 13 | ok |
| integridade (record repetido, bruto ausente, fase e etapa fora do mapa, histórico, gatilhos ligados, sequências, RLS, STATUS EXECUÇÃO conferido ou aplicado) | 18 | ok |
| **total** | **182 linhas** | **TUDO CONFERE** |

Somas que atravessaram inteiras (em centavos): valor da causa 69.961.541.433; cálculo do
reclamante 4.431.877.169; homologado 6.773.521.615; acordos 2.929.091.297; recebido total
3.751.889.977; honorários recebidos 1.608.767.575; faltantes 9.438.361.012.

Provado também: **recarregar sem `--recriar` preserva o trabalho humano** — duas conferências
marcadas à mão (uma RESOLVIDA com dono, anotação e data; uma IGNORADA) voltaram intactas depois
da recarga, e a prova seguiu passando. E o **plano B** (`dados/carga_real.sql`, 36.673.158 bytes,
53.369 linhas, 48.224 INSERTs, gerado em 2 s) aplicado com `psql -v ON_ERROR_STOP=1` num banco
vazio em 25 s deu TUDO CONFERE e as mesmas contagens em todas as tabelas. É o caminho para subir
ao Supabase sem URI, em blocos pelo `apply_migration`. Fica em `dados/`, fora do git.

## Quantos valores foram normalizados, de/para — os campos poluídos

| campo | preenchidos | traduzidos | ficaram só no `_original` + conferência |
|---|---:|---:|---:|
| RESCISAO (PRÉ, texto livre) | 666 | 565: 330 SEM_JUSTA_CAUSA · 101 RESCISAO_INDIRETA · 86 PEDIDO_DEMISSAO · 40 JUSTA_CAUSA · 7 CONTRATO_VIVO · 1 TERMINO_CONTRATO | 101 (75 trazem data/telefone, 26 texto sem modalidade) |
| STATUS EXECUÇÃO (PROCESSUAL vence; 36 opções) | 810 na CÓPIA, 615 na PROCESSUAL | 629 estados limpos em 12 valores (298 AGUARDANDO_CALCULO, 76 EM_RECURSO_EXECUCAO, 61 AGUARDANDO_TRANSITO, 57 HOMOLOGADO, 53 CALCULOS_APRESENTADOS, 34 PESQUISA_PATRIMONIAL, 23 AGUARDANDO_ALVARA, 11 RECEBIDO, 7 PARCELAMENTO_916, 5 PERICIA_CONTABIL, 1 NEGOCIANDO_ACORDO) | 243: 45 poluídos (SIM/NÃO/EXECUÇÃO/RECURSAL) + 198 na coluna errada, dos quais 174 coerentes com a fase (aplicados ou nada a fazer) e 24 em conferência |
| FASE PROCESSUAL (CÓPIA) | 3.722 | 3.719 em 9 fases: 2.638 ENCERRADO · 646 CONHECIMENTO · 449 RECURSAL · 74 EXEC. DEFINITIVA · 19 EXEC. PROVISÓRIA · 15 ACORDO · 12 SOBRESTADO · 1 RECEBENDO · 1 DESISTENCIA | 3 INAPLICÁVEL (fora do escopo) + 66 "EXECUÇÃO" sem CumPrSe nem trânsito (entram DEFINITIVA com conferência) |
| STATUS DO PROCESSO (CÓPIA) | 3.722 | 2.549 ARQUIVADO → resultado_final · 174 ROUBADO/RECEBIDO POR ELES/RECUPERADO → incidentes · 25 TRÂNSITO → transito_em · 12 SOBRESTADO → fase · 625 derivados (aguardando audiência/sentença/acórdão) | 0 |
| TURMA (CÓPIA, texto) | 1.411 | 1.411: 20 turmas, 1 câmara, 4 órgãos — 270 "VICE-PRESIDÊNCIA JUDICIA" (texto cortado em 24 caracteres) viraram VICE-PRESIDÊNCIA JUDICIAL por prefixo | 0 (o "11" da PROCESSUAL nunca vence a CÓPIA) |
| TRT (CÓPIA) | 3.722 | 3.722 em 19 números; 108 processos sem TRT em nenhuma das fontes | 0 |
| CLASSIFICACAO | 3.674 | 3.377 classe+rito (2.701 AT ordinário, 378 AT sumaríssimo, 302 RT ordinário) · 305 classe de incidente (194 exec. provisória, 105 definitiva, 6 embargos de terceiro) | 0 |
| AUDIENCIA (tipo + modalidade + rito no mesmo campo) | 2.898 | 2.914 audiências com tipo (1.479 UNA, 1.012 INSTRUÇÃO, 283 INICIAL, 118 CONCILIAÇÃO EM EXECUÇÃO, 22 JULGAMENTO); 324 por vídeo; 167 UNA-RS marcam rito sumaríssimo [CONFIRMAR 17] | 121 audiências só com data, sem tipo |
| DECISAO SENTENCA / RESULTADO RECURSO | 2.118 / 1.244 | 2.148 sentenças e 1.520 acórdãos em `decisoes`; 1 sentença completada por ULTIMA DECISAO | 0 |
| FONTE (PRÉ) | 77 | 77: 59 PROJETO/PUXADA (inclui "JUXADA" e "17/06") · 9 DISPARO/LAILLA · 3 INDICAÇÃO (três grafias) · 1 CLIENTE ATIVO · 1 BENEFÍCIO E ERROS · 1 OUTRO | 0; 720 fichas sem fonte |
| STATUS ENTREVISTA (PRÉ) | 592 | 448 ENTREVISTA-OK → fato · 113 DESISTÊNCIA + 17 SEM RESPOSTA + 2 STAND-BY + 3 PENDENTE → etapa · 7 AGENDADA → evento · 2 PRIMEIRO CONTATO → contatos | 0 |
| PENDENCIAS (PRÉ, multi-select) | 2.239 marcas | 2.235 pendências de documento em 8 tipos (472 TRCT, 465 PROVAS, 441 HOLERITES — 36 delas "HOLERITE" —, 388 DOCS MÉDICOS, 244 FGTS, 113 CTPS, 98 CNH/RG, 14 PIS) | 4 ("OK", "DOCUMENTAÇÃO OK": não são documento) |
| ETAPA + STATUS PETIÇÃO + STATUS ENTREVISTA + STATUS DOCUMENTAÇÃO → uma etapa | 797 | 489 DISTRIBUIDO · 169 CANCELADO · 54 PET. AGUARDANDO APROVAÇÃO · 35 PET. PENDENTE · 19 DOCUMENTAÇÃO · 14 SEM RESPOSTA · 6 PET. EM CRIAÇÃO · 5 PET. APROVADA · 4 ENTREVISTA · 2 STAND BY | 3 divergências ETAPA×PETIÇÃO em conferência |
| REVOGAÇÃO (PROCESSUAL vence) | 1.029 / 696 | 774 SIM · 39 NÃO · 42+46 NÃO SE APLICA; 5 recados viraram tarefa | 0 |
| AND. NECESSÁRIO | 138 / 127 | 73 tarefas de andamento (inclui 3 recados longos, título cortado e texto inteiro guardado); "Encerrado" (63) e "ACORDO" (1) não viram tarefa | 0 |
| DEMISSAO (PRÉ, 6 grafias de data) | 616 | 616 | 0 |
| NASCIMENTO (CÓPIA, texto) | 2.509 | 2.508 | 1 (ano 2977) |
| SUCUMBENCIA % | 558 / 259 | 555 | 3 ("2500%", "38.75%") |
| VALOR (faltantes) | 600 | 599 | 1 (vinte dígitos: número de processo no campo de moeda) |
| CPF (CÓPIA, dos autos) | 3.610 | 3.608 gravados em `cpf_parte`; cliente por CPF válido em 2.129 dos 2.270 criados dos autos | — |

## As divergências CÓPIA × PROCESSUAL, por campo

Só nos 2.516 processos em que as duas fontes casaram por CNJ. Cada uma é uma linha de
`conferencias` com os dois valores, de onde veio cada um e o que a migração gravou.

| campo | divergências | quem venceu na gravação |
|---|---:|---|
| FASE PROCESSUAL | 1.405 | CÓPIA (atualizada pela leitura dos autos em 31/08) |
| VARA | 569 | CÓPIA; a grafia da PROCESSUAL foi para `processo_alias` (569) |
| STATUS DO PROCESSO | 341 | CÓPIA |
| VALOR | 271 | CÓPIA |
| ENCERRAMENTO | 197 | CÓPIA |
| NOME | 84 | CÓPIA; a outra grafia em `processo_alias` (84) |
| DECISAO SENTENCA | 30 | CÓPIA |
| STATUS ACORDO | 20 | CÓPIA |
| **total** | **2.917** | |

Mais 3 divergências internas da PRÉ (ETAPA diz concluído, STATUS PETIÇÃO não). A regra de quem
vence está na coluna **vence** de `docs/de-para.md`; nos 11 campos em que a PROCESSUAL vence
(DATA REVOG, Nº CumPrSe, VALOR HOM, SUCUMB RECEBIDO, STATUS EXECUÇÃO, REVOGAÇÃO, NOTIFICAÇÃO,
PROVIDENCIAS, CLIENTE AVISADO?, AND. NECESSÁRIO, SITU. EMPRESA) não se abre conferência, por
decisão de projeto: são os campos que a equipe edita hoje só lá.

## As 3.300 conferências, por tipo

| tipo | linhas | o que é |
|---|---:|---|
| DIVERGENCIA_FONTE | 2.920 | a tabela acima |
| VALOR_SEM_TRADUCAO | 241 | 101 rescisão · 69 STATUS EXECUÇÃO (45 poluídos + 24 na coluna errada e incoerentes com a fase) · 66 "EXECUÇÃO" sem qualificação · 2 sucumbência fora do art. 791-A · 2 testemunhas sem nome · 1 valor implausível |
| SEM_NUMERO | 106 | registros da PROCESSUAL sem CNJ: entraram como processo próprio |
| CNJ_DUPLICADO | 25 | 19 na CÓPIA, 6 na PROCESSUAL: cada um virou um processo |
| FORA_DO_ESCOPO | 3 | os `INAPLICÁVEL` |
| LINK_QUEBRADO | 3 | PÓS PROCESSUAL sem link e sem CNJ que case |
| DATA_ILEGIVEL | 1 | nascimento com ano 2977 |
| CLIENTE_AMBIGUO | 1 | duas fichas com o mesmo nome e sem CPF que decida: nasceu ficha nova |

## O que fica só em `airtable_bruto` — contagens reais

`airtable_bruto` guarda o registro inteiro em toda linha migrada (nos processos, os dois lados).
O que **não** tem coluna própria, e quantos registros preenchem cada um:

| o que | preenchidos | por quê |
|---|---:|---|
| `_BACKUP_VALOR / _COMPLEXIDADE / _FEITO_EM_SCRIPT` (PROCESSUAL) | 233 / 181 / 233 | backup de um script de julho/2026; rascunho não ganha coluna |
| `Created By` (PROCESSUAL 2.652 · CÓPIA 3.722 · TESTEMUNHAS 424) | 6.798 | quem criou o registro no Airtable; na PROCESSUAL é `lastModifiedTime` com nome errado |
| `ENVIAR MENSAGEM` (botão, 4 tabelas) · `LINK DA TESTEMUNHA` | 7.595 · 424 | URL montada dos outros campos: recalcula-se |
| `SITU. EMPRESA` (lookup) · `EMPRESA PROCESSADA` | 4.469 · 784 | JOIN com `empresas` |
| `MOTIVO` (PROCESSUAL 1 · CÓPIA 4) | 5 | sem função clara |
| `PROCESSUAL copy` (PÓS) | 436 | link legado para a CÓPIA; a ligação útil é o CNJ |
| `STATUS RECEBIMENTO` (PÓS) | 80 | derivado de `recebimentos` |
| `ENCONTROU NOSSO CLIENTE NA ETAPA PROCESSUAL` (TESTEMUNHAS) | 44 | vai como observação do `testemunha_vinculo` com processo |
| `PRESCREVE` · `prescrição próxima` · `URGENCIA` (fórmulas da PRÉ) | 616 · 49 · 226 | derivados: conta de data na view |
| `TESE PRINCIPAL`, `CADASTRADO POR`, `ÚLTIMA ALTERAÇÃO POR/EM`, `origem_comercial_tabela_id`, `EVENTOS`, `DATA DE ASSINATURA` (PÓS), `STATUS REPASSE`, `PROCESSUAL 2`, `✅ VALIDAR E SUBIR`, `DOSSIE` | 0 | vazios em 100% na base real |
| contadores e links inversos (`QTD *`, `VINCULADOS *`, `rec_id`, `TEMP_RECORD_ID`, `PROCESSUAL copy` em FUNCIONARIOS/EMPRESAS, `PRE PROCESSUAL`/`PROCESSUAL`/`TESTEMUNHAS` em EMPRESAS e FUNCIONARIOS) | — | o outro lado de uma FK, e o COUNT sobre ela |

## O que a carga real revelou que a amostra não mostrou

Sete defeitos. Nenhum apareceria numa conferência de contagem simples, e três deles só
apareceram porque a prova recalcula da origem.

1. **Um número de processo no campo de valor.** Em Conferência de Faltantes, um `VALOR` de vinte
   dígitos: em centavos estoura o `bigint` e derrubou a carga inteira no passo 9 de 10. Agora
   `normalizar.dinheiro()` recusa o que passa de R$ 1 bilhão — fica NULL, o original no bruto, e
   abre conferência — e `conferir.py` exige que cada implausível tenha a sua.
2. **270 turmas "cortadas".** A CÓPIA guarda TURMA como texto de 24 caracteres: "VICE-PRESIDÊNCIA
   JUDICIA". Só um órgão começa assim; entra por prefixo, e a distribuição de turma passou a ser
   provada.
3. **Duas testemunhas sem nome que a carga pulava** — e com elas um vínculo com processo e um
   status. Perda zero: entram como "(sem nome na origem)" com conferência, e a prova passou a
   contar 424, não 422.
4. **198 processos com STATUS EXECUÇÃO na coluna errada** (ARQUIVADO, EXTINTA, EXECUÇÃO
   PROVISÓRIA, SOBRESTADO, AUDIÊNCIA CONCILIAÇÃO) que a primeira versão guardava no `_original` e
   ignorava, calada. Agora: coerente com a fase gravada, aplica-se (EXTINTA em processo encerrado
   vira `resultado_final`) ou nada há a fazer; incoerente (24), conferência. A prova recalcula a
   regra.
5. **Um IMPROCEDENTE a mais no banco** que na origem: ULTIMA DECISAO completava a sentença num
   UPDATE que a prova não recalculava. A regra mudou para um método só (`resultado_sentenca`),
   usado pelos dois — o mesmo remédio do `fase_final`.
6. **98 rescisões indiretas em branco** por um trecho de de/para com acento — os trechos são
   comparados com o texto sem acento, e "RESCISÃO INDIRET" nunca casava. A prova não pegou porque
   não conferia a distribuição da rescisão; agora confere rescisão, canal, documento pendente e
   turma. É o defeito mais instrutivo da rodada: um de/para "melhorado" à mão piorou a carga, e
   só a contagem por opção denuncia isso.
7. **O plano B estava quebrado.** O SQL gerado dobrava a barra invertida; com
   `standard_conforming_strings` ligado (padrão do Postgres e do Supabase) isso corrompe o JSON do
   `airtable_bruto` que traz `\"`, e o `psql` parava no INSERT 3.171. A carga direta por psycopg
   nunca passa por aí — por isso nunca apareceu. Junto: o casamento PÓS/faltantes → processo por
   CNJ saía de um SELECT, que em modo arquivo devolvia vazio; o mapa agora vive em memória e o
   SQL produz o mesmo banco da carga direta, provado tabela a tabela.

Mais três que não são defeitos, mas vale saber: o `docs/.airtable_schema_raw.json` cobre 8 das
10 tabelas (falta CÓPIA e AUDITORIA), então o conversor decide o tipo pela forma do valor e usa o
schema só como conferência; `DOSSIE` das fragilidades está vazio em 100% (os 8 anexos são todos de
testemunhas); e 720 das 797 fichas da PRÉ não têm FONTE — a taxa de conversão por canal nasce
sem histórico, como a resposta 5 do Lucas já previa.

## O que depende do Lucas

As da rodada anterior continuam (PENDENCIAS pedido×falta — respondida: é falta, e assim entrou;
REVOGAÇÃO dois sentidos; AÇÃO×DISTRIBUIÇÃO; UNA-RS; TRATAMENTO; ARQUIVO TST), mais duas que a
carga real trouxe:

7. **`TURMA` = "11"** (1 processo) — é a 11ª Turma? Hoje fica NULL com conferência.
8. **`RESCISAO` = "DEMISSÃO"** sozinho (9 fichas) — sem justa causa ou a pedido? A urgência de
   rescisão indireta e a prescrição dependem da modalidade.

## Para rodar no Supabase

```bash
export GGV_SUPABASE_TRAB=...                 # a URI do Postgres do PrevGGVLucas
./.venv/bin/python migrar.py --recriar       # apaga o public e refaz: esquema + governança + carga
./.venv/bin/python conferir.py               # 182 linhas, TUDO CONFERE
```

Antes: a cópia externa (pg_dump) do `prev_2026_09`, como manda o `CLAUDE.md`. `--recriar` apaga o
`public` — e só ele. Sem URI, o plano B é `dados/carga_real.sql` em blocos pelo `apply_migration`
(36,7 MB; o arquivo começa com `SET standard_conforming_strings = on`, DROP/CREATE SCHEMA e os dois
`.sql`, depois 48.224 INSERTs em ordem de dependência, e termina acertando as sequências).
