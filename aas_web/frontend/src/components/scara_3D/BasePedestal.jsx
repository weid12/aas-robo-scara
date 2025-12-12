import React from "react";

const BasePedestal = ({ baseHeight = 20 }) => {
  // Stäubli TS2-80 Base approximation
  // Taller, more slender cylinder with a flared base.

  return (
    <group>
      {/* Bottom Flange/Foot */}
      <mesh castShadow position={[0, 2, 0]}>
        <cylinderGeometry args={[10, 14, 4, 32]} />
        <meshStandardMaterial color="#f5c400" />
      </mesh>

      {/* Main Column */}
      {/* The base height in the reference is substantial. */}
      <mesh castShadow position={[0, 12 + 2, 0]}>
        <cylinderGeometry args={[9, 10, 24, 32]} />
        <meshStandardMaterial color="#f5c400" />
      </mesh>

      {/* Upper Flange (Joint 1 Base) */}
      <mesh castShadow position={[0, 24 + 4, 0]}>
        <cylinderGeometry args={[10, 9, 6, 32]} />
        <meshStandardMaterial color="#f5c400" />
      </mesh>

      {/* Connector details (Cable ports etc - simplified as dark patches) */}
      <mesh position={[0, 8, 9.5]}>
        <boxGeometry args={[4, 6, 1]} />
        <meshStandardMaterial color="#333" />
      </mesh>
    </group>
  );
};

export default BasePedestal;
