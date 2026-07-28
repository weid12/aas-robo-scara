import { Card, CardContent, Typography } from "@mui/material";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { RobotState } from "../../types/robot";

interface HistoryChartProps {
  history: RobotState[];
}

export function HistoryChart({ history }: HistoryChartProps) {
  const chartData = history
    .map((item) => ({
      cycle: item.cycle_time_s ?? 0,
      timestamp: new Date(item.timestamp).getTime(),
    }))
    .filter((item) => item.cycle > 0)
    .reverse();

  return (
    <Card
      sx={{
        background: "rgba(20,21,35,0.95)",
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
          Cycle time (s)
        </Typography>
        {chartData.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Not enough historical data.
          </Typography>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(value: number) =>
                  new Date(value).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })
                }
                stroke="rgba(255,255,255,0.45)"
              />
              <YAxis stroke="rgba(255,255,255,0.45)" />
              <Tooltip
                labelStyle={{ color: "black" }}
                labelFormatter={(value: number) =>
                  new Date(value).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })
                }
                formatter={(value: number) => [
                  (Math.round(value * 100) / 100).toString(),
                  "Cycle Time",
                ]}
              />
              <Line
                type="monotone"
                dataKey="cycle"
                stroke="#00e5ff"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
