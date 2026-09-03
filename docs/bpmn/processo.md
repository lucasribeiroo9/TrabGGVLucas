# Ciclo do processo — diagrama

> Gerado de `fluxo_transicoes` por `gerar_governanca.py`. Governa `processos.fase`.

```mermaid
flowchart TD
    CONHECIMENTO(["Conhecimento<br/><small>Jurídico · 365d</small>"])
    RECURSAL["Recursal<br/><small>Jurídico · 365d</small>"]
    EXECUCAO_PROVISORIA["Execução provisória<br/><small>Jurídico · 365d</small>"]
    EXECUCAO_DEFINITIVA["Execução definitiva<br/><small>Jurídico · 365d</small>"]
    ACORDO["Acordo em cumprimento<br/><small>Jurídico · 365d</small>"]
    RECEBENDO["Recebendo<br/><small>Financeiro · 30d</small>"]
    SOBRESTADO["Sobrestado<br/><small>Jurídico</small>"]
    ENCERRADO["Encerrado<br/><small>Jurídico</small>"]
    DESISTENCIA["Desistência<br/><small>Jurídico</small>"]

    ACORDO -->|"Encerrar (ADVOGADO) 🔒"| ENCERRADO
    ACORDO -->|"Quebra de acordo: executar (ADVOGADO) 🔒"| EXECUCAO_DEFINITIVA
    ACORDO -->|"Parcelas quitadas 🔒"| RECEBENDO
    CONHECIMENTO -->|"Acordo homologado 🔒"| ACORDO
    CONHECIMENTO -->|"Desistência homologada (ADVOGADO) 🔒"| DESISTENCIA
    CONHECIMENTO -->|"Encerrar (ADVOGADO) 🔒"| ENCERRADO
    CONHECIMENTO -->|"Trânsito em julgado favorável (ADVOGADO) 🔒"| EXECUCAO_DEFINITIVA
    CONHECIMENTO -->|"Sentença publicada: recurso interposto (ADVOGADO) 🔒"| RECURSAL
    CONHECIMENTO -->|"Sobrestar 🔒"| SOBRESTADO
    DESISTENCIA -->|"Reabrir (DIRECAO) 🔒"| CONHECIMENTO
    ENCERRADO -->|"Reabrir (DIRECAO) 🔒"| CONHECIMENTO
    ENCERRADO -->|"Reabrir execução (DIRECAO) 🔒"| EXECUCAO_DEFINITIVA
    EXECUCAO_DEFINITIVA -->|"Acordo na execução 🔒"| ACORDO
    EXECUCAO_DEFINITIVA -->|"Desistência homologada (ADVOGADO) 🔒"| DESISTENCIA
    EXECUCAO_DEFINITIVA -->|"Encerrar (ADVOGADO) 🔒"| ENCERRADO
    EXECUCAO_DEFINITIVA -->|"Valor liberado 🔒"| RECEBENDO
    EXECUCAO_DEFINITIVA -->|"Sobrestar 🔒"| SOBRESTADO
    EXECUCAO_PROVISORIA -->|"Acordo homologado 🔒"| ACORDO
    EXECUCAO_PROVISORIA -->|"Desistência homologada (ADVOGADO) 🔒"| DESISTENCIA
    EXECUCAO_PROVISORIA -->|"Encerrar (ADVOGADO) 🔒"| ENCERRADO
    EXECUCAO_PROVISORIA -->|"Trânsito em julgado (ADVOGADO) 🔒"| EXECUCAO_DEFINITIVA
    EXECUCAO_PROVISORIA -->|"Sobrestar 🔒"| SOBRESTADO
    RECEBENDO -->|"Repasse feito: encerrar 🔒"| ENCERRADO
    RECEBENDO -->|"Saldo a executar (ADVOGADO) 🔒"| EXECUCAO_DEFINITIVA
    RECURSAL -->|"Acordo homologado 🔒"| ACORDO
    RECURSAL -->|"Sentença anulada: volta à origem (ADVOGADO) 🔒"| CONHECIMENTO
    RECURSAL -->|"Desistência homologada (ADVOGADO) 🔒"| DESISTENCIA
    RECURSAL -->|"Trânsito desfavorável: encerrar (ADVOGADO) 🔒"| ENCERRADO
    RECURSAL -->|"Trânsito em julgado favorável (ADVOGADO) 🔒"| EXECUCAO_DEFINITIVA
    RECURSAL -->|"Abrir cumprimento provisório (ADVOGADO) 🔒"| EXECUCAO_PROVISORIA
    RECURSAL -->|"Sobrestar 🔒"| SOBRESTADO
    SOBRESTADO -->|"Retomar 🔒"| CONHECIMENTO
    SOBRESTADO -->|"Encerrar (ADVOGADO) 🔒"| ENCERRADO
    SOBRESTADO -->|"Retomar 🔒"| EXECUCAO_DEFINITIVA
    SOBRESTADO -->|"Retomar 🔒"| EXECUCAO_PROVISORIA
    SOBRESTADO -->|"Retomar 🔒"| RECURSAL

    classDef inicial fill:#dcfce7,stroke:#16a34a,color:#14532d
    class CONHECIMENTO inicial
    classDef final fill:#e5e7eb,stroke:#6b7280,color:#374151
    class ENCERRADO,DESISTENCIA final
```

🔒 = a ação só aparece quando o pré-requisito está cumprido. O que cada um exige está
em [`../governanca.md`](../governanca.md).
