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

    // Extrair valores
    const values = data.map((d) => d.v);
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
      return padding.left + (index / (data.length - 1 || 1)) * chartWidth;
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
    ctx.strokeStyle = color || "#ff7746";
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    ctx.beginPath();
    data.forEach((point, index) => {
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
    ctx.fillStyle = color || "#ff7746";
    if (data.length < 50) {
      // Só desenhar pontos se não houver muitos dados
      data.forEach((point, index) => {
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

    const labelCount = Math.min(5, data.length);
    for (let i = 0; i < labelCount; i++) {
      const index = Math.floor((i / (labelCount - 1 || 1)) * (data.length - 1));
      const x = scaleX(index);
      const timestamp = data[index].t;

      // Formatar timestamp (pegar apenas hora:minuto)
      let label = "";
      try {
        const date = new Date(timestamp);
        label = date.toLocaleTimeString("pt-BR", {
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch {
        label = timestamp.slice(11, 16);
      }

      ctx.fillText(label, x, padding.top + chartHeight + 20);
    }

    // Título e unidade
    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.font = "bold 13px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(title || "Métrica", padding.left, 20);

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
        <p>Sem dados disponíveis</p>
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
