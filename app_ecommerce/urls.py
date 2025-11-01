from django.urls import path

from . import views

app_name = 'app_ecommerce'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('cart/', views.CartView.as_view(), name='cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('api/cart/update/', views.update_cart_item, name='update_cart_item'),
]
