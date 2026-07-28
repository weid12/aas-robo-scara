import { useEffect, useMemo, useState, useRef } from "react";
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

function formatDateRange(from, to) {
  if (!from && !to) return "Select period";
  const formatDate = (d) => {
    if (!d) return "";
    const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
    return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
  };
  if (from && to) {
    return `${formatDate(from)} - ${formatDate(to)}`;
  }
  return from ? formatDate(from) : formatDate(to);
}

export default function RangeFilterInline({ value, onChange, className }) {
  const [isOpen, setIsOpen] = useState(false);
  const [fromStr, setFromStr] = useState(toDateInputValue(value?.from));
  const [toStr, setToStr] = useState(toDateInputValue(value?.to));
  const [alignRight, setAlignRight] = useState(false);
  const dropdownRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    setFromStr(toDateInputValue(value?.from));
    setToStr(toDateInputValue(value?.to));
  }, [value?.from, value?.to]);

  // Calcular posição do dropdown para evitar overflow
  useEffect(() => {
    if (isOpen && triggerRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const dropdownWidth = 350; // Largura estimada do dropdown
      const viewportWidth = window.innerWidth;

      // Se não houver espaço à esquerda, alinhar à direita
      const spaceOnLeft = triggerRect.left;
      const spaceOnRight = viewportWidth - triggerRect.right;

      if (spaceOnLeft < dropdownWidth && spaceOnRight > spaceOnLeft) {
        setAlignRight(false);
      } else if (triggerRect.right + dropdownWidth > viewportWidth) {
        setAlignRight(true);
      } else {
        setAlignRight(false);
      }
    }
  }, [isOpen]);

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const canApply = useMemo(() => !!fromStr && !!toStr, [fromStr, toStr]);
  const canClear = useMemo(() => !!fromStr || !!toStr, [fromStr, toStr]);

  const apply = () => {
    const next = { from: fromDateInputValue(fromStr), to: fromDateInputValue(toStr) };
    onChange && onChange(next);
    setIsOpen(false);
  };

  const clear = () => {
    setFromStr("");
    setToStr("");
    onChange && onChange(undefined);
    setIsOpen(false);
  };

  return (
    <div className={`${styles.wrapper} ${className || ""}`.trim()} ref={dropdownRef}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        onClick={() => setIsOpen(!isOpen)}
      >
        <svg className={styles.icon} viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth="2" />
          <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2" />
          <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2" />
          <line x1="3" y1="10" x2="21" y2="10" strokeWidth="2" />
        </svg>
        <span className={styles.triggerText}>
          {formatDateRange(value?.from, value?.to)}
        </span>
        <svg className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <polyline points="6 9 12 15 18 9" strokeWidth="2" />
        </svg>
      </button>

      {isOpen && (
        <div className={`${styles.dropdown} ${alignRight ? styles.dropdownRight : ""}`}>
          <div className={styles.dateInputs}>
            <div className={styles.inputGroup}>
              <label className={styles.label}>De:</label>
              <input
                type="date"
                className={styles.input}
                value={fromStr}
                onChange={(e) => setFromStr(e.target.value)}
              />
            </div>
            <div className={styles.inputGroup}>
              <label className={styles.label}>Até:</label>
              <input
                type="date"
                className={styles.input}
                value={toStr}
                onChange={(e) => setToStr(e.target.value)}
              />
            </div>
          </div>
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.btn}
              onClick={clear}
              disabled={!canClear}
            >
              Limpar
            </button>
            <button
              type="button"
              className={`${styles.btn} ${styles.btnPrimary}`}
              onClick={apply}
              disabled={!canApply}
            >
              Aplicar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
