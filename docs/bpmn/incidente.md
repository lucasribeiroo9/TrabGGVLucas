# Incidente de representação — diagrama

> Gerado de `fluxo_transicoes` por `gerar_governanca.py`. Governa `incidentes.situacao`.

```mermaid
flowchart TD
    DETECTADO(["Detectado<br/><small>Jurídico · 5d</small>"])
    NOTIFICADO["Notificado<br/><small>Jurídico · 30d</small>"]
    HONORARIOS_RESERVADOS["Honorários reservados nos autos<br/><small>Jurídico</small>"]
    RECUPERADO["Cliente recuperado<br/><small>Jurídico</small>"]
    HONORARIOS_RECEBIDOS["Honorários recebidos<br/><small>Financeiro</small>"]
    PERDIDO["Perdido<br/><small>Direção</small>"]
    SEM_OBJETO["Alarme falso<br/><small>Jurídico</small>"]

    DETECTADO -->|"Reserva pedida ao juízo (ADVOGADO) 🔒"| HONORARIOS_RESERVADOS
    DETECTADO -->|"Notificação enviada 🔒"| NOTIFICADO
    DETECTADO -->|"Cliente voltou"| RECUPERADO
    DETECTADO -->|"Alarme falso 🔒"| SEM_OBJETO
    HONORARIOS_RESERVADOS -->|"Honorários recebidos 🔒"| HONORARIOS_RECEBIDOS
    HONORARIOS_RESERVADOS -->|"Dar por perdido (DIRECAO) 🔒"| PERDIDO
    HONORARIOS_RESERVADOS -->|"Cliente voltou"| RECUPERADO
    NOTIFICADO -->|"Honorários recebidos 🔒"| HONORARIOS_RECEBIDOS
    NOTIFICADO -->|"Reserva pedida ao juízo (ADVOGADO) 🔒"| HONORARIOS_RESERVADOS
    NOTIFICADO -->|"Dar por perdido (DIRECAO) 🔒"| PERDIDO
    NOTIFICADO -->|"Cliente voltou"| RECUPERADO
    PERDIDO -->|"Reabrir cobrança (DIRECAO) 🔒"| NOTIFICADO

    classDef inicial fill:#dcfce7,stroke:#16a34a,color:#14532d
    class DETECTADO inicial
    classDef final fill:#e5e7eb,stroke:#6b7280,color:#374151
    class RECUPERADO,HONORARIOS_RECEBIDOS,PERDIDO,SEM_OBJETO final
```

🔒 = a ação só aparece quando o pré-requisito está cumprido. O que cada um exige está
em [`../governanca.md`](../governanca.md).
