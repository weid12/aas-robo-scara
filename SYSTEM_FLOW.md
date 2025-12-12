# Fluxo Completo do Sistema - AAS SCARA Robot Monitoring

## Visão Geral da Arquitetura

Este sistema monitora um robô SCARA através de OPC UA, persiste os dados seguindo o padrão Asset Administration Shell (AAS), e disponibiliza visualização web em tempo real.

## Arquitetura do Sistema

```mermaid
graph TB
    subgraph "Camada 1: Dispositivo Físico"
        ROBOT["Robô SCARA<br/>Atuadores e Sensores<br/>OPC UA Server Integrado"]
    end
    
    subgraph "Camada 2: Camada de Aquisição"
        direction TB
        CLIENT["OPC UA Client<br/>client_asyncua.py"]
        CONFIG["Configuração<br/>config_opcua.json"]
        MAPPER["Mapeador<br/>opcua_to_json_mapper.py"]
    end
    
    subgraph "Camada 3: Persistência AAS"
        direction LR
        AAS_FILES["AAS JSON Files<br/>aas-submodels/*.json<br/>(Padrão AAS)"]
        LATEST["Snapshot Atual<br/>latest_data.json"]
        SQLITE["Histórico SQLite<br/>aas_history.sqlite3"]
    end
    
    subgraph "Camada 4: Servidor Local (Opcional)"
        LOCAL_SVR["OPC UA Local Server<br/>server.py<br/>opc.tcp://0.0.0.0:4881"]
    end
    
    subgraph "Camada 5: Backend API"
        direction TB
        
        subgraph "FastAPI - Robot API"
            FASTAPI["FastAPI<br/>/api/robot/*"]
            CRUD["CRUD Layer<br/>crud.py"]
            MODELS["Models<br/>models.py + schemas.py"]
        end
        
        subgraph "Flask - Auth & HR"
            FLASK["Flask<br/>/api/auth/* & /api/hr/*"]
            AUTH_SVC["Auth Service<br/>login/service.py"]
        end
        
        subgraph "Data Routes"
            DATA_ROUTES["Data Routes<br/>data_routes.py<br/>(Séries Temporais)"]
        end
        
        DB_LAYER["Database Layer<br/>persist_db.py"]
    end
    
    subgraph "Camada 6: Frontend Web"
        direction TB
        REACT["React App<br/>Vite + TypeScript"]
        
        subgraph "Páginas Principais"
            HUB["Dashboard Hub<br/>AAS_ScaraMonitoringHub.tsx"]
            DATA_PAGE["Data Analysis<br/>Data.jsx"]
            LOGIN["Login<br/>LoginPage.tsx"]
            REGISTER["Register<br/>Register.jsx"]
        end
        
        subgraph "Componentes"
            GAUGE["Gauges"]
            CHARTS["Charts - Recharts"]
            ROBOT_VIS["Robot Visualization"]
        end
        
        API_SVC["API Service<br/>services/api.ts"]
    end
    
    subgraph "Camada 7: Exportação AAS"
        EXPORT["AASX Exporter<br/>export_aasx.py"]
        AASX_FILE["Arquivo AASX<br/>output/robot_scara.aasx"]
    end
    
    %% Conexões Camada 1-2
    ROBOT -->|"OPC UA<br/>(opc.tcp://192.168.0.120:4880)"| CLIENT
    CONFIG -.->|"JSON Config"| CLIENT
    CLIENT -->|"Python Objects"| MAPPER
    
    %% Conexões Camada 2-3
    MAPPER -->|"File I/O<br/>(JSON)"| AAS_FILES
    MAPPER -->|"File I/O<br/>(JSON)"| LATEST
    MAPPER -->|"SQLAlchemy<br/>(SQL)"| SQLITE
    
    %% Conexões Camada 3-4
    LATEST -->|"File Watch<br/>(JSON)"| LOCAL_SVR
    
    %% Conexões Camada 3-5
    SQLITE <-->|"SQLAlchemy<br/>(ORM)"| DB_LAYER
    DB_LAYER -->|"Python Objects"| CRUD
    DB_LAYER -->|"SQL Queries"| DATA_ROUTES
    CRUD -->|"SQLAlchemy Models"| MODELS
    MODELS -->|"Pydantic Schemas"| FASTAPI
    AUTH_SVC -->|"HTTP/HTTPS<br/>(REST)"| FLASK
    
    %% Conexões Camada 5-6
    FASTAPI -->|"HTTP/REST<br/>(JSON)"| API_SVC
    FLASK -->|"HTTP/REST<br/>(JSON)"| API_SVC
    DATA_ROUTES -->|"HTTP/REST<br/>(JSON)"| API_SVC
    API_SVC -->|"Fetch API<br/>(TypeScript)"| REACT
    REACT -->|"React Components"| HUB
    REACT -->|"React Components"| DATA_PAGE
    REACT -->|"React Router"| LOGIN
    HUB -->|"Props"| GAUGE
    HUB -->|"Props"| CHARTS
    HUB -->|"Props"| ROBOT_VIS
    DATA_PAGE -->|"Props"| CHARTS
    
    %% Conexões Camada 3-7
    AAS_FILES -->|"File I/O<br/>(JSON)"| EXPORT
    EXPORT -->|"ZIP Archive<br/>(AASX)"| AASX_FILE
    
    %% Estilos
    classDef physical fill:#ff6b6b,stroke:#c92a2a,stroke-width:2px,color:#fff
    classDef acquisition fill:#45b7d1,stroke:#1971c2,stroke-width:2px,color:#fff
    classDef persistence fill:#f9ca24,stroke:#f59f00,stroke-width:2px,color:#000
    classDef server fill:#95afc0,stroke:#495057,stroke-width:2px,color:#fff
    classDef backend fill:#6c5ce7,stroke:#5f3dc4,stroke-width:2px,color:#fff
    classDef frontend fill:#fd79a8,stroke:#e03131,stroke-width:2px,color:#fff
    classDef export fill:#a29bfe,stroke:#7048e8,stroke-width:2px,color:#fff
    
    class ROBOT physical
    class CLIENT,CONFIG,MAPPER acquisition
    class AAS_FILES,LATEST,SQLITE persistence
    class LOCAL_SVR server
    class FASTAPI,FLASK,CRUD,MODELS,AUTH_SVC,DATA_ROUTES,DB_LAYER backend
    class REACT,HUB,DATA_PAGE,LOGIN,REGISTER,GAUGE,CHARTS,ROBOT_VIS,API_SVC frontend
    class EXPORT,AASX_FILE export
```

### Descrição das Camadas

**Camada 1 - Dispositivo Físico**: Robô SCARA com atuadores/sensores e servidor OPC UA integrado expondo variáveis industriais.

**Camada 2 - Aquisição**: Cliente Python assíncrono coleta dados via OPC UA e mapeia para estrutura AAS.

**Camada 3 - Persistência**: Três destinos de armazenamento (JSON AAS, snapshot atual, banco histórico SQLite).

**Camada 4 - Servidor Local**: Espelha dados via OPC UA para consumo externo sem sobrecarregar o robô.

**Camada 5 - Backend**: API híbrida (FastAPI para dados do robô, Flask para autenticação/HR).

**Camada 6 - Frontend**: SPA React com dashboard em tempo real, análise histórica e autenticação.

**Camada 7 - Exportação**: Geração de pacotes AASX padronizados para interoperabilidade.

### Protocolos de Comunicação

- **OPC UA** (opc.tcp): Comunicação industrial entre robô e cliente de aquisição
- **HTTP/REST** (JSON): APIs backend (FastAPI/Flask) para frontend
- **SQLAlchemy/SQL**: Persistência e consultas ao banco de dados SQLite
- **File I/O** (JSON): Leitura/escrita de arquivos de configuração e dados AAS
- **WebSocket** (futuro): Comunicação em tempo real planejada

## Diagrama de Fluxo

```mermaid
graph TB
    subgraph "Fonte de Dados"
        Robot[Robô SCARA<br/>OPC UA Server Integrado]
    end
    
    subgraph "Aquisição de Dados"
        OPCClient[client_asyncua.py<br/>Cliente OPC UA]
        Config[config_opcua.json<br/>Mapeamento]
    end
    
    subgraph "Persistência"
        JSON[latest_data.json<br/>Snapshot Atual]
        DB[(aas_history.sqlite3<br/>Histórico)]
        AAS[aas-submodels/*.json<br/>Arquivos AAS]
    end
    
    subgraph "Servidor Local"
        LocalServer[server.py<br/>OPC UA Server Local]
    end
    
    subgraph "Backend API"
        Flask[Flask App<br/>Auth + HR]
        FastAPI[FastAPI App<br/>Robot Data]
        DBModule[persist_db.py<br/>Camada de Dados]
    end
    
    subgraph "Frontend Web"
        React[React App<br/>Vite + TypeScript]
        Dashboard[Dashboard<br/>Visualização]
        DataView[Data View<br/>Análise Histórica]
    end
    
    Robot -->|OPC UA<br/>opc.tcp://192.168.0.120:4880| OPCClient
    Config -.->|JSON Config| OPCClient
    OPCClient -->|File I/O| JSON
    OPCClient -->|SQLAlchemy| DB
    OPCClient -->|File I/O| AAS
    JSON -->|File Watch| LocalServer
    DB -->|SQL Query| DBModule
    DBModule -->|ORM| FastAPI
    FastAPI -->|HTTP/REST| React
    Flask -->|HTTP/REST| React
    React -->|React Router| Dashboard
    React -->|React Router| DataView
```

## Diagrama de Classes

```mermaid
classDiagram
    %% Backend Models
    class RobotState {
        +Integer id
        +DateTime timestamp
        +String status
        +String mode
        +Float cycle_time_s
        +Float joint1_deg
        +Float joint2_deg
        +Float joint3_mm
        +Float joint4_deg
        +Float temperature_c
        +Float energy_kwh
        +Float oee
        +Float availability
        +Float performance
        +Float quality
    }
    
    class RobotStateBase {
        +datetime timestamp
        +str status
        +str mode
        +Optional~float~ cycle_time_s
        +Optional~float~ joint1_deg
        +Optional~float~ joint2_deg
        +Optional~float~ joint3_mm
        +Optional~float~ joint4_deg
        +Optional~float~ temperature_c
        +Optional~float~ energy_kwh
        +Optional~float~ oee
        +Optional~float~ availability
        +Optional~float~ performance
        +Optional~float~ quality
    }
    
    class RobotStateRead {
        +int id
    }
    
    class RobotSummary {
        +date date
        +float operation_time_s
        +float downtime_s
        +int cycles
        +float energy_kwh
        +Optional~float~ oee_avg
        +Optional~float~ availability_avg
        +Optional~float~ performance_avg
        +Optional~float~ quality_avg
    }
    
    %% Frontend Types
    class RobotStateTS {
        +number id
        +string timestamp
        +string status
        +string mode
        +number|null cycle_time_s
        +number|null joint1_deg
        +number|null joint2_deg
        +number|null joint3_mm
        +number|null joint4_deg
        +number|null temperature_c
        +number|null energy_kwh
        +number|null oee
        +number|null availability
        +number|null performance
        +number|null quality
    }
    
    class RobotSummaryTS {
        +string date
        +number operation_time_s
        +number downtime_s
        +number cycles
        +number energy_kwh
        +number|null oee_avg
        +number|null availability_avg
        +number|null performance_avg
        +number|null quality_avg
    }
    
    %% CRUD Operations
    class RobotCRUD {
        +get_latest_state(db) RobotState
        +get_history(db, limit) List~RobotState~
        +get_summary_metrics(db) RobotSummary
    }
    
    %% API Service
    class RobotAPI {
        +getLatestState() Promise~RobotStateTS~
        +getHistory(limit) Promise~RobotStateTS[]~
        +getSummaryMetrics() Promise~RobotSummaryTS~
    }
    
    %% Database Persistence
    class PersistDB {
        +save_all_submodels(db_path, data)
        +init_db(db_path)
        +backfill_normalized_from_json(db_path)
    }
    
    %% OPC UA Client
    class OPCUAClient {
        +map_opcua_to_submodels(client, config) Dict
        +load_config(path) Dict
        +write_json_atomic(filepath, data)
    }
    
    %% Relationships
    RobotStateRead --|> RobotStateBase : extends
    RobotState ..> RobotStateRead : maps to
    RobotStateTS ..> RobotStateRead : mirrors
    RobotSummaryTS ..> RobotSummary : mirrors
    
    RobotCRUD ..> RobotState : queries
    RobotCRUD ..> RobotSummary : creates
    RobotAPI ..> RobotCRUD : calls
    
    OPCUAClient ..> PersistDB : uses
    PersistDB ..> RobotState : persists
```

## Diagramas de Sequência

### Sequência 1: Aquisição e Persistência de Dados

```mermaid
sequenceDiagram
    participant Robot as Robô SCARA/PLC
    participant OPC as OPC UA Server
    participant Client as client_asyncua.py
    participant Config as config_opcua.json
    participant DB as persist_db.py
    participant SQLite as aas_history.sqlite3
    participant JSON as latest_data.json
    participant AAS as aas-submodels/*.json

    Client->>Config: load_config()
    Config-->>Client: Retorna mapeamento
    
    loop Ciclo de Leitura (intervalo configurável)
        Client->>OPC: Conecta ao servidor
        OPC-->>Client: Conexão estabelecida
        
        Client->>OPC: Lê nós configurados
        Robot->>OPC: Atualiza variáveis
        OPC-->>Client: Retorna valores
        
        Client->>Client: map_opcua_to_submodels()
        Client->>Client: Converte tipos OPC UA
        
        par Persistência Paralela
            Client->>JSON: write_json_atomic()
            JSON-->>Client: Snapshot salvo
        and
            Client->>DB: save_all_submodels()
            DB->>SQLite: INSERT snapshots
            DB->>SQLite: INSERT timeseries
            SQLite-->>DB: Confirmação
            DB-->>Client: Dados persistidos
        and
            Client->>AAS: update_aas_submodels_from_opcua()
            AAS-->>Client: Arquivos atualizados
        end
    end
```

### Sequência 2: Monitoramento em Tempo Real (Dashboard)

```mermaid
sequenceDiagram
    participant User as Usuário
    participant Browser as React App
    participant API as RobotAPI Service
    participant Backend as FastAPI
    participant CRUD as RobotCRUD
    participant DB as SQLite

    User->>Browser: Acessa /hub
    Browser->>Browser: Verifica autenticação
    Browser->>API: getLatestState()
    API->>Backend: GET /api/robot/state/latest
    Backend->>CRUD: get_latest_state(db)
    CRUD->>DB: SELECT * FROM robot_state ORDER BY timestamp DESC LIMIT 1
    DB-->>CRUD: Retorna último registro
    CRUD-->>Backend: RobotState
    Backend-->>API: JSON (RobotStateRead)
    API-->>Browser: Promise<RobotState>
    Browser->>Browser: Atualiza componentes
    Browser->>User: Exibe Dashboard

    loop Polling a cada 2 segundos
        Browser->>API: getLatestState()
        API->>Backend: GET /api/robot/state/latest
        Backend->>CRUD: get_latest_state(db)
        CRUD->>DB: SELECT...
        DB-->>CRUD: Dados
        CRUD-->>Backend: RobotState
        Backend-->>API: JSON
        API-->>Browser: Dados atualizados
        Browser->>Browser: Re-renderiza gauges/charts
    end
```

### Sequência 3: Análise Histórica

```mermaid
sequenceDiagram
    participant User as Usuário
    participant Browser as React App
    participant Backend as Flask/FastAPI
    participant DB as SQLite

    User->>Browser: Acessa aba "Data"
    Browser->>User: Exibe filtros de período
    
    User->>Browser: Seleciona período (ex: 01/11 - 07/11)
    Browser->>Backend: GET /api/data/timeseries?submodel=OperationalData&path=JointPosition1&start=2024-11-01&end=2024-11-07
    
    Backend->>DB: SELECT value, created_at FROM timeseries WHERE...
    DB-->>Backend: Array de registros
    
    Backend->>Backend: Formata resposta {rows: [{t, v}]}
    Backend-->>Browser: JSON com série temporal
    
    Browser->>Browser: Renderiza gráfico (Recharts)
    Browser->>User: Exibe visualização
    
    User->>Browser: Exporta dados
    Browser->>Browser: Gera CSV/Excel
    Browser->>User: Download do arquivo
```

### Sequência 4: Autenticação de Usuário

```mermaid
sequenceDiagram
    participant User as Usuário
    participant Browser as React App
    participant Backend as Flask
    participant AuthService as login/service.py
    participant ExtAPI as API Externa (AD)

    User->>Browser: Insere credenciais
    Browser->>Backend: POST /api/auth/login {userId, password}
    
    Backend->>AuthService: authenticate_user(userId, password)
    
    AuthService->>AuthService: _normalize_base_url()
    
    loop Estratégias de Autenticação
        alt Estratégia 1: POST JSON
            AuthService->>ExtAPI: POST /api/ad/authenticate (JSON body)
            ExtAPI-->>AuthService: Response
        end
        
        alt Estratégia 2: POST Query
            AuthService->>ExtAPI: POST /api/ad/authenticate?userId=X&password=Y
            ExtAPI-->>AuthService: Response
        end
        
        alt Estratégia 3: GET Query
            AuthService->>ExtAPI: GET /api/ad/authenticate?userId=X&password=Y
            ExtAPI-->>AuthService: Response
        end
        
        break Sucesso (status < 400 ou 401/403)
            AuthService->>AuthService: _finalize_response()
        end
    end
    
    AuthService-->>Backend: AuthResult {payload, status_code}
    Backend-->>Browser: JSON {IsAuthenticated: true/false}
    
    alt Autenticação bem-sucedida
        Browser->>Browser: Armazena em AuthContext
        Browser->>User: Redireciona para /hub
    else Falha na autenticação
        Browser->>User: Exibe mensagem de erro
    end
```

### Sequência 5: Exportação AASX

```mermaid
sequenceDiagram
    participant Dev as Desenvolvedor
    participant Script as export_aasx.py
    participant Files as aas-submodels/*.json
    participant AASCore as aas-core3
    participant Output as output/robot.aasx

    Dev->>Script: python -m aas_export.export_aasx
    Script->>Files: Lê todos Submodel_*.json
    Files-->>Script: Lista de submodelos JSON
    
    loop Para cada submodelo
        Script->>Script: _normalize_submodel_json()
        Script->>Script: Converte arrays em SubmodelElementList
        Script->>AASCore: submodel_from_jsonable()
        AASCore-->>Script: Objeto Submodel validado
    end
    
    Script->>Script: _make_shell_for_submodels()
    Script->>AASCore: Cria AssetAdministrationShell
    Script->>AASCore: Cria Environment
    
    Script->>AASCore: write_env_as_xml()
    AASCore-->>Script: XML serializado
    
    Script->>Script: write_minimal_aasx()
    Script->>Output: Cria arquivo ZIP
    Script->>Output: Adiciona [Content_Types].xml
    Script->>Output: Adiciona aasx/aas.xml
    Script->>Output: Adiciona aasx/aasx-origin
    
    Output-->>Script: Arquivo criado
    Script-->>Dev: ✓ AASX exportado com sucesso
```

## Componentes Principais

### 1. Cliente OPC UA (`opcua_client/client_asyncua.py`)

**Responsabilidade**: Coletar dados do robô via OPC UA e distribuir para múltiplos destinos.

**Fluxo de Execução**:
1. Carrega configuração de `config_opcua.json`
2. Conecta ao servidor OPC UA do robô (`opc.tcp://192.168.0.120:4880`)
3. Para cada ciclo de leitura:
   - Lê valores dos nós OPC UA configurados
   - Mapeia para estrutura de submodelos AAS
   - **Salva em 3 destinos**:
     - `latest_data.json`: Snapshot mais recente
     - `data/aas_history.sqlite3`: Histórico via `persist_db.save_all_submodels()`
     - `aas-submodels/*.json`: Atualiza arquivos AAS padrão

**Modos de Operação**:
- `--once`: Executa um ciclo único
- Modo contínuo: Loop com intervalo configurável

**Arquivos Auxiliares**:
- `opcua_to_json_mapper.py`: Conversão de tipos OPC UA para JSON
- `client_read_local.py`: Cliente simplificado para debug
- `localizador.py`: Ferramenta de indexação de nós OPC UA

### 2. Persistência de Dados (`database/persist_db.py`)

**Responsabilidade**: Gerenciar armazenamento SQLite com schema otimizado.

**Schema do Banco**:

```sql
-- Snapshots JSON completos
CREATE TABLE submodel_snapshots_json (
    id INTEGER PRIMARY KEY,
    submodel_name TEXT,
    data TEXT,  -- JSON completo
    created_at TEXT
);

-- Snapshots normalizados (1 linha por elemento)
CREATE TABLE submodel_snapshots (
    id INTEGER PRIMARY KEY,
    submodel_name TEXT,
    idshort TEXT,  -- Caminho completo (ex: "OperationalData.JointPosition1")
    value_text TEXT,
    value_num REAL,
    value_bool INTEGER,
    created_at TEXT
);

-- Séries temporais (apenas valores numéricos)
CREATE TABLE timeseries (
    id INTEGER PRIMARY KEY,
    submodel_name TEXT,
    element_path TEXT,
    value REAL,
    created_at TEXT
);
```

**Funcionalidades**:
- Escrita atômica com transações
- Migração automática de dados legados
- Tratamento especial para arrays (JointPosition)

### 3. Backend API (`aas_web_template/backend`)

**Arquitetura Híbrida**: Flask + FastAPI montados via ASGI.

#### 3.1 FastAPI - Robot API (`robot_api/`)

**Endpoints**:
- `GET /api/robot/state/latest`: Estado mais recente
- `GET /api/robot/state/history?limit=50`: Histórico
- `GET /api/robot/metrics/summary`: Métricas agregadas do dia

**Camada de Dados** (`crud.py`):
- `get_latest_state()`: Última linha da tabela `robot_state`
- `get_history()`: Últimos N registros
- `get_summary_metrics()`: Calcula OEE, tempo de operação, downtime

**Modelos** (`models.py`):
```python
class RobotState(Base):
    __tablename__ = "robot_state"
    id, timestamp, status, mode
    cycle_time_s, joint1_deg, joint2_deg, joint3_mm, joint4_deg
    temperature_c, energy_kwh
    oee, availability, performance, quality
```

**Seed Data** (`seed_data.py`):
- Gera 180 registros fictícios para desenvolvimento
- Simula variação realista de métricas

#### 3.2 Flask - Auth & Integração (`login/`, `hr_proxy.py`)

**Endpoints**:
- `POST /api/auth/login`: Autenticação de usuário
- `GET /api/hr/employee?userName=X`: Proxy para sistema HR

**Estratégia de Auth** (`login/service.py`):
- Tenta múltiplos formatos de requisição (POST JSON, POST query, GET query)
- Fallback automático entre estratégias

#### 3.3 Data Routes (`data_routes.py`)

**Endpoints para análise histórica**:
- `GET /api/data/paths`: Lista todas as métricas disponíveis
- `GET /api/data/timeseries?submodel=X&path=Y`: Série temporal
- `GET /api/data/snapshots?submodel=X`: Snapshots normalizados
- `GET /api/data/stats`: Estatísticas gerais do banco
- `GET /api/data/latest`: Valores mais recentes de todas as métricas

### 4. Frontend (`aas_web_template/frontend`)

**Stack**: React 18 + Vite + TypeScript + Recharts

#### 4.1 Estrutura de Rotas (`App.tsx`)

```
/login          → LoginPage
/hub            → AAS_ScaraMonitoringHub (Dashboard principal)
/data           → Data (Análise histórica)
/register       → Register (Cadastro de planos)
```

Todas as rotas (exceto login) protegidas por `ProtectedRoute`.

#### 4.2 Dashboard (`pages/ProductionHub/AAS_ScaraMonitoringHub.tsx`)

**Componentes**:
- `StatusCard`: Status atual (Running/Idle/Alarm)
- `GaugeCard`: Medidores circulares (OEE, Availability, Performance, Quality)
- `MetricCard`: Métricas numéricas (temperatura, energia, tempo de ciclo)
- `RobotCellCard`: Visualização 3D das juntas
- `HistoryChart`: Gráfico de linha com histórico
- `EventsTable`: Tabela de eventos recentes

**Polling**: Atualiza a cada 2 segundos via `setInterval`.

#### 4.3 Data View (`pages/Data/Data.jsx`)

**Funcionalidades**:
- Filtro de período (RangeFilterInline)
- Tabela paginada com dados históricos
- Formatação brasileira de números (1.234,56)
- Export de dados

#### 4.4 Serviços (`services/api.ts`)

```typescript
getLatestState(): Promise<RobotState>
getHistory(limit): Promise<RobotState[]>
getSummaryMetrics(): Promise<RobotSummary>
```

### 5. Servidor OPC UA Local (`server_opcua_local/server.py`)

**Responsabilidade**: Espelhar dados do `latest_data.json` via OPC UA.

**Fluxo**:
1. Carrega `latest_data.json` inicial
2. Cria estrutura de nós OPC UA espelhando a hierarquia JSON
3. Inicia servidor em `opc.tcp://0.0.0.0:4881/`
4. Monitora alterações no arquivo (polling a cada 1s)
5. Atualiza valores dos nós quando arquivo muda

**Uso**: Permite que outros clientes OPC UA consumam os dados sem sobrecarregar o PLC real.

### 6. Exportação AAS (`aas_export/export_aasx.py`)

**Responsabilidade**: Gerar pacotes AASX válidos.

**Fluxo**:
1. Lê arquivos JSON de `aas-submodels/`
2. Normaliza estrutura (converte arrays em SubmodelElementList)
3. Cria Environment AAS com Shell e Submodels
4. Serializa para XML
5. Empacota em arquivo ZIP (formato AASX)

**Saída**: Arquivo `.aasx` compatível com ferramentas AAS padrão.

## Fluxos de Uso Típicos

### Fluxo 1: Monitoramento em Tempo Real

```
1. Robô executa movimento
2. PLC atualiza variáveis OPC UA
3. client_asyncua.py lê valores (ciclo a cada 0.1s)
4. Dados salvos em SQLite e latest_data.json
5. Frontend consulta /api/robot/state/latest (polling 2s)
6. Dashboard atualiza gauges e gráficos
```

### Fluxo 2: Análise Histórica

```
1. Usuário acessa aba "Data"
2. Seleciona período (ex: última semana)
3. Frontend chama /api/data/timeseries?submodel=OperationalData&path=...
4. Backend consulta tabela timeseries com filtro de data
5. Retorna array de {t: timestamp, v: value}
6. Frontend renderiza gráfico com Recharts
```

### Fluxo 3: Autenticação

```
1. Usuário insere credenciais
2. POST /api/auth/login
3. Backend tenta autenticar via API externa (AUTH_API_BASE)
4. Se sucesso, retorna token/sessão
5. Frontend armazena em contexto (AuthProvider)
6. Rotas protegidas verificam autenticação
```

### Fluxo 4: Geração de AASX

```
1. Executar script: python -m aas_export.export_aasx
2. Lê todos Submodel_*.json de aas-submodels/
3. Valida e normaliza estrutura
4. Gera Environment completo
5. Exporta para output/robot_scara.aasx
```

## Configuração e Deploy

### Variáveis de Ambiente

```bash
# OPC UA
OPCUA_SERVER_URL=opc.tcp://192.168.0.120:4880
LOG_LEVEL=INFO

# Backend
PORT=5000
AUTH_API_BASE=http://auth-server:8080
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Frontend
VITE_API_URL=http://localhost:5000
```

### Inicialização

```bash
# 1. Backend
cd aas_web_template/backend
.venv\Scripts\activate
python app.py

# 2. Frontend
cd aas_web_template/frontend
npm install
npm run dev

# 3. Cliente OPC UA (opcional, se robô disponível)
cd opcua_client
python client_asyncua.py

# 4. Servidor OPC UA Local (opcional, para testes)
cd server_opcua_local
python server.py
```

## Tecnologias Utilizadas

**Backend**:
- Python 3.10+
- FastAPI (API moderna)
- Flask (compatibilidade legada)
- SQLAlchemy (ORM)
- asyncua (cliente/servidor OPC UA)
- aas-core3 (validação AAS)

**Frontend**:
- React 18
- TypeScript
- Vite (build tool)
- Recharts (visualização)
- React Router (navegação)

**Banco de Dados**:
- SQLite (desenvolvimento/produção leve)

**Protocolos**:
- OPC UA (comunicação industrial)
- HTTP/REST (API web)
- WebSocket (futuro: real-time)
