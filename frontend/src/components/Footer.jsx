export default function Footer({ setPage }) {
  return (
    <footer className="footer">
      <div className="footer-grid">
        <div className="footer-brand">
          <div className="logo" style={{ cursor: "default" }}>
            <span className="logo-main">Arthra</span>
            <span className="logo-ai">AI</span>
          </div>
          <p>
            AI-powered financial intelligence delivering
            real-time market sentiment and news analysis across
            Indian and global markets.
          </p>
        </div>

        <div className="footer-col">
          <h4>Navigate</h4>
          <p onClick={() => setPage("home")}>Home</p>
          <p onClick={() => setPage("news")}>Markets</p>
          <p onClick={() => setPage("bias")}>Bias Score</p>
        </div>

        <div className="footer-col">
          <h4>Markets</h4>
          <p>NSE / BSE</p>
          <p>NYSE / NASDAQ</p>
          <p>Commodities</p>
          <p>Indices</p>
        </div>

        <div className="footer-col">
          <h4>Company</h4>
          <p>About</p>
          <p>Methodology</p>
          <p>Contact</p>
        </div>
      </div>

      <div className="footer-bottom">
        <p>© 2026 <span>ArthraAI</span> · Financial Intelligence Platform</p>
        <p style={{ fontFamily: "var(--font-mono)", fontSize: "9px", letterSpacing: "1.5px" }}>
          NOT FINANCIAL ADVICE · AI-GENERATED ANALYSIS
        </p>
      </div>
    </footer>
  );
}