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

## 3. Metric Units & Corrected Fault Accounting (Table 7)

### 3.1 Clarification of Temporal Frequencies & Units
The system operates across three distinct time bases and data representations:

1. **OPC UA Data-Change Notification Stream:**
   * Generated asynchronously by the Stäubli embedded OPC UA server across 33 monitored nodes.
   * Aggregate observed arrival rate: **7.46 Hz** (7.4599 notifications/s).
   * In a 10 s fault duration: $10\text{ s} \times 7.4599\text{ Hz} \approx 74.6$ expected incoming notifications.
   * In a 30 s fault duration: $30\text{ s} \times 7.4599\text{ Hz} \approx 223.8$ (~224) expected incoming notifications.

2. **Persistence Flush Cycle (Write Slots):**
   * Scheduled by `_writer_task` in `client_asyncua.py` and monitored by `SnapshotMonitor` in `fault_injection_benchmark.py`.
   * Nominal interval: **0.5 s** ($T_w = 0.5\text{ s}$, a ceiling of 2.0 write slots/s).
   * In practice, the client only flushes to SQLite when values change. The observed steady-state rate of **1.05 flushes/s** shows that approximately half of the nominal 0.5 s intervals do not have a new batch to record.
   * In a 10 s fault duration: 20 nominal write slots.
   * In a 30 s fault duration: 60 nominal write slots.

3. **SQLite Relational Table Rows (`timeseries`):**
   * Each executed flush commits an atomic transaction inserting **19 rows** into the `timeseries` table (one for each actively monitored numeric telemetry metric).
   * **Observed Steady-State Insertion Rate ($R_{\text{regime}}$):** **20.03 rows/s** (1.05 flushes/s $\times$ 19 rows).
   * Across all tables (including normalized snapshot key-values and JSON blobs): **93.82 rows/s**.

### 3.2 Corrected Loss Accounting (Expected Rows = Baseline Rate $\times$ Fault Duration)
To use a single unit across all calculations, expected data rows are derived from the observed steady-state insertion rate ($R_{\text{regime}} = 20.03\text{ rows/s}$) multiplied by the fault duration:

* **Intermittent Connectivity (30 s fault duration, ~20% port block):**
  - **Expected `timeseries` Rows:** $R_{\text{regime}} \times 30\text{ s} = 20.03 \times 30 \approx \mathbf{601\text{ rows}}$ (across 60 nominal 0.5 s slots).
  - **Observed Rows in Fault Window:** Across the 3 iterations, 27 to 28 batches were committed, yielding **513 to 532 rows** (mean $\approx 527$ rows, observed rate in fault window $\approx 17.55\text{ rows/s}$).
  - **Missed Rows:** $601 - 532 = 69\text{ rows}$ to $601 - 513 = 88\text{ rows}$ (mean $\approx 74\text{ rows}$).
  - **Loss Ratio:**
    $$\text{Loss Ratio} = \frac{69 \text{ to } 88\text{ missed rows}}{601\text{ expected rows}} = \mathbf{11.5\% \text{ to } 14.6\%} \quad (\text{Mean: } \mathbf{12.3\%})$$
  - *Observation:* This loss of 11.5%–14.6% remains strictly below the 20% network blockage window (and is consistent with the ~14.5% previously cited), as acquisition continued in degraded form without requiring unverified causal assumptions.

* **Connection Loss (10 s fault duration):**
  - **Expected `timeseries` Rows:** $R_{\text{regime}} \times 10\text{ s} = 20.03 \times 10 \approx \mathbf{200\text{ rows}}$.
  - **Observed Rows in Fault Window:** **0 rows** (0 of 20 nominal slots committed).
  - **Missed Rows:** **200 rows (100% loss)** during the outage.

* **Gateway Restart (10 s downtime):**
  - **Expected `timeseries` Rows:** $R_{\text{regime}} \times 10\text{ s} = 20.03 \times 10 \approx \mathbf{200\text{ rows}}$.
  - **Observed Rows in Fault Window:** **0 rows** (0 of 20 nominal slots committed).
  - **Missed Rows:** **200 rows (100% loss)** during downtime.

### 3.3 Definition of Measurement Windows and Session Rates
* **Baseline Insert Rate (60 s pre-fault window / steady-state):** Measured over 60 s immediately preceding fault injection (18.37 rows/s) and during steady-state continuous pick-and-place (20.03 rows/s, 1.05 flushes/s).
* **Fault Window Insert Rate:** Measured strictly during the active fault duration (0 rows/s for connection loss and gateway restart; 17.55 rows/s for intermittent connectivity).
* **Entire Session Rate:** Measured over the complete multi-trial session including pre-fault stabilization and post-fault recovery intervals:
  - *Connection loss session (123.5 s total, 5 faults):* 18.30 rows/s (2,261 rows, 119 flushes).
  - *Intermittent connectivity session (128.9 s total, 3 faults):* 17.55 rows/s (2,261 rows, 119 flushes).
  - *Gateway restart session (73.5 s total, 3 faults):* 26.38 rows/s (1,938 rows, 99 flushes). The session rate rises above steady-state baseline because upon subscription re-creation, the OPC UA server immediately publishes initial values for all 33 monitored nodes, generating a transient burst of write transactions during the initial recovery interval.
* **Total Unavailability Definition:** Total unavailability (10.76 s for gateway restart) is defined as the 10.0 s process downtime plus the 0.76 s cold restart and reconnection delay.

