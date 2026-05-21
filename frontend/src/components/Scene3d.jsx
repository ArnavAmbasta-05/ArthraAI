import { useEffect, useRef } from "react";
import * as THREE from "three";

/* ─── Background 3D scene ────────────────────────────────
   A large wireframe icosahedron slowly rotating in deep
   background. Gold-tinted edges, very low opacity.
   Stays fixed behind all page content.
   Pointer-events: none — completely non-interactive.
──────────────────────────────────────────────────────── */
export default function Scene3D() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha:     true,
      antialias: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);
    camera.position.set(0, 0, 14);

    // ── Main icosahedron (wireframe) ──────────────────────
    const icoGeo = new THREE.IcosahedronGeometry(5, 1);
    const icoMat = new THREE.MeshBasicMaterial({
      color:     0xd4af37,
      wireframe: true,
      opacity:   0.06,
      transparent: true,
    });
    const ico = new THREE.Mesh(icoGeo, icoMat);
    scene.add(ico);

    // ── Inner icosahedron — slightly smaller, cyan ────────
    const icoGeo2 = new THREE.IcosahedronGeometry(3.2, 1);
    const icoMat2 = new THREE.MeshBasicMaterial({
      color:     0x38bdf8,
      wireframe: true,
      opacity:   0.035,
      transparent: true,
    });
    const ico2 = new THREE.Mesh(icoGeo2, icoMat2);
    scene.add(ico2);

    // ── Floating point cloud (sparse, far back) ───────────
    const ptCount = 200;
    const ptPos   = new Float32Array(ptCount * 3);
    for (let i = 0; i < ptCount; i++) {
      ptPos[i * 3]     = (Math.random() - 0.5) * 30;
      ptPos[i * 3 + 1] = (Math.random() - 0.5) * 20;
      ptPos[i * 3 + 2] = (Math.random() - 0.5) * 10 - 5;
    }
    const ptGeo = new THREE.BufferGeometry();
    ptGeo.setAttribute("position", new THREE.BufferAttribute(ptPos, 3));
    const ptMat = new THREE.PointsMaterial({
      color:       0xd4af37,
      size:        0.05,
      transparent: true,
      opacity:     0.4,
    });
    scene.add(new THREE.Points(ptGeo, ptMat));

    // ── Mouse parallax ────────────────────────────────────
    let mouseX = 0, mouseY = 0;
    const onMouseMove = (e) => {
      mouseX = (e.clientX / window.innerWidth  - 0.5) * 2;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMouseMove);

    // ── Animation loop ────────────────────────────────────
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);

      // Slow auto-rotation
      ico.rotation.x  += 0.0006;
      ico.rotation.y  += 0.0009;
      ico2.rotation.x -= 0.0004;
      ico2.rotation.y -= 0.0007;

      // Gentle parallax on mouse
      ico.rotation.y  += mouseX * 0.0003;
      ico.rotation.x  += mouseY * 0.0002;

      renderer.render(scene, camera);
    };
    animate();

    // ── Resize ────────────────────────────────────────────
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize",    onResize);
      renderer.dispose();
      icoGeo.dispose();  icoMat.dispose();
      icoGeo2.dispose(); icoMat2.dispose();
      ptGeo.dispose();   ptMat.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position:      "fixed",
        inset:         0,
        width:         "100%",
        height:        "100%",
        pointerEvents: "none",
        zIndex:        0,
        opacity:       0.9,
      }}
    />
  );
}