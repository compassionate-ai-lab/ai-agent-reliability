"""Fixed-sample exact one-sided bounds. Python standard library only."""
import math

def _validate(x, n, alpha):
    if (not isinstance(n, int) or not isinstance(x, int)
            or isinstance(x, bool) or isinstance(n, bool)
            or n < 0 or x < 0 or x > n or not 0 < alpha < 1):
        raise ValueError("Require integer 0 <= x <= n and 0 < alpha < 1")

def _tail(x, n, p):
    if p <= 0: return float(x == 0)
    if p >= 1: return 1.0
    logs = [math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)
            + k*math.log(p)+(n-k)*math.log1p(-p)
            for k in range(x, n+1)]
    m = max(logs)
    return min(1.0, math.exp(m)*math.fsum(math.exp(v-m) for v in logs))

# [book:lower]
def lower(x, n, alpha=.05):
    _validate(x, n, alpha)
    if n == 0: return None
    if x == 0: return 0.0
    if x == n: return alpha**(1/n)
    lo, hi = 0.0, 1.0
    for _ in range(64):
        mid = (lo+hi)/2
        if _tail(x, n, mid) < alpha: lo = mid
        else: hi = mid
    return (lo+hi)/2

# [/book:lower]

def upper(x, n, alpha=.05):
    _validate(x, n, alpha)
    if n == 0: return None
    return 1-lower(n-x, n, alpha)

# [book:weighted]
def weighted(groups, alpha=.05):
    """Each group: {x,n,weight}; equal alpha allocation, no dropped groups."""
    if not groups: raise ValueError("Empty registry")
    weights = [g['weight'] for g in groups]
    if any(w < 0 or not math.isfinite(w) for w in weights):
        raise ValueError("Invalid weights")
    if not math.isclose(sum(weights), 1.0, abs_tol=1e-12):
        raise ValueError("Weights must sum to one")
    bounds = [lower(g['x'],g['n'],alpha/len(groups)) for g in groups]
    return {'qualified_evidence':all(b is not None for b in bounds),
            'lower_floor':sum(g['weight']*(b or 0)
                              for g,b in zip(groups,bounds)),
            'bounds':bounds}

def gate(evidence_complete, thresholds_pass, critical_events):
    if critical_events: return 'Criteria not met'
    if not evidence_complete: return 'Insufficient evidence'
    return 'Qualified within the stated envelope' if thresholds_pass else 'Criteria not met'

# [/book:weighted]

def repeat_block(values):
    if not values or any(v not in (0,1) for v in values):
        raise ValueError("A repeat block requires registered binary results")
    return int(all(values))

def cpao(costs, accepted):
    if accepted < 0 or any(c < 0 for c in costs): raise ValueError("Negative inputs")
    return sum(costs)/accepted if accepted else None
