import { useEffect, useState } from "react";
import aasLogo from "../../assets/aas-logo.png";
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
      <div className={styles.logoWrapper}>
        <img src={aasLogo} alt="AAS SCARA" className={styles.logo} />
      </div>
    </div>
  );
}
