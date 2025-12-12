import { useMemo, useEffect, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

// Simplified robot for landing page with predefined animation
export default function LandingRobot({ onHover }: { onHover?: (hovered: boolean) => void }) {
    // Load GLTF models
    const { scene: model01Scene } = useGLTF('/models/01.glb');
    const { scene: model02Scene } = useGLTF('/models/02.glb');
    const { scene: model03Scene } = useGLTF('/models/03.glb');
    const { scene: model04Scene } = useGLTF('/models/04.glb');
    const { scene: baseScene } = useGLTF('/models/base.glb');

    // Clone scenes
    const model01 = useMemo(() => model01Scene.clone(), [model01Scene]);
    const model02 = useMemo(() => model02Scene.clone(), [model02Scene]);
    const model03 = useMemo(() => model03Scene.clone(), [model03Scene]);
    const model04 = useMemo(() => model04Scene.clone(), [model04Scene]);
    const baseModel = useMemo(() => baseScene.clone(), [baseScene]);

    // Animation state
    const [animationTime, setAnimationTime] = useState(0);
    const [baseHeight, setBaseHeight] = useState(0);
    const [isHovered, setIsHovered] = useState(false);

    // Apply colors to models
    useEffect(() => {
        model02.traverse((child: any) => {
            if (child.isMesh) {
                child.material = child.material.clone();
                child.material.color.set('#ff6b00');
                child.material.emissive = new THREE.Color('#ff6b00');
                child.material.emissiveIntensity = isHovered ? 0.15 : 0;
            }
        });
    }, [model02, isHovered]);

    useEffect(() => {
        const box = new THREE.Box3().setFromObject(model03);
        const midY = (box.max.y + box.min.y) / 2;

        model03.traverse((child: any) => {
            if (child.isMesh) {
                child.material = child.material.clone();
                child.material.onBeforeCompile = (shader: any) => {
                    shader.uniforms.colorBottom = { value: new THREE.Color('#111111') };
                    shader.uniforms.colorTop = { value: new THREE.Color('#ff6b00') };
                    shader.uniforms.splitY = { value: midY };

                    shader.vertexShader = `
            varying vec3 vLocalPos;
            ${shader.vertexShader}
          `.replace(
                        '#include <begin_vertex>',
                        `
            #include <begin_vertex>
            vLocalPos = position;
            `
                    );

                    shader.fragmentShader = `
            uniform vec3 colorBottom;
            uniform vec3 colorTop;
            uniform float splitY;
            varying vec3 vLocalPos;
            ${shader.fragmentShader}
          `.replace(
                        '#include <color_fragment>',
                        `
            #include <color_fragment>
            float mixFactor = step(splitY, vLocalPos.y);
            diffuseColor.rgb = mix(colorBottom, colorTop, mixFactor);
            `
                    );
                };
                child.material.needsUpdate = true;
            }
        });
    }, [model03]);

    useEffect(() => {
        model01.traverse((child: any) => {
            if (child.isMesh) {
                child.material = child.material.clone();
                child.material.color.set('#111111');
            }
        });
    }, [model01]);

    useEffect(() => {
        if (baseModel) {
            baseModel.scale.set(0.5, 0.5, 0.5);
            baseModel.rotation.set(0, Math.PI / 2, 0);
            baseModel.updateMatrixWorld(true);
            const scaledBox = new THREE.Box3().setFromObject(baseModel);
            setBaseHeight(scaledBox.max.y);

            baseModel.traverse((child: any) => {
                if (child.isMesh) {
                    child.material = child.material.clone();
                    child.material.color.set('#666666');
                }
            });
        }
    }, [baseModel]);

    // Predefined animation loop
    useFrame((state, delta) => {
        setAnimationTime((prev) => prev + delta);
    });

    // Calculate smooth joint movement for demo animation
    const t = animationTime * 0.5;
    const j1_deg = Math.sin(t) * 45;
    const j2_deg = Math.cos(t * 0.7) * 35;
    const j3_mm = Math.sin(t * 0.3) * -80 - 100;

    const j1_rad = THREE.MathUtils.degToRad(j1_deg);
    const j2_rad = THREE.MathUtils.degToRad(j2_deg);
    const j3_pos = Math.min(0, j3_mm / 20);

    const handlePointerOver = () => {
        setIsHovered(true);
        onHover?.(true);
    };

    const handlePointerOut = () => {
        setIsHovered(false);
        onHover?.(false);
    };

    return (
        <group
            dispose={null}
            onPointerOver={handlePointerOver}
            onPointerOut={handlePointerOut}
        >
            {/* Base */}
            <group position={[0, 6, 0]}>
                <primitive object={baseModel} scale={[0.4, 0.4, 0.4]} rotation={[0, Math.PI / 2, 0]} />
            </group>

            {/* Robot Group */}
            <group position={[0, baseHeight + 25, 0]}>
                <group position={[0, 0, 0]}>
                    <group position={[0, 0, 0]}>
                        <primitive object={model01} scale={[0.1, 0.1, 0.1]} />

                        <group position={[1, 18, -1]} rotation={[0, j1_rad, 0]}>
                            <primitive object={model02} scale={[0.1, 0.1, 0.1]} />

                            <group position={[37, 19, 0]} rotation={[0, j2_rad, 0]}>
                                <primitive object={model03} scale={[0.1, 0.1, 0.1]} />

                                <group position={[41, -12 + j3_pos, 0]} rotation={[0, THREE.MathUtils.degToRad(-36), 0]}>
                                    <primitive object={model04} scale={[0.1, 0.1, 0.1]} />
                                </group>
                            </group>
                        </group>
                    </group>
                </group>
            </group>
        </group>
    );
}

// Preload models
useGLTF.preload('/models/01.glb');
useGLTF.preload('/models/02.glb');
useGLTF.preload('/models/03.glb');
useGLTF.preload('/models/04.glb');
useGLTF.preload('/models/base.glb');
