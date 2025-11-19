export interface RobotState {
  id: number;
  timestamp: string;
  status: string;
  mode: string;
  cycle_time_s: number | null;
  joint1_deg: number | null;
  joint2_deg: number | null;
  joint3_mm: number | null;
  joint4_deg: number | null;
  temperature_c: number | null;
  energy_kwh: number | null;
  oee: number | null;
  availability: number | null;
  performance: number | null;
  quality: number | null;
}

export interface RobotSummary {
  date: string;
  operation_time_s: number;
  downtime_s: number;
  cycles: number;
  energy_kwh: number;
  oee_avg: number | null;
  availability_avg: number | null;
  performance_avg: number | null;
  quality_avg: number | null;
}
