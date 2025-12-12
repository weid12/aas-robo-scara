import styles from "./DataCard.module.css";

/**
 * Card para exibir métricas e estatísticas
 */
export default function DataCard({ title, value, unit, subtitle, icon, trend, color }) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        {icon && <div className={styles.icon} style={{ color }}>{icon}</div>}
        <div className={styles.titleGroup}>
          <h3 className={styles.title}>{title}</h3>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
      </div>

      <div className={styles.body}>
        <div className={styles.valueGroup}>
          <span className={styles.value} style={{ color }}>
            {value}
          </span>
          {unit && <span className={styles.unit}>{unit}</span>}
        </div>

        {trend !== undefined && (
          <div className={`${styles.trend} ${trend >= 0 ? styles.trendUp : styles.trendDown}`}>
            <span className={styles.trendIcon}>{trend >= 0 ? "↑" : "↓"}</span>
            <span className={styles.trendValue}>{Math.abs(trend).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}

// PropTypes removed to avoid external dependency
