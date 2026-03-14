import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Color } from 'three';
import { MeshStandardMaterial } from 'three';

// For a true custom shader, we'd use shaderMaterial from drei
// but for MVP robustness, we can achieve a "toon-ish" look with
// Standard material + high roughness + specific lighting
// OR implement the custom shader provided in the prompt.

import { shaderMaterial } from "@react-three/drei";
import * as THREE from "three";
import { extend } from "@react-three/fiber";

const ToonShaderMaterial = shaderMaterial(
  { color: new THREE.Color("#ff5500") },
  // Vertex Shader
  `
    varying vec3 vNormal;
    void main() {
      vNormal = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);
    }
  `,
  // Fragment Shader
  `
    uniform vec3 color;
    varying vec3 vNormal;
    void main() {
      float intensity = dot(vNormal, vec3(0.0, 0.0, 1.0));
      // Cel shading steps
      float shade = 1.0;
      if (intensity < 0.5) shade = 0.6;
      if (intensity < 0.25) shade = 0.4;

      gl_FragColor = vec4(color * shade, 1.0);
    }
  `
);

extend({ ToonShaderMaterial });

// React component wrapper
export default function ToonMaterial({ color }: { color: string }) {
  // @ts-ignore - ToonShaderMaterial is added to JSX via extend
  return <toonShaderMaterial color={new THREE.Color(color)} />;
}
