# O que precisa ser aplicado depois de cada carga

A carga do Airtable recria `pessoas`, e com ela **setor e chefia se perdem** — as contas de
acesso (`usuarios`) já são preservadas pelo `migrar.py`, o organograma ainda não
[CONFIRMAR com o DBA: preservar `setor` e `supervisor_id` como preserva as contas].

Enquanto isso, o que está decidido vive aqui, versionado, e se aplica com um comando:

```bash
./.venv/bin/python equipe_setores.py dados_iniciais/equipe.csv          # confere, não grava
./.venv/bin/python equipe_setores.py dados_iniciais/equipe.csv --aplicar
```

## `equipe.csv` — o que o Lucas já decidiu (03/09/2026)

- **Glauco** é o sócio do trabalhista, setor Direção, perfil DIRECAO.
- **Dr. Vitor Esteves** é a segunda direção, para quando o Glauco está fora; fica na Gestão.
  São duas contas, não uma direção de plantão: o sistema não sabe quando alguém viajou.
- Rai e Lucas **não** são sócios do trabalhista e não têm perfil de direção aqui.

Os outros 70 ainda estão sem setor, e é isso que trava a aprovação da petição inicial: sem
ninguém em **Petição Inicial**, as 54 minutas paradas não têm quem aprove. A planilha
`organograma-trabalhista.xlsx` foi enviada ao Lucas em 03/09/2026 para preencher os 72 de uma
vez; quando voltar, vira linhas deste CSV.

O organograma do dia a dia **não é este arquivo**: é a ficha da pessoa em `/equipe/{id}`, onde
setor e chefia se editam com rastro. Este CSV é só a carga inicial e a rede contra a recarga.
