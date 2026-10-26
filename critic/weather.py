"""World GTS observations from KMA; geocoding is separate from weather evidence."""
import asyncio
import csv
import io
import math
import os
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import httpx

KMA = "https://apihub.kma.go.kr/api/"
STATION_CATALOG = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
SYNOP_URL = KMA + "typ01/url/gts_bufr_syn1.php"
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

def parse_station_catalog(text, day):
    """NOAA ISD metadata only; six-digit USAF WMO entries ending in zero."""
    reader = csv.DictReader(io.StringIO(text))
    if not {'USAF', 'LAT', 'LON', 'BEGIN', 'END'} <= set(reader.fieldnames or []):
        raise WeatherError("NOAA station catalog header could not be decoded.")
    stations = {}
    for row in reader:
        code = row['USAF']
        if len(code) != 6 or not code.isdigit() or not code.endswith('0'):
            continue
        try:
            lat, lon = float(row['LAT']), float(row['LON'])
            begin = datetime.strptime(row['BEGIN'], '%Y%m%d').date()
            end = datetime.strptime(row['END'], '%Y%m%d').date()
        except (ValueError, TypeError):
            continue
        if begin > day or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            continue
        stn = code[:5]
        candidate = dict(id=stn, latitude=lat, longitude=lon,
                         name=row.get('STATION NAME', ''), metadata_end=end.isoformat(),
                         metadata_source=STATION_CATALOG)
        if stn not in stations or candidate['metadata_end'] > stations[stn]['metadata_end']:
            stations[stn] = candidate
    if not stations:
        raise WeatherError("No usable stations in NOAA catalog.")
    return list(stations.values())


def parse_bufr_synop(text, station_id, instant):
    """Parse the actual KMA help=1 text header. RH is a code, not hours."""
    header = None
    rows = []
    for line in text.splitlines():
        parts = line.lstrip('# ').split()
        if line.startswith('#'):
            if parts and parts[0] == 'YYMMDDHHMI' and {'STN','TA','HM','RN','RH'} <= set(parts):
                header = parts
            continue
        if not line.strip():
            continue
        if header is None or len(parts) != len(header):
            raise WeatherError("KMA SYNOP text has an unexpected header or row length.")
        raw = dict(zip(header, parts))
        try:
            tm = datetime.strptime(raw['YYMMDDHHMI'], '%Y%m%d%H%M').replace(tzinfo=timezone.utc)
        except ValueError:
            raise WeatherError("KMA SYNOP timestamp is invalid.") from None
        if raw['STN'].zfill(5) != station_id or tm != instant:
            raise WeatherError("KMA returned a different station or observation time.")
        rows.append(dict(time=tm.isoformat(), temperature_c=number(raw['TA'],-90,60),
                         humidity_pct=number(raw['HM'],0,100), precipitation_mm=number(raw['RN'],0,3000),
                         precipitation_period_hours={'1':6,'2':12,'3':18,'4':24,'5':1,'6':2,'7':3,'8':9,'9':15}.get(raw['RH']), raw=raw))
    if header is None or '#7777END' not in text:
        raise WeatherError("KMA SYNOP response is missing its header or completion marker.")
    return rows


async def fetch_weather(location_id, day):
    key=os.getenv('KMA_AUTH_KEY','').strip()
    if not key: raise WeatherError("Set KMA_AUTH_KEY in critic/.env and authorize the KMA world GTS services.")
    async with httpx.AsyncClient(timeout=35) as client:
        place=await resolve_location(client,location_id)
        start,end,times=observation_times(day,place['timezone'])
        if not times: raise WeatherError("No completed synoptic observation time is available for this local day yet.")
        response=await get_response(client,STATION_CATALOG,{})
        stations=parse_station_catalog(response.text,day)
        station=min(stations,key=lambda s:distance_km(place,s))
        station['distance_km']=round(distance_km(place,station),1)
        if station['distance_km'] > 100:
            raise WeatherError("No GTS station within 100 km. A more distant station will not be substituted.")
        semaphore=asyncio.Semaphore(4)
        async def fetch(instant):
            async with semaphore:
                try:
                    r=await get_response(client,SYNOP_URL,
                        dict(tm=instant.strftime('%Y%m%d%H%M'),dtm=0,stn=station['id'],help=1,authKey=key))
                    return parse_bufr_synop(r.text,station['id'],instant),None
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
            sources=[SYNOP_URL, STATION_CATALOG, 'https://open-meteo.com/en/docs/geocoding-api'],
            limitations=errors+[f"Station coordinates use NOAA ISD metadata (record ends {station['metadata_end']}); station activity on the requested date is not guaranteed.", 'Three-hourly samples are not daily extremes or climate normals.',
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


COUNTRY_STATIONS_URL=KMA+'typ02/openApi/GtsInfoService/getGtsStn'

def parse_country_stations(text):
    import xml.etree.ElementTree as ET
    try:
        root=ET.fromstring(text)
        code=root.findtext('./header/resultCode')
        if code=='03':return [],0
        if code!='00':raise WeatherError('KMA country-station API rejected the country/category request.')
        total=int(root.findtext('./body/totalCount','0'));items=[]
        for item in root.findall('./body/items/item'):
            stn=item.findtext('stnId','').strip()
            if not stn.isdigit() or len(stn)>5:raise ValueError('Invalid station ID')
            items.append(dict(id=stn.zfill(5),country_name='Russia' if item.findtext('countryName','')=='\ub7ec\uc2dc\uc544' else item.findtext('countryName',''),name=item.findtext('stnNm','')))
        if total<0 or total>10000:raise ValueError('Unexpected station count')
        return items,total
    except (ET.ParseError,ValueError):raise WeatherError('KMA country-station XML could not be decoded.') from None

async def country_stations(country_code,category='temp'):
    if not country_code.isdigit() or not 1<=len(country_code)<=8 or category not in ('temp','rain'):
        raise WeatherError('Use an explicit numeric KMA country code and temp/rain category.')
    key=os.getenv('KMA_AUTH_KEY','').strip()
    if not key:raise WeatherError('KMA_AUTH_KEY is not configured.')
    async with httpx.AsyncClient(timeout=20) as client:
        all_items=[];page=1;expected=None
        while True:
            response=await get_response(client,COUNTRY_STATIONS_URL,dict(numOfRows=100,pageNo=page,dataType='XML',cc=country_code,category=category,authKey=key))
            items,total=parse_country_stations(response.text)
            if expected is not None and total!=expected:raise WeatherError('KMA station count changed during pagination.')
            expected=total;all_items.extend(items)
            if len(all_items)>=total:break
            if not items or page>=100:raise WeatherError('KMA station list is incomplete.')
            page+=1
        unique={item['id']:item for item in all_items}
        if len(unique)!=expected:raise WeatherError('KMA country station pagination contains duplicate or missing entries.')
        metadata_sources=[]
        has_hangul=lambda value:any('\uac00'<=ch<='\ud7a3' for ch in value)
        if any(has_hangul(item['name']) for item in unique.values()):
            names={}
            try:
                catalog=await get_response(client,STATION_CATALOG,{})
                names={item['id']:item['name'] for item in parse_station_catalog(catalog.text,date.today())}
                metadata_sources.append(STATION_CATALOG)
            except WeatherError:
                pass
            for item in unique.values():
                if has_hangul(item['name']):item['name']=names.get(item['id'],f"Station {item['id']}")
        for item in unique.values():
            if has_hangul(item['country_name']):item['country_name']=f"KMA country {country_code}"
        return dict(country_code=country_code,category=category,total_count=expected,stations=list(unique.values()),source=COUNTRY_STATIONS_URL,metadata_sources=metadata_sources,
                    limitations=['KMA country codes must be provided explicitly; 1001 is Russia, not Korea.','This service supplies station IDs/names, not coordinates or weather measurements. Korean station names use NOAA English aliases when available; otherwise Station ID is displayed.'])
