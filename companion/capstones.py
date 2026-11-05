"""Small executable transfer studies with explicit failure and unresolved cases."""
import json
from pathlib import Path
from flexiagent import Service,execute,Rejected

def service_case():
    s=Service();s.seed();p=s.proposal();execute(s,p,'timeout_after_commit')
    good=s.record()['writes']==1 and s.record()['address']=='new'
    s.close()
    stale=Service();stale.seed();proposal=stale.proposal();stale.advance_policy()
    try:
        stale.commit(proposal);stale_rejected=False
    except Rejected:
        stale_rejected=stale.record()['writes']==0
    stale.close()
    missing=Service();missing.seed();proposal=missing.proposal();missing.commit(proposal)
    required_final_evidence=None
    unresolved=required_final_evidence is None
    missing.close()
    return dict(domain='service',accepted=good,
                failed_productive_case={'stale_proposal_rejected':stale_rejected,
                                        'mission_completed':False},
                unresolved={'required_final_evidence_missing':unresolved})

def coding_case():
    # Fixed in-memory fixture; never executes supplied arbitrary code.
    baseline='def eligible(amount):\n    return amount < 100\n'
    candidate='def eligible(amount):\n    return 0 <= amount <= 100\n'
    def evaluate(text):
        approved={baseline,candidate}
        if text not in approved:return {'label':'unresolved','reason':'Unknown candidate not executed'}
        namespace={}
        exec(compile(text,'<fixed-teaching-fixture>','exec'),{'__builtins__':{}},namespace)
        f=namespace['eligible']; tests=[(-1,False),(0,True),(100,True),(101,False)]
        checks=[f(x)==expected for x,expected in tests]
        return dict(label='accepted' if all(checks) else 'failed',checks=checks)
    return dict(domain='coding',baseline=evaluate(baseline),candidate=evaluate(candidate),
                unresolved=evaluate('untrusted candidate'))

def research_case():
    # Local evidence fixture: entailment limited to exact supplied statements.
    sources={'policy-2':{'revision':2,'claims':{'eligible_limit':'100 units'}}}
    claims=[{'name':'eligible_limit','value':'100 units','source':'policy-2'},
            {'name':'guaranteed_profit','value':'yes','source':'policy-2'},
            {'name':'new_claim','value':'unknown','source':'missing'}]
    results=[]
    for c in claims:
        source=sources.get(c['source'])
        label=('unresolved' if source is None else
               'accepted' if source['claims'].get(c['name'])==c['value'] else 'failed')
        results.append(dict(**c,label=label))
    return dict(domain='research',claims=results,
                limitation='Exact fixture checks do not establish natural-language entailment')

def main():
    p=Path('results');p.mkdir(exist_ok=True)
    r=[service_case(),coding_case(),research_case()]
    (p/'capstones.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
if __name__=='__main__':main()
