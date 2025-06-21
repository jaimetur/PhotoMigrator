import pkgutil, importlib

__all__ = []

for _, modname, is_pkg in pkgutil.iter_modules(__path__):
    if not is_pkg:
        module = importlib.import_module(f"{__name__}.{modname}")
        globals()[modname] = module
        __all__.append(modname)
