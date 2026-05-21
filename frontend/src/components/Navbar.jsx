export default function Navbar({ setPage, page }) {
  const links = [
    { id: "home",  label: "Home"       },
    { id: "news",  label: "Markets"    },
    { id: "bias",  label: "Bias Score" },
  ];

  return (
    <header className="navbar">
      <div className="logo" onClick={() => setPage("home")}>
        <span className="logo-main">Arthra</span>
        <span className="logo-ai">AI</span>
      </div>

      <nav className="nav-links">
        {links.map(({ id, label }) => (
          <button
            key={id}
            className={page === id ? "active" : ""}
            onClick={() => setPage(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className="nav-markets-tag">NSE &nbsp;·&nbsp; BSE &nbsp;·&nbsp; NYSE</div>
    </header>
  );
}
