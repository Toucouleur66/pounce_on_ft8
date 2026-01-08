"""
PyInstaller hook for pywinauto
Forces inclusion of all pywinauto modules
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect everything from pywinauto
datas, binaries, hiddenimports = collect_all('pywinauto')

# Also collect comtypes which pywinauto depends on
comtypes_datas, comtypes_binaries, comtypes_hiddenimports = collect_all('comtypes')

datas += comtypes_datas
binaries += comtypes_binaries
hiddenimports += comtypes_hiddenimports

# Add specific imports that might be missed
hiddenimports += [
    'pywinauto.application',
    'pywinauto.timings',
    'pywinauto.controls',
    'pywinauto.base_wrapper',
    'pywinauto.uia_defines',
    'pywinauto.uia_element_info',
    'comtypes.client',
    'comtypes.gen',
]
