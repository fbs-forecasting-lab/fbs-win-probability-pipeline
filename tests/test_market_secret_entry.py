"""Hidden-entry guards with fake clients only; no secret or cloud action occurs."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

spec=importlib.util.spec_from_file_location('entry',Path(__file__).resolve().parents[1]/'bin/enter_market_secret.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)

class SecretEntryTests(unittest.TestCase):
    def run_entry(self,approved=True,tty=True,account='synthetic-account'):
        args=['entry','--expected-account','synthetic-account']+(['--approved-create'] if approved else [])
        sts=Mock();sts.get_caller_identity.return_value={'Account':account};secret=Mock()
        with patch('sys.argv',args),patch.object(entry.sys.stdin,'isatty',return_value=tty),patch.object(entry.sys.stderr,'isatty',return_value=tty),patch.object(entry.getpass,'getpass',return_value='synthetic-key-only') as prompt,patch.object(entry.boto3,'client',side_effect=[sts,secret]) as client,patch('builtins.print') as output:
            if not approved or not tty or account!='synthetic-account':
                with self.assertRaises(SystemExit):entry.main()
                prompt.assert_not_called();secret.create_secret.assert_not_called()
            else:
                entry.main();secret.create_secret.assert_called_once_with(Name='fbs/the-odds-api-key',SecretString='synthetic-key-only')
                self.assertNotIn('synthetic-key-only',str(output.call_args))
    def test_approval_required(self):self.run_entry(approved=False)
    def test_real_terminal_required(self):self.run_entry(tty=False)
    def test_account_mismatch_before_prompt(self):self.run_entry(account='other')
    def test_single_create_and_value_withheld(self):self.run_entry()
    def test_echo_fallback_is_fatal_before_secret_creation(self):
        sts=Mock();sts.get_caller_identity.return_value={'Account':'synthetic-account'}
        with patch('sys.argv',['entry','--approved-create','--expected-account','synthetic-account']),patch.object(entry.sys.stdin,'isatty',return_value=True),patch.object(entry.sys.stderr,'isatty',return_value=True),patch.object(entry.boto3,'client',return_value=sts),patch.object(entry.getpass,'getpass',side_effect=entry.getpass.GetPassWarning('no echo control')):
            with self.assertRaises(SystemExit):entry.main()
            sts.create_secret.assert_not_called()
