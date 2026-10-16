"""Start the independent database-backed worker."""

import logging, time
from services.worker.jobs import run_once
from packages.adapters.calendar import deliver_once

logging.basicConfig(level=logging.INFO)
from services.worker.liveness import start

start()
while True:
    try:
        if run_once() is None and deliver_once() is None:
            time.sleep(0.5)
    except Exception as error:
        logging.error("worker failed: %s", type(error).__name__)
        time.sleep(1)
