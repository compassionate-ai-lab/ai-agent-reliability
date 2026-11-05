"""Models behind the worked examples and charts of the book.

Standard library only. Regions between `# [book:name]` and
`# [/book:name]` are printed verbatim as numbered listings, so the code a
reader runs is the code the book shows. Inputs are teaching values.
"""
from collections import namedtuple
from dataclasses import dataclass, field
import hashlib
import json
import math
import sys
from metrics import lower, _tail, upper


# ------------------------------------------------------------- Ch 1
def horizon_success(p, steps):
    """All-of-m success for independent steps (an idealization)."""
    return p ** steps


# ------------------------------------------------------------- Ch 2
# [book:incident]
@dataclass
class IncidentRecord:
    """Five columns that keep cause, path and consequence apart."""
    initiating_condition: str
    first_invalid_state: str
    propagation_path: list
    missed_barriers: list
    consequence: str
    severity: str = "unclassified"
    exposure_unit: str = "mission"

    def controls(self):
        """One prevention or detection point per missed barrier."""
        return [f"strengthen: {b}" for b in self.missed_barriers]
# [/book:incident]


FAILURE_REGISTER = [  # (mode, events per 10k missions, severity 1-5)
    ("draft formatting error", 300, 1), ("stale policy used", 40, 3),
    ("wrong record selected", 12, 4), ("duplicate write", 8, 3),
    ("false completion", 25, 3), ("lost handoff", 30, 2),
    ("post-revocation commit", 1, 5), ("cross-tenant read", 0.5, 5),
]


# ------------------------------------------------------------- Ch 3
# [book:horizon]
def finite_horizon(Q, r, s0, h):
    """R(h) = s0^T (sum_{k<h} Q^k) r for a transient-state model."""
    n = len(Q)
    v = list(s0)                      # s0^T Q^k, starting at k = 0
    total = 0.0
    for _ in range(h):
        total += sum(v[i] * r[i] for i in range(n))
        v = [sum(v[i] * Q[i][j] for i in range(n)) for j in range(n)]
    return total
# [/book:horizon]


def two_step_rho_range(p1, p2):
    """Feasible correlation range for two Bernoulli steps with these marginals.

    The joint success P(both) must lie between the Frechet bounds
    max(0, p1 + p2 - 1) and min(p1, p2); the correlation is limited accordingly.
    """
    sd = math.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    lo, hi = max(0.0, p1 + p2 - 1), min(p1, p2)
    return (lo - p1 * p2) / sd, (hi - p1 * p2) / sd


def two_step_joint(p1, p2, rho):
    """Joint success of two Bernoulli steps with correlation rho.

    Raises ValueError when rho is impossible for the given marginals.
    """
    lo_r, hi_r = two_step_rho_range(p1, p2)
    if not lo_r - 1e-12 <= rho <= hi_r + 1e-12:
        raise ValueError(f"correlation {rho} infeasible for marginals "
                         f"{p1}, {p2}; allowed [{lo_r:.4f}, {hi_r:.4f}]")
    sd = math.sqrt(p1 * (1 - p1) * p2 * (1 - p2))
    return p1 * p2 + rho * sd


def retry_with_cap(p, attempts):
    return 1 - (1 - p) ** attempts


# ------------------------------------------------------------- Ch 4
def cpao_review(attempts, attempt_cost, review_share, review_cost,
                accepted):
    total = attempts * attempt_cost + attempts * review_share * review_cost
    return total / accepted


# ------------------------------------------------------------- Ch 5
# [book:sample_size]
def qualifies(rate, target, n, alpha=0.05):
    """Does the exact lower bound at x = round(rate * n) reach the target?
    L >= target exactly when P(X >= x | p = target) <= alpha."""
    x = round(rate * n)
    if x == 0:
        return False
    if x == n:
        return alpha ** (1 / n) >= target
    return _tail(x, n, target) <= alpha


def required_n(rate, target, alpha=0.05, n_max=20000, stable=False):
    """Smallest n that qualifies, found by checking every n in turn.
    Rounding x makes qualification switch on and off near the answer;
    stable=True returns the smallest n from which every n up to twice
    that size also qualifies. None when the target is out of reach."""
    if rate <= target:
        return None
    for n in range(1, n_max + 1):
        if qualifies(rate, target, n, alpha) and (not stable or all(
                qualifies(rate, target, m, alpha) for m in range(n, 2 * n + 1))):
            return n
    return None
# [/book:sample_size]


# ------------------------------------------------------------- Ch 7
# [book:forecast]
def _paired(forecasts, outcomes):
    q, y = list(forecasts), list(outcomes)
    if len(q) != len(y):
        raise ValueError("forecasts and outcomes differ in length")
    if not q:
        raise ValueError("no forecasts supplied")
    return q, y


def brier(forecasts, outcomes):
    q, y = _paired(forecasts, outcomes)
    return sum((a - b) ** 2 for a, b in zip(q, y)) / len(q)


def coverage_risk(forecasts, outcomes, threshold):
    """Automate cases with forecast >= threshold; refer the rest.
    Risk among automated cases is None (unknown) when none is automated."""
    q, y = _paired(forecasts, outcomes)
    auto = [b for a, b in zip(q, y) if a >= threshold]
    coverage = len(auto) / len(y)
    risk = (len(auto) - sum(auto)) / len(auto) if auto else None
    return coverage, risk
# [/book:forecast]


def synthetic_forecasts(n=2000, seed=7):
    """A calibrated forecaster: outcome ~ Bernoulli(q)."""
    import random
    rng = random.Random(seed)
    qs, ys = [], []
    for _ in range(n):
        q = min(0.995, max(0.30, rng.betavariate(6, 1.6)))
        qs.append(q)
        ys.append(1 if rng.random() < q else 0)
    return qs, ys


# ------------------------------------------------------------- Ch 8
# [book:tail]
def zero_event_n(rate, alpha=0.05):
    """Clean opportunities needed for U(0, n) <= rate."""
    return math.ceil(math.log(alpha) / math.log(1 - rate))


def cvar(dist, level):
    """CVaR for a discrete loss distribution [(prob, loss), ...]."""
    tail, need = 0.0, 1 - level
    for prob, loss in sorted(dist, key=lambda d: -d[1]):
        take = min(prob, need)
        tail += take * loss
        need -= take
        if need <= 1e-15:
            break
    return tail / (1 - level)
# [/book:tail]


# ------------------------------------------------------------- Ch 9
# [book:transitions]
ALLOWED = {
    "planned": {"preparing", "cancelled"},
    "preparing": {"awaiting_approval", "committing", "cancelled"},
    "awaiting_approval": {"committing", "cancelled", "escalated"},
    "committing": {"verifying", "uncertain"},
    "uncertain": {"verifying", "escalated"},
    "verifying": {"accepted", "failed"},
}


def advance(state, target, expected_revision, current_revision):
    """Only listed transitions, and only from the expected revision."""
    if expected_revision != current_revision:
        raise ValueError("stale task revision")
    if target not in ALLOWED.get(state, set()):
        raise ValueError(f"{state} -> {target} is not permitted")
    return target, current_revision + 1
# [/book:transitions]


def reachable_invalid(n_states, allowed_edges):
    """Ordered state pairs that a free loop could take but the
    table forbids."""
    return n_states * (n_states - 1) - allowed_edges


# ------------------------------------------------------------- Ch 10
def expected_duplicates(q_timeout, retries, idempotent):
    """Expected extra effects when each attempt commits and then
    times out with probability q, followed by a blind retry."""
    if idempotent:
        return 0.0
    dup, alive = 0.0, 1.0
    for _ in range(retries):
        alive *= q_timeout        # previous attempt hid a commit
        dup += alive
    return dup


# ------------------------------------------------------------- Ch 11
# [book:progress]
def stalled(history, window=4):
    """True when the last `window` steps changed no accepted
    milestone and repeated an already-seen action."""
    if len(history) < window:
        return False
    recent = history[-window:]
    no_progress = len({h["milestones"] for h in recent}) == 1
    repeats = len({h["action"] for h in recent}) < window
    return no_progress and repeats
# [/book:progress]


def finish_within(p_progress, milestones, budget):
    """P(reach `milestones` successes within `budget` steps)."""
    return sum(math.comb(budget, k) * p_progress ** k
               * (1 - p_progress) ** (budget - k)
               for k in range(milestones, budget + 1))


# ------------------------------------------------------------- Ch 12
def checkpoint_overhead(interval, cost, rate):
    """Fraction of time lost: c/tau + lambda*tau/2 (Young)."""
    return cost / interval + rate * interval / 2


def young_interval(cost, rate):
    return math.sqrt(2 * cost / rate)


# ------------------------------------------------------------- Ch 13
# [book:envelope]
@dataclass(frozen=True)
class SourceEnvelope:
    source: str
    revision: int
    authority: str            # e.g. "approved-policy"
    tenant: str
    valid_from: int
    valid_until: int | None


def eligible(env, *, tenant, now, head_revision, required_authority):
    """Evidence may justify an action only if every check passes."""
    return (env.tenant == tenant
            and env.authority == required_authority
            and env.revision == head_revision
            and env.valid_from <= now
            and (env.valid_until is None or now < env.valid_until))
# [/book:envelope]


def stale_probability(rate_per_day, days):
    return 1 - math.exp(-rate_per_day * days)


# ------------------------------------------------------------- Ch 14
def exposure_record_days(births, keep_days, horizon):
    return sum(min(horizon, b + keep_days) - b if keep_days else horizon - b
               for b in births)


# ------------------------------------------------------------- Ch 15
# [book:scope]
def effective_scope(user, task, tool, credential):
    """An action may use only what every layer of authority allows."""
    return (frozenset(user) & frozenset(task)
            & frozenset(tool) & frozenset(credential))


def permitted(action, scope, revoked=frozenset()):
    return action in scope and action not in revoked
# [/book:scope]


def filter_tradeoff(threshold):
    """Synthetic logistic detector: attack-pass and legitimate-block
    rates as the score threshold moves (illustration only)."""
    attack_pass = 1 / (1 + math.exp(12 * (threshold - 0.35)))
    legit_block = 1 / (1 + math.exp(-12 * (threshold - 0.75)))
    return attack_pass, legit_block


# ------------------------------------------------------------- Ch 16 helpers
EPS = sys.float_info.epsilon
UNKNOWN = 'unknown'          # an edge that exists but was not measured


def check_matrix(A):
    """Square, nonempty, finite, nonnegative real matrix (as floats)."""
    if not isinstance(A, (list, tuple)) or not A:
        raise ValueError('matrix must be a nonempty list of rows')
    n = len(A)
    out = []
    for row in A:
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError('matrix must be square')
        r = []
        for a in row:
            if isinstance(a, bool) or not isinstance(a, (int, float)):
                raise ValueError('entries must be real numbers')
            if not math.isfinite(a) or a < 0:
                raise ValueError('entries must be finite and nonnegative')
            r.append(float(a))
        out.append(r)
    return out


def check_counts(counts):
    """Square table of (propagated, injections), None or UNKNOWN."""
    if not isinstance(counts, (list, tuple)) or not counts:
        raise ValueError('counts must be a nonempty square table')
    n = len(counts)
    for row in counts:
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError('counts must be square')
        for c in row:
            if c is None or c == UNKNOWN:
                continue
            if (not isinstance(c, (list, tuple)) or len(c) != 2
                    or any(isinstance(v, bool) or not isinstance(v, int)
                           for v in c)
                    or not 0 <= c[0] <= c[1] or c[1] == 0):
                raise ValueError(f'invalid edge count {c!r}')
    return n


def strong_blocks(A):
    """Strongly connected components (mutual reachability)."""
    n = len(A)
    reach = [[i == j or A[i][j] > 0 for j in range(n)] for i in range(n)]
    for k in range(n):
        for i in range(n):
            if reach[i][k]:
                for j in range(n):
                    if reach[k][j]:
                        reach[i][j] = True
    seen, blocks = set(), []
    for i in range(n):
        if i not in seen:
            b = [j for j in range(n) if reach[i][j] and reach[j][i]]
            seen.update(b)
            blocks.append(b)
    return blocks


# ------------------------------------------------------------- Ch 16
# [book:radius]
Bracket = namedtuple('Bracket', 'lower upper converged')


def radius_bracket(A, tol=1e-12, max_iter=200_000):
    """Guaranteed enclosure lower <= rho(A) <= upper, A nonnegative.

    rho(A) is the largest radius of A's strongly connected blocks, so a
    reducible matrix is split first. Each block is shifted to B = A + I,
    which is primitive, and for any x > 0 the Collatz-Wielandt ratios
    satisfy min (Bx)_i/x_i <= rho(B) <= max (Bx)_i/x_i. Power steps tighten
    both sides; if they do not meet, the enclosure is still valid but
    `converged` is False."""
    A = check_matrix(A)
    lo = hi = 0.0
    converged = True
    for block in strong_blocks(A):
        if len(block) == 1 and A[block[0]][block[0]] == 0:
            continue                      # acyclic node: radius 0
        B = [[A[i][j] + (i == j) for j in block] for i in block]
        x = [1.0] * len(block)
        for _ in range(max_iter):
            y = [math.fsum(b * v for b, v in zip(row, x)) for row in B]
            ratios = [yi / xi for yi, xi in zip(y, x)]
            b_lo, b_hi = min(ratios) - 1.0, max(ratios) - 1.0
            if b_hi - b_lo <= tol * max(1.0, b_hi):
                break
            top = max(y)
            x = [yi / top for yi in y]
        else:
            converged = False
        lo, hi = max(lo, b_lo), max(hi, b_hi)
    if hi == 0.0:
        return Bracket(0.0, 0.0, True)             # no cycle at all
    slack = 16 * len(A) * EPS * (1.0 + hi)          # floating-point rounding
    return Bracket(max(0.0, lo - slack), hi + slack, converged)


def decay_verdict(bracket, tol=1e-9):
    """'decays' only if the upper enclosure is below one."""
    if bracket.upper < 1.0 - tol:
        return 'decays'
    if bracket.lower > 1.0 + tol:
        return 'grows'
    return 'inconclusive'


def spectral_radius(A):
    """Point estimate (midpoint of the enclosure); never a bound."""
    b = radius_bracket(A)
    if not b.converged:
        raise ArithmeticError('radius not resolved; use radius_bracket')
    return (b.lower + b.upper) / 2


def upper_matrix(counts, alpha=0.05):
    """Simultaneous exact upper bounds for measured Bernoulli edges.
    None = declared structural zero; UNKNOWN = unmeasured edge, bounded
    by 1 (no evidence). Alpha is split over the measured edges."""
    n = check_counts(counts)
    measured = [(i, j) for i in range(n) for j in range(n)
                if counts[i][j] not in (None, UNKNOWN)]
    a = alpha / max(1, len(measured))
    U = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            c = counts[i][j]
            if c == UNKNOWN:
                U[i][j] = 1.0
            elif c is not None:
                U[i][j] = upper(c[0], c[1], a)
    return U


def radius_upper(counts, alpha=0.05):
    """Valid upper enclosure of rho for the simultaneous bound matrix."""
    return radius_bracket(upper_matrix(counts, alpha)).upper
# [/book:radius]


def propagation_verdict(counts, alpha=0.05):
    """Release wording for a measured propagation graph."""
    return decay_verdict(radius_bracket(upper_matrix(counts, alpha)))


def joint_interval(ps):
    return max(0.0, 1 - sum(1 - p for p in ps)), min(ps)


def redundant_miss(p, beta):
    return beta * p + (1 - beta) * p * p


# ------------------------------------------------------------- Ch 17
# [book:evaluator]
def observed_positive(p, sens, spec):
    return sens * p + (1 - spec) * (1 - p)


def corrected_rate(observed, sens, spec):
    """Rogan-Gladen correction; valid only if sens + spec > 1."""
    if sens + spec <= 1:
        raise ValueError("evaluator carries no information")
    return min(1.0, max(0.0, (observed + spec - 1) / (sens + spec - 1)))
# [/book:evaluator]


# ------------------------------------------------------------- Ch 19
# [book:mcnemar]
def mcnemar_exact(new_only, old_only):
    """Two-sided exact test on discordant pairs."""
    n, k = new_only + old_only, min(new_only, old_only)
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)
# [/book:mcnemar]


def paired_power(p_new_only, p_old_only, n, alpha=0.05, sims=None):
    """Exact power of the McNemar test for n paired tasks."""
    pd = p_new_only + p_old_only
    if pd == 0:
        return 0.0
    share = p_new_only / pd
    power = 0.0
    for d in range(n + 1):
        pdisc = math.comb(n, d) * pd ** d * (1 - pd) ** (n - d)
        if pdisc < 1e-12:
            continue
        for b in range(d + 1):
            if mcnemar_exact(b, d - b) <= alpha and b > d - b:
                power += pdisc * math.comb(d, b) * share ** b \
                    * (1 - share) ** (d - b)
    return power


# ------------------------------------------------------------- Ch 20
# [book:manifest]
def manifest(files):
    """Content hashes that let another team prove they ran the same
    tasks, code and evaluator."""
    entries = {name: hashlib.sha256(data).hexdigest()
               for name, data in sorted(files.items())}
    root = hashlib.sha256(json.dumps(entries, sort_keys=True)
                          .encode()).hexdigest()
    return {"files": entries, "root": root}
# [/book:manifest]


# ------------------------------------------------------------- Ch 21
# [book:event]
@dataclass(frozen=True)
class MissionEvent:
    mission: str
    seq: int
    kind: str                   # "tool_call", "commit", "verify_state", ...
    agent: str
    layer: str
    versions: dict = field(default_factory=dict)
    parent: int | None = None   # seq of the causing event
    operation: str | None = None  # operation identity the event concerns
    passed: bool | None = None    # outcome of a verification event


def false_completion(events):
    """Completion claims with no later passing verification of the
    same mission and operation. Returns the unsupported claims."""
    verified = [e for e in events if e.kind == "verify_state" and e.passed]
    return [c for c in events if c.kind == "claim_complete" and not any(
        v.mission == c.mission and v.operation == c.operation and v.seq > c.seq
        for v in verified)]
# [/book:event]


# ------------------------------------------------------------- Ch 22
# [book:slo]
def burn_rate(failures, missions, target):
    return (failures / missions) / (1 - target)


def ewma(values, lam, z0):
    z, out = z0, []
    for y in values:
        z = lam * y + (1 - lam) * z
        out.append(z)
    return out
# [/book:slo]


def standardized(rates, weights):
    return sum(rates[k] * weights[k] for k in rates)


# ------------------------------------------------------------- Ch 23
def canary_n(p_fail_new, p_detect=0.95):
    """Missions needed to see at least one failure with p_detect."""
    return math.ceil(math.log(1 - p_detect) / math.log(1 - p_fail_new))


# ------------------------------------------------------------- Ch 25
def mm1(lam, mu):
    rho = lam / mu
    return {"utilization": rho, "W_min": 60 / (mu - lam),
            "Wq_min": 60 * lam / (mu * (mu - lam))}


# ------------------------------------------------------------- Ch 26
# [book:floors]
def subgroup_check(results, floors, alpha=0.05):
    """Every registered subgroup must clear its own floor; an overall
    rate cannot compensate for one that does not."""
    a = alpha / len(results)
    report = {}
    for group, (x, n) in results.items():
        lb = lower(x, n, a) if n else None
        report[group] = {"rate": x / n if n else None, "lower": lb,
                         "passes": lb is not None and lb >= floors[group]}
    return report
# [/book:floors]


# ------------------------------------------------------------- Ch 29
# [book:value]
def incremental_value(N, p0, p1, V, c0, c1, f0=0, f1=0, F=0, I=0):
    """Delta V = N[(p1-p0)V - (c1-c0) + (f0-f1)F] - I."""
    return N * ((p1 - p0) * V - (c1 - c0) + (f0 - f1) * F) - I
# [/book:value]


# ------------------------------------------------------------- Ch 31
def debt_queue(weeks, arrivals, capacity):
    """Total age (item-weeks) of unresolved reliability debt."""
    queue, series = [], []
    for w in range(weeks):
        queue += [w] * arrivals
        queue = queue[min(capacity, len(queue)):]
        series.append(sum(w - b for b in queue))
    return series


# ------------------------------------------------------------- Ch 32
# [book:envelope_set]
def supported(envelope, evidence, gates, criteria):
    """e is in A_v only with adequate evidence, passing criteria and
    every hard gate: A_v = {e : E_v(e) P_v(e) G_v(e) = 1}."""
    return bool(evidence.get(envelope) and criteria.get(envelope)
                and gates.get(envelope))
# [/book:envelope_set]


# ------------------------------------------------------------- V7 additions
def min_budget(p_progress, milestones, target, b_max=10000):
    """Smallest step budget whose completion probability reaches the target."""
    b = milestones
    while b <= b_max:
        if finish_within(p_progress, milestones, b) >= target:
            return b
        b += 1
    return None


def budget_consumed(burn, window_hours, period_hours):
    """Fraction of a period's error budget consumed by one window at a burn rate."""
    return burn * window_hours / period_hours


def sojourn_exceeds(lam, mu, t):
    """M/M/1: probability that a case spends longer than t in the system."""
    if lam >= mu:
        raise ValueError("unstable queue: arrivals must be below service rate")
    return math.exp(-(mu - lam) * t)


def affected_missions(rate_per_hour, detect_minutes, contain_minutes):
    """Expected missions started between a fault's onset and its containment."""
    return rate_per_hour * (detect_minutes + contain_minutes) / 60


def _binom_pmf(n, p):
    out, q = [], 1 - p
    for k in range(n + 1):
        out.append(math.comb(n, k) * p ** k * q ** (n - k))
    return out


def reproduction_gap(p, n, points):
    """Probability that two independent runs of n tasks at true rate p
    differ in observed acceptance by at least `points` percentage points."""
    f = _binom_pmf(n, p)
    need = points / 100 * n - 1e-9
    return sum(f[i] * f[j] for i in range(n + 1) for j in range(n + 1)
               if abs(i - j) >= need)


def reconstructed_rate(reported_accepted, attempts, human_repaired=0, excluded=0):
    """Autonomous verified acceptance once repairs and exclusions are restored."""
    return (reported_accepted - human_repaired) / (attempts + excluded)


def labour_margin(price, minutes, hourly_cost):
    """Revenue per accepted task left after specialist labour."""
    return price - minutes / 60 * hourly_cost


def break_even_acceptance(attempt_cost, review_share, review_cost, manual_cost):
    """Acceptance rate at which automated CPAO equals the manual cost."""
    return (attempt_cost + review_share * review_cost) / manual_cost
# [/v7]


def radius_sensitivity(A, delta=0.01):
    """Drop in spectral radius when each nonzero edge is reduced by delta."""
    base = spectral_radius(A); out = {}
    for i, row in enumerate(A):
        for j, a in enumerate(row):
            if a > 0:
                B = [r[:] for r in A]; B[i][j] = max(0.0, a - delta)
                out[(i, j)] = base - spectral_radius(B)
    return out
