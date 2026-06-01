import { useState, useCallback } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Intro    from "./components/intro";
import Navbar   from "./components/Navbar";
import Scene3D  from "./components/Scene3d";
import Home     from "./pages/Home";
import News     from "./pages/News";
import Bias     from "./pages/Bias";
import Footer   from "./components/Footer";

function AppLayout({ showIntro }) {
  const location = useLocation();
 
  return (
    <div
      className="app"
      style={{
        opacity:    showIntro ? 0 : 1,
        transition: "opacity 0.5s ease 0.1s",
      }}
    >
      <Navbar />
 
      {/* key=pathname re-mounts page on route change → triggers fadeUp animation */}
      <div className="page-content" key={location.pathname}>
        <Routes>
          <Route path="/"        element={<Home />} />
          <Route path="/markets" element={<News />} />
          <Route path="/bias"    element={<Bias />} />
          {/* Catch-all → home */}
          <Route path="*"        element={<Home />} />
        </Routes>
      </div>
 
      <Footer />
    </div>
  );
}
 
/* ─── Root app ──────────────────────────────────────────── */
export default function App() {
  const [showIntro, setShowIntro] = useState(true);
  const handleIntroDone = useCallback(() => setShowIntro(false), []);
 
  return (
    <BrowserRouter>
      {/* Data-stream shimmer bar */}
      <div className="data-stream-bar" />
 
      {/* Three.js background */}
      <Scene3D />
 
      {/* Fine grid overlay */}
      <div className="bg-grid" />
 
      {/* Intro splash */}
      {showIntro && <Intro onDone={handleIntroDone} />}
 
      {/* Main app */}
      <AppLayout showIntro={showIntro} />
    </BrowserRouter>
  );
}