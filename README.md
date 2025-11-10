# AAS Robô Scara - Sistema de Monitoramento

Sistema integrado para monitoramento de robô SCARA utilizando Asset Administration Shell (AAS) e OPC UA.

## 📋 Estrutura do Projeto

```
teste_aas_08_11/
├── opcua_client/           # Cliente OPC UA
├── dashboard/              # Interface Streamlit
├── aas_web_template/       # Template Web
└── data/                   # Dados SQLite
```

## 🛠️ Tecnologias

- Python 3.11+
- asyncua (Cliente OPC UA)
- Flask (Backend API)
- React + Vite (Frontend)
- SQLite (Persistência)

## ⚙️ Requisitos

- Python 3.11+
- Node.js 16+
- OPC UA Server
- Git

## 🚀 Instalação

### Cliente OPC UA
```powershell
cd opcua_client
python -m venv venv
.\venv\Scripts\activate
pip install asyncua python-dotenv
```

### Web Interface
```powershell
# Backend
cd aas_web_template/backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## ⚡ Executando

1. **Cliente OPC UA**
```powershell
cd opcua_client
.\venv\Scripts\activate
python client_asyncua.py
```

2. **Web Interface**
```powershell
# Terminal 1 - Backend
cd aas_web_template/backend
.\venv\Scripts\activate
python app.py

# Terminal 2 - Frontend
cd aas_web_template/frontend
npm run dev
```

## 🔒 Acesso

- Frontend: http://localhost:5173
- Backend API: http://localhost:5000

**Credenciais**
- Usuário: `admin`
- Senha: `admin`

## 📊 Funcionalidades

- Coleta de dados OPC UA em tempo real
- Dashboard web responsivo
- Histórico de métricas
- Gráficos de performance
- Interface administrativa

## 👥 Contribuição

1. Fork o projeto
2. Crie sua Feature Branch (`git checkout -b feature/Feature`)
3. Commit suas mudanças (`git commit -m 'Add some Feature'`)
4. Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença do Programa de Pós-graduação em Engenharia Elétrica (PPGEEL).

## ✉️ Contato

Weidson Feitoza - weidsondeoliveira@gmail.com

Projeto: [https://github.com/weid12/aas-robo-scara](https://github.com/weid12/aas-robo-scara)


