import { FaChartPie, FaRobot, FaHistory, FaBell } from 'react-icons/fa';
import styles from '../LandingPage.module.css';

export default function FeaturesSection() {
    const features = [
        {
            icon: <FaChartPie />,
            title: 'Interactive Dashboard',
            description: 'Visualize KPIs, production rates, and efficiency metrics in real-time.'
        },
        {
            icon: <FaRobot />,
            title: 'Digital Twin',
            description: '3D visualization of the robot state synchronized with physical hardware.'
        },
        {
            icon: <FaHistory />,
            title: 'Event Logging',
            description: 'Comprehensive history of operations, errors, and system events.'
        },
        {
            icon: <FaBell />,
            title: 'Smart Alerts',
            description: 'Instant notifications for anomalies and maintenance requirements.'
        }
    ];

    return (
        <section className={styles.featuresSection}>
            <div className={styles.container}>
                <h2 className={styles.sectionTitle}>Powerful Features</h2>
                <div className={styles.grid}>
                    {features.map((feature, index) => (
                        <div key={index} className={styles.card}>
                            <div className={styles.iconWrapper}>{feature.icon}</div>
                            <h3 className={styles.cardTitle}>{feature.title}</h3>
                            <p className={styles.cardDescription}>{feature.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
