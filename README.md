# AAS Robô Scara — Sistema de Monitoramento

Sistema integrado para monitoramento de robô SCARA utilizando Asset Administration Shell (AAS) e OPC UA.

## 📋 Estrutura do Projeto

```
aas-robo-scara/
├── acquisition/                # Camada de aquisição de dados
│   ├── opcua_client/           # Cliente OPC UA (coleta em tempo real)
│   └── server_opcua_local/     # Servidor OPC UA local (simulação)
├── digital_twin/               # Submodelos AAS (arquivos JSON/AASX)
├── persistence/                # Camada de persistência
│   └── db/                     # Banco de dados SQLite
├── web/                        # Aplicação Web
│   ├── backend/                # Flask + FastAPI (Python)
│   └── frontend/               # React + Vite + TypeScript
├── docs/                       # Documentação técnica
├── requirements.txt            # Dependências Python (aquisição)
└── start.ps1                   # Script de inicialização rápida
```

## 🛠️ Tecnologias

### Backend (`web/backend`)
- Python 3.11+ com ambiente virtual `.venv`
- **FastAPI** — API de dados do robô (`/api/robot/*`, `/api/users/*`)
- **Flask** — Autenticação e rotas de dados (`/api/auth/*`, `/api/data/*`)
- **Uvicorn** — Servidor ASGI (integra Flask + FastAPI)
- **SQLAlchemy** + **SQLite** — Persistência de usuários e estados do robô
- **bcrypt** — Hash seguro de senhas

### Frontend (`web/frontend`)
- React 18 + TypeScript
- Vite (build e dev server)
- TailwindCSS
- Proxy configurado para `/api` → `http://localhost:5000`

### Aquisição de Dados (`acquisition/`)
- **asyncua** — Cliente OPC UA assíncrono
- **aiofiles**, **aiosqlite** — I/O assíncrono
- Python-dotenv — Configuração via variáveis de ambiente

## ⚙️ Requisitos

- Python 3.11+
- Node.js 18+
- Git

## 🚀 Inicialização Rápida

Execute o script na raiz do projeto para abrir backend e frontend em terminais separados:

```powershell
.\start.ps1
```

> Se o Windows bloquear a execução por política de segurança:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

## 🔧 Instalação Manual

### Backend
```powershell
cd web\backend
# Ambiente virtual já incluso em .venv — ative-o:
.\.venv\Scripts\Activate.ps1
# Instalar / atualizar dependências:
pip install -r requirements.txt
# Iniciar servidor (http://localhost:5000):
python app.py
```

### Frontend
```powershell
cd web\frontend
npm install          # apenas na primeira vez
npm run dev          # http://localhost:5173
```

### Cliente OPC UA (dados reais)
```powershell
cd acquisition\opcua_client
# Configure o endereço do servidor OPC UA:
$env:OPCUA_SERVER_URL="opc.tcp://<IP-DO-ROBO>:4840"
python client_asyncua.py
```

### Servidor OPC UA Local (simulação)
```powershell
cd acquisition\server_opcua_local
python server.py     # opc.tcp://0.0.0.0:4881
```

## 📝 Acesso

| Serviço | URL |
|---|---|
| **Frontend** | http://localhost:5173 |
| **Backend API** | http://localhost:5000 |
| **Docs FastAPI** | http://localhost:5000/docs |

### Credenciais Padrão
| Campo | Valor |
|---|---|
| Usuário | `admin` |
| Senha | `admin123` |

> A autenticação é feita localmente via banco de dados SQLite (`web/backend/user_management/users_v2.db`).
> Para criar ou redefinir o usuário admin, execute:
> ```powershell
> cd web\backend
> .\.venv\Scripts\python.exe create_test_user.py
> ```

## 🔧 Configuração

### Backend — Variáveis de Ambiente
Crie um arquivo `.env` em `web/backend/`:
```bash
PORT=5000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
DEBUG=False
```

### Cliente OPC UA — Configuração
Edite `acquisition/opcua_client/config_opcua.json` para ajustar:
- Endereço do servidor OPC UA
- Mapeamento de variáveis (NodeIDs)
- Intervalo de coleta

## 📊 Funcionalidades

### Dashboard Web
- Monitoramento em tempo real do robô SCARA
- Visualização de estado operacional (Running / Idle / Alarm)
- Métricas OEE (Disponibilidade, Performance, Qualidade)
- Gráficos de juntas e séries temporais
- Histórico de eventos e temperatura

### Integração AAS
- Exportação de dados no padrão Asset Administration Shell
- Submodelos JSON: Identificação, Dados Técnicos, Dados Operacionais, Performance

### Gestão de Usuários
- Cadastro com roles (`director`, `operator`, etc.)
- Autenticação local com bcrypt
- Gerenciamento via API REST (`/api/users/*`)

## 📦 Dependências (`requirements.txt`)

| Grupo | Versões-chave |
|---|---|
| OPC UA | `asyncua==1.0.3`, `aiofiles==23.2.1` |
| Web | `fastapi==0.135.1`, `uvicorn==0.41.0`, `flask==3.1.3` |
| Banco | `sqlalchemy==2.0.48` |
| Segurança | `cryptography>=43.0.0`, `bcrypt==4.0.1` |
| Dev | `pytest==9.0.2`, `black==25.1.0`, `pylint==4.0.5` |

> **Nota:** `pydantic<2` é mantido intencionalmente no backend (`web/backend/requirements.txt`) por compatibilidade. A migração para pydantic v2 exigirá refatoração dos modelos.

## 🚨 Troubleshooting

### Backend não inicia
- Confirme que está usando o Python do `.venv`: `web\backend\.venv\Scripts\python.exe app.py`
- Verifique se a porta 5000 está disponível

### Login inválido
- Certifique-se de que o backend está rodando
- Para recriar o usuário admin: `python create_test_user.py` (dentro de `web\backend`)

### Erro ao conectar no OPC UA
- Verifique se o servidor OPC UA está ativo e acessível
- Use o servidor local para simulação: `python acquisition\server_opcua_local\server.py`

### Frontend não carrega dados
- Confirme que o backend está rodando em `localhost:5000`
- O proxy Vite (`/api → localhost:5000`) requer que o dev server esteja ativo

## 📚 Documentação Adicional

- [SYSTEM_FLOW.md](./docs/SYSTEM_FLOW.md) — Fluxo do sistema e diagramas de sequência
- [SYSTEM_IMPLEMENTATION.md](./docs/SYSTEM_IMPLEMENTATION.md) — Detalhes de implementação IEEE

## ✉️ Contato

Weidson Feitoza — weidsondeoliveira@gmail.com

Projeto: [https://github.com/weid12/aas-robo-scara](https://github.com/weid12/aas-robo-scara)
