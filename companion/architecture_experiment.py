"""Seeded synthetic propagation experiment, separate from live-agent claims."""
import json
import random
from pathlib import Path
from metrics import upper
from calculations import radius
from models import radius_bracket, decay_verdict

def campaign(seed=114,trials=1000):
    rng=random.Random(seed)
    registered=[(0,0,.2),(1,0,.3),(1,1,.2),(2,1,.3),(2,2,.2),(0,2,.4)]
    counts=[];matrix=[[0.0]*3 for _ in range(3)];bounded=[[0.0]*3 for _ in range(3)]
    for target,source,p in registered:
        x=sum(rng.random()<p for _ in range(trials))
        matrix[target][source]=x/trials
        bounded[target][source]=upper(x,trials,.05/len(registered))
        counts.append(dict(source=source,target=target,confirmed_injections=trials,
                           propagated=x,point=x/trials,upper=bounded[target][source]))
    # Structural zeros are part of the teaching graph, not untested real-world paths.
    return dict(provenance='Seeded Bernoulli teaching generator; probabilities chosen as inputs',
                seed=seed,edges=counts,matrix=matrix,upper_matrix=bounded,
                estimated_radius=radius(matrix),upper_radius=radius_bracket(bounded).upper,
                verdict=decay_verdict(radius_bracket(bounded)),
                limitation='Coverage conditional on registered Bernoulli edges and correct structural zeros')

if __name__=='__main__':
    out=Path('results');out.mkdir(exist_ok=True)
    r=campaign();(out/'propagation_campaign.json').write_text(json.dumps(r,indent=2))
    print(json.dumps(r,indent=2))
