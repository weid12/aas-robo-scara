import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaUser, FaLock, FaSignInAlt } from "react-icons/fa";

import { adAuthenticate } from "./api.js";
import { useAuth } from "./useAuth";
import styles from "./LoginPage.module.css";
import aasLogo from "../assets/AAS.png";

export default function LoginPage() {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { isAuthenticated, login } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/hub", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorMessage("");
    setLoading(true);

    // Verificação simplificada com credenciais fixas
    if (userId === "admin" && password === "admin") {
      login("admin");
      navigate("/hub", { replace: true });
    } else {
      setErrorMessage("Credenciais inválidas. Use admin/admin");
    }
    setLoading(false);
  }

  return (
    <div className={styles.root}>
      <div className={styles.card}>
        <div className={styles.logoContainer}>
          <img src={aasLogo} alt="AAS Logo" className={styles.logo} />
        </div>
        <div className={styles.brand}>
          <span>AAS Robô Scara</span>
        </div>

        <h1 className={styles.title}>Entrar</h1>
        <p className={styles.subtitle}>
          Use <b>admin</b> como usuário e senha.
        </p>

        <form className={styles.form} onSubmit={handleSubmit}>
          <label className={styles.label}>
            <FaUser className={styles.icon} />
            <input
              className={styles.input}
              type="text"
              placeholder="Digite admin"
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
              required
              disabled={loading}
            />
          </label>

          <label className={styles.label}>
            <FaLock className={styles.icon} />
            <input
              className={styles.input}
              type="password"
              placeholder="Digite admin"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              disabled={loading}
            />
          </label>

          {errorMessage ? <div className={styles.error}>{errorMessage}</div> : null}

          <button className={styles.submit} disabled={loading}>
            <FaSignInAlt />
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <div className={styles.footerNote}>
          <small>Mestrando Weidson Feitoza</small>
        </div>
      </div>
    </div>
  );
}
