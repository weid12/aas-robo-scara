import { Sparkles } from "@/components/ui/sparkles"
import { InfiniteSlider } from "@/components/ui/infinite-slider"
import { ProgressiveBlur } from "@/components/ui/progressive-blur"

import {
    SiPython,
    SiTypescript,
    SiJavascript,
    SiReact,
    SiTailwindcss,
    SiFastapi,
    SiFlask,
    SiSqlite,
} from "react-icons/si"

import { FaNetworkWired, FaDatabase } from "react-icons/fa"

type LogoItem = {
    id: string
    label: string
    component: () => JSX.Element
    className: string
}

const PythonLogo = () => <SiPython className="w-full h-auto" />
const TypeScriptLogo = () => <SiTypescript className="w-full h-auto" />
const JavaScriptLogo = () => <SiJavascript className="w-full h-auto" />
const ReactLogo = () => <SiReact className="w-full h-auto" />
const TailwindLogo = () => <SiTailwindcss className="w-full h-auto" />
const FastAPILogo = () => <SiFastapi className="w-full h-auto" />
const FlaskLogo = () => <SiFlask className="w-full h-auto" />
const SQLiteLogo = () => <SiSqlite className="w-full h-auto" />

const OpcuaLogo = () => <FaNetworkWired className="w-full h-auto" />
const SqlAlchemyLogo = () => <FaDatabase className="w-full h-auto" />

const logos: LogoItem[] = [
    { id: "python", label: "Python", component: PythonLogo, className: "w-20" },
    { id: "typescript", label: "TypeScript", component: TypeScriptLogo, className: "w-20" },
    { id: "javascript", label: "JavaScript", component: JavaScriptLogo, className: "w-20" },
    { id: "react", label: "React", component: ReactLogo, className: "w-20" },
    { id: "tailwind", label: "Tailwind CSS", component: TailwindLogo, className: "w-28" },
    { id: "fastapi", label: "FastAPI", component: FastAPILogo, className: "w-20" },
    { id: "flask", label: "Flask", component: FlaskLogo, className: "w-20" },
    { id: "opcua", label: "OPC UA", component: OpcuaLogo, className: "w-20" },
    { id: "sqlite", label: "SQLite", component: SQLiteLogo, className: "w-20" },
    { id: "sqlalchemy", label: "SQLAlchemy", component: SqlAlchemyLogo, className: "w-20" },
]

export function TrustedBySection() {
    return (
        <div className="h-[800px] w-full overflow-hidden bg-[#0f1115] text-white font-sans">
            <div className="mx-auto mt-32 w-full px-6 md:px-10 lg:px-16">
                <div className="text-center">
                    <span className="text-[#e94f88] font-semibold text-[42px]">
                        Project Technology Overview
                    </span>
                    <br />
                    <span className="text-gray-400 text-[25px]">
                        A stack built for immersive, data driven experiences and responsive UI for industrial insights using AAS.
                    </span>
                </div>

                <div className="relative mt-7 h-[150px] w-full">
                    <InfiniteSlider
                        className="flex h-full w-full items-center"
                        duration={30}
                        gap={80}
                    >
                        {logos.map(({ id, label, component: Logo, className }) => (
                            <div
                                key={id}
                                title={label}
                                className={`
                  ${className}
                  flex flex-col items-center justify-center gap-2
                  text-gray-400 hover:text-[#e94f88]
                  transition-colors duration-300
                `}
                            >
                                <Logo />
                                <span className="text-xs font-medium text-current whitespace-nowrap">
                                    {label}
                                </span>
                            </div>
                        ))}
                    </InfiniteSlider>

                    {/* Blurs laterais aumentados */}
                    <ProgressiveBlur
                        className="pointer-events-none absolute top-0 left-0 h-full w-[260px]"
                        direction="left"
                        blurIntensity={1}
                    />
                    <ProgressiveBlur
                        className="pointer-events-none absolute top-0 right-0 h-full w-[260px]"
                        direction="right"
                        blurIntensity={1}
                    />
                </div>
            </div>

            <div className="relative -mt-32 h-96 w-full overflow-hidden [mask-image:radial-gradient(50%_50%,white,transparent)]">
                <div className="absolute inset-0 before:absolute before:inset-0 before:bg-[radial-gradient(circle_at_bottom_center,#e94f88,transparent_70%)] before:opacity-40" />
                <div className="absolute -left-1/2 top-1/2 aspect-[1/0.7] z-10 w-[200%] rounded-[100%] border-t border-white/10 bg-[#0f1115]" />
                <Sparkles
                    density={1200}
                    className="absolute inset-x-0 bottom-0 h-full w-full [mask-image:radial-gradient(50%_50%,white,transparent_85%)]"
                    color="#e94f88"
                />
            </div>
        </div>
    )
}
