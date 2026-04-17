from pathlib import Path


# Compatibility shim for the AgroDron submodule, which now lives in
# external/cyber_drons but still uses imports under systems.agrodron.*.
_PACKAGE_DIR = Path(__file__).resolve().parent
_SUBMODULE_ROOT = _PACKAGE_DIR.parents[1] / "external" / "cyber_drons"
__path__ = [str(_PACKAGE_DIR), str(_SUBMODULE_ROOT)]
