import importlib, traceback

importlib.invalidate_caches()
try:
    m = importlib.import_module('api.auth')
    print('IMPORT_OK', hasattr(m, 'router'))
    print('router:', getattr(m, 'router', None))
except Exception:
    traceback.print_exc()
