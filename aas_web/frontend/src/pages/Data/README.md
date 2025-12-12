# Dashboard de Dados do Robô SCARA

## Visão Geral

Esta página implementa um dashboard completo e intuitivo para visualização dos dados do robô SCARA armazenados no banco de dados SQLite. O dashboard oferece visualizações em tempo real através de gráficos, tabelas e cards de estatísticas.

## Funcionalidades

### 1. **Cards de Estatísticas Gerais**
- Total de registros no banco de dados
- Número de métricas ativas
- Lista de submodelos disponíveis
- Timestamp da última atualização

### 2. **Gráfico de Série Temporal**
- Visualização interativa de qualquer métrica disponível
- Seletor dropdown para escolher a métrica desejada
- Mini-cards mostrando estatísticas do gráfico:
  - Valor atual
  - Valor mínimo
  - Valor máximo
  - Valor médio
- Renderização otimizada usando Canvas API
- Suporte para até 300 pontos de dados

### 3. **Tabela de Valores Recentes**
- Exibe os 20 valores mais recentes de todas as métricas
- Colunas ordenáveis (clique no cabeçalho)
- Formatação de timestamps em português
- Scroll vertical e horizontal

### 4. **Auto-Refresh**
- Toggle para habilitar/desabilitar atualização automática
- Série temporal: atualiza a cada 5 segundos
- Valores recentes: atualiza a cada 3 segundos
- Estatísticas gerais: carregadas uma vez na inicialização

## Componentes Criados

### `LineChart.jsx`
Componente de gráfico de linha usando Canvas API nativa do navegador.

**Props:**
- `data`: Array de objetos `{t: string, v: number}` (timestamp e valor)
- `title`: Título do gráfico
- `unit`: Unidade de medida (opcional)
- `color`: Cor da linha (padrão: `#ff7746`)

**Características:**
- Renderização de alta performance
- Grid horizontal com labels
- Eixo X com timestamps formatados
- Pontos visíveis quando há poucos dados (< 50)
- Responsivo (adapta ao tamanho do container)

### `DataCard.jsx`
Card para exibir métricas e estatísticas.

**Props:**
- `title`: Título do card
- `value`: Valor principal
- `unit`: Unidade (opcional)
- `subtitle`: Texto secundário (opcional)
- `icon`: Emoji ou ícone (opcional)
- `trend`: Percentual de tendência (opcional)
- `color`: Cor de destaque

**Características:**
- Animação de hover
- Suporte para indicador de tendência (↑/↓)
- Design glassmorphism

### `DataTable.jsx`
Tabela de dados com ordenação.

**Props:**
- `columns`: Array de definições de colunas
  - `key`: Chave do dado
  - `label`: Label da coluna
  - `sortable`: Se permite ordenação (padrão: true)
  - `render`: Função customizada de renderização (opcional)
- `data`: Array de objetos com os dados
- `maxHeight`: Altura máxima (padrão: `500px`)

**Características:**
- Ordenação por clique no cabeçalho
- Scroll com scrollbar customizada
- Header fixo (sticky)
- Hover em linhas

## API Endpoints Utilizados

### `GET /api/data/stats`
Retorna estatísticas gerais do banco de dados.

**Resposta:**
```json
{
  "total_records": 12345,
  "submodels": ["OperationalData", "RuntimeDiagnostics"],
  "date_range": {
    "first": "2024-01-01T00:00:00Z",
    "last": "2024-01-02T12:00:00Z"
  },
  "metrics_count": 42
}
```

### `GET /api/data/paths`
Lista todos os caminhos de métricas disponíveis.

**Resposta:**
```json
{
  "paths": [
    {"submodel": "OperationalData", "path": "OperationalData.JointPosition1"},
    {"submodel": "OperationalData", "path": "OperationalData.JointPosition2"}
  ],
  "count": 2
}
```

### `GET /api/data/timeseries`
Retorna série temporal de uma métrica específica.

**Query Params:**
- `submodel`: Nome do submodelo
- `path`: Caminho do elemento
- `limit`: Número máximo de pontos (padrão: 200, máx: 2000)

**Resposta:**
```json
{
  "rows": [
    {"t": "2024-01-01T12:00:00Z", "v": 123.45},
    {"t": "2024-01-01T12:00:05Z", "v": 124.12}
  ],
  "submodel": "OperationalData",
  "path": "OperationalData.JointPosition1",
  "count": 2
}
```

### `GET /api/data/latest`
Retorna os valores mais recentes de todas as métricas.

**Resposta:**
```json
{
  "metrics": [
    {
      "submodel": "OperationalData",
      "path": "OperationalData.JointPosition1",
      "value": 123.45,
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "count": 1
}
```

## Estrutura de Arquivos

```
aas_web_template/frontend/src/
├── pages/
│   └── Data/
│       ├── Data.jsx              # Página principal do dashboard
│       ├── Data.module.css       # Estilos da página
│       └── README.md             # Esta documentação
├── components/
│   ├── Charts/
│   │   ├── LineChart.jsx         # Componente de gráfico
│   │   └── LineChart.module.css
│   ├── DataCard/
│   │   ├── DataCard.jsx          # Card de estatísticas
│   │   └── DataCard.module.css
│   └── DataTable/
│       ├── DataTable.jsx         # Tabela de dados
│       └── DataTable.module.css
```

## Backend

```
aas_web_template/backend/
├── app.py                        # Aplicação Flask principal
└── data_routes.py                # Rotas de API para dados
```

## Como Usar

### 1. Iniciar o Backend
```bash
cd aas_web_template/backend
python app.py
```

### 2. Iniciar o Frontend
```bash
cd aas_web_template/frontend
npm run dev
```

### 3. Acessar o Dashboard
Navegue para `http://localhost:5173/data` (ou a porta configurada)

## Requisitos

### Backend
- Python 3.8+
- Flask
- flask-cors
- SQLite3 (incluído no Python)

### Frontend
- React 18+
- Vite
- PropTypes

## Configuração

### Variáveis de Ambiente (Frontend)

Crie um arquivo `.env` em `aas_web_template/frontend/`:

```env
VITE_API_BASE=http://localhost:5000
```

### Banco de Dados

O dashboard espera encontrar o banco de dados em:
```
data/aas_history.sqlite3
```

Certifique-se de que o cliente OPC UA está rodando e populando o banco de dados.

## Personalização

### Cores
As cores podem ser ajustadas nos arquivos CSS de cada componente. As cores principais são:
- Primária: `#ff7746` (laranja)
- Sucesso: `#22c55e` (verde)
- Info: `#3b82f6` (azul)
- Roxo: `#a855f7`
- Erro: `#ef4444` (vermelho)

### Intervalos de Refresh
Ajuste os intervalos em `Data.jsx`:
```javascript
// Série temporal (linha 88)
const interval = setInterval(fetchTimeseries, 5000); // 5 segundos

// Valores recentes (linha 107)
const interval = setInterval(fetchLatest, 3000); // 3 segundos
```

### Limite de Dados
Ajuste o limite de pontos no gráfico (linha 75):
```javascript
&limit=300  // Altere para o valor desejado (máx: 2000)
```

## Troubleshooting

### "Database not available"
- Verifique se o arquivo `data/aas_history.sqlite3` existe
- Certifique-se de que o cliente OPC UA está rodando
- Verifique as permissões do arquivo

### Gráfico não aparece
- Abra o console do navegador (F12) e verifique erros
- Confirme que a API está retornando dados
- Verifique se há dados no banco para a métrica selecionada

### Auto-refresh não funciona
- Verifique se o toggle está habilitado
- Confirme que o backend está acessível
- Verifique o console para erros de CORS

## Melhorias Futuras

- [ ] Adicionar zoom e pan no gráfico
- [ ] Exportar dados para CSV/Excel
- [ ] Filtros de data/hora personalizados
- [ ] Múltiplos gráficos simultâneos
- [ ] Alertas e notificações
- [ ] Comparação entre métricas
- [ ] Gráficos de pizza e barras
- [ ] Dashboard customizável (drag & drop)

