# Como o escritório trabalha, em cinco fluxos

> Gerado a partir do próprio sistema por `gerar_governanca.py`. O que está escrito aqui
> é o que o software realmente faz — não é folheto.

Todo caso caminha por etapas, e o sistema **não deixa pular etapa**. Não é recomendação na
tela: é regra dentro do banco, que recusa a mudança mesmo por fora do sistema. São cinco
caminhos, e um caso percorre vários ao mesmo tempo — o processo anda enquanto uma audiência
se prepara e um prazo corre.

## Do primeiro contato à distribuição da inicial

Começa quando alguém liga ou o captador traz. Com contrato e procuração assinados, a Documentação reúne TRCT, CTPS, holerites e FGTS; a entrevista levanta os fatos e as testemunhas; o Jurídico redige a inicial, alguém aprova e ela é distribuída. O relógio aqui é a prescrição de dois anos da saída — e, na rescisão indireta, o contrato que ainda está correndo.

**As etapas, em ordem:** Lead (primeiro contato) → Documentação → Entrevista → Petição a redigir → Petição em redação → Petição aguardando aprovação → Petição aprovada, a distribuir → Stand by.

**Como termina:** Distribuído (concluído), Cancelado, Prescrito, Sem resposta.

O diagrama completo está em [`cliente.md`](cliente.md).

## O processo, da distribuição ao arquivo

Conhecimento (audiências, defesa, perícias, sentença), recursal (TRT e TST), execução provisória enquanto a reclamada recorre, execução definitiva depois do trânsito, acordo em qualquer ponto, recebimento e repasse ao cliente antes de encerrar. Cliente que troca de advogado não muda a fase do processo: vira um incidente com ciclo próprio.

**As etapas, em ordem:** Conhecimento → Recursal → Execução provisória → Execução definitiva → Acordo em cumprimento → Recebendo → Sobrestado.

**Como termina:** Encerrado, Desistência.

O diagrama completo está em [`processo.md`](processo.md).

## Cada audiência

Designada, preparada (cliente orientado, testemunhas confirmadas, ad video feito, documentos), realizada, redesignada, adiada ou não realizada. Audiência a menos de uma semana sem preparação acende alerta.

**As etapas, em ordem:** Designada → Em preparação.

**Como termina:** Realizada, Redesignada, Adiada sem data, Não realizada, Cancelada.

O diagrama completo está em [`audiencia.md`](audiencia.md).

## Cada prazo

Nasce da publicação no DEJT, da intimação ou da ata; conta em dias úteis (CLT art. 775) com os feriados do TRT e o recesso; é cumprido com protocolo registrado, suspenso, sem objeto ou — só por gestor, com motivo — perdido.

**As etapas, em ordem:** Aberto → Suspenso.

**Como termina:** Cumprido, Perdido, Sem objeto.

O diagrama completo está em [`prazo.md`](prazo.md).

## Cliente que trocou de advogado

Detectado nos autos, notificado extrajudicialmente, honorários reservados no juízo, e o desfecho: cliente recuperado, honorários recebidos ou perdido.

**As etapas, em ordem:** Detectado → Notificado → Honorários reservados nos autos.

**Como termina:** Cliente recuperado, Honorários recebidos, Perdido, Alarme falso.

O diagrama completo está em [`incidente.md`](incidente.md).

---

## O que isso garante na prática

- **Nada pula etapa.** A regra está no banco, não na tela.
- **Toda mudança fica registrada** — quem moveu, quando, de onde para onde e por quê.
- **Prazo é contado pela lei**: dias úteis (CLT art. 775), da publicação no DEJT, com os
  feriados do TRT e o recesso de 20/12 a 20/01.
- **Ação depois da prescrição bienal é barrada pelo banco**, salvo dispensa justificada.
- **A máquina propõe, a pessoa decide.** Nenhuma automação protocola peça nem move etapa.
