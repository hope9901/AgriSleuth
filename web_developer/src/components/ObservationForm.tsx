import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Crop, InvestigationInput } from "../types/investigation";

interface ObservationFormProps {
  busy: boolean;
  onSubmit: (input: InvestigationInput) => Promise<void>;
}

interface SamplePreset {
  id: "rice_blast" | "maize_blight";
  label: string;
  badge: string;
  crop: Crop;
  region: string;
  observedDate: string;
  growthStage: string;
  affectedPart: string;
  symptoms: string;
  imagePath: string;
  fileName: string;
  sourceLabel: string;
  sourceUrl: string;
}

const SAMPLE_PRESETS: SamplePreset[] = [
  {
    id: "rice_blast",
    label: "Rice leaf blast sample",
    badge: "Oryza sativa",
    crop: "rice",
    region: "Gimje-si, Jeonbuk",
    observedDate: "2026-07-18",
    growthStage: "vegetative",
    affectedPart: "leaf",
    symptoms:
      "Eye-shaped spindle lesion with a gray-white sporulating center, dark brown necrotic margin, and yellow chlorotic halo along the leaf blade after several days of high humidity.",
    imagePath: "/samples/rice-blast-usda-d542-1.jpg",
    fileName: "rice-blast-usda-d542-1.jpg",
    sourceLabel: "USDA ARS Public Domain (Photo by Yulin Jia, D542-1)",
    sourceUrl:
      "https://commons.wikimedia.org/wiki/File:Rice_blast_Magnaporthe_grisea.jpg",
  },
  {
    id: "maize_blight",
    label: "Maize leaf blight sample",
    badge: "Zea mays",
    crop: "maize",
    region: "Hongcheon-gun, Gangwon",
    observedDate: "2026-08-09",
    growthStage: "flowering",
    affectedPart: "leaf",
    symptoms:
      "Extensive coalescing tan-to-brown necrotic blight lesions and chlorotic flecking spreading along the leaf blade parallel to the midrib after warm summer rains.",
    imagePath: "/samples/maize-blight-usda-k7753-4.jpg",
    fileName: "maize-blight-usda-k7753-4.jpg",
    sourceLabel: "USDA ARS Public Domain (Photo by Keith Weller, K7753-4)",
    sourceUrl: "https://www.ars.usda.gov/is/graphics/photos/sep97/k7753-4.htm",
  },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}

async function loadPublicDomainSampleFile(
  preset: SamplePreset,
): Promise<File> {
  const response = await fetch(preset.imagePath);
  if (!response.ok) {
    throw new Error(`Failed to load sample image (${response.status})`);
  }
  const blob = await response.blob();
  return new File([blob], preset.fileName, {
    type: blob.type || "image/jpeg",
  });
}

export default function ObservationForm({
  busy,
  onSubmit,
}: ObservationFormProps) {
  const [crop, setCrop] = useState<Crop>("rice");
  const [region, setRegion] = useState("");
  const [observedDate, setObservedDate] = useState("");
  const [growthStage, setGrowthStage] = useState("");
  const [affectedPart, setAffectedPart] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [activePresetId, setActivePresetId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState("");
  const [dateError, setDateError] = useState("");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const activePreset = SAMPLE_PRESETS.find((p) => p.id === activePresetId);

  const previewRef = useRef<string | null>(null);
  function selectPhoto(file: File | null) {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    const url = file ? URL.createObjectURL(file) : null;
    previewRef.current = url;
    setPhoto(file);
    setPreviewUrl(url);
  }
  useEffect(() => () => {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
  }, []);

  async function handleSelectPreset(preset: SamplePreset) {
    if (busy) return;

    try {
      setFileError("");
      const sampleFile = await loadPublicDomainSampleFile(preset);
      setCrop(preset.crop);
      setRegion(preset.region);
      setObservedDate(preset.observedDate);
      setGrowthStage(preset.growthStage);
      setAffectedPart(preset.affectedPart);
      setSymptoms(preset.symptoms);
      selectPhoto(sampleFile);
      setActivePresetId(preset.id);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch {
      setFileError("Could not load the sample photograph.");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (busy) return;

    if (!photo) {
      setFileError("Please attach a symptom photograph.");
      return;
    }

    if (observedDate) {
      const parsed = new Date(`${observedDate}T00:00:00Z`);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(observedDate) || Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== observedDate) {
        setDateError("Enter a valid date in YYYY-MM-DD format, or leave it blank.");
        return;
      }
    }
    setDateError("");
    await onSubmit({
      crop,
      photo,
      region: region.trim(),
      observedDate,
      growthStage,
      affectedPart,
      symptoms: symptoms.trim(),
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
        <span className="subtle-label">Photograph required · Other details optional</span>
      </header>

      <p className="helper-text" id="observation-help">A symptom photograph is required. All other details are optional. Adding location, observation date, growth stage, affected part, and symptom notes can help the agent make a more specific assessment and reduce uncertainty.</p>
      <div className="sample-preset-bar" aria-label="Quick demo presets">
        <div className="sample-preset-header">
          <span className="sample-preset-title">
            Quick demo presets for judges
          </span>
          <span className="sample-preset-note">
            USDA ARS attributed reference photos
          </span>
        </div>
        <div className="sample-preset-buttons">
          {SAMPLE_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              disabled={busy}
              className={`preset-chip ${
                activePresetId === preset.id ? "preset-chip--active" : ""
              }`}
              onClick={() => void handleSelectPreset(preset)}
            >
              <span aria-hidden="true">
                {preset.crop === "rice" ? "↟" : "✳"}
              </span>
              <span>{preset.label}</span>
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} noValidate aria-describedby="observation-help">
        <fieldset
          disabled={busy}
          style={{ border: 0, margin: 0, padding: 0 }}
        >
          <legend className="sr-only">Investigation input</legend>

          <fieldset className="crop-fieldset">
            <legend>Select target crop</legend>

            <div className="crop-grid">
              {(
                [
                  ["rice", "Rice", "Oryza sativa"],
                  ["maize", "Maize", "Zea mays"],
                ] as const
              ).map(([value, label, scientificName]) => (
                <label className="crop-card" key={value}>
                  <input
                    type="radio"
                    name="crop"
                    value={value}
                    checked={crop === value}
                    onChange={() => {
                      setCrop(value);
                      setActivePresetId(null);
                    }}
                  />
                  <span className="crop-symbol" aria-hidden="true">
                    {value === "rice" ? "↟" : "✳"}
                  </span>
                  <span className="crop-name">{label}</span>
                  <span className="scientific-name">{scientificName}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="field">
            <label htmlFor="photo">
              Symptom photograph
              <span className="required-label">Required</span>
            </label>

            <div className={`upload-area ${previewUrl ? "has-preview" : ""}`}>
              <div className="upload-symbol" aria-hidden="true">
                📷
              </div>
              <strong>Add a clear field photograph</strong>
              <p>
                Capture both the affected lesion or discoloration and adjacent
                healthy tissue for accurate visual comparison.
              </p>

              <input
                ref={fileInputRef}
                id="photo"
                type="file"
                hidden
                style={{ display: "none" }}
                accept="image/jpeg,image/png,image/webp"
                required={!photo}
                aria-describedby="photo-help photo-error"
                aria-invalid={Boolean(fileError)}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setFileError("");
                  setActivePresetId(null);
                  selectPhoto(null);

                  if (!file) return;

                  const allowed = ["image/jpeg", "image/png", "image/webp"];

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

                  selectPhoto(file);
                }}
              />

              <button type="button" className="secondary-button" onClick={() => fileInputRef.current?.click()} aria-describedby="photo-help photo-error">{photo ? "Change photograph" : "Choose photograph"}</button>
              <p className="helper-text" aria-live="polite">{photo ? photo.name : "No photograph selected"}</p>
              <small id="photo-help">JPG, PNG or WEBP · Up to 10 MB</small>

              {previewUrl && photo && (
                <figure className="photo-preview-card">
                  <div className="photo-preview-frame">
                    <img
                      src={previewUrl}
                      alt={`Selected ${crop} symptom preview`}
                      className="photo-preview-img"
                    />
                  </div>
                  <figcaption className="photo-preview-meta">
                    <span className="photo-preview-name" title={photo.name}>
                      {photo.name}
                    </span>
                    <span className="photo-preview-size">
                      {activePreset ? (
                        <a
                          href={activePreset.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ textDecoration: "underline" }}
                        >
                          {activePreset.sourceLabel} ↗
                        </a>
                      ) : null}
                      {activePreset ? " · " : ""}
                      {formatFileSize(photo.size)}
                    </span>
                  </figcaption>
                </figure>
              )}
            </div>

            <p id="photo-error" className="error-text" role="alert">
              {fileError}
            </p>
          </div>

          <div className="field-grid">
            <div className="field">
              <label htmlFor="region">
                Growing location
                <span className="subtle-label">Optional</span>
              </label>
              <input
                id="region"
                name="region"
                type="text"
                placeholder="e.g., Gimje-si, Jeonbuk"
                maxLength={200}
                value={region}
                onChange={(event) => setRegion(event.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="observed-date">
                Observation date
                <span className="subtle-label">Optional</span>
              </label>
              <input
                id="observed-date"
                name="observed_date"
                type="text"
                inputMode="numeric"
                placeholder="YYYY-MM-DD"
                maxLength={10}
                aria-describedby="observed-date-help observed-date-error"
                aria-invalid={Boolean(dateError)}
                value={observedDate}
                onChange={(event) => { setObservedDate(event.target.value); setDateError(""); }}
              />
            </div>
          </div>

          <p id="observed-date-help" className="helper-text">Optional date in YYYY-MM-DD format. Location and observation date are needed only for historical weather lookup.</p>
          <p id="observed-date-error" className="error-text" role="alert">{dateError}</p>
          <div className="field-grid">
            <div className="field">
              <label htmlFor="growth-stage">Growth stage <span className="subtle-label">Optional</span></label>
              <select
                id="growth-stage"
                name="growth_stage"
                value={growthStage}
                onChange={(event) => setGrowthStage(event.target.value)}
              >
                <option value="">Unknown</option>
                <option value="seedling">Seedling</option>
                <option value="vegetative">Vegetative</option>
                <option value="flowering">Flowering</option>
                <option value="grain_filling">Grain filling</option>
                <option value="maturity">Maturity</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="affected-part">Affected part <span className="subtle-label">Optional</span></label>
              <select
                id="affected-part"
                name="affected_part"
                value={affectedPart}
                onChange={(event) => setAffectedPart(event.target.value)}
              >
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
            <label htmlFor="symptoms">
              What have you observed?
              <span className="subtle-label">Optional</span>
            </label>
            <textarea
              id="symptoms"
              name="symptoms"
              rows={4}
              maxLength={5000}
              placeholder="Describe lesion shape, color, progression speed, weather conditions, and whether neighboring plants show similar symptoms."
              value={symptoms}
              onChange={(event) => setSymptoms(event.target.value)}
            />
          </div>

          <button className="primary-button" type="submit" disabled={busy}>
            <span>{busy ? "Submitting…" : "Save observations"}</span>
            <span aria-hidden="true">→</span>
          </button>

          <p className="helper-text">
            Save observations first, then start the agent to investigate cited
            disease evidence and unresolved observations.
          </p>
        </fieldset>
      </form>
    </section>
  );
}
