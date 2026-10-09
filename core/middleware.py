from django.core.cache import cache

from orders.services import release_expired_reservations

HOUSEKEEPING_CACHE_KEY = "housekeeping:last_run"
HOUSEKEEPING_INTERVAL = 120  # segundos


def housekeeping_middleware(get_response):
    """Libera reservas de estoque expiradas periodicamente, em qualquer requisição."""

    def middleware(request):
        if cache.add(HOUSEKEEPING_CACHE_KEY, 1, HOUSEKEEPING_INTERVAL):
            try:
                release_expired_reservations()
            except Exception:  # pragma: no cover - nunca deve quebrar a requisição
                import logging

                logging.getLogger("orders").exception("Falha ao liberar reservas expiradas")
        return get_response(request)

    return middleware
