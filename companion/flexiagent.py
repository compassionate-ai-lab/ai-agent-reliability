"""Offline service simulator. No network, credentials, or real user records."""
import hashlib
import json
import sqlite3

class Rejected(Exception): pass
class UncertainCommit(Exception): pass

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
                         separators=(',',':')).encode()).hexdigest()

class Service:
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS records(
          tenant TEXT, rid TEXT, address TEXT, revision INTEGER,
          writes INTEGER, PRIMARY KEY(tenant,rid));
        CREATE TABLE IF NOT EXISTS authority(
          mission TEXT PRIMARY KEY, tenant TEXT, rid TEXT,
          revision INTEGER, active INTEGER);
        CREATE TABLE IF NOT EXISTS operations(
          op TEXT PRIMARY KEY, fingerprint TEXT, receipt TEXT);
        CREATE TABLE IF NOT EXISTS policy(
          singleton INTEGER PRIMARY KEY, revision INTEGER);
        INSERT OR IGNORE INTO policy VALUES(1,1);
        CREATE TABLE IF NOT EXISTS checkpoints(
          mission TEXT PRIMARY KEY, payload TEXT, checksum TEXT);
        CREATE TABLE IF NOT EXISTS memory(
          tenant TEXT, name TEXT, value TEXT, revision INTEGER,
          active INTEGER, PRIMARY KEY(tenant,name));
        ''')
        self.events = []

    def seed(self, mission='m', tenant='t', rid='r'):
        self.db.execute('INSERT INTO records VALUES(?,?,?,?,?)',
                        (tenant,rid,'old',1,0))
        self.db.execute('INSERT INTO authority VALUES(?,?,?,?,?)',
                        (mission,tenant,rid,1,1))

    def event(self, kind, **fields):
        self.events.append({'seq':len(self.events)+1,'event':kind,**fields})

    def record(self,tenant='t',rid='r'):
        row=self.db.execute('SELECT * FROM records WHERE tenant=? AND rid=?',
                            (tenant,rid)).fetchone()
        return dict(row) if row else None

    def revoke(self, mission='m'):
        self.db.execute('UPDATE authority SET revision=revision+1,active=0 WHERE mission=?',
                        (mission,))
        self.event('authority_revoked',mission=mission)

    def policy_revision(self):
        return self.db.execute('SELECT revision FROM policy').fetchone()[0]

    def advance_policy(self):
        self.db.execute('UPDATE policy SET revision=revision+1')

    def proposal(self,mission='m',tenant='t',rid='r',address='new',op='op-1'):
        auth=self.db.execute('SELECT * FROM authority WHERE mission=?',(mission,)).fetchone()
        rec=self.record(tenant,rid)
        if auth is None or rec is None: raise Rejected('Unknown scope')
        return dict(mission=mission,tenant=tenant,rid=rid,address=address,
                    op=op,expected_revision=rec['revision'],
                    authority_revision=auth['revision'],
                    policy_revision=self.policy_revision())

    def reconcile(self, proposal):
        row=self.db.execute('SELECT * FROM operations WHERE op=?',
                            (proposal['op'],)).fetchone()
        if not row: return None
        if row['fingerprint'] != digest(proposal):
            raise Rejected('Operation identity reused with different payload')
        return json.loads(row['receipt'])

    def commit(self, p, fault=None):
        if not isinstance(p,dict) or set(p) != {'mission','tenant','rid','address','op','expected_revision',
                      'authority_revision','policy_revision'}:
            raise Rejected('Invalid proposal schema')
        for field in ('mission','tenant','rid','address','op'):
            if not isinstance(p[field],str) or not p[field].strip() or len(p[field])>1000:
                raise Rejected('Invalid text field')
        for field in ('expected_revision','authority_revision','policy_revision'):
            if not isinstance(p[field],int) or isinstance(p[field],bool) or p[field]<1:
                raise Rejected('Invalid revision field')
        # [book:commit]
        self.db.execute('BEGIN IMMEDIATE')
        try:
            prior=self.reconcile(p)
            if prior is not None:
                self.db.execute('COMMIT')
                self.event('receipt_replayed',mission=p['mission'],op=p['op'])
                return prior
            auth=self.db.execute('SELECT * FROM authority WHERE mission=?',
                                 (p['mission'],)).fetchone()
            if (not auth or not auth['active']
                or auth['revision'] != p['authority_revision']
                or auth['tenant'] != p['tenant'] or auth['rid'] != p['rid']):
                raise Rejected('Current authority does not permit effect')
            if self.policy_revision() != p['policy_revision']:
                raise Rejected('Policy changed')
            cur=self.db.execute('''UPDATE records SET address=?, revision=revision+1,
              writes=writes+1 WHERE tenant=? AND rid=? AND revision=?''',
              (p['address'],p['tenant'],p['rid'],p['expected_revision']))
            if cur.rowcount != 1: raise Rejected('Record conflict')
            receipt=dict(op=p['op'],mission=p['mission'],tenant=p['tenant'],
                         rid=p['rid'],address=p['address'],
                         revision=p['expected_revision']+1)
            self.db.execute('INSERT INTO operations VALUES(?,?,?)',
                            (p['op'],digest(p),json.dumps(receipt,sort_keys=True)))
            self.db.execute('COMMIT')
        except Exception:
            if self.db.in_transaction: self.db.execute('ROLLBACK')
            raise
        # [/book:commit]
        self.event('committed',mission=p['mission'],op=p['op'])
        if fault == 'timeout_after_commit':
            self.event('fault_delivered',fault_type='timeout_after_commit')
            raise UncertainCommit('Receipt lost after durable commit')
        return receipt

    def checkpoint(self,mission,payload):
        text=json.dumps(payload,sort_keys=True)
        self.db.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?,?)',
                        (mission,text,digest(payload)))

    def restore(self,mission):
        row=self.db.execute('SELECT * FROM checkpoints WHERE mission=?',(mission,)).fetchone()
        if not row: raise Rejected('Missing checkpoint')
        try:payload=json.loads(row['payload'])
        except (ValueError,TypeError) as exc:raise Rejected('Malformed checkpoint') from exc
        if digest(payload) != row['checksum']: raise Rejected('Corrupt checkpoint')
        return payload

    def remember(self,tenant,name,value):
        self.db.execute('''INSERT INTO memory VALUES(?,?,?,1,1)
          ON CONFLICT(tenant,name) DO UPDATE SET value=excluded.value,
          revision=memory.revision+1,active=1''',(tenant,name,value))

    def recall(self,tenant,name):
        row=self.db.execute('SELECT value FROM memory WHERE tenant=? AND name=? AND active=1',
                            (tenant,name)).fetchone()
        return row[0] if row else None

    def forget(self,tenant,name):
        self.db.execute('DELETE FROM memory WHERE tenant=? AND name=?',(tenant,name))

    def close(self): self.db.close()

# [book:execute]
def execute(service,p,fault=None):
    """Bounded execute-reconcile-verify path; does not invent new permission."""
    try:
        receipt=service.commit(p,fault=fault)
    except UncertainCommit:
        receipt=service.reconcile(p)
        if receipt is None: raise Rejected('Unresolved external outcome')
    row=service.record(p['tenant'],p['rid'])
    if row['address'] != p['address'] or row['revision'] != receipt['revision']:
        raise Rejected('Final-state verification failed')
    return receipt

# [/book:execute]
