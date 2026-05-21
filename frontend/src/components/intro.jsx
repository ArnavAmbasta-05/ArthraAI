import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

/* ─── Three.js particle field ────────────────────────────
   ~600 particles in 3D space, gold + cyan tinted,
   slowly drifting outward from center.
   Mounted on a canvas behind the logo text.
   Disposed cleanly when intro unmounts.
──────────────────────────────────────────────────────── */
function ParticleField({ canvasRef }) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setClearColor(0x000000, 0);

    // Scene + camera
    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, canvas.clientWidth / canvas.clientHeight, 0.1, 100);
    camera.position.z = 5;

    // Geometry — 600 random points in a sphere
    const COUNT    = 600;
    const positions = new Float32Array(COUNT * 3);
    const colors    = new Float32Array(COUNT * 3);

    const goldColor = new THREE.Color("#d4af37");
    const cyanColor = new THREE.Color("#38bdf8");

    for (let i = 0; i < COUNT; i++) {
      // Spherical distribution
      const r     = 2 + Math.random() * 4;
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1);

      positions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);

      // Mix gold and cyan based on position
      const mix   = Math.random();
      const color = goldColor.clone().lerp(cyanColor, mix * 0.4);
      colors[i * 3]     = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color",    new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size:         0.04,
      vertexColors: true,
      transparent:  true,
      opacity:      0.75,
      sizeAttenuation: true,
    });

    const points = new THREE.Points(geo, mat);
    scene.add(points);

    // Slow rotation
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      points.rotation.y += 0.0008;
      points.rotation.x += 0.0003;
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const onResize = () => {
      if (!canvas) return;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      geo.dispose();
      mat.dispose();
    };
  }, [canvasRef]);

  return null;
}

/* ─── Intro component ────────────────────────────────── */
export default function Intro({ onDone }) {
  const [gone,   setGone]   = useState(false);
  const canvasRef            = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setGone(true);
      onDone();
    }, 4400);
    return () => clearTimeout(t);
  }, [onDone]);

  if (gone) return null;

  return (
    <div className="intro-page">
      {/* Three.js canvas — fills entire intro */}
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          pointerEvents: "none",
        }}
      />
      <ParticleField canvasRef={canvasRef} />

      {/* Legacy radial pulse — keep as a soft secondary glow */}
      <div className="intro-bg" />

      <div className="intro-content">
        <div className="intro-logo">
          <span className="intro-logo-main">Arthra</span>
          <span className="intro-logo-ai">AI</span>
        </div>
        <p className="intro-tagline">Financial Intelligence · Decoded</p>
        <div className="intro-line" />
        <div className="intro-loader">
          <div className="intro-dot" />
          <div className="intro-dot" />
          <div className="intro-dot" />
        </div>
      </div>
    </div>
  );
}