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
  const normalized = status?.toLowerCase() ?? "desconhecido";
  const chipColor = STATUS_COLORS[normalized] ?? "#64b5f6";

  return (
    <Card
      sx={{
        background: "linear-gradient(135deg, rgba(76,175,80,0.18), rgba(21,27,40,0.9))",
        borderRadius: 3,
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <CardContent sx={{ display: "flex", flexDirection: "column", gap: 1.2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <SensorsIcon sx={{ color: chipColor }} />
          <Typography variant="subtitle2" color="text.secondary" textTransform="uppercase">
            Status atual
          </Typography>
        </Box>
        <Chip
          label={status ?? "Sem dados"}
          sx={{
            alignSelf: "flex-start",
            fontWeight: 600,
            bgcolor: chipColor,
            color: "#101018",
            px: 1,
          }}
        />
        <Typography variant="body2" color="text.secondary">
          Modo: <strong>{mode ?? "N/D"}</strong>
        </Typography>
        {timestamp && (
          <Typography variant="caption" color="text.secondary">
            Atualizado em {new Date(timestamp).toLocaleString()}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
