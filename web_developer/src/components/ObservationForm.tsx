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
  fileName: string;
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
      "Diamond-shaped spindle lesions with gray-white centers and reddish-brown necrotic borders on middle and upper leaves after 4 days of high humidity and morning fog. Neighboring paddy rows along the windward bund show similar coalescing lesions.",
    fileName: "rice-leaf-blast-cc0-sample.png",
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
      "Elongated cigar-shaped grayish-green to tan necrotic lesions (3 to 12 cm) starting on lower leaves and progressing upward toward the ear leaf after frequent summer showers. Lesions run parallel to leaf veins without distinct yellow halos.",
    fileName: "maize-leaf-blight-cc0-sample.png",
  },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(2)} MB`;
}

/**
 * Generates an original, copyright-free (CC0) synthetic botanical symptom PNG
 * directly in the browser so hackathon judges can test the full pipeline with
 * zero third-party image licensing or attribution issues.
 */
async function createSyntheticSymptomFile(
  preset: SamplePreset,
): Promise<File> {
  const canvas = document.createElement("canvas");
  canvas.width = 960;
  canvas.height = 600;
  const ctx = canvas.getContext("2d");

  if (!ctx) {
    throw new Error("Canvas context unavailable");
  }

  // Soft field background gradient
  const bg = ctx.createLinearGradient(0, 0, 960, 600);
  bg.addColorStop(0, "#e5efe0");
  bg.addColorStop(1, "#cfdrc8".replace("r", "d"));
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, 960, 600);

  // Subtle out-of-focus background foliage
  ctx.save();
  ctx.globalAlpha = 0.22;
  ctx.fillStyle = "#4d7c42";
  ctx.beginPath();
  ctx.ellipse(220, 120, 340, 70, -0.35, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(760, 500, 380, 85, -0.28, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  if (preset.crop === "rice") {
    // Draw Rice Leaf Blade (slender arched blade)
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(40, 490);
    ctx.quadraticCurveTo(460, 170, 920, 110);
    ctx.quadraticCurveTo(510, 340, 95, 560);
    ctx.closePath();

    const leafGrad = ctx.createLinearGradient(40, 520, 920, 110);
    leafGrad.addColorStop(0, "#3b7a38");
    leafGrad.addColorStop(0.55, "#4f9446");
    leafGrad.addColorStop(1, "#3f7d3a");
    ctx.fillStyle = leafGrad;
    ctx.fill();

    // Midrib and parallel veins
    ctx.strokeStyle = "rgba(218, 240, 195, 0.65)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(68, 525);
    ctx.quadraticCurveTo(485, 255, 920, 110);
    ctx.stroke();

    // Characteristic diamond/spindle-shaped rice blast lesions
    const lesions = [
      { x: 340, y: 350, w: 46, h: 16, angle: -0.46 },
      { x: 470, y: 278, w: 62, h: 20, angle: -0.43 },
      { x: 590, y: 222, w: 50, h: 17, angle: -0.4 },
      { x: 695, y: 178, w: 38, h: 13, angle: -0.37 },
    ];

    for (const l of lesions) {
      ctx.save();
      ctx.translate(l.x, l.y);
      ctx.rotate(l.angle);

      // Chlorotic yellow halo
      ctx.fillStyle = "rgba(232, 204, 94, 0.72)";
      ctx.beginPath();
      ctx.moveTo(-l.w * 1.25, 0);
      ctx.quadraticCurveTo(0, -l.h * 1.35, l.w * 1.25, 0);
      ctx.quadraticCurveTo(0, l.h * 1.35, -l.w * 1.25, 0);
      ctx.fill();

      // Reddish-brown necrotic border
      ctx.fillStyle = "#6e3423";
      ctx.beginPath();
      ctx.moveTo(-l.w, 0);
      ctx.quadraticCurveTo(0, -l.h, l.w, 0);
      ctx.quadraticCurveTo(0, l.h, -l.w, 0);
      ctx.fill();

      // Gray-white sporulating center
      ctx.fillStyle = "#d9ddd4";
      ctx.beginPath();
      ctx.moveTo(-l.w * 0.58, 0);
      ctx.quadraticCurveTo(0, -l.h * 0.55, l.w * 0.58, 0);
      ctx.quadraticCurveTo(0, l.h * 0.55, -l.w * 0.58, 0);
      ctx.fill();

      ctx.restore();
    }
    ctx.restore();
  } else {
    // Draw Maize Leaf Blade (broad arched blade)
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(20, 470);
    ctx.quadraticCurveTo(450, 120, 940, 130);
    ctx.lineTo(940, 310);
    ctx.quadraticCurveTo(490, 360, 60, 580);
    ctx.closePath();

    const maizeGrad = ctx.createLinearGradient(20, 520, 940, 180);
    maizeGrad.addColorStop(0, "#2f6b34");
    maizeGrad.addColorStop(0.5, "#3f8242");
    maizeGrad.addColorStop(1, "#2d6631");
    ctx.fillStyle = maizeGrad;
    ctx.fill();

    // Prominent central midrib
    ctx.strokeStyle = "rgba(227, 242, 210, 0.78)";
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(40, 525);
    ctx.quadraticCurveTo(470, 240, 940, 215);
    ctx.stroke();

    // Elongated cigar-shaped Northern Corn Leaf Blight lesions
    const lesions = [
      { x: 330, y: 345, w: 115, h: 22, angle: -0.36 },
      { x: 545, y: 285, w: 135, h: 25, angle: -0.25 },
      { x: 690, y: 205, w: 98, h: 19, angle: -0.15 },
    ];

    for (const l of lesions) {
      ctx.save();
      ctx.translate(l.x, l.y);
      ctx.rotate(l.angle);

      // Tan-brown margin
      ctx.fillStyle = "#7a5b34";
      ctx.beginPath();
      ctx.ellipse(0, 0, l.w, l.h, 0, 0, Math.PI * 2);
      ctx.fill();

      // Grayish-tan necrotic interior
      ctx.fillStyle = "#b8ab8e";
      ctx.beginPath();
      ctx.ellipse(0, 0, l.w * 0.82, l.h * 0.72, 0, 0, Math.PI * 2);
      ctx.fill();

      // Subtle dark fungal stippling
      ctx.fillStyle = "rgba(68, 56, 40, 0.45)";
      ctx.beginPath();
      ctx.ellipse(0, 0, l.w * 0.45, l.h * 0.3, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }
    ctx.restore();
  }

  // Metadata overlay bar (CC0 attribution-free notice)
  ctx.fillStyle = "rgba(24, 42, 31, 0.78)";
  ctx.fillRect(24, 528, 912, 48);
  ctx.fillStyle = "#edf5e8";
  ctx.font = "600 15px system-ui, -apple-system, sans-serif";
  ctx.fillText(
    `AgriSleuth Synthetic Reference Specimen · ${preset.label} (${preset.badge})`,
    42,
    557,
  );
  ctx.fillStyle = "#b8d4a7";
  ctx.font = "500 13px system-ui, -apple-system, sans-serif";
  ctx.textAlign = "right";
  ctx.fillText("CC0 Public Domain · Generated in-browser", 918, 557);

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((b) => {
      if (b) resolve(b);
      else reject(new Error("Failed to encode sample image"));
    }, "image/png");
  });

  return new File([blob], preset.fileName, { type: "image/png" });
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
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!photo) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(photo);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [photo]);

  async function handleSelectPreset(preset: SamplePreset) {
    if (busy) return;

    try {
      setFileError("");
      const sampleFile = await createSyntheticSymptomFile(preset);
      setCrop(preset.crop);
      setRegion(preset.region);
      setObservedDate(preset.observedDate);
      setGrowthStage(preset.growthStage);
      setAffectedPart(preset.affectedPart);
      setSymptoms(preset.symptoms);
      setPhoto(sampleFile);
      setActivePresetId(preset.id);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch {
      setFileError("Could not generate sample photograph.");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (busy) return;

    if (!photo) {
      setFileError("Please attach a symptom photograph.");
      return;
    }

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
        <span className="subtle-label">Required inputs</span>
      </header>

      <div className="sample-preset-bar" aria-label="Quick demo presets">
        <div className="sample-preset-header">
          <span className="sample-preset-title">
            Quick demo presets for judges
          </span>
          <span className="sample-preset-note">
            CC0 synthetic imagery · No copyright restrictions
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

      <form onSubmit={handleSubmit}>
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
                accept="image/jpeg,image/png,image/webp"
                required={!photo}
                aria-describedby="photo-help photo-error"
                aria-invalid={Boolean(fileError)}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setFileError("");
                  setActivePresetId(null);
                  setPhoto(null);

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

                  setPhoto(file);
                }}
              />

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
                      {activePresetId ? "CC0 Synthetic · " : ""}
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
                <span className="required-label">Required</span>
              </label>
              <input
                id="region"
                name="region"
                type="text"
                placeholder="e.g., Gimje-si, Jeonbuk"
                maxLength={200}
                pattern={".*\\S.*"}
                value={region}
                onChange={(event) => setRegion(event.target.value)}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="observed-date">
                Observation date
                <span className="required-label">Required</span>
              </label>
              <input
                id="observed-date"
                name="observed_date"
                type="date"
                value={observedDate}
                onChange={(event) => setObservedDate(event.target.value)}
                required
              />
            </div>
          </div>

          <div className="field-grid">
            <div className="field">
              <label htmlFor="growth-stage">Growth stage</label>
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
              <label htmlFor="affected-part">Affected part</label>
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
              <span className="required-label">Required</span>
            </label>
            <textarea
              id="symptoms"
              name="symptoms"
              rows={4}
              maxLength={5000}
              placeholder="Describe lesion shape, color, progression speed, weather conditions, and whether neighboring plants show similar symptoms."
              value={symptoms}
              onChange={(event) => setSymptoms(event.target.value)}
              required
            />
          </div>

          <button className="primary-button" type="submit" disabled={busy}>
            <span>{busy ? "Submitting…" : "Start investigation"}</span>
            <span aria-hidden="true">→</span>
          </button>

          <p className="helper-text">
            AgriSleuth cross-checks your visual and field observations against
            peer-reviewed extension guides before proposing hypotheses.
          </p>
        </fieldset>
      </form>
    </section>
  );
}
