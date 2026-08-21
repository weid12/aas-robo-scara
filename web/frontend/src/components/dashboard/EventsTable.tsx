import { useState, forwardRef } from "react";
import { formatNumber } from "../../lib/utils";
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
  // Filters history to keep only effective status changes
  const deduplicatedHistory = history.filter((event, index, array) => {
    if (index === array.length - 1) return true;
    return event.status !== array[index + 1].status;
  });

  const events = deduplicatedHistory.slice(0, 8); // Keep limited view for card
  const allEvents = deduplicatedHistory; // Use full history for modal

  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  // Helper to count status types for summary
  const statusCounts = allEvents.reduce((acc, curr) => {
    let group = "Others";
    if (/running|power_on|joint|moving|auto/i.test(curr.status)) group = "Running";
    else if (/alarm|error|fault/i.test(curr.status)) group = "Alarms";
    else if (/estop/i.test(curr.status)) group = "E-Stop";
    else if (/hold/i.test(curr.status)) group = "Hold";
    
    acc[group] = (acc[group] || 0) + 1;
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
          }}>Time</TableCell>
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
          }}>Mode</TableCell>
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
                  bgcolor:
                    /running|power_on|joint|moving|auto/i.test(row.status) ? "rgba(76, 175, 80, 0.2)" :
                    /alarm|error|fault/i.test(row.status)  ? "rgba(255, 82, 82, 0.2)"  :
                    /estop/i.test(row.status)              ? "rgba(255, 152, 0, 0.2)"  :
                    /hold/i.test(row.status)               ? "rgba(100, 181, 246, 0.2)" :
                    "rgba(255, 255, 255, 0.1)",
                  color:
                    /running|power_on|joint|moving|auto/i.test(row.status) ? "#66bb6a" :
                    /alarm|error|fault/i.test(row.status)  ? "#ff5252"  :
                    /estop/i.test(row.status)              ? "#ffa726"  :
                    /hold/i.test(row.status)               ? "#64b5f6"  :
                    "#888"
                }}
              />
            </TableCell>
            <TableCell sx={{ color: "#e0e0e0", fontSize: "0.8rem", padding: "8px 4px" }}>{row.mode}</TableCell>
            <TableCell sx={{ color: "#e0e0e0", fontWeight: 500, fontSize: "0.8rem", padding: "8px 4px" }}>{row.temperature_c != null ? formatNumber(row.temperature_c, 1) : "N/A"}</TableCell>
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
                Recent Events
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
              No events in this period.
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
                Event History
              </Typography>
            </Box>
            <Typography variant="caption" sx={{ color: "#b0b0c0", fontSize: "0.9rem", ml: "calc(1.75rem + 12px)", display: "block" }}>
              Complete robot activity log
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
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>Total Events</Typography>
              <Typography variant="h6" color="#e94f88" sx={{ fontWeight: 600 }}>{allEvents.length}</Typography>
            </Box>
            <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
            <Box>
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>Running</Typography>
              <Typography variant="h6" color="#66bb6a" sx={{ fontWeight: 600 }}>{statusCounts["Running"] || 0}</Typography>
            </Box>
            <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
            <Box>
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>Alarms</Typography>
              <Typography variant="h6" color="#ff5252" sx={{ fontWeight: 600 }}>{statusCounts["Alarms"] || 0}</Typography>
            </Box>
            <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
            <Box>
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>E-Stop</Typography>
              <Typography variant="h6" color="#ffa726" sx={{ fontWeight: 600 }}>{statusCounts["E-Stop"] || 0}</Typography>
            </Box>
            <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.1)" }} />
            <Box>
              <Typography variant="caption" color="#b0b0c0" textTransform="uppercase" sx={{ fontSize: "0.85rem" }}>Hold</Typography>
              <Typography variant="h6" color="#64b5f6" sx={{ fontWeight: 600 }}>{statusCounts["Hold"] || 0}</Typography>
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
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
