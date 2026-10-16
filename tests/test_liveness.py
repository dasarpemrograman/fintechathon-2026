from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import json, tempfile, unittest
from services.worker import liveness


class WorkerLivenessTests(unittest.TestCase):
    def test_missing_current_and_stale_worker_are_distinct(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(liveness, "path", return_value=Path(folder) / "worker.json"),
        ):
            self.assertFalse(liveness.ready())
            liveness.pulse()
            self.assertTrue(liveness.ready())
            target = liveness.path()
            target.write_text(
                json.dumps(
                    {
                        "mode": liveness.settings.mode,
                        "at": (
                            datetime.now(timezone.utc) - timedelta(seconds=30)
                        ).isoformat(),
                    }
                )
            )
            self.assertFalse(liveness.ready())
