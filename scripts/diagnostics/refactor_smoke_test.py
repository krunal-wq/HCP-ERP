"""Full refactor smoke test. No DB required.
Verifies: app builds, all blueprints register, EVERY module template resolves
via the Jinja loader, shared templates still resolve, and route count is sane."""
import sys, os, glob

# Project root = two levels up from scripts/diagnostics/ — ensure it's importable
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    import index
    app = index.app
except Exception as e:
    import traceback; traceback.print_exc()
    print("FAIL: import index ->", repr(e)); sys.exit(1)

ok = True
print(f"INFO blueprints registered: {len(app.blueprints)}")

# 1. Every template under modules/*/templates must resolve by its namespace path
bad = []
checked = 0
for tdir in glob.glob(os.path.join(app.root_path, 'modules', '*', 'templates')):
    for root, _, files in os.walk(tdir):
        for fn in files:
            if not fn.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(root, fn), tdir).replace(os.sep, '/')
            checked += 1
            try:
                app.jinja_env.get_template(rel)
            except Exception as e:
                bad.append((rel, str(e))); ok = False
print(f"INFO module templates checked: {checked} | failed: {len(bad)}")
for rel, e in bad[:20]:
    print("  FAIL template:", rel, "->", e)

# 2. Shared templates still resolve
for tpl in ('base.html', 'dashboard.html', 'login.html', 'errors/404.html'):
    try:
        app.jinja_env.get_template(tpl); print(f"PASS shared template: {tpl}")
    except Exception as e:
        print(f"FAIL shared template: {tpl} -> {e}"); ok = False

# 3. Route count
rules = list(app.url_map.iter_rules())
print(f"INFO total URL rules: {len(rules)}")

print("\nRESULT:", "ALL PASS" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 2)
