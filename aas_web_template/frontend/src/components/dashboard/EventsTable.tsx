import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from "@mui/material";
import type { RobotState } from "../../types/robot";

interface EventsTableProps {
  history: RobotState[];
}

export function EventsTable({ history }: EventsTableProps) {
  const events = history.slice(0, 8);

  return (
    <Card
      sx={{
        background: "rgba(13,14,22,0.95)",
        borderRadius: 3,
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary" textTransform="uppercase">
          Eventos recentes
        </Typography>
        <Table size="small" sx={{ mt: 1 }}>
          <TableHead>
            <TableRow>
              <TableCell>Horário</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Modo</TableCell>
              <TableCell>Temp (°C)</TableCell>
              <TableCell>OEE</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {events.map((row) => (
              <TableRow key={row.id} hover>
                <TableCell>
                  {new Date(row.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </TableCell>
                <TableCell>{row.status}</TableCell>
                <TableCell>{row.mode}</TableCell>
                <TableCell>{row.temperature_c?.toFixed(1) ?? "N/D"}</TableCell>
                <TableCell>{row.oee != null ? `${(row.oee * 100).toFixed(1)}%` : "N/D"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {events.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            Sem eventos no período.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
