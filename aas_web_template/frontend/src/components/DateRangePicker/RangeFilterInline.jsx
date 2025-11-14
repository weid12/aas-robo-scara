import { useEffect, useMemo, useState } from "react";
import styles from "./RangeFilterInline.module.css";

function toDateInputValue(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function fromDateInputValue(v) {
  if (!v) return undefined;
  const d = new Date(`${v}T00:00`);
  return Number.isNaN(d.getTime()) ? undefined : d;
}

export default function RangeFilterInline({ value, onChange, className }) {
  const [fromStr, setFromStr] = useState(toDateInputValue(value?.from));
  const [toStr, setToStr] = useState(toDateInputValue(value?.to));

  useEffect(() => {
    setFromStr(toDateInputValue(value?.from));
    setToStr(toDateInputValue(value?.to));
  }, [value?.from, value?.to]);

  const canApply = useMemo(() => !!fromStr && !!toStr, [fromStr, toStr]);
  const canClear = useMemo(() => !!fromStr || !!toStr, [fromStr, toStr]);

  const apply = () => {
    const next = { from: fromDateInputValue(fromStr), to: fromDateInputValue(toStr) };
    onChange && onChange(next);
  };

  const clear = () => {
    setFromStr("");
    setToStr("");
    onChange && onChange(undefined);
  };

  return (
    <div className={`${styles.wrapper} ${className || ""}`.trim()}>
      <span className={styles.label}>Período:</span>
      <input type="date" className={styles.input} value={fromStr} onChange={(e) => setFromStr(e.target.value)} />
      <span className={styles.sep}>—</span>
      <input type="date" className={styles.input} value={toStr} onChange={(e) => setToStr(e.target.value)} />
      <span className={styles.actions}>
        <button type="button" className={styles.btn} onClick={clear} disabled={!canClear}>
          Limpar
        </button>
        <button type="button" className={`${styles.btn} ${styles.btnPrimary}`} onClick={apply} disabled={!canApply}>
          Aplicar
        </button>
      </span>
    </div>
  );
}

