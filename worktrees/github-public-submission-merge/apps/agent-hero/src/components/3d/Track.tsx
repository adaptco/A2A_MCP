import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useLoader } from '@react-three/fiber';
import { TextureLoader } from 'three';

export default function Track() {
  const roadRef = useRef<any>(null);

  // Simple infinite scroll effect or large static track
  useFrame((state, delta) => {
    // Scroll texture or move segments
    // For MVP: Static procedural track
  });

  return (
    <group>
      {/* Road Surface */}
      <mesh receiveShadow rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -50]}>
        <planeGeometry args={[20, 200]} />
        <meshStandardMaterial color="#333" roughness={0.8} />
      </mesh>

      {/* Track Markings (Stripes) */}
      {Array.from({ length: 20 }).map((_, i) => (
        <mesh
          key={i}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[0, 0.01, -i * 10 + 50]}
        >
          <planeGeometry args={[0.5, 4]} />
          <meshBasicMaterial color="#fff" />
        </mesh>
      ))}

      {/* Side Barriers */}
      <mesh position={[10.5, 1, -50]}>
        <boxGeometry args={[1, 2, 200]} />
        <meshStandardMaterial color="#ff0000" emissive="#500" emissiveIntensity={0.5} />
      </mesh>
      <mesh position={[-10.5, 1, -50]}>
        <boxGeometry args={[1, 2, 200]} />
        <meshStandardMaterial color="#ff0000" emissive="#500" emissiveIntensity={0.5} />
      </mesh>

      {/* Decorative Neon Signs */}
      <NeonSign position={[15, 5, -20]} color="#0ff" text="NEO-TOKYO" />
      <NeonSign position={[-15, 8, -60]} color="#f0f" text="DRIFT CORP" />
      <NeonSign position={[12, 6, -100]} color="#ff0" text="SPEED" />
    </group>
  );
}

function NeonSign({ position, color, text }: { position: [number, number, number], color: string, text: string }) {
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[8, 4, 0.2]} />
        <meshStandardMaterial color="#111" />
      </mesh>
      <mesh position={[0, 0, 0.15]}>
        <boxGeometry args={[7.5, 3.5, 0.1]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2} toneMapped={false} />
      </mesh>
      {/* Text would require FontLoader, keeping simple for now */}
    </group>
  );
}
