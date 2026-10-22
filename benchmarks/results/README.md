# Resultados Experimentais e Logs Brutos (Benchmark Results)

Este diretório contém os logs brutos e dados estruturados gerados durante as campanhas experimentais do artigo:
> **"An Asset Administration Shell Architecture with Dual Data Persistence for the Monitoring of an Industrial SCARA Robot"**

Para facilitar a reprodução, conferência e auditoria científica pelos revisores, os arquivos estão disponíveis tanto sob seus nomes de execução originais com carimbo de data/hora quanto através de arquivos com nomes autoexplicativos (`table6_*`, `table7_*`).

---

## 1. Mapeamento de Sessões Experimentais, Interfaces de Rede e Taxas de Inserção

A tabela a seguir consolida os ensaios das **Tabelas 5, 6 e 7** do artigo, detalhando a interface de rede utilizada, duração, total de linhas gravadas na tabela `timeseries` e as taxas observadas:

| Nome do Arquivo (Autoexplicativo / Original) | Cenário / Tabela Correspondente no Artigo | Interface de Rede Utilizada | Duração (s) | Total de Linhas (`timeseries` rows) | Taxa de Inserção Observada (rows/s) |
|---|---|---|:---:|:---:|:---:|
| [`table6_proposed_stack_latency_1h.json`](./table6_proposed_stack_latency_1h.json)<br>*(orig: `latency_benchmark_20260812_151547.json`)* | **Tabela 6 (Proposed Stack)** & **Tabela 5 (1h Telemetry Campaign)** — Pipeline completo: OPC UA $\rightarrow$ AAS $\rightarrow$ JSON atômico + SQLite | **Ethernet 100 Mbps (Robot OPC UA)**<br>*(Killer E2600, IP 192.168.0.200 $\rightarrow$ CS9 192.168.0.31:4880)* | 3.600,5 s | 68.400 linhas (banco completo: 1.587.108 linhas) | **20,03 rows/s** (`timeseries`)<br>*93,82 rows/s (total todas tabelas)* |
| [`table6_direct_opcua_baseline.json`](./table6_direct_opcua_baseline.json)<br>*(orig: `comparative_baseline_20260812_170007.json`)* | **Tabela 6 (Direct OPC UA)** — Baseline de cliente OPC UA direto puro sem camada AAS, sem persistência em disco | **Ethernet 100 Mbps (Robot OPC UA)**<br>*(Killer E2600, IP 192.168.0.200 $\rightarrow$ CS9 192.168.0.31:4880)* | 300,8 s | 0 linhas *(em memória; 2.263 notificações recebidas)* | **0,00 rows/s** *(N/A — apenas memória)* |
| [`table6_basyx_aas_server.json`](./table6_basyx_aas_server.json)<br>*(orig: `comparative_basyx_20260812_134147.json`)* | **Tabela 6 (Eclipse BaSyx AAS Server)** — Ingestão via requisições HTTP PUT em servidor AAS externo | **Ethernet 100 Mbps (Robot OPC UA)** +<br>**vEthernet 10 Gbps / Loopback 127.0.0.1** *(HTTP BaSyx :4001)* | 120,6 s | 927 atualizações *(BaSyx armazena apenas estado atual)* | **7,69 updates/s** *(taxa de publicação HTTP)* |
| [`table6_influxdb_tsdb.json`](./table6_influxdb_tsdb.json)<br>*(orig: `comparative_influxdb_20260812_134348.json`)* | **Tabela 6 (InfluxDB Database)** — Ingestão direta em TSDB dedicado (1 INSERT/notificação em WAL) | **Ethernet 100 Mbps (Robot OPC UA)** +<br>**vEthernet 10 Gbps / Local Storage** *(escrita WAL)* | 120,2 s | 919 linhas numéricas | **7,65 rows/s** |
| [`table6_sqlite_historical_queries.json`](./table6_sqlite_historical_queries.json)<br>*(orig: `db_benchmark_20260804_092003.json`)* | **Tabela 6 (Consultas históricas SQLite `last` e `range 500`)** & Seção 4.4 | **vEthernet 10 Gbps / Loopback 127.0.0.1** *(FastAPI/Flask REST API :5000)* | 1.000 queries por view | 1.587.108 linhas avaliadas | **20,03 rows/s** *(taxa sustentada de inserção)* |
| [`table7_fault_connection_loss.json`](./table7_fault_connection_loss.json)<br>*(orig: `fault_injection_disconnect_reconnect_20260811_162935.json`)* | **Tabela 7 (Connection Loss)** — Desconexão total via bloqueio de firewall na porta OPC UA (5 iterações × 10 s) | **Ethernet 100 Mbps (Robot OPC UA)**<br>*(bloqueio outbound porta 4880)* | 123,5 s | 2.261 linhas gravadas *(≈200 linhas / 0 de 20 slots gravados na falha, 100% perda)* | **18,30 rows/s** (`timeseries` sessão inteira)<br>*0,00 rows/s (janela de falha)* |
| [`table7_fault_intermittent_connectivity.json`](./table7_fault_intermittent_connectivity.json)<br>*(orig: `fault_injection_packet_loss_20260811_163406.json`)* | **Tabela 7 (Intermittent Connectivity)** — Conectividade degradada por ciclos rápidos (~20% duty cycle, 3 iterações × 30 s) | **Ethernet 100 Mbps (Robot OPC UA)**<br>*(ciclos de firewall 20ms block / 80ms open)* | 128,9 s | 2.261 linhas gravadas *(513–532 linhas observadas / 69–88 linhas perdidas de ≈601 esperadas, 11,5%–14,6% perda)* | **17,55 rows/s** (`timeseries` sessão inteira)<br>*17,52 rows/s (janela de falha)* |
| [`table7_fault_gateway_restart.json`](./table7_fault_gateway_restart.json)<br>*(orig: `fault_injection_gateway_restart_20260811_164906.json`)* | **Tabela 7 (Gateway Restart)** — Crash abrupto (SIGKILL) e reinício sob carga (3 iterações × 10 s downtime) | **Ethernet 100 Mbps (Robot OPC UA)**<br>*(interrupção do processo local)* | 73,5 s | 1.938 linhas gravadas *(≈200 linhas / 0 de 20 slots gravados na falha, 100% perda)* | **26,38 rows/s** (`timeseries` sessão inteira; burst de valores iniciais pós-reconexão)<br>*0,00 rows/s (janela de falha)* |

---

## 2. Descrição das Interfaces de Rede Físicas e Virtuais

O gateway de borda opera com três domínios de rede bem definidos:

1. **Rede Industrial do Robô (Física — Ethernet 100 Mbps):**
   * **Adaptador Físico:** `Killer E2600 Gigabit Ethernet Controller`
   * **Endereço MAC:** `B4-45-06-C3-4F-D1`
   * **IP Gateway / Sub-rede:** `192.168.0.200 / 24`
   * **Velocidade Negociada:** `100 Mbps` (100BASE-TX full-duplex com o transceiver industrial do controlador Stäubli CS9).
   * **Endpoint do Ativo:** `opc.tcp://192.168.0.31:4880/Staubli`
   * **Função:** Transporte determinístico da telemetria de 33 nós monitorados via subscription OPC UA (200 ms publishing interval).

2. **Rede de Supervisão da Fábrica (Sem Fio — Wi-Fi 173.3 Mbps):**
   * **Adaptador:** `Killer(R) Wi-Fi 6 AX1650i 160MHz Wireless Network Adapter`
   * **Endereço MAC:** `4E-CA-F7-0B-8D-62`
   * **IP / Velocidade:** `10.193.249.17` / `173.3 Mbps`
   * **Função:** Acesso remoto ao dashboard operacional pelos operadores e engenharia, desacoplado da rede de controle do robô.

3. **Rede Local do Gateway (Virtualizada / Interprocess — vEthernet 10 Gbps e Loopback):**
   * **Interfaces:** `vEthernet (Default Switch)` (`172.28.80.1`, 10 Gbps) e `Loopback Pseudo-Interface 1` (`127.0.0.1`).
   * **Função:** Comunicação interna entre o backend FastAPI/Flask (`:5000`), frontend React (`:5173`), persistência local SQLite e os testes comparativos com BaSyx (`:4001`).

---

## 3. Desambiguação de Unidades e Contabilidade de Falhas (Tabela 7)

Para assegurar consistência dimensional rigorosa e uso de uma única unidade (linhas de séries temporais):

### 3.1 Camadas Temporais do Sistema
* **Notificações OPC UA:** Taxa de chegada agregada de **7,46 Hz** (7,4599 notificações/s). Em 30 s de ensaio, são esperadas $\approx 224$ notificações.
* **Slots de Escrita do Banco (Write Slots):** Agendados a cada **0,5 s** ($T_w = 0,5\text{ s}$, teto nominal de 2,0 slots/s). Em regime contínuo, a taxa real de gravação observada é de **1,05 gravações/s**, demonstrando que aproximadamente metade dos intervalos nominais não possui novo lote a persistir.
* **Linhas na Tabela `timeseries`:** Cada lote gravado insere atomicamente **19 linhas** de métricas numéricas na tabela `timeseries`. A taxa de regime observada é $R_{\text{regime}} = 1,05 \times 19 \approx \mathbf{20,03\text{ linhas/s}}$.

### 3.2 Contabilidade de Perda Corrigida (Linhas Esperadas = Taxa de Regime $\times$ Duração da Falha)
Utilizando a taxa de regime observada ($R_{\text{regime}} = 20,03\text{ linhas/s}$) como denominador:

* **Conectividade Intermitente (30 s, ~20% de bloqueio):**
  - **Linhas Esperadas:** $20,03 \times 30 \approx \mathbf{601\text{ linhas}}$ (em 60 slots nominais).
  - **Linhas Observadas na Janela de Falha:** 27 a 28 lotes commitados $\times$ 19 linhas = **513 a 532 linhas** (média $\approx 527$ linhas, taxa observada $\approx 17,55\text{ linhas/s}$).
  - **Linhas Perdidas:** $601 - 532 = 69\text{ linhas}$ a $601 - 513 = 88\text{ linhas}$ (média $\approx 74\text{ linhas}$).
  - **Percentual de Perda:**
    $$\frac{69 \text{ a } 88 \text{ linhas perdidas}}{601 \text{ linhas esperadas}} = \mathbf{11,5\% \text{ a } 14,6\%} \quad (\text{Média: } \mathbf{12,3\%})$$
  - *Consistência Física:* O valor de 11,5%–14,6% fica estritamente abaixo do bloqueio de rede nominal de 20%, confirmando que a aquisição continuou de forma degradada e é coerente com os 14,5% reportados na Rodada 1, sem a necessidade de hipóteses causais especulativas.

* **Desconexão de Rede (10 s) e Reinício do Gateway (10 s downtime):**
  - **Linhas Esperadas:** $20,03 \times 10 \approx \mathbf{200\text{ linhas}}$ (em 20 slots nominais).
  - **Linhas Observadas na Janela de Falha:** **0 linhas** (0 lotes gravados).
  - **Linhas Perdidas:** **200 linhas (100% de perda)** durante o período de indisponibilidade ativa.

### 3.3 Definição das Janelas Temporais de Medição
* **Taxa de Linha de Base (Baseline pre-fault / steady-state):** Medida nos 60 s anteriores à injeção de falha (18,37 linhas/s) e durante o regime contínuo de operação (20,03 linhas/s).
* **Taxa na Janela de Falha:** Medida estritamente durante o período ativo de falha (0 linhas/s para desconexão e reinício; 17,55 linhas/s para intermitente).
* **Taxa da Sessão Inteira:** Medida ao longo de todo o arquivo de log (incluindo estabilização pré-falha e recuperação pós-falha):
  - *Connection loss (123,5 s):* 18,30 linhas/s (reflete a operação normal antes e depois das 5 falhas de 10 s).
  - *Intermittent connectivity (128,9 s):* 17,55 linhas/s.
  - *Gateway restart (73,5 s):* 26,38 linhas/s. Esta taxa fica acima do regime porque, ao restabelecer a subscription após o reinício, o servidor OPC UA envia imediatamente o valor inicial de todos os 33 nós monitorados, gerando um surto transitório (*burst*) de lotes logo após a reconexão.
* **Indisponibilidade Total (Gateway Restart):** Os 10,76 s médios correspondem aos 10,0 s de indisponibilidade programada mais 0,76 s de atraso de *cold restart* e reconexão OPC UA.

---

## 4. Manifesto Completo

Para detalhes linha a linha de cada amostra, percentis e decomposição de latência, consulte também:
- [`BENCHMARK_SESSIONS_MANIFEST.md`](./BENCHMARK_SESSIONS_MANIFEST.md)
- [`benchmark_sessions_manifest.json`](./benchmark_sessions_manifest.json)
