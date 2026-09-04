# Onde o projeto parou — 03/09/2026

Para quem abrir uma sessão nova: **este arquivo é o ponto de partida**. Leia depois o
`CLAUDE.md`, `docs/respostas-do-lucas.md` (as decisões do Lucas mandam mais que qualquer
proposta) e `docs/auditoria-fechamento.md` (o que foi provado e o que não foi).

## Pronto e provado

| | |
|---|---|
| Diagnóstico do Airtable | 10 tabelas, 350 campos, 14 automações lidas e explicadas |
| Governança | 5 máquinas, 40 etapas, 111 transições, 18 tipos de prazo, gatilhos em PL/pgSQL |
| Esquema | 35 tabelas, RLS em todas, 88 FKs, 229 CHECKs — **aplicado no Supabase, vazio** |
| Migração | 350/350 campos com destino; carga real provada num Postgres local |
| Conferência | 249 verificações, TUDO CONFERE — e a própria prova testada contra 6 sabotagens |
| Portal | 18 telas de leitura + escrita, ficha da equipe com setor e chefia editáveis |
| Auditoria | duas passagens completas; os defeitos graves corrigidos e reprovados |

Números da carga real: 3.067 clientes · 3.855 processos · 3.668 decisões · 3.035 audiências ·
2.428 recebimentos · 2.235 pendências · 10.183 linhas de histórico · 3.300 conferências abertas.

## O que falta, em ordem

1. **Carregar o Supabase** (o passo seguinte). O esquema está lá; falta o dado e a governança.
   Precisa de `GGV_SUPABASE_TRAB` no ambiente — o Lucas cadastrou em 03/09/2026, mas variável
   só chega a sessões abertas DEPOIS do cadastro. Antes de escrever: `pg_dump` do
   `prev_2026_09` (a cópia congelada do previdenciário) para um arquivo fora do Supabase.
   Depois: `migrar.py --recriar` (só ele religa a RLS) e `conferir.py` até TUDO CONFERE.
   O passo a passo está em `docs/migracao-resultado.md`.
2. **Aplicar `dados_iniciais/equipe.csv`** depois da carga (ver `dados_iniciais/LEIA-ME.md`).
3. **O organograma dos 72.** A planilha `organograma-trabalhista.xlsx` foi enviada ao Lucas
   para preencher. Sem ninguém em **Petição Inicial**, as 54 minutas paradas não têm quem
   aprove — a regra é do próprio Lucas e está funcionando, só falta o dado.
4. **Fase 4b — o que o portal ainda não faz** (detalhe em `docs/portal-telas.md`):
   - **criar ficha pelo portal** (lead, cliente, processo, audiência, prazo, testemunha).
     Hoje o portal lê e move, não cria: tudo nasceu da migração.
   - **a leitura do DEJT** — o buraco mais fundo. Hoje prazo corre sem ninguém saber.
     No Prev esse papel é do `aasp.py`; aqui não existe equivalente ainda.
   - a mesa dos 1.067 faltantes do Datajud · mensagens enviadas · gestão por ano e mês ·
     a agenda no Google · agendamento das automações (launchd) · rotação do `servidor.log`.
5. **Ressalvas menores do laudo de fechamento**, todas listadas lá com arquivo e linha.

## Decisões do Lucas que valem mais que qualquer proposta

Estão em `docs/respostas-do-lucas.md`: existe LEAD antes da assinatura (Lailla e ZapSign);
pendência tem tipo e só a de documento trava etapa; documento pedido e não recebido continua
pendente; quem aprova a inicial é a equipe de Petição Inicial; repasse é do financeiro; os oito
setores estão fechados e o organograma se edita na ficha da pessoa; a direção do trabalhista é
o Glauco, com o Dr. Vitor como segunda conta.

## O que NÃO se faz aqui

Airtable é somente leitura. Não tocar em `prev_2026_09` nem no esquema `juridico` do Supabase.
Nada de `~/ggv-juridico` (previdenciário) nem `~/ggv-portal` (financeiro) — o previdenciário da
Mapech virou o oficial e nosso trabalho lá está encerrado. Nenhum dado de cliente no
repositório: nome, CPF, telefone, e-mail ou número CNJ, em nenhum arquivo.
