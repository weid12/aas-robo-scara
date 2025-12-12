import React from 'react';
import { Link } from 'react-router-dom';
import { FiGithub, FiLinkedin, FiMail, FiArrowUp } from 'react-icons/fi';
import aasLogo from '../../assets/aas-logo.png';

const Footer: React.FC = () => {
    const scrollToTop = () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const currentYear = new Date().getFullYear();

    return (
        <footer className="relative w-full bg-gradient-to-b from-[#0a0c10] via-[#0b0a0d] to-[#0e090c] text-white border-t border-[#e94f88]/10">
            {/* Gradient Overlay - Subtle pink gradient */}
            <div className="absolute inset-0 bg-gradient-to-t from-[#e94f88]/8 via-[#e94f88]/3 to-transparent pointer-events-none" />

            {/* Top Glow Effect */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-px bg-gradient-to-r from-transparent via-[#e94f88]/30 to-transparent" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-6 bg-gradient-to-b from-[#e94f88]/5 to-transparent blur-xl pointer-events-none" />

            <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
                {/* Main Footer Content */}
                <div className="py-12 lg:py-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
                    {/* Brand Section */}
                    <div className="lg:col-span-1">
                        <div className="flex items-center gap-3 mb-4">
                            <img
                                src={aasLogo}
                                alt="AAS Robot Scara Logo"
                                className="h-12 w-auto object-contain"
                            />
                            <div>
                                <h3 className="text-lg font-bold text-white">AAS Robot Scara</h3>
                                <span className="text-xs text-[#e94f88] font-medium">Digital Twin Platform</span>
                            </div>
                        </div>
                        <p className="text-sm text-gray-400 leading-relaxed mt-4">
                            Plataforma de monitoramento e controle industrial baseada em Asset Administration Shell para robôs SCARA.
                        </p>
                    </div>

                    {/* Quick Links */}
                    <div className="text-left">
                        <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">
                            Navegação
                        </h4>
                        <ul className="space-y-3 text-left">
                            <li>
                                <a
                                    href="#benefits"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    Benefícios
                                </a>
                            </li>
                            <li>
                                <a
                                    href="#features"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    Funcionalidades
                                </a>
                            </li>
                            <li>
                                <a
                                    href="#architecture"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    Arquitetura
                                </a>
                            </li>
                            <li>
                                <a
                                    href="#use-cases"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    Casos de Uso
                                </a>
                            </li>
                        </ul>
                    </div>

                    {/* Resources */}
                    <div>
                        <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">
                            Recursos
                        </h4>
                        <ul className="space-y-3">
                            <li>
                                <a
                                    href="https://www.plattform-i40.de/PI40/Redaktion/EN/Standardartikel/specification-administrationshell.html"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    Documentação AAS
                                </a>
                            </li>
                            <li>
                                <a
                                    href="#"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    API Reference
                                </a>
                            </li>
                            <li>
                                <a
                                    href="#"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    Guia de Integração
                                </a>
                            </li>
                            <li>
                                <Link
                                    to="/login"
                                    className="text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                                >
                                    Acessar Sistema
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Contact & Social */}
                    <div>
                        <h4 className="text-sm font-semibold text-white uppercase tracking-wider mb-4">
                            Contato
                        </h4>
                        <div className="space-y-4">
                            <a
                                href="mailto:wdof.mee24@uea.edu.br"
                                className="flex items-center gap-3 text-sm text-gray-400 hover:text-[#e94f88] transition-colors duration-200"
                            >
                                <FiMail className="w-4 h-4" />
                                wdof.mee24@uea.edu.br
                            </a>
                            <div className="flex items-center gap-4 pt-2">
                                <a
                                    href="https://github.com"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-2 rounded-lg bg-white/5 hover:bg-[#e94f88]/20 text-gray-400 hover:text-[#e94f88] transition-all duration-200"
                                    aria-label="GitHub"
                                >
                                    <FiGithub className="w-5 h-5" />
                                </a>
                                <a
                                    href="https://linkedin.com"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-2 rounded-lg bg-white/5 hover:bg-[#e94f88]/20 text-gray-400 hover:text-[#e94f88] transition-all duration-200"
                                    aria-label="LinkedIn"
                                >
                                    <FiLinkedin className="w-5 h-5" />
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Divider */}
                <div className="w-full h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

                {/* Bottom Bar */}
                <div className="py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 text-xs text-gray-500">
                        <span>© {currentYear} AAS Robot Scara. Todos os direitos reservados.</span>
                        <span className="hidden sm:inline">•</span>
                        <span>Desenvolvido para Indústria 4.0</span>
                    </div>

                    {/* Back to Top */}
                    <button
                        onClick={scrollToTop}
                        className="group flex items-center gap-2 text-xs text-gray-500 hover:text-[#e94f88] transition-colors duration-200"
                        aria-label="Voltar ao topo"
                    >
                        <span>Voltar ao topo</span>
                        <div className="p-1.5 rounded-md bg-white/5 group-hover:bg-[#e94f88]/20 transition-all duration-200">
                            <FiArrowUp className="w-3.5 h-3.5 group-hover:animate-bounce" />
                        </div>
                    </button>
                </div>
            </div>

            {/* Decorative Elements */}
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#e94f88] to-transparent opacity-30" />
        </footer>
    );
};

export default Footer;
