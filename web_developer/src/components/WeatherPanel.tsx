import { API_BASE_URL } from "../api/investigations";
import { useEffect, useState } from "react";
import { collectWeather, searchWeatherLocations, getCountryStations, getSavedWeather } from "../api/weather";
import type { WeatherLocation, WeatherReport } from "../api/weather";

export default function WeatherPanel({ investigationId, initialRegion, status }: { investigationId: string; initialRegion: string; status?: string }) {
  const [countryCode, setCountryCode] = useState("");
  const [stationList, setStationList] = useState<Awaited<ReturnType<typeof getCountryStations>> | null>(null);
  async function lookupStations() {
    setBusy(true); setError(""); setStationList(null);
    try { setStationList(await getCountryStations(countryCode)); }
    catch (e) { setError(e instanceof Error ? e.message : "Station lookup failed."); }
    finally { setBusy(false); }
  }
  const [query, setQuery] = useState(initialRegion);
  const [locations, setLocations] = useState<WeatherLocation[]>([]);
  const [selected, setSelected] = useState("");
  const [report, setReport] = useState<WeatherReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void getSavedWeather(investigationId).then(saved => { if (active) setReport(saved); }).catch(error => { if (active && !(error instanceof Error && error.message.includes('No saved weather'))) setError('Saved weather could not be loaded. Retry the location lookup or reload this case.'); });
    return () => { active = false; };
  }, [investigationId, status]);
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
      {report.environment_assessments && <><h3>Collected environment references and window coverage</h3><p>These English references preserve the collected source conditions. Sample overlap does not establish infection; unmet inputs and windows remain unknown.</p>{report.environment_assessments.map(item => <details key={item.disease_id}><summary>{item.name} · {item.assessment}</summary><p lang="en">{item.name_ko}: {item.thresholds_text}</p><p>Required inputs: {item.required_inputs.join(", ")}</p><ul>{item.windows.map(window => <li key={window.window_id}>{window.window_id}: {window.coverage} ({window.covered_days ?? 0}/{window.required_days ?? "anchor required"} days) · {window.evidence_type}</li>)}</ul>{item.checks.map(check => <p key={check.metric}>{check.metric}: {check.samples_matching}/{check.valid_samples}. {check.interpretation}</p>)}{item.sources.filter(source => /^https?:\/\//i.test(source.url)).map(source => <p key={source.url}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.label} ↗</a></p>)}</details>)}</>}
      <h3>Disease environment references — researcher review</h3><p>These are source conditions, not disease probabilities or confirmed matches.</p>
      {report.comparisons.map(item => <details key={item.disease_id}><summary>{item.name}</summary><p>{item.reason}</p>{item.temperature_check && <p>Temperature reference {item.temperature_check.range_c.join("–")} °C: {item.temperature_check.samples_in_range}/{item.temperature_check.valid_samples} valid samples in range. {item.temperature_check.interpretation}</p>}{item.conditions.map((c,i) => <article key={i}><p>{c.description}</p><small>{c.source_name} · {c.location_in_source}</small><p>{(Array.isArray(c.url) ? c.url : [c.url]).filter(url => /^https?:\/\//i.test(url)).map(url => <a key={url} href={url} target="_blank" rel="noopener noreferrer">Source ↗ </a>)}</p></article>)}</details>)}
    </>}
    <details><summary>Country station directory — KMA</summary><p>Enter an official KMA country code. Example 1001 is Russia. This directory supplies station IDs and names, not growing-location coordinates.</p><label htmlFor="country-code">KMA country code</label><input id="country-code" value={countryCode} onChange={e => setCountryCode(e.target.value)} /><button type="button" disabled={busy || !/^\d{1,8}$/.test(countryCode)} onClick={() => void lookupStations()}>Look up stations</button>{stationList && <><p>{stationList.total_count} stations received.</p><ul>{stationList.stations.map(station => <li key={station.id}>{station.id} · {station.country_name} · {station.name}</li>)}</ul></>}</details>
    <small>Weather: Korea Meteorological Administration. Location data: GeoNames via Open-Meteo.</small>
  </section>;
}
