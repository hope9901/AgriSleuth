import WeatherPanel from "./WeatherPanel";
import type { InvestigationResult } from "../types/investigation";

interface InvestigationResultsProps {
  result: InvestigationResult | null;
  busy: boolean;
  region?: string;
}

const statusLabels: Record<InvestigationResult["status"], string> = {
  ready: "Inputs validated — analysis not connected",
  received: "Received",
  validating: "Validating observations",
  researching: "Researching evidence",
  reviewing: "Reviewing hypotheses",
  needs_input: "Additional information needed",
  completed: "Investigation completed",
  abstained: "Judgment withheld",
  failed: "Investigation failed",
};

function safeSourceUrl(value?: string): string | undefined {
  if (!value) return undefined;

  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export default function InvestigationResults({
  result,
  busy,
  region = "",
}: InvestigationResultsProps) {
  const statusText = busy
    ? "Submitting investigation…"
    : result
      ? statusLabels[result.status]
      : "Awaiting observations";

  const statusTone = busy
    ? "active"
    : result?.status === "completed"
      ? "success"
      : result?.status === "failed" || result?.status === "abstained"
        ? "warning"
        : "neutral";

  return (
    <div className="results-column">
      <section className="panel" aria-labelledby="progress-title">
        <header className="panel-heading">
          <div>
            <p className="eyebrow">02 / INVESTIGATION</p>
            <h2 id="progress-title">Investigation status</h2>
          </div>

          <span className={`status-badge status-badge--${statusTone}`}>
            <span className="status-dot" aria-hidden="true" />
            <span role="status" aria-live="polite">
              {statusText}
            </span>
          </span>
        </header>

        <p className="review-placeholder">
          {result?.summary ??
            "Submit observations to begin an evidence-based multi-agent investigation."}
        </p>

        {!result && !busy && (
          <ol className="workflow" aria-label="Agent workflow stages">
            <li>
              <span className="step-number">01</span>
              <div>
                <h3>Multimodal observation intake</h3>
                <p>
                  Validates crop selection, field metadata, and symptom
                  imagery.
                </p>
              </div>
              <span className="step-state">Ready</span>
            </li>
            <li>
              <span className="step-number">02</span>
              <div>
                <h3>Agronomic evidence retrieval</h3>
                <p>
                  Queries Korean rice and maize pathology literature and
                  weather context.
                </p>
              </div>
              <span className="step-state">Standby</span>
            </li>
            <li>
              <span className="step-number">03</span>
              <div>
                <h3>Critic verification loop</h3>
                <p>
                  Audits candidate hypotheses for unsupported claims or missing
                  differentials.
                </p>
              </div>
              <span className="step-state">Standby</span>
            </li>
          </ol>
        )}

        {result && (
          <small className="helper-text">Investigation ID: {result.id}</small>
        )}
      </section>

      <section
        id="evidence"
        className="panel"
        aria-labelledby="evidence-title"
      >
        <header className="panel-heading">
          <div>
            <p className="eyebrow">03 / SUPPORTING MATERIAL</p>
            <h2 id="evidence-title">Evidence &amp; hypotheses</h2>
          </div>
          {result && (
            <span className="subtle-label">
              {result.hypotheses.length} candidate
              {result.hypotheses.length === 1 ? "" : "s"}
            </span>
          )}
        </header>

        {!result?.hypotheses.length ? (
          <div className="empty-state">
            <div className="empty-symbol" aria-hidden="true">
              ◈
            </div>
            <h3>No hypotheses available</h3>
            <p>
              Supported diagnostic candidates and cited evidence will appear
              here once the investigation runs.
            </p>
          </div>
        ) : (
          <div className="cards-stack">
            {result.hypotheses.map((hypothesis) => (
              <article className="result-card" key={hypothesis.id}>
                <div className="result-card-header">
                  <h3>{hypothesis.name}</h3>
                  <span className="tag">{hypothesis.id}</span>
                </div>
                <p>{hypothesis.reasoning}</p>
                <small className="evidence-citation">
                  Evidence: {hypothesis.evidenceIds.join(", ") || "None cited"}
                </small>
              </article>
            ))}
          </div>
        )}

        {Boolean(result?.evidence.length) && (
          <div className="evidence-list">
            <h3>Sources</h3>

            <div className="cards-stack">
              {result?.evidence.map((source) => {
                const href = safeSourceUrl(source.url);

                return (
                  <article className="result-card" key={source.id}>
                    <h4>
                      {href ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {source.title} ↗
                        </a>
                      ) : (
                        source.title
                      )}
                    </h4>
                    <p>{source.excerpt}</p>
                    <small>
                      {source.id}
                      {source.location ? ` · ${source.location}` : ""}
                    </small>
                  </article>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {result && <WeatherPanel key={result.id} investigationId={result.id} initialRegion={region} />}

      <section id="review" className="panel" aria-labelledby="review-title">
        <header className="panel-heading">
          <div>
            <p className="eyebrow">04 / REVIEW</p>
            <h2 id="review-title">What should be verified next?</h2>
          </div>
        </header>

        <p className="review-placeholder">
          {result?.nextAction ??
            "The next verification step will appear after review."}
        </p>

        {Boolean(result?.reviewIssues.length) && (
          <div className="cards-stack">
            {result?.reviewIssues.map((issue) => (
              <article className="result-card" key={issue.id}>
                <span
                  className={`severity-badge severity-badge--${issue.severity}`}
                >
                  {issue.severity}
                </span>
                <p>{issue.reason}</p>
              </article>
            ))}
          </div>
        )}

        {Boolean(result?.questions.length) && (
          <div className="review-subsection">
            <h3>Additional observations requested</h3>
            <ul className="result-list">
              {result?.questions.map((question, index) => (
                <li key={`${index}-${question}`}>{question}</li>
              ))}
            </ul>
          </div>
        )}

        {Boolean(result?.limitations.length) && (
          <div className="review-subsection">
            <h3>Limitations</h3>
            <ul className="result-list">
              {result?.limitations.map((limitation, index) => (
                <li key={`${index}-${limitation}`}>{limitation}</li>
              ))}
            </ul>
          </div>
        )}

        <details className="trace-details">
          <summary>Execution history</summary>

          {!result?.events.length ? (
            <p>No execution events have been received.</p>
          ) : (
            <ol className="result-list trace-list">
              {result.events.map((event) => (
                <li key={event.id}>
                  <div className="trace-event-head">
                    <strong>{event.node}</strong>
                    <time dateTime={event.timestamp}>{event.timestamp}</time>
                  </div>
                  <p>{event.summary}</p>
                </li>
              ))}
            </ol>
          )}
        </details>
      </section>

      <aside className="boundary-note">
        <strong>Evidence-based support</strong>
        <p>
          Findings are investigation hypotheses generated for the Open Agent
          Hackathon 2026 prototype. Field confirmation may require additional
          observations or laboratory testing.
        </p>
      </aside>
    </div>
  );
}
