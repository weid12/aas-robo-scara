# Campanha de Medição de Latência e Taxa de Aquisição

## 1. Definição da Latência Fim-a-Fim

A latência fim-a-fim (L) é definida como o intervalo entre o instante de registro
no controlador e a disponibilidade do dado no cliente:

```
L = T_recepção_cliente − T_servidor_OPC_UA − Offset_relógio
```

Onde:
- **T_servidor_OPC_UA** = ServerTimestamp do DataValue OPC UA (instante em que o stack do servidor empacotou a notificação)
- **T_recepção_cliente** = Instante UTC capturado via clock monotônico calibrado (`perf_counter + epoch_offset`) no momento do callback `datachange_notification`
- **Offset_relógio** = Diferença medida entre os relógios do cliente e do servidor, obtida via método NTP half-RTT

## 2. Método de Sincronização de Relógios (NTP half-RTT)

### 2.1 Descrição do Método

A sincronização dos relógios entre o gateway (cliente) e o controlador (servidor OPC UA)
foi realizada utilizando o método **NTP half-RTT** (Network Time Protocol — half Round-Trip Time),
adaptado para o protocolo OPC UA. Este método é análogo ao mecanismo de sincronização
definido na RFC 5905 (NTPv4) e segue os mesmos princípios do IEEE 1588 (PTP) para
estimação de one-way delay.

### 2.2 Protocolo de Medição

```
Para i = 1 até N (N = 30 amostras):
    1. T_antes ← clock_utc_cliente()
    2. T_servidor ← ler_opc_ua(ServerStatus.CurrentTime, ns=0;i=2258)
    3. T_depois ← clock_utc_cliente()
    4. RTT_i ← T_depois − T_antes
    5. T_cliente_mid_i ← (T_antes + T_depois) / 2
    6. Offset_i ← T_cliente_mid_i − T_servidor

Filtragem:
    7. RTT_mediana ← mediana(RTT_1..N)
    8. Descartar amostras com RTT_i > max(RTT_mediana × 2, 5 ms)
    9. Offset_final ← mediana(Offsets filtrados)
   10. Jitter ← desvio_padrão(Offsets filtrados)
```

### 2.3 Justificativa do Método

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| Estimador | Mediana (não média) | Robusto a outliers causados por congestionamento de rede |
| Filtragem | RTT > 2×mediana | Remove amostras com congestionamento atípico |
| N amostras | 30 (pré) + 10 (pós) | Significância estatística + verificação de drift |
| Clock local | `time.perf_counter()` + calibração | Monotônico, não afetado por ajustes NTP do SO |
| Timestamp remoto | ServerTimestamp (não SourceTimestamp) | Gerado pelo stack OPC UA no instante do empacotamento — mesmo relógio que `CurrentTime` |

### 2.4 Modelo de Erro

```
Offset_medido = Timezone + Drift_controlador + Jitter_medição

Onde:
  Timezone         = −4h (UTC−4, Manaus — controlador reporta hora local como UTC)
  Drift_controlador = +40,9 s (relógio interno não sincronizado via NTP)
  Jitter_medição   = ±287 ms (resolução do relógio + variação de rede)
```

### 2.5 Verificação Pré e Pós-Ensaio

O método inclui verificação dupla para detectar drift durante o ensaio:

| Fase | Offset (ms) | DP (ms) | Horário PC (UTC) | Horário Controlador |
|------|-------------|---------|-------------------|---------------------|
| PRÉ-ensaio | +14.440.923 | ±287 | 18:15:46 | 14:14:05 |
| PÓS-ensaio | +14.440.976 | ±290 | 19:15:47 | 15:14:06 |
| **Drift** | **+53 ms** | — | — | — |
| **Taxa de drift** | **0,88 ms/min** | — | — | — |

**Conclusão:** Drift de 53 ms em 3.600 s (0,88 ms/min) — desprezível para a resolução da medição (jitter ±287 ms). Os relógios permaneceram estáveis durante todo o ensaio.

### 2.6 Limitações

- O controlador **não suporta NTP/PTP nativo** (Stäubli CS9 firmware 2.0.0)
- A precisão máxima alcançável com este método é limitada pelo jitter do relógio interno do controlador (~±287 ms)
- Para precisão sub-milissegundo, seria necessário PTP (IEEE 1588) com hardware compatível no controlador e switches boundary/transparent clock

## 3. Protocolo do Ensaio

| Parâmetro | Valor |
|-----------|-------|
| Duração | 3.600,5 s (1 hora) |
| N amostras válidas | 26.859 |
| Outliers descartados | 10 (|L| > 10s, indicam bloqueio do event loop) |
| Nós monitorados | 33 |
| Publishing interval | 200 ms |
| Modo de aquisição | OPC UA Subscription (push-based) |
| Ciclos do robô (J3) | 2.121 |
| Servidor OPC UA | opc.tcp://192.168.0.31:4880/Staubli |
| Rede | Ethernet 100 Mbps (dedicada) |
| Gateway | Windows 11, Intel 11ª gen, 16 GB RAM, Python 3.12 |

## 4. Resultados

### 4.1 Dispersão de Latência (Jitter do Sistema)

Devido à ausência de sincronização NTP/PTP no controlador, os valores absolutos de latência incluem o jitter do relógio interno (±287 ms). A **dispersão** (diferença entre percentis) é a métrica mais representativa do desempenho real do transporte OPC UA:

| Métrica | Valor |
|---------|-------|
| Dispersão P95–P5 | **531,99 ms** |
| Desvio padrão | **158,19 ms** |
| Amplitude total (max–min) | **587,61 ms** |
| Percentil 95 | 207,93 ms (relativo à mediana) |
| Percentil 99 | 245,59 ms (relativo à mediana) |
| Pior caso (máximo) | 263,55 ms (relativo à mediana) |

### 4.2 Taxa de Aquisição

| Métrica | Valor |
|---------|-------|
| Taxa efetiva | **7,46 notificações/s** |
| Total de notificações | 26.869 |
| Notificações/nó (média) | 813,9 |
| Ciclos do robô detectados | 2.121 |
| Notificações por ciclo | ~12,7 |

### 4.3 Carga Declarada

33 nós OPC UA monitorados via subscription (publishing_interval = 200 ms), em rede Ethernet 100 Mbps dedicada, durante 3.600 s, com o robô executando movimentação cíclica contínua (2.121 ciclos de pick-and-place detectados via inversão de direção da junta J3).

## 5. Verificação de Estabilidade dos Relógios

| Verificação | PRÉ-ensaio | PÓS-ensaio |
|-------------|------------|------------|
| Offset (ms) | +14.440.923 | +14.440.976 |
| Drift durante ensaio | +53 ms (0,88 ms/min) |
| Conclusão | Drift desprezível (~1 ms/min) — relógios estáveis durante o ensaio |

## 6. Interpretação para Artigo

> A latência de transporte OPC UA fim-a-fim foi avaliada em uma campanha de
> **3.600 segundos** (1 hora), totalizando **26.859 amostras** válidas sob carga
> de **33 nós** monitorados via subscription (publishing_interval = 200 ms),
> durante **2.121 ciclos** operacionais do robô SCARA.
>
> A sincronização de relógios foi realizada via método NTP half-RTT adaptado
> para OPC UA (30 amostras, filtragem RTT, mediana). O controlador não suporta
> NTP/PTP nativo, apresentando um offset fixo de +4h (timezone UTC-4) com drift
> residual de 40,9 s e jitter de ±287 ms.
>
> A dispersão de latência medida (DP = **158 ms**, P95-P5 = **532 ms**) reflete
> a composição do jitter do relógio do controlador (±287 ms) com a variação real
> do transporte OPC UA (~50-100 ms em Ethernet 100 Mbps).
>
> A taxa de aquisição efetiva foi de **7,46 Hz** (7,46 notificações/s), com
> 10 outliers descartados (< 0,04%) por bloqueio transitório do event loop Python.
> O drift dos relógios durante o ensaio foi de apenas 53 ms (0,88 ms/min),
> confirmando a estabilidade da medição.

## 7. Limitações e Recomendações

1. **Sincronização NTP do controlador:** Para obter latências absolutas precisas (não apenas dispersão), o controlador deve ser configurado com NTP apontando para o mesmo servidor que o gateway.

2. **Jitter dominante:** O jitter de ±287 ms é do relógio do controlador (resolução de ~1s do `CurrentTime`), não da rede. A latência real de rede Ethernet é tipicamente < 1 ms.

3. **Medida alternativa:** Para isolar a latência de rede pura, usar o RTT médio medido (1,1 ms) dividido por 2 como estimativa de one-way delay (~0,5 ms).
