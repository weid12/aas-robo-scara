---
description: Run the full stack web application
---

This workflow describes how to run the backend and frontend of the application.

## Prerequisites

- Python 3.10+ installed
- Node.js 18+ installed

## 1. Setup and Run Backend

The backend is a Python application that serves the API.

1.  Open a terminal.
2.  Navigate to the backend directory:
    ```powershell
    cd aas_web/backend
    ```
3.  (Optional) Create and activate a virtual environment:
    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```
4.  Install dependencies:
    ```powershell
    pip install -r requirements.txt
    ```
5.  Run the server:
    ```powershell
    python app.py
    ```
    The backend will start on **http://localhost:5000**.

## 2. Setup and Run Frontend

The frontend is a React application.

1.  Open a **new** terminal.
2.  Navigate to the frontend directory:
    ```powershell
    cd aas_web/frontend
    ```
3.  Install dependencies:
    ```powershell
    npm install
    ```
4.  Run the development server:
    ```powershell
    npm run dev
    ```
    The frontend will start on **http://localhost:5173**.

## 3. (Optional) Live Data Simulation

If you want to simulate live data flow (Digital Twin):

1.  **Mock Server**: Runs a local OPC UA server.
    ```powershell
    # Terminal 3
    cd server_opcua_local
    python server.py
    ```
    Runs on `opc.tcp://0.0.0.0:4881`.

2.  **Data Client**: Reads from OPC UA and saves to database.
    ```powershell
    # Terminal 4
    cd opcua_client
    $env:OPCUA_SERVER_URL="opc.tcp://localhost:4881"
    python client_asyncua.py
    ```
