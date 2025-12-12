import { useState } from "react";
import styles from "./DataTable.module.css";

/**
 * Componente de tabela para exibir dados tabulares
 */
export default function DataTable({ columns, data, maxHeight }) {
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState("asc");

  const handleSort = (columnKey) => {
    if (sortColumn === columnKey) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(columnKey);
      setSortDirection("asc");
    }
  };

  const sortedData = [...data].sort((a, b) => {
    if (!sortColumn) return 0;

    const aVal = a[sortColumn];
    const bVal = b[sortColumn];

    if (aVal === bVal) return 0;

    const comparison = aVal < bVal ? -1 : 1;
    return sortDirection === "asc" ? comparison : -comparison;
  });

  if (!data || data.length === 0) {
    return (
      <div className={styles.empty}>
        <p>Nenhum dado disponível</p>
      </div>
    );
  }

  return (
    <div className={styles.container} style={{ maxHeight }}>
      <table className={styles.table}>
        <thead className={styles.thead}>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={styles.th}
                onClick={() => col.sortable !== false && handleSort(col.key)}
                style={{ cursor: col.sortable !== false ? "pointer" : "default" }}
              >
                <div className={styles.thContent}>
                  <span>{col.label}</span>
                  {sortColumn === col.key && (
                    <span className={styles.sortIcon}>
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={styles.tbody}>
          {sortedData.map((row, index) => (
            <tr key={index} className={styles.tr}>
              {columns.map((col) => (
                <td key={col.key} className={styles.td}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

DataTable.defaultProps = {
  maxHeight: "500px",
};
