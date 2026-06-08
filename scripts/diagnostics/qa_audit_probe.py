"""
QA audit probe — empirical auth-coverage + 500-crash smoke test.
Read-only: skips any endpoint whose name/path suggests a mutation/side effect.
"""
import sys, os, re, traceback
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import logging
logging.disable(logging.CRITICAL)

import index
from models import db, User

app = index.app
app.config['WTF_CSRF_ENABLED'] = False
app.testing = True
app.config['PROPAGATE_EXCEPTIONS'] = False  # let error handlers/500 render so we see status

# Endpoints that mutate state or have side effects -> skip in smoke test
DANGER = re.compile(r'(setup|seed|fix[_-]|reset|migrate|sync|clean|delete|remove|destroy|purge|'
                    r'logout|approve|reject|restore|send|mail|whatsapp|export|import|upload|'
                    r'finalize|finalise|dispatch|cancel|generate|create|add|edit|update|save|'
                    r'login|salary|qr-scan|kiosk|deactivate|activate)', re.I)

def fill_path(rule):
    """Build a concrete URL from a rule, filling converters with dummy values."""
    path = rule.rule
    for arg in rule.arguments:
        conv = rule._converters.get(arg) if hasattr(rule, '_converters') else None
        # Use 1 for everything; works for int and string converters
        path = re.sub(r'<[^:>]+:%s>' % re.escape(arg), '1', path)
        path = re.sub(r'<%s>' % re.escape(arg), '1', path)
        path = re.sub(r'<[^:>]+:%s\??>' % re.escape(arg), '1', path)
    # any leftover converters
    path = re.sub(r'<[^>]+>', '1', path)
    return path

rules = [r for r in app.url_map.iter_rules() if 'GET' in (r.methods or set()) and r.endpoint != 'static']

public_200 = []   # reachable WITHOUT auth and returns 200 -> potential auth gap
errors_anon = []
errors_auth = []
ok_auth = 0
skipped = 0

# ---------- Phase A: unauthenticated ----------
with app.test_client() as c:
    for r in rules:
        url = fill_path(r)
        try:
            resp = c.get(url, follow_redirects=False)
            sc = resp.status_code
            if sc == 200:
                public_200.append((r.endpoint, url))
            elif sc == 500:
                errors_anon.append((r.endpoint, url, 500, ''))
        except Exception as e:
            errors_anon.append((r.endpoint, url, 'EXC', repr(e)[:200]))

# ---------- Phase B: authenticated as admin, read-only GETs ----------
with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    admin_id = admin.id if admin else None

if admin_id:
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['_user_id'] = str(admin_id)
            sess['_fresh'] = True
        for r in rules:
            if DANGER.search(r.endpoint) or DANGER.search(r.rule):
                skipped += 1
                continue
            url = fill_path(r)
            try:
                resp = c.get(url, follow_redirects=False)
                sc = resp.status_code
                if sc == 500:
                    body = resp.get_data(as_text=True)
                    m = re.search(r'(\w+Error|\w+Exception)[^<\n]{0,160}', body)
                    errors_auth.append((r.endpoint, url, sc, m.group(0)[:160] if m else ''))
                else:
                    ok_auth += 1
            except Exception as e:
                tb = traceback.format_exc().strip().splitlines()
                errors_auth.append((r.endpoint, url, 'EXC', tb[-1][:200] if tb else repr(e)[:200]))

print("="*70)
print("AUTH GAP: GET routes returning 200 with NO authentication (%d):" % len(public_200))
for ep, url in sorted(public_200):
    print(f"   [PUBLIC] {ep:45s} {url}")

print("\n" + "="*70)
print("500 / EXCEPTIONS while UNAUTHENTICATED (%d):" % len(errors_anon))
for ep, url, sc, msg in errors_anon[:60]:
    print(f"   [{sc}] {ep:40s} {url}  {msg}")

print("\n" + "="*70)
print("500 / EXCEPTIONS while AUTH as admin (read-only GETs) (%d of %d tested, %d ok, %d skipped):"
      % (len(errors_auth), len(rules)-skipped, ok_auth, skipped))
for ep, url, sc, msg in sorted(errors_auth):
    print(f"   [{sc}] {ep:40s} {url}\n          -> {msg}")
print("DONE_PROBE")
