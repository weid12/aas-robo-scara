# Protocolo de Medição de Latência e Taxa de Aquisição

## 1. Definições

### 1.1 Latência fim-a-fim (L)

```
L = T_receive - T_source - Offset_clock
```

| Símbolo | Definição |
|---------|-----------|
| `T_source` | **SourceTimestamp** do `DataValue` OPC UA — instante em que o servidor amostrou a variável no controlador |
| `T_receive` | Instante UTC no cliente (gateway) em que o callback `datachange_notification` registrou o valor em memória |
| `Offset_clock` | Diferença sistemática entre os relógios do servidor e do cliente, estimada via método half-RTT |

### 1.2 Taxa de aquisição efetiva

```
R = N_notificações / T_ensaio   [notif/s ou Hz]
```

---

## 2. Sincronização de Relógios

### 2.1 Método primário: NTP

- Ambas as máquinas (controlador Stäubli e gateway Windows) devem estar sincronizadas via NTP com o mesmo servidor de referência
- Precisão esperada: **1–10 ms** em LAN Ethernet
- Verificar com: `w32tm /query /status` (Windows) ou leitura do nó `ServerStatus.CurrentTime`

### 2.2 Método alternativo: PTP (IEEE 1588)

- Se o hardware suportar, PTP oferece precisão < 1 µs
- Requer switches compatíveis com PTP (boundary/transparent clock)
- O controlador Stäubli TS2 **não** suporta PTP nativamente

### 2.3 Compensação residual (half-RTT)

O script mede o offset residual antes do ensaio:

1. Lê `Server.ServerStatus.CurrentTime` (ns=0;i=2258) 20 vezes
2. Para cada leitura: `offset_i = (T_before + T_after)/2 - T_server`
3. Remove outliers (> 2σ)
4. Offset final: média das amostras filtradas

Esse offset é subtraído de cada medição de latência.

---

## 3. Protocolo do Ensaio

### 3.1 Pré-requisitos

- [ ] Gateway e controlador com NTP sincronizado
- [ ] Rede estável (sem downloads pesados ou interferências)
- [ ] Robô em modo de operação representativo (manual/automático)
- [ ] Nenhum outro cliente OPC UA conectado (carga isolada)
- [ ] Script de benchmark com acesso direto ao servidor (sem proxy)

### 3.2 Parâmetros configuráveis

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `--duration` | 60 s | Duração da coleta |
| `--pub-interval` | 200 ms | Publishing interval da subscription |
| `--clock-sync` | NTP | Método de sincronização declarado |
| `--server` | opc.tcp://192.168.0.31:4880/Staubli | Endpoint OPC UA |

### 3.3 Duração recomendada

| Finalidade | Duração | N amostras esperadas* |
|-----------|---------|----------------------|
| Teste rápido | 60 s | ~1.500 |
| Ensaio de artigo | 3600 s (1 h) | ~90.000 |
| Ensaio estendido | 7200 s (2 h) | ~180.000 |

*Estimativa: 33 nós × 5 notificações/s (publishing_interval=200ms, com mudanças contínuas)

### 3.4 Execução

```bash
# Ensaio padrão (1 minuto)
python benchmarks/latency_benchmark.py --duration 60

# Ensaio para artigo (1 hora)
python benchmarks/latency_benchmark.py --duration 3600 --output benchmarks/results/

# Com publishing interval diferente
python benchmarks/latency_benchmark.py --duration 3600 --pub-interval 100
```

---

## 4. Métricas Reportadas

| Métrica | Descrição |
|---------|-----------|
| **Média ± DP** | Latência média e desvio padrão |
| **Mediana** | Percentil 50 (robusto a outliers) |
| **P95** | 95% das amostras abaixo deste valor |
| **P99** | 99% das amostras abaixo deste valor |
| **Pior caso** | Latência máxima observada |
| **Taxa de aquisição** | Notificações totais / duração [Hz] |
| **Carga declarada** | Nº nós, pub interval, tipo de rede |

---

## 5. Fontes de Incerteza

| Fonte | Magnitude estimada | Mitigação |
|-------|-------------------|-----------|
| Offset NTP residual | ±1–10 ms | Medição half-RTT + compensação |
| Jitter Wi-Fi | ±1–20 ms | Usar Ethernet quando possível |
| Carga CPU do gateway | ±0.1–1 ms | Fechar aplicações desnecessárias |
| Resolução do relógio Windows | ~1 ms (`time.time()`) | Usar `time.perf_counter()` para delta |
| Queueing no servidor OPC UA | 0–publishing_interval | Diminuir publishing_interval |
| GC do Python | ±0–5 ms (esporádico) | Desabilitar GC durante coleta (opcional) |

---

## 6. Critérios de Validade

O ensaio é considerado válido se:

1. **N ≥ 1000 amostras** (significância estatística)
2. **Offset de relógio DP < 5 ms** (sincronização aceitável)
3. **Latências negativas < 5%** do total (caso contrário, offset mal calibrado)
4. **Nenhuma desconexão** durante o ensaio (verificar logs)
5. **Robô ativo** (pelo menos temperatura e contadores variando)

---

## 7. Interpretação dos Resultados

### Para artigo/dissertação:

> "A latência fim-a-fim medida entre o registro no controlador (SourceTimestamp)
> e a disponibilidade no data store do cliente foi de **X ± Y ms** (média ± DP),
> com percentil 95 de **Z ms** e pior caso de **W ms**, em um ensaio de
> **D segundos** com **N amostras**, sob carga de **K nós** monitorados via
> subscription OPC UA (publishing_interval = **P ms**), sincronização via **NTP**
> (offset medido: **O ± S ms**)."

---

## 8. Saída do Script

O script gera dois arquivos em `benchmarks/results/`:

- `latency_benchmark_YYYYMMDD_HHMMSS.json` — dados estruturados (para processamento)
- `latency_benchmark_YYYYMMDD_HHMMSS.txt` — relatório formatado (para documentação)


---

## 9. Benchmark de Persistência Histórica

Além da latência OPC UA, o script `db_benchmark.py` quantifica o desempenho do armazenamento em banco de dados SQLite.

### 9.1 Métricas coletadas

| Métrica | Descrição |
|---------|-----------|
| **Período de aquisição** | Intervalo entre inserções consecutivas (média ± DP, mediana, p95, p99, min/max) |
| **Taxa de inserção** | Registros/s efetivos para cada tabela |
| **Tamanho do banco** | Bytes, páginas, freelist, registros por tabela |
| **Latência das consultas** | Tempo de execução das views da API (100 execuções cada) |

### 9.2 Consultas testadas (views)

| View | Descrição | Equivalente na API |
|------|-----------|-------------------|
| `latest_snapshot` | Último snapshot JSON completo | GET /api/robot/state/latest |
| `history_50` | Últimos 50 registros | GET /api/robot/state/history?limit=50 |
| `history_500` | Últimos 500 registros | GET /api/robot/state/history?limit=500 |
| `timeseries_1h` | Série de 1 variável (1h) | Dashboard de temperatura |
| `timeseries_24h` | Série de 1 variável (24h) | Gráfico histórico |
| `summary_today` | Agregação diária | GET /api/robot/metrics/summary |
| `filter_element` | Filtro composto (submodel + idshort) | Busca específica |
| `count_all` | Contagem total | Monitoramento de crescimento |

### 9.3 Execução

```bash
# Banco de histórico AAS (gerado pelo cliente OPC UA)
python benchmarks/db_benchmark.py

# Banco do backend web
python benchmarks/db_benchmark.py --db web/backend/robot_api/aas_robot_scara.db

# Com mais execuções por consulta (maior precisão estatística)
python benchmarks/db_benchmark.py --queries 500

# Incluindo benchmark da API HTTP (backend deve estar rodando)
python benchmarks/db_benchmark.py --api http://localhost:5000
```

### 9.4 Interpretação para artigo

> "O banco de dados SQLite (X MB, Y registros) apresentou período de inserção
> mediano de **P s** (taxa efetiva de **R reg/s**). A latência de consulta para
> o estado mais recente foi de **L ± S ms** (N=100), com percentil 99 de **Q ms**.
> Para consultas de histórico com 500 registros, a latência foi de **H ± D ms**."


---

## 10. Benchmark de Fidelidade de Sincronização

O script `sync_fidelity_benchmark.py` mede a **distribuição do offset de timestamp** entre o evento no controlador e a atualização efetiva do snapshot, ao longo de N ciclos do robô.

### 10.1 Definição

```
Δt_sync = T_snapshot_write - T_source_event
```

| Símbolo | Definição |
|---------|-----------|
| `T_source_event` | SourceTimestamp OPC UA ou CurrentTime anotado no snapshot |
| `T_snapshot_write` | mtime do arquivo (modo observer) ou instante de flush (modo instrumented) |
| `Δt_sync` | Offset de sincronização — quanto o gêmeo digital "atrasa" em relação ao físico |

### 10.2 Modos de medição

| Modo | Descrição | Quando usar |
|------|-----------|-------------|
| **observer** | Monitora mtime do `latest_data.json` externamente | Cliente OPC UA já rodando; mede cadeia completa |
| **instrumented** | Conecta ao OPC UA e usa SourceTimestamp real | Acesso ao controlador; maior precisão |

### 10.3 Métricas reportadas

| Métrica | Descrição |
|---------|-----------|
| **Offset médio ± DP** | Atraso sistemático do gêmeo digital |
| **Mediana** | Valor típico (robusto a outliers) |
| **P5 / P95 / P99** | Distribuição |
| **Min / Max** | Pior e melhor caso |
| **Jitter médio** | Variação entre ciclos consecutivos |
| **Jitter máximo** | Pior variação entre dois ciclos |
| **Taxa efetiva** | Ciclos/s realmente coletados |
| **Ciclos perdidos** | Escritas não detectadas |
| **Histograma** | 20 bins para gráfico de distribuição |

### 10.4 Execução

```bash
# Modo observador (cliente OPC UA deve estar rodando)
python benchmarks/sync_fidelity_benchmark.py --cycles 1000
python benchmarks/sync_fidelity_benchmark.py --cycles 5000 --duration 3600

# Modo instrumentado (acesso direto ao servidor)
python benchmarks/sync_fidelity_benchmark.py --mode instrumented --cycles 5000
python benchmarks/sync_fidelity_benchmark.py --mode instrumented --server opc.tcp://192.168.0.31:4880/Staubli
```

### 10.5 Saída

- `sync_fidelity_YYYYMMDD_HHMMSS.json` — resultados estruturados
- `sync_fidelity_samples_YYYYMMDD_HHMMSS.csv` — amostras brutas (para gráficos)
- `sync_fidelity_YYYYMMDD_HHMMSS.txt` — relatório formatado + histograma ASCII

### 10.6 Interpretação para artigo

> "A fidelidade de sincronização entre o controlador e o gêmeo digital foi avaliada
> em **N ciclos** ao longo de **D minutos**. O offset médio (T_snapshot − T_source)
> foi de **X ± Y ms** (mediana: **M ms**, P95: **Z ms**, pior caso: **W ms**).
> O jitter inter-ciclo foi de **J ± K ms**, indicando [estabilidade/variação]
> na cadeia de aquisição."


---

## 11. Benchmark de Injeção de Falhas

O script `fault_injection_benchmark.py` executa ensaios controlados de falha para avaliar a resiliência do sistema.

### 11.1 Ensaios disponíveis

| Ensaio | Método de injeção | O que mede |
|--------|-------------------|------------|
| **disconnect** | Bloqueia porta OPC UA via regra de firewall | Detecção de desconexão + reconexão automática |
| **packet-loss** | Ciclos intermitentes de block/unblock (simula ~X% perda) | Degradação do throughput + amostras perdidas |
| **gateway-restart** | Mata o processo `client_asyncua.py` e reinicia após N s | Tempo de cold-start + recuperação |

### 11.2 Métricas reportadas

| Métrica | Definição |
|---------|-----------|
| **Tempo de detecção** | T_detect − T_inject (ms) — quando o snapshot para de atualizar |
| **Tempo de recuperação** | T_recover − T_inject (ms) — quando o snapshot volta a atualizar |
| **Amostras perdidas** | Nº esperado durante a falha − Nº efetivamente recebido |
| **Comportamento de fallback** | `stale_value` (último válido mantido), `reconnected`, `null`, `error` |

### 11.3 Pré-requisitos

- **disconnect / packet-loss**: execução como Administrador (para `netsh advfirewall`)
- **gateway-restart**: processo `client_asyncua.py` em execução
- **Todos**: `latest_data.json` sendo atualizado pelo cliente OPC UA

### 11.4 Execução

```bash
# Desconexão OPC UA (5 iterações, 10s de falha cada)
python benchmarks/fault_injection_benchmark.py --test disconnect --iterations 5

# Perda de pacotes 30% por 30 segundos
python benchmarks/fault_injection_benchmark.py --test packet-loss --loss-pct 30 --fault-duration 30

# Restart do gateway (3 iterações, 15s de downtime)
python benchmarks/fault_injection_benchmark.py --test gateway-restart --iterations 3 --fault-duration 15

# Todos os ensaios em sequência
python benchmarks/fault_injection_benchmark.py --test all --fault-duration 10 --iterations 5
```

### 11.5 Protocolo detalhado

#### 11.5.1 Desconexão/Reconexão OPC UA

```
1. Estabilização (10s) — confirma snapshot atualizando
2. Bloqueia porta via netsh advfirewall (t=0)
3. Monitora mtime do snapshot — detecta parada
4. Após N segundos, remove regra de firewall
5. Monitora — detecta retomada de atualização
6. Registra: T_detecção, T_recuperação, amostras perdidas
7. Repete K vezes
```

#### 11.5.2 Perda de Pacotes

```
1. Estabilização
2. Loop de block/unblock rápido (duty cycle = loss_pct%)
   - Block: ~100ms × (loss_pct/100)
   - Unblock: ~100ms × (1 - loss_pct/100)
3. Conta amostras efetivamente recebidas durante o período
4. Compara com esperado (fault_duration / write_interval)
5. Registra perda efetiva e recuperação
```

#### 11.5.3 Restart do Gateway

```
1. Encontra PID do client_asyncua.py
2. Kill -9 (crash abrupto)
3. Monitora — snapshot congela
4. Após N segundos, reinicia o processo
5. Monitora — snapshot volta a atualizar
6. Registra tempo total de recuperação (inclui cold-start + reconexão OPC UA)
```

### 11.6 Interpretação para artigo

> "Foram realizados N ensaios de [desconexão/perda de pacotes/restart] com
> duração de falha de **D segundos**. O tempo médio de detecção foi de
> **Td ± σd ms** e o tempo de recuperação de **Tr ± σr ms** (P95: **Tp ms**).
> Em média, **L amostras** foram perdidas por evento (esperadas: **E**,
> taxa de perda: **L/E × 100%**). O comportamento de fallback predominante
> foi **[stale_value/reconnected]**, indicando que o gêmeo digital mantém
> o último estado válido durante a indisponibilidade."


---

## 12. Benchmark Comparativo entre Arquiteturas

O script `comparative_benchmark.py` executa os mesmos ensaios em 3 cenários distintos para comparação direta.

### 12.1 Cenários

| # | Cenário | Descrição | Persistência |
|---|---------|-----------|--------------|
| (i) | **baseline** | Cliente OPC UA direto, sem camada AAS, sem persistência | Nenhuma (memória) |
| (ii) | **basyx** | OPC UA → Servidor AAS aberto (Eclipse BaSyx ou FA³ST via HTTP) | Gerenciada pelo servidor AAS |
| (iii) | **influxdb** | Arquitetura proposta com InfluxDB/TimescaleDB ao invés de SQLite | InfluxDB 2.x |

### 12.2 Métricas comparadas

| Métrica | Unidade | O que mede |
|---------|---------|------------|
| Latência média ± DP | ms | Overhead de cada camada |
| Latência P95 / P99 | ms | Comportamento sob carga |
| Taxa de aquisição | Hz | Throughput efetivo |
| CPU média / pico | % | Custo computacional |
| Memória RSS média / pico | MB | Footprint |
| Armazenamento | MB | Eficiência de storage |
| Consulta histórica | ms | Performance de leitura |

### 12.3 Pré-requisitos por cenário

```
baseline:   pip install asyncua numpy psutil
basyx:      + Eclipse BaSyx rodando em http://localhost:4001
influxdb:   + pip install influxdb-client
            + InfluxDB 2.x rodando em http://localhost:8086
            + Variáveis: INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET
```

### 12.4 Execução

```bash
# Cenário individual (5 minutos cada)
python benchmarks/comparative_benchmark.py --scenario baseline --duration 300
python benchmarks/comparative_benchmark.py --scenario basyx --duration 300
python benchmarks/comparative_benchmark.py --scenario influxdb --duration 300

# Todos em sequência (gera tabela comparativa automaticamente)
python benchmarks/comparative_benchmark.py --scenario all --duration 300

# Gerar tabela a partir de resultados anteriores
python benchmarks/comparative_benchmark.py --compare benchmarks/results/
```

### 12.5 Saída

- `comparative_<cenario>_YYYYMMDD_HHMMSS.json` — resultado individual
- `comparative_all_YYYYMMDD_HHMMSS.json` — todos os cenários consolidados
- `comparative_table_YYYYMMDD_HHMMSS.txt` — tabela comparativa formatada

### 12.6 Template de tabela para artigo

```
┌───────────────────────────────────┬────────────────────┬────────────────────┬────────────────────┐
│ Métrica                           │ Baseline (i)       │ BaSyx (ii)         │ InfluxDB (iii)     │
├───────────────────────────────────┼────────────────────┼────────────────────┼────────────────────┤
│ Latência média±DP (ms)            │                    │                    │                    │
│ Latência P95 (ms)                 │                    │                    │                    │
│ Taxa aquisição (Hz)               │                    │                    │                    │
│ CPU média (%)                     │                    │                    │                    │
│ Memória RSS (MB)                  │                    │                    │                    │
│ Armazenamento (MB)                │                    │                    │                    │
│ Consulta histórica last (ms)      │                    │                    │                    │
│ Consulta histórica 1h (ms)        │                    │                    │                    │
└───────────────────────────────────┴────────────────────┴────────────────────┴────────────────────┘
```

### 12.7 Interpretação

- **Baseline** representa o floor de latência (overhead mínimo do transporte OPC UA)
- **BaSyx** mostra o overhead de um servidor AAS completo (HTTP + serialização AAS)
- **InfluxDB** mostra o trade-off de usar um TSDB dedicado vs SQLite embarcado
- A diferença (cenário - baseline) isola o custo de cada camada adicionada
