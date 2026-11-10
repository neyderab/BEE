"""Crea las claves VAPID para las notificaciones push.

Cópialas como variables de entorno en Render (o en tu .env). Se crean una
sola vez: si cambian, los celulares que ya activaron los avisos tienen que
volver a activarlos.

    python scripts/generar_claves_push.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.servicios.push import crear_claves  # noqa: E402

claves = crear_claves()
print(f"VAPID_PUBLIC_KEY={claves['publica']}")
print(f"VAPID_PRIVATE_KEY={claves['privada']}")
