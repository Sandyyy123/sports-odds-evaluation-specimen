import argparse,copy,json
from pathlib import Path
from evaluator import report

def fixtures():
    rows=[]
    for sport in ['synthetic_tennis','synthetic_basketball']:
        for i in range(400):
            # Each fixture has one synthetic signal; half win by construction.
            rows.append({'fixture_id':f'{sport}-{i}','signal_id':f's-{i}', 'sport':sport,
                         'market_key':'match|moneyline|incl_overtime|home',
                         'reference_market_key':'match|moneyline|incl_overtime|home',
                         'reference_time':10,'signal_time':11,'close_time':19,'start_time':20,
                         'active':True,'reference_active':True,'available_limit':100,'required_limit':10,
                         'reference_odds':[1.90,1.90], 'closing_odds':[1.88+(i%5)*.01,1.92-(i%5)*.01],
                         'outcome_index':0,'offered_odds':2.10, 'settlement':'win' if i%2==0 else 'loss'})
    for field,value in [('reference_market_key','match|moneyline|regulation|home'),('reference_time',12),('active',False),('available_limit',0),('offered_odds',1.90)]:
        r=copy.deepcopy(rows[0]);r['signal_id']=field;r[field]=value;rows.append(r)
    rows.append(copy.deepcopy(rows[0]))
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Offline synthetic evaluator, no external requests')
    parser.add_argument('--output',default='synthetic_report.json');args=parser.parse_args()
    data=report(fixtures());Path(args.output).write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))
