/**
 * ------------------------------------------------------------------------------------------------------------------
 * Componente raiz da aplicação React.
 * Gerencia o roteamento principal (React Router), tela de splash e proteção de rotas.
 * ------------------------------------------------------------------------------------------------------------------
 */

/**
 * Instruções rápidas:
 * 1. Popular o banco: python -m backend.seed_data
 * 2. Iniciar API: uvicorn backend.main:app --reload
 * 3. Iniciar frontend: cd aas_web_template/frontend && npm install && npm run dev
 */

import { type FC, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import AAS_ScaraMonitoringHub from "./pages/ProductionHub/AAS_ScaraMonitoringHub";
import Register from "./pages/Register/Register";
import Data from "./pages/Data/Data.jsx";
import EmergencyStopButtonDemo from "./components/EmergencyStopButton/EmergencyStopButtonDemo";

import Splash from "./components/Splash/Splash.jsx";
import { LoginPage, ProtectedRoute } from "./login";
import LandingPage from "./pages/LandingPage/LandingPage";

const App: FC = () => {
  const [bootDone, setBootDone] = useState(false);

  return (
    <>
      {!bootDone && <Splash onFinish={() => setBootDone(true)} />}

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/hub"
          element={
            <ProtectedRoute>
              <AAS_ScaraMonitoringHub />
            </ProtectedRoute>
          }
        />
        <Route
          path="/register"
          element={
            <ProtectedRoute>
              <Register />
            </ProtectedRoute>
          }
        />
        <Route
          path="/data"
          element={
            <ProtectedRoute>
              <Data />
            </ProtectedRoute>
          }
        />
        <Route
          path="/emergency-stop-demo"
          element={<EmergencyStopButtonDemo />}
        />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </>
  );
};

export default App;
