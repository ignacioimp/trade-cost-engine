import copy,json,unittest
from pathlib import Path
from engine import reconcile

class CostTests(unittest.TestCase):
    def setUp(self): self.data=json.loads((Path(__file__).parents[1]/'examples/synthetic.json').read_text())
    def test_totals(self):
        r=reconcile(self.data); self.assertEqual(r['forecast_totals']['gross'],'1430.00'); self.assertEqual(r['recorded_actual_totals']['economic'],'1281.00'); self.assertEqual(r['recorded_actual_totals']['economic_per_unit'],'12.81')
    def test_duplicate_and_missing(self):
        r=reconcile(self.data); self.assertEqual(len(r['duplicates_skipped']),1); self.assertFalse(r['actual_complete']); self.assertIsNone(next(x for x in r['rows'] if x['cost_id']=='delivery')['actual_gross'])
    def test_variance(self):
        r=reconcile(self.data); self.assertEqual(next(x for x in r['rows'] if x['cost_id']=='freight')['gross_variance'],'11.00')
    def test_conflict(self):
        self.data['actual'][2]['amount']='211'; self.assertRaises(ValueError,reconcile,self.data)
    def test_payment_duplicates(self):
        self.data['payments'].append(copy.deepcopy(self.data['payments'][0])); r=reconcile(self.data); self.assertEqual(r['recorded_paid'],'400.00'); self.assertEqual(len(r['duplicates_skipped']),2)
    def test_overpayment(self):
        self.data['payments'][0]['amount']='1100'; self.assertIn('overpayment',[x['kind'] for x in reconcile(self.data)['flags']])
    def test_missing_fx(self):
        self.data['fx_to_base']={}; self.assertRaises(ValueError,reconcile,self.data)
    def test_bad_recoverable(self):
        self.data['forecast'][2]['recoverable']='151'; self.assertRaises(ValueError,reconcile,self.data)
    def test_unknown_payment(self):
        self.data['payments'][0]['invoice']='missing'; self.assertRaises(ValueError,reconcile,self.data)
    def test_zero_quantity(self):
        self.data['quantity']=0; self.assertRaises(ValueError,reconcile,self.data)
