# Arquitetura do Sistema - Padrão RAMI 4.0 (Reference Architecture Model Industrie 4.0)

Este documento descreve a arquitetura do sistema de monitoramento do robô SCARA mapeada para as camadas do **RAMI 4.0**, proporcionando uma visão padronizada da Indústria 4.0.

O modelo RAMI 4.0 divide a arquitetura em 6 camadas principais (Layers). Abaixo, apresentamos como os componentes do nosso sistema se encaixam em cada uma dessas camadas, fluindo desde os processos de negócios até o ativo físico.

## Diagrama Mermaid

```mermaid
graph TD
    %% Cores das camadas baseadas em convenções visuais para RAMI 4.0
    classDef business fill:#e0f7fa,stroke:#006064,stroke-width:2px,color:#000
    classDef functional fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000
    classDef information fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef communication fill:#fff8e1,stroke:#f57f17,stroke-width:2px,color:#000
    classDef integration fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000
    classDef asset fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000

    subgraph RAMI_Layers ["Dimensão: Layers (Camadas RAMI 4.0)"]
        direction TB
        
        subgraph Business ["1. Business Layer (Negócios)"]
            direction LR
            DASH["Dashboard Web<br/>(React/Vite)"]
            SYS_MGMT["Gestão de Usuários &<br/>Regras de Negócio (OEE)"]
        end
        
        subgraph Functional ["2. Functional Layer (Funcional)"]
            direction LR
            API_ROBOT["FastAPI<br/>(Lógica de Dados do Robô)"]
            API_HR["Flask App<br/>(Lógica de Auth/HR)"]
            METRICS["Cálculo de Métricas<br/>(Performance, Disponibilidade)"]
        end
        
        subgraph Information ["3. Information Layer (Informação)"]
            direction LR
            AAS_DT["Digital Twin / Modelos AAS<br/>(aas-submodels/*.json)"]
            DB_HIST[("Banco de Dados Histórico<br/>(aas_history.sqlite3)")]
            DB_USER[("Banco de Dados de Usuários<br/>(users.db)")]
            AASX_EXP["Exportador AASX"]
        end
        
        subgraph Communication ["4. Communication Layer (Comunicação)"]
            direction LR
            REST_API["HTTP / REST API<br/>(Comunicação Web)"]
            OPC_SERVER_LOCAL["OPC UA Local Server<br/>(server.py)"]
            OPC_CLIENT["OPC UA Client<br/>(client_asyncua.py)"]
        end
        
        subgraph Integration ["5. Integration Layer (Integração)"]
            direction LR
            MAPPER["Mapeador OPC UA para AAS<br/>(opcua_to_json_mapper.py)"]
            PLC_OPC["Servidor OPC UA Integrado<br/>(Controlador do Robô)"]
        end
        
        subgraph Asset ["6. Asset Layer (Ativos Físicos)"]
            direction LR
            SCARA["Robô SCARA Físico"]
            SENSORS["Sensores de Temperatura,<br/>Atuadores e Juntas"]
        end
    end
    
    %% Atribuição de classes para cores
    class Business,DASH,SYS_MGMT business
    class Functional,API_ROBOT,API_HR,METRICS functional
    class Information,AAS_DT,DB_HIST,DB_USER,AASX_EXP information
    class Communication,REST_API,OPC_SERVER_LOCAL,OPC_CLIENT communication
    class Integration,MAPPER,PLC_OPC integration
    class Asset,SCARA,SENSORS asset

    %% Relacionamentos e Fluxo de Dados (Top-Down e Bottom-Up)
    DASH <-->|Interação do Usuário| API_ROBOT
    DASH <-->|Login/Auth| API_HR
    SYS_MGMT --> METRICS
    
    API_ROBOT <-->|Queries SQL| DB_HIST
    API_HR <-->|Queries SQL| DB_USER
    API_ROBOT --> REST_API
    API_HR --> REST_API
    
    DB_HIST -.->|File Watch| OPC_SERVER_LOCAL
    AAS_DT --> AASX_EXP
    
    OPC_CLIENT -->|Salva arquivos JSON| AAS_DT
    OPC_CLIENT -->|Persiste dados| DB_HIST
    
    MAPPER -->|Estrutura de dados normalizada| OPC_CLIENT
    PLC_OPC <-->|opc.tcp (Leitura de Variáveis)| MAPPER
    
    SCARA -->|Sinais Elétricos / Mecânicos| PLC_OPC
    SENSORS -->|Medições| PLC_OPC
```

## Descrição do Mapeamento

1. **Business Layer (Camada de Negócios):** 
   - Representa os processos de negócio, orchestrando o funcionamento geral do sistema voltado ao usuário final. Aqui reside o **Dashboard Web** (React) e as regras organizacionais (como cálculos de rentabilidade indicados indiretamente pelo OEE e gerenciamento de permissões de usuários).

2. **Functional Layer (Camada Funcional):**
   - Contém a lógica das funções isoladas e serviços do sistema. Engloba o backend híbrido com **FastAPI** (manipulação de dados industriais) e **Flask** (regras de autenticação/RH), além das funções intrínsecas de cálculo de métricas de OEE (Performance, Qualidade, Disponibilidade).

3. **Information Layer (Camada de Informação):**
   - Responsável pelo gerenciamento, armazenamento e provisionamento de dados com uma semântica formal. Aqui encontramos os bancos de dados **SQLite** e o coração do conceito da Indústria 4.0: o modelo **Asset Administration Shell (AAS)** representado por arquivos JSON, além da ferramenta de compilação de pacotes interoperáveis **AASX**.

4. **Communication Layer (Camada de Comunicação):**
   - Lida com a transmissão padronizada de dados. Inclui os protocolos de rede operando na arquitetura corporativa (`HTTP/REST`) entre o Frontend e Backend, e os protocolos industriais de conectividade como o **OPC UA Client** (que adquire os dados) e o **OPC UA Local Server** (que atua como espelho).

5. **Integration Layer (Camada de Integração):**
   - Faz a transição do mundo físico para o digital. Inclui os CLPs (Controladores Lógico Programáveis) e interfaces. O servidor **OPC UA embutido** no controlador do robô e o **módulo mapeador de nós OPC UA para semântica AAS** atuam aqui, traduzindo sinais do chão de fábrica para elementos lógicos compreensíveis computacionalmente.

6. **Asset Layer (Camada de Ativos):**
   - O mundo físico real. Consiste em todos os bens materiais necessários para o processo industrial: o próprio **Robô SCARA**, seus braços mecânicos, juntas, motores e **sensores de temperatura/posição**.
