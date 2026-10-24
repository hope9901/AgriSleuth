import type { InvestigationResult } from "../types/investigation";

interface InvestigationResultsProps {
  result: InvestigationResult | null;
  busy: boolean;
}

const statusLabels: Record<InvestigationResult["status"], string> = {
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
    return ["http:", "https:"].includes(url.protocol)
      ? url.href
      : undefined;
  } catch {
    return undefined;
  }
}

export default function InvestigationResults({
  result,
  busy,
}: InvestigationResultsProps) {
  return (
    <div className="results-column">
      <section className="panel" aria-labelledby="progress-title">
        <header className="panel-heading">
          <div>
            <p className="eyebrow">02 / INVESTIGATION</p>
            <h2 id="progress-title">Investigation status</h2>
          </div>
        </header>

        <p role="status" aria-live="polite">
          {busy
            ? "Submitting investigation…"
            : result
              ? statusLabels[result.status]
              : "Awaiting observations"}
        </p>

        <p className="review-placeholder">
          {result?.summary ??
            "Submit observations to begin an evidence-based investigation."}
        </p>

        {result && (
          <small className="helper-text">
            Investigation ID: {result.id}
          </small>
        )}
      </section>

      <section id="evidence" className="panel">
        <header className="panel-heading">
          <div>
            <p className="eyebrow">03 / SUPPORTING MATERIAL</p>
            <h2>Evidence & hypotheses</h2>
          </div>
        </header>

        {!result?.hypotheses.length ? (
          <div className="empty-state">
            <h3>No hypotheses available</h3>
            <p>Supported candidates will appear here when available.</p>
          </div>
        ) : (
          result.hypotheses.map((hypothesis) => (
            <article className="result-card" key={hypothesis.id}>
              <h3>{hypothesis.name}</h3>
              <p>{hypothesis.reasoning}</p>
              <small>
                Evidence: {hypothesis.evidenceIds.join(", ") || "None cited"}
              </small>
            </article>
          ))
        )}

        {Boolean(result?.evidence.length) && (
          <div className="evidence-list">
            <h3>Sources</h3>

            {result?.evidence.map((source) => {
              const href = safeSourceUrl(source.url);

              return (
                <article className="result-card" key={source.id}>
                  <h4>
                    {href ? (
                      <a href={href} target="_blank" rel="noopener noreferrer">
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
        )}
      </section>

      <section id="review" className="panel">
        <header className="panel-heading">
          <div>
            <p className="eyebrow">04 / REVIEW</p>
            <h2>What should be verified next?</h2>
          </div>
        </header>

        <p className="review-placeholder">
          {result?.nextAction ??
            "The next verification step will appear after review."}
        </p>

        {result?.reviewIssues.map((issue) => (
          <article className="result-card" key={issue.id}>
            <span className="">{issue.severity}</span>
            <p>{issue.reason}</p>
          </article>
        ))}

        {Boolean(result?.questions.length) && (
          <>
            <h3>Additional observations requested</h3>
            <ul className="result-list">
              {result?.questions.map((question, index) => (
                <li key={`${index}-${question}`}>{question}</li>
              ))}
            </ul>
          </>
        )}

        {Boolean(result?.limitations.length) && (
          <>
            <h3>Limitations</h3>
            <ul className="result-list">
              {result?.limitations.map((limitation, index) => (
                <li key={`${index}-${limitation}`}>{limitation}</li>
              ))}
            </ul>
          </>
        )}

        <details className="trace-details">
          <summary>Execution history</summary>

          {!result?.events.length ? (
            <p>No execution events have been received.</p>
          ) : (
            <ol className="result-list">
              {result.events.map((event) => (
                <li key={event.id}>
                  <strong>{event.node}</strong>
                  <p>{event.summary}</p>
                  <time dateTime={event.timestamp}>
                    {event.timestamp}
                  </time>
                </li>
              ))}
            </ol>
          )}
        </details>
      </section>

      <aside className="boundary-note">
        <strong>Evidence-based support</strong>
        <p>
          Findings are investigation hypotheses. Confirmation may require
          additional observations or laboratory testing.
        </p>
      </aside>
    </div>
  );
}
