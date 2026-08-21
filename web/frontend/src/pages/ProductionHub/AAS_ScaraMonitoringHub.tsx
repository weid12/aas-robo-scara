import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  CircularProgress,
  CssBaseline,
  Stack,
  ThemeProvider,
  Typography,
  createTheme,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import AddAlarmIcon from "@mui/icons-material/AddAlarm";
import AllInclusiveIcon from "@mui/icons-material/AllInclusive";
import WarningIcon from "@mui/icons-material/Warning";
import CloseIcon from "@mui/icons-material/Close";
import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import styles from "./AAS_ScaraMonitoringHub.module.css";
import { getHistory, getLatestState, getSummaryMetrics, getConnectionCount } from "../../services/api";
import { formatInt } from "../../lib/utils";
import type { RobotState, RobotSummary } from "../../types/robot";
import { StatusCard } from "../../components/dashboard/StatusCard";
import { MetricCard } from "../../components/dashboard/MetricCard";
import { RobotCellCard } from "../../components/dashboard/RobotCellCard";
import { EmergencyStopCard } from "../../components/dashboard/EmergencyStopCard";
import { EventsTable } from "../../components/dashboard/EventsTable";
import RobotCard from "../../components/scara_3D/RobotCard";
import { TemperatureCard } from "../../components/dashboard/TemperatureCard";

const REFRESH_MS = 500;

const dashboardTheme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0f111a",
      paper: "rgba(20,21,35,0.95)",
    },
    text: {
      primary: "#f4f4f8ff",
      secondary: "#a0a7c7ff",
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

export default function AAS_ScaraMonitoringHub() {
  const [latest, setLatest] = useState<RobotState | null>(null);
  const [history, setHistory] = useState<RobotState[]>([]);
  const [summary, setSummary] = useState<RobotSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [emergencyArmed, setEmergencyArmed] = useState(false);
  const [showEmergencyPopup, setShowEmergencyPopup] = useState(false);
  const [connectionCount, setConnectionCount] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [latestState, historyState, summaryMetrics, connCount] = await Promise.all([
        getLatestState(),
        getHistory(64),
        getSummaryMetrics(),
        getConnectionCount(),
      ]);
      setLatest(latestState);
      setHistory(historyState);
      setSummary(summaryMetrics);
      setConnectionCount(connCount.count);
      setError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error updating dashboard";
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

  const handleEmergencyChange = (armed: boolean) => {
    setEmergencyArmed(armed);
    if (armed) {
      setShowEmergencyPopup(true);
    } else {
      setShowEmergencyPopup(false);
    }
  };

  const metrics = useMemo(() => {
    let operationUptime = 0;
    
    // Utilize the uptime calculated directly from RuntimeDiagnostics (StartTime to CurrentTime)
    if (latest != null && typeof latest.uptime_s === 'number') {
      operationUptime = latest.uptime_s;
    }

    return [
      {
        label: "Uptime",
        value: formatDuration(operationUptime),
        helper: "Since last restart",
        icon: <AccessTimeIcon sx={{ color: "#e94f88" }} />,
      },
      {
        label: "Downtime",
        value: "1h 15m",
        helper: "Alarms + Idle",
        icon: <AddAlarmIcon sx={{ color: "#e94f88" }} />,
      },
      {
        label: "Cycles",
        value: connectionCount !== null ? formatInt(connectionCount) : "—",
        helper: "OPC UA connections",
        icon: <AllInclusiveIcon sx={{ color: "#e94f88" }} />,
      },
    ];
  }, [summary, latest, connectionCount]);



  return (
    <div className={styles.wrapper}>
      <Sidebar />

      <ThemeProvider theme={dashboardTheme}>
        <CssBaseline />
        <main className={styles.content}>
          <header className={styles.header}>
            <h1 className={styles.brandLabel}>
              <span className={styles.brandSigla}>AAS</span>
              <span className={styles.brandName}>SCARA Monitoring Hub</span>
            </h1>
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
                Loading SCARA robot data...
              </Typography>
            </Box>
          ) : (
            <Grid
              container
              spacing={3}
              sx={{
                m: 0,
                width: "100%",
              }}
            >
              {/* Left + Center Group (9 columns) */}
              <Grid item xs={12} md={9}>
                <Grid container spacing={3}>
                  {/* Left Column (Status + Metrics) */}
                  <Grid item xs={12} md={4}>
                    <Stack spacing={2} className={styles.columns} sx={{ height: "100%" }}>
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

                  {/* Center Column (Robot Cell + 3D Mockup) */}
                  <Grid item xs={12} md={8}>
                    <Stack spacing={2} className={styles.columns} sx={{ height: "100%" }}>
                      <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, gap: 2 }}>
                        <Box sx={{ flex: { md: 2 }, minWidth: 0 }}>
                          <RobotCellCard latest={latest} />
                        </Box>
                        <Box sx={{ flex: { md: 1 }, minWidth: 0 }}>
                          <EmergencyStopCard onEmergencyChange={handleEmergencyChange} />
                        </Box>
                      </Box>

                      <Box sx={{ flex: 1, minHeight: 0 }}>
                        <RobotCard
                          joints={{
                            j1_deg: latest?.joint1_deg ?? 0,
                            j2_deg: latest?.joint2_deg ?? 0,
                            j3_mm: latest?.joint3_mm ?? 0,
                            j4_deg: latest?.joint4_deg ?? 0
                          }}
                          width="100%"
                          height="100%"
                          emergencyArmed={emergencyArmed}
                        />
                      </Box>
                    </Stack>
                  </Grid>
                </Grid>
              </Grid>

              {/* Right Column (Temperature + Events) */}
              <Grid item xs={12} md={3} sx={{ height: { md: 0 }, minHeight: "100%" }}>
                <Stack spacing={2} className={styles.columns} sx={{ height: "100%", overflow: "hidden" }}>
                  <TemperatureCard latest={latest} />
                  <Box sx={{ flex: 1, minHeight: 0 }}>
                    <EventsTable history={history} />
                  </Box>
                </Stack>
              </Grid>
            </Grid>
          )}

          {/* Emergency Stop Pop-up */}
          <Dialog
            open={showEmergencyPopup}
            onClose={() => setShowEmergencyPopup(false)}
            PaperProps={{
              style: {
                backgroundColor: "rgba(30, 0, 0, 0.95)",
                border: "2px solid #ff5252",
                boxShadow: "0 0 50px rgba(255, 0, 0, 0.5)",
                color: "white",
                minWidth: "300px",
                textAlign: "center",
                borderRadius: "12px"
              },
            }}
          >
            <DialogTitle sx={{ display: "flex", justifyContent: "center", alignItems: "center", position: "relative" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <WarningIcon sx={{ color: "#ff5252", fontSize: 40 }} />
                <Typography variant="h5" color="#ff5252" fontWeight="bold">
                  ALERT
                </Typography>
              </Box>
              <IconButton
                onClick={() => setShowEmergencyPopup(false)}
                sx={{
                  color: "#888",
                  fontSize: "2rem",
                  padding: "0.25rem",
                  borderRadius: "6px",
                  transition: "all 0.2s ease",
                  position: "absolute",
                  right: 8,
                  top: 8,
                  "&:hover": {
                    color: "#e94f88",
                    background: "rgba(233, 79, 136, 0.1)",
                    transform: "rotate(90deg)"
                  }
                }}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            </DialogTitle>
            <DialogContent>
              <Typography variant="h6" sx={{ mt: 2, mb: 2 }}>
                EMERGENCY STOP ACTIVATED!
              </Typography>
              <Typography variant="body1" color="text.secondary">
                The robot has been immediately stopped.
              </Typography>
            </DialogContent>
          </Dialog>
        </main>
      </ThemeProvider>
    </div>
  );
}
