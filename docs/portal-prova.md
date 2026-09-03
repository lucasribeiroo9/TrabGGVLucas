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
