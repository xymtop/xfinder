# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/xfinder/app.py'],
    pathex=[],
    binaries=[],
    datas=[('src/xfinder', 'xfinder'), ('pyproject.toml', '.')],
    hiddenimports=['xfinder', 'xfinder.app', 'xfinder.sdk', 'xfinder.indexer', 'xfinder.searcher', 'xfinder.config'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='XFinder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src/xfinder/resource/logo.icns'],
)
app = BUNDLE(
    exe,
    name='XFinder.app',
    icon='src/xfinder/resource/logo.icns',
    bundle_identifier='com.xfinder',
)
