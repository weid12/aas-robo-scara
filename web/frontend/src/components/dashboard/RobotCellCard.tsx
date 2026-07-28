import { Card, CardContent, Typography, Box, Grid } from "@mui/material";
import PrecisionManufacturingIcon from "@mui/icons-material/PrecisionManufacturing";
import type { RobotState } from "../../types/robot";

interface RobotCellCardProps {
  latest?: RobotState | null;
}

const INFO_FIELDS: Array<{ key: keyof RobotState; label: string; suffix?: string }> = [
  { key: "joint1_deg", label: "Joint 1", suffix: "°" },
  { key: "joint2_deg", label: "Joint 2", suffix: "°" },
  { key: "joint3_mm", label: "Joint 3", suffix: "mm" },
  { key: "joint4_deg", label: "Joint 4", suffix: "°" },
];

export function RobotCellCard({ latest }: RobotCellCardProps) {
  return (
    <Card
      sx={{
        background: "linear-gradient(135deg, rgba(0,176,155,0.25), rgba(15,18,30,0.9))",
        borderRadius: 4,
        border: "1px solid rgba(0, 0, 0, 0.4)",
        height: "220px",
        transition: "all 0.3s ease-in-out",
        position: "relative",
        "&:hover": {
          borderColor: "rgba(233, 79, 136, 0.5)",
          boxShadow: "0 0 15px rgba(233, 79, 136, 0.3)",
        },
      }}
    >
      <CardContent sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <PrecisionManufacturingIcon sx={{ fontSize: 40, color: "#e94f88" }} />
          <Box>
            <Typography variant="h5" fontWeight={600}>
              SCARA Cell
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Current mode: {latest?.mode ?? "N/A"} · Temp:{" "}
              {latest?.temperature_c != null ? `${latest.temperature_c.toFixed(1)} °C` : "N/A"}
            </Typography>
          </Box>
        </Box>

        <Grid container spacing={2}>
          {INFO_FIELDS.map((field) => {
            const value = latest?.[field.key];
            return (
              <Grid key={field.key as string} item xs={6} md={3}>
                <Typography variant="overline" color="text.secondary">
                  {field.label}
                </Typography>
                <Typography variant="h6" fontWeight={600}>
                  {typeof value === "number"
                    ? `${value.toFixed(1)}${field.suffix ?? ""}`
                    : "N/A"}
                </Typography>
              </Grid>
            );
          })}
        </Grid>
        <Typography variant="body2" color="text.secondary" sx={{ marginTop: 0, paddingLeft: 0.5 }}>
          Axis Positions
        </Typography>
      </CardContent>
    </Card>
  );
}
