# A prova de que o portal sobe e obedece

> Rodada em 03/09/2026, na porta **8771**, contra o banco de desenvolvimento
> `trab_dev` (Postgres local, esquema aplicado por `migrar.py --recriar` sobre a
> amostra **sintética** de `dados_exemplo.py`). O banco de prova compartilhado,
> `trab_prova`, não foi tocado — outro agente estava carregando dados nele.
>
> Nenhum nome, CPF, telefone ou número CNJ real aparece aqui: os dados da
> amostra são inventados ("Reclamante 01", "Colaborador 3") e vivem em `dados/`,
> fora do git.
>
> **A senha das contas de prova não está escrita neste arquivo**, como não está
> em lugar nenhum do repositório. Elas foram criadas por `python3 auth.py equipe`,
> que mostra a senha uma vez e só.

```bash
GGV_DSN='postgresql://postgres:***@localhost:5432/trab_dev' GGV_SEGREDO=… ./rodar.sh
# banco: postgresql://***@localhost:5432/trab_dev
# ✓ no ar em http://127.0.0.1:8771  (pid 3532)
```

## 1. Entrada

```
GET  /entrar                     200
POST /entrar   (gestor)          302        → sessão criada, token de CSRF girado
POST /entrar   (advogado)        302
POST /entrar   (senha errada)    403        ← recusado pela trava de CSRF, porque
                                              o pedido veio sem o token daquela
                                              sessão. Com o token, a senha errada
                                              devolve a tela de login com o recado.
```

A conta nasce com senha provisória, e o sistema **não deixa andar** para outra
tela antes da troca: qualquer rota redireciona para `/senha` enquanto
`trocar_senha` for verdadeiro.

## 2. As telas, com sessão de gestor

```
GET  /                              200    13.620 bytes
GET  /clientes                      200    16.927
GET  /processos                     200    15.093
GET  /audiencias                    200     8.237
GET  /prazos                        200    14.985
GET  /empresas                      200     7.985
GET  /testemunhas                   200     9.446
GET  /conferencias                  200    31.382
GET  /tarefas                       200     8.228
GET  /equipe                        200     9.767
GET  /fluxos                        200    67.941
GET  /painel                        200    15.630
GET  /saude                         200        26     {"ok": true, "processos": 14}
GET  /api/agora                     200       214

as fichas
GET  /clientes/1                    200    26.564
GET  /processos/1                   200    23.975
GET  /audiencias/1                  200    18.341
GET  /empresas/1                    200     9.145
GET  /testemunhas/1                 200     8.278

os filtros — e cada tela conta DENTRO do recorte
GET  /clientes?status=DOCUMENTACAO  200     9.164
GET  /clientes?vivos=1              200    10.646
GET  /processos?fase=CONHECIMENTO   200    11.091
GET  /processos?falta=empresa       200     9.738
GET  /audiencias?janela=todas       200     8.390
GET  /prazos?situacao=todas         200    17.422
GET  /conferencias?tipo=CNJ_DUPLICADO 200   8.133
GET  /tarefas?quem=sem_dono         200    12.493
```

## 3. A permissão é do servidor, não do menu

O mesmo endereço, digitado por um **advogado** (o menu dele nem mostra estas
telas — mas o menu é conveniência, não trava):

```
GET  /processos    200
GET  /clientes     200
GET  /equipe       403
GET  /painel       403
GET  /fluxos       403
```

## 4. CSRF

```
POST /mover/clientes/2  sem token   403 · "Este pedido não veio de dentro do sistema."
```

A recusa **explica** em vez de dizer 403 e mais nada, porque o caso comum não é
ataque: é a aba que ficou aberta a noite inteira e a sessão que expirou junto.

## 5. A governança: o que a tela recusa, e por quê

Uma ficha nova, nascida em `LEAD` (a única porta de entrada que o gatilho
`gov_nasce_na_inicial` aceita):

```
fora do mapa: LEAD → DISTRIBUIDO
   → não existe caminho da etapa atual para DISTRIBUIDO

gate contrato_assinado (a pessoa não assinou)
   → falta o contrato de honorários assinado, com data. Sem ele o escritório
     não representa ninguém

gate motivo (cancelar sem dizer por quê)
   → escreva o motivo da mudança

o mesmo cancelamento, com o motivo digitado na janela
   → etapa alterada e registrada no histórico
```

Uma ficha com a minuta esperando aprovação — o gargalo do funil:

```
gate minuta_anexada
   → anexe a minuta da inicial na ficha — não se aprova o que não está escrito
```

Uma ficha aprovada, indo distribuir. Dois gates ao mesmo tempo, e a mensagem
diz os dois:

```
   → informe o número CNJ com 20 dígitos — é ele que faz o processo nascer;
     e a prescrição bienal já se consumou (CF art. 7º XXIX; CLT art. 11).
     Registre a dispensa justificada na ficha antes de distribuir

com o CNJ preenchido, sobra o que ainda falta:
   → a prescrição bienal já se consumou (…). Registre a dispensa justificada
     na ficha antes de distribuir
```

A audiência, com o checklist e a etapa:

```
marcar "testemunhas confirmadas"                → preparação atualizada
                                                  (e a audiência foi de DESIGNADA
                                                   para EM_PREPARACAO pelo mesmo
                                                   mapa, não por escrita direta)
registrar realização sem dizer o que houve
   → registre o que aconteceu: acordo, defesa juntada, instrução encerrada,
     sentença designada
com o resultado escolhido na janela              → etapa alterada e registrada
```

O processo:

```
gate sentenca_registrada (ir para recursal)
   → registre a decisão (resultado objetivo, data e nota) antes de mudar de fase
     — é isso que alimenta o mapa de onde estamos perdendo
gate resultado (encerrar sem dizer o quê)
   → informe o resultado final do processo antes de encerrar
com o resultado escolhido na janela              → etapa alterada e registrada
```

O prazo — e aqui o gatilho do banco tem exigência própria:

```
PERDIDO sem motivo   → escreva o motivo da mudança
PERDIDO com motivo   → etapa alterada e registrada
                       (prazos.motivo = "publicacao nao foi lida a tempo")
CUMPRIDO sem nada    → informe a data do protocolo e o número do protocolo no PJe
CUMPRIDO com os dois → etapa alterada; prazos.protocolo = PJE-123456,
                       cumprido_em = 2026-09-03
```

**Nenhuma dessas recusas virou erro 500.** Toda escrita roda em SAVEPOINT e os
`except` usam `banco.Integridade` / `banco.Operacional`; a recusa do gatilho vira
recado na tela.

## 6. O que ficou gravado

```
 entidade   | id |        de        |       para       | quem | motivo
------------+----+------------------+------------------+------+-----------------------------
 clientes   |  1 | DOCUMENTACAO     | STAND_BY         |    1 | prova do portal
 audiencias |  1 | DESIGNADA        | EM_PREPARACAO    |    1 | primeiro item da preparação…
 prazos     |  1 | ABERTO           | PERDIDO          |    1 | publicacao nao foi lida a tempo
 prazos     |  2 | ABERTO           | CUMPRIDO         |    1 |
 clientes   |  2 | ENTREVISTA       | PETICAO_PENDENTE |    1 |
 clientes   |  2 | PETICAO_PENDENTE | CANCELADO        |    1 | prova do portal
 clientes   | 23 | LEAD             | CANCELADO        |    1 | prova do portal: …
 audiencias |  1 | EM_PREPARACAO    | REALIZADA        |    1 |
 processos  |  1 | CONHECIMENTO     | ENCERRADO        |    1 |
```

Cada linha nasceu do gatilho `gov_historico`, e o portal completou **quem** e
**por quê**. É o histórico que o Airtable nunca teve.

E os campos da janela foram parar na coluna certa:

```
audiencias 1 → situacao=REALIZADA, resultado=DEFESA_JUNTADA, testemunhas_confirmadas_em=2026-09-03
processos  1 → fase=ENCERRADO, resultado_final=ARQUIVADO_AUSENCIA
clientes  23 → status=CANCELADO, motivo="…a pessoa não retornou"
```

## 7. Os gatilhos, provados por fora do portal

O portal não é a única porta, e a regra não pode depender dele. No `psql`, como
usuário do banco:

```sql
update clientes set status='DISTRIBUIDO' where id=2;
ERROR:  transição de status fora do fluxo CLIENTE: ENTREVISTA → DISTRIBUIDO

insert into clientes (status, nome, nome_norm) values ('ENTREVISTA','Outra','OUTRA');
ERROR:  clientes não pode nascer em ENTREVISTA: só na etapa inicial do fluxo CLIENTE

insert into processos (cliente_id, fase, numero_cnj) values (5,'CONHECIMENTO','9999');
ERROR:  prescrição bienal consumada (CF art. 7º XXIX; CLT art. 11): registre
        dispensa_prescricao_motivo na ficha do cliente antes de abrir o processo
```

## 8. Os módulos, fora da tela

```
$ python3 automacao.py
PRESCRICAO_BIENAL          prescricao:1
PRESCRICAO_BIENAL          prescricao:2
PRESCRICAO_BIENAL          prescricao:3
PRESCRICAO_BIENAL          prescricao:5

$ python3 automacao.py          # de novo: a chave natural (automacao, chave) segura
nada a fazer

$ python3 prazo_legal.py
hoje: 2026-09-03 · dia útil: True
disponibilizado hoje, prazo de 8 dias úteis (RO, CLT art. 895 I):
  publicação 2026-09-04 · começa 2026-09-08 · vence 2026-09-17

$ python3 -c "import execucao, banco; …execucao.vigiar(db)"
{'codigo': 'DEJT_LEITURA', 'rodou_hoje': 0, 'nivel': 'vermelho',
 'recado': 'o DEJT não foi lido hoje — 2 leitura(s) já deveriam ter acontecido.
            Publicação não lida é prazo correndo sem ninguém saber.'}
```

O vigia acusando vermelho está **certo**: ninguém lê o DEJT ainda. É exatamente
o alarme que deve tocar — e a falta dele é que seria o problema.

`DISTRIBUIR_FILA` não entregou nenhuma tarefa, e também está certo: ela procura
gente no setor da tarefa, e `pessoas.setor` está vazio porque `equipe.AJUSTES`
está vazio esperando a resposta 30 do Lucas. As tarefas ficaram na fila "sem
dono", que é o comportamento correto para um organograma que ainda não existe.

## 9. Parar

```bash
./parar.sh
# parado (pid 3532)
```

`parar.sh` mata **só** quem estiver na porta 8771. Nunca `pkill -f "uvicorn
app:app"`: esse padrão casaria também com o sistema previdenciário (8770) e com
o portal financeiro (8700), e derrubar o sistema em que o escritório está
trabalhando para parar o nosso é o pior desfecho possível.

---

## Nota sobre a prova por `curl`

`curl -d "campo=não"` manda os bytes **crus**, sem percent-encoding — o
navegador não faz isso. Numa primeira passagem, isso fez o motivo chegar ao
banco como `nÃ£o` e pareceu defeito de codificação do portal. Não era: com
`--data-urlencode`, que é o que o formulário do navegador faz, o texto chega
inteiro:

```sql
select texto from anotacoes where origem='MANUAL';
 acentuação e cedilha: ação, prescrição, não
```

Fica escrito para ninguém perseguir esse fantasma de novo.

---

# Os consertos da auditoria de 03/09/2026 — a prova

> Segunda rodada do DEV do portal, 03/09/2026, depois de `docs/auditoria-fase-3-4.md`.
> Desta vez contra a carga real: `trab_prova` (3.855 processos), na porta 8771,
> subido com `GGV_DSN=… GGV_SEGREDO=… ./rodar.sh` e derrubado com `./parar.sh`.
>
> `trab_prova` não foi recriado. As **recusas não escrevem nada** — é o que
> uma recusa é —, então elas rodaram direto ali. O caminho de SUCESSO do
> repasse (que encerra um processo) rodou numa cópia descartável,
> `createdb -T trab_prova trab_auto`, apagada no fim; a mesma escolha que o
> Auditor fez com `trab_aud`, e pelo mesmo motivo: prova não deve deixar
> resíduo no banco dos outros.
>
> Duas contas de prova que já existiam tiveram a senha redefinida para eu poder
> entrar (o portal não guarda senha em texto e ninguém tinha a antiga). As
> senhas ficaram fora do repositório, como sempre. Nenhum nome de cliente, CPF,
> telefone, e-mail ou CNJ aparece abaixo.

## Verificação 7 — a recusa do banco vira recado, e a conexão volta ao poço

O defeito: `except (banco.Integridade, banco.Operacional)` em cinco rotas.
Os dois nomes **já são tuplas** (`banco.py`), e Python não aceita tupla dentro
de tupla no `except` — em vez de pegar o erro, levanta
`TypeError: catching classes that do not inherit from BaseException`. O
tratamento sumia sem avisar: toda recusa do Postgres virava 500 **e** pulava o
`db.close()`, que estava fora de `finally`. Com `max_size=6`, seis recusas
esgotavam o poço e o portal parava para todo mundo (`PoolTimeout`, 20 s).

O conserto tem três partes:

1. `banco.ErroBanco = Integridade + Operacional` — uma tupla PLANA, com o
   comentário explicando por que a aninhada não funciona, para ninguém
   reescrever do jeito antigo.
2. `db.close()` em `finally` em **toda** rota de escrita. `Ponte.close()` dá
   rollback e devolve a conexão ao poço; fora do `finally`, a exceção pulava
   a linha.
3. As três rotas que não tinham tratamento nenhum ganharam o mesmo:
   `cliente_responsavel`, `processo_anotacao`, `prazo_responsavel`.

### As oito recusas seguidas, pelo portal, com sessão de gestor

```
1 transição fora do mapa (processo CONHECIMENTO → RECEBENDO)
    HTTP 302 · não existe caminho da etapa atual para RECEBENDO
2 gate: encerrar sem informar o resultado
    HTTP 302 · informe o resultado final do processo antes de encerrar
3 gate: motivo em branco (processo CONHECIMENTO → SOBRESTADO)
    HTTP 302 · escreva o motivo da mudança
4 CHECK do banco: resultado_final fora da lista
    HTTP 302 · o valor não está entre os que este campo aceita. Escolha um dos
               oferecidos na tela (processos_resultado_final_check)
5 FK do banco: dono do atendimento inexistente
    HTTP 302 · esse campo aponta para um registro que não existe … Escolha um
               da lista (clientes_responsavel_id_fkey)
6 FK do banco: anotação em processo inexistente
    HTTP 302 · … (anotacoes_processo_id_fkey)
7 FK do banco: dono de conferência inexistente
    HTTP 302 · … (conferencias_dono_id_fkey)
8 CHECK do banco: pendência com tipo fora da lista
    HTTP 302 · o valor não está entre os que este campo aceita … (pendencias_tipo_check)

500 encontrados: 0
```

As quatro primeiras eram as que o Auditor viu virar 500 (4 é literalmente o
caso dele, "encerrar com `resultado_final` fora do CHECK"); 5, 6 e 7 são as
rotas que não tinham `except` nenhum.

**A nona requisição — e as seguintes:**

```
GET /processos     200  (144.672 bytes)
GET /clientes      200  (121.565)
GET /audiencias    200   (66.188)
GET /prazos        200   (16.114)
GET /saude         200       (28)
```

E o teste de esforço, com o poço de 6:

```
25 recusas seguidas em 0,6 s · códigos: {302: 25}
logo depois: GET /processos 200
```

Antes, a sétima já esperava 20 s e falhava. `servidor.log` da rodada inteira:
**0 tracebacks, 0 respostas 500** (43 × 200, 2 × 302 no smoke; 9 × 302 nas
recusas).

### As recusas do esquema também viraram frase

A recusa da **governança** vem de um `RAISE` do PL/pgSQL e já é escrita para
gente ler — dela só se tira o cabeçalho. A recusa do **esquema** (CHECK, FK,
UNIQUE, NOT NULL) vinha em inglês, citando o nome do constraint: correta e
inútil para quem clicou. `_recado()` traduz por SQLSTATE (23503, 23514, 23505,
23502, 22P02, 22001) e mantém o nome do constraint entre parênteses, para quem
for investigar depois.

E **só a primeira linha do erro passa**, sempre: as linhas de `DETAIL` de um
erro do Postgres trazem o registro inteiro (`Failing row contains …`: nome,
CPF, telefone), e isso iria parar na barra de endereço do navegador e no
`servidor.log`. Erro não é lugar de vazar cadastro — é a mesma observação que
o Auditor fez na seção 5.

## Verificação 10 — o segredo do cookie não tem valor de reserva

`app.py` tinha `os.environ.get("GGV_SEGREDO", "trocar-em-producao")`, e
`rodar.sh` só avisava. Agora não há reserva: sem a variável o portal **recusa
subir**, e o `rodar.sh` para antes, para o recado sair no terminal em vez do
fim do `servidor.log`.

```
$ ./rodar.sh
banco: …
✗ GGV_SEGREDO não definido — o portal não sobe sem ele.

  Gere um (48 bytes, base64 url-safe):

      export GGV_SEGREDO=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
      ./rodar.sh

  Para não gerar um novo a cada vez, guarde no Keychain do Mac …
      security add-generic-password -a "$USER" -s ggv-trab-segredo -w "$GGV_SEGREDO" -U
      export GGV_SEGREDO=$(security find-generic-password -a "$USER" -s ggv-trab-segredo -w)

$ GGV_DSN=… python3 -c "import app"
✗ GGV_SEGREDO não definido — o portal não sobe sem ele.
  É o segredo que assina o cookie de sessão. Não há valor de reserva: …
```

A recusa está em `app.py` e não só no `rodar.sh` de propósito: quem sobe por
launchd, systemd ou `uvicorn` na mão não passa pelo script. Segredo com menos
de 32 caracteres também é recusado.

## Verificação 4 — todo contador conta dentro do recorte

O filtro de cada tela passou a ser montado por **dimensão** (`Recorte`, em
`app.py`), e cada chip conta o recorte **sem a sua própria dimensão** — os três
chips de qualidade são alternativas entre si, e contá-los já com `falta=numero`
aplicado daria a interseção. O link do chip também mudou: era
`/processos?falta=empresa` fixo, que largava o filtro; agora é
`qs(request, falta=…)`, que o mantém. Contador dentro do recorte com link que
sai dele seria trocar um engano por outro.

**Tela × `SELECT COUNT(*)` com o mesmo WHERE**, em `trab_prova`:

```
ok /processos?fase=RECURSAL   sem reclamada     tela=0      sql=0      (era 11, global)
ok /processos?fase=RECURSAL   sem número        tela=5      sql=5
ok /processos?fase=RECURSAL   sem valor         tela=0      sql=0
ok /processos?trt=2           sem reclamada     tela=4      sql=4
ok /processos?trt=2           sem valor         tela=0      sql=0
ok /processos                 sem reclamada     tela=11     sql=11
ok /audiencias?tipo=UNA&janela=todas  sem preparação  tela=14  sql=14  (era 2.670)
ok /audiencias?janela=todas           sem preparação  tela=21  sql=21
ok /audiencias?situacao=NAO_REALIZADA sem preparação  tela=0   sql=0

divergências: 0
```

O "sem preparação" ganhou também um **piso de data**: audiência que já
aconteceu não se prepara. A view `v_audiencias_sem_preparacao` não tem esse
piso e devolve as 2.649 audiências com data no passado que a migração gravou
como DESIGNADA — era metade do engano dos 2.670.

Os chips de **fase** e de **situação da execução** seguiram o mesmo caminho, e
ficam listados mesmo com 0 no recorte, ou não haveria como navegar para fora do
filtro atual:

```
/processos?trt=2   chip Recursal = 436 · Conhecimento = 407 · Encerrado = 2.567
sql trt=2          ENCERRADO 2.567 · RECURSAL 436 · CONHECIMENTO 407 · …
```

E os totais das filas continuam batendo depois da remontagem do filtro:

```
ok /processos?fase=RECURSAL&trt=2                  tela=436   sql=436
ok /processos?falta=numero&fase=RECURSAL           tela=5     sql=5
ok /audiencias?situacao=NAO_REALIZADA&janela=todas tela=123   sql=123
ok /audiencias?tipo=UNA&janela=todas               tela=1.384 sql=1.384
```

As 32 telas e fichas do portal responderam 200 depois da mudança — **0 fora do
200**.

## Verificação 11 — o repasse tem rota, e o gate deixou de ser porta sem chave

`fluxo.repasse_registrado` exigia a referência e **não havia como registrá-la**:
o único processo em RECEBENDO não podia ser encerrado por ninguém. Agora há
`POST /processos/{id}/repasse` e o formulário na ficha, no bloco de Dinheiro.

Ele registra a **referência**, não o repasse — resposta 26 do Lucas: quem paga
é o financeiro. Por isso a tela pede "entregue ao financeiro em" e não tem
botão "repassar". Permissão conferida no servidor por `exige(req, "processos")`
— a mesma da transição que a referência destrava, que em `fluxo_transicoes` não
exige papel. CSRF pela trava, como todo formulário do sistema.

```
fase antes: RECEBENDO

1. encerrar SEM a referência (o gate)
   → registre o repasse ao cliente (valor, data, comprovante) — ou marque que
     não havia valor a repassar, com motivo — e a entrega ao financeiro
2. repasse sem a data de entrega ao financeiro
   → informe a data em que a referência foi entregue ao financeiro — é ela que
     fecha o caso
3. repasse sem valor e sem motivo
   → informe o valor repassado — ou, se não havia o que repassar, escreva o motivo
4. valor que não é dinheiro ("uns mil reais")
   → não entendi o valor "uns mil reais" — escreva como 1.234,56
5. a referência completa
   → repasse registrado
     repasses:  123456 | 2026-09-01 | 2026-09-02
     auditoria: repasses INSERT pessoa=9
6. agora encerrar
   → etapa alterada e registrada no histórico
     processo: RECEBENDO → ENCERRADO   (historico_etapas, pelo gatilho)
7. o mesmo POST sem sessão
   → HTTP 403, "Pedido não aceito"

sem valor a repassar (a outra saída)
   → repasse registrado; sem_valor_motivo = "honorário e custas consumiram o alvará"
```

O `CHECK (valor_centavos IS NOT NULL OR sem_valor_motivo IS NOT NULL)` da
tabela cobra o mesmo que o passo 3 — a rota diz a razão antes, para quem clicou
ler a frase e não o nome do constraint.

**Fica anotado:** RECEBENDO → ENCERRADO **não** exige `resultado`, só
`repasse_registrado` (`governanca.sql`), então o processo encerrou com
`resultado_final` vazio. É coerente com os 68 ENCERRADO sem resultado que o
Auditor contou. É decisão de governança, não do portal — se o escritório quiser
o resultado também aqui, muda-se a linha de `fluxo_transicoes`.

## Verificação 9 — automação: fila viva, e rodada vazia com rastro

**`AUDIENCIA_PREPARAR` só alcança o que ainda vai acontecer.** A regra lia
`v_audiencias_sem_preparacao` inteira; a view não tem piso de data e devolve as
2.649 audiências passadas que a migração gravou como DESIGNADA. A primeira
rodada abriria 2.670 tarefas de uma vez, e as poucas da semana — a fila de
verdade — sumiriam dentro do passivo. É o princípio da `DISTRIBUIR_FILA` do
Prev: regra nova trabalha para a frente; o passivo é decisão de gestão.

```
select count(*) from v_audiencias_sem_preparacao                          → 2.670
select count(*) from v_audiencias_sem_preparacao where dias_para_audiencia >= 0 →  21
```

**Rodada vazia deixa rastro.** `_uma_vez` grava uma linha por AÇÃO; uma rodada
sem nada a fazer não gravava nada, e "rodou e não havia nada" ficava idêntico a
"não rodou" — o silêncio que a regra 6 da casa proíbe e que `execucao.py`
existe para vigiar. `rodar()` passou a correr dentro de
`execucao.registrar("AUTOMACAO_RODADA")`, que grava `OK` com a contagem,
`SEM_ACAO` na rodada vazia e `ERRO` com a mensagem se estourar. Modo `--seco`
não grava — não escreve nada, nem o rastro.

Duas rodadas seguidas, na cópia `trab_auto`:

```
$ python3 automacao.py          # primeira
AUDIENCIA_PREPARAR   audiencia:…   (21 tarefas, não 2.670)
PRESCRICAO_BIENAL    …            (11)

$ python3 automacao.py          # segunda: a chave natural segura
nada a fazer

    automacao     | resultado |              detalhe                | em
------------------+-----------+-------------------------------------+------------------
 AUTOMACAO_RODADA | OK        | 6 regra(s) ligada(s): PRESCRICAO_…   | 2026-09-03 16:29:46
 AUTOMACAO_RODADA | SEM_ACAO  | 6 regra(s) ligada(s): PRESCRICAO_…   | 2026-09-03 16:29:47
```

É a linha `SEM_ACAO` que faltava. Sem ela, uma automação que parou de rodar e
um dia sem trabalho são a mesma coisa vista do banco.

**Continua pendente** (está no "pode esperar" da auditoria): não há launchd nem
cron para `automacao.py` e `execucao.py --vigiar` — sem pasta `implantar/`, o
rastro existe e ninguém o lê de hora em hora. E `_uma_vez` ainda grava a linha
**antes** de `abrir_tarefa`: quando a tarefa já existia, o log diz OK e nada
aconteceu.

## O que estas correções NÃO tocaram

Do laudo, seguem com o outro agente (`migrar.py`, `normalizar.py`,
`conferir.py`, `governanca.sql`): `limpar()` apagando `usuarios`, DATA REVOG e
o sentido 1 da REVOGAÇÃO, audiências do passado gravadas como DESIGNADA na
carga (aqui só se deixou de contá-las), quem aprova a inicial, o histórico da
migração com a data da carga, o de/para declarado e não aplicado, e as datas
inventadas.

E seguem em aberto, do portal: rotas de cadastro (lead, decisão, acordo,
parcela, pendência de processo), validação de tipo dos campos da janela
(`cumprido_em = "ontem"`), `/saude` e `/api/agora` sem sessão, e a rotação do
`servidor.log`, que num servidor precisa de permissão restrita — a primeira
linha do erro já não leva dado pessoal, mas o `uvicorn` continua registrando
tudo o que acontece.
