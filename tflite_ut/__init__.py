import os
import re
import glob

mods = []

files = glob.glob(os.path.join(os.path.dirname(__file__), "*.py"))
for f in files:
    if os.path.isfile(f) and not f.endswith('__.py'):
        name = os.path.basename(f)[:-3]
        __import__('%s.%s' %(__package__, name))
        mod = globals()[name]
        if hasattr(mod, 'unit_test'):
            mods.append(mod)

def unit_test(mp):
    errcnt = 0
    for m in mods:
        errcnt += m.unit_test(mp)
    print('-' * 80)
    print('PASS' if errcnt == 0 else 'FAILED: %d' %(errcnt))
    return
