# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files


datas = collect_data_files('mediapipe', include_py_files=False)

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='EasyDJ',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['EasyDJ_Logo1.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EasyDJ',
)
info_plist = {
    'CFBundleName': 'EasyDJ',
    'CFBundleDisplayName': 'EasyDJ',
    'CFBundleShortVersionString': '1.0.0',
    'CFBundleVersion': '1',
    # Keep the app in the foreground space; actual always-on-top is handled in code via OpenCV window hint
    'LSBackgroundOnly': False,
    'NSCameraUsageDescription': 'EasyDJ uses the camera for hand gesture control.',
    'NSMicrophoneUsageDescription': 'Allows audio input for future features.',
    'NSHighResolutionCapable': True,
    'LSApplicationCategoryType': 'public.app-category.music',
}
app = BUNDLE(
    coll,
    name='EasyDJ.app',
    icon='EasyDJ_Logo1.icns',
    bundle_identifier='com.hackmit.ai_dj',
    info_plist=info_plist,
)
