"""Isolated immutable outputs and durable, at-most-once external attempt ledgers."""
from src.ingestion.s3_storage import S3Store
from src.pipeline.monitor_storage import MonitorStore,completion,publish,verified_object
from src.pipeline.cloud_ingestion import create_once
from src.pipeline.run_contract import ContractError,digest,encode

class InsightsStore(MonitorStore):
    """Preserve source-bound explanation and market claims, response checkpoints and immutable results."""
    def _get(self,key,*,optional=False):
        if not isinstance(key,str) or not key.startswith(self.prefix+'/stakeholder/'):
            return super()._get(key,optional=optional)
        if optional:
            response=self.client.list_objects_v2(Bucket=self.bucket,Prefix=key,MaxKeys=1)
            if not any(v.get('Key')==key for v in response.get('Contents',[])):return None
        return S3Store._get(self,key,optional=False)
    def _put(self,key,content):
        if not key.startswith(self.prefix+'/stakeholder/'):raise ContractError('Stakeholder adapters cannot change source/model/monitoring evidence.')
        self._private_bucket()
        return S3Store._put(self,key,content)

def claim(store,base,identity):
    store._private_bucket();raw=encode(identity)
    if store._get(base+'/claim.json',optional=True) is None:create_once(store,base+'/claim.json',raw)
    if store._get(base+'/claim.json')!=raw:raise ContractError('Token conflicts with the original request/configuration/code.')
    return digest(raw)

def external_once(store,base,claim_sha256,call):
    from src.pipeline.insights_contract import decode,MAX_MARKET_BYTES
    existing=store._get(base+'/response.json',optional=True)
    if existing is not None:
        result=decode(existing,2*MAX_MARKET_BYTES)
        if result['claim_sha256']!=claim_sha256 or result['result_sha256']!=digest(encode(result['result'])):raise ContractError('Response checkpoint identity differs.')
        return result['result']
    store._private_bucket()
    attempt=encode({'claim_sha256':claim_sha256,'provider_attempts':1})
    if not create_once(store,base+'/attempt.json',attempt):
        if store._get(base+'/attempt.json')!=attempt:raise ContractError('Conflicting provider-attempt marker.')
        # The call may have happened. Never refetch or publish a guessed completion.
        return None
    result=call()
    store._put(base+'/response.json',encode({'claim_sha256':claim_sha256,'result_sha256':digest(encode(result)),'result':result}))
    return result

def replay(store,base,request):
    result=completion(store,base)
    if result is not None and result['request']!=request:raise ContractError('Completed request identity differs.')
    return result
