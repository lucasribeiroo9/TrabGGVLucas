# Respostas do Lucas — 03/09/2026

O que o escritório respondeu das 34 perguntas. O que está aqui **vale mais que a proposta do
arquiteto**: onde divergir, esta folha manda.

## 5 · Existe lead antes da assinatura? **SIM**

A captação trabalha com **disparo pelo sistema Lailla**, e o cliente fecha pelo **ZapSign**. A
assinatura é hoje a **métrica mais usada** do escritório. Logo:

- A etapa `LEAD` **fica** no fluxo do cliente, como proposta. Ela é a fase que o Airtable não
  enxerga — lá a pessoa só aparece depois de assinar.
- `LEAD → DOCUMENTACAO` continua travada pelo **contrato assinado**, e o que destrava é o
  documento do **ZapSign** (como no Prev, onde `zapsign_docs` prova a assinatura).
- A ficha guarda **origem do lead** (canal + campanha do Lailla) desde o primeiro contato: é o
  numerador e o denominador da conversão que o escritório mede.
- A migração nasce com o funil **truncado**: os 797 registros do Airtable entram já assinados.
  Lead sem assinatura só passa a existir a partir da entrada do portal. A tela precisa dizer isso,
  senão a taxa de conversão do primeiro mês mente.

## 7 · A lista de PENDENCIAS: **são coisas diferentes, não só documento**

O escritório tem pendência de **documento**, de **marcar entrevista**, de **fazer petição**, de
**marcar reunião pré-audiência** e de **fazer réplica**. Logo:

- `pendencias` é **uma tabela só, com tipo**, não um campo de documentos. Cada linha: tipo, o que
  falta, quem deve resolver, prazo, quando foi resolvida (ou dispensada, com motivo).
- O gate que hoje se chama `documentos_obrigatorios` passa a ser **"nenhuma pendência aberta do
  tipo DOCUMENTO"**. Os outros tipos não travam etapa: viram **tarefa com dono**, que é o que já
  são na prática.
- Pendência de **reunião pré-audiência** e de **réplica** pertencem ao processo, não ao cliente —
  a mesma tabela serve às duas pontas (`pendencias.cliente_id` ou `pendencias.processo_id`).
- Isso explica as 172 fichas "COMPLETA" com pendência aberta: a pendência não era de documento.

## 8 · Quem aprova a petição inicial: **a equipe de petição inicial**

"Existe um setor próprio para cada etapa." Então o setor não é um rótulo genérico: é **quem
responde pela etapa**. `PETICAO_AGUARDANDO_APROVACAO` tem como grupo **Petição Inicial**, e a
aprovação é papel dessa equipe — não da Gestão, como o arquiteto supôs.

Consequência: `equipe.py` nasce com os setores **por etapa**, e não com os cinco do Prev.
[CONFIRMAR] a lista fechada de setores e quem chefia cada um (pergunta 30).

## 26 · Repasse ao cliente: **é do financeiro**

O jurídico **não** registra repasse. O portal guarda a **referência** (houve, quando, valor) para
poder dizer que o processo terminou de verdade, e o dinheiro é lançado no financeiro, que já está
projetado para isso.

Consequência na governança: o gate de `RECEBENDO → ENCERRADO` **não exige** repasse registrado
aqui. Exige que o recebimento esteja fechado e o repasse **marcado como entregue ao financeiro**.

## Autorização para seguir

> "pode fazer, para entendermos o resultado, caso seja necessário mudamos mais pra frente a
> governança, mas podemos iniciar"

A Fase 3 (esquema e migração) começa com a governança como está. Mudança de mapa depois é barata:
`fluxo_etapas` e `fluxo_transicoes` são **linhas de tabela**, não código — mexer nelas não obriga a
migrar de novo.

## 7 (complemento) · Pendência de documento: **pedido sem recebimento confirmado continua pendente**

> "O que foi pedido, já confirmou que foi recebido? Porque se não responderam, ainda é pendência.
> Embora possa ser uma etapa diferente neste caso, o documento em si continua pendente."

Logo a leitura conservadora da migração está certa: `PENDENCIAS` lista o que **falta**. A pendência
de documento tem um sub-estado — **ainda não pedida** ou **pedida, aguardando** — que é atributo
(`solicitada_em`), não etapa; a pendência só fecha com `recebida_em` ou dispensa justificada. As 551
fichas entram como pendência aberta, e a tela mostra há quanto tempo cada uma espera resposta.
