import React, { useMemo, useEffect, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { useGraph } from "@react-three/fiber";
import * as THREE from "three";

import BasePedestal from "./BasePedestal"; // Fallback for missing base.glb

// Calibration Constants (Offsets)
// Adjust these values to match the visual assembly of your GLTF models.
const OFFSETS = {
  BASE_HEIGHT: 20,      // Adjusted for BasePedestal
  AXIS1_LENGTH: [0, 6, 0], // Lift Axis 2 up by 6 units (higher above Axis 1)
  AXIS2_LENGTH: [30, 0, 0], // Move Tool out by 30 units (length of arm 2)
  TOOL_OFFSET: 0,
};

export default function ScaraRobot({ joints = {} }) {
  const { j1_deg = 0, j2_deg = 0, j3_mm = 0, j4_deg = 0 } = joints;

  // Load GLTF models
  // Note: Ensure base.glb and ferramenta.glb are present in public/models/
  // Only loading existing models to prevent crash
  const { scene: model01Scene } = useGLTF("/models/01.glb");
  const { scene: model02Scene } = useGLTF("/models/02.glb");
  const { scene: model03Scene } = useGLTF("/models/03.glb");
  const { scene: model04Scene } = useGLTF("/models/04.glb");
  const { scene: baseScene } = useGLTF("/models/base.glb");
  // const { scene: toolScene } = useGLTF("/models/ferramenta.glb"); // Missing

  // Clone scenes to avoid mutation issues if reused
  const model01 = useMemo(() => model01Scene.clone(), [model01Scene]);
  const model02 = useMemo(() => model02Scene.clone(), [model02Scene]);
  const model03 = useMemo(() => model03Scene.clone(), [model03Scene]);
  const model04 = useMemo(() => model04Scene.clone(), [model04Scene]);
  const baseModel = useMemo(() => baseScene.clone(), [baseScene]);

  // State for smooth joint movement
  const [currentJoints, setCurrentJoints] = useState({
    j1: j1_deg,
    j2: j2_deg,
    j3: j3_mm,
    j4: j4_deg,
  });

  // Apply orange color to model02
  useEffect(() => {
    model02.traverse((child) => {
      if (child.isMesh) {
        child.material = child.material.clone();
        child.material.color.set("#ff6b00");
      }
    });
  }, [model02]);

  // Apply split color (Black/Orange) to model03
  useEffect(() => {
    const box = new THREE.Box3().setFromObject(model03);
    const midY = (box.max.y + box.min.y) / 2;

    model03.traverse((child) => {
      if (child.isMesh) {
        child.material = child.material.clone();
        child.material.onBeforeCompile = (shader) => {
          shader.uniforms.colorBottom = { value: new THREE.Color("#111111") }; // Black
          shader.uniforms.colorTop = { value: new THREE.Color("#ff6b00") };    // Orange
          shader.uniforms.splitY = { value: midY }; // Split at center

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
        // Trigger re-compile
        child.material.needsUpdate = true;
      }
    });
  }, [model03]);

  // Apply black color to model01
  useEffect(() => {
    model01.traverse((child) => {
      if (child.isMesh) {
        child.material = child.material.clone();
        child.material.color.set("#111111");
      }
    });
  }, [model01]);

  // Update target joints when props change
  useEffect(() => {
    // We don't directly set currentJoints here, but rather let the dampening
    // function in useFrame catch up to these new target values.
    // For simplicity, we can just update the target values that useFrame will read.
    // A more robust solution might involve a separate ref for target values.
    // For now, we'll let the currentJoints state be the "target" for the next frame's damp.
    // This means the dampening will always be trying to reach the latest prop values.
  }, [j1_deg, j2_deg, j3_mm, j4_deg]);

  useFrame((state, delta) => {
    // Smooth dampening for fluid movement
    // lambda = smoothing factor (higher is faster/tighter, lower is smoother/looser)
    const lambda = 2.5;

    setCurrentJoints((prev) => ({
      j1: THREE.MathUtils.damp(prev.j1, j1_deg, lambda, delta),
      j2: THREE.MathUtils.damp(prev.j2, j2_deg, lambda, delta),
      j3: THREE.MathUtils.damp(prev.j3, j3_mm, lambda, delta),
      j4: THREE.MathUtils.damp(prev.j4, j4_deg, lambda, delta),
    }));
  });

  // Convert degrees to radians using damped values
  const j1_rad = THREE.MathUtils.degToRad(currentJoints.j1);
  const j2_rad = THREE.MathUtils.degToRad(currentJoints.j2);
  const j4_rad = THREE.MathUtils.degToRad(currentJoints.j4);

  // J3 is linear movement (Z-axis usually in SCARA for quill, but user said Y negative)
  // "Grupo Linear J3 (Move-se no eixo Y negativo baseado em j3_mm)"
  const j3_pos = Math.min(0, currentJoints.j3 / 20); // Clamp to 0 to prevent going above origin

  const [baseHeight, setBaseHeight] = useState(0);

  // Calculate base height to position robot on top
  useEffect(() => {
    if (baseModel) {
      // Sync scale and rotation for accurate measurement
      baseModel.scale.set(0.6, 0.6, 0.6);
      baseModel.rotation.set(0, Math.PI / 2, 0); // 90 degrees on Y
      baseModel.updateMatrixWorld(true);

      const scaledBox = new THREE.Box3().setFromObject(baseModel);
      setBaseHeight(scaledBox.max.y);
    }
  }, [baseModel]);

  // Apply darker gray color to base model
  useEffect(() => {
    if (baseModel) {
      baseModel.traverse((child) => {
        if (child.isMesh) {
          child.material = child.material.clone();
          child.material.color.set("#666666"); // Lighter gray
        }
      });
    }
  }, [baseModel]);

  return (
    <group dispose={null}>
      {/* Base (Static) */}
      <group position={[0, 6, 0]}>
        <primitive object={baseModel} scale={[1, 1, 1]} rotation={[0, Math.PI / 2, 0]} />
      </group>

      {/* Robot Group (01-04) positioned on top of base */}
      <group position={[0, baseHeight, 0]}>
        {/* Axis 1 Group (Rotates around Y) */}
        {/* Adjusted Y position to sit on top of BasePedestal */}
        {/* Axis 1 Group (Static Base Tower) */}
        {/* Adjusted Y position to sit on top of BasePedestal */}
        <group position={[0, 0, 0]}>
          {/* Model 01 (Above Base) */}
          <group position={[0, 0, 0]}> {/* Moved to 0 relative to group */}
            <primitive object={model01} scale={[0.1, 0.1, 0.1]} />

            {/* Model 02 (Above 01) */}
            <group position={[1, 18, -1]} rotation={[0, j1_rad, 0]}>
              <primitive object={model02} scale={[0.1, 0.1, 0.1]} />

              {/* Model 03 (Above 02) */}
              <group position={[37, 19, 0]} rotation={[0, j2_rad, 0]}>
                <primitive object={model03} scale={[0.1, 0.1, 0.1]} />

                {/* Model 04 (Above 03) - Fixed Rotation (-36deg) and Moves Vertically (J3) */}
                {/* Offset by -36 degrees for correct alignment, J4 rotation disabled */}
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

// Preload only existing models
useGLTF.preload("/models/01.glb");
useGLTF.preload("/models/02.glb");
useGLTF.preload("/models/03.glb");
useGLTF.preload("/models/04.glb");
useGLTF.preload("/models/base.glb");
