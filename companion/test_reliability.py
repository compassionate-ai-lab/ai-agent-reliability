import json
import math
import os
import tempfile
import unittest
from flexiagent import Service, execute, Rejected, UncertainCommit
from metrics import lower, upper, weighted, gate, repeat_block, cpao

class TransactionTests(unittest.TestCase):
    def setUp(self): self.s=Service(); self.s.seed()
    def tearDown(self): self.s.close()
    def test_normal(self):
        execute(self.s,self.s.proposal()); self.assertEqual(self.s.record()['writes'],1)
    def test_timeout_reconciles_once(self):
        p=self.s.proposal(); execute(self.s,p,'timeout_after_commit')
        execute(self.s,p); self.assertEqual(self.s.record()['writes'],1)
    def test_raw_timeout_is_uncertain(self):
        p=self.s.proposal()
        with self.assertRaises(UncertainCommit): self.s.commit(p,'timeout_after_commit')
        self.assertEqual(self.s.record()['writes'],1)
        self.assertIsNotNone(self.s.reconcile(p))
    def test_op_reuse_payload(self):
        p=self.s.proposal(); self.s.commit(p); p['address']='evil'
        with self.assertRaises(Rejected): self.s.commit(p)
    def test_revoked_no_effect(self):
        p=self.s.proposal(); self.s.revoke()
        with self.assertRaises(Rejected): self.s.commit(p)
        self.assertEqual(self.s.record()['writes'],0)
    def test_scope(self):
        self.s.db.execute("INSERT INTO records VALUES('other','r','old',1,0)")
        p=self.s.proposal(); p['tenant']='other'
        with self.assertRaises(Rejected): self.s.commit(p)
        self.assertEqual(self.s.record('other')['writes'],0)
    def test_authority_revision(self):
        p=self.s.proposal(); self.s.db.execute('UPDATE authority SET revision=2')
        with self.assertRaises(Rejected): self.s.commit(p)
    def test_policy_revision(self):
        p=self.s.proposal(); self.s.advance_policy()
        with self.assertRaises(Rejected): self.s.commit(p)
        fresh=self.s.proposal(); execute(self.s,fresh)
        self.assertEqual(self.s.record()['writes'],1)
    def test_conflicting_workers(self):
        p=self.s.proposal(op='a'); q=self.s.proposal(address='second',op='b')
        self.s.commit(p)
        with self.assertRaises(Rejected): self.s.commit(q)
        self.assertEqual(self.s.record()['writes'],1)
    def test_receipt_after_revocation_no_new_write(self):
        p=self.s.proposal(); self.s.commit(p); self.s.revoke(); self.s.commit(p)
        self.assertEqual(self.s.record()['writes'],1)
    def test_schema_rejected(self):
        p=self.s.proposal(); p['extra']='instruction'
        with self.assertRaises(Rejected): self.s.commit(p)
    def test_unknown_scope(self):
        with self.assertRaises(Rejected): self.s.proposal(tenant='absent')
    def test_types_rejected(self):
        for field,value in [('authority_revision',True),('address',{}),('rid','')]:
            p=self.s.proposal();p[field]=value
            with self.assertRaises(Rejected):self.s.commit(p)
    def test_checkpoint_tamper(self):
        self.s.checkpoint('m',{'op':'a'})
        self.s.db.execute("UPDATE checkpoints SET payload='{}'")
        with self.assertRaises(Rejected): self.s.restore('m')
    def test_checkpoint_roundtrip(self):
        p=self.s.proposal(); self.s.checkpoint('m',p); self.assertEqual(self.s.restore('m'),p)
    def test_memory_correction_isolation_delete(self):
        self.s.remember('t','city','old'); self.s.remember('t','city','new')
        self.assertEqual(self.s.recall('t','city'),'new')
        self.assertIsNone(self.s.recall('other','city'))
        self.s.forget('t','city'); self.assertIsNone(self.s.recall('t','city'))
    def test_crash_reopen(self):
        with tempfile.TemporaryDirectory() as d:
            path=os.path.join(d,'state.db'); a=Service(path); a.seed()
            p=a.proposal(); a.checkpoint('m',p)
            with self.assertRaises(UncertainCommit): a.commit(p,'timeout_after_commit')
            a.close(); b=Service(path)
            restored=b.restore('m'); execute(b,restored)
            self.assertEqual(b.record()['writes'],1); b.close()

class BoundTests(unittest.TestCase):
    def test_zero(self): self.assertEqual(lower(0,10),0)
    def test_all(self): self.assertAlmostEqual(lower(10,10),.05**.1)
    def test_none(self): self.assertIsNone(lower(0,0))
    def test_invalid(self):
        for args in [(2,1,.05),(-1,1,.05),(1,2,0),(1.,2,.05),(True,2,.05)]:
            with self.assertRaises(ValueError): lower(*args)
    def test_reference_96(self): self.assertAlmostEqual(lower(96,100),.9108,places=4)
    def test_upper_zero(self): self.assertAlmostEqual(upper(0,1000),1-.05**.001)
    def test_upper_all(self): self.assertEqual(upper(10,10),1)
    def test_monotonic_successes(self):
        vals=[lower(x,20) for x in range(21)]
        self.assertTrue(all(a<=b for a,b in zip(vals,vals[1:])))
    def test_added_failure(self): self.assertLess(lower(9,11),lower(9,10))
    def test_missing_not_renormalized(self):
        r=weighted([dict(x=10,n=10,weight=.7),dict(x=0,n=0,weight=.3)])
        self.assertFalse(r['qualified_evidence']); self.assertLess(r['lower_floor'],.7)
    def test_bad_weights(self):
        with self.assertRaises(ValueError): weighted([dict(x=1,n=1,weight=.5)])
    def test_gate(self):
        self.assertEqual(gate(True,True,1),'Criteria not met')
        self.assertEqual(gate(False,True,0),'Insufficient evidence')
        self.assertEqual(gate(False,False,1),'Criteria not met')
        self.assertEqual(gate(False,False,0),'Insufficient evidence')
        self.assertEqual(gate(True,False,0),'Criteria not met')
        self.assertEqual(gate(True,True,0),'Qualified within the stated envelope')
    def test_repeat(self): self.assertEqual(repeat_block([1,1,0]),0)
    def test_economics(self):
        self.assertIsNone(cpao([1],0)); self.assertEqual(cpao([1,2],2),1.5)

class ProfileTests(unittest.TestCase):
    def test_card_gate(self):
        from scorecard import build,illustrative_registry
        r=build(illustrative_registry())
        self.assertEqual(r['constituent_bounds'],9)
        self.assertEqual(r['status'],'Criteria not met')
        self.assertIn('confirmed hard-gate violation',r['reasons'])
        self.assertIn('no approved release criteria',r['reasons'])
    def test_no_criteria_cannot_qualify(self):
        from scorecard import build,illustrative_registry
        r=illustrative_registry();r['critical_events']=0
        self.assertEqual(build(r)['status'],'Insufficient evidence')
    def test_unknown_stress_not_dropped(self):
        from scorecard import build,illustrative_registry
        r=illustrative_registry();r['claims'][-1]['groups'][-1].update(x=0,n=0)
        card=build(r);self.assertEqual(card['rows'][-1]['score'],0)
        self.assertFalse(card['rows'][-1]['evidence_complete'])
    def test_duplicate_claim_rejected(self):
        from scorecard import build,illustrative_registry
        r=illustrative_registry();r['claims'].append(r['claims'][0])
        with self.assertRaises(ValueError):build(r)
    def test_verifier_partition(self):
        wrong_plan=.97*.03+.03*.7;wrong=wrong_plan*.9+(1-wrong_plan)*.02
        parts=[(1-wrong)*.99,(1-wrong)*.01,wrong*.6,wrong*.4]
        self.assertAlmostEqual(sum(parts),1)

if __name__=='__main__': unittest.main()
