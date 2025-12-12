# AAS Robô Scara - Sistema de Monitoramento

Sistema integrado para monitoramento de robô SCARA utilizando Asset Administration Shell (AAS) e OPC UA.

## 📋 Estrutura do Projeto

```
aas-robo-scara/
├── opcua_client/           # Cliente OPC UA para coleta de dados
├── aas_web/                # Aplicação Web (Backend + Frontend)
│   ├── backend/            # Flask + FastAPI
│   └── frontend/           # React + Vite + TypeScript
├── aas-submodels/          # Arquivos JSON no padrão AAS
├── database/               # Scripts de persistência SQLite
├── data/                   # Banco de dados SQLite
└── server_opcua_local/     # Servidor OPC UA local (opcional)
```

## 🛠️ Tecnologias

### Backend
- Python 3.11+
- asyncua (Cliente OPC UA)
- Flask (Autenticação e integração HR)
- FastAPI (API de dados do robô)
- SQLAlchemy (ORM)
- SQLite (Persistência)

### Frontend
- React 18
- TypeScript
- Vite (Build tool)
- Recharts (Gráficos)
- Material-UI (Componentes)

## ⚙️ Requisitos

- Python 3.11+
- Node.js 16+
- Servidor OPC UA (opcional - para coleta de dados reais)
- Git

## 🚀 Instalação

### Cliente OPC UA
```powershell
cd aas-robo-scara/opcua_client
python -m venv venv
.\\venv\\Scripts\\activate
pip install asyncua python-dotenv
```

### Web Interface
```powershell
# Backend (Flask + FastAPI)
cd aas-robo-scara/aas_web/backend
python -m venv .venv
.\\.venv\\Scripts\\activate
pip install -r requirements.txt

# Frontend (React + Vite + TypeScript)
cd ../frontend
npm install
```

## ⚡ Executando

### 1. Cliente OPC UA (Coleta de dados em tempo real)
```powershell
cd aas-robo-scara/opcua_client
.\\venv\\Scripts\\activate
python client_asyncua.py
```
> **Nota:** O cliente OPC UA requer um servidor OPC UA ativo no robô SCARA. Se estiver testando sem o robô, você pode pular esta etapa e usar dados simulados.

### 2. Web Interface

#### Terminal 1 - Backend API
```powershell
cd aas-robo-scara/aas_web/backend
.\\.venv\\Scripts\\activate
python app.py
```
O backend estará disponível em: **http://localhost:5000**

#### Terminal 2 - Frontend Web
```powershell
cd aas-robo-scara/aas_web/frontend
npm run dev
```
O frontend estará disponível em: **http://localhost:5173**

## 📝 Acesso

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:5000
- **API Docs (FastAPI):** http://localhost:5000/docs

### Credenciais Padrão
- Usuário: `admin`
- Senha: `admin123`

> **Nota:** As credenciais são autenticadas via API externa configurada no backend. Certifique-se de que a variável `AUTH_API_BASE` está corretamente configurada no arquivo `.env` do backend.

## 🔧 Configuração

### Backend - Variáveis de Ambiente
Crie um arquivo `.env` em `aas_web/backend/`:
```bash
PORT=5000
AUTH_API_BASE=http://seu-servidor-autenticacao:8080
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
```

### Cliente OPC UA - Configuração
Edite `opcua_client/config_opcua.json` para configurar:
- Endereço do servidor OPC UA
- Mapeamento de variáveis
- Intervalo de coleta

## 📊 Funcionalidades

### Dashboard Web
- Monitoramento em tempo real do robô SCARA
- Visualização de estado operacional (Running/Idle/Alarm)
- Métricas OEE (Overall Equipment Effectiveness)
- Gráficos de performance (Availability, Performance, Quality)
- Visualização de juntas do robô
- Histórico de eventos

### Análise de Dados
- Consulta de dados históricos com filtros de período
- Exportação de dados em CSV/Excel
- Visualização de séries temporais
- Formatação de números no padrão brasileiro

### Integração AAS
- Exportação de dados no padrão Asset Administration Shell
- Geração de arquivos AASX compatíveis
- Estrutura de submodelos conforme especificação AAS

## 📁 Estrutura de Dados

### Banco de Dados SQLite
- `robot_state`: Estados completos do robô
- `submodel_snapshots`: Snapshots normalizados por elemento
- `timeseries`: Séries temporais de valores numéricos

### Arquivos AAS
- `Submodel_Identification.json`: Identificação do ativo
- `Submodel_TechnicalData.json`: Dados técnicos
- `Submodel_OperationalData.json`: Dados operacionais
- `Submodel_Performance.json`: Métricas de performance

## 🚨 Troubleshooting

### Erro ao conectar no OPC UA
- Verifique se o servidor OPC UA está ativo
- Confirme o endereço em `config_opcua.json`
- Teste com o servidor local: `python server_opcua_local/server.py`

### Backend não inicia
- Verifique se a porta 5000 está disponível
- Confirme que todas as dependências foram instaladas
- Verifique logs em `logs/` (se configurado)

### Frontend não carrega dados
- Confirme que o backend está rodando
- Verifique CORS no backend
- Inspecione Network tab no DevTools do navegador

## �👥 Contribuição

1. Fork o projeto
2. Crie sua Feature Branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a Branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença do Programa de Pós-graduação em Engenharia Elétrica (PPGEEL).

## ✉️ Contato

Weidson Feitoza - weidsondeoliveira@gmail.com

Projeto: [https://github.com/weid12/aas-robo-scara](https://github.com/weid12/aas-robo-scara)

## 📚 Documentação Adicional

- [SYSTEM_FLOW.md](./SYSTEM_FLOW.md) - Documentação completa do fluxo do sistema e arquitetura
