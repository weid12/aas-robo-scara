import React, { useState } from 'react';
import styles from './EmergencyStopButton.module.css';

export interface EmergencyStopButtonProps {
    /** Callback fired when the button state changes */
    onStateChange?: (armed: boolean) => void;
    /** Initial state of the button */
    initialState?: boolean;
    /** Additional CSS class */
    className?: string;
}

/**
 * Emergency Stop Button Component
 * 
 * A toggle-style emergency stop button that mimics industrial automation behavior.
 * - Click once to arm (pressed state with pink glow)
 * - Click again to disarm (raised state)
 */
const EmergencyStopButton: React.FC<EmergencyStopButtonProps> = ({
    onStateChange,
    initialState = false,
    className = ''
}) => {
    const [isArmed, setIsArmed] = useState(initialState);

    const handleClick = () => {
        const newState = !isArmed;
        setIsArmed(newState);
        onStateChange?.(newState);
    };

    return (
        <div className={`${styles.container} ${className}`}>
            <div className={styles.housing}>
                <div
                    className={styles.statusIndicator + (isArmed ? ` ${styles.armed}` : '')}
                    title={isArmed ? 'Armed' : 'Disarmed'}
                />
                <button
                    className={`${styles.button} ${isArmed ? styles.armed : styles.disarmed}`}
                    onClick={handleClick}
                    aria-label={isArmed ? 'Emergency Stop Armed' : 'Emergency Stop Disarmed'}
                    aria-pressed={isArmed}
                />
            </div>
            <div className={`${styles.label} ${isArmed ? styles.armed : ''}`}>
                {isArmed ? 'ARMED' : 'DISARMED'}
            </div>
        </div>
    );
};

export default EmergencyStopButton;
