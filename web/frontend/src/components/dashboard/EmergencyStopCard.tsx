import { Card, CardContent, Box, Typography } from "@mui/material";
import EmergencyStopButton from "../EmergencyStopButton/EmergencyStopButton";
import WarningIcon from "@mui/icons-material/Warning";

export interface EmergencyStopCardProps {
    onEmergencyChange?: (armed: boolean) => void;
}

export function EmergencyStopCard({ onEmergencyChange }: EmergencyStopCardProps) {
    return (
        <Card
            sx={{
                background: "linear-gradient(135deg, rgba(255,0,0,0.15), rgba(15,18,30,0.9))",
                borderRadius: 4,
                border: "1px solid rgba(0, 0, 0, 0.4)",
                minHeight: "220px",
                height: "120px",
                transition: "all 0.3s ease-in-out",
                display: "flex",
                alignItems: "stretch",
                justifyContent: "flex-start",
                "&:hover": {
                    borderColor: "rgba(233, 79, 136, 0.5)",
                    boxShadow: "0 0 15px rgba(233, 79, 136, 0.3)",
                },
            }}
        >
            <CardContent sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0, textAlign: "left", width: "100%" }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <WarningIcon sx={{ color: "#e94f88" }} />
                    <Typography 
                        variant="h6" 
                        fontWeight={600} 
                        sx={{ 
                            fontSize: { xs: "1rem", sm: "1.125rem", md: "1.25rem" },
                            lineHeight: 1.2
                        }}
                    >
                        Emergency Stop
                    </Typography>
                </Box>
                <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", width: "100%", flex: 1 }}>
                    <EmergencyStopButton
                        onStateChange={onEmergencyChange}
                        className="emergency-button-hub"
                    />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ marginTop: -1, paddingLeft: 0.5 }}>
                    Operation Interrupt
                </Typography>
            </CardContent>
        </Card>
    );
}
