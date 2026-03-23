from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone

from ..models import Blog, CMSPage, Service
from ..seo import get_canonical_origin


def _static_paths():
    return ['/', '/about/', '/services/', '/blogs/', '/contact/', '/login/']


def sitemap_view(request):
    origin = get_canonical_origin(request)
    if not origin:
        origin = request.build_absolute_uri('/').rstrip('/')

    urls = []
    now = timezone.now().strftime('%Y-%m-%d')
    for p in _static_paths():
        loc = f'{origin}{p}' if p.startswith('/') else f'{origin}/{p}'
        urls.append(f'  <url><loc>{escape(loc)}</loc><lastmod>{now}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>')

    for blog in Blog.objects.filter(is_active=True, robots_noindex=False).only('slug', 'updated_at'):
        loc = f'{origin}/blog/{blog.slug}/'
        lm = blog.updated_at.strftime('%Y-%m-%d') if blog.updated_at else now
        urls.append(
            f'  <url><loc>{escape(loc)}</loc><lastmod>{lm}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>'
        )

    for page in CMSPage.objects.filter(is_active=True, robots_noindex=False).only('slug', 'updated_at'):
        loc = f'{origin}/page/{page.slug}/'
        lm = page.updated_at.strftime('%Y-%m-%d') if page.updated_at else now
        urls.append(
            f'  <url><loc>{escape(loc)}</loc><lastmod>{lm}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>'
        )

    for svc in Service.objects.filter(is_active=True, robots_noindex=False).only('slug', 'updated_at'):
        loc = f'{origin}/service/{svc.slug}/'
        lm = svc.updated_at.strftime('%Y-%m-%d') if svc.updated_at else now
        urls.append(
            f'  <url><loc>{escape(loc)}</loc><lastmod>{lm}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>'
        )

    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(urls)
        + '\n</urlset>'
    )
    return HttpResponse(body, content_type='application/xml')


def robots_txt_view(request):
    origin = get_canonical_origin(request)
    if not origin:
        origin = request.build_absolute_uri('/').rstrip('/')
    sitemap_url = f'{origin}/sitemap.xml'
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /api/',
        f'Sitemap: {sitemap_url}',
        '',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')
