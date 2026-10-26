import { API_BASE_URL } from "./investigations";
export interface WeatherLocation { id: number; label: string; latitude: number; longitude: number; timezone: string }
export interface WeatherReport {
  status: string;
  observed_date: string;
  location?: WeatherLocation;
  station?: { id: string; distance_km: number };
  summary: { sample_count?: number; requested_sample_count?: number; sampled_min_temperature_c?: number | null; sampled_max_temperature_c?: number | null; sampled_mean_humidity_pct?: number | null };
  environment_assessments?: { disease_id: string; name: string; name_ko: string; assessment: string; thresholds_text: string; required_inputs: string[]; sources: {label: string; url: string}[]; windows: {window_id: string; coverage: string; required_days?: number; covered_days?: number; evidence_type: string}[]; checks: {metric: string; samples_matching: number; valid_samples: number; interpretation: string}[] }[];
  comparisons: { disease_id: string; name: string; reason: string; temperature_check?: {range_c: number[]; samples_in_range: number; valid_samples: number; interpretation: string} | null; conditions: {description: string; source_name: string; url: string[] | string; location_in_source: string}[] }[];
  limitations: string[];
}
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(API_BASE_URL + path, { ...options, signal: AbortSignal.timeout(55_000) });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Weather request failed: HTTP ${response.status}`);
  }
  return response.json();
}
export function searchWeatherLocations(q: string) {
  return request<{locations: WeatherLocation[]}>(`/api/weather/locations?q=${encodeURIComponent(q)}`);
}
export function collectWeather(id: string, locationId: number) {
  return request<WeatherReport>(`/api/investigations/${encodeURIComponent(id)}/weather`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ location_id: locationId }),
  });
}

export function getCountryStations(countryCode: string) {
 return request<{total_count: number; stations: {id: string; country_name: string; name: string}[]; limitations: string[]}>(`/api/weather/stations?country_code=${encodeURIComponent(countryCode)}&category=temp`);
}

export function getSavedWeather(id: string) {
 return request<WeatherReport>(`/api/investigations/${encodeURIComponent(id)}/weather`);
}
