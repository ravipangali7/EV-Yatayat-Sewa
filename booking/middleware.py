"""
Middleware to ensure POST .../seat-bookings/checkout/ is always handled
even when URL config differs on server (e.g. old deployment or proxy stripping).
"""
from django.http import HttpRequest, HttpResponse


def _is_checkout_path(path: str) -> bool:
    """Match any path ending with seat-bookings/checkout (with or without api/ prefix)."""
    p = path.rstrip("/")
    return p.endswith("seat-bookings/checkout") or p.endswith("api/seat-bookings/checkout")


class SeatBookingCheckoutFallbackMiddleware:
    """
    If the request is POST to .../seat-bookings/checkout, handle it by calling
    the checkout view directly. Guarantees the endpoint works even when URL
    routing fails (e.g. different server config or path prefix).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not _is_checkout_path(request.path):
            return self.get_response(request)

        # CORS preflight: return 200 so browser then sends POST
        if request.method == "OPTIONS":
            from django.http import HttpResponse as PlainHttpResponse
            return PlainHttpResponse(status=200)

        if request.method != "POST":
            return self.get_response(request)

        # View is @api_view; it expects HttpRequest and wraps it in DRF Request itself
        from booking.views.seat_booking_views import seat_booking_checkout_view

        response = seat_booking_checkout_view(request)
        # Ensure we never return an unrendered TemplateResponse (causes ContentNotRenderedError in gunicorn)
        if getattr(response, "is_rendered", True) is False and hasattr(response, "render"):
            response.render()
        return response
