import { useEffect, useState } from "react";
import styles from "./Splash.module.css";

const DISPLAY_MS = 1200;
const FADE_MS = 320;

export default function Splash({ onFinish }) {
  const [phase, setPhase] = useState("enter");

  useEffect(() => {
    const enterTimer = setTimeout(() => setPhase("exit"), DISPLAY_MS);
    return () => clearTimeout(enterTimer);
  }, []);

  useEffect(() => {
    if (phase !== "exit") {
      return undefined;
    }

    const exitTimer = setTimeout(() => {
      setPhase("done");
      if (typeof onFinish === "function") {
        onFinish();
      }
    }, FADE_MS);

    return () => clearTimeout(exitTimer);
  }, [phase, onFinish]);

  if (phase === "done") {
    return null;
  }

  return (
    <div
      className={`${styles.overlay} ${phase === "exit" ? styles.fadeOut : ""}`}
      role="presentation"
    >
      <div className={styles.card}>
        <div className={styles.logo}>
          <span className={styles.dot} />
          <span className={styles.brand}>Work_Instruction_Control</span>
        </div>
        <div className={styles.caption}>carregando WIC</div>
        <div className={styles.spinner} aria-hidden />
      </div>
    </div>
  );
}
