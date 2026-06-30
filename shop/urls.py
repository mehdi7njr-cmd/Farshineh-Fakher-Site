from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.home_page, name='home'),
    path('category/<str:category_slug>/', views.category_detail, name='category_detail'),
    path('brand/<str:brand_slug>/', views.brand_detail, name='brand_detail'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('search/', views.search_products, name='search'),
    path('products/all/', views.all_products, name='all_products'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/remove/<str:unique_key>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<str:unique_key>/<str:action>/', views.cart_update, name='cart_update'),
    path('login/', views.send_otp_view, name='login'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('bank-transfer/', views.bank_transfer, name='bank_transfer'),
    path('payment/request/', views.payment_request, name='payment_request'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('profile/', views.user_profile, name='profile'),
    path('contact-us/', TemplateView.as_view(template_name='contact.html'), name='contact'),
    path('terms/', TemplateView.as_view(template_name='terms.html'), name='terms'),
    path('complaints/', TemplateView.as_view(template_name='complaints.html'), name='complaints'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('track-order/', views.track_order, name='track_order'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('toggle-favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
]