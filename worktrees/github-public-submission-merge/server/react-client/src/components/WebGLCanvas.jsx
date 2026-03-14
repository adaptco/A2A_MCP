import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

/**
 * WebGLCanvas Component
 * Renders the Game Engine state using Three.js for hardware acceleration.
 */
const WebGLCanvas = ({ gameState }) => {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);

  useEffect(() => {
    // 1. Initialize Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050505);
    sceneRef.current = scene;

    // Use OrthographicCamera for 2D pixel-art style rendering
    // Assuming engine coordinates are in pixels (0,0 top-left typically, but let's check)
    // Three.js standard: Y up. Engine Y seems to go up? 
    // Let's assume (0,0) is center or bottom-left. 
    // Sandbox uses positive coords like (300, 100).
    // Let's set (0,0) to bottom-left for now.

    // Width/Height from window
    const width = window.innerWidth;
    const height = window.innerHeight;

    // config: left, right, top, bottom, near, far
    // To match typical screen coords (0,0 top left, Y down), we do top=0, bottom=-height?
    // Or just flip Sprite Y.
    // Let's map 0..width, 0..height.
    const camera = new THREE.OrthographicCamera(0, width, height, 0, 0.1, 1000);
    camera.position.z = 10;

    const renderer = new THREE.WebGLRenderer({ antialias: false }); // Disable AA for crisp pixels
    renderer.setSize(width, height);
    mountRef.current.appendChild(renderer.domElement);

    // 2. Lights
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xffffff, 1, 100);
    pointLight.position.set(5, 5, 5);
    scene.add(pointLight);

    // 3. Simple Mock objects for Game State
    const geometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
    const material = new THREE.MeshPhongMaterial({ color: 0x00ff00 });
    const cube = new THREE.Mesh(geometry, material);
    scene.add(cube);

    // 4. WebSocket Connection
    // Connection to the Node.js server which proxies the C++ engine
    const ws = new WebSocket('ws://localhost:8080');

    ws.onopen = () => {
      console.log('Connected to Game Server');
    };

    // Map to track meshes
    const spriteMeshes = useRef(new Map());

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // console.log('Engine State:', data);

        if (data.type === 'render_frame' && data.sprites && Array.isArray(data.sprites)) {
          // Very naive rendering: Clear all and redraw
          // Optimizations would involve object pooling or updating existing meshes
          spriteMeshes.current.forEach(mesh => scene.remove(mesh));
          spriteMeshes.current.clear();

          data.sprites.forEach((sprite, i) => {
            const geometry = new THREE.PlaneGeometry(sprite.w, sprite.h);
            // Random color based on texture ID hash to differentiate
            // For now just green
            const material = new THREE.MeshBasicMaterial({ color: 0x00ff00, side: THREE.DoubleSide });
            const mesh = new THREE.Mesh(geometry, material);
            mesh.position.set(sprite.x, sprite.y, 0);
            scene.add(mesh);
            spriteMeshes.current.set(i, mesh);
          });
        }

      } catch (e) {
        // console.error('Failed to parse engine state:', e);
      }
    };

    ws.onclose = () => {
      console.log('Disconnected from Game Server');
    };

    const animate = () => {
      requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };

    animate();

    // 5. Cleanup
    return () => {
      ws.close();
      mountRef.current?.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
        zIndex: 1
      }}
    />
  );
};

export default WebGLCanvas;
