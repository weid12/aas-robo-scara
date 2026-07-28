import { Card, CardContent, LinearProgress, Typography, Stack } from "@mui/material";
import type { RobotSummary } from "../../types/robot";

interface SummaryCardProps {
  summary?: RobotSummary | null;
  fallback?: number;
  className?: string;
}

export function SummaryCard({ summary, fallback, className }: SummaryCardProps) {
  const meters = [
    { key: "oee_avg", label: "OEE" },
    { key: "availability_avg", label: "Availability" },
    { key: "performance_avg", label: "Performance" },
    { key: "quality_avg", label: "Quality" },
  ] as const;

  return (
    <Card
      className={className}
      sx={{
        background: "rgba(20,22,33,0.95)",
        borderRadius: 3,
        border: "1px solid rgba(255,255,255,0.08)",
        transition: "all 0.3s ease-in-out",
        "&:hover": {
          borderColor: "rgba(233, 79, 136, 0.5)",
          boxShadow: "0 0 15px rgba(233, 79, 136, 0.3)",
        },
      }}
    >
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary" textTransform="uppercase">
          Daily Metrics
        </Typography>
        <Stack spacing={1.5} sx={{ mt: 2 }}>
          {meters.map((meter) => {
            const rawValue = summary?.[meter.key];
            const percent = Math.round(((rawValue ?? fallback ?? 0) as number) * 100);
            return (
              <div key={meter.key}>
                <Typography variant="body2" color="text.secondary">
                  {meter.label} · {percent}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={percent}
                  sx={{
                    height: 8,
                    borderRadius: 999,
                    backgroundColor: "rgba(255,255,255,0.1)",
                    "& .MuiLinearProgress-bar": {
                      borderRadius: 999,
                    },
                  }}
                />
              </div>
            );
          })}
        </Stack>
      </CardContent>
    </Card>
  );
}
