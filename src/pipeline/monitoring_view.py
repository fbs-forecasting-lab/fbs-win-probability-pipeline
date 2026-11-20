"""Strict allowlist stakeholder draft; no raw rows, reviewer identities or private references."""

import html
import json


def stakeholder(report):
    quality, drift, perf = report['quality'],report['distributions'],report['performance']
    return {'title':'Retrospective pipeline monitoring — operational publication withheld',
            'pipeline_status':report['pipeline_state'],'as_of':report['request']['as_of'],
            'source_age_seconds':quality['source_age_seconds'],'raw_records':quality['counts']['input'],
            'quarantined':quality['counts']['quarantined'],'technical_rows':quality['eligible'],
            'distribution_status':drift['state'],'distribution_indicators':sum(bool(v['changed']) for v in drift.get('features',{}).values()),
            'performance_status':perf['state'],'matched_outcomes':perf.get('matched',0),
            'pending_outcomes':perf.get('pending',0),'review_state':report['review_state'],
            'alert_count':len(report['alerts']),'operational_forecast_approved':False,
            'limitation':'No automatic retraining or operational approval; missing labels are not zero error.'}


def render(view):
    rows=''.join('<tr><th>'+html.escape(key.replace('_',' '))+'</th><td>'+html.escape(str(value))+'</td></tr>'
                 for key,value in view.items() if key!='title')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>Pipeline monitoring draft</title><style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:1rem}'
            'th,td{text-align:left;padding:6px 12px;border-bottom:1px solid currentColor;overflow-wrap:anywhere}</style>'
            '<h1>'+html.escape(view['title'])+'</h1><p>Private draft — not published.</p><table>'+rows+'</table></html>').encode()
