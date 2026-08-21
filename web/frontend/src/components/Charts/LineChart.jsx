import { useEffect, useRef } from "react";
import styles from "./LineChart.module.css";

/**
 * Componente de gráfico de linha simples usando Canvas API
 * Otimizado para séries temporais de dados do robô
 */
export default function LineChart({ data, title, unit, color }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;

    // Configurar tamanho do canvas
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const padding = { top: 30, right: 20, bottom: 40, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Limpar canvas
    ctx.clearRect(0, 0, width, height);

    // Extrair valores — downsample if too many points (keep min/max per bucket for visibility)
    let plotData = data;
    const maxPoints = Math.min(Math.floor(chartWidth), 600);
    if (data.length > maxPoints) {
      // LTTB-like: keep min and max per bucket to preserve visual peaks/valleys
      const bucketSize = Math.ceil(data.length / maxPoints);
      plotData = [];
      for (let i = 0; i < data.length; i += bucketSize) {
        const bucket = data.slice(i, i + bucketSize);
        const minPt = bucket.reduce((a, b) => (b.v < a.v ? b : a), bucket[0]);
        const maxPt = bucket.reduce((a, b) => (b.v > a.v ? b : a), bucket[0]);
        // Add in order of appearance to keep time ordering
        const minIdx = bucket.indexOf(minPt);
        const maxIdx = bucket.indexOf(maxPt);
        if (minIdx <= maxIdx) {
          plotData.push(minPt);
          if (minPt !== maxPt) plotData.push(maxPt);
        } else {
          plotData.push(maxPt);
          if (minPt !== maxPt) plotData.push(minPt);
        }
      }
    }

    const values = plotData.map((d) => d.v);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const valueRange = maxValue - minValue || 1;

    // Função para mapear valor para coordenada Y
    const scaleY = (value) => {
      return (
        padding.top +
        chartHeight -
        ((value - minValue) / valueRange) * chartHeight
      );
    };

    // Função para mapear índice para coordenada X
    const scaleX = (index) => {
      return padding.left + (index / (plotData.length - 1 || 1)) * chartWidth;
    };

    // Desenhar grid horizontal
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 1;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (i / gridLines) * chartHeight;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(padding.left + chartWidth, y);
      ctx.stroke();

      // Labels do eixo Y
      const value = maxValue - (i / gridLines) * valueRange;
      ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(value.toFixed(2), padding.left - 10, y + 4);
    }

    // Desenhar linha do gráfico
    ctx.strokeStyle = color || "#e94f88";
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    ctx.beginPath();
    plotData.forEach((point, index) => {
      const x = scaleX(index);
      const y = scaleY(point.v);

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // Desenhar pontos
    ctx.fillStyle = color || "#e94f88";
    if (plotData.length < 50) {
      plotData.forEach((point, index) => {
        const x = scaleX(index);
        const y = scaleY(point.v);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    // Desenhar eixos
    ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, padding.top + chartHeight);
    ctx.lineTo(padding.left + chartWidth, padding.top + chartHeight);
    ctx.stroke();

    // Labels do eixo X (timestamps)
    ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";

    const labelCount = Math.min(6, plotData.length);
    // Detect if range spans more than 1 day
    let spanDays = 0;
    try {
      const firstDate = new Date(plotData[0].t);
      const lastDate = new Date(plotData[plotData.length - 1].t);
      spanDays = (lastDate - firstDate) / (1000 * 60 * 60 * 24);
    } catch {}

    for (let i = 0; i < labelCount; i++) {
      const index = Math.floor((i / (labelCount - 1 || 1)) * (plotData.length - 1));
      const x = scaleX(index);
      const timestamp = plotData[index].t;

      let label = "";
      try {
        const date = new Date(timestamp);
        if (spanDays > 1) {
          // Show date + time for multi-day ranges
          label = date.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
                  " " + date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
        } else {
          // Show only time for same-day data
          label = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
        }
      } catch {
        label = timestamp?.slice(11, 16) || "";
      }

      ctx.fillText(label, x, padding.top + chartHeight + 20);
    }

    // Título e unidade
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.font = "bold 13px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(title || "Metric", padding.left, 20);

    if (unit) {
      ctx.font = "11px sans-serif";
      ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
      ctx.textAlign = "right";
      ctx.fillText(unit, width - padding.right, 20);
    }
  }, [data, title, unit, color]);

  if (!data || data.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No data available</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <canvas ref={canvasRef} className={styles.canvas} />
    </div>
  );
}

// PropTypes removed to avoid external dependency
