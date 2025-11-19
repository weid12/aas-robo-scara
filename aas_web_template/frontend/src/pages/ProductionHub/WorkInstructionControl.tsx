import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  CircularProgress,
  CssBaseline,
  Grid,
  Stack,
  ThemeProvider,
  Typography,
  createTheme,
} from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import AddAlarmIcon from "@mui/icons-material/AddAlarm";
import AllInclusiveIcon from "@mui/icons-material/AllInclusive";
import BoltIcon from "@mui/icons-material/Bolt";

import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import styles from "./WorkInstructionControl.module.css";
import { getHistory, getLatestState, getSummaryMetrics } from "../../services/api";
import type { RobotState, RobotSummary } from "../../types/robot";
import { StatusCard } from "../../components/dashboard/StatusCard";
import { MetricCard } from "../../components/dashboard/MetricCard";
import { RobotCellCard } from "../../components/dashboard/RobotCellCard";
import { GaugeCard } from "../../components/dashboard/GaugeCard";
import { HistoryChart } from "../../components/dashboard/HistoryChart";
import { EventsTable } from "../../components/dashboard/EventsTable";
import { SummaryCard } from "../../components/dashboard/SummaryCard";

const REFRESH_MS = 5000;

const dashboardTheme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0f111a",
      paper: "rgba(20,21,35,0.95)",
    },
    text: {
      primary: "#f4f4f8",
      secondary: "#a0a7c7",
    },
  },
  typography: {
    fontFamily: '"Barlow", "Roboto", "Segoe UI", sans-serif',
  },
});

const formatDuration = (value: number) => {
  const totalSeconds = Math.max(0, Math.floor(value));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
};

export default function WorkInstructionControl() {
  const [latest, setLatest] = useState<RobotState | null>(null);
  const [history, setHistory] = useState<RobotState[]>([]);
  const [summary, setSummary] = useState<RobotSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [latestState, historyState, summaryMetrics] = await Promise.all([
        getLatestState(),
        getHistory(64),
        getSummaryMetrics(),
      ]);
      setLatest(latestState);
      setHistory(historyState);
      setSummary(summaryMetrics);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao atualizar painel";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, REFRESH_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  const metrics = useMemo(() => {
    return [
      {
        label: "Tempo em operação",
        value: formatDuration(summary?.operation_time_s ?? 0),
        helper: "Janela do dia",
        icon: <AccessTimeIcon sx={{ color: "#64ffda" }} />,
      },
      {
        label: "Tempo em parada",
        value: formatDuration(summary?.downtime_s ?? 0),
        helper: "Alarmes + Idle",
        icon: <AddAlarmIcon sx={{ color: "#ffa726" }} />,
      },
      {
        label: "Ciclos",
        value: summary ? summary.cycles.toString() : "0",
        helper: "Eventos registrados",
        icon: <AllInclusiveIcon sx={{ color: "#82b1ff" }} />,
      },
      {
        label: "Energia no dia",
        value: `${(summary?.energy_kwh ?? latest?.energy_kwh ?? 0).toFixed(2)} kWh`,
        helper: "Evita amostras manuais",
        icon: <BoltIcon sx={{ color: "#ffeb3b" }} />,
      },
    ];
  }, [summary, latest]);

  const gaugeMetrics = useMemo(() => {
    const fallback = latest?.oee ?? 0;
    return [
      { label: "OEE", value: summary?.oee_avg ?? latest?.oee ?? fallback },
      {
        label: "Disponibilidade",
        value: summary?.availability_avg ?? latest?.availability ?? fallback,
      },
      {
        label: "Desempenho",
        value: summary?.performance_avg ?? latest?.performance ?? fallback,
      },
      {
        label: "Qualidade",
        value: summary?.quality_avg ?? latest?.quality ?? fallback,
      },
    ];
  }, [summary, latest]);

  return (
    <div className={styles.wrapper}>
      <Sidebar />

      <ThemeProvider theme={dashboardTheme}>
        <CssBaseline />
        <main className={styles.content}>
          <header className={styles.header}>
            <h1 className={styles.brandLabel}>
              <span className={styles.brandSigla}>AAS</span>
              <span className={styles.brandName}>SCARA Operations Hub</span>
            </h1>
            <span className={styles.statusNote}>Telemetria em tempo real · 5s refresh</span>
          </header>

          {error && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {loading ? (
            <Box sx={{ display: "grid", placeItems: "center", minHeight: "40vh" }}>
              <CircularProgress />
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                Carregando dados do robô SCARA...
              </Typography>
            </Box>
          ) : (
            <div className={styles.dashboard}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={3}>
                  <Stack spacing={2} className={styles.columns}>
                    <StatusCard
                      status={latest?.status}
                      mode={latest?.mode}
                      timestamp={latest?.timestamp}
                    />
                    {metrics.map((metric) => (
                      <MetricCard key={metric.label} {...metric} />
                    ))}
                  </Stack>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Stack spacing={2}>
                    <RobotCellCard latest={latest} />
                    <Grid container spacing={2}>
                      {gaugeMetrics.map((gauge) => (
                        <Grid key={gauge.label} item xs={12} sm={6} md={3}>
                          <GaugeCard label={gauge.label} value={gauge.value ?? 0} />
                        </Grid>
                      ))}
                    </Grid>
                    <HistoryChart history={history} />
                  </Stack>
                </Grid>

                <Grid item xs={12} md={3}>
                  <Stack spacing={2} className={styles.columns}>
                    <SummaryCard summary={summary} fallback={latest?.oee ?? 0} />
                    <EventsTable history={history} />
                  </Stack>
                </Grid>
              </Grid>
            </div>
          )}
        </main>
      </ThemeProvider>
    </div>
  );
}
