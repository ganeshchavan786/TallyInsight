# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Tally Database Loader

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all hidden imports for FastAPI and dependencies
hidden_imports = [
    # Uvicorn
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    
    # FastAPI
    'fastapi',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.staticfiles',
    'fastapi.responses',
    'fastapi.templating',
    'fastapi.security',
    
    # Starlette
    'starlette',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.staticfiles',
    'starlette.responses',
    'starlette.templating',
    'starlette.routing',
    
    # Pydantic
    'pydantic',
    'pydantic_settings',
    'pydantic.fields',
    'pydantic_core',
    
    # Database
    'aiosqlite',
    'sqlite3',
    
    # HTTP
    'httpx',
    'httpx._transports',
    'httpx._transports.default',
    
    # Async
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'sniffio',
    'asyncio',
    
    # YAML/Config
    'yaml',
    'dotenv',
    'python_dotenv',
    
    # Date/Time
    'dateutil',
    'dateutil.relativedelta',
    'dateutil.parser',
    'dateutil.tz',
    
    # XML
    'lxml',
    'lxml.etree',
    'lxml.html',
    
    # Templates
    'jinja2',
    'jinja2.ext',
    
    # Multipart
    'multipart',
    'python_multipart',
    
    # Validation
    'email_validator',
    
    # Logging
    'loguru',
    'loguru._logger',
    
    # WebSockets
    'websockets',
    'websockets.server',
    'websockets.client',
    'websockets.legacy',
    'websockets.legacy.server',
    
    # Scheduler
    'apscheduler',
    'apscheduler.schedulers',
    'apscheduler.schedulers.background',
    'apscheduler.schedulers.asyncio',
    'apscheduler.triggers',
    'apscheduler.triggers.interval',
    'apscheduler.triggers.cron',
    'apscheduler.jobstores',
    'apscheduler.executors',
    
    # Cryptography (for httpx)
    'cryptography',
    'cryptography.hazmat',
    'cryptography.hazmat.primitives',
    
    # Other common dependencies
    'certifi',
    'charset_normalizer',
    'idna',
    'h11',
    'httpcore',
    'typing_extensions',
    'annotated_types',
]

# Data files to include
datas = [
    ('app', 'app'),
    ('static', 'static'),
    ('config.yaml', '.'),
    ('tally-export-config.yaml', '.'),
    ('tally-export-config-incremental.yaml', '.'),
    ('database-structure.sql', '.'),
    ('database-structure-incremental.sql', '.'),
]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TallySync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for GUI mode (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico' if os.path.exists('static/favicon.ico') else None,
)
