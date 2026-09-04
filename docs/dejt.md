# A leitura do diário — o que está pronto e o que falta

> 04/09/2026. Item 4 do `docs/onde-paramos.md`: *"a leitura do DEJT — o buraco
> mais fundo. Hoje prazo corre sem ninguém saber."* Este arquivo é o estado.

## Por que não é o `aasp.py` do Prev com outro nome

No previdenciário a publicação é praticamente **log**: entra no histórico do
processo e alguém lê. O prazo do JEF corre em **dias corridos** e a Lei
11.419/2006 resolve sozinha. Aqui nada disso vale:

| | Prev | Trabalhista |
|---|---|---|
| contagem | dias corridos | **dias úteis** (CLT art. 775) |
| recesso 20/12–20/01 | não existe | **suspende** (CLT art. 775-A) |
| intimação em audiência | — | conta da audiência (**Súmula 197 TST**) |
| tipos de prazo | do JEF | os **18 da CLT**, em `prazo_tipos` |
| o que a publicação é | um registro | **o que faz o prazo nascer** |

A última linha é a que muda o desenho. Como aqui a publicação é a origem do
prazo, e prazo perdido é o pior dia do escritório, a tabela `publicacoes` guarda
as **duas datas que a lei separa** e que todo mundo confunde:

- `disponibilizado_em` — o dia em que o ato saiu no DEJT;
- `publicado_em` — o **primeiro dia útil seguinte** (Lei 11.419/2006, art. 4º,
  §§ 3º e 4º), que é de onde o prazo começa a correr.

Contá-las como uma só erra o vencimento em dois dias. Para o lado errado.

## O que está pronto e provado

`dejt.py` lê um lote, casa com o processo e **propõe**. A tabela `publicacoes`
existe no `esquema.sql` e já está aplicada no Supabase (migration
`trab_publicacoes_do_dejt`), com RLS e a FK do tipo sugerido apontando para
`prazo_tipos` — para a proposta nunca oferecer um tipo que o `prazos` recusaria.

A prova (`./.venv/bin/python dejt.py --amostra`), com publicações sintéticas:

| disponibilizado | publicado | tipo proposto | vence | o que prova |
|---|---|---|---|---|
| 03/09 qui | 04/09 sex | `RECURSO_ORDINARIO` 8d | 17/09 | pulou o feriado de 07/09 |
| 03/09 | 04/09 | `EMBARGOS_DECLARACAO` 5d | 14/09 | ED antes de "sentença" na ordem das regras |
| 03/09 | 04/09 | `IMPUGNACAO_CALCULOS` 8d | 17/09 | art. 879 §2º, sob pena de preclusão |
| 03/09 | 04/09 | `MANIFESTACAO_LAUDO` 15d | 28/09 | prazo sem `dias` legal usa `dias_padrao` |
| 03/09 | 04/09 | — | — | "arquivem-se os autos" **não abre prazo** |
| 03/09 | 04/09 | `OUTRO` 5d | 14/09 | ato não reconhecido pede confirmação |
| **04/09 sex** | **08/09 ter** | `RECURSO_ORDINARIO` | 18/09 | sexta → segunda é feriado → terça |
| **22/12** | **21/01/2027** | `RECURSO_ORDINARIO` | 02/02/2027 | o recesso inteiro, art. 775-A |

Rodar duas vezes não duplica: a chave `(fonte, fonte_id)` recusa, e sem ela a
mesma intimação entraria de novo a cada retry ou janela de datas sobreposta.

## A regra que não se negocia

**A máquina propõe; o prazo nasce quando gente lê.** `prazo_tipo_sugerido` e
`vencimento_sugerido` são leitura de máquina; `prazo_id` só é preenchido quando
alguém do Jurídico decide. É a regra 5 da casa e é a mesma decisão que o Lucas
tomou no Prev em 23/08/2026 para as decisões do diário — para o hábito de ler
não se perder.

Por isso o ato que **não** abre prazo é reconhecido e marcado: encher a fila de
publicação que não pede nada é o jeito mais rápido de fazer o Jurídico parar de
ler a fila.

E por isso o que o mapa não reconhece **não é chutado**: cai em `OUTRO`, 5 dias
(CPC art. 218 §3º), com `[CONFIRMAR o tipo]` escrito na sugestão. Chutar tipo de
prazo é errar vencimento.

## A fonte: DJEN — decisão do Lucas, 04/09/2026

Entre DJEN, AASP e PJe, ficou o **DJEN**, e é a mais limpa das três: não pede
credencial (é diário oficial), é nacional — não depende de a assinatura da AASP
cobrir o trabalhista — e devolve o número do processo em **campo próprio**, não
preso no meio do texto como no e-mail da AASP, onde o Prev precisa caçá-lo por
expressão regular.

`djen.py` é o cliente, e `dejt.py --djen` já o chama:

```bash
./.venv/bin/python djen.py --oab 123456 --uf SP --dias 3 --cru lote.json
./.venv/bin/python dejt.py --arquivo lote.json          # confere e grava
./.venv/bin/python dejt.py --djen --oab 123456 --dias 3 # ou direto
```

**Na primeira vez, use `--cru`**: ele baixa e salva sem gravar nada no banco,
para a forma ser conferida antes de deixar entrar.

### A trava: forma desconhecida é recusa, não palpite

Mesma regra do `do_conector.py`. Cada campo tem uma lista de nomes candidatos
(a API mistura camelCase e snake_case, e já trocou de um para o outro), e se
nenhum casar num campo obrigatório o lote inteiro é **recusado**, com as chaves
que de fato vieram impressas na tela. O modo de falha que isso evita é o pior
possível: publicação gravada sem data é prazo que não nasce, e ninguém percebe.

Provado sem tocar na rede, 7 de 7: aceita `items` em camelCase, `content` em
snake_case e lista nua; **recusa** texto com nome desconhecido (e a mensagem
diz qual nome veio), **recusa** resposta sem lista, pula item incompleto sem
derrubar o lote, e `buscar()` sem recorte para antes de qualquer chamada.

E o caminho inteiro, contra o banco: uma comunicação com CNJ do cadastro casou
por `CNJ` e virou proposta de recurso ordinário vencendo em 17/09; uma com CNJ
inexistente entrou marcada como órfã, com a proposta dela do mesmo jeito.

### O que ainda falta para ligar

**A OAB do escritório — número e UF.** É o recorte: sem ela o DJEN devolve o
diário do país inteiro, e o que é nosso é o que sai no nome dos nossos
advogados. `--tribunal TRT2` funciona como recorte grosso para um primeiro
teste, mas não serve para o dia a dia.

O host `comunicaapi.pje.jus.br` foi testado da sessão de 04/09/2026 e **a
política de rede daquela sessão bloqueou** (403 no CONNECT do proxy): não dá
para provar a API real de dentro do Claude Code na web. De uma máquina comum é
uma chamada HTTPS simples, e é por isso que `--cru` existe — a primeira execução
de verdade mostra a forma antes de qualquer coisa entrar no banco.

**3. Quem recebe a tarefa.** A publicação casada com processo deve virar tarefa
para quem? O `advogado_id` do processo, o setor Jurídico, ou uma fila só?
[CONFIRMAR com o Lucas.]

**4. Os feriados do TRT.** `prazo_legal.py` usa os **nacionais**. Faltam os do
TRT (portarias anuais, que variam por região e ano) e os municipais da sede da
vara. Enquanto não vierem, a conta erra **para o lado curto** — o prazo aparece
vencendo antes, não depois. É o lado seguro do erro, e está assim de propósito.

## O que vem depois, quando a fonte existir

- a tela `/publicacoes`, com o pente fino (período, ato, vara, lida/não lida) e
  o botão que transforma a proposta em prazo de verdade;
- a tela `/decisoes`, que é a publicação de mérito com o trabalho projetado —
  no Prev ela existe desde 23/08/2026 e é onde o Jurídico dá o OK;
- o agendamento (launchd 3×/dia, como o `aasp.py` do Prev) com rastro de cada
  execução em `automacao_log`, porque o modo de falha do diário é o silêncio:
  rodada que falhou tem de ser distinguível de dia sem publicação.
