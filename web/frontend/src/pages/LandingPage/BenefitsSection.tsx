import React from 'react';
import { FiActivity, FiDatabase, FiCpu, FiLayers } from 'react-icons/fi';

interface Benefit {
    id: number;
    title: string;
    description: string;
    metric: string;
    icon: React.ElementType;
}

const benefitsData: Benefit[] = [
    {
        id: 1,
        title: 'Real-Time Monitoring',
        description: 'Continuous tracking of robot state with low latency.',
        metric: 'Latency < 50ms',
        icon: FiActivity,
    },
    {
        id: 2,
        title: 'Historical Traceability',
        description: 'Full storage of events and process variables.',
        metric: '100% Coverage',
        icon: FiDatabase,
    },
    {
        id: 3,
        title: 'Diagnostics Improvement',
        description: 'Fast identification of faults and operational anomalies.',
        metric: '40% Reduction',
        icon: FiCpu,
    },
    {
        id: 4,
        title: 'AAS Standardization',
        description: 'Guaranteed interoperability through the Asset Administration Shell.',
        metric: 'Full Interoperability',
        icon: FiLayers,
    },
];

const BenefitsSection: React.FC = () => {
    return (
        <section className="w-full py-20 bg-[#0f1115] text-white">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="mb-12 text-center">
                    <span className="text-[#e94f88] font-semibold text-[42px]">
                        Platform Benefits
                    </span>
                    <br />
                    <span className="text-gray-400 text-[25px]">
                        Power your operations with cutting-edge technologies for Digital Twin and Industry 4.0.
                    </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {benefitsData.map((benefit) => (
                        <div
                            key={benefit.id}
                            className="group relative p-6 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm hover:border-[#e94f88]/50 transition-all duration-300 hover:-translate-y-1"
                        >
                            <div className="absolute inset-0 bg-gradient-to-br from-[#e94f88]/0 to-[#e94f88]/5 opacity-0 group-hover:opacity-100 rounded-xl transition-opacity duration-300" />

                            <div className="relative z-10 flex flex-col h-full">
                                <div className="mb-4 inline-flex items-center justify-center w-12 h-12 rounded-lg bg-[#e94f88]/10 text-[#e94f88] group-hover:bg-[#e94f88] group-hover:text-white transition-colors duration-300">
                                    <benefit.icon className="w-6 h-6" />
                                </div>

                                <h3 className="text-lg font-semibold mb-2 text-white group-hover:text-[#e94f88] transition-colors">
                                    {benefit.title}
                                </h3>

                                <p className="text-sm text-gray-400 mb-6 flex-grow">
                                    {benefit.description}
                                </p>

                                <div className="pt-4 border-t border-white/10">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Impact
                                        </span>
                                        <span className="text-sm font-bold text-[#e94f88]">
                                            {benefit.metric}
                                        </span>
                                    </div>
                                    {/* Mini visual detail: Simple progress bar */}
                                    <div className="w-full h-1 bg-white/10 rounded-full mt-2 overflow-hidden">
                                        <div className="h-full bg-[#e94f88] w-3/4 rounded-full opacity-70 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default BenefitsSection;
