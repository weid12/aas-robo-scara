# Benchmark Sessions Manifest & Raw Log Traceability

This document establishes the formal mapping between the experimental results presented in the manuscript (*"An Asset Administration Shell Architecture with Dual Data Persistence for the Monitoring of an Industrial SCARA Robot"*) and the raw log files, database artifacts, and physical network interfaces preserved in this repository.

---

## 1. Network Interface Identification & Hardware Configuration

All telemetry acquisition campaigns and physical fault injection trials communicating with the physical robot controller were conducted over a dedicated wired industrial Ethernet connection.

### 1.1 Physical Robot Industrial Network Interface
* **OS Interface Name:** `Ethernet`
* **Hardware Network Adapter:** `Killer E2600 Gigabit Ethernet Controller`
* **MAC Address:** `B4-45-06-C3-4F-D1`
* **IPv4 Address / Subnet:** `192.168.0.200 / 24` (`255.255.255.0`)
* **Physical Topology:** Dedicated point-to-point Cat6 UTP industrial Ethernet link connecting the edge gateway to the Stäubli CS9 controller.
* **Negotiated Link Speed:** `100 Mbps` (100BASE-TX full-duplex, determined by the CS9 industrial port transceiver).
* **Target OPC UA Server Endpoint:** `opc.tcp://192.168.0.31:4880/Staubli`
* **Operating Role:** Real-time OPC UA subscription stream handling 33 monitored nodes at 200 ms publishing interval.

### 1.2 Auxiliary & Plant Network Interfaces
* **WLAN Interface (`Wi-Fi`):** `Killer(R) Wi-Fi 6 AX1650i 160MHz Wireless Network Adapter`, IP `10.193.249.17`, MAC `4E-CA-F7-0B-8D-62`, speed `173.3 Mbps`. Used exclusively for supervisory dashboard remote access and gateway management; isolated from the shop-floor robot control loop.
* **Loopback Pseudo-Interface (`127.0.0.1`):** Used for intra-gateway interprocess communications (REST API between FastAPI/Flask backend at `:5000` and React frontend at `:5173`, internal gateway benchmark evaluations, and local synthetic servers).
* **Virtual Ethernet (`vEthernet`):** `Hyper-V Virtual Ethernet Adapter`, IP `172.28.80.1`, speed `10 Gbps`. Virtual switch interface on the Windows 11 host.

---

## 2. Comprehensive Traceability Matrix: Manuscript to Raw Logs

The table below maps each table, section, and key metric in the manuscript to its authoritative raw JSON/text log file in `benchmarks/results/`.

| Paper Item | Experiment Description | Authoritative Raw Log File | Network Interface Used | Target Server Endpoint |
|---|---|---|---|---|
| **Table 5 & Section 4.2** | 1-hour Pick-and-Place Telemetry Campaign ($N=26,859$, 7.46 Hz, P95=330 ms) | [`latency_benchmark_20260812_151547.json`](./latency_benchmark_20260812_151547.json) / [`.txt`](./latency_benchmark_20260812_151547.txt) | `Ethernet` (`192.168.0.200`) | `opc.tcp://192.168.0.31:4880/Staubli` |
| **Table 6 (Col 1)** | Proposed Stack (Atomic JSON + SQLite dual persistence) | [`latency_benchmark_20260812_151547.json`](./latency_benchmark_20260812_151547.json) | `Ethernet` (`192.168.0.200`) | `opc.tcp://192.168.0.31:4880/Staubli` |
| **Table 6 (Col 2)** | Direct OPC UA Baseline (Pure client, no AAS, in-memory) | [`comparative_baseline_20260812_170007.json`](./comparative_baseline_20260812_170007.json) | `Ethernet` (`192.168.0.200`) | `opc.tcp://192.168.0.31:4880/Staubli` |
| **Table 6 (Col 3)** | Eclipse BaSyx AAS Server Baseline (HTTP PUT ingestion) | [`comparative_basyx_20260812_134147.json`](./comparative_basyx_20260812_134147.json) | `Ethernet` (OPC UA ingress) + `Loopback` (`127.0.0.1:4001`) | Robot: `192.168.0.31:4880`, BaSyx: `:4001` |
| **Table 6 (Col 4)** | InfluxDB Dedicated TSDB Baseline (WAL single-insert) | [`comparative_influxdb_20260812_134348.json`](./comparative_influxdb_20260812_134348.json) | `Ethernet` (OPC UA ingress) + Local storage | `opc.tcp://192.168.0.31:4880/Staubli` |
| **Table 6 (Query Rows)** | SQLite Historical Query Latency (`last`, `range-500`) | [`db_benchmark_20260804_092003.json`](./db_benchmark_20260804_092003.json) / [`db_benchmark_20260803_144611.json`](./db_benchmark_20260803_144611.json) | `Loopback` (`127.0.0.1:5000`) | REST API on local SQLite store |
| **Table 7 (Col 1)** | Fault: Connection Loss ($n=5$ trials, 10 s outage) | [`fault_injection_disconnect_reconnect_20260811_162935.json`](./fault_injection_disconnect_reconnect_20260811_162935.json) / [`.txt`](./fault_injection_disconnect_reconnect_20260811_162935.txt) | `Ethernet` (`192.168.0.200`) | `opc.tcp://192.168.0.31:4880/Staubli` |
| **Table 7 (Col 2)** | Fault: Intermittent Connectivity ($n=3$ trials, 30 s window, ~20% drop) | [`fault_injection_packet_loss_20260811_163406.json`](./fault_injection_packet_loss_20260811_163406.json) / [`.txt`](./fault_injection_packet_loss_20260811_163406.txt) | `Ethernet` (`192.168.0.200`) | `opc.tcp://192.168.0.31:4880/Staubli` |
| **Table 7 (Col 3)** | Fault: Gateway Process Restart ($n=3$ trials, 10 s downtime) | [`fault_injection_gateway_restart_20260811_164906.json`](./fault_injection_gateway_restart_20260811_164906.json) / [`.txt`](./fault_injection_gateway_restart_20260811_164906.txt) | `Ethernet` (`192.168.0.200`) | `opc.tcp://192.168.0.31:4880/Staubli` |
| **Section 4.3** | Internal Processing Delay (1000 robot cycles, local simulation) | [`sync_fidelity_20260804_104946.json`](./sync_fidelity_20260804_104946.json) / [`.txt`](./sync_fidelity_20260804_104946.txt) | `Loopback` (`127.0.0.1`) | `opc.tcp://0.0.0.0:4842` |
| **Table 8 & Section 4.6** | Portability Assessment (KUKA KR 210 6-axis remapping) | [`portability_report_6axis.txt`](./portability_report_6axis.txt) | `Loopback` (`127.0.0.1`) | Simulated 6-axis server |

---

## 3. Disentanglement of Metric Units & Fault Accounting (Table 7)

### 3.1 Clarification of Temporal Frequencies & Units
The system operates across three distinct time bases and data representations:

1. **OPC UA Data-Change Notification Stream:**
   * Generated asynchronously by the Stäubli embedded OPC UA server across 33 monitored nodes.
   * Aggregate observed arrival rate: **7.46 Hz** (7.4599 notifications/s).
   * In a 10 s fault duration: $10\text{ s} \times 7.4599\text{ Hz} \approx 74.6$ expected incoming notifications.
   * In a 30 s fault duration: $30\text{ s} \times 7.4599\text{ Hz} \approx 223.8$ (~224) expected incoming notifications.

2. **Persistence Flush Cycle (Write Slot):**
   * Scheduled by `_writer_task` in `client_asyncua.py` and monitored by `SnapshotMonitor` in `fault_injection_benchmark.py`.
   * Nominal interval: **0.5 s** (2.0 write slots/s).
   * In a 10 s fault duration: $10\text{ s} / 0.5\text{ s} = 20$ expected write slots.
   * In a 30 s fault duration: $30\text{ s} / 0.5\text{ s} = 60$ expected write slots.

3. **SQLite Relational Table Rows:**
   * Each executed write slot executes a single atomic transaction inserting records into the SQLite tables:
     - `timeseries` table: **19 rows** per write slot (one row for each active numeric metric: 4 Joint positions, CycleTime, 5 Temperature probes, 6 Safety signals, 2 Power metrics, 1 Operation counter).
     - `submodel_snapshots` table: **33 rows** per write slot (normalized key-value representation).
     - `submodel_snapshots_json` table: **9 rows** per write slot (complete submodel JSON blobs).
     - Total rows across all tables: **61 to 89 rows** per write slot.
   * Nominal timeseries insertion rate: $19\text{ rows} \times 2.0\text{ slots/s} = 38.0\text{ rows/s}$.

### 3.2 Resolution of the Ambiguity on Page 18
In early drafts of page 18, the count of **32 to 33 missed write slots** was divided by the **224 expected OPC UA notifications**, yielding the mathematically inconsistent ratio:
$$\frac{32.5\text{ missed write slots}}{224\text{ expected notifications}} \approx 14.5\% \quad \text{[INCONSISTENT UNITS]}$$

When numerator and denominator share the same unit:
* **In terms of Write Slots (nominal 0.5 s slots):**
  $$\text{Loss Ratio} = \frac{32 \text{ to } 33\text{ missed write slots}}{60\text{ expected write slots}} = 53.33\% \text{ to } 55.00\% \quad (\text{Mean: } 53.89\%)$$
* **In terms of Timeseries Rows (19 rows/slot):**
  $$\text{Loss Ratio} = \frac{32.33 \times 19\text{ missed rows}}{60 \times 19\text{ expected rows}} = \frac{614.3\text{ missed rows}}{1140\text{ expected rows}} = 53.89\%$$
* **In terms of Ingress Network Block Duty Cycle:**
  The port was blocked for ~20% of the 30 s window (~6 s total blockage). Because the OPC UA subscription uses a server-side queue size of 1, transient disconnection and TCP connection renegotiations cause intermediate value coalescing, resulting in a 53.89% reduction in distinct persisted snapshots.

### 3.3 Observed SQLite Insert Rates During Fault Sessions
Measured directly from the production database (`persistence/storage/aas_history.sqlite3`) over the exact execution intervals:

* **Baseline Pick-and-Place (Normal Operation):**
  - Observed flush frequency: $1.05\text{ flushes/s}$ (median inter-flush $\Delta t = 0.936\text{ s}$).
  - Timeseries insert rate: **20.03 rows/s**.
  - Total database insert rate (all tables): **93.82 rows/s**.
* **Connection Loss Session (123.5 s window, 5 faults of 10 s):**
  - Observed flush frequency: $0.96\text{ flushes/s}$ (median $\Delta t = 1.045\text{ s}$).
  - Timeseries insert rate: **18.30 rows/s** (2,261 rows in 123.5 s).
  - Total database insert rate: **85.74 rows/s**.
* **Intermittent Connectivity Session (128.9 s window, 3 faults of 30 s):**
  - Observed flush frequency: $0.92\text{ flushes/s}$ (median $\Delta t = 1.093\text{ s}$).
  - Timeseries insert rate: **17.55 rows/s** (2,261 rows in 128.9 s).
  - Total database insert rate: **82.19 rows/s**.
* **Gateway Restart Session (73.5 s window, 3 cold restarts of 10 s downtime):**
  - Observed flush frequency: $1.35\text{ flushes/s}$ (median $\Delta t = 0.776\text{ s}$).
  - Timeseries insert rate: **26.38 rows/s** (1,938 rows in 73.5 s).
  - Total database insert rate: **123.55 rows/s**.
