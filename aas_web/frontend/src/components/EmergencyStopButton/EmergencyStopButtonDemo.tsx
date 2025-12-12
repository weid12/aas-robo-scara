import React, { useState } from 'react';
import EmergencyStopButton from './EmergencyStopButton';

/**
 * Demo page for the EmergencyStopButton component
 * 
 * This standalone page showcases the button's toggle behavior
 * and visual states without integrating it into the main application.
 */
const EmergencyStopButtonDemo: React.FC = () => {
    const [state, setState] = useState(false);
    const [clickCount, setClickCount] = useState(0);

    const handleStateChange = (armed: boolean) => {
        setState(armed);
        setClickCount(prev => prev + 1);
    };

    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(145deg, #0f111a, #1a1d2e)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '3rem',
            padding: '2rem',
            fontFamily: '"Barlow", "Roboto", "Segoe UI", sans-serif',
            color: '#f4f4f8'
        }}>
            <div style={{
                textAlign: 'center',
                marginBottom: '2rem'
            }}>
                <h1 style={{
                    fontSize: '2.5rem',
                    fontWeight: 700,
                    background: 'linear-gradient(135deg, #e94f88, #f06292)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                    marginBottom: '1rem'
                }}>
                    Emergency Stop Button Demo
                </h1>
                <p style={{
                    fontSize: '1.1rem',
                    color: '#a0a7c7',
                    maxWidth: '600px',
                    margin: '0 auto'
                }}>
                    Click the button to toggle between armed and disarmed states.
                    The button mimics industrial automation emergency stop behavior.
                </p>
            </div>

            <EmergencyStopButton
                onStateChange={handleStateChange}
                initialState={false}
            />

            <div style={{
                background: 'rgba(30, 30, 42, 0.6)',
                border: '1px solid rgba(233, 79, 136, 0.2)',
                borderRadius: '12px',
                padding: '2rem',
                minWidth: '400px',
                textAlign: 'center'
            }}>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '1.5rem',
                    marginBottom: '1.5rem'
                }}>
                    <div>
                        <div style={{
                            fontSize: '0.85rem',
                            color: '#a0a7c7',
                            textTransform: 'uppercase',
                            letterSpacing: '1px',
                            marginBottom: '0.5rem'
                        }}>
                            Current State
                        </div>
                        <div style={{
                            fontSize: '1.5rem',
                            fontWeight: 700,
                            color: state ? '#e94f88' : '#4caf50'
                        }}>
                            {state ? 'ARMED' : 'DISARMED'}
                        </div>
                    </div>
                    <div>
                        <div style={{
                            fontSize: '0.85rem',
                            color: '#a0a7c7',
                            textTransform: 'uppercase',
                            letterSpacing: '1px',
                            marginBottom: '0.5rem'
                        }}>
                            Click Count
                        </div>
                        <div style={{
                            fontSize: '1.5rem',
                            fontWeight: 700,
                            color: '#82b1ff'
                        }}>
                            {clickCount}
                        </div>
                    </div>
                </div>

                <div style={{
                    padding: '1rem',
                    background: state
                        ? 'rgba(233, 79, 136, 0.1)'
                        : 'rgba(76, 175, 80, 0.1)',
                    border: `1px solid ${state ? 'rgba(233, 79, 136, 0.3)' : 'rgba(76, 175, 80, 0.3)'}`,
                    borderRadius: '8px',
                    fontSize: '0.9rem',
                    color: '#e0e0e0'
                }}>
                    {state ? (
                        <>
                            <strong style={{ color: '#e94f88' }}>⚠️ Emergency Stop Armed</strong>
                            <br />
                            The button is in pressed state with pink glow effect.
                        </>
                    ) : (
                        <>
                            <strong style={{ color: '#4caf50' }}>✓ System Normal</strong>
                            <br />
                            The button is in raised state, ready to be activated.
                        </>
                    )}
                </div>
            </div>

            <div style={{
                fontSize: '0.85rem',
                color: '#666',
                textAlign: 'center',
                maxWidth: '500px'
            }}>
                <p style={{ margin: '0.5rem 0' }}>
                    <strong>Disarmed:</strong> Button raised, green indicator, normal appearance
                </p>
                <p style={{ margin: '0.5rem 0' }}>
                    <strong>Armed:</strong> Button pressed, pink indicator, glowing effect
                </p>
            </div>
        </div>
    );
};

export default EmergencyStopButtonDemo;
