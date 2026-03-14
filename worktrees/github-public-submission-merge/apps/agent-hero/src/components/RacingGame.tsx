import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import Car from './3d/Car';
import Track from './3d/Track';
import HUD from './HUD';

export default function RacingGame() {
  return (
    <div className="relative w-full h-full bg-gradient-to-b from-orange-900 to-black">
      <Canvas
        shadows
        camera={{ position: [0, 5, 10], fov: 60 }}
        className="touch-none"
      >
        <PerspectiveCamera makeDefault position={[0, 8, 12]} fov={50} />
        <OrbitControls
          enableZoom={false}
          maxPolarAngle={Math.PI / 2.5}
          minPolarAngle={Math.PI / 3}
        />

        {/* Cel-Shaded Lighting */}
        <ambientLight intensity={0.6} />
        <directionalLight
          position={[10, 20, 10]}
          intensity={1.5}
          castShadow
          shadow-mapSize={[1024, 1024]}
        />

        <Track />
        <Car />

        {/* Environment - Simple Ground */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
          <planeGeometry args={[100, 100]} />
          <meshStandardMaterial color="#1a1a1a" />
        </mesh>

        {/* Fog for depth */}
        <fog attach="fog" args={['#000', 10, 40]} />
      </Canvas>
      <HUD />
    </div>
  );
}
