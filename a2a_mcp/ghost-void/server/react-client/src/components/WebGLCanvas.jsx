import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

export function WebGLCanvas({ gameState, sendInput }) {
    const mountRef = useRef(null);
    const sceneRef = useRef(null);
    const cameraRef = useRef(null);
    const rendererRef = useRef(null);
    const avatarRef = useRef(null);
    const floorRef = useRef(null);

    // Initial Setup
    useEffect(() => {
        const mount = mountRef.current;
        const width = 800;
        const height = 600;

        // Scene
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0a0a);
        sceneRef.current = scene;

        // Camera
        const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        camera.position.z = 400;
        camera.position.y = 300;
        camera.lookAt(400, 300, 0);
        cameraRef.current = camera;

        // Renderer
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(width, height);
        mount.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);
        const pointLight = new THREE.PointLight(0xffffff, 1);
        pointLight.position.set(400, 500, 200);
        scene.add(pointLight);

        // Avatar (Blue Cube)
        const geometry = new THREE.BoxGeometry(30, 30, 30);
        const material = new THREE.MeshStandardMaterial({ color: 0x0066ff });
        const avatar = new THREE.Mesh(geometry, material);
        scene.add(avatar);
        avatarRef.current = avatar;

        // Floor
        const floorGeo = new THREE.BoxGeometry(800, 100, 100);
        const floorMat = new THREE.MeshStandardMaterial({ color: 0x444444 });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.position.set(400, 550, 0); // Y is down in engine
        scene.add(floor);
        floorRef.current = floor;

        // Animation Loop
        const animate = () => {
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        };
        animate();

        return () => {
            mount.removeChild(renderer.domElement);
            renderer.dispose();
        };
    }, []);

    // Update Avatar Position from Engine State
    useEffect(() => {
        if (gameState && gameState.avatar && avatarRef.current) {
            // Coordinate mapping: Engine (0-800, 0-600) to Three.js
            avatarRef.current.position.x = gameState.avatar.x;
            avatarRef.current.position.y = gameState.avatar.y;
        }
    }, [gameState]);

    // Input Handling
    useEffect(() => {
        const keys = {};
        const handleDown = (e) => {
            keys[e.code] = true;
            pushInput();
        };
        const handleUp = (e) => {
            keys[e.code] = false;
            pushInput();
        };
        const pushInput = () => {
            sendInput({
                left: keys['ArrowLeft'] || false,
                right: keys['ArrowRight'] || false,
                jump: keys['Space'] || keys['ArrowUp'] || false,
                shoot: keys['KeyZ'] || false
            });
        };
        window.addEventListener('keydown', handleDown);
        window.addEventListener('keyup', handleUp);
        return () => {
            window.removeEventListener('keydown', handleDown);
            window.removeEventListener('keyup', handleUp);
        };
    }, [sendInput]);

    return (
        <div 
            ref={mountRef} 
            style={{ 
                width: '800px', 
                height: '600px', 
                border: '4px solid #333',
                backgroundColor: '#000'
            }} 
        />
    );
}
