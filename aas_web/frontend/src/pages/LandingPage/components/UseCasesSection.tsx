import styles from '../LandingPage.module.css';

export default function UseCasesSection() {
    const useCases = [
        {
            title: 'Assembly Line',
            description: 'High-speed pick and place operations for electronics assembly.',
            stat: '99.9%',
            statLabel: 'Accuracy'
        },
        {
            title: 'Quality Control',
            description: 'Automated visual inspection and sorting of defective parts.',
            stat: '< 0.5s',
            statLabel: 'Cycle Time'
        },
        {
            title: 'Packaging',
            description: 'Efficient boxing and palletizing of finished goods.',
            stat: '24/7',
            statLabel: 'Operation'
        }
    ];

    return (
        <section className={styles.useCasesSection}>
            <div className={styles.container}>
                <h2 className={styles.sectionTitle}>Industrial Applications</h2>
                <div className={styles.grid}>
                    {useCases.map((useCase, index) => (
                        <div key={index} className={styles.useCaseCard}>
                            <div className={styles.useCaseContent}>
                                <h3 className={styles.cardTitle}>{useCase.title}</h3>
                                <p className={styles.cardDescription}>{useCase.description}</p>
                            </div>
                            <div className={styles.useCaseStat}>
                                <span className={styles.statValue}>{useCase.stat}</span>
                                <span className={styles.statLabel}>{useCase.statLabel}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
