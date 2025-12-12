import React from 'react';
import CardFlip from '../../components/ui/CardFlip';
import { Activity, Thermometer, Bell, Network, Gauge, Clock, TrendingUp, Database, FileText, AlertTriangle, Radio, Settings } from 'lucide-react';
import { LucideIcon } from 'lucide-react';

interface Feature {
    id: number;
    title: string;
    subtitle: string;
    description: string;
    features: string[];
    color: string;
    icon: LucideIcon;
    featureIcons: LucideIcon[];
}

const featuresData: Feature[] = [
    {
        id: 1,
        title: 'Estado Operacional',
        subtitle: 'Monitoramento em tempo real',
        description: 'Monitoramento contínuo do status do robô e variáveis de controle.',
        features: [
            'Status em tempo real',
            'Variáveis de controle',
            'Alertas automáticos',
            'Dashboard interativo',
        ],
        color: '#e94f88',
        icon: Activity,
        featureIcons: [Activity, Gauge, Bell, TrendingUp],
    },
    {
        id: 2,
        title: 'Temperatura e Ciclo',
        subtitle: 'Métricas críticas',
        description: 'Acompanhamento de métricas críticas para manutenção preditiva.',
        features: [
            'Monitoramento de temperatura',
            'Tempo de ciclo',
            'Cálculo de OEE',
            'Análise de tendências',
        ],
        color: '#e94f88',
        icon: Thermometer,
        featureIcons: [Thermometer, Clock, Gauge, TrendingUp],
    },
    {
        id: 3,
        title: 'Histórico e Alertas',
        subtitle: 'Registro detalhado',
        description: 'Registro detalhado de eventos e notificações de anomalias.',
        features: [
            'Séries temporais',
            'Logs de eventos',
            'Sistema de alertas',
            'Análise histórica',
        ],
        color: '#e94f88',
        icon: Bell,
        featureIcons: [Database, FileText, AlertTriangle, TrendingUp],
    },
    {
        id: 4,
        title: 'Mapeamento OPC UA',
        subtitle: 'Integração direta',
        description: 'Integração direta entre nós OPC UA e submodelos AAS.',
        features: [
            'Conexão OPC UA',
            'Mapeamento AAS',
            'Sincronização automática',
            'Configuração flexível',
        ],
        color: '#e94f88',
        icon: Network,
        featureIcons: [Radio, Network, TrendingUp, Settings],
    },
];

const KeyFeaturesSection: React.FC = () => {
    return (
        <section className="w-full py-20 bg-[#0f1115] text-white">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <div className="mb-16 text-center">
                    <span className="text-[#e94f88] font-semibold text-[42px]">
                        Funcionalidades Principais
                    </span>
                    <br />
                    <span className="text-gray-400 text-[25px]">
                        Explore as capacidades avançadas do nosso Digital Twin.
                    </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 justify-items-center">
                    {featuresData.map((feature) => (
                        <CardFlip
                            key={feature.id}
                            title={feature.title}
                            subtitle={feature.subtitle}
                            description={feature.description}
                            features={feature.features}
                            color={feature.color}
                            icon={feature.icon}
                            featureIcons={feature.featureIcons}
                        />
                    ))}
                </div>
            </div>
        </section>
    );
};

export default KeyFeaturesSection;
