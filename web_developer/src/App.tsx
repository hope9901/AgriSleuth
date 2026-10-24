import InvestigationWorkspace from "./components/InvestigationWorkspace";
import { submitInvestigation } from "./api/investigations";
import "./styles.css";

export default function App() {
  return (
    <>
      {/* Keep your existing header here. */}

      <main id="main" className="workspace">
        <section className="page-heading">
          <div>
            <p className="eyebrow">CROP HEALTH INVESTIGATION</p>
            <h1>Observe. Investigate. Verify.</h1>
            <p className="intro">
              Connect field observations with evidence.
              Understand what to check next.
            </p>
          </div>

          <span className="scope-badge">
            South Korea · Rice & Maize
          </span>
        </section>

        <InvestigationWorkspace onSubmit={submitInvestigation} />
      </main>

      {/* Keep your existing footer here. */}
    </>
  );
}
