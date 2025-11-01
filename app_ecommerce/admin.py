from django.contrib import admin

from . import models


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0
    autocomplete_fields = ('product',)


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'is_available', 'updated_at')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'slug', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'stock', 'is_available')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'created_at', 'is_completed', 'transaction_id')
    list_filter = ('is_completed', 'created_at')
    search_fields = ('transaction_id', 'customer__email')
    inlines = (OrderItemInline,)


@admin.register(models.OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'added_at')
    list_filter = ('added_at', 'order__is_completed')
    autocomplete_fields = ('order', 'product')


@admin.register(models.ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ('order', 'customer', 'city', 'state', 'zipcode')
    search_fields = ('city', 'state', 'zipcode', 'customer__email')
