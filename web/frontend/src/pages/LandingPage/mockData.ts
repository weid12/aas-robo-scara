// Mock data for landing page KPI dashboard cards

export const mockKPIs = {
    productionRate: {
        value: 156,
        unit: 'units/hr',
        label: 'Production Rate',
        trend: '+12%',
        status: 'operational'
    },
    uptime: {
        value: 98.7,
        unit: '%',
        label: 'Uptime',
        trend: '+2.3%',
        status: 'operational'
    },
    cycleTime: {
        value: 4.2,
        unit: 's',
        label: 'Cycle Time',
        trend: '-0.3s',
        status: 'optimal'
    },
    temperature: {
        value: 35,
        unit: '°C',
        label: 'Motor Temp',
        trend: 'stable',
        status: 'normal'
    },
    efficiency: {
        value: 94.5,
        unit: '%',
        label: 'OEE',
        trend: '+5%',
        status: 'operational'
    }
};

export const mockChartData = {
    production: [
        { time: '00:00', value: 120 },
        { time: '04:00', value: 145 },
        { time: '08:00', value: 160 },
        { time: '12:00', value: 155 },
        { time: '16:00', value: 170 },
        { time: '20:00', value: 156 },
    ],
    efficiency: [
        { name: 'Performance', value: 96 },
        { name: 'Quality', value: 98 },
        { name: 'Availability', value: 94 },
    ]
};

export const robotStatus = {
    state: 'Running',
    mode: 'Automatic',
    joints: {
        j1: 45,
        j2: -30,
        j3: 120,
        j4: 0
    }
};
