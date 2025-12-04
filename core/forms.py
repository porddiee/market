from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class SignUpForm(UserCreationForm):
    is_seller = forms.BooleanField(required=False, label='Register as seller')

    class Meta:
        model = User
        fields = ('username', 'email', 'is_seller', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Relax username validators for friendlier signup
        try:
            self.fields['username'].validators = []
        except Exception:
            pass
        # Reduce strict help text for passwords
        if 'password1' in self.fields:
            self.fields['password1'].help_text = ''
        if 'password2' in self.fields:
            self.fields['password2'].help_text = ''


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['phone_number', 'default_address', 'seller_lat', 'seller_lng']
        widgets = {
            'default_address': forms.Textarea(attrs={'rows': 3}),
        }


from .models import Product, ProductImage, Category


class ProductForm(forms.ModelForm):
    image = forms.ImageField(required=False, label='Main image')

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'unit', 'stock', 'brand', 'category']

    def save(self, seller=None, commit=True):
        product = super().save(commit=False)
        if seller is not None:
            product.seller = seller
        if commit:
            product.save()
            # handle image
            img = self.cleaned_data.get('image')
            if img:
                ProductImage.objects.create(product=product, image=img)
        return product
