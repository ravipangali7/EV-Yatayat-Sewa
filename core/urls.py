from django.urls import path
from .views import (
    auth_views,
    user_views,
    wallet_views,
    transaction_views,
    super_setting_views,
    card_views,
)

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', auth_views.login_view, name='auth-login'),
    path('auth/logout/', auth_views.logout_view, name='auth-logout'),
    path('auth/me/', auth_views.me_view, name='auth-me'),
    path('auth/register/', auth_views.register_view, name='auth-register'),
    path('auth/register-request-otp/', auth_views.register_request_otp_view, name='auth-register-request-otp'),
    path('auth/register-verify/', auth_views.register_verify_view, name='auth-register-verify'),
    path('auth/forgot-password/', auth_views.forgot_password_view, name='auth-forgot-password'),
    path('auth/verify-otp/', auth_views.verify_otp_view, name='auth-verify-otp'),
    path('auth/change-password/', auth_views.change_password_view, name='auth-change-password'),
    
    # User endpoints
    path('users/', user_views.user_list_get_view, name='user-list-get'),
    path('users/create/', user_views.user_list_post_view, name='user-list-post'),
    path('users/<int:pk>/', user_views.user_detail_get_view, name='user-detail-get'),
    path('users/<int:pk>/edit/', user_views.user_detail_post_view, name='user-detail-post'),
    path('users/<int:pk>/delete/', user_views.user_delete_get_view, name='user-delete'),
    
    # Wallet endpoints
    path('wallets/', wallet_views.wallet_list_get_view, name='wallet-list-get'),
    path('wallets/create/', wallet_views.wallet_list_post_view, name='wallet-list-post'),
    path('wallets/<int:pk>/', wallet_views.wallet_detail_get_view, name='wallet-detail-get'),
    path('wallets/<int:pk>/edit/', wallet_views.wallet_detail_post_view, name='wallet-detail-post'),
    path('wallets/<int:pk>/delete/', wallet_views.wallet_delete_get_view, name='wallet-delete'),
    path('wallets/my/deposit/', wallet_views.wallet_my_deposit_view, name='wallet-my-deposit'),
    
    # Card endpoints
    path('cards/', card_views.card_list_get_view, name='card-list-get'),
    path('cards/search/', card_views.card_search_by_number_view, name='card-search'),
    path('cards/<int:pk>/', card_views.card_detail_get_view, name='card-detail-get'),
    path('cards/<int:pk>/topup/', card_views.card_topup_view, name='card-topup'),
    
    # Transaction endpoints
    path('transactions/', transaction_views.transaction_list_get_view, name='transaction-list-get'),
    path('transactions/create/', transaction_views.transaction_list_post_view, name='transaction-list-post'),
    path('transactions/<int:pk>/', transaction_views.transaction_detail_get_view, name='transaction-detail-get'),
    path('transactions/<int:pk>/edit/', transaction_views.transaction_detail_post_view, name='transaction-detail-post'),
    path('transactions/<int:pk>/delete/', transaction_views.transaction_delete_get_view, name='transaction-delete'),
    
    # Super Setting endpoints
    path('super-settings/', super_setting_views.super_setting_list_get_view, name='super-setting-list-get'),
    path('super-settings/create/', super_setting_views.super_setting_list_post_view, name='super-setting-list-post'),
    path('super-settings/<int:pk>/', super_setting_views.super_setting_detail_get_view, name='super-setting-detail-get'),
    path('super-settings/<int:pk>/edit/', super_setting_views.super_setting_detail_post_view, name='super-setting-detail-post'),
    path('super-settings/<int:pk>/delete/', super_setting_views.super_setting_delete_get_view, name='super-setting-delete'),
]
