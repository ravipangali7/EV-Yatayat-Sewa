"""Public marketing URLs: HTML shell with SEO + SPA assets (mount before admin.site.urls)."""
from django.urls import path

from .views.seo_shell import (
    spa_shell_about,
    spa_shell_blog,
    spa_shell_blog_alias,
    spa_shell_blogs,
    spa_shell_contact,
    spa_shell_cms_page,
    spa_shell_home,
    spa_shell_login,
    spa_shell_service,
    spa_shell_services,
)

urlpatterns = [
    path('', spa_shell_home, name='spa_shell_home'),
    path('about/', spa_shell_about, name='spa_shell_about'),
    path('services/', spa_shell_services, name='spa_shell_services'),
    path('blogs/', spa_shell_blogs, name='spa_shell_blogs'),
    path('blog/', spa_shell_blog_alias, name='spa_shell_blog_list_alias'),
    path('blog/<slug:slug>/', spa_shell_blog, name='spa_shell_blog'),
    path('service/<slug:slug>/', spa_shell_service, name='spa_shell_service'),
    path('page/<slug:slug>/', spa_shell_cms_page, name='spa_shell_cms_page'),
    path('contact/', spa_shell_contact, name='spa_shell_contact'),
    path('login/', spa_shell_login, name='spa_shell_login'),
]
