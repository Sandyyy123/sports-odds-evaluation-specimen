import copy,unittest
from evaluator import no_vig,assess_record,report,cluster_ci
from main import fixtures

class EvaluationContracts(unittest.TestCase):
 def setUp(self):self.r=fixtures()[0]
 def test_no_vig_complete_market(self):
  p=no_vig([1.9,1.9]);self.assertEqual(p,[.5,.5]);self.assertAlmostEqual(sum(no_vig([2,3,4])),1)
 def test_invalid_odds(self):
  for odds in [[1],[1,2],[float('nan'),2],[0,2]]:
   with self.assertRaises(ValueError):no_vig(odds)
 def test_future_close_cannot_change_signal_ev(self):
  a,_=assess_record(self.r);r=copy.deepcopy(self.r);r['closing_odds']=[1.5,3]
  b,_=assess_record(r);self.assertEqual(a['ev'],b['ev']);self.assertNotEqual(a['clv'],b['clv'])
 def test_mismatch_and_future_reference_rejected(self):
  for field,value,reason in [('reference_market_key','regulation','market mismatch'),('reference_time',12,'timestamp order')]:
   r=copy.deepcopy(self.r);r[field]=value;self.assertEqual(assess_record(r)[1],reason)
 def test_duplicate_has_no_extra_signal(self):
  r=report([self.r,copy.deepcopy(self.r)]);self.assertEqual(r['accepted_signals'],1);self.assertEqual(r['excluded']['duplicate signal'],1)
 def test_missing_real_data_never_passes(self):
  r=report(fixtures());self.assertEqual(r['accepted_signals'],800)
  for s in r['sports'].values():self.assertEqual(s['decision'],'NOT_ELIGIBLE_FOR_LIVE_ALERTS');self.assertIn('absent',s['rule3'])
 def test_cluster_count_not_rows(self):
  rows=[{'fixture_id':'one','x':i} for i in range(100)];self.assertIsNone(cluster_ci(rows,'x'))
 def test_bootstrap_reproducible(self):
  rows=[{'fixture_id':str(i),'x':(-1)**i} for i in range(40)];self.assertEqual(cluster_ci(rows,'x'),cluster_ci(rows,'x'))
 def test_all_requested_exclusions_counted(self):
  r=report(fixtures());self.assertEqual(sum(r['excluded'].values()),6)

if __name__=='__main__':unittest.main()
