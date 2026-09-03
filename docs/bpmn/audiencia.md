# Audiência — diagrama

> Gerado de `fluxo_transicoes` por `gerar_governanca.py`. Governa `audiencias.situacao`.

```mermaid
flowchart TD
    DESIGNADA(["Designada<br/><small>Jurídico</small>"])
    EM_PREPARACAO["Em preparação<br/><small>Jurídico</small>"]
    REALIZADA["Realizada<br/><small>Jurídico</small>"]
    REDESIGNADA["Redesignada<br/><small>Jurídico</small>"]
    ADIADA["Adiada sem data<br/><small>Jurídico</small>"]
    NAO_REALIZADA["Não realizada<br/><small>Jurídico</small>"]
    CANCELADA["Cancelada<br/><small>Jurídico</small>"]

    DESIGNADA -->|"Adiada sem data 🔒"| ADIADA
    DESIGNADA -->|"Cancelar 🔒"| CANCELADA
    DESIGNADA -->|"Iniciar preparação"| EM_PREPARACAO
    DESIGNADA -->|"Não realizada 🔒"| NAO_REALIZADA
    DESIGNADA -->|"Registrar realização 🔒"| REALIZADA
    DESIGNADA -->|"Redesignada 🔒"| REDESIGNADA
    EM_PREPARACAO -->|"Adiada sem data 🔒"| ADIADA
    EM_PREPARACAO -->|"Cancelar 🔒"| CANCELADA
    EM_PREPARACAO -->|"Não realizada 🔒"| NAO_REALIZADA
    EM_PREPARACAO -->|"Registrar realização 🔒"| REALIZADA
    EM_PREPARACAO -->|"Redesignada 🔒"| REDESIGNADA
    REALIZADA -->|"Registrada por engano (GESTOR) 🔒"| EM_PREPARACAO

    classDef inicial fill:#dcfce7,stroke:#16a34a,color:#14532d
    class DESIGNADA inicial
    classDef final fill:#e5e7eb,stroke:#6b7280,color:#374151
    class REALIZADA,REDESIGNADA,ADIADA,NAO_REALIZADA,CANCELADA final
```

🔒 = a ação só aparece quando o pré-requisito está cumprido. O que cada um exige está
em [`../governanca.md`](../governanca.md).
