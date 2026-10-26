import { useEffect, useRef, useState } from "react";
import InvestigationWorkspace from "./components/InvestigationWorkspace";
import { submitInvestigation } from "./api/investigations";
import "./styles.css";

const PROJECT_METADATA = {
  projectName: "AgriSleuth",
  hackathonName: "Open Agent Hackathon 2026",
  scopeLabel: "Track 2 · Explain Why · Rice & Maize",
  contactEmail: "hope9901@gmail.com",
  githubUrl: "https://github.com/hope9901/AgriSleuth",
  githubDisplay: "github.com/hope9901/AgriSleuth",
};

export default function App() {
  const [emailCopied, setEmailCopied] = useState(false);
  const copyTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (copyTimerRef.current !== null) {
        window.clearTimeout(copyTimerRef.current);
      }
    };
  }, []);

  async function handleCopyEmail() {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(PROJECT_METADATA.contactEmail);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = PROJECT_METADATA.contactEmail;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }

      setEmailCopied(true);
      if (copyTimerRef.current !== null) {
        window.clearTimeout(copyTimerRef.current);
      }
      copyTimerRef.current = window.setTimeout(() => {
        setEmailCopied(false);
      }, 2000);
    } catch {
      // Ignore if clipboard permission is denied
    }
  }

  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to investigation workspace
      </a>

      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand-group">
            <a href="#main" className="brand" aria-label="AgriSleuth home">
              <span className="brand-mark" aria-hidden="true">
                ✦
              </span>
              <span className="brand-text">
                {PROJECT_METADATA.projectName}
                <span className="brand-dot">.</span>
              </span>
            </a>
            <span className="hackathon-pill">
              <span className="pulse-dot" aria-hidden="true" />
              {PROJECT_METADATA.hackathonName}
            </span>
          </div>

          <nav aria-label="Workspace sections" className="topbar-nav">
            <a href="#observation">01 Observations</a>
            <a href="#progress-title">02 Status</a>
            <a href="#evidence">03 Evidence</a>
            <a href="#review">04 Review</a>
          </nav>

          <div className="topbar-actions">
            <a
              href={PROJECT_METADATA.githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="topbar-link"
            >
              GitHub ↗
            </a>
          </div>
        </div>
      </header>

      <main id="main" className="workspace">
        <section className="page-heading">
          <div className="hero-copy">
            <div className="hero-badges">
              <p className="eyebrow">
                MULTI-AGENT CROP HEALTH INVESTIGATION ·{" "}
                {PROJECT_METADATA.hackathonName.toUpperCase()}
              </p>
            </div>
            <h1>Observe. Investigate. Verify.</h1>
            <p className="intro">
              <strong>{PROJECT_METADATA.projectName}</strong> connects field
              observations and symptom imagery with agronomic evidence through a
              self-reflective multi-agent workflow—helping growers and
              researchers understand both candidate diagnoses and what to verify
              next.
            </p>
          </div>

          <div className="hero-meta">
            <span className="scope-badge">
              <span className="scope-indicator" aria-hidden="true" />
              {PROJECT_METADATA.scopeLabel}
            </span>
            <div className="agent-pill-row" aria-label="Agent pipeline stages">
              <span className="tag">Vision &amp; Intake</span>
              <span className="tag">RAG Evidence</span>
              <span className="tag">Critic Loop</span>
            </div>
          </div>
        </section>

        <InvestigationWorkspace onSubmit={submitInvestigation} />
      </main>

      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-brand-col">
            <div className="footer-title-row">
              <span className="brand-mark brand-mark--sm" aria-hidden="true">
                ✦
              </span>
              <strong>{PROJECT_METADATA.projectName}</strong>
              <span className="footer-badge">
                {PROJECT_METADATA.hackathonName}
              </span>
            </div>
            <p className="footer-description">
              Evidence-grounded multi-agent diagnostic workspace for rice and
              maize crop pathology in South Korea.
            </p>
          </div>

          <div className="footer-links-col">
            <div className="footer-contact-group">
              <span className="footer-label">Contact &amp; Repository</span>
              <div className="footer-links">
                <div className="copy-email-wrapper">
                  <button
                    type="button"
                    onClick={() => void handleCopyEmail()}
                    className={`footer-link footer-copy-button ${
                      emailCopied ? "footer-copy-button--copied" : ""
                    }`}
                    aria-label={`Copy email address ${PROJECT_METADATA.contactEmail}`}
                  >
                    <span aria-hidden="true">{emailCopied ? "✓" : "✉"}</span>
                    <span>{PROJECT_METADATA.contactEmail}</span>
                  </button>
                  <span
                    className={`copy-toast ${
                      emailCopied ? "copy-toast--visible" : ""
                    }`}
                    role="status"
                    aria-live="polite"
                  >
                    {emailCopied ? "Copied to clipboard!" : ""}
                  </span>
                </div>

                <a
                  href={PROJECT_METADATA.githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="footer-link"
                >
                  <span aria-hidden="true">⌘</span>
                  <span>{PROJECT_METADATA.githubDisplay} ↗</span>
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <span>
            © 2026 {PROJECT_METADATA.projectName} · Submitted to{" "}
            {PROJECT_METADATA.hackathonName}
          </span>
          <span>
            Research &amp; decision-support prototype · Verify critical cases
            with local agricultural extension services
          </span>
        </div>
      </footer>
    </div>
  );
}
