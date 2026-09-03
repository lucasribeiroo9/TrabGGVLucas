# Sistema Operacional GGV Trabalhista — guia do projeto

Sistema do escritório **trabalhista** da GGV, que atua **pelo reclamante** (empregado).
Irmão do sistema previdenciário em `~/ggv-juridico` (GGV Prev): mesmo padrão, mesma cadeia de
ideias, governança própria. **Não mexer** no `~/ggv-juridico`, no `~/ggv-portal` (financeiro) nem
em nada da Mapech — o previdenciário deles virou o oficial e nosso trabalho lá está encerrado.

## Decisões do Lucas (03/09/2026)

- **Fonte de hoje**: base Airtable **BASE GGV - TRAB V3** (`appMFTjWGygZ4ob5T`), lida como
  colaborador somente leitura. Airtable é **somente leitura**, sempre — o escritório trabalha nela.
- **Banco de destino**: o projeto Supabase **PrevGGVLucas** (`yzayjwlgjjnoxdxgruss`, sa-east-1),
  reaproveitado para o trabalhista. **Feito em 03/09/2026**: o `public` do Prev foi renomeado para
  `prev_2026_09` (69 tabelas, 123.264 linhas, 36 funções, 12 gatilhos, `pg_trgm`), conferido
  antes e depois, fora da API e sem acesso para `anon`/`authenticated`. O trabalhista nasce num
  `public` vazio. **Não tocar em `prev_2026_09`** nem no esquema `juridico` (extensão `vector`,
  origem a confirmar com o Lucas). Cópia externa (pg_dump) ainda a fazer no Mac. RLS ligada desde
  a primeira migration.
- **Repositório**: este, `lucasribeiroo9/TrabGGVLucas`, separado do Prev.
- **Governança**: quatro máquinas de estado, como no Prev — cliente (pré-processual), caso,
  processo (conhecimento → recursal → execução) e etapas judiciais (audiência, prazo) — desenhadas a
  partir das opções de select do Airtable + rito da CLT, e **exportadas para o Lucas confirmar
  antes de virar código**.

## Os agentes (`.claude/agents/`)

| Agente | Papel | Escreve em |
|---|---|---|
| `leitor-airtable` | Entende a base e a explica em termos jurídicos. Só leitura | `docs/dicionario-dados.md`, `docs/leitura-juridica.md`, `docs/automacoes-airtable.md` |
| `arquiteto-governanca` | Desenha fluxos, etapas, transições, gates e SLAs | `governanca.sql`, `docs/governanca.md` |
| `dba-migracao` | Esquema e migração com perda zero, prova de contagem | `esquema.sql`, `migrar.py`, `conferir.py` |
| `dev-portal` | As telas, sobre o código do Prev | `app.py`, `templates/`, módulos |
| `auditor` | Cruza o trabalho dos quatro; nada sobe sem TUDO CONFERE | `docs/auditoria-*.md` |

Quem coordena é a sessão principal (diretor). Cada agente lê este arquivo primeiro.

**Modelo por agente** (decisão do Lucas, 03/09/2026, revista no mesmo dia por cota de uso): todos os
agentes rodam em Opus, com o diretor revisando o que entregam. Está no `model:` de cada definição.

## Regras da casa (herdadas do Prev, valem aqui)

1. **Airtable é somente leitura.**
2. **Governança no banco, não na tela.** Gatilhos `BEFORE UPDATE` recusam transição fora do mapa.
3. **Nada de inventar.** O que falta vira `[CONFIRMAR: ...]`.
4. **Nenhum nome de cliente, CPF, telefone, e-mail ou número de processo entra no repositório.**
   Nem em doc, nem em teste, nem em commit. Nome de funcionário pode.
5. **Automação cria tarefa e rascunho; nunca protocola nem move etapa.** Toda execução deixa rastro.
6. **Número na tela sai de consulta**, e todo contador conta dentro do recorte ativo.
7. **Perda zero na migração**: todo campo do Airtable vira coluna nomeada; o que não couber no
   modelo vai para `airtable_bruto` (jsonb) em vez de sumir. `conferir.py` só libera com TUDO CONFERE.
8. **Prazo trabalhista conta em dias úteis** (CLT, art. 775) e nasce da publicação no DEJT — não é a
   regra do JEF/Lei 11.419 que o Prev usa.

## O que vem do Prev sem mudar

`banco.py` (ponte sqlite→psycopg), `auth.py`, `csrf.py`, `execucao.py`, motor de `automacao.py`,
`agenda_google.py`, cofre, tarefas, `equipe.py`, `gerar_governanca.py`, padrão de `conferir.py`.
O que muda é o domínio: `governanca.sql`, tabelas de processo, `migrar.py`, `prazo_legal.py` e as
telas de audiência, defesa/réplica, cálculo, testemunhas, empresas e pós-processual.
