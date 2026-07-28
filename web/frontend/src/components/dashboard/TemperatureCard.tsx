import { Card, CardContent, Typography, Box, Grid, useTheme } from "@mui/material";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import DeviceThermostatIcon from "@mui/icons-material/DeviceThermostat";
import type { RobotState } from "../../types/robot";

interface TemperatureCardProps {
    latest?: RobotState | null;
}

const MIN_TEMP = 5;
const MAX_TEMP = 40;
const RANGE = MAX_TEMP - MIN_TEMP;

// Helper to get color based on temperature
const getTempColor = (temp: number) => {
    if (temp > 40) return "#ff5252"; // Alert (Red)
    if (temp >= 32) return "#ffa726"; // Warning (Orange)
    return "#64ffda"; // Safe (Green/Cyan)
};

// Helper to generate chart data
const getChartData = (temp: number) => {
    // Clamp temp between min and max for visualization percentage, 
    // but allow overflow for color logic if needed
    const effectiveTemp = Math.max(MIN_TEMP, temp);
    const percentage = Math.min(100, Math.max(0, ((effectiveTemp - MIN_TEMP) / RANGE) * 100));

    return [
        { name: "Used", value: percentage },
        { name: "Remaining", value: 100 - percentage },
    ];
};

export function TemperatureCard({ latest }: TemperatureCardProps) {
    const theme = useTheme();
    const baseTemp = latest?.temperature_c ?? 0;

    // Real temperatures per axis read from OPC UA via latest_data.json
    const axes = [
        { name: "Axis 1", temp: latest?.motorProbe1_temp ?? 0 },
        { name: "Axis 2", temp: latest?.motorProbe2_temp ?? 0 },
        { name: "Axis 3", temp: latest?.motorProbe3_temp ?? 0 },
        { name: "Axis 4", temp: latest?.motorProbe4_temp ?? 0 },
    ];

    return (
        <Card
            sx={{
                background: "linear-gradient(135deg, rgba(20,22,33,0.95), rgba(15,18,30,0.98))",
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
                <Box sx={{ mb: 3 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                        <DeviceThermostatIcon sx={{ color: "#e94f88" }} />
                        <Typography variant="h6" fontWeight={600}>
                            Axis Temperature
                        </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                        Monitoring the operational range from +5 °C to +40 °C
                    </Typography>
                </Box>

                <Grid container spacing={2}>
                    {axes.map((axis) => {
                        const color = getTempColor(axis.temp);
                        const data = getChartData(axis.temp);
                        const percentage = Math.round(((axis.temp - MIN_TEMP) / RANGE) * 100);
                        const isAlert = axis.temp > 40;

                        return (
                            <Grid item xs={6} key={axis.name}>
                                <Box
                                    sx={{
                                        display: "flex",
                                        flexDirection: "column",
                                        alignItems: "center",
                                        p: 1,
                                        background: "rgba(255,255,255,0.02)",
                                        borderRadius: 2,
                                    }}
                                >
                                    <Box sx={{ width: 100, height: 100, position: "relative" }}>
                                        <ResponsiveContainer width="100%" height="100%">
                                            <PieChart>
                                                <Pie
                                                    data={data}
                                                    cx="50%"
                                                    cy="50%"
                                                    innerRadius={35}
                                                    outerRadius={45}
                                                    startAngle={90}
                                                    endAngle={-270}
                                                    dataKey="value"
                                                    stroke="none"
                                                >
                                                    <Cell key="used" fill={color} />
                                                    <Cell key="remaining" fill="rgba(255,255,255,0.1)" />
                                                </Pie>
                                            </PieChart>
                                        </ResponsiveContainer>
                                        <Box
                                            sx={{
                                                position: "absolute",
                                                top: 0,
                                                left: 0,
                                                right: 0,
                                                bottom: 0,
                                                display: "flex",
                                                flexDirection: "column",
                                                alignItems: "center",
                                                justifyContent: "center",
                                            }}
                                        >
                                            <Typography variant="h6" fontWeight={700} sx={{ color: "#fff", lineHeight: 1 }}>
                                                {axis.temp.toFixed(1)}
                                            </Typography>
                                            <Typography variant="caption" sx={{ color: "#fff", fontSize: "0.65rem", opacity: 0.9 }}>
                                                °C
                                            </Typography>
                                        </Box>
                                    </Box>

                                    <Box sx={{ mt: 1, textAlign: "center" }}>
                                        <Typography variant="subtitle2" sx={{ color: color, fontWeight: 600 }}>
                                            {axis.name}
                                        </Typography>
                                        {isAlert && (
                                            <Typography variant="caption" sx={{ color: "#ff5252", display: "block", mt: 0.5, fontSize: "0.65rem" }}>
                                                Temperature alert
                                            </Typography>
                                        )}
                                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.5, fontSize: "0.65rem", opacity: 0.7 }}>
                                            Faixa: +5 a +40 °C
                                        </Typography>
                                    </Box>
                                </Box>
                            </Grid>
                        );
                    })}
                </Grid>
            </CardContent>
        </Card>
    );
}
