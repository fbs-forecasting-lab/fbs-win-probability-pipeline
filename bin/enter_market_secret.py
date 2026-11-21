"""Future approved hidden-terminal secret creation; never call during preparation."""
import argparse
import getpass
import sys
import warnings
import boto3
from botocore.config import Config


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--approved-create',action='store_true')
    p.add_argument('--expected-account',required=True)
    a=p.parse_args()
    if not a.approved_create or not sys.stdin.isatty() or not sys.stderr.isatty():
        p.error('Separate creation approval and a real hidden-input terminal are required.')
    cfg=Config(connect_timeout=5,read_timeout=20,retries={'total_max_attempts':1})
    if boto3.client('sts',region_name='us-east-1',config=cfg).get_caller_identity()['Account'] != a.expected_account:
        raise SystemExit('Account mismatch; nothing created.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            value=getpass.getpass('Market key (hidden): ')
    except (getpass.GetPassWarning, EOFError, OSError):
        raise SystemExit('Hidden input unavailable; nothing created.') from None
    if not 8 <= len(value) <= 512 or any(c.isspace() for c in value):
        raise SystemExit('Invalid key format; nothing created.')
    try:
        client=boto3.client('secretsmanager',region_name='us-east-1',config=cfg)
        client.create_secret(Name='fbs/the-odds-api-key',SecretString=value)
    except Exception:
        raise SystemExit('Secret creation stopped; inspect metadata off screen before any retry.') from None
    finally:
        value=None
    print('Secret created; value withheld. Record its ARN through metadata only.')


if __name__=='__main__':main()
