"""Original synthetic evaluation specimen. Offline only; no bookmaker/API calls."""
from collections import defaultdict
from math import isfinite
from random import Random
from statistics import mean


def no_vig(odds):
    if len(odds) < 2 or any(not isfinite(x) or x <= 1 for x in odds):
        raise ValueError('Need a complete mutually exclusive market with decimal odds > 1')
    inverse = [1 / x for x in odds]
    return [x / sum(inverse) for x in inverse]


def assess_record(r):
    """Signal uses contemporaneous prices only; closing prices measure CLV later."""
    if r['market_key'] != r['reference_market_key']:
        return None, 'market mismatch'
    if r.get('settlement') not in ('win', 'loss'):
        return None, 'unsupported or missing settlement'
    if any(not isfinite(r[k]) for k in ('reference_time','signal_time','close_time','start_time','available_limit','required_limit')):
        return None, 'nonfinite time or limit'
    if r['required_limit'] <= 0:
        return None, 'invalid required limit'
    if not r['reference_time'] <= r['signal_time'] < r['close_time'] <= r['start_time']:
        return None, 'timestamp order'
    if not r.get('active', False) or not r.get('reference_active', False):
        return None, 'inactive quote'
    if not r.get('available_limit') or r['available_limit'] < r['required_limit']:
        return None, 'insufficient or unknown limit'
    if not isfinite(r['offered_odds']) or not 1.25 <= r['offered_odds'] <= 2.5:
        return None, 'odds outside requested range'
    i = r['outcome_index']
    if r['reference_outcome_ids'] != r['closing_outcome_ids'] or len(set(r['reference_outcome_ids'])) != len(r['reference_outcome_ids']):
        return None, 'outcome correspondence'
    if len(r['reference_outcome_ids']) != len(r['reference_odds']) or len(r['reference_odds']) != len(r['closing_odds']):
        return None, 'incomplete outcome correspondence'
    if not 0 <= i < len(r['reference_odds']):
        return None, 'outcome index'
    ps = no_vig(r['reference_odds'])[i]
    pc = no_vig(r['closing_odds'])[i]
    ev = r['offered_odds'] * ps - 1
    if ev < .03:
        return None, 'signal EV below 3 percent'
    win = r['settlement'] == 'win'
    return {'fixture_id':r['fixture_id'], 'sport':r['sport'], 'ev':ev,
            'clv':r['offered_odds'] * pc - 1,
            'roi':r['offered_odds'] * int(win) - 1,
            # Signal-sample diagnostic only. NOT the all-market calibration universe.
            'fair_close_return':int(win) / pc - 1}, None


def cluster_ci(rows, field, confidence=.95, reps=500, seed=17):
    """Percentile cluster bootstrap by fixture; equal-stake per-bet mean.

    Preserves multiple correlated signals within a fixture. Production may require
    date/block bootstrap as well. Small or degenerate samples are indeterminate.
    """
    groups=defaultdict(list)
    for r in rows: groups[r['fixture_id']].append(float(r[field]))
    if len(groups) < 30: return None
    summaries=[(sum(v),len(v)) for v in groups.values()]
    if len({x for values in groups.values() for x in values}) < 2:
        return None
    rng=Random(seed);dist=[];n=len(summaries)
    for _ in range(reps):
        picked=[summaries[rng.randrange(n)] for _ in range(n)]
        dist.append(sum(x[0] for x in picked)/sum(x[1] for x in picked))
    dist.sort();alpha=(1-confidence)/2
    def quantile(p):
        index=(len(dist)-1)*p;a=int(index);z=index-a
        return dist[a]*(1-z)+dist[min(a+1,len(dist)-1)]*z
    return [quantile(alpha),quantile(1-alpha)]


def report(records):
    kept=[];excluded=defaultdict(int)
    seen=set()
    for r in records:
        try:
            key=(r['fixture_id'],r['signal_id'])
            if key in seen: excluded['duplicate signal']+=1;continue
            seen.add(key)
            value,reason=assess_record(r)
        except (KeyError,TypeError,ValueError,IndexError):value,reason=None,'invalid schema'
        if reason:excluded[reason]+=1
        else:kept.append(value)
    sports={}
    for sport in sorted({r['sport'] for r in kept}):
        rows=[r for r in kept if r['sport']==sport]
        for r in rows:r['roi_minus_clv']=r['roi']-r['clv']
        clv_ci=cluster_ci(rows,'clv');roi_ci=cluster_ci(rows,'roi')
        diff_ci=cluster_ci(rows,'roi_minus_clv')
        # No full all-market universe or real execution log in this offline demo.
        # Therefore NEVER emit a passing sport or a pooled profitability claim.
        sports[sport]={'signals':len(rows),'fixtures':len({r['fixture_id'] for r in rows}),
            'mean_clv':mean(r['clv'] for r in rows),'clv_ci95':clv_ci,
            'roi_equal_stake':mean(r['roi'] for r in rows),'roi_ci95':roi_ci,
            'roi_minus_clv_ci95':diff_ci,
            'rule1':'INSUFFICIENT_DATA: all-market calibration universe absent',
            'rule2':'DIAGNOSTIC_ONLY: locked held-out evaluation and pooled test not supplied',
            'rule3':'INSUFFICIENT_DATA: accepted-bet observation log absent',
            'decision':'NOT_ELIGIBLE_FOR_LIVE_ALERTS'}
    return {'data_kind':'SYNTHETIC ONLY','method':'proportional no-vig; equal-stake; fixture-cluster percentile bootstrap',
            'input_records':len(records),'accepted_signals':len(kept),'excluded':dict(excluded),'sports':sports,
            'combined_roi90':'NOT COMPUTED: no prequalified held-out sport set',
            'limits':['No profitability inference from synthetic outcomes.',
                      'Calibration on selected signals alone is selection-biased; full market universe required.',
                      '30 accepted observations is a minimum count, not assurance of useful precision.',
                      'No exchange commission, void/partial settlement, time-block dependence or API adapter implemented.',
                      'No actual bets, bankroll operations, credentials or network access.']}
