import { useState, useCallback } from "react";
import Intro    from "./components/Intro";
import Navbar   from "./components/Navbar";
import Scene3D  from "./components/Scene3D";
import Home     from "./pages/Home";
import News     from "./pages/News";
import Bias     from "./pages/Bias";
import Footer   from "./components/Footer";

function App() {
  const [showIntro, setShowIntro] = useState(true);
  const [page,      setPage]      = useState("home");

  const handleIntroDone = useCallback(() => setShowIntro(false), []);

  return (
    <>
      {/* Data-stream shimmer bar — always on top */}
      <div className="data-stream-bar" />

      {/* Three.js background scene — rotating icosahedron + particles
          Replaces the old CSS orb pseudo-elements.
          z-index: 0, pointer-events: none */}
      <Scene3D />

      {/* Fine grid overlay — sits on top of the 3D scene */}
      <div className="bg-grid" />

      {/* Intro splash with particle field */}
      {showIntro && <Intro onDone={handleIntroDone} />}

      {/* Main app shell */}
      <div
        className="app"
        style={{
          opacity:    showIntro ? 0 : 1,
          transition: "opacity 0.5s ease 0.1s",
        }}
      >
        <Navbar setPage={setPage} page={page} />

        <div className="page-content" key={page}>
          {page === "home" && <Home setPage={setPage} />}
          {page === "news" && <News />}
          {page === "bias" && <Bias />}
        </div>

        <Footer setPage={setPage} />
      </div>
    </>
  );
}

export default App;
