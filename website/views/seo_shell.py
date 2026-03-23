"""Serve HTML shell with Open Graph / Twitter meta for crawlers and SPA mount."""
from pathlib import Path

from django.conf import settings
from django.shortcuts import render

from ..models import Blog, CMSPage, Service, SiteSetting
from ..seo import (
    absolute_media_url,
    article_json_ld,
    get_canonical_origin,
    organization_json_ld,
    parse_vite_index_html,
    strip_html_to_text,
)


def _site():
    return SiteSetting.objects.first()


def _full_public_url(origin: str, path: str) -> str:
    path = (path or '/').strip()
    if not path.startswith('/'):
        path = '/' + path
    base = (origin or '').rstrip('/')
    if base:
        return f'{base}{path}'
    return path


def _site_default_og_image(request, site):
    if not site:
        return None
    return (
        absolute_media_url(request, site.default_og_image)
        or absolute_media_url(request, site.cover_image)
        or absolute_media_url(request, site.logo)
    )


def _vite_assets():
    index_path = getattr(settings, 'SPA_INDEX_HTML_PATH', None) or (
        Path(settings.BASE_DIR).parent / 'web' / 'dist' / 'index.html'
    )
    scripts, styles = parse_vite_index_html(index_path)
    return scripts, styles


def _base_context(request, site):
    origin = get_canonical_origin(request)
    scripts, styles = _vite_assets()
    favicon = None
    if site:
        favicon = absolute_media_url(request, site.favicon) or absolute_media_url(request, site.logo)
    tw = (site.twitter_handle if site else '') or ''
    tw = tw.strip().lstrip('@')
    twitter_site = f'@{tw}' if tw else ''
    return {
        'canonical_origin': origin,
        'spa_scripts': scripts,
        'spa_stylesheets': styles,
        'favicon_url': favicon,
        'facebook_app_id': (site.facebook_app_id if site else '') or '',
        'google_site_verification': (site.google_site_verification if site else '') or '',
        'twitter_site': twitter_site,
        'og_locale': (site.og_locale if site and site.og_locale else 'en_US') or 'en_US',
        'site_name': (site.name if site and site.name else '') or 'Yatayat Sewa',
    }


def _seo_static_page(request, *, page_key: str, path: str, title_suffix: str, description_override: str = ''):
    site = _site()
    ctx = _base_context(request, site)
    origin = ctx['canonical_origin']
    site_name = ctx['site_name']

    title = (site.meta_title if site and site.meta_title else '') or site_name
    if title_suffix:
        title = f'{title_suffix} | {title}' if title else title_suffix

    desc = description_override or (site.meta_description if site and site.meta_description else '') or (
        (site.tagline if site else '') or ''
    )
    desc = (desc or '')[:300]

    og_image = _site_default_og_image(request, site)
    robots = 'index,follow'

    ctx.update(
        {
            'html_title': title[:70],
            'meta_description': desc,
            'og_title': title[:70],
            'og_description': desc,
            'og_image': og_image,
            'og_image_alt': site_name,
            'og_type': 'website',
            'og_url': _full_public_url(origin, path),
            'robots': robots,
            'article_published_time': '',
            'json_ld_script': organization_json_ld(origin, site),
        }
    )

    if page_key == 'about':
        about = CMSPage.objects.filter(is_active=True, is_about=True).order_by('id').first()
        if about:
            t = (about.meta_title or about.title or '').strip()
            if t:
                ctx['html_title'] = t[:70]
                ctx['og_title'] = t[:70]
            d = (about.meta_description or '').strip() or strip_html_to_text(about.content, 300)
            if d:
                ctx['meta_description'] = d[:300]
                ctx['og_description'] = d[:300]
            img = absolute_media_url(request, about.og_image) or absolute_media_url(request, about.image)
            if img:
                ctx['og_image'] = img
            if about.og_image_alt:
                ctx['og_image_alt'] = about.og_image_alt[:255]
            if about.robots_noindex:
                ctx['robots'] = 'noindex,nofollow'

    return ctx


def _seo_blog(request, slug: str):
    site = _site()
    ctx = _base_context(request, site)
    origin = ctx['canonical_origin']
    site_name = ctx['site_name']

    try:
        blog = Blog.objects.get(slug=slug, is_active=True)
    except Blog.DoesNotExist:
        return None

    title = (blog.meta_title or blog.name or '').strip()[:70]
    desc = (
        (blog.meta_description or '').strip()
        or (blog.excerpt or '').strip()
        or strip_html_to_text(blog.content, 300)
    )[:300]

    og_image = (
        absolute_media_url(request, blog.og_image)
        or absolute_media_url(request, blog.image)
        or _site_default_og_image(request, site)
    )

    path = (blog.canonical_path or '').strip() or f'/blog/{blog.slug}/'
    if not path.startswith('/'):
        path = '/' + path

    ctx.update(
        {
            'html_title': title,
            'meta_description': desc,
            'og_title': title,
            'og_description': desc,
            'og_image': og_image,
            'og_image_alt': (blog.og_image_alt or blog.name or site_name)[:255],
            'og_type': 'article',
            'og_url': _full_public_url(origin, path),
            'robots': 'noindex,nofollow' if blog.robots_noindex else 'index,follow',
            'article_published_time': blog.created_at.isoformat() if blog.created_at else '',
            'json_ld_script': article_json_ld(
                blog,
                title,
                desc,
                og_image,
                _full_public_url(origin, path),
                publisher_name=site_name,
            ),
        }
    )
    return ctx


def _seo_service(request, slug: str):
    site = _site()
    ctx = _base_context(request, site)
    origin = ctx['canonical_origin']
    site_name = ctx['site_name']

    try:
        svc = Service.objects.get(slug=slug, is_active=True)
    except Service.DoesNotExist:
        return None

    title = (svc.meta_title or svc.name or '').strip()[:70]
    desc = ((svc.meta_description or '').strip() or strip_html_to_text(svc.description, 300))[:300]
    og_image = absolute_media_url(request, svc.og_image) or _site_default_og_image(request, site)

    path = (svc.canonical_path or '').strip() or f'/service/{svc.slug}/'
    if not path.startswith('/'):
        path = '/' + path

    ctx.update(
        {
            'html_title': title,
            'meta_description': desc,
            'og_title': title,
            'og_description': desc,
            'og_image': og_image,
            'og_image_alt': (svc.og_image_alt or svc.name or site_name)[:255],
            'og_type': 'website',
            'og_url': _full_public_url(origin, path),
            'robots': 'noindex,nofollow' if svc.robots_noindex else 'index,follow',
            'article_published_time': '',
            'json_ld_script': organization_json_ld(origin, site),
        }
    )
    return ctx


def _seo_cms_page(request, slug: str):
    site = _site()
    ctx = _base_context(request, site)
    origin = ctx['canonical_origin']
    site_name = ctx['site_name']

    try:
        page = CMSPage.objects.get(slug=slug, is_active=True)
    except CMSPage.DoesNotExist:
        return None

    title = (page.meta_title or page.title or '').strip()[:70]
    desc = ((page.meta_description or '').strip() or strip_html_to_text(page.content, 300))[:300]
    og_image = (
        absolute_media_url(request, page.og_image)
        or absolute_media_url(request, page.image)
        or _site_default_og_image(request, site)
    )

    path = (page.canonical_path or '').strip() or f'/page/{page.slug}/'
    if not path.startswith('/'):
        path = '/' + path

    ctx.update(
        {
            'html_title': title,
            'meta_description': desc,
            'og_title': title,
            'og_description': desc,
            'og_image': og_image,
            'og_image_alt': (page.og_image_alt or page.title or site_name)[:255],
            'og_type': 'website',
            'og_url': _full_public_url(origin, path),
            'robots': 'noindex,nofollow' if page.robots_noindex else 'index,follow',
            'article_published_time': '',
            'json_ld_script': organization_json_ld(origin, site),
        }
    )
    return ctx


def _render(request, builder, status=200):
    ctx = builder()
    if ctx is None:
        site = _site()
        base = _base_context(request, site)
        origin = base['canonical_origin']
        base.update(
            {
                'html_title': 'Not found | ' + base['site_name'],
                'meta_description': 'The page you requested was not found.',
                'og_title': 'Not found',
                'og_description': 'The page you requested was not found.',
                'og_image': _site_default_og_image(request, site),
                'og_image_alt': base['site_name'],
                'og_type': 'website',
                'og_url': _full_public_url(origin, request.path),
                'robots': 'noindex,nofollow',
                'article_published_time': '',
                'json_ld_script': organization_json_ld(origin, site),
            }
        )
        ctx = base
        status = 404
    return render(request, 'website/spa_shell.html', ctx, status=status)


def spa_shell_home(request):
    return _render(request, lambda: _seo_static_page(request, page_key='home', path='/'))


def spa_shell_about(request):
    return _render(request, lambda: _seo_static_page(request, page_key='about', path='/about/'))


def spa_shell_services(request):
    return _render(
        request,
        lambda: _seo_static_page(
            request, page_key='services', path='/services/', title_suffix='Services'
        ),
    )


def spa_shell_blogs(request):
    return _render(
        request,
        lambda: _seo_static_page(request, page_key='blogs', path='/blogs/', title_suffix='Blog'),
    )


def spa_shell_blog_alias(request):
    return spa_shell_blogs(request)


def spa_shell_contact(request):
    return _render(
        request,
        lambda: _seo_static_page(request, page_key='contact', path='/contact/', title_suffix='Contact'),
    )


def spa_shell_login(request):
    return _render(request, lambda: _seo_static_page(request, page_key='login', path='/login/', title_suffix='Login'))


def spa_shell_blog(request, slug):
    return _render(request, lambda: _seo_blog(request, slug))


def spa_shell_service(request, slug):
    return _render(request, lambda: _seo_service(request, slug))


def spa_shell_cms_page(request, slug):
    return _render(request, lambda: _seo_cms_page(request, slug))
