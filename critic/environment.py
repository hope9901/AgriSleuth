"""Source-preserving environment assessment. No inferred infection probability."""
from datetime import date,timedelta

def evaluate_environment(references,weather):
    reports=weather.get('daily_reports',[])+[weather]
    rows={row['time']:row for report in reports for row in report.get('observations',[])}
    dates={report['observed_date'] for report in reports if report.get('observations')}
    observation=date.fromisoformat(weather.get('case_observed_date') or weather['observed_date'])
    result=[]
    for ref in references:
        p=ref['profile'];windows=[]
        for w in p['windows']:
            item={k:w.get(k) for k in ('window_id','applies_to','anchor','core','evidence_type','resolution','note')}
            if w['anchor']=='D' and w.get('unit')=='days' and isinstance(w.get('start'),int) and isinstance(w.get('end'),int):
                start=observation+timedelta(days=w['start']);end=observation+timedelta(days=w['end'])
                expected={(start+timedelta(days=i)).isoformat() for i in range((end-start).days+1)}
                item.update(start_date=str(start),end_date=str(end),covered_days=len(expected & dates),required_days=len(expected),coverage='dates_covered' if expected<=dates else 'incomplete')
            else:item.update(coverage='anchor_input_required')
            windows.append(item)
        checks=[]
        # Explicit collected rice-blast reference: air RH is NOT leaf wetness.
        if ref['disease_id']=='rice_001' and '20–25' in p['thresholds_text'] and '90%' in p['thresholds_text']:
            temperatures=[v['temperature_c'] for v in rows.values() if v.get('temperature_c') is not None]
            humidity=[v['humidity_pct'] for v in rows.values() if v.get('humidity_pct') is not None]
            for metric,values,low,high in [('station_temperature_overlap_20_25_c',temperatures,20,25),('station_humidity_at_least_90_pct',humidity,90,100)]:
                checks.append(dict(metric=metric,samples_matching=sum(low<=v<=high for v in values),valid_samples=len(values),interpretation='Sample overlap only; not the required five-day mean, sustained wetness or infection assessment.',sources=[source for source in p['threshold_sources'] if source['label']=='RDA 2023-06-15']))
        result.append(dict(disease_id=ref['disease_id'],name=p['disease_en'],name_ko=p['disease_ko'],assessment='insufficient_for_infection_assessment',
            reference_language='en',thresholds_text=p['thresholds_text'],sources=p['threshold_sources'],required_inputs=p['required_inputs'],
            key_weather_variables=p['key_weather_variables'],evidence_summary=p['evidence_summary'],windows=windows,checks=checks,
            limitations=['Collected reference claims have not all been independently verified.','Three-hourly station air observations do not establish canopy humidity, leaf wetness, continuous duration or infection.','Unresolved growth-stage anchors and incomplete observation windows remain unknown.'],reference_sha256=ref['content_sha256']))
    return result

async def attach_environment(report,crop):
    import database
    refs=await database.weather_references(crop)
    report['environment_assessments']=evaluate_environment(refs,report)
    return report
