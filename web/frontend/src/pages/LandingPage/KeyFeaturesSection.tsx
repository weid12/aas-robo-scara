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
        title: 'Operational State',
        subtitle: 'Real-time monitoring',
        description: 'Continuous monitoring of robot status and control variables.',
        features: [
            'Real-time status',
            'Control variables',
            'Automatic alerts',
            'Interactive dashboard',
        ],
        color: '#e94f88',
        icon: Activity,
        featureIcons: [Activity, Gauge, Bell, TrendingUp],
    },
    {
        id: 2,
        title: 'Temperature & Cycle',
        subtitle: 'Critical metrics',
        description: 'Tracking of critical metrics for predictive maintenance.',
        features: [
            'Temperature monitoring',
            'Cycle time',
            'OEE calculation',
            'Trend analysis',
        ],
        color: '#e94f88',
        icon: Thermometer,
        featureIcons: [Thermometer, Clock, Gauge, TrendingUp],
    },
    {
        id: 3,
        title: 'History & Alerts',
        subtitle: 'Detailed logging',
        description: 'Detailed logging of events and anomaly notifications.',
        features: [
            'Time series',
            'Event logs',
            'Alert system',
            'Historical analysis',
        ],
        color: '#e94f88',
        icon: Bell,
        featureIcons: [Database, FileText, AlertTriangle, TrendingUp],
    },
    {
        id: 4,
        title: 'OPC UA Mapping',
        subtitle: 'Direct integration',
        description: 'Direct integration between OPC UA nodes and AAS submodels.',
        features: [
            'OPC UA connection',
            'AAS mapping',
            'Automatic synchronization',
            'Flexible configuration',
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
                        Key Features
                    </span>
                    <br />
                    <span className="text-gray-400 text-[25px]">
                        Explore the advanced capabilities of our Digital Twin.
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
