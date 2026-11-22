"""Read-only source domains and isolated immutable monitoring/review writes."""

import json

from src.ingestion.s3_storage import S3Store
from src.pipeline.run_contract import ContractError, digest, encode


class MonitorStore(S3Store):
    """Read verified monitoring inputs and store private reports, alerts and review records."""
    def _get(self, key, *, optional=False):
        allowed = ('monitoring/', 'weekly/runs/', 'cloud-modeling/', 'cloud-ingestion/runs/', 'raw/cfbd/games/', 'datasets/')
        if not isinstance(key,str) or not key.startswith(tuple(self.prefix+'/'+s for s in allowed)):
            raise ContractError('Monitoring read outside approved project domains.')
        if optional:
            result = self.client.list_objects_v2(Bucket=self.bucket,Prefix=key,MaxKeys=1)
            if not any(r.get('Key')==key for r in result.get('Contents',[])): return None
        return super()._get(key,optional=False)

    def _put(self, key, content):
        if not key.startswith(self.prefix+'/monitoring/'):
            raise ContractError('Monitoring cannot write pipeline, source or model data.')
        # Failure-alert paths must not bypass a failed privacy preflight.
        self._private_bucket()
        return super()._put(key,content)


def verified_object(store, key, expected):
    content = store._get(key)
    if digest(content) != expected: raise ContractError('Monitoring input hash mismatch.')
    return content


def completion(store, base):
    content = store._get(base+'/complete.json',optional=True)
    if content is None: return None
    result = json.loads(content)
    for key,value in result['artifact_sha256'].items(): verified_object(store,key,value)
    return result


def publish(store, base, artifacts, facts):
    result = dict(facts,artifact_sha256={base+'/'+n:digest(v) for n,v in artifacts.items()})
    store._upload(base,dict(artifacts,**{'complete.json':encode(result)}),'complete.json')
    return result


def alert(store, evidence, code, severity, action, simulated=False):
    content = {'schema_version':1,'code':code,'severity':severity,'evidence':evidence,
               'recommended_investigation':action,'simulated':simulated,
               'retraining_authorized':False,'operational_publication_authorized':False}
    alert_id = digest(encode(content));content['alert_id'] = alert_id
    key = store.prefix+'/monitoring/alerts/'+alert_id+'/alert.json'
    data = encode(content);existing = store._get(key,optional=True)
    if existing is None: store._put(key,data)
    elif existing != data: raise ContractError('Conflicting alert record; existing evidence preserved.')
    return {'alert_id':alert_id,'sha256':digest(data),'key':key,'code':code,'severity':severity}
