"""Keep a claimed job lease fresh without sharing a transaction across threads."""

from contextlib import contextmanager
from datetime import timedelta
import logging, threading
import sqlalchemy as sa
from services.api import store


@contextmanager
def heartbeat(job, interval=10):
    stop = threading.Event()

    def pulse():
        while not stop.wait(interval):
            try:
                with store.engine.begin() as conn:
                    conn.execute(sa.text("SET LOCAL lock_timeout = '1s'"))
                    conn.execute(
                        store.jobs.update()
                        .where(
                            store.jobs.c.tenant_id == job["tenant_id"],
                            store.jobs.c.id == job["id"],
                            store.jobs.c.state == "running",
                            store.jobs.c.attempts == job["attempts"] + 1,
                        )
                        .values(lease_until=store.now() + timedelta(seconds=90))
                    )
            except Exception as error:
                logging.warning(
                    "job heartbeat failed: job=%s type=%s",
                    job["id"],
                    type(error).__name__,
                )

    thread = threading.Thread(target=pulse, daemon=True, name="allexport-job-heartbeat")
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=2)
