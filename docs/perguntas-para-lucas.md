# Perguntas para o Lucas (e para o Glauco) — o que só o escritório responde

Numeradas para citar nas respostas. As mesmas marcas `[CONFIRMAR]` estão nos outros documentos.

## Fonte e migração
1. **Qual PROCESSUAL vale?** A CÓPIA tem 1.187 processos a mais (o passivo, quase todo encerrado) e a fase
   atualizada pela leitura dos autos; a PROCESSUAL é a que a equipe edita. Para 1.403 processos a FASE diverge
   (ex.: 757 "CONHECIMENTO" na PROCESSUAL são "ENCERRADO" com data na CÓPIA). Migramos da CÓPIA e completamos
   com a PROCESSUAL? Quando divergem, quem ganha?
2. A **Conferência de Faltantes** ainda serve? 450 dos 1.067 já estão na PROCESSUAL, 986 na CÓPIA, 78 em
   nenhuma. Ninguém marcou "VALIDAR E SUBIR" e a automação prometida não existe.
3. Os 99 registros do PÓS PROCESSUAL sem processo ligado: importação manual? descartar?
4. O **Astrea** continua em uso (prazos, publicações)? E o ZapSign (há uma view "DADOS ZAPSIGN" na CÓPIA)?

## Funil de entrada
5. A pessoa só entra na base **depois de assinar** (DATA DE ASSINATURA em 99%). Onde ficam os leads que ainda
   não assinaram — no WhatsApp/Lailla? O portal deve ter a etapa "lead" antes da assinatura?
6. O **SLA de 15/20 dias** (🟡/🔴) conta da assinatura até a distribuição? É esse mesmo o prazo interno?
7. **PENDENCIAS** lista o que **falta** ou o que foi **solicitado**? (172 fichas "COMPLETA" têm 4 pendências.)
8. Quem **aprova a petição inicial** (AGUARDANDO APROVAÇÃO → APROVADA)? Há 54 esperando e 6 em criação.
9. A entrevista é presencial, por vídeo ou telefone? Onde fica o conteúdo (RESUMO ENTREVISTA só em 51)?
10. Na **rescisão indireta**, a cadência 5/10/12/15 dias cobra quem, e o que acontece no 15º dia?
11. **Prescrição**: quem recebe o aviso do n8n e o que faz com ele? Querem controlar também a quinquenal?
12. **FONTE** vira dois campos (canal e campanha)? Quais campanhas existem ("PROJETO PUXADA", "DISP LAILLA")?
13. O **captador** recebe comissão por caso e por testemunha? Isso deve entrar no portal ou fica no financeiro?

## Processual
14. O que é **AD VIDEO** (DATA/RESP/STATUS ADVIDEO, view "AD VIDEOS")? Preparação do cliente por vídeo antes da
    audiência? Está vazio na base — o fluxo existe fora dela?
15. O que é o campo **AÇÃO** (data, 7% preenchido)? Difere de DISTRIBUIÇAO?
16. **COMPLEXIDADE A/B/C** muda quem cuida do caso ou só serve a relatório?
17. **CLASSIFICACAO**: querem separar rito (ordinário/sumaríssimo) de classe do incidente (CumPrSe, embargos,
    RR/AIRR)? E "UNA-RS" em AUDIENCIA é "una — rito sumaríssimo"?
18. **STATUS EXECUÇÃO**: a lista limpa da CÓPIA (16 estados) é a boa? Ordem sugerida em `leitura-juridica.md` §12.
19. **AND. NECESSÁRIO** e **PROVIDENCIAS** viram tarefas com dono e prazo (em vez de select)?
20. **REVOGAÇÃO = SIM** tem dois sentidos (revogamos o advogado anterior do cliente × o cliente nos revogou)?
21. Fluxo do **cliente roubado**: detectar → notificação extrajudicial → travar recebimento → recuperar/cobrar.
    É isso? Quem faz cada passo? Existe modelo da notificação?
22. **RESULTADO RECURSO** (PROVIDO/NEGADO…) refere-se ao recurso de quem — nosso ou da reclamada?
23. Há **correspondente no TST** (Planilha Correspondente TST)? Quem alimenta?
24. **SENTENCA / RESULTADO ACORDAO / ULTIMA DECISAO** (RUIM/MÉDIA/ÓTIMA): quem dá a nota e com que critério?
    Mantemos como avaliação separada do resultado objetivo?

## Dinheiro
25. **Honorários contratuais**: 30% do recebido é o padrão (603 de 687 acordos)? Quando é 33–41%?
26. Onde se registra o **repasse ao cliente** (STATUS REPASSE está vazio em 556/556)? Vai para o portal
    financeiro ou para o jurídico?
27. **HONOR TOTAL** exclui sucumbência (SUCUMB RECEBIDO é separado)? A sucumbência é 100% do escritório?
28. ENCERRADO (fase), ARQUIVADO (status judicial) e STATUS ARQUIVAMENTO (PÓS): três coisas ou uma?
29. **TOTAL RECEBIDO = 50 × VALOR ACORDO** em 15 casos — erro de digitação? Corrigir na origem?

## Equipe e integrações
30. Organograma: quem supervisiona quem? Setores (Jurídico, Documentação, Captação, Testemunhas, TI,
    Atendimento, Publicação) — o campo FUNCOES basta ou querem setor + cargo como no previdenciário?
31. **n8n**: quem tem acesso? Precisamos ler os fluxos de lá (aniversário, RI, prescrição, testemunhas,
    Lailla) — são regras de negócio que não estão no Airtable. O disparo de aniversário está falhando em
    ~85% (148 `aniversario_erro`): alguém sabe?
32. A **AUDITORIA TESTEMUNHAS** e o Formulário Interno Único estão em produção? Só há 2 eventos.
33. **FRAGILIDADES**: querem estender para outras empresas? Quem alimenta — o jurídico ou o pipeline de leitura?
34. **TESE PRINCIPAL** (0/797) — querem catálogo de matérias por caso (horas extras, insalubridade, RI, dano moral…)?
