import os
import sys
import time
import threading
import logging

from django.apps import AppConfig
from django.conf import settings


logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    cleanup_thread_started = False

    def ready(self):
        # Run only with development server, not during check/migrate/shell.
        if "runserver" not in sys.argv:
            return

        # Prevent duplicate thread because Django runserver uses auto-reloader.
        if os.environ.get("RUN_MAIN") != "true":
            return

        if CoreConfig.cleanup_thread_started:
            return

        CoreConfig.cleanup_thread_started = True

        interval_seconds = getattr(settings, "OTP_CLEANUP_INTERVAL_SECONDS", 10)

        def cleanup_loop():
            while True:
                try:
                    from core.services import cleanup_expired_pending_registrations

                    deleted_count = cleanup_expired_pending_registrations()

                    if deleted_count > 0:
                        logger.info(
                            "Deleted %s expired pending registration account(s).",
                            deleted_count
                        )

                except Exception:
                    logger.exception("Error while cleaning expired pending registrations.")

                time.sleep(interval_seconds)

        thread = threading.Thread(
            target=cleanup_loop,
            daemon=True,
            name="otp-cleanup-thread"
        )
        thread.start()