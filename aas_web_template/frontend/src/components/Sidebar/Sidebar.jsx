import { useState, useEffect } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { FaSearch, FaHome, FaClipboardList, FaChartBar, FaProjectDiagram, FaSignOutAlt } from "react-icons/fa";

import styles from "./Sidebar.module.css";
import { useAuth } from "../../login";

const MENU = [
  { key: "hub", label: "Hub", icon: <FaHome />, to: "/hub" },
  { key: "register", label: "Register", icon: <FaClipboardList />, to: "/register" },
  { key: "data", label: "Data", icon: <FaChartBar />, to: "/data" },
  { key: "sequencial-plan", label: "Sequencial Plan", icon: <FaProjectDiagram />, to: "/sequencial-plan" },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { userId, logout } = useAuth();

  const [open, setOpen] = useState(() => (typeof window !== "undefined" ? window.innerWidth >= 980 : true));

  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 980) {
      setOpen(false);
    }
  }, [location.pathname]);

  const trimmedUserId = (userId || "").trim();
  const userInitial = trimmedUserId ? trimmedUserId.charAt(0).toUpperCase() : "?";
  const userLabel = trimmedUserId || "Usuario";

  const toggleOpen = () => setOpen((value) => !value);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className={`${styles.container} ${open ? "" : styles.containerCollapsed}`}>
      <aside className={`${styles.root} ${open ? "" : styles.closed}`} role="navigation">
        <div className={styles.top}>
          <div className={styles.brand}>
            <span className={styles.brandMark}>AAS</span>
            <span className={styles.brandText}>Robô Scara</span>
          </div>
        </div>

        <div className={styles.searchBox}>
          <FaSearch className={styles.searchIcon} />
          <input className={styles.searchInput} placeholder="Buscar" aria-label="Buscar" />
        </div>

        <div className={styles.divider} />

        <div className={styles.mainContent}>
          <div className={styles.sectionTitle}>Navegacao</div>

          <nav className={styles.nav}>
            {MENU.map((item) => (
              <NavLink
                key={item.key}
                to={item.to}
                aria-label={item.label}
                className={({ isActive }) =>
                  `${styles.item} ${styles.tip} ${isActive ? styles.active : ""}`
                }
                title={open ? "" : item.label}
                end
              >
                <span className={styles.icon}>{item.icon}</span>
                <span className={styles.label}>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        <div className={styles.bottom}>
          <div className={styles.divider} />

          <div className={styles.userSection}>
            <div className={styles.userRow}>
              <div
                className={`${styles.userIcon} ${styles.tip}`}
                aria-label={userLabel}
                title={open ? "" : userLabel}
              >
                <span aria-hidden="true">{userInitial}</span>
              </div>

              <div className={styles.userActions}>
                <span className={styles.userName}>{userLabel}</span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className={`${styles.actText} ${styles.logoutButton}`}
                  aria-label="Encerrar sessao"
                >
                  <FaSignOutAlt />
                  <span>Sair</span>
                </button>
              </div>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className={`${styles.logoutButtonCollapsed} ${styles.tip}`}
              aria-label="Encerrar sessao"
              title={open ? "" : "Sair"}
            >
              <FaSignOutAlt />
            </button>
          </div>
        </div>
      </aside>

      <button
        type="button"
        className={styles.toggleCircleTop}
        aria-label={open ? "Recolher menu" : "Expandir menu"}
        title={open ? "Recolher" : "Expandir"}
        onClick={toggleOpen}
        aria-expanded={open}
      >
        <span className={`${styles.arrow} ${open ? styles.arrowOpen : ""}`}>
          <svg
            stroke="currentColor"
            fill="currentColor"
            strokeWidth="0"
            viewBox="0 0 320 512"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M285.476 272.971L91.132 467.314c-9.373 9.373-24.569 9.373-33.941 0l-22.667-22.667c-9.357-9.357-9.375-24.522-.04-33.901L188.505 256 34.484 101.255c-9.335-9.379-9.317-24.544.04-33.901l22.667-22.667c9.373-9.373 24.569-9.373 33.941 0L285.475 239.03c9.373 9.372 9.373 24.568.001 33.941z" />
          </svg>
        </span>
      </button>
    </div>
  );
}
