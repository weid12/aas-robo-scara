import { Canvas, useFrame } from '@react-three/fiber';
import { Environment, PerspectiveCamera, ContactShadows, Float, Stars } from '@react-three/drei';
import { Suspense, useRef, useState } from 'react';
import * as THREE from 'three';
import LandingRobot from '../LandingRobot';
import DashboardCards3D from './DashboardCards3D';

function CameraController() {
    const vec = new THREE.Vector3();

    useFrame((state) => {
        // Smooth parallax camera movement based on mouse position
        const { x, y } = state.pointer;

        // Target position: slight movement around the center
        const targetX = 80 + x * 10;
        const targetY = 60 + y * 10;
        const targetZ = 80 + (x + y) * 5;

        state.camera.position.lerp(vec.set(targetX, targetY, targetZ), 0.05);
        state.camera.lookAt(0, 25, 0);
    });

    return null;
}

export default function HeroScene3D() {
    const [robotHovered, setRobotHovered] = useState(false);

    return (
        <div style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, zIndex: 0 }}>
            <Canvas shadows dpr={[1, 2]}>
                <PerspectiveCamera makeDefault position={[80, 60, 80]} fov={45} />
                <CameraController />

                {/* Lighting */}
                <ambientLight intensity={0.5} />
                <directionalLight
                    position={[-10, 20, 10]}
                    intensity={2}
                    color="#ffffff"
                />
                <spotLight
                    position={[50, 50, 50]}
                    angle={0.15}
                    penumbra={1}
                    intensity={10}
                    castShadow
                    color="#e94f88"
                />
                <pointLight position={[-20, 10, -20]} intensity={2} color="#4caf50" distance={50} />

                {/* Environment */}
                <Stars radius={300} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                <Environment preset="city" />

                {/* Floor Reflections */}
                <ContactShadows
                    resolution={1024}
                    scale={200}
                    blur={2}
                    opacity={0.5}
                    far={50}
                    color="#000000"
                />

                {/* Scene Content */}
                <Suspense fallback={null}>
                    <group position={[-20, -10, 0]} scale={[0.6, 0.6, 0.6]}>
                        <LandingRobot onHover={setRobotHovered} />
                    </group>

                    <Float
                        speed={2}
                        rotationIntensity={0.2}
                        floatIntensity={0.5}
                        floatingRange={[-1, 1]}
                    >
                        <DashboardCards3D />
                    </Float>
                </Suspense>

                {/* Fog for depth */}
                <fog attach="fog" args={['#0f1115', 50, 300]} />
            </Canvas>
        </div>
    );
}
