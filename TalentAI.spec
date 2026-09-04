# TalentAI.spec — PyInstaller build spec
# Run with: pyinstaller TalentAI.spec
# Output:   dist\TalentAI\TalentAI.exe  (folder mode, ~30-40MB)
#   OR      dist\TalentAI.exe            (onefile mode, ~60-80MB, slower startup)

import os
block_cipher = None

# Root directory of the project
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'TalentAI_App.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        # Bundle the entire compiled Next.js output
        (os.path.join(ROOT, 'frontend', 'out'), 'frontend/out'),
    ],
    hiddenimports=[
        # pywebview backend imports (Windows uses pythonnet/EdgeChromium)
        'webview',
        'webview.platforms.winforms',
        'clr',
        'pythonnet',
        # stdlib http server
        'http.server',
        'socketserver',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude things we do NOT need in the desktop app
        'pytest', 'numpy', 'pandas', 'scipy', 'matplotlib',
        'sqlalchemy', 'psycopg2', 'fastapi', 'uvicorn',
        'pydantic', 'requests', 'email', 'xml',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TalentAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # No black terminal console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='frontend/public/favicon.ico',  # Uncomment if you have an .ico file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TalentAI',
)
