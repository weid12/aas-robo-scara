import { FaMicrochip, FaNetworkWired, FaShieldAlt, FaCogs } from 'react-icons/fa';
import styles from '../LandingPage.module.css';

export default function BenefitsSection() {
    const benefits = [
        {
            icon: <FaMicrochip />,
            title: 'Industry 4.0 Ready',
            description: 'Fully compliant with Asset Administration Shell (AAS) standards for interoperability.'
        },
        {
            icon: <FaNetworkWired />,
            title: 'Real-time Connectivity',
            description: 'Low-latency communication protocol for instant feedback and control.'
        },
        {
            icon: <FaShieldAlt />,
            title: 'Enhanced Safety',
            description: 'Integrated emergency stop systems and predictive maintenance alerts.'
        },
        {
            icon: <FaCogs />,
            title: 'Smart Automation',
            description: 'Advanced control algorithms for precise and repeatable robotic movements.'
        }
    ];

    return (
        <section className={styles.benefitsSection}>
            <div className={styles.container}>
                <h2 className={styles.sectionTitle}>Why Choose AAS Scara?</h2>
                <div className={styles.grid}>
                    {benefits.map((benefit, index) => (
                        <div key={index} className={styles.card}>
                            <div className={styles.iconWrapper}>{benefit.icon}</div>
                            <h3 className={styles.cardTitle}>{benefit.title}</h3>
                            <p className={styles.cardDescription}>{benefit.description}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
