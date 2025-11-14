import { useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import layout from "../ProductionHub/WorkInstructionControl.module.css";
import styles from "./Data.module.css";

import LineChart from "../../components/Charts/LineChart.jsx";
import DataCard from "../../components/DataCard/DataCard.jsx";
import DataTable from "../../components/DataTable/DataTable.jsx";
import RangeFilterInline from "../../components/DateRangePicker/RangeFilterInline.jsx";

export default function Data() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [stats, setStats] = useState(null);
  const [paths, setPaths] = useState([]); // [{submodel, path}]
  const [selected, setSelected] = useState(null); // {submodel, path}

  const [series, setSeries] = useState([]); // [{t, v}]
  const [latest, setLatest] = useState([]); // [{submodel, path, value, timestamp}]

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [range, setRange] = useState(undefined); // { from?: Date, to?: Date }

  // Bytes -> string legível (KB/MB/GB)
  const formatBytes = (bytes) => {
    if (bytes == null) return "N/D";
    const units = ["B", "KB", "MB", "GB", "TB"]; 
    let v = Number(bytes);
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
  };

  const fetchJSON = async (url) => {
    const res = await fetch(url, { credentials: "include" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.error || `Erro ${res.status}`);
    return data;
  };

  const loadStats = async () => setStats(await fetchJSON("/api/data/stats"));
  const loadPaths = async () => {
    const data = await fetchJSON("/api/data/paths");
    setPaths(data.paths || []);
    return data.paths || [];
  };
  const loadLatest = async () => {
    const data = await fetchJSON("/api/data/latest");
    setLatest(data.metrics || []);
  };
  const loadSeries = async (sel) => {
    if (!sel) return;
    const params = new URLSearchParams({
      submodel: sel.submodel,
      path: sel.path,
      limit: "300",
    });
    if (range?.from instanceof Date && !Number.isNaN(range.from.getTime())) {
      params.set("start", range.from.toISOString());
    }
    if (range?.to instanceof Date && !Number.isNaN(range.to.getTime())) {
      params.set("end", range.to.toISOString());
    }
    // no time filter
    const data = await fetchJSON(`/api/data/timeseries?${params.toString()}`);
    setSeries(data.rows || []);
  };

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [pathsLoaded] = await Promise.all([
          loadPaths(),
          loadStats(),
          loadLatest(),
        ]);
        if (!active) return;
        const first = pathsLoaded && pathsLoaded.length ? pathsLoaded[0] : null;
        if (first) {
          setSelected(first);
          await loadSeries(first);
        }
        setLoading(false);
      } catch (e) {
        setError(e.message || String(e));
        setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!autoRefresh || !selected) return;
    const id = setInterval(() => {
      loadSeries(selected).catch(() => {});
    }, 5000);
    return () => clearInterval(id);
  }, [autoRefresh, selected?.submodel, selected?.path, range?.from?.getTime?.(), range?.to?.getTime?.()]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => {
      loadLatest().catch(() => {});
    }, 3000);
    return () => clearInterval(id);
  }, [autoRefresh]);

  const seriesStats = useMemo(() => {
    if (!series || series.length === 0) return null;
    const values = series.map((d) => Number(d.v)).filter((v) => !Number.isNaN(v));
    if (!values.length) return null;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const cur = values[values.length - 1];
    return { min, max, avg, cur };
  }, [series]);

  const formatDbSize = (bytes) => {
    if (bytes == null) return "N/D";
    const nf2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const mb = Number(bytes) / (1024 * 1024);
    if (mb >= 1024) {
      const gb = mb / 1024;
      return `${nf2.format(gb)} GB`;
    }
    return `${nf2.format(mb)} MB`;
  };

  // Inteiros com separador de milhar em pt-BR (ex.: 108.617)
  const formatIntBr = (n) => {
    try {
      return new Intl.NumberFormat('pt-BR').format(Number(n || 0));
    } catch {
      return String(n ?? 0);
    }
  };
  const columns = useMemo(
    () => [
      { key: "submodel", label: "Submodelo" },
      { key: "path", label: "Caminho" },
      { key: "value", label: "Valor", render: (v) => { const n = Number(v); return Number.isFinite(n) ? new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 6 }).format(n) : v; } },
      {
        key: "timestamp",
        label: "Atualizado",
        render: (v) => {
          try {
            const d = new Date(v);
            return d.toLocaleString();
          } catch {
            return v;
          }
        },
      },
    ],
    []
  );

  if (loading) {
    return (
      <div className={layout.wrapper}>
        <Sidebar />
        <main className={layout.content}>
          <div className={styles.loading}>
            <div className={styles.spinner} />
            <p>Carregando dados...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className={layout.wrapper}>
        <Sidebar />
        <main className={layout.content}>
          <div className={styles.error}>
            <h2>Erro ao carregar dados</h2>
            <p>{error}</p>
            <p className={styles.errorHint}>
              Verifique se o backend esta rodando e se o banco SQLite existe em
              <code style={{ marginLeft: 6 }}>data/aas_history.sqlite3</code>.
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={layout.wrapper}>
      <Sidebar />

      <main className={layout.content}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <h1 className={styles.title}>Data</h1>
            <p className={styles.subtitle}>Visualizacao dos dados do robo SCARA</p>
          </div>
          <div className={styles.headerRight}>
            <label className={styles.refreshToggle}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <span>Auto-refresh</span>
            </label>
          </div>
        </header>

        {stats && (
          <section className={styles.statsGrid}>
            <DataCard
              title="Registros"
              value={formatIntBr(stats.total_records)}
              subtitle={
                stats.date_range
                  ? `Ultimo: ${new Date(stats.date_range.last).toLocaleString()}`
                  : "Sem dados"
              }
            />
            <DataCard
              title="Metricas"
              value={formatIntBr(stats.metrics_count)}
              subtitle={`Submodelos: ${stats.submodels?.length ?? 0}`}
            />
            <div title={`Path: ${stats.db_path || ''}\nBytes: ${stats.db_size_bytes == null ? 'N/D' : formatIntBr(stats.db_size_bytes)}`}>
              <DataCard
                title="Tamanho do banco"
                value={formatDbSize(stats.db_size_bytes)}
                subtitle={
                  stats.db_mtime
                    ? `Ultima atualizacao: ${new Date(stats.db_mtime).toLocaleString()}`
                    : "Ultima atualizacao: N/D"
                }
              />
            </div>
          </section>
        )}

        <section className={styles.chartSection}>
          <div className={styles.chartHeader}>
            <h2 className={styles.sectionTitle}>Serie temporal</h2>
            <div className={styles.pathSelector}>
              <label>Metrica:</label>
              <label htmlFor="metricSelect">Metrica:</label>
              <select
                id="metricSelect"
                className={styles.select}
                value={selected ? `${selected.submodel}|${selected.path}` : ""}
                onChange={(e) => {
                  const [submodel, ...rest] = e.target.value.split("|");
                  const path = rest.join("|");
                  const sel = { submodel, path };
                  setSelected(sel);
                  loadSeries(sel).catch(() => {});
                }}
              >
                {paths.map((p) => (
                  <option key={`${p.submodel}|${p.path}`} value={`${p.submodel}|${p.path}`}>
                    {p.path}
                  </option>
                ))}
              </select>
            <div className={styles.pathSelector}>
              <RangeFilterInline
                value={range}
                onChange={(r) => {
                  setRange(r);
                  if (selected) loadSeries(selected).catch(() => {});
                }}
              />
            </div>
            </div>

          </div>

          {seriesStats && (
            <div className={styles.chartStatsGrid}>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Atual</span>
                <span className={styles.miniValue}>{seriesStats.cur.toFixed(3)}</span>
              </div>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Minimo</span>
                <span className={styles.miniValue}>{seriesStats.min.toFixed(3)}</span>
              </div>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Maximo</span>
                <span className={styles.miniValue}>{seriesStats.max.toFixed(3)}</span>
              </div>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Media</span>
                <span className={styles.miniValue}>{seriesStats.avg.toFixed(3)}</span>
              </div>
            </div>
          )}

          <div className={styles.chartContainer}>
            <LineChart data={series} title={selected?.path || ""} />
          </div>
        </section>

        <section className={styles.tableSection}>
          <h2 className={styles.sectionTitle}>Valores recentes</h2>
          <DataTable columns={columns} data={latest} maxHeight="420px" />
        </section>
      </main>
    </div>
  );
}



