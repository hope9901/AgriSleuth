import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx

from .models import WeatherContext, WeatherDay, WeatherQuery

KMA_URL = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"


class WeatherServiceError(Exception):
    """Sanitized error: never includes the request URL or service key."""


async def fetch_asos_daily(
    client: httpx.AsyncClient, service_key: str, query: WeatherQuery
) -> list[dict]:
    """Transport boundary. At most one retry for transient failures."""
    if query.end >= datetime.now(timezone(timedelta(hours=9))).date():
        raise ValueError("Use completed observation days before today in Korea.")
    params = {
        "serviceKey": service_key, "dataType": "JSON",
        "dataCd": "ASOS", "dateCd": "DAY",
        "pageNo": 1, "numOfRows": 100,
        "startDt": query.start.strftime("%Y%m%d"),
        "endDt": query.end.strftime("%Y%m%d"),
        "stnIds": query.station_id,
    }
    for attempt in range(2):
        try:
            response = await client.get(KMA_URL, params=params, timeout=15)
            if response.status_code == 429 or response.status_code >= 500:
                raise WeatherServiceError("KMA transient HTTP failure.")
            response.raise_for_status()
        except (httpx.TimeoutException, httpx.TransportError, WeatherServiceError):
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            raise WeatherServiceError("KMA request failed after retry.") from None
        except httpx.HTTPStatusError:
            raise WeatherServiceError("KMA rejected the request.") from None

        try:
            envelope = response.json()["response"]
            code = envelope["header"]["resultCode"]
            if code == "03":  # No data; not zero precipitation.
                return []
            if code != "00":
                raise WeatherServiceError("KMA returned an API error.")
            body = envelope["body"]
            if int(body["totalCount"]) > 100:
                raise WeatherServiceError("Unexpected result size; pagination required.")
            items = body.get("items") or {}
            rows = items.get("item", [])
            return [rows] if isinstance(rows, dict) else rows
        except (KeyError, TypeError, ValueError, AttributeError):
            # Authentication failures can arrive as XML even when JSON was requested.
            raise WeatherServiceError("KMA response could not be decoded.") from None
    raise WeatherServiceError("KMA request did not complete.")


def optional_number(value) -> float | None:
    """Blank means unknown, never automatically zero."""
    return None if value is None or str(value).strip() == "" else float(value)


def normalize_weather(rows: list[dict], query: WeatherQuery) -> WeatherContext:
    """Pure normalization: no network, model, or database calls."""
    days = []
    for row in rows:
        observed = date.fromisoformat(row["tm"])
        if str(row["stnId"]) != query.station_id or not query.start <= observed <= query.end:
            raise ValueError("Weather response does not match the requested station/period.")
        days.append(WeatherDay(
            observed_date=observed,
            mean_temperature_c=optional_number(row.get("avgTa")),
            mean_humidity_pct=optional_number(row.get("avgRhm")),
            precipitation_mm=optional_number(row.get("sumRn")),
        ))
    dates = {day.observed_date for day in days}
    if len(dates) != len(days):
        raise ValueError("Duplicate observation dates.")
    expected = (query.end - query.start).days + 1
    complete = len(days) == expected and all(
        d.mean_temperature_c is not None and d.mean_humidity_pct is not None
        and d.precipitation_mm is not None for d in days
    )
    return WeatherContext(
        status="available" if complete else "partial" if days else "unavailable",
        query=query, retrieved_at=datetime.now(timezone.utc),
        days=sorted(days, key=lambda d: d.observed_date),
        limitations=[] if complete else ["Some observation dates or values are missing."],
    )


async def get_weather_context(client, service_key, query) -> WeatherContext:
