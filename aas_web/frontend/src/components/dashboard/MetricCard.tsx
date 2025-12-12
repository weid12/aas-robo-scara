import { Card, CardContent, Typography, Box } from "@mui/material";
import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string;
  helper?: string;
  icon?: ReactNode;
  accent?: string;
}

export function MetricCard({ label, value, helper, icon, accent }: MetricCardProps) {
  return (
    <Card
      sx={{
        background: "rgba(23,23,30,0.9)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 3,
        transition: "all 0.3s ease-in-out",
        "&:hover": {
          borderColor: "rgba(233, 79, 136, 0.5)",
          boxShadow: "0 0 15px rgba(233, 79, 136, 0.3)",
        },
      }}
    >
      <CardContent sx={{ display: "flex", flexDirection: "column", gap: 1.2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {icon}
          <Typography variant="h6" fontWeight={600}>
            {label}
          </Typography>
        </Box>
        <Typography variant="h4" fontWeight={600} color={accent ?? "text.primary"}>
          {value}
        </Typography>
        {helper && (
          <Typography variant="body2" color="text.secondary">
            {helper}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
