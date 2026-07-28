/**
 * ------------------------------------------------------------------------------------------------------------------
 * Definições de tipos TypeScript para a entidade Robô.
 * Espelha os modelos do backend para garantir tipagem forte no frontend.
 * ------------------------------------------------------------------------------------------------------------------
 */

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
  motorProbe1_temp: number | null;
  motorProbe2_temp: number | null;
  motorProbe3_temp: number | null;
  motorProbe4_temp: number | null;
  energy_kwh: number | null;
  oee: number | null;
  availability: number | null;
  performance: number | null;
  quality: number | null;
  uptime_s?: number | null;
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
