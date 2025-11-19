/**
 * Instruções rápidas:
 * 1. Popular o banco: python -m backend.seed_data
 * 2. Iniciar API: uvicorn backend.main:app --reload
 * 3. Iniciar frontend: cd aas_web_template/frontend && npm install && npm run dev
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/global.css";
import { AuthProvider } from "./login";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Elemento root não encontrado");
}

ReactDOM.createRoot(container).render(
  <BrowserRouter>
    <AuthProvider>
      <App />
    </AuthProvider>
  </BrowserRouter>
);
