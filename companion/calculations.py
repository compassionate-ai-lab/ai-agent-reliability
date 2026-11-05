"""Reproduce analytical teaching inputs; these are not observed model results."""
import json
import math
from pathlib import Path
from metrics import lower, upper, weighted

def matvec(a,v): return [sum(x*y for x,y in zip(row,v)) for row in a]
from models import spectral_radius, radius_bracket

def radius(a):
    """Point estimate of the spectral radius; the single implementation
    lives in models.radius_bracket (guaranteed enclosure)."""
    return spectral_radius(a)

def stationary(a,b):
    v=[0.0]*len(b)
    for _ in range(1000):
        w=[x+y for x,y in zip(matvec(a,v),b)]
        if max(abs(x-y) for x,y in zip(v,w))<1e-14:return w
        v=w
    raise ValueError('Stationary iteration did not converge')

def main():
    out=Path('results');out.mkdir(exist_ok=True)
    a=[[.2,0,.4],[.3,.2,0],[0,.3,.2]]
    wrong_plan=.97*.03+.03*.70
    wrong_state=wrong_plan*.90+(1-wrong_plan)*.02
    core=[('ARI-O',960,1000),('ARI-P (m=5)',83,100),('ARI-R',184,200),
          ('ARI-C',299,300),('ARI-S',290,300),('ARI-M',175,200),
          ('Stress 1',180,200),('Stress 2',160,200),('Stress 3',150,200)]
    architecture=[('Authority layer',198,200),('Context-memory layer',190,200),
          ('Planning-coordination layer',194,200),('Tools-verification layer',196,200),
          ('Horizontal',185,200),('Vertical',192,200),('Cross',178,200),
          ('ARI-J(A)',174,200),('ARI-L(B)',168,200),('ARI-J(B)',167,200)]
    card=lambda rows:[dict(claim=s,x=x,n=n,lower=lower(x,n,.05/len(rows)))
                      for s,x,n in rows]
    report={
      'provenance':'Analytical calculations on illustrative inputs',
      'lower_96_100':lower(96,100),'lower_960_1000':lower(960,1000),
      'weighted_two_strata':weighted([dict(x=470,n=500,weight=.7),dict(x=170,n=200,weight=.3)]),
      'zero_event_upper_1000':upper(0,1000),
      'zero_event_sample_below_001':math.ceil(math.log(.05)/math.log(.999)),
      'eight_stage_independent':.98**8,
      'common_cause_workers':.92*(1-.1**3),
      'two_verifier_mixture_miss':.5*.2+.5*.2**2,
      'verifier':dict(wrong_plan=wrong_plan,wrong_state=wrong_state,
             correct_accepted=(1-wrong_state)*.99,
             correct_rejected=(1-wrong_state)*.01,
             wrong_detected=wrong_state*.60,wrong_accepted=wrong_state*.40),
      'matrix':a,'radius':radius(a),'double_radius':radius([[2*x for x in r] for r in a]),
      'stationary':stationary(a,[.01]*3),
      'markov_three_steps':.72*(1+.2+.2**2),'markov_eventual':.72/.8,
      'latent_conditional':14/181,'latent_all_missions':14/200,
      'core_card':card(core),'architecture_card':card(architecture),
      'queue':{'lambda_per_hour':10,'mu_per_hour':12,'utilization':10/12,
               'mean_system_minutes':60/(12-10),'mean_queue_minutes':60*10/(12*(12-10))},
      'loss':{'expected':.015*10+.005*100,'cvar99':(.005*100+.005*10)/.01}
    }
    (out/'analytical_results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if 'card' not in k},indent=2))

if __name__=='__main__':main()
