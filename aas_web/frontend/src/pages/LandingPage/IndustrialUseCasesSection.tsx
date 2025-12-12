import { FiTool, FiTrendingUp, FiShield } from 'react-icons/fi';

interface UseCase {
    id: number;
    title: string;
    summary: string;
    results: string[];
    icon: React.ElementType;
}

const useCasesData: UseCase[] = [
    {
        id: 1,
        title: 'Manutenção Preditiva',
        summary: 'Antecipação de falhas mecânicas através da análise de vibração e temperatura do motor em tempo real.',
        results: ['Redução de downtime não planejado', 'Aumento da vida útil do ativo'],
        icon: FiTool,
    },
    {
        id: 2,
        title: 'Otimização de Ciclo',
        summary: 'Ajuste fino de parâmetros de controle baseado no histórico de performance e gargalos identificados.',
        results: ['Aumento de throughput', 'Redução de consumo energético'],
        icon: FiTrendingUp,
    },
    {
        id: 3,
        title: 'Auditoria e Compliance',
        summary: 'Rastreabilidade completa de todas as ações e estados do robô para fins de auditoria e qualidade.',
        results: ['Histórico imutável', 'Conformidade com normas'],
        icon: FiShield,
    },
];

const IndustrialUseCasesSection: React.FC = () => {
    return (
        <section className="w-full py-20 bg-[#0f1115] text-white">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="mb-16 text-center">
                    <span className="text-[#e94f88] font-semibold text-[42px]">
                        Casos de Uso Industriais
                    </span>
                    <br />
                    <span className="text-gray-400 text-[25px]">
                        Aplicações reais da nossa tecnologia no chão de fábrica.
                    </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {useCasesData.map((useCase) => (
                        <div
                            key={useCase.id}
                            className="flex flex-col p-8 rounded-2xl bg-white/5 border border-white/10 hover:border-[#e94f88]/30 transition-colors duration-300"
                        >
                            <div className="mb-6 inline-flex items-center justify-center w-14 h-14 rounded-full bg-[#e94f88]/10 text-[#e94f88]">
                                <useCase.icon className="w-7 h-7" />
                            </div>

                            <h3 className="text-xl font-bold mb-3 text-white">
                                {useCase.title}
                            </h3>

                            <p className="text-gray-400 mb-6 leading-relaxed">
                                {useCase.summary}
                            </p>

                            <div className="mt-auto pt-6 border-t border-white/10">
                                <h4 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">
                                    Resultados Esperados
                                </h4>
                                <ul className="space-y-2">
                                    {useCase.results.map((result, index) => (
                                        <li key={index} className="flex items-start gap-2 text-sm text-gray-400">
                                            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[#e94f88] flex-shrink-0" />
                                            <span>{result}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default IndustrialUseCasesSection;
