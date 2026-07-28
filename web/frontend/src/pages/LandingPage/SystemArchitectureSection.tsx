import React from 'react';
import {
    FiCpu,
    FiRadio,
    FiDatabase,
    FiServer,
    FiMonitor,
    FiArrowRight,
    FiArrowDown,
} from 'react-icons/fi';

const steps = [
    {
        id: 1,
        label: 'Physical Asset',
        name: 'Robot',
        description: 'Raw data generation and control',
        icon: FiCpu,
    },
    {
        id: 2,
        label: 'Connectivity',
        name: 'OPC UA Client',
        description: 'Collection and standardization',
        icon: FiRadio,
    },
    {
        id: 3,
        label: 'Persistence',
        name: 'SQLite',
        description: 'Historical storage',
        icon: FiDatabase,
    },
    {
        id: 4,
        label: 'Backend',
        name: 'FastAPI / Flask',
        description: 'Business logic and AAS',
        icon: FiServer,
    },
    {
        id: 5,
        label: 'Visualization',
        name: 'Dashboard',
        description: 'Interactive 3D interface',
        icon: FiMonitor,
    },
];

const SystemArchitectureSection: React.FC = () => {
    return (
        <section className="w-full py-20 bg-[#0f1115] text-white overflow-hidden">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="mb-16 text-center">
                    <span className="text-[#e94f88] font-semibold text-[42px]">
                        System Architecture
                    </span>
                    <br />
                    <span className="text-gray-400 text-[25px]">
                        End-to-end data flow, from the shop floor to the web platform.
                    </span>
                </div>

                <div className="relative">
                    {/* Linha do fluxo desktop */}
                    <div className="hidden lg:block absolute inset-x-10 top-1/2 -translate-y-1/2 z-0">
                        <div className="h-px bg-gradient-to-r from-transparent via-[#e94f88]/30 to-transparent" />
                    </div>

                    {/* Linha do fluxo mobile */}
                    <div className="lg:hidden absolute left-1/2 top-4 bottom-4 w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-white/10 to-transparent" />

                    <div className="relative z-10 flex flex-col lg:flex-row items-center justify-center gap-8 lg:gap-6">
                        {steps.map((step, index) => {
                            const Icon = step.icon;
                            const isLast = index === steps.length - 1;

                            return (
                                <React.Fragment key={step.id}>
                                    <div className="flex flex-col items-center text-center group">
                                        <div
                                            className="
                                                relative flex items-center justify-center
                                                w-16 h-16 sm:w-18 sm:h-18
                                                rounded-full
                                                bg-[#151822]
                                                border border-white/15
                                                shadow-[0_10px_30px_rgba(0,0,0,0.45)]
                                                ring-1 ring-transparent
                                                transition-all duration-300
                                                group-hover:-translate-y-0.5
                                                group-hover:border-[#e94f88]/50
                                                group-hover:ring-[#e94f88]/25
                                                focus-within:ring-2
                                                focus-within:ring-[#e94f88]/70
                                            "
                                        >
                                            <button
                                                type="button"
                                                className="flex items-center justify-center w-full h-full rounded-full focus:outline-none"
                                                aria-label={`${step.label} ${step.name}`}
                                            >
                                                <Icon className="w-7 h-7 text-[#e94f88]" />
                                            </button>
                                            <span
                                                aria-hidden="true"
                                                className="
                                                    pointer-events-none
                                                    absolute -inset-1
                                                    rounded-full
                                                    bg-[#e94f88]/10
                                                    opacity-0
                                                    blur-xl
                                                    transition-opacity duration-300
                                                    group-hover:opacity-100
                                                "
                                            />
                                        </div>

                                        <div className="mt-4">
                                            <div className="text-[#e94f88] text-[11px] sm:text-xs font-semibold tracking-[0.16em] uppercase">
                                                {step.label}
                                            </div>
                                            <div className="mt-1 text-sm sm:text-base font-semibold text-white">
                                                {step.name}
                                            </div>
                                        </div>

                                        <p className="mt-3 text-xs sm:text-sm text-gray-400/80 max-w-[180px] leading-relaxed">
                                            {step.description}
                                        </p>
                                    </div>

                                    {/* Conectores entre ícones */}
                                    {!isLast && (
                                        <>
                                            {/* Conector horizontal desktop */}
                                            <div className="hidden lg:flex items-center justify-center">
                                                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[#151822] border border-white/15 text-[#e94f88]/80">
                                                    <FiArrowRight className="w-4 h-4" />
                                                </span>
                                            </div>

                                            {/* Conector vertical mobile */}
                                            <div className="lg:hidden flex items-center justify-center">
                                                <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-[#151822] border border-white/15 text-[#e94f88]/80">
                                                    <FiArrowDown className="w-4 h-4" />
                                                </span>
                                            </div>
                                        </>
                                    )}
                                </React.Fragment>
                            );
                        })}
                    </div>
                </div>

                <div className="mt-16 flex justify-center gap-8 text-sm text-gray-400">
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-[#e94f88]" />
                        <span>Data Flow</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-[#1a1d24] border border-white/10" />
                        <span>System Component</span>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default SystemArchitectureSection;
