from django import forms

from .models import ShippingAddress


class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ('address', 'city', 'state', 'zipcode')
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Departamento/Estado'}),
            'zipcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código postal'}),
        }
