# Prazo processual — diagrama

> Gerado de `fluxo_transicoes` por `gerar_governanca.py`. Governa `prazos.situacao`.

```mermaid
flowchart TD
    ABERTO(["Aberto<br/><small>Jurídico</small>"])
    SUSPENSO["Suspenso<br/><small>Jurídico</small>"]
    CUMPRIDO["Cumprido<br/><small>Jurídico</small>"]
    PERDIDO["Perdido<br/><small>Gestão</small>"]
    SEM_OBJETO["Sem objeto<br/><small>Jurídico</small>"]

    ABERTO -->|"Cumprido: registrar protocolo 🔒"| CUMPRIDO
    ABERTO -->|"Registrar prazo perdido (GESTOR) 🔒"| PERDIDO
    ABERTO -->|"Sem objeto 🔒"| SEM_OBJETO
    ABERTO -->|"Suspender 🔒"| SUSPENSO
    CUMPRIDO -->|"Reabrir (registro errado) (GESTOR) 🔒"| ABERTO
    SEM_OBJETO -->|"Reabrir (GESTOR) 🔒"| ABERTO
    SUSPENSO -->|"Retomar contagem 🔒"| ABERTO
    SUSPENSO -->|"Sem objeto 🔒"| SEM_OBJETO

    classDef inicial fill:#dcfce7,stroke:#16a34a,color:#14532d
    class ABERTO inicial
    classDef final fill:#e5e7eb,stroke:#6b7280,color:#374151
    class CUMPRIDO,PERDIDO,SEM_OBJETO final
```

🔒 = a ação só aparece quando o pré-requisito está cumprido. O que cada um exige está
em [`../governanca.md`](../governanca.md).
