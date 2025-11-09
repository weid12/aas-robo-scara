import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import WorkInstructionControl from "./pages/ProductionHub/WorkInstructionControl.jsx";
import Register from "./pages/Register/Register.jsx";
import Data from "./pages/Data/Data.jsx";
import SequencialPlan from "./pages/SequencialPlan/SequencialPlan.jsx";
import Splash from "./components/Splash/Splash.jsx";
import { LoginPage, ProtectedRoute } from "./login";

export default function App() {
  const [bootDone, setBootDone] = useState(false);

  return (
    <>
      {!bootDone && <Splash onFinish={() => setBootDone(true)} />}

      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/hub"
          element={
            <ProtectedRoute>
              <WorkInstructionControl />
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
          path="/sequencial-plan"
          element={
            <ProtectedRoute>
              <SequencialPlan />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </>
  );
}
