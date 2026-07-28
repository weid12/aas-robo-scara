import React, { useState, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, PerspectiveCamera } from "@react-three/drei";
import { FaCog, FaPlay, FaChevronRight, FaLock, FaUnlock, FaGamepad } from "react-icons/fa";
import ScaraRobot from "./ScaraRobot";

export default function RobotCard({
    joints = {},
    width = "100%",
    height = "500px",
    style = {},
    className = "",
    emergencyArmed = false
}) {
    const [isHovered, setIsHovered] = useState(false);

    // Simulation State
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isSimulating, setIsSimulating] = useState(false);
    const [simulatedJoints, setSimulatedJoints] = useState(joints);

    // Camera Lock State (Default Locked)
    const [isCameraLocked, setIsCameraLocked] = useState(true);

    // Manual Control State
    const [isControlModalOpen, setIsControlModalOpen] = useState(false);
    const [controlMode, setControlMode] = useState("auto"); // 'auto' | 'manual'
    const [manualJoints, setManualJoints] = useState({
        j1_deg: 0,
        j2_deg: 0,
        j3_mm: 0,
        j4_deg: 0
    });
    const [showWarning, setShowWarning] = useState(false);

    // Emergency Stop Logic
    useEffect(() => {
        if (emergencyArmed) {
            setIsSimulating(false);
            setControlMode("auto");
            setIsControlModalOpen(false);
        }
    }, [emergencyArmed]);

    // Simulation Logic
    useEffect(() => {
        let interval;
        if (isSimulating && controlMode === "auto" && !emergencyArmed) {
            interval = setInterval(() => {
                setSimulatedJoints({
                    j1_deg: (Math.random() * 180) - 90,
                    j2_deg: (Math.random() * 180) - 90,
                    j3_mm: -(Math.random() * 200),
                    j4_deg: (Math.random() * 720) - 360,
                });
            }, 2000); // Update every 2 seconds
        } else if (controlMode === "auto") {
            setSimulatedJoints(joints);
        }
        return () => clearInterval(interval);
    }, [isSimulating, joints, controlMode, emergencyArmed]);

    // Sync props when not simulating and in auto mode
    useEffect(() => {
        if (!isSimulating && controlMode === "auto") {
            setSimulatedJoints(joints);
        }
    }, [joints, isSimulating, controlMode]);

    // Initialize manual joints when switching to manual
    useEffect(() => {
        if (controlMode === "manual") {
            setManualJoints(simulatedJoints);
        }
    }, [controlMode]); // Only run when mode changes

    const handleSliderChange = (joint, value) => {
        if (controlMode === "auto") {
            setShowWarning(true);
            setTimeout(() => setShowWarning(false), 2000);
            return;
        }
        setManualJoints(prev => ({
            ...prev,
            [joint]: parseFloat(value)
        }));
    };

    // Determine which joints to display
    const displayJoints = controlMode === "manual" ? manualJoints : simulatedJoints;

    return (
        <div
            className={className}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            style={{
                width,
                height,
                position: "relative",
                background: "#000",
                overflow: "hidden",
                borderRadius: "16px",
                border: isHovered ? "1px solid rgba(233, 79, 136, 0.5)" : "1px solid rgba(255,255,255,0.08)",
                boxShadow: isHovered ? "0 0 15px rgba(233, 79, 136, 0.3)" : "none",
                transition: "all 0.3s ease",
                ...style
            }}
        >
            <Canvas shadows>
                <PerspectiveCamera makeDefault position={[120, 220, 120]} fov={45} />

                <OrbitControls
                    makeDefault
                    enableDamping
                    dampingFactor={0.1}
                    target={[0, 30, 0]}
                    enabled={!isCameraLocked} // Disable controls when locked
                />

                <ambientLight intensity={0.8} />
                <directionalLight
                    position={[10, 20, 10]}
                    intensity={1.5}
                    castShadow
                    shadow-mapSize={[1024, 1024]}
                />
                <Environment preset="city" />

                <gridHelper args={[2000, 20, "#1e2334", "#1e2334"]} />
                <axesHelper args={[100]} />

                <ScaraRobot joints={displayJoints} />

                <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
                    <planeGeometry args={[5000, 5000]} />
                    <meshStandardMaterial color="#1b1b2d" roughness={0.8} />
                </mesh>
            </Canvas>

            {/* Warning Toast */}
            {showWarning && (
                <div style={{
                    position: "absolute",
                    top: "20px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "rgba(255, 0, 0, 0.8)",
                    color: "white",
                    padding: "8px 16px",
                    borderRadius: "8px",
                    zIndex: 100,
                    fontSize: "12px",
                    fontWeight: "bold",
                    backdropFilter: "blur(4px)"
                }}>
                    Switch to Manual Mode to control!
                </div>
            )}

            {/* Control Modal (Left Side) */}
            {isControlModalOpen && (
                <div style={{
                    position: "absolute",
                    top: "50%",
                    left: "20px",
                    transform: "translateY(-50%)",
                    width: "220px",
                    background: "rgba(0, 0, 0, 0.6)",
                    backdropFilter: "blur(10px)",
                    borderRadius: "12px",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    padding: "15px",
                    zIndex: 50,
                    color: "white"
                }}>
                    <style>{`
                        .modern-range {
                            -webkit-appearance: none;
                            width: 100%;
                            height: 4px;
                            background: rgba(255, 255, 255, 0.2);
                            border-radius: 2px;
                            outline: none;
                            opacity: 0.7;
                            transition: opacity .2s;
                        }
                        .modern-range:hover {
                            opacity: 1;
                        }
                        .modern-range::-webkit-slider-thumb {
                            -webkit-appearance: none;
                            appearance: none;
                            width: 12px;
                            height: 12px;
                            border-radius: 50%;
                            background: #1de9b6;
                            cursor: pointer;
                            box-shadow: 0 0 5px rgba(29, 233, 182, 0.5);
                            transition: transform 0.1s;
                        }
                        .modern-range::-webkit-slider-thumb:hover {
                            transform: scale(1.2);
                        }
                        .modern-range::-moz-range-thumb {
                            width: 12px;
                            height: 12px;
                            border-radius: 50%;
                            background: #1de9b6;
                            cursor: pointer;
                            box-shadow: 0 0 5px rgba(29, 233, 182, 0.5);
                        }
                    `}</style>

                    {/* Header / Toggle */}
                    <div style={{ marginBottom: "15px", display: "flex", justifyContent: "center" }}>
                        <div style={{
                            display: "flex",
                            background: "rgba(0,0,0,0.5)",
                            borderRadius: "20px",
                            padding: "2px",
                            border: "1px solid rgba(255,255,255,0.1)"
                        }}>
                            <button
                                onClick={() => setControlMode("auto")}
                                style={{
                                    background: controlMode === "auto" ? "#1de9b6" : "transparent",
                                    color: controlMode === "auto" ? "#000" : "#aaa",
                                    borderRadius: "16px",
                                    padding: "4px 12px",
                                    border: "none",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    fontWeight: "bold",
                                    transition: "all 0.3s ease",
                                    outline: "none"
                                }}
                            >
                                Auto
                            </button>
                            <button
                                onClick={() => setControlMode("manual")}
                                style={{
                                    background: controlMode === "manual" ? "#1de9b6" : "transparent",
                                    color: controlMode === "manual" ? "#000" : "#aaa",
                                    borderRadius: "16px",
                                    padding: "4px 12px",
                                    border: "none",
                                    cursor: "pointer",
                                    fontSize: "11px",
                                    fontWeight: "bold",
                                    transition: "all 0.3s ease",
                                    outline: "none"
                                }}
                            >
                                Manual
                            </button>
                        </div>
                    </div>

                    {/* Sliders */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                        {[
                            { label: "Arm 1", key: "j1_deg", min: -90, max: 90, unit: "°" },
                            { label: "Arm 2", key: "j2_deg", min: -90, max: 90, unit: "°" },
                            { label: "Fix Cylinder", key: "j3_mm", min: -200, max: 0, unit: "mm" },
                            // J4 Removed as requested
                        ].map((joint) => (
                            <div key={joint.key}>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "6px", color: "#ccc", fontWeight: 500 }}>
                                    <span>{joint.label}</span>
                                    <span style={{ color: "#1de9b6" }}>{Math.round(displayJoints[joint.key])}{joint.unit}</span>
                                </div>
                                <input
                                    type="range"
                                    className="modern-range"
                                    min={joint.min}
                                    max={joint.max}
                                    value={displayJoints[joint.key]}
                                    onChange={(e) => handleSliderChange(joint.key, e.target.value)}
                                    style={{
                                        cursor: controlMode === "manual" ? "pointer" : "not-allowed",
                                        opacity: controlMode === "manual" ? 1 : 0.5
                                    }}
                                />
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Simulation Menu (Bottom Left) */}
            <div style={{
                position: "absolute",
                bottom: 20,
                left: 20,
                display: "flex",
                alignItems: "center",
                zIndex: 10
            }}>
                {/* Toggle Button */}
                <button
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                    style={{
                        background: "rgba(0,0,0,0.3)", // More transparent
                        color: "#1de9b6", // Lighter green/teal
                        border: "2px solid #1de9b6", // Lighter green/teal border
                        borderRadius: "50%",
                        width: "40px",
                        height: "40px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "pointer",
                        backdropFilter: "blur(4px)",
                        zIndex: 20,
                        outline: "none"
                    }}
                >
                    <FaCog size={20} />
                    <FaChevronRight size={12} style={{
                        marginLeft: "2px",
                        transform: isMenuOpen ? "rotate(180deg)" : "rotate(0deg)",
                        transition: "transform 0.3s ease"
                    }} />
                </button>

                {/* Expanding Menu */}
                <div style={{
                    width: isMenuOpen ? "300px" : "0px", // Increased width for toggle + lock + gamepad
                    height: "40px",
                    background: "rgba(0,0,0,0.3)", // Semi-transparent
                    backdropFilter: "blur(10px)", // Blur effect
                    border: isMenuOpen ? "1px solid rgba(255,255,255,0.1)" : "none",
                    borderRadius: "0 20px 20px 0",
                    marginLeft: "-20px", // Overlap with button
                    paddingLeft: "25px", // Space for button
                    display: "flex",
                    alignItems: "center",
                    gap: "15px", // Space between buttons
                    overflow: "hidden",
                    transition: "all 0.5s ease-in-out", // Papyrus effect
                    opacity: isMenuOpen ? 1 : 0
                }}>
                    {/* Mode Toggle */}
                    <div style={{
                        display: "flex",
                        background: "rgba(0,0,0,0.5)",
                        borderRadius: "20px",
                        padding: "2px",
                        border: "1px solid rgba(255,255,255,0.1)"
                    }}>
                        <button
                            onClick={() => setIsSimulating(false)}
                            disabled={emergencyArmed}
                            style={{
                                background: !isSimulating ? "#1de9b6" : "transparent",
                                color: !isSimulating ? "#000" : "#aaa",
                                borderRadius: "16px",
                                padding: "4px 12px",
                                border: "none",
                                cursor: emergencyArmed ? "not-allowed" : "pointer",
                                fontSize: "11px",
                                fontWeight: "bold",
                                transition: "all 0.3s ease",
                                outline: "none",
                                opacity: emergencyArmed ? 0.5 : 1
                            }}
                        >
                            Real Time
                        </button>
                        <button
                            onClick={() => setIsSimulating(true)}
                            disabled={emergencyArmed}
                            style={{
                                background: isSimulating ? "#1de9b6" : "transparent",
                                color: isSimulating ? "#000" : "#aaa",
                                borderRadius: "16px",
                                padding: "4px 12px",
                                border: "none",
                                cursor: emergencyArmed ? "not-allowed" : "pointer",
                                fontSize: "11px",
                                fontWeight: "bold",
                                transition: "all 0.3s ease",
                                outline: "none",
                                opacity: emergencyArmed ? 0.5 : 1
                            }}
                        >
                            Simulation
                        </button>
                    </div>

                    {/* Camera Lock Button */}
                    <button
                        onClick={() => setIsCameraLocked(!isCameraLocked)}
                        style={{
                            background: "transparent",
                            border: "none",
                            color: isCameraLocked ? "#ff4444" : "#1de9b6", // Red when locked, Green when unlocked
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            fontSize: "14px",
                            outline: "none"
                        }}
                        title={isCameraLocked ? "Unlock Camera" : "Lock Camera"}
                    >
                        {isCameraLocked ? <FaLock size={16} /> : <FaUnlock size={16} />}
                    </button>

                    {/* Manual Control Button */}
                    <button
                        onClick={() => !emergencyArmed && setIsControlModalOpen(!isControlModalOpen)}
                        disabled={emergencyArmed}
                        style={{
                            background: "transparent",
                            border: "none",
                            color: isControlModalOpen ? "#1de9b6" : "#888",
                            cursor: emergencyArmed ? "not-allowed" : "pointer",
                            display: "flex",
                            alignItems: "center",
                            fontSize: "14px",
                            outline: "none",
                            opacity: emergencyArmed ? 0.5 : 1
                        }}
                        title={emergencyArmed ? "Disabled (Emergency Stop)" : "Manual Control"}
                    >
                        <FaGamepad size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
}
