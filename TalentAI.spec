# TalentAI.spec — PyInstaller build spec
# Run with: pyinstaller TalentAI.spec
# Output:   dist\TalentAI_App\TalentAI.exe

import os
from PyInstaller.utils.hooks import collect_submodules, collect_all

block_cipher = None

# Root directory of the project
ROOT = os.path.dirname(os.path.abspath(SPEC))

# ─── Validate required assets exist before building ───────────────────────────
frontend_out = os.path.join(ROOT, 'frontend', 'out')
if not os.path.isdir(frontend_out):
    raise FileNotFoundError(
        f"Frontend build not found at: {frontend_out}\n"
        "Run:  cd frontend && npm run build\n"
        "This creates the 'frontend/out' directory required for the exe."
    )

backend_env = os.path.join(ROOT, 'backend', '.env')
if not os.path.isfile(backend_env):
    raise FileNotFoundError(
        f"Backend .env not found at: {backend_env}\n"
        "Copy .env.example to backend/.env and fill in production credentials."
    )

# Collect all resources for reportlab (fonts, encodings, etc.)
rl_datas, rl_binaries, rl_hidden = collect_all('reportlab')

# Build complete list of hidden imports
hidden_imports = [
    # pywebview backend imports (Windows uses pythonnet/EdgeChromium)
    'webview',
    'webview.platforms.winforms',
    'clr',
    'pythonnet',
    # stdlib http server
    'http.server',
    'socketserver',
    'threading',
    # pkg_resources and stdlib dependencies
    'email',
    'email.mime',
    'email.mime.text',
    'email.mime.multipart',
    'xml',
    'xml.etree',
    'xml.etree.ElementTree',
    'pkg_resources',
    'pkg_resources.extern',
    # dotenv (critical for config loading)
    'dotenv',

    # Backend primary dependencies
    'main',
    'uvicorn',
    'fastapi',
    'starlette',
    'sqlalchemy',
    'psycopg2',
    'bcrypt',
    'jwt',
    'pydantic',
    'pydantic_settings',
    'redis',
    'docx',
    'pypdf',
    'requests',
    'urllib3',
    'certifi',
    'multipart',
    'python_multipart',
    'numpy',
    'passlib',
    'passlib.handlers.bcrypt',
    'pgvector',
    'pgvector.sqlalchemy',
    # Uvicorn runtime internals
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    # tkinter for error dialogs
    'tkinter',
    'tkinter.messagebox',
]

# Collect submodules
hidden_imports += collect_submodules('uvicorn')
hidden_imports += collect_submodules('fastapi')
hidden_imports += collect_submodules('starlette')
hidden_imports += collect_submodules('pydantic')
hidden_imports += collect_submodules('pydantic_settings')
hidden_imports += collect_submodules('api')
hidden_imports += collect_submodules('core')
hidden_imports += collect_submodules('models')
hidden_imports += collect_submodules('services')
hidden_imports += rl_hidden

a = Analysis(
    [os.path.join(ROOT, 'TalentAI_App.py')],
    pathex=[ROOT, os.path.join(ROOT, 'backend')],
    binaries=rl_binaries,
    datas=[
        # ──────────────────────────────────────────────────────────────────
        # CRITICAL: Bundle the compiled Next.js static output
        # This MUST be a directory that exists (validated above)
        # ──────────────────────────────────────────────────────────────────
        (frontend_out, os.path.join('frontend', 'out')),
        # Bundle backend source code (excluding storage and test caches)
        (os.path.join(ROOT, 'backend', 'api'), os.path.join('backend', 'api')),
        (os.path.join(ROOT, 'backend', 'core'), os.path.join('backend', 'core')),
        (os.path.join(ROOT, 'backend', 'models'), os.path.join('backend', 'models')),
        (os.path.join(ROOT, 'backend', 'services'), os.path.join('backend', 'services')),
        (os.path.join(ROOT, 'backend', 'alembic'), os.path.join('backend', 'alembic')),
        (os.path.join(ROOT, 'backend', 'alembic.ini'), 'backend'),
        (os.path.join(ROOT, 'backend', 'main.py'), 'backend'),
        # Bundle backend .env (production credentials)
        (backend_env, 'backend'),
        # Bundle root .env as fallback
        (os.path.join(ROOT, '.env'), '.'),
    ] + rl_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest', 'matplotlib', 'pandas', 'scipy', 'torch', 'tensorflow', 'tensorboard'
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TalentAI_App',
)
