"""World GTS observations from KMA; geocoding is separate from weather evidence."""
import asyncio
import math
import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx

KMA = "https://apihub.kma.go.kr/api/"
GEO = "https://geocoding-api.open-meteo.com/v1/"

class WeatherError(Exception):
    pass

async def get_response(client, url, params):
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response
    except httpx.HTTPStatusError as exc:
        raise WeatherError(f"Weather provider rejected the request (HTTP {exc.response.status_code}). Check API authorization.") from None
    except httpx.HTTPError:
        raise WeatherError("Weather provider could not be reached. Try again later.") from None


def location(item):
    try:
        result = {k: item[k] for k in ('id','name','latitude','longitude','timezone')}
        ZoneInfo(result['timezone'])
        result['label'] = ', '.join(str(item[k]) for k in ('name','admin1','country') if item.get(k))
        return result
    except (KeyError, ZoneInfoNotFoundError):
        raise WeatherError("The location provider returned incomplete location information.") from None

async def search_locations(query):
    async with httpx.AsyncClient(timeout=12) as client:
        response = await get_response(client, GEO+'search', dict(name=query,count=8,language='en',format='json'))
        try:
            return [location(item) for item in response.json().get('results', [])]
        except (ValueError, TypeError):
            raise WeatherError("Location response was invalid.") from None

async def resolve_location(client, location_id):
    response = await get_response(client, GEO+'get', dict(id=location_id,language='en',format='json'))
    try:
        return location(response.json())
    except (ValueError, TypeError):
        raise WeatherError("Location response was invalid.") from None


def parse_stations(text):
    # Column positions come from KMA's header, never a guessed fixed offset.
    header = None
    stations = []
    for line in text.splitlines():
        parts = line.lstrip('# ').split()
        upper = [p.upper() for p in parts]
        if line.startswith('#'):
            if 'STN' in upper and 'LAT' in upper and 'LON' in upper:
                header = upper
            continue
        if not line.strip() or header is None:
            continue
        try:
            stn = parts[header.index('STN')]
            lat = float(parts[header.index('LAT')]); lon = float(parts[header.index('LON')])
            if not stn.isdigit() or not 4 <= len(stn) <= 5 or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            stations.append(dict(id=stn.zfill(5),latitude=lat,longitude=lon))
        except (ValueError, IndexError):
            continue
    if not stations:
        raise WeatherError("KMA station metadata could not be parsed. Live header verification is required.")
    return stations


def distance_km(a, b):
    lat1,lat2 = map(math.radians, (a['latitude'],b['latitude']))
    dl = math.radians(b['longitude']-a['longitude'])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dl/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(h)))


def observation_times(day, tz, now=None):
    now = now or datetime.now(timezone.utc)
    start = datetime.combine(day,time(),ZoneInfo(tz)).astimezone(timezone.utc)
    end = datetime.combine(day+timedelta(days=1),time(),ZoneInfo(tz)).astimezone(timezone.utc)
    if start > now:
        raise WeatherError("Future observation dates cannot be requested.")
    # Global synoptic hours; retained timestamps must fall in the user's local day.
    cursor = start.replace(minute=0,second=0,microsecond=0)
    while cursor < start or cursor.hour % 3:
        cursor += timedelta(hours=1)
    result=[]
    while cursor < end and cursor <= now:
        result.append(cursor); cursor += timedelta(hours=3)
    return start,end,result


def number(value, low, high):
    try:
        n=float(value)
        if str(value).strip() in ('-99','-99.0','-99.9','-999','-999.0','-999.9'): return None
        return n if math.isfinite(n) and low <= n <= high else None
    except (ValueError,TypeError): return None


def parse_synop(payload, station_id, instant):
    try:
        envelope=payload['response']
        code=str(envelope['header']['resultCode'])
        if code == '03': return []
        if code != '00': raise WeatherError("KMA returned an API error. Check service authorization.")
        body=envelope['body']; items=(body.get('items') or {}).get('item',[])
        if isinstance(items,dict): items=[items]
        if int(body.get('totalCount',len(items))) > len(items):
            raise WeatherError("KMA returned a truncated page; observations were not used.")
        result=[]
        for row in items:
            if str(row['stnId']).zfill(5)!=station_id: raise WeatherError("KMA returned a different station.")
            tm=datetime.strptime(str(row['tm']).strip(),'%Y%m%d%H%M').replace(tzinfo=timezone.utc)
            if tm != instant: raise WeatherError("KMA returned a different observation time.")
            result.append(dict(time=tm.isoformat(),temperature_c=number(row.get('ta'),-90,60),
                humidity_pct=number(row.get('hm'),0,100),precipitation_mm=number(row.get('rn'),0,3000),
                precipitation_period_hours=number(row.get('rnWrchHr'),0,240),raw=row))
        return result
    except (KeyError,TypeError,ValueError):
        raise WeatherError("KMA observation response could not be decoded.") from None

async def fetch_weather(location_id, day):
    key=os.getenv('KMA_AUTH_KEY','').strip()
    if not key: raise WeatherError("Set KMA_AUTH_KEY in critic/.env and authorize the KMA world GTS services.")
    async with httpx.AsyncClient(timeout=12) as client:
        place=await resolve_location(client,location_id)
        start,end,times=observation_times(day,place['timezone'])
        if not times: raise WeatherError("No completed synoptic observation time is available for this local day yet.")
        response=await get_response(client,KMA+'typ01/url/stn_gts1.php',
            dict(tm=times[-1].strftime('%Y%m%d%H%M'),upp=0,mode=1,help=1,authKey=key))
        stations=parse_stations(response.text)
        station=min(stations,key=lambda s:distance_km(place,s))
        station['distance_km']=round(distance_km(place,station),1)
        if station['distance_km'] > 100:
            raise WeatherError("No GTS station within 100 km. A more distant station will not be substituted.")
        semaphore=asyncio.Semaphore(4)
        async def fetch(instant):
            async with semaphore:
                try:
                    r=await get_response(client,KMA+'typ02/openApi/GtsInfoService/getSynop',
                        dict(tm=instant.strftime('%Y%m%d%H%M'),stnId=station['id'],numOfRows=100,pageNo=1,dataType='JSON',authKey=key))
                    try: payload=r.json()
                    except ValueError: raise WeatherError("KMA returned a non-JSON response. Check service authorization.") from None
                    return parse_synop(payload,station['id'],instant),None
                except WeatherError as exc: return [],str(exc)
        responses=await asyncio.gather(*(fetch(t) for t in times))
        observations={row['time']:row for rows,_ in responses for row in rows}
        rows=sorted(observations.values(),key=lambda r:r['time'])
        errors=sorted({err for _,err in responses if err})
        values=[r['temperature_c'] for r in rows if r['temperature_c'] is not None]
        humidities=[r['humidity_pct'] for r in rows if r['humidity_pct'] is not None]
        return dict(status='partial' if rows else 'unavailable',location=place,station=station,
            observed_date=day.isoformat(),period_start=start.isoformat(),period_end=end.isoformat(),
            retrieved_at=datetime.now(timezone.utc).isoformat(),observations=rows,
            summary=dict(sample_count=len(rows),requested_sample_count=len(times),
                sampled_min_temperature_c=min(values) if values else None,
                sampled_max_temperature_c=max(values) if values else None,
                sampled_mean_humidity_pct=round(sum(humidities)/len(humidities),1) if humidities else None),
            sources=['https://apihub.kma.go.kr/apiList.do?seqApi=12', 'https://open-meteo.com/en/docs/geocoding-api'],
            limitations=errors+['Three-hourly samples are not daily extremes or climate normals.',
                'Station weather does not measure canopy humidity or leaf wetness. Rainfall windows are not summed.',
                'Only the observation day is sampled; earlier infection periods are not assessed.',
                'The nearest listed station may have no reports; no alternative station is silently substituted.'])


def compare_conditions(diseases, weather):
    """Retain source conditions; no disease probability or guessed numeric thresholds."""
    result=[]
    temperatures=[row['temperature_c'] for row in weather.get('observations',[]) if row.get('temperature_c') is not None]
    # Reviewed source-specific field ranges. Do not extract arbitrary numbers from prose.
    rules = {
        'maize_013': ('CPN Encyclopedia NCLB', '18–27 °C', 18, 27),
        'maize_014': ("Nongsaro 'Southern corn leaf blight (kkaessimunui-byeong)'", '20–30 °C', 20, 30),
    }
    for disease in diseases:
        conditions=[]
        for feature in disease['features']:
            category=str(feature.get('category','')).lower()
            if any(term in category for term in ('environment','weather','favorable','favourable','timing of occurrence')):
                conditions.append({k:feature.get(k) for k in ('category','description','source_name','url','location_in_source')})
        if conditions:
            temperature_check = None
            rule=rules.get(disease['disease_id'])
            if rule and temperatures:
                source,phrase,low,high=rule
                matched=next((c for c in conditions if c['source_name']==source and phrase in (c['description'] or '')),None)
                if matched and not disease['source_conflicts']:
                    temperature_check=dict(range_c=[low,high], samples_in_range=sum(low <= t <= high for t in temperatures),
                        valid_samples=len(temperatures), source_name=source,
                        interpretation='Sampled station temperature overlap only. Other required conditions are not established.')
            result.append(dict(disease_id=disease['disease_id'],name=disease['name_en'],conditions=conditions,
                assessment='manual_review_required',temperature_check=temperature_check,
                reason='Compare cited conditions with sampled station measurements; growth stage, canopy humidity and leaf wetness may be unknown.',
                source_conflicts=disease['source_conflicts']))
    return result
