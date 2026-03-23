"""SEO helpers: canonical origin, text cleanup, absolute image URLs for Open Graph."""
import json
import re
from html import unescape

from django.conf import settings


def get_canonical_origin(request=None):
    """
    Public site base URL for og:url and sitemap (must be https in production).
    Set SITE_CANONICAL_ORIGIN in settings or env, e.g. https://www.evyatayatsewa.com
    """
    raw = getattr(settings, 'SITE_CANONICAL_ORIGIN', '') or ''
    raw = (raw or '').strip().rstrip('/')
    if raw and not raw.startswith('http'):
        raw = f'https://{raw}'
    if raw:
        return raw
    if request:
        scheme = 'https' if request.is_secure() else request.scheme
        host = request.get_host()
        return f'{scheme}://{host}'.rstrip('/')
    return ''


def absolute_media_url(request, file_field):
    """
    Build an absolute HTTPS URL for uploaded media (og:image, etc.).
    Prefer MEDIA_PUBLIC_BASE_URL (e.g. API host that serves /media/) when set,
    else SITE_CANONICAL_ORIGIN so links match the public marketing domain,
    else the incoming request host.
    """
    if not file_field:
        return None
    try:
        url = file_field.url
    except ValueError:
        return None
    if url.startswith('http'):
        return url
    path = url if url.startswith('/') else f'/{url}'

    media_base = getattr(settings, 'MEDIA_PUBLIC_BASE_URL', '') or ''
    media_base = media_base.strip().rstrip('/')
    if media_base and not media_base.startswith('http'):
        media_base = f'https://{media_base}'
    if media_base:
        return f'{media_base}{path}'

    canonical = getattr(settings, 'SITE_CANONICAL_ORIGIN', '') or ''
    canonical = canonical.strip().rstrip('/')
    if canonical and not canonical.startswith('http'):
        canonical = f'https://{canonical}'
    if canonical:
        return f'{canonical}{path}'

    if request:
        return request.build_absolute_uri(url)
    origin = get_canonical_origin()
    if not origin:
        return path
    return f'{origin.rstrip("/")}{path}'


def strip_html_to_text(html, max_length=300):
    if not html:
        return ''
    text = re.sub(r'<[^>]+>', ' ', html)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    if max_length and len(text) > max_length:
        text = text[: max_length - 1].rsplit(' ', 1)[0] + '…'
    return text


def canonical_url_from_path(origin, path):
    if not path:
        return origin + '/' if origin else '/'
    path = path.strip()
    if not path.startswith('/'):
        path = '/' + path
    if origin:
        return f'{origin}{path}'.rstrip('/') + ('' if path.endswith('/') else '')
    return path


def parse_vite_index_html(index_path):
    """
    Return (script_srcs, stylesheet_hrefs) as absolute paths (e.g. /assets/index-abc.js).
    """
    from pathlib import Path

    p = Path(index_path)
    if not p.is_file():
        return [], []
    html = p.read_text(encoding='utf-8')
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, flags=re.I)
    styles = re.findall(
        r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    )
    styles += re.findall(
        r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\'][^>]+rel=["\']stylesheet["\']',
        html,
        flags=re.I,
    )
    seen = set()
    styles_unique = []
    for h in styles:
        if h not in seen:
            seen.add(h)
            styles_unique.append(h)
    return scripts, styles_unique


def organization_json_ld(origin, site):
    if not site:
        return None
    name = (site.name or '').strip() or 'Site'
    data = {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        'name': name,
    }
    if site.tagline:
        data['description'] = site.tagline[:500]
    if origin:
        data['url'] = origin + '/'
    phones = site.phones or []
    emails = site.emails or []
    if phones:
        data['telephone'] = phones[0]
    if emails:
        data['email'] = emails[0]
    return json.dumps(data, ensure_ascii=False)


def article_json_ld(blog, title, description, image_url, page_url, publisher_name=''):
    data = {
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': title[:110],
        'description': (description or '')[:500],
    }
    if page_url:
        data['url'] = page_url
    if image_url:
        data['image'] = image_url
    if blog and getattr(blog, 'created_at', None):
        data['datePublished'] = blog.created_at.isoformat()
    if publisher_name:
        data['publisher'] = {'@type': 'Organization', 'name': publisher_name[:255]}
    return json.dumps(data, ensure_ascii=False)
