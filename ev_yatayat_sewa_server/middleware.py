"""Project middleware."""
import os

from django.http import HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin


class SystemSubdomainRootRedirectMiddleware(MiddlewareMixin):
    """
    If the request host is system.<domain> (first DNS label configurable), redirect GET / to /admin/.
    Marketing hosts keep / for the SEO shell + SPA. Disable with SYSTEM_SUBDOMAIN_ROOT_REDIRECT=0.
    """

    def process_request(self, request):
        if os.environ.get('SYSTEM_SUBDOMAIN_ROOT_REDIRECT', 'true').lower() not in (
            '1',
            'true',
            'yes',
        ):
            return None
        prefix = os.environ.get('SYSTEM_SUBDOMAIN_HOST_PREFIX', 'system').strip().lower()
        if not prefix:
            return None
        host = request.get_host().split(':')[0].lower()
        first = host.split('.')[0] if host else ''
        if first != prefix:
            return None
        if request.method != 'GET':
            return None
        if request.path not in ('/', ''):
            return None
        return HttpResponseRedirect('/admin/')
