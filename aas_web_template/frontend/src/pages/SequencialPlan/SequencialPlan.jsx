import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import layout from "../ProductionHub/WorkInstructionControl.module.css";

export default function SequencialPlan() {
  return (
    <div className={layout.wrapper}>
      <Sidebar />

      <main className={layout.content}>
        <header className={layout.header}>
          <h1>Sequencial Plan</h1>
          <span className={layout.statusNote}>Em desenvolvimento</span>
        </header>

        <section className={layout.placeholder}>
          <div className={layout.card}>
            <h2>Status</h2>
            <p>O planejamento sequencial esta em desenvolvimento.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
