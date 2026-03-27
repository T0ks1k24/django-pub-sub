from __future__ import annotations
import sys
from pathlib import Path
from django.conf import settings

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if not settings.configured:
    settings.configure(...)

import django
django.setup()

from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)



from __future__ import annotations

import sys
from pathlib import Path

from django.conf import settings

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-secret-key",
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "ecp_lib",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        USE_TZ=True,
    )






