import { useState } from "react";
import type { FormEvent } from "react";
import type {
  Crop,
  InvestigationInput,
} from "../types/investigation";

interface ObservationFormProps {
  busy: boolean;
  onSubmit: (input: InvestigationInput) => Promise<void>;
}

export default function ObservationForm({
  busy,
  onSubmit,
}: ObservationFormProps) {
  const [crop, setCrop] = useState<Crop>("rice");
  const [photo, setPhoto] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (busy) return;

    if (!photo) {
      setFileError("Please attach a symptom photograph.");
      return;
    }

    const data = new FormData(event.currentTarget);

    await onSubmit({
      crop,
      photo,
      region: String(data.get("region") ?? "").trim(),
      observedDate: String(data.get("observed_date") ?? ""),
      growthStage: String(data.get("growth_stage") ?? ""),
      affectedPart: String(data.get("affected_part") ?? ""),
      symptoms: String(data.get("symptoms") ?? "").trim(),
    });
  }

  return (
    <section
      id="observation"
      className="panel observation-panel"
      aria-labelledby="observation-title"
    >
      <header className="panel-heading">
        <div>
          <p className="eyebrow">01 / START HERE</p>
          <h2 id="observation-title">Field observations</h2>
        </div>
      </header>

      <form onSubmit={handleSubmit}>
        <fieldset
          disabled={busy}
          style={{ border: 0, margin: 0, padding: 0 }}
        >
          <legend className="sr-only">Investigation input</legend>

          <fieldset className="crop-fieldset">
            <legend>Select crop</legend>

            <div className="crop-grid">
              {([
                ["rice", "Rice", "Oryza sativa"],
                ["maize", "Maize", "Zea mays"],
              ] as const).map(([value, label, scientificName]) => (
                <label className="crop-card" key={value}>
                  <input
                    type="radio"
                    name="crop"
                    value={value}
                    checked={crop === value}
                    onChange={() => setCrop(value)}
                  />
                  <span className="crop-symbol" aria-hidden="true">
                    {value === "rice" ? "↟" : "✳"}
                  </span>
                  <span className="crop-name">{label}</span>
                  <span className="scientific-name">
                    {scientificName}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="field">
            <label htmlFor="photo">Symptom photograph</label>

            <div className="upload-area">
              <strong>Add a clear photograph</strong>
              <p>Include the affected area and surrounding tissue.</p>

              <input
                id="photo"
                type="file"
            accept="image/jpeg,image/png,image/webp"
                required
                aria-describedby="photo-help photo-error"
                aria-invalid={Boolean(fileError)}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setFileError("");
                  setPhoto(null);

                  if (!file) return;

                  const allowed = [
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                  ];

                  if (!allowed.includes(file.type)) {
                    setFileError("Choose a JPG, PNG or WEBP image.");
                    event.target.value = "";
                    return;
                  }

                  if (file.size > 10 * 1024 * 1024) {
                    setFileError("Choose an image no larger than 10 MB.");
                    event.target.value = "";
                    return;
                  }

                  setPhoto(file);
                }}
              />

              <small id="photo-help">JPG, PNG or WEBP · Up to 10 MB</small>
            </div>

            <p id="photo-error" className="error-text" role="alert">
              {fileError}
            </p>
          </div>

          <div className="field-grid">
            <div className="field">
              <label htmlFor="region">Growing location</label>
              <input
                id="region"
                name="region"
                type="text"
                placeholder="City / county, province"
                maxLength={200}
                pattern={".*\\S.*"}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="observed-date">Observation date</label>
              <input
                id="observed-date"
                name="observed_date"
                type="date"
                required
              />
            </div>
          </div>

          <div className="field-grid">
            <div className="field">
              <label htmlFor="growth-stage">Growth stage</label>
              <select id="growth-stage" name="growth_stage">
                <option value="">Unknown</option>
                <option value="seedling">Seedling</option>
                <option value="vegetative">Vegetative</option>
                <option value="flowering">Flowering</option>
                <option value="grain_filling">Grain filling</option>
                <option value="maturity">Maturity</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="affected-part">Affected part</label>
              <select id="affected-part" name="affected_part">
                <option value="">Unknown</option>
                <option value="leaf">Leaf</option>
                <option value="stem">Stem / sheath</option>
                <option value="root">Root</option>
                <option value="reproductive">Panicle / ear</option>
                <option value="whole_plant">Whole plant</option>
              </select>
            </div>
          </div>

          <div className="field">
            <label htmlFor="symptoms">What have you observed?</label>
            <textarea
              id="symptoms"
              name="symptoms"
              rows={4}
              maxLength={5000}
              placeholder="Describe symptoms, onset and nearby affected plants."
              required
            />
          </div>

          <button
            className="primary-button"
            type="submit"
            disabled={busy}
          >
            {busy ? "Submitting…" : "Start investigation"}
        <span aria-hidden="true">→</span>  
	</button>
        </fieldset>
      </form>
    </section>
  );
}
