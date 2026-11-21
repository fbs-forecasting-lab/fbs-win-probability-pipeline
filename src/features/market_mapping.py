"""Deterministic evidence-only event mapping; no fuzzy names or provider requests."""
from collections import Counter

from src.features.markets import instant
from src.pipeline.run_contract import ContractError


def build_event_map(predictions, markets, bookmaker='draftkings', aliases=None):
    """Map unique exact home/away/kickoff triples; aliases bind team IDs explicitly.

    Call only with hash-verified captured rows. Aliases are a reviewed ID-to-exact
    provider-name crosswalk recorded with the mapping, never inferred synonyms.
    Returns an event_map and exclusions, including a legitimate empty overlap.
    """
    aliases = {} if aliases is None else aliases
    if not isinstance(aliases, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v.strip() for k, v in aliases.items()):
        raise ContractError('Aliases require explicit team IDs and literal provider names.')
    known = {str(r[k]) for r in predictions for k in ('home_id', 'away_id')}
    if not set(aliases) <= known or len(set(aliases.values())) != len(aliases):
        raise ContractError('Unrelated or ambiguous team aliases.')
    counts = Counter(str(r['game_id']) for r in predictions)
    if any(v != 1 for v in counts.values()):
        raise ContractError('Duplicate prediction game IDs.')
    selected = [r for r in markets if r['bookmaker'] == bookmaker]
    event_counts = Counter(r['event_id'] for r in selected)
    result, excluded = [], []
    for row in sorted(predictions, key=lambda r: str(r['game_id'])):
        home = aliases.get(str(row['home_id']), row.get('home_team'))
        away = aliases.get(str(row['away_id']), row.get('away_team'))
        candidates = [q for q in selected if home and away and q['home'] == home and q['away'] == away
                      and instant(q['kickoff']) == instant(row['cutoff'])]
        if len(candidates) != 1 or event_counts[candidates[0]['event_id']] != 1:
            excluded.append({'game_id': str(row['game_id']), 'reason': 'missing_or_ambiguous_exact_match'})
            continue
        q = candidates[0]
        result.append({'game_id': str(row['game_id']), 'home_id': str(row['home_id']), 'away_id': str(row['away_id']),
                       'market_event_id': q['event_id'], 'market_home': q['home'], 'market_away': q['away']})
    reused = Counter(r['market_event_id'] for r in result)
    duplicates = {r['game_id'] for r in result if reused[r['market_event_id']] != 1}
    excluded.extend({'game_id': g, 'reason': 'provider_event_reused'} for g in sorted(duplicates))
    return {'event_map': [r for r in result if r['game_id'] not in duplicates],
            'excluded': excluded, 'reviewed_aliases': dict(aliases)}
