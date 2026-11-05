"""Profile construction from preregistered counts. No automatic release thresholds."""
import json
import math
from pathlib import Path
from metrics import lower, gate

def build(registry):
    alpha=registry['alpha']; claims=registry['claims']
    if not 0<alpha<1 or not claims:raise ValueError('Invalid confidence registry')
    ids=[c['id'] for c in claims]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate claim identity')
    k=sum(len(c['groups']) for c in claims)
    if not k:raise ValueError('Empty claim groups')
    a=alpha/k; rows=[]; evidence=True; local_floors_pass=True
    for claim in claims:
        groups=claim['groups'];mode=claim['mode']
        if mode not in ('weighted','minimum'):raise ValueError('Unknown construction')
        if not groups:raise ValueError('Missing required groups')
        if mode=='weighted':
            weights=[g['weight'] for g in groups]
            if any(w<0 or not math.isfinite(w) for w in weights):raise ValueError('Invalid weights')
            if not math.isclose(sum(weights),1,abs_tol=1e-12):raise ValueError('Bad weights')
        bounds=[lower(g['x'],g['n'],a) for g in groups]
        known=all(b is not None for b in bounds)
        evidence=evidence and known
        for g,bound in zip(groups,bounds):
            if 'minimum_required' in g:
                local_floors_pass = local_floors_pass and bound is not None and 100*bound>=g['minimum_required']
        score=(sum(g['weight']*(b or 0) for g,b in zip(groups,bounds))
               if mode=='weighted' else min(b or 0 for b in bounds))
        rows.append(dict(id=claim['id'],score=100*score,evidence_complete=known,
                         groups=[dict(**g,lower=b) for g,b in zip(groups,bounds)],
                         shared_evidence=claim.get('shared_evidence',[])))
    evidence=evidence and registry['required_evidence_complete']
    floors=registry.get('thresholds',{})
    if set(floors)-set(ids):raise ValueError('Unknown threshold claim')
    thresholds_pass=local_floors_pass and all(row['score']>=floors[row['id']] for row in rows if row['id'] in floors)
    # A demonstration with no approved criteria cannot qualify by an empty conjunction.
    criteria_registered=bool(floors) and registry.get('criteria_approved',False)
    status=gate(evidence and criteria_registered,thresholds_pass,registry['critical_events'])
    reasons=[]    # every reason stays listed, whichever one sets the status
    if registry['critical_events']:reasons.append('confirmed hard-gate violation')
    if not evidence:reasons.append('required evidence incomplete')
    if not criteria_registered:reasons.append('no approved release criteria')
    if not thresholds_pass:reasons.append('threshold or floor not met on the available evidence')
    return dict(confidence=1-alpha,constituent_bounds=k,allocated_alpha=a,rows=rows,
                status=status,reasons=reasons,criteria_registered=criteria_registered,
                interpretation=registry['interpretation'])

def illustrative_registry():
    core=[('ARI-O',960,1000),('ARI-P m=5',83,100),('ARI-R',184,200),
          ('ARI-C',299,300),('ARI-S',290,300),('ARI-M',175,200)]
    claims=[dict(id=s,mode='weighted',groups=[dict(family=s,x=x,n=n,weight=1)]) for s,x,n in core]
    claims.append(dict(id='ARI-G',mode='minimum',groups=[dict(family=f'stress-{i}',x=x,n=200)
                                                                     for i,x in enumerate([180,160,150],1)]))
    return dict(alpha=.05,claims=claims,required_evidence_complete=True,critical_events=1,
                thresholds={},criteria_approved=False,
                interpretation='Illustrative counts only; one prohibited post-stop commit blocks release')

if __name__=='__main__':
    out=Path('results');out.mkdir(exist_ok=True)
    registry=illustrative_registry()
    (out/'illustrative_registry.json').write_text(json.dumps(registry,indent=2))
    result=build(registry)
    (out/'illustrative_scorecard.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
