from django.urls import path
from .views import (
    HomeView,
    ProductDetailView,
    cart_view,
    update_cart,
    SignUpView,
    checkout_view,
    order_detail,
    buyer_dashboard,
    seller_dashboard,
    seller_update_order_status,
    seller_add_product,
    seller_edit_product,
    seller_delete_product,
    profile_view,
    admin_dashboard,
    CustomLoginView,
)
from django.contrib.auth.views import LogoutView
from core.views import seller_store


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('product/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('cart/', cart_view, name='cart'),
    path('cart/update/', update_cart, name='update_cart'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('checkout/', checkout_view, name='checkout'),
    path('order/<int:pk>/', order_detail, name='order_detail'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('accounts/login/', CustomLoginView.as_view(), name='accounts_login'),
    path('accounts/logout/', LogoutView.as_view(next_page='/'), name='logout'),

    # Dashboards
    path('buyer/dashboard/', buyer_dashboard, name='buyer_dashboard'),
    path('seller/dashboard/', seller_dashboard, name='seller_dashboard'),
    path('seller/<int:pk>/', seller_store, name='seller_store'),
    path('seller/order/<int:pk>/update/', seller_update_order_status, name='seller_update_order_status'),
    path('seller/product/add/', seller_add_product, name='seller_add_product'),
    path('seller/product/<int:pk>/edit/', seller_edit_product, name='seller_edit_product'),
    path('seller/product/<int:pk>/delete/', seller_delete_product, name='seller_delete_product'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('profile/', profile_view, name='profile'),
]
