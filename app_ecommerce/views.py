from __future__ import annotations

import json
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Sum
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from .forms import ShippingAddressForm
from .models import Category, Order, OrderItem, Product, ShippingAddress

SESSION_CART_KEY = 'cart'
SESSION_ORDER_KEY = 'cart_order_id'


def _get_session_cart(request: HttpRequest) -> Dict[str, int]:
    return request.session.setdefault(SESSION_CART_KEY, {})


def _save_session_cart(request: HttpRequest, cart: Dict[str, int]) -> None:
    request.session[SESSION_CART_KEY] = cart
    request.session.modified = True


def _get_active_order(request: HttpRequest) -> Order | None:
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, is_completed=False)
        request.session[SESSION_ORDER_KEY] = order.pk
        return order

    order_id = request.session.get(SESSION_ORDER_KEY)
    if order_id:
        try:
            return Order.objects.get(pk=order_id, is_completed=False)
        except Order.DoesNotExist:
            request.session.pop(SESSION_ORDER_KEY, None)
    return None


def _sync_order_from_cart(order: Order, cart: Dict[str, int]) -> None:
    kept_product_ids = [int(pk) for pk in cart.keys()]
    existing_items = {item.product_id: item for item in order.items.select_related('product')}

    # Update or create items based on the cart
    products = Product.objects.filter(id__in=kept_product_ids)
    for product in products:
        quantity = int(cart.get(str(product.pk), 0))
        if quantity <= 0:
            continue

        order_item = existing_items.get(product.pk)
        if order_item:
            order_item.quantity = quantity
            order_item.save(update_fields=('quantity',))
        else:
            OrderItem.objects.create(order=order, product=product, quantity=quantity)

    # Remove items that are no longer in the cart
    for product_id, order_item in existing_items.items():
        if str(product_id) not in cart:
            order_item.delete()


def _build_cart_items(cart: Dict[str, int]) -> Tuple[List[Dict], Decimal]:
    if not cart:
        return [], Decimal('0.00')

    product_ids = [int(pk) for pk in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    items = []
    total = Decimal('0.00')

    for product in products:
        quantity = int(cart.get(str(product.pk), 0))
        if quantity <= 0:
            continue
        subtotal = product.price * quantity
        total += subtotal
        items.append(
            {
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal,
            }
        )

    return items, total


def _cart_snapshot(cart: Dict[str, int]) -> Dict[str, object]:
    items, total = _build_cart_items(cart)
    return {
        'count': sum(item['quantity'] for item in items),
        'total': str(total),
        'items': [
            {
                'id': item['product'].pk,
                'name': item['product'].name,
                'quantity': item['quantity'],
                'subtotal': str(item['subtotal']),
            }
            for item in items
        ],
    }


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'app_ecommerce/dashboard.html'
    login_url = 'page_login'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = _get_session_cart(self.request)

        total_products = Product.objects.count()
        total_categories = Category.objects.count()
        total_orders = Order.objects.count()
        completed_orders = Order.objects.filter(is_completed=True).count()

        completed_items = OrderItem.objects.filter(order__is_completed=True).select_related('product')
        total_sales = Decimal('0.00')
        for item in completed_items:
            if item.product and item.quantity:
                total_sales += item.product.price * item.quantity

        recent_orders = (
            Order.objects.select_related('customer')
            .prefetch_related('items__product')
            .order_by('-created_at')[:5]
        )

        top_products = (
            Product.objects.filter(orderitem__order__is_completed=True)
            .annotate(total_sold=Sum('orderitem__quantity'))
            .order_by('-total_sold')[:5]
        )

        context.update(
            {
                'cart_count': sum(cart.values()),
                'total_products': total_products,
                'total_categories': total_categories,
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'total_sales': total_sales,
                'recent_orders': recent_orders,
                'top_products': top_products,
            }
        )
        return context


class ProductListView(ListView):
    model = Product
    template_name = 'app_ecommerce/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_available=True)
            .select_related('category')
            .order_by('-created_at')
        )
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = _get_session_cart(self.request)
        context['categories'] = Category.objects.all()
        context['active_category'] = self.request.GET.get('category')
        context['cart_count'] = sum(cart.values())
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'app_ecommerce/product_detail.html'
    context_object_name = 'product'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = _get_session_cart(self.request)
        context['cart_count'] = sum(cart.values())
        return context


class CartView(TemplateView):
    template_name = 'app_ecommerce/cart.html'

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        cart = _get_session_cart(request)
        order = _get_active_order(request)
        if order:
            _sync_order_from_cart(order, cart)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = _get_session_cart(self.request)
        items, total = _build_cart_items(cart)
        context.update(
            {
                'cart_items': items,
                'cart_total': total,
                'cart_count': sum(item['quantity'] for item in items),
            }
        )
        return context


class CheckoutView(FormView):
    template_name = 'app_ecommerce/checkout.html'
    form_class = ShippingAddressForm
    success_url = reverse_lazy('app_ecommerce:dashboard')

    def dispatch(self, request: HttpRequest, *args, **kwargs):
        cart = _get_session_cart(request)
        items, total = _build_cart_items(cart)
        if not items:
            messages.warning(request, _('Tu carrito está vacío. Agrega productos antes de continuar.'))
            return redirect('app_ecommerce:product_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request
        cart = _get_session_cart(request)
        items, total = _build_cart_items(cart)

        order = _get_active_order(request)
        if not order:
            order = Order.objects.create(customer=request.user if request.user.is_authenticated else None)
            request.session[SESSION_ORDER_KEY] = order.pk

        _sync_order_from_cart(order, cart)

        shipping_address, created = ShippingAddress.objects.get_or_create(order=order, defaults=form.cleaned_data)
        if not created:
            for field, value in form.cleaned_data.items():
                setattr(shipping_address, field, value)
            shipping_address.save()

        if total == 0:
            messages.error(request, _('No se puede procesar un pedido sin productos.'))
            return redirect('app_ecommerce:product_list')

        messages.success(
            request,
            _('Dirección registrada correctamente. Completa el pago para finalizar tu compra.'),
        )
        return super().form_valid(form)


class UpdateCartItemView(View):
    http_method_names = ['post']

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            data = request.POST

        product_id = data.get('productId') or data.get('product_id')
        action = data.get('action', 'add')
        quantity = data.get('quantity')

        if not product_id:
            return HttpResponseBadRequest('productId is required')

        product = get_object_or_404(Product, pk=product_id, is_available=True)
        cart = _get_session_cart(request)
        product_key = str(product.pk)
        current_qty = int(cart.get(product_key, 0))

        if action == 'add':
            increment = int(quantity or 1)
            cart[product_key] = current_qty + increment
        elif action == 'remove':
            decrement = int(quantity or 1)
            new_qty = current_qty - decrement
            if new_qty > 0:
                cart[product_key] = new_qty
            else:
                cart.pop(product_key, None)
        elif action == 'set':
            new_qty = int(quantity or 0)
            if new_qty > 0:
                cart[product_key] = new_qty
            else:
                cart.pop(product_key, None)
        elif action == 'delete':
            cart.pop(product_key, None)
        else:
            return HttpResponseBadRequest('Unsupported action')

        _save_session_cart(request, cart)

        order = _get_active_order(request)
        if order:
            _sync_order_from_cart(order, cart)

        snapshot = _cart_snapshot(cart)
        snapshot['message'] = _('Carrito actualizado correctamente.')
        return JsonResponse(snapshot, status=200)


# Naming the view explicitly for URL imports
update_cart_item = UpdateCartItemView.as_view()
