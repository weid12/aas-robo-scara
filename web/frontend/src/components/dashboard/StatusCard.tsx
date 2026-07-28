import { Card, CardContent, Chip, Typography, Box } from "@mui/material";
import SensorsIcon from "@mui/icons-material/Sensors";

interface StatusCardProps {
  status?: string;
  mode?: string;
  timestamp?: string;
}

const STATUS_COLORS: Record<string, string> = {
  running: "#4caf50",
  idle: "#ffb74d",
  alarm: "#ff5252",
};

export function StatusCard({ status, mode, timestamp }: StatusCardProps) {
  const normalized = status?.toLowerCase() ?? "unknown";
  const chipColor = STATUS_COLORS[normalized] ?? "#64b5f6";

  return (
    <Card
      sx={{
        background: "linear-gradient(135deg, rgba(76,175,80,0.18), rgba(21,27,40,0.9))",
        borderRadius: 3,
        border: "1px solid rgba(255,255,255,0.08)",
        height: "220px",
        display: "flex",
        flexDirection: "column",
        transition: "all 0.3s ease-in-out",
        "&:hover": {
          borderColor: "rgba(233, 79, 136, 0.5)",
          boxShadow: "0 0 15px rgba(233, 79, 136, 0.3)",
        },
      }}
    >
      <CardContent sx={{ display: "flex", flexDirection: "column", gap: 1.2, flex: 1, justifyContent: "space-between" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <SensorsIcon sx={{ color: "#e94f88" }} />
          <Typography variant="h6" fontWeight={600}>
            Current Status
          </Typography>
        </Box>
        <Chip
          label={status ?? "No data"}
          sx={{
            alignSelf: "flex-start",
            fontWeight: 600,
            bgcolor: chipColor,
            color: "#101018",
            px: 1,
          }}
        />
        <Typography variant="body2" color="text.secondary" sx={{ marginTop: -1, paddingLeft: 0.5 }}>
          Mode: <strong>{mode ?? "N/A"}</strong>
        </Typography>
        {timestamp && (
          <Typography variant="body2" color="text.secondary" sx={{ marginTop: 0, paddingLeft: 0.5 }}>
            Updated at {new Date(timestamp).toLocaleString()}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
