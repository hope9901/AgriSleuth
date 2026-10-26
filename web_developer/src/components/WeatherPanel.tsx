import { API_BASE_URL } from "../api/investigations";
import { useState } from "react";
import { collectWeather, searchWeatherLocations } from "../api/weather";
import type { WeatherLocation, WeatherReport } from "../api/weather";

export default function WeatherPanel({ investigationId, initialRegion }: { investigationId: string; initialRegion: string }) {
  const [query, setQuery] = useState(initialRegion);
  const [locations, setLocations] = useState<WeatherLocation[]>([]);
  const [selected, setSelected] = useState("");
  const [report, setReport] = useState<WeatherReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function search() {
    setBusy(true); setError(""); setLocations([]); setSelected(""); setReport(null);
    try {
      const data = await searchWeatherLocations(query.trim()); setLocations(data.locations);
      if (!data.locations.length) setError("No location found. Try the city name, in Korean or English.");
    } catch (e) { setError(e instanceof Error ? e.message : "Location search failed."); }
    finally { setBusy(false); }
  }
  async function collect() {
    setBusy(true); setError(""); setReport(null);
    try { setReport(await collectWeather(investigationId, Number(selected))); }
    catch (e) { setError(e instanceof Error ? e.message : "Weather retrieval failed."); }
    finally { setBusy(false); }
  }
  async function confirmForAgent() {
    setBusy(true); setError("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/investigations/${encodeURIComponent(investigationId)}/location`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({location_id:Number(selected)}),signal:AbortSignal.timeout(15_000)});
      const data = await response.json();
      if (!response.ok) throw Error(typeof data.detail === "string" ? data.detail : "Location confirmation failed.");
      setError(`Location confirmed for agent: ${data.label}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Location confirmation failed."); }
    finally { setBusy(false); }
  }
  return <section className="panel" aria-labelledby="weather-title">
    <header className="panel-heading"><div><p className="eyebrow">WEATHER EVIDENCE</p><h2 id="weather-title">KMA world observations</h2></div></header>
    <p>Confirm the growing location to retrieve station observations for the saved observation date.</p>
    <label htmlFor="weather-region">City / region</label>
    <input id="weather-region" value={query} onChange={e => setQuery(e.target.value)} placeholder="e.g. Gimje or Seoul" disabled={busy} />
    <button type="button" onClick={() => void search()} disabled={busy || query.trim().length < 2}>Find location</button>
    {locations.length > 0 && <><label htmlFor="weather-location">Confirm a location</label><select id="weather-location" value={selected} onChange={e => { setSelected(e.target.value); setReport(null); }} disabled={busy}>
      <option value="">Select location</option>{locations.map(item => <option value={item.id} key={item.id}>{item.label} ({item.latitude}, {item.longitude})</option>)}
    </select><button type="button" onClick={() => void collect()} disabled={busy || !selected}>Retrieve weather evidence</button><button type="button" onClick={() => void confirmForAgent()} disabled={busy || !selected}>Use location for agent</button></>}
    {busy && <p role="status">Retrieving evidence…</p>}{error && <p role="alert">{error}</p>}
    {report && <><h3>{report.observed_date} · {report.status}</h3>{report.location && <p>{report.location.label} · {report.location.timezone}</p>}
      {report.station && <p>Station {report.station.id} · {report.station.distance_km} km from selected location</p>}
      {report.summary.sample_count !== undefined && <p>{report.summary.sample_count}/{report.summary.requested_sample_count} requested timestamps received. Sampled temperature: {report.summary.sampled_min_temperature_c ?? "unknown"} to {report.summary.sampled_max_temperature_c ?? "unknown"} °C. Sampled mean humidity: {report.summary.sampled_mean_humidity_pct ?? "unknown"}%.</p>}
      <ul>{report.limitations.map((text,i) => <li key={i}>{text}</li>)}</ul>
      <h3>Disease environment references — researcher review</h3><p>These are source conditions, not disease probabilities or confirmed matches.</p>
      {report.comparisons.map(item => <details key={item.disease_id}><summary>{item.name}</summary><p>{item.reason}</p>{item.temperature_check && <p>Temperature reference {item.temperature_check.range_c.join("–")} °C: {item.temperature_check.samples_in_range}/{item.temperature_check.valid_samples} valid samples in range. {item.temperature_check.interpretation}</p>}{item.conditions.map((c,i) => <article key={i}><p>{c.description}</p><small>{c.source_name} · {c.location_in_source}</small><p>{(Array.isArray(c.url) ? c.url : [c.url]).filter(url => /^https?:\/\//i.test(url)).map(url => <a key={url} href={url} target="_blank" rel="noopener noreferrer">Source ↗ </a>)}</p></article>)}</details>)}
    </>}
    <small>Weather: Korea Meteorological Administration. Location data: GeoNames via Open-Meteo.</small>
  </section>;
}
