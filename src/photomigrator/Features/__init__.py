import pkgutil, importlib

__all__ = []

for _, subpkg, is_pkg in pkgutil.iter_modules(__path__):
    if is_pkg:
        pkg = importlib.import_module(f"{__name__}.{subpkg}")
        globals()[subpkg] = pkg
        __all__.append(subpkg)
