import { Html } from '@react-three/drei';
import { FaChartLine, FaThermometerHalf, FaClock, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';
import { mockKPIs, mockChartData } from '../mockData';
import { useState } from 'react';

// Recharts for mini visualizations
import { LineChart, Line, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#e94f88', '#2a2d3a'];

export default function DashboardCards3D() {
    const [hoveredCard, setHoveredCard] = useState<string | null>(null);

    const cardStyle = (id: string) => ({
        width: '240px',
        background: 'rgba(23, 23, 30, 0.85)',
        backdropFilter: 'blur(12px)',
        borderRadius: '16px',
        padding: '20px',
        border: hoveredCard === id ? '1px solid #e94f88' : '1px solid rgba(255, 255, 255, 0.1)',
        boxShadow: hoveredCard === id ? '0 0 30px rgba(233, 79, 136, 0.2)' : '0 10px 30px rgba(0, 0, 0, 0.5)',
        color: 'white',
        transition: 'all 0.3s ease',
        cursor: 'default',
        userSelect: 'none' as const,
    });

    return (
        <group position={[40, 20, 0]} rotation={[0, -0.2, 0]}>
            {/* Main Production Card */}
            <Html
                transform
                position={[10, 20, -5]}
                rotation={[0, 0, 0]}
                scale={5}
                occlude="blending"
            >
                <div
                    style={cardStyle('production')}
                    onMouseEnter={() => setHoveredCard('production')}
                    onMouseLeave={() => setHoveredCard(null)}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{ padding: '8px', background: 'rgba(233, 79, 136, 0.1)', borderRadius: '8px', color: '#e94f88' }}>
                                <FaChartLine />
                            </div>
                            <span style={{ fontSize: '14px', fontWeight: 600, color: '#a0a0a0' }}>Production</span>
                        </div>
                        <span style={{ color: '#4caf50', fontSize: '12px', fontWeight: 600 }}>{mockKPIs.productionRate.trend}</span>
                    </div>

                    <div style={{ marginBottom: '15px' }}>
                        <span style={{ fontSize: '32px', fontWeight: 700 }}>{mockKPIs.productionRate.value}</span>
                        <span style={{ fontSize: '14px', color: '#666', marginLeft: '5px' }}>{mockKPIs.productionRate.unit}</span>
                    </div>

                    <div style={{ height: '60px', width: '100%' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={mockChartData.production}>
                                <Line
                                    type="monotone"
                                    dataKey="value"
                                    stroke="#e94f88"
                                    strokeWidth={2}
                                    dot={false}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </Html>

            {/* Efficiency Card */}
            <Html
                transform
                position={[10, -5, 5]}
                rotation={[0, 0.1, 0]}
                scale={5}
                occlude="blending"
            >
                <div
                    style={cardStyle('efficiency')}
                    onMouseEnter={() => setHoveredCard('efficiency')}
                    onMouseLeave={() => setHoveredCard(null)}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{ padding: '8px', background: 'rgba(233, 79, 136, 0.1)', borderRadius: '8px', color: '#e94f88' }}>
                                <FaCheckCircle />
                            </div>
                            <span style={{ fontSize: '14px', fontWeight: 600, color: '#a0a0a0' }}>Efficiency</span>
                        </div>
                        <span style={{ color: '#4caf50', fontSize: '12px', fontWeight: 600 }}>{mockKPIs.efficiency.trend}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                        <div style={{ position: 'relative', width: '80px', height: '80px' }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={mockChartData.efficiency}
                                        innerRadius={25}
                                        outerRadius={35}
                                        paddingAngle={5}
                                        dataKey="value"
                                        stroke="none"
                                    >
                                        {mockChartData.efficiency.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={index === 0 ? '#e94f88' : '#333'} />
                                        ))}
                                    </Pie>
                                </PieChart>
                            </ResponsiveContainer>
                            <div style={{
                                position: 'absolute',
                                top: '50%',
                                left: '50%',
                                transform: 'translate(-50%, -50%)',
                                fontSize: '12px',
                                fontWeight: 700
                            }}>
                                {mockKPIs.efficiency.value}%
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '12px', color: '#a0a0a0', marginBottom: '4px' }}>OEE Score</div>
                            <div style={{ fontSize: '18px', fontWeight: 700 }}>Excellent</div>
                        </div>
                    </div>
                </div>
            </Html>

            {/* Status Indicators Card */}
            <Html
                transform
                position={[-20, 5, 0]}
                rotation={[0, 0.1, 0]}
                scale={5}
                occlude="blending"
            >
                <div
                    style={{ ...cardStyle('status'), width: '240px' }}
                    onMouseEnter={() => setHoveredCard('status')}
                    onMouseLeave={() => setHoveredCard(null)}
                >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <FaThermometerHalf style={{ color: '#e94f88' }} />
                                <span style={{ fontSize: '14px', color: '#ccc' }}>Temp</span>
                            </div>
                            <span style={{ fontWeight: 600 }}>{mockKPIs.temperature.value}{mockKPIs.temperature.unit}</span>
                        </div>

                        <div style={{ width: '100%', height: '4px', background: '#333', borderRadius: '2px' }}>
                            <div style={{ width: '45%', height: '100%', background: '#4caf50', borderRadius: '2px' }} />
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <FaClock style={{ color: '#e94f88' }} />
                                <span style={{ fontSize: '14px', color: '#ccc' }}>Cycle</span>
                            </div>
                            <span style={{ fontWeight: 600 }}>{mockKPIs.cycleTime.value}{mockKPIs.cycleTime.unit}</span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '5px', padding: '8px', background: 'rgba(76, 175, 80, 0.1)', borderRadius: '6px' }}>
                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#4caf50' }} />
                            <span style={{ fontSize: '12px', color: '#4caf50', fontWeight: 600 }}>SYSTEM OPTIMAL</span>
                        </div>
                    </div>
                </div>
            </Html>
        </group>
    );
}
