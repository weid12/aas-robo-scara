import { useState, forwardRef } from "react";
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Box,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Slide,
  Chip,
  Divider,
  useTheme,
} from "@mui/material";
import { TransitionProps } from "@mui/material/transitions";
import FullscreenIcon from "@mui/icons-material/Fullscreen";
import CloseIcon from "@mui/icons-material/Close";
import EventNoteIcon from "@mui/icons-material/EventNote";
import HistoryIcon from "@mui/icons-material/History";
import type { RobotState } from "../../types/robot";

interface EventsTableProps {
  history: RobotState[];
}

const Transition = forwardRef(function Transition(
  props: TransitionProps & {
    children: React.ReactElement<any, any>;
  },
  ref: React.Ref<unknown>,
) {
  return <Slide direction="up" ref={ref} {...props} />;
});

export function EventsTable({ history }: EventsTableProps) {
  const [open, setOpen] = useState(false);
  const theme = useTheme();
  const events = history.slice(0, 8); // Keep limited view for card
  const allEvents = history; // Use full history for modal

  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  // Helper to count status types for summary
  const statusCounts = allEvents.reduce((acc, curr) => {
    acc[curr.status] = (acc[curr.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Reusable table content
  const renderTable = (data: RobotState[], sticky: boolean = true) => (
    <Table size="small" stickyHeader={sticky} sx={{ tableLayout: "fixed", width: "100%" }}>
      <TableHead>
        <TableRow>
          <TableCell sx={{
            bgcolor: sticky ? "rgba(30, 30, 42, 0.95)" : "transparent",
            fontWeight: 600,
            color: "#a0a0b0",
            fontSize: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.3px",
            padding: "8px 4px",
            width: "25%"
          }}>Horário</TableCell>
          <TableCell sx={{
            bgcolor: sticky ? "rgba(30, 30, 42, 0.95)" : "transparent",
            fontWeight: 600,
            color: "#a0a0b0",
            fontSize: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.3px",
            padding: "8px 4px",
            width: "25%"
          }}>Status</TableCell>
          <TableCell sx={{
            bgcolor: sticky ? "rgba(30, 30, 42, 0.95)" : "transparent",
            fontWeight: 600,
            color: "#a0a0b0",
            fontSize: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.3px",
            padding: "8px 4px",
            width: "25%"
          }}>Modo</TableCell>
          <TableCell sx={{
            bgcolor: sticky ? "rgba(30, 30, 42, 0.95)" : "transparent",
            fontWeight: 600,
            color: "#a0a0b0",
            fontSize: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.3px",
            padding: "8px 4px",
            whiteSpace: "nowrap",
            width: "25%"
          }}>Temp (°C)</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {data.map((row) => (
          <TableRow
            key={row.id}
            hover
            sx={{
              "&:hover": { bgcolor: "rgba(255, 255, 255, 0.02) !important" },
              transition: "background-color 0.2s"
            }}
          >
            <TableCell sx={{ fontFamily: "monospace", color: "#e0e0e0", fontSize: "0.8rem", padding: "8px 4px" }}>
              {new Date(row.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </TableCell>
            <TableCell>
              <Chip
                label={row.status}
                size="small"
                sx={{
                  height: 20,
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  bgcolor: row.status === "Running" ? "rgba(76, 175, 80, 0.2)" :
                    row.status === "Alarm" ? "rgba(255, 82, 82, 0.2)" : "rgba(255, 255, 255, 0.1)",
                  color: row.status === "Running" ? "#66bb6a" :
                    row.status === "Alarm" ? "#ff5252" : "#888"
                }}
              />
            </TableCell>
            <TableCell sx={{ color: "#e0e0e0", fontSize: "0.8rem", padding: "8px 4px" }}>{row.mode}</TableCell>
            <TableCell sx={{ color: "#e0e0e0", fontWeight: 500, fontSize: "0.8rem", padding: "8px 4px" }}>{row.temperature_c?.toFixed(1) ?? "N/D"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );

  return (
    <>
      <Card
        sx={{
          background: "rgba(13,14,22,0.95)",
          borderRadius: 3,
          border: "1px solid rgba(255,255,255,0.08)",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          transition: "all 0.3s ease-in-out",
          "&:hover": {
            borderColor: "rgba(233, 79, 136, 0.5)",
            boxShadow: "0 0 15px rgba(233, 79, 136, 0.3)",
          },
        }}
      >
        <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <EventNoteIcon sx={{ color: "#e94f88" }} />
              <Typography variant="h6" fontWeight={600}>
                Eventos Recentes
              </Typography>
            </Box>
            <IconButton size="small" onClick={handleOpen} sx={{ color: "text.secondary", "&:hover": { color: "#64ffda" } }}>
              <FullscreenIcon fontSize="small" />
            </IconButton>
          </Box>

          <Box sx={{
            flex: 1,
            overflow: "auto",
            mt: 1,
            "&::-webkit-scrollbar": {
              width: "8px"
            },
            "&::-webkit-scrollbar-track": {
              background: "rgba(0, 0, 0, 0.2)",
              borderRadius: "10px"
            },
            "&::-webkit-scrollbar-thumb": {
              background: "rgba(233, 79, 136, 0.3)",
              borderRadius: "10px"
            },
            "&::-webkit-scrollbar-thumb:hover": {
              background: "rgba(233, 79, 136, 0.5)"
            }
          }}>
            {renderTable(events)}
          </Box>
          {events.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Sem eventos no período.
            </Typography>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={open}
        onClose={handleClose}
        TransitionComponent={Transition}
        maxWidth="md"
        fullWidth
        slotProps={{
          backdrop: {
            sx: {
              backdropFilter: "blur(8px)",
              backgroundColor: "rgba(0, 0, 0, 0.75)",
            }
          }
        }}
        PaperProps={{
          sx: {
            background: "linear-gradient(145deg, rgba(30, 30, 42, 1), rgba(20, 20, 32, 1))",
            backgroundImage: "none",
            border: "1px solid rgba(233, 79, 136, 0.15)",
            borderRadius: "20px",
            boxShadow: "0 25px 70px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.05)",
            overflow: "hidden",
            fontFamily: "inherit",
            animation: "slideUp 0.3s ease-out",
            "@keyframes slideUp": {
              from: {
                opacity: 0,
                transform: "translateY(30px) scale(0.95)"
              },
              to: {
                opacity: 1,
                transform: "translateY(0) scale(1)"
              }
            }
          }
        }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            paddingBottom: "1.5rem",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            py: 2.5
          }}
        >
          <Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
              <HistoryIcon sx={{ color: "#e94f88", fontSize: "1.75rem" }} />
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 600,
                  fontSize: "1.75rem",
                  background: "linear-gradient(135deg, #e94f88, #f06292)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  lineHeight: 1.2
                }}
              >
                Histórico de Eventos
              </Typography>
            </Box>
            <Typography variant="caption" sx={{ color: "#b0b0c0", fontSize: "0.9rem", ml: "calc(1.75rem + 12px)", display: "block" }}>
              Registro completo de atividades do robô
            </Typography>
          </Box>
          <IconButton
            onClick={handleClose}
            sx={{
              color: "#888",
              fontSize: "2rem",
              padding: "0.25rem",
              borderRadius: "6px",
              transition: "all 0.2s ease",
              "&:hover": {
                color: "#e94f88",
                background: "rgba(233, 79, 136, 0.1)",
                transform: "rotate(90deg)"
              }
            }}
          >
            <CloseIcon fontSize="inherit" />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ p: 0, bgcolor: "transparent" }}>
          {/* Summary Stats Bar */}
          <Box sx={{
            display: "flex",
            gap: 3,
            p: 2,
            bgcolor: "rgba(255,255,255,0.02)",
            borderBottom: "1px solid rgba(255,255,255,0.08)"
          }}>
            <Box>
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>Total de Eventos</Typography>
              <Typography variant="h6" color="#e94f88" sx={{ fontWeight: 600 }}>{allEvents.length}</Typography>
            </Box>
            <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
            <Box>
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>Running</Typography>
              <Typography variant="h6" color="#66bb6a" sx={{ fontWeight: 600 }}>{statusCounts["Running"] || 0}</Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>Alarmes</Typography>
              <Typography variant="h6" color="#ff5252" sx={{ fontWeight: 600 }}>{statusCounts["Alarm"] || 0}</Typography>
            </Box>
          </Box>

          <Box
            sx={{
              maxHeight: "60vh",
              overflow: "auto",
              "&::-webkit-scrollbar": {
                width: "8px"
              },
              "&::-webkit-scrollbar-track": {
                background: "rgba(0, 0, 0, 0.2)",
                borderRadius: "10px"
              },
              "&::-webkit-scrollbar-thumb": {
                background: "rgba(233, 79, 136, 0.3)",
                borderRadius: "10px"
              },
              "&::-webkit-scrollbar-thumb:hover": {
                background: "rgba(233, 79, 136, 0.5)"
              }
            }}
          >
            {renderTable(allEvents, false)}
          </Box>
        </DialogContent>

        <DialogActions sx={{
          bgcolor: "transparent",
          borderTop: "1px solid rgba(255,255,255,0.08)",
          p: 2,
          gap: 1
        }}>
          <Button
            onClick={handleClose}
            variant="outlined"
            sx={{
              color: "#b0b0c0",
              borderColor: "rgba(255,255,255,0.1)",
              borderRadius: "10px",
              padding: "0.5rem 1.5rem",
              fontWeight: 600,
              transition: "all 0.3s ease",
              "&:hover": {
                borderColor: "#e94f88",
                color: "#e94f88",
                background: "rgba(233, 79, 136, 0.1)"
              }
            }}
          >
            Fechar
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
