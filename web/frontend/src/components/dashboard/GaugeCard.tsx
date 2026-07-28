import { Card, CardContent, Typography } from "@mui/material";
import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";

interface GaugeCardProps {
  label: string;
  value: number;
}

export function GaugeCard({ label, value }: GaugeCardProps) {
  const safeValue = Math.max(0, Math.min(value ?? 0, 1));
  const percent = Number((safeValue * 100).toFixed(1));
  const data = [{ name: label, value: percent, fill: "#00e676" }];

  return (
    <Card
      sx={{
        background: "rgba(15,15,22,0.9)",
        borderRadius: 3,
        border: "1px solid rgba(255,255,255,0.08)",
        transition: "all 0.3s ease-in-out",
        "&:hover": {
          borderColor: "rgba(233, 79, 136, 0.5)",
          boxShadow: "0 0 15px rgba(233, 79, 136, 0.3)",
        },
      }}
    >
      <CardContent sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        <Typography variant="subtitle2" color="text.secondary" textTransform="uppercase">
          {label}
        </Typography>
        <ResponsiveContainer width="100%" height={160}>
          <RadialBarChart
            innerRadius="60%"
            outerRadius="100%"
            barSize={15}
            data={data}
            startAngle={180}
            endAngle={0}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            <RadialBar
              background
              dataKey="value"
              cornerRadius={8}
            />
            <text
              x="50%"
              y="60%"
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#e0e0e0"
              fontSize="24"
              fontWeight="600"
            >
              {percent}%
            </text>
          </RadialBarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
