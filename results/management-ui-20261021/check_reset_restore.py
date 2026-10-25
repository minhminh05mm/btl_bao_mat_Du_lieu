from contextlib import contextmanager
import json
from lab import operations as ops
from lab.management import profiles, restore_employees_after_reset
from app.db import USERS

original=ops.db
with original() as conn:
    conn.execute('CREATE TEMP TABLE principals (LIKE public.principals INCLUDING ALL)')
    conn.execute('CREATE TEMP TABLE devices (LIKE public.devices INCLUDING ALL)')
    fixture_names=[name for name,_,_ in USERS]
    conn.execute('INSERT INTO principals SELECT * FROM public.principals WHERE username=ANY(%s)',(fixture_names,))
    @contextmanager
    def isolated(url=None):
        yield conn
    ops.db=isolated
    try:
        count=restore_employees_after_reset()
        observed={r['id']:r for r in ops.rows('principals')}
        custom={k:v for k,v in profiles().items() if k not in fixture_names}
        assert count==len(custom)
        for name,profile in custom.items():
            assert all(observed[name][key]==profile[key] for key in ['role','department','active'])
        assert restore_employees_after_reset()==0
        print(json.dumps({'passed':True,'restored_custom_accounts':count,'idempotent':True,'real_tables_changed':False}))
    finally:ops.db=original
