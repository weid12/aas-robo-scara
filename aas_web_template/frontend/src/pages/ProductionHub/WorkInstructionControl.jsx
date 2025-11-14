import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import styles from "./WorkInstructionControl.module.css";

export default function WorkInstructionControl() {
  return (
    <div className={styles.wrapper}>
      <Sidebar />

      <main className={styles.content}>
        <header className={styles.header}>
          <h1 className={styles.brandLabel}>
            <span className={styles.brandSigla}>AAS</span>
            <span className={styles.brandName}>Asset Administration Shell Robô Scara</span>
          </h1>

          <span className={styles.statusNote}>Em desenvolvimento</span>
        </header>

        <section className={styles.placeholder}>
          <div className={styles.card}>
            <h2>Status</h2>
            <p>Modulo em desenvolvimento. Em breve exibira os indicadores principais do hub.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
