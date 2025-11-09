import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import layout from "../ProductionHub/WorkInstructionControl.module.css";

export default function Register() {
  return (
    <div className={layout.wrapper}>
      <Sidebar />

      <main className={layout.content}>
        <header className={layout.header}>
          <h1>Register</h1>
          <span className={layout.statusNote}>Em desenvolvimento</span>
        </header>

        <section className={layout.placeholder}>
          <div className={layout.card}>
            <h2>Status</h2>
            <p>O modulo de registro esta em desenvolvimento.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
