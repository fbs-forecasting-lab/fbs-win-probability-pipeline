"""Build a scalar-only static monitoring candidate, without publishing anything."""
import html
import json
import math

from src.features.games import _utc_timestamp
from src.pipeline.run_contract import STATUS, digest


def build_view(report_bytes, expected_sha256):
    """Extract allowlisted measurements from a hash-pinned private report.

    Returns a new public-safe dictionary. Raw rows, references, free text,
    alerts/reviewer details and individual predictions are never copied.
    Invalid state/count/identity fails; missing measurements stay unavailable.
    Hash verification alone does not establish trust: use a verified producer.
    """
    if len(report_bytes) > 4*1024*1024 or digest(report_bytes) != expected_sha256:
        raise ValueError('Verified report bytes are required.')
    report = json.loads(report_bytes)
    if any(report.get(k) != v for k, v in STATUS.items()) or report.get('operational_forecast_approved') is not False:
        raise ValueError('Retrospective safeguards differ.')
    quality, distributions, performance = (report[n] for n in ('quality', 'distributions', 'performance'))
    if distributions['state'] not in ('measured','insufficient_data','failed') or performance['state'] not in ('measured','pending','insufficient_data','failed'):
        raise ValueError('Unknown measurement state.')
    def count(value):
        if type(value) is not int or not 0 <= value <= 1000000:
            raise ValueError('Invalid count.')
        return value
    age = quality['source_age_seconds']
    if age is not None and (type(age) not in (float,int) or not math.isfinite(age) or age < 0):
        raise ValueError('Invalid saved observation age.')
    return dict(STATUS, as_of=_utc_timestamp(report['request']['as_of']),
                raw_records=count(quality['counts']['input']), retained=count(quality['counts']['retained']),
                quarantined=count(quality['counts']['quarantined']), technical_rows=count(quality['eligible']),
                saved_source_age_seconds=age, distribution_state=distributions['state'],
                performance_state=performance['state'],
                matched_outcomes=None if performance['state']=='failed' else count(performance['matched']),
                pending_outcomes=None if performance['state']=='failed' else count(performance['pending']),
                operational_forecast_approved=False)


def render(view):
    """Render only the fixed scalar schema as escaped HTML; no upload or delivery."""
    fields = set(STATUS) | {'as_of','raw_records','retained','quarantined','technical_rows','saved_source_age_seconds',
                           'distribution_state','performance_state','matched_outcomes','pending_outcomes','operational_forecast_approved'}
    if set(view) != fields or any(isinstance(v,(dict,list)) for v in view.values()):
        raise ValueError('Unexpected public view fields.')
    if any(view[k] != v for k,v in STATUS.items()) or view['operational_forecast_approved'] is not False:
        raise ValueError('Public safeguards differ.')
    _utc_timestamp(view['as_of'])
    if view['distribution_state'] not in ('measured','insufficient_data','failed') or view['performance_state'] not in ('measured','pending','insufficient_data','failed'):
        raise ValueError('Unknown measurement state.')
    for key in fields-set(STATUS)-{'as_of','distribution_state','performance_state','operational_forecast_approved'}:
        value=view[key]
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<0):
            raise ValueError('Only measured numeric values may be displayed.')
    rows = ''.join('<tr><th>'+html.escape(k.replace('_',' '))+'</th><td>'+html.escape('Unavailable' if v is None else str(v))+'</td></tr>' for k,v in view.items())
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Retrospective pipeline monitoring</title><style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:1rem}th,td{text-align:left;padding:6px;border-bottom:1px solid currentColor;overflow-wrap:anywhere}</style>'
            '<h1>Retrospective monitoring: operational approval withheld</h1>'
            '<p>Dated saved observation, not current live health. Pending labels are not zero error. Distribution changes do not prove concept drift.</p>'
            '<p>Static publication candidate; no automatic updates, notifications, retraining or forecast approval.</p><table>'+rows+'</table></html>').encode()
