from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils.text import slugify


def _generate_unique_slug(instance: models.Model, source: str, *, slug_field: str = 'slug') -> str:
    """
    Build a slug from `source`, appending a counter until it is unique for the model.
    """
    base_slug = slugify(source) or 'item'
    slug = base_slug
    ModelClass = instance.__class__
    counter = 1

    while ModelClass.objects.filter(**{slug_field: slug}).exclude(pk=instance.pk).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1

    return slug


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ('name',)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug and self.name:
            self.slug = _generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('slug',)),
            models.Index(fields=('is_available', 'category')),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug and self.name:
            self.slug = _generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)

    @property
    def available_stock(self) -> int:
        return self.stock if self.is_available else 0


class Order(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'Pedido #{self.pk or "nuevo"}'

    @property
    def total_items(self) -> int:
        return sum(item.quantity or 0 for item in self.items.all())

    @property
    def subtotal(self) -> Decimal:
        total = Decimal('0.00')
        for item in self.items.select_related('product'):
            if item.product:
                total += item.subtotal
        return total

    @property
    def has_physical_items(self) -> bool:
        return any(item.product for item in self.items.all())


class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, related_name='items')
    quantity = models.PositiveIntegerField(default=0, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Artículo de pedido'
        verbose_name_plural = 'Artículos de pedido'
        ordering = ('-added_at',)

    def __str__(self) -> str:
        return f'{self.product} x {self.quantity}'

    @property
    def subtotal(self) -> Decimal:
        if self.product and self.quantity:
            return self.product.price * self.quantity
        return Decimal('0.00')


class ShippingAddress(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=20)

    class Meta:
        verbose_name = 'Dirección de envío'
        verbose_name_plural = 'Direcciones de envío'
        ordering = ('-order__created_at',)

    def __str__(self) -> str:
        recipient = self.customer.get_full_name() if self.customer else 'Cliente invitado'
        return f'{recipient} - {self.address}'
