'use client';

import { cn } from '@/lib/utils';
import { ArrowRight, LucideIcon } from 'lucide-react';
import { useState } from 'react';

export interface CardFlipProps {
    title?: string;
    subtitle?: string;
    description?: string;
    features?: string[];
    color?: string;
    icon?: LucideIcon;
    featureIcons?: LucideIcon[];
}

export default function CardFlip({
    title = 'Build MVPs Fast',
    subtitle = 'Launch your idea in record time',
    description = 'Copy, paste, customize—and launch your MVP faster than ever with our developer-first component library.',
    features = [
        'Copy & Paste Ready',
        'Developer-First',
        'MVP Optimized',
        'Zero Setup Required',
    ],
    color = '#e94f88',
    icon: MainIcon,
    featureIcons = [],
}: CardFlipProps) {
    const [isFlipped, setIsFlipped] = useState(false);

    return (
        <div
            style={{
                ['--primary' as any]: color ?? '#e94f88',
            }}
            className="group relative h-[400px] w-full max-w-[300px] [perspective:2000px]"
            onMouseEnter={() => setIsFlipped(true)}
            onMouseLeave={() => setIsFlipped(false)}
        >
            <div
                className={cn(
                    'relative h-full w-full',
                    '[transform-style:preserve-3d]',
                    'transition-all duration-700',
                    isFlipped
                        ? '[transform:rotateY(180deg)]'
                        : '[transform:rotateY(0deg)]',
                )}
            >
                {/* Front of card */}
                <div
                    className={cn(
                        'absolute inset-0 h-full w-full',
                        '[transform:rotateY(0deg)] [backface-visibility:hidden]',
                        'overflow-hidden rounded-xl',
                        'bg-white/5 backdrop-blur-sm',
                        'border border-white/10',
                        'transition-all duration-300',
                        'group-hover:border-[#e94f88]/50',
                        isFlipped ? 'opacity-0' : 'opacity-100',
                    )}
                >
                    {/* Hover gradient overlay */}
                    <div className="absolute inset-0 bg-gradient-to-br from-[#e94f88]/0 to-[#e94f88]/5 opacity-0 group-hover:opacity-100 rounded-xl transition-opacity duration-300" />

                    <div className="relative z-10 flex flex-col h-full p-6">
                        {/* Animated code lines at top */}
                        <div className="mb-auto">
                            <div className="space-y-2">
                                {[...Array(2)].map((_, i) => (
                                    <div
                                        key={i}
                                        className="h-1 rounded-full bg-gradient-to-r from-[#e94f88]/20 via-[#e94f88]/40 to-[#e94f88]/20 opacity-60"
                                        style={{
                                            width: i === 0 ? '60%' : '40%',
                                        }}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Central icon with animated code blocks */}
                        <div className="flex items-center justify-center my-auto">
                            <div className="relative flex h-[100px] w-[200px] items-center justify-center">
                                {/* Animated code blocks behind icon */}
                                {[...Array(6)].map((_, i) => (
                                    <div
                                        key={i}
                                        className={cn(
                                            'absolute h-2 rounded-sm',
                                            'bg-gradient-to-r from-[#e94f88]/20 via-[#e94f88]/30 to-[#e94f88]/20',
                                            'animate-[slideIn_2s_ease-in-out_infinite]',
                                            'opacity-0',
                                        )}
                                        style={{
                                            width: `${60 + Math.random() * 40}%`,
                                            animationDelay: `${i * 0.2}s`,
                                            left: `${Math.random() * 20}%`,
                                            top: `${20 + i * 12}%`,
                                        }}
                                    />
                                ))}

                                {/* Central icon */}
                                <div className="relative z-10 inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#e94f88]/10 text-[#e94f88] group-hover:bg-[#e94f88] group-hover:text-white transition-all duration-500 group-hover:scale-110 group-hover:rotate-12 animate-pulse">
                                    {MainIcon && <MainIcon className="w-8 h-8" />}
                                </div>
                            </div>
                        </div>

                        {/* Bottom content */}
                        <div className="mt-auto space-y-3">
                            <div>
                                <h3 className="text-xl font-bold mb-1 text-white group-hover:text-[#e94f88] transition-colors">
                                    {title}
                                </h3>
                                <p className="text-sm text-gray-400">
                                    {subtitle}
                                </p>
                            </div>

                            {/* Hint */}
                            <div className="pt-3 border-t border-white/10">
                                <div className="flex items-center justify-between text-xs text-gray-500">
                                    <span>Passe o mouse para mais</span>
                                    <ArrowRight className="w-4 h-4 text-[#e94f88] opacity-50 group-hover:opacity-100 transition-opacity" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Back of card */}
                <div
                    className={cn(
                        'absolute inset-0 h-full w-full',
                        '[transform:rotateY(180deg)] [backface-visibility:hidden]',
                        'rounded-xl p-6',
                        'bg-white/5 backdrop-blur-sm',
                        'border border-[#e94f88]/50',
                        'flex flex-col',
                        'transition-all duration-300',
                        !isFlipped ? 'opacity-0' : 'opacity-100',
                    )}
                >
                    {/* Background gradient */}
                    <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-[#e94f88]/5 via-transparent to-[#e94f88]/10" />

                    <div className="relative z-10 flex-1 space-y-4">
                        <div className="space-y-2">
                            <div className="flex items-center gap-2.5">
                                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#e94f88] text-white">
                                    {MainIcon && <MainIcon className="h-5 w-5" />}
                                </div>
                                <h3 className="text-lg font-semibold text-white">
                                    {title}
                                </h3>
                            </div>
                            <p className="text-sm text-gray-400">
                                {description}
                            </p>
                        </div>

                        <div className="space-y-2.5">
                            {features.map((feature, index) => {
                                const IconComponent = featureIcons[index];

                                return (
                                    <div
                                        key={feature}
                                        className="flex items-center gap-2.5 text-sm text-gray-300"
                                        style={{
                                            transform: isFlipped
                                                ? 'translateX(0)'
                                                : 'translateX(-10px)',
                                            opacity: isFlipped ? 1 : 0,
                                            transitionDelay: `${index * 100 + 200}ms`,
                                            transition: 'all 0.5s',
                                        }}
                                    >
                                        <div className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-[#e94f88]/20">
                                            {IconComponent && <IconComponent className="text-[#e94f88] h-3 w-3" />}
                                        </div>
                                        <span className="font-medium">{feature}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    <div className="relative z-10 mt-auto border-t border-white/10 pt-4">
                        <div
                            className={cn(
                                'group/start relative',
                                'flex items-center justify-between',
                                'rounded-lg p-3',
                                'transition-all duration-300',
                                'bg-white/5',
                                'hover:bg-[#e94f88]/20',
                                'hover:scale-[1.02] hover:cursor-pointer',
                                'border border-transparent hover:border-[#e94f88]/30',
                            )}
                        >
                            <span className="text-sm font-semibold text-white transition-colors duration-300 group-hover/start:text-[#e94f88]">
                                Saiba Mais
                            </span>
                            <ArrowRight className="text-[#e94f88] h-4 w-4 transition-all duration-300 group-hover/start:translate-x-1" />
                        </div>
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes slideIn {
                    0% {
                        transform: translateX(-100px);
                        opacity: 0;
                    }
                    50% {
                        transform: translateX(0);
                        opacity: 0.8;
                    }
                    100% {
                        transform: translateX(100px);
                        opacity: 0;
                    }
                }
            `}</style>
        </div>
    );
}
