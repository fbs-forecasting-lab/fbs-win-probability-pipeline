"""Fictional captured-event matching; all network access is blocked."""
import unittest
from unittest.mock import patch
from src.features.market_mapping import build_event_map


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('requests.sessions.Session.request', side_effect=AssertionError('offline')))
        self.enterContext(patch('botocore.httpsession.URLLib3Session.send', side_effect=AssertionError('offline')))
        self.p = {'game_id':'1','home_id':'11','away_id':'22','home_team':'Fictional Owls','away_team':'Fictional Bears','cutoff':'2026-11-25T20:00:00Z'}
        self.q = {'bookmaker':'draftkings','event_id':'fictional-1','home':'Fictional Owls','away':'Fictional Bears','kickoff':'2026-11-25T15:00:00-05:00'}
    def test_exact_identity_and_equivalent_utc_kickoff(self):
        r = build_event_map([self.p],[self.q]); self.assertEqual(r['event_map'][0]['market_event_id'],'fictional-1')
    def test_no_fuzzy_name_or_reversed_orientation_or_changed_kickoff(self):
        for q in (dict(self.q,home='Fictional Owl'),dict(self.q,home=self.q['away'],away=self.q['home']),dict(self.q,kickoff='2026-11-25T21:00:00Z')):
            self.assertEqual(build_event_map([self.p],[q])['event_map'],[])
    def test_missing_or_other_bookmaker_is_not_substituted(self):
        self.assertEqual(build_event_map([self.p],[])['event_map'],[])
        self.assertEqual(build_event_map([self.p],[dict(self.q,bookmaker='other')])['event_map'],[])
    def test_duplicate_events_and_duplicate_matchups_are_ambiguous(self):
        for rows in ([self.q,self.q],[self.q,dict(self.q,event_id='fictional-2')]):
            self.assertEqual(build_event_map([self.p],rows)['event_map'],[])
        self.assertEqual(build_event_map([self.p,dict(self.p,game_id='2')],[self.q])['event_map'],[])
    def test_reviewed_literal_alias_not_inferred(self):
        q=dict(self.q,home='Fictional Owls University')
        self.assertEqual(build_event_map([self.p],[q])['event_map'],[])
        r=build_event_map([self.p],[q],aliases={'11':q['home']})
        self.assertEqual(len(r['event_map']),1);self.assertEqual(r['reviewed_aliases'],{'11':q['home']})
    def test_unrelated_or_ambiguous_alias_and_duplicate_game_refused(self):
        for a in ({'99':'Unknown'},{'11':'Same','22':'Same'}):
            with self.assertRaises(ValueError):build_event_map([self.p],[self.q],aliases=a)
        with self.assertRaises(ValueError):build_event_map([self.p,self.p],[self.q])
