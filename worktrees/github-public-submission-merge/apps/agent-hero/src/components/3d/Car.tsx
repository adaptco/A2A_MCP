import React, { useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import { Vector3, MathUtils } from 'three';
import ToonMaterial from './ToonMaterial';

export default function Car() {
  const meshRef = useRef<any>(null);
  const [speed, setSpeed] = useState(0);
  const [turning, setTurning] = useState(0);

  useFrame((state, delta) => {
    // Basic movement simulation
    setSpeed((s) => Math.min(s + delta * 5, 20)); // Accelerate

    // Simple steering simulation (sine wave for demo)
    const time = state.clock.getElapsedTime();
    const steer = Math.sin(time * 0.5) * 0.5; // Auto-steer
    setTurning(steer);

    // Apply rotation
    if (meshRef.current) {
      // Rotation
      meshRef.current.rotation.y = -steer * 0.5;

      // Banking effect (lean into turn)
      meshRef.current.rotation.z = MathUtils.lerp(
        meshRef.current.rotation.z,
        steer * 0.2,
        delta * 5
      );

      // Pitch effect (acceleration squat)
      meshRef.current.rotation.x = MathUtils.lerp(
        meshRef.current.rotation.x,
        -speed * 0.005,
        delta * 2
      );
    }
  });

  return (
    <group ref={meshRef} position={[0, 0.5, 0]}>
      {/* Car Body */}
      <mesh castShadow receiveShadow>
        <boxGeometry args={[1, 0.6, 2.2]} />
        <ToonMaterial color="#ff4500" />
      </mesh>

      {/* Roof/Cabin */}
      <mesh position={[0, 0.6, -0.2]} castShadow>
        <boxGeometry args={[0.8, 0.5, 1.2]} />
        <ToonMaterial color="#222" />
      </mesh>

      {/* Wheels */}
      <Wheel position={[0.6, -0.3, 0.7]} />
      <Wheel position={[-0.6, -0.3, 0.7]} />
      <Wheel position={[0.6, -0.3, -0.8]} />
      <Wheel position={[-0.6, -0.3, -0.8]} />

      {/* Headlights */}
      <mesh position={[0.3, 0, 1.15]}>
        <boxGeometry args={[0.2, 0.1, 0.1]} />
        <meshStandardMaterial color="#fff" emissive="#fff" emissiveIntensity={2} />
      </mesh>
      <mesh position={[-0.3, 0, 1.15]}>
        <boxGeometry args={[0.2, 0.1, 0.1]} />
        <meshStandardMaterial color="#fff" emissive="#fff" emissiveIntensity={2} />
      </mesh>

      {/* Tail Lights */}
      <mesh position={[0, 0.1, -1.11]}>
         <boxGeometry args={[0.8, 0.1, 0.1]} />
         <meshStandardMaterial color="#ff0000" emissive="#ff0000" emissiveIntensity={1} />
      </mesh>
    </group>
  );
}

function Wheel({ position }: { position: [number, number, number] }) {
  const wheelRef = useRef<any>(null);

  useFrame((state, delta) => {
    if (wheelRef.current) {
      wheelRef.current.rotation.x += delta * 10; // Spin wheels
    }
  });

  // Rotation [0, 0, Math.PI / 2] aligns cylinder to be a wheel
  return (
    <mesh ref={wheelRef} position={position} rotation={[0, 0, Math.PI / 2]} castShadow>
      <cylinderGeometry args={[0.3, 0.3, 0.2, 16]} />
      <meshStandardMaterial color="#111" />
    </mesh>
  );
}
