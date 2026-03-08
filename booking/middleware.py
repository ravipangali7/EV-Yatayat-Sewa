"""
Middleware to ensure POST /api/seat-bookings/checkout/ is always handled
even when URL config differs on server (e.g. old deployment or proxy stripping).
"""
from django.http import HttpRequest


# Paths that should be handled by checkout view (without trailing slash, for comparison)
CHECKOUT_PATHS = frozenset({'/api/seat-bookings/checkout', '/seat-bookings/checkout'})


class SeatBookingCheckoutFallbackMiddleware:
    """
    If the request is POST to seat-bookings/checkout (with or without api/ prefix),
    handle it by calling the checkout view directly. This guarantees the endpoint
    works even when URL routing fails to match (e.g. different server config).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if request.method != 'POST':
            return self.get_response(request)

        path = request.path.rstrip('/')
        if path not in CHECKOUT_PATHS:
            return self.get_response(request)

        # View is @api_view; it expects HttpRequest and wraps it in DRF Request itself
        from booking.views.seat_booking_views import seat_booking_checkout_view

        return seat_booking_checkout_view(request)
