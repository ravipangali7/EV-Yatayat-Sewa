from django.urls import path
from .views import (
    slider_views,
    cms_page_views,
    team_views,
    testimonial_views,
    service_views,
    faq_views,
    contact_message_views,
    blog_views,
    site_setting_views,
    public_views,
)

urlpatterns = [
    # Admin: Sliders
    path('sliders/', slider_views.slider_list_get_view),
    path('sliders/create/', slider_views.slider_list_post_view),
    path('sliders/<int:pk>/', slider_views.slider_detail_get_view),
    path('sliders/<int:pk>/edit/', slider_views.slider_detail_post_view),
    path('sliders/<int:pk>/delete/', slider_views.slider_delete_view),
    # Admin: CMS Pages
    path('cms-pages/', cms_page_views.cms_page_list_get_view),
    path('cms-pages/create/', cms_page_views.cms_page_list_post_view),
    path('cms-pages/<int:pk>/', cms_page_views.cms_page_detail_get_view),
    path('cms-pages/<int:pk>/edit/', cms_page_views.cms_page_detail_post_view),
    path('cms-pages/<int:pk>/delete/', cms_page_views.cms_page_delete_view),
    # Admin: Team
    path('team/', team_views.team_list_get_view),
    path('team/create/', team_views.team_list_post_view),
    path('team/reorder/', team_views.team_reorder_view),
    path('team/<int:pk>/', team_views.team_detail_get_view),
    path('team/<int:pk>/edit/', team_views.team_detail_post_view),
    path('team/<int:pk>/delete/', team_views.team_delete_view),
    # Admin: Testimonials
    path('testimonials/', testimonial_views.testimonial_list_get_view),
    path('testimonials/create/', testimonial_views.testimonial_list_post_view),
    path('testimonials/<int:pk>/', testimonial_views.testimonial_detail_get_view),
    path('testimonials/<int:pk>/edit/', testimonial_views.testimonial_detail_post_view),
    path('testimonials/<int:pk>/delete/', testimonial_views.testimonial_delete_view),
    # Admin: Services
    path('services/', service_views.service_list_get_view),
    path('services/create/', service_views.service_list_post_view),
    path('services/reorder/', service_views.service_reorder_view),
    path('services/<int:pk>/', service_views.service_detail_get_view),
    path('services/<int:pk>/edit/', service_views.service_detail_post_view),
    path('services/<int:pk>/delete/', service_views.service_delete_view),
    # Admin: FAQs
    path('faqs/', faq_views.faq_list_get_view),
    path('faqs/create/', faq_views.faq_list_post_view),
    path('faqs/reorder/', faq_views.faq_reorder_view),
    path('faqs/<int:pk>/', faq_views.faq_detail_get_view),
    path('faqs/<int:pk>/edit/', faq_views.faq_detail_post_view),
    path('faqs/<int:pk>/delete/', faq_views.faq_delete_view),
    # Admin: Contact Messages
    path('contact-messages/', contact_message_views.contact_message_list_get_view),
    path('contact-messages/<int:pk>/', contact_message_views.contact_message_detail_get_view),
    path('contact-messages/<int:pk>/edit/', contact_message_views.contact_message_detail_post_view),
    path('contact-messages/<int:pk>/delete/', contact_message_views.contact_message_delete_view),
    # Admin: Blog
    path('blogs/', blog_views.blog_list_get_view),
    path('blogs/create/', blog_views.blog_list_post_view),
    path('blogs/<int:pk>/', blog_views.blog_detail_get_view),
    path('blogs/<int:pk>/edit/', blog_views.blog_detail_post_view),
    path('blogs/<int:pk>/delete/', blog_views.blog_delete_view),
    # Admin: Site Setting
    path('site-setting/', site_setting_views.site_setting_get_view),
    path('site-setting/edit/', site_setting_views.site_setting_post_view),
    # Public (AllowAny)
    path('website/sliders/', public_views.public_sliders_view),
    path('website/site-setting/', public_views.public_site_setting_view),
    path('website/cms-pages/about/', public_views.public_cms_about_view),
    path('website/cms-pages/by-slug/<slug:slug>/', public_views.public_cms_by_slug_view),
    path('website/cms-pages/header/', public_views.public_cms_header_view),
    path('website/services/', public_views.public_services_view),
    path('website/team/', public_views.public_team_view),
    path('website/testimonials/', public_views.public_testimonials_view),
    path('website/blogs/', public_views.public_blogs_view),
    path('website/blogs/by-slug/<slug:slug>/', public_views.public_blog_by_slug_view),
    path('website/faqs/', public_views.public_faqs_view),
    path('website/contact-messages/', public_views.public_contact_message_create_view),
    path('website/vehicles/', public_views.public_vehicles_view),
]
