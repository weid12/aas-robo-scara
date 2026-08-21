import { useEffect, useMemo, useState } from "react";
import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import layout from "../ProductionHub/AAS_ScaraMonitoringHub.module.css";
import styles from "./Data.module.css";

import LineChart from "../../components/Charts/LineChart.jsx";
import DataCard from "../../components/DataCard/DataCard.jsx";
import DataTable from "../../components/DataTable/DataTable.jsx";
import DateRangeCalendar from "../../components/DateRangePicker/DateRangeCalendar";
import SearchableSelect from "../../components/ui/SearchableSelect";

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

  // Bytes -> human-readable string (KB/MB/GB)
  const formatBytes = (bytes) => {
    if (bytes == null) return "N/A";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let v = Number(bytes);
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${new Intl.NumberFormat('en-US', { minimumFractionDigits: i === 0 ? 0 : 2, maximumFractionDigits: i === 0 ? 0 : 2 }).format(v)} ${units[i]}`;
  };

  // Format number in English locale (comma=thousands, dot=decimal)
  const formatBrNumber = (num, decimals = 2) => {
    if (num == null || isNaN(num)) return "N/A";
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(Number(num));
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
      loadSeries(selected).catch(() => { });
    }, 5000);
    return () => clearInterval(id);
  }, [autoRefresh, selected?.submodel, selected?.path, range?.from?.getTime?.(), range?.to?.getTime?.()]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => {
      loadLatest().catch(() => { });
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
    if (bytes == null) return "N/A";
    const nf2 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
      return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(Number(n || 0));
    } catch {
      return String(n ?? 0);
    }
  };
  const columns = useMemo(
    () => [
      { key: "submodel", label: "Submodel" },
      { key: "path", label: "Path" },
      { key: "value", label: "Value", render: (v) => { const n = Number(v); return Number.isFinite(n) ? formatBrNumber(n, 2) : v; } },
      {
        key: "timestamp",
        label: "Updated",
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
            <p>Loading data...</p>
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
            <h2>Error loading data</h2>
            <p>{error}</p>
            <p className={styles.errorHint}>
              Check if the backend is running and the SQLite database exists at
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
            <p className={styles.subtitle}>SCARA robot data visualization</p>
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
              title="Records"
              value={formatIntBr(stats.total_records)}
              subtitle={
                stats.date_range
                  ? `Last: ${new Date(stats.date_range.last).toLocaleString()}`
                  : "No data"
              }
            />
            <DataCard
              title="Metrics"
              value={formatIntBr(stats.metrics_count)}
              subtitle={`Submodelos: ${stats.submodels?.length ?? 0}`}
            />
            <div title={`Path: ${stats.db_path || ''}\nBytes: ${stats.db_size_bytes == null ? 'N/D' : formatIntBr(stats.db_size_bytes)}`}>
              <DataCard
                title="Database Size"
                value={formatDbSize(stats.db_size_bytes)}
                subtitle={
                  stats.db_mtime
                    ? `Last update: ${new Date(stats.db_mtime).toLocaleString()}`
                    : "Last update: N/A"
                }
              />
            </div>
          </section>
        )}

        <section className={styles.chartSection}>
          <div className={styles.chartHeader}>
            <h2 className={styles.sectionTitle}>Time series</h2>
          </div>

          <div className={styles.pathSelector}>
            <label>Metric:</label>
            <SearchableSelect
              options={paths.map((p) => ({
                value: `${p.submodel}|${p.path}`,
                label: p.path
              }))}
              value={selected ? `${selected.submodel}|${selected.path}` : ""}
              onChange={(value) => {
                const [submodel, ...rest] = value.split("|");
                const path = rest.join("|");
                const sel = { submodel, path };
                setSelected(sel);
                loadSeries(sel).catch(() => { });
              }}
              placeholder="Select a metric"
              className={styles.metricSelect}
            />
            <DateRangeCalendar
              value={range}
              onChange={(r) => {
                setRange(r);
                if (selected) loadSeries(selected).catch(() => { });
              }}
            />
          </div>

          {seriesStats && (
            <div className={styles.chartStatsGrid}>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Current</span>
                <span className={styles.miniValue}>{formatBrNumber(seriesStats.cur, 2)}</span>
              </div>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Min</span>
                <span className={styles.miniValue}>{formatBrNumber(seriesStats.min, 2)}</span>
              </div>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Max</span>
                <span className={styles.miniValue}>{formatBrNumber(seriesStats.max, 2)}</span>
              </div>
              <div className={styles.miniCard}>
                <span className={styles.miniLabel}>Avg</span>
                <span className={styles.miniValue}>{formatBrNumber(seriesStats.avg, 2)}</span>
              </div>
            </div>
          )}

          <div className={styles.chartContainer}>
            <LineChart data={series} title={selected?.path || ""} />
          </div>
        </section>

        <section className={styles.tableSection}>
          <h2 className={styles.sectionTitle}>Recent values</h2>
          <DataTable columns={columns} data={latest} maxHeight="420px" />
        </section>
      </main>
    </div>
  );
}



