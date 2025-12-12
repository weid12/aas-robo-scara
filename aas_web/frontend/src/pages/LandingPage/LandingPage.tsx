import { FC, Suspense, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import styles from './LandingPage.module.css';
import HeroScene3D from './components/HeroScene3D';
import Aurora from './Aurora';
import { TrustedBySection } from './TrustedBySection';
import BenefitsSection from './BenefitsSection';
import KeyFeaturesSection from './KeyFeaturesSection';
import SystemArchitectureSection from './SystemArchitectureSection';
import IndustrialUseCasesSection from './IndustrialUseCasesSection';
import Footer from './Footer';

const LandingPage: FC = () => {
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        const checkMobile = () => setIsMobile(window.innerWidth < 768);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    return (
        <motion.div
            className={styles.container}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
        >
            <section className={styles.hero}>
                {/* 3D Scene Background */}
                <div className={styles.sceneContainer}>
                    {!isMobile ? (
                        <Suspense fallback={<div className={styles.loader}>Loading 3D Scene...</div>}>
                            <HeroScene3D />
                        </Suspense>
                    ) : (
                        <Aurora
                            colorStops={["#d44478", "#7c6ab4ff", "#a268a6"]}
                            blend={0.5}
                            amplitude={1.0}
                            speed={0.5}
                        />
                    )}
                </div>

                {/* Hero Content Overlay */}
                <div className={styles.heroContent}>
                    <h1 className={styles.title}>
                        AAS Scara Robot<br />Control System
                    </h1>
                    <p className={styles.subtitle}>
                        Experience the future of industrial automation with real-time monitoring,
                        precise control, and comprehensive data analytics.
                    </p>
                    <Link to="/login" className={styles.ctaButton}>
                        Access System
                    </Link>
                </div>
            </section>

            <motion.div
                initial={{ opacity: 0, y: 60 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, margin: "-100px" }}
                transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
                <BenefitsSection />
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 60 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, margin: "-100px" }}
                transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
                <KeyFeaturesSection />
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 60 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, margin: "-100px" }}
                transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
                <SystemArchitectureSection />
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 60 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, margin: "-100px" }}
                transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
                <IndustrialUseCasesSection />
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 60 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, margin: "-100px" }}
                transition={{ duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
                <TrustedBySection />
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: false, margin: "-50px" }}
                transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
                <Footer />
            </motion.div>
        </motion.div>
    );
};

export default LandingPage;
