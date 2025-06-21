import pkgutil, importlib

__all__ = []

# 1) expone cada subpaquete (Features, Globals, …)
for _, pkg_name, is_pkg in pkgutil.iter_modules(__path__):
    if is_pkg:
        pkg = importlib.import_module(f"{__name__}.{pkg_name}")
        globals()[pkg_name] = pkg
        __all__.append(pkg_name)

# 2) re-exporta todas las funciones/clases públicas de cada módulo
for _, full_name, is_pkg in pkgutil.walk_packages(__path__, prefix=__name__ + "."):
    if not is_pkg:
        mod = importlib.import_module(full_name)
        public = getattr(mod, "__all__", [n for n in dir(mod) if not n.startswith("_")])
        for name in public:
            if name not in globals():
                globals()[name] = getattr(mod, name)
                __all__.append(name)
