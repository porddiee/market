from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, FormView

from .forms import SignUpForm, AddToCartForm
from .forms import ProfileForm
from django.db.models import Q
from .models import Product, Category, ProductImage, Order, OrderItem
from decimal import Decimal
from .forms import ProductForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseForbidden
from django.conf import settings
import math


class HomeView(ListView):
    model = Product
    template_name = 'home.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ProductDetailView(DetailView, FormView):
    model = Product
    template_name = 'product_detail.html'
    form_class = AddToCartForm

    def get_success_url(self):
        return reverse('cart')

    def post(self, request, *args, **kwargs):
        product = self.get_object()
        form = self.get_form()
        if form.is_valid():
            qty = form.cleaned_data['quantity']
            # If user clicked 'Buy Now', redirect to checkout with a temporary buy_now payload in session
            if request.POST.get('buy_now'):
                # store buy_now payload in session and redirect to checkout where buyer can fill address/phone
                request.session['buy_now'] = {'product_id': product.id, 'quantity': qty}
                request.session.modified = True
                if not request.user.is_authenticated:
                    return redirect('accounts_login')
                return redirect('checkout')

            # Otherwise, add to cart (default behavior)
            cart = request.session.get('cart', {})
            item = cart.get(str(product.id), {'quantity': 0, 'price': str(product.price)})
            item['quantity'] = item.get('quantity', 0) + qty
            cart[str(product.id)] = item
            request.session['cart'] = cart
            messages.success(request, 'Added to cart')
            return redirect('cart')
        return self.get(request, *args, **kwargs)


def cart_view(request):
    cart = request.session.get('cart', {})
    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.objects.filter(id__in=product_ids)
    items = []
    subtotal = Decimal('0.00')
    for p in products:
        qty = cart.get(str(p.id), {}).get('quantity', 0)
        unit_price = Decimal(str(p.price))
        discount_pct = Decimal('0')
        # Apply bulk discount only if logged-in user is a seller and buying another seller's product
        if request.user.is_authenticated and getattr(request.user, 'is_seller', False) and p.seller != request.user:
            if qty >= 10:
                discount_pct = Decimal('0.10')
            elif qty >= 5:
                discount_pct = Decimal('0.05')

        effective_unit = (unit_price * (Decimal('1.0') - discount_pct)).quantize(Decimal('0.01'))
        total_price = (effective_unit * qty).quantize(Decimal('0.01'))
        subtotal += total_price
        items.append({'product': p, 'quantity': qty, 'unit_price': effective_unit, 'total_price': total_price, 'discount_pct': discount_pct})
    return render(request, 'cart.html', {'items': items, 'subtotal': subtotal})


def update_cart(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        action = request.POST.get('action')
        pid = request.POST.get('product_id')
        if not pid:
            return redirect('cart')
        if action == 'remove':
            cart.pop(pid, None)
        else:
            qty = int(request.POST.get('quantity', 1))
            if qty <= 0:
                cart.pop(pid, None)
            else:
                item = cart.get(pid, {})
                item['quantity'] = qty
                cart[pid] = item
        request.session['cart'] = cart
    return redirect('cart')


class SignUpView(View):
    def get(self, request):
        form = SignUpForm()
        return render(request, 'registration/signup.html', {'form': form})

    def post(self, request):
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        return render(request, 'registration/signup.html', {'form': form})


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated')
            return redirect('profile')
    else:
        form = ProfileForm(instance=user)
    return render(request, 'profile.html', {'form': form})

class CustomLoginView(DjangoLoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {self.request.user.username}! 👋')
        return response

    def get_success_url(self):
        """Redirect based on user role: admin -> admin dashboard, seller -> seller dashboard, buyer -> buyer dashboard."""
        user = self.request.user
        if user.is_superuser:
            return reverse('admin_dashboard')
        elif user.is_seller:
            return reverse('seller_dashboard')
        else:
            return reverse('buyer_dashboard')


@login_required(login_url='/accounts/login/')
def checkout_view(request):
    cart = request.session.get('cart', {})
    buy_now = request.session.get('buy_now')

    # If neither cart nor buy_now, nothing to checkout
    if not cart and not buy_now:
        messages.error(request, 'Your cart is empty')
        return redirect('home')

    # Build items list and subtotal either from buy_now (single item) or cart
    items = []
    subtotal = Decimal('0.00')

    if buy_now:
        try:
            product = Product.objects.get(id=int(buy_now.get('product_id')))
            qty = int(buy_now.get('quantity', 1))
        except Product.DoesNotExist:
            messages.error(request, 'Product not found')
            return redirect('home')

        unit_price = Decimal(str(product.price))
        discount_pct = Decimal('0')
        if request.user.is_authenticated and getattr(request.user, 'is_seller', False) and product.seller != request.user:
            if qty >= 10:
                discount_pct = Decimal('0.10')
            elif qty >= 5:
                discount_pct = Decimal('0.05')

        effective_unit = (unit_price * (Decimal('1.0') - discount_pct)).quantize(Decimal('0.01'))
        total_price = (effective_unit * qty).quantize(Decimal('0.01'))
        items.append({'product': product, 'quantity': qty, 'unit_price': effective_unit, 'total_price': total_price, 'discount_pct': discount_pct})
        subtotal += total_price
    else:
        # build from cart
        product_ids = [int(pid) for pid in cart.keys()]
        products = Product.objects.filter(id__in=product_ids)
        for p in products:
            qty = cart.get(str(p.id), {}).get('quantity', 0)
            unit_price = Decimal(str(p.price))
            discount_pct = Decimal('0')
            if request.user.is_authenticated and getattr(request.user, 'is_seller', False) and p.seller != request.user:
                if qty >= 10:
                    discount_pct = Decimal('0.10')
                elif qty >= 5:
                    discount_pct = Decimal('0.05')

            effective_unit = (unit_price * (Decimal('1.0') - discount_pct)).quantize(Decimal('0.01'))
            total_price = (effective_unit * qty).quantize(Decimal('0.01'))
            subtotal += total_price
            items.append({'product': p, 'quantity': qty, 'unit_price': effective_unit, 'total_price': total_price, 'discount_pct': discount_pct})

    if request.method == 'POST':
        # create order using items computed above; get address and phone from POST (or user's defaults)
        address = request.POST.get('address') or (request.user.default_address if hasattr(request.user, 'default_address') else '')
        phone = request.POST.get('phone') or (request.user.phone_number if hasattr(request.user, 'phone_number') else '')
        # optional lat/lng captured from browser geolocation
        lat = request.POST.get('delivery_lat')
        lng = request.POST.get('delivery_lng')

        def _parse_float(v):
            try:
                return float(v)
            except Exception:
                return None

        lat_f = _parse_float(lat)
        lng_f = _parse_float(lng)

        # prepare delivery fee parameters (used per-item later)
        try:
            base_fee = float(getattr(settings, 'DELIVERY_BASE_FEE', 50.0))
            per_km = float(getattr(settings, 'DELIVERY_PER_KM', 12.0))
            store_lat = float(getattr(settings, 'STORE_LAT', 14.599512))
            store_lng = float(getattr(settings, 'STORE_LNG', 120.984222))
        except Exception:
            base_fee = float(getattr(settings, 'DELIVERY_BASE_FEE', 50.0))
            per_km = float(getattr(settings, 'DELIVERY_PER_KM', 12.0))
            store_lat = float(getattr(settings, 'STORE_LAT', 14.599512))
            store_lng = float(getattr(settings, 'STORE_LNG', 120.984222))

        # Save provided phone/address to user's profile so future orders and sidebar show correct contact info
        try:
            updated = False
            if phone and (not getattr(request.user, 'phone_number', '') or request.user.phone_number != phone):
                request.user.phone_number = phone
                updated = True
            if address and (not getattr(request.user, 'default_address', '') or request.user.default_address != address):
                request.user.default_address = address
                updated = True
            if updated:
                request.user.save()
        except Exception:
            # ignore profile save failures in dev
            pass

        order = Order.objects.create(
            buyer=request.user,
            delivery_address=address,
            delivery_fee=0,
            delivery_lat=lat_f,
            delivery_lng=lng_f,
            status='pending'
        )

        # Create order items and compute per-item delivery fees (based on seller coords)
        total_item_fees = 0.0
        R = 6371.0
        for it in items:
            seller = getattr(it['product'], 'seller', None)
            # determine seller coords, fallback to store coordinates
            s_lat = s_lng = None
            if seller is not None:
                try:
                    s_lat = float(getattr(seller, 'seller_lat'))
                    s_lng = float(getattr(seller, 'seller_lng'))
                except Exception:
                    s_lat = s_lng = None

            if lat_f is not None and lng_f is not None:
                if s_lat is not None and s_lng is not None:
                    phi1 = math.radians(s_lat)
                    phi2 = math.radians(lat_f)
                    dphi = math.radians(lat_f - s_lat)
                    dlambda = math.radians(lng_f - s_lng)
                else:
                    phi1 = math.radians(store_lat)
                    phi2 = math.radians(lat_f)
                    dphi = math.radians(lat_f - store_lat)
                    dlambda = math.radians(lng_f - store_lng)

                a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                distance_km = R * c
                item_fee = round(base_fee + (per_km * distance_km), 2)
            else:
                item_fee = round(base_fee, 2)

            total_item_fees += float(item_fee)
            OrderItem.objects.create(
                order=order,
                product=it['product'],
                quantity=it['quantity'],
                price=it['unit_price'],
                delivery_fee=item_fee
            )

        # persist the sum of per-item delivery fees on the order
        order.delivery_fee = round(total_item_fees, 2)
        order.save()

        # Clear buy_now or cart as appropriate
        if buy_now:
            request.session.pop('buy_now', None)
        else:
            request.session['cart'] = {}

        messages.success(request, f'🎉 Order {order.order_number} placed successfully! Track your delivery in My Account.')
        return redirect('order_detail', pk=order.pk)

    # GET request: render checkout form with items, subtotal, and prefilled user defaults
    initial_address = request.user.default_address if hasattr(request.user, 'default_address') else ''
    initial_phone = request.user.phone_number if hasattr(request.user, 'phone_number') else ''
    return render(request, 'checkout.html', {
        'items': items,
        'subtotal': subtotal,
        'initial_address': initial_address,
        'initial_phone': initial_phone,
        'buy_now': bool(buy_now),
        'STORE_LAT': getattr(settings, 'STORE_LAT', ''),
        'STORE_LNG': getattr(settings, 'STORE_LNG', ''),
        'DELIVERY_BASE_FEE': getattr(settings, 'DELIVERY_BASE_FEE', ''),
        'DELIVERY_PER_KM': getattr(settings, 'DELIVERY_PER_KM', ''),
    })

def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items = order.items.all()
    subtotal = sum(item.total_price for item in items)
    fees_total = sum(float(getattr(item, 'delivery_fee', 0)) for item in items)
    return render(request, 'order_detail.html', {'order': order, 'subtotal': subtotal, 'fees_total': fees_total})


@login_required
def buyer_dashboard(request):
    orders = request.user.orders.order_by('-created_at')
    pending = orders.filter(status='pending')
    context = {'orders': orders, 'pending': pending}
    return render(request, 'buyer_dashboard.html', context)


def _is_seller(user):
    return user.is_authenticated and user.is_seller


def seller_store(request, pk):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    seller = get_object_or_404(User, pk=pk)
    products = Product.objects.filter(seller=seller).order_by('-created_at')
    return render(request, 'seller_store.html', {'seller': seller, 'products': products})


@user_passes_test(_is_seller)
def seller_dashboard(request):
    products = Product.objects.filter(seller=request.user)
    # orders that include this seller's products
    orders = Order.objects.filter(items__product__seller=request.user).distinct().order_by('-created_at')
    pending = orders.filter(status='pending')

    # Compute bulk discounted prices for display on seller dashboard only
    for p in products:
        try:
            price = float(p.price)
        except Exception:
            price = 0.0
        # 5+ pieces -> 5% off, 10+ pieces -> 10% off
        p.bulk_price_5 = price * 0.95
        p.bulk_price_10 = price * 0.90

    return render(request, 'seller_dashboard.html', {'products': products, 'orders': orders, 'pending': pending})


@user_passes_test(_is_seller)
@require_http_methods(['GET', 'POST'])
def seller_add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(seller=request.user)
            messages.success(request, 'Product added')
            return redirect('seller_dashboard')
    else:
        form = ProductForm()
    return render(request, 'seller_product_form.html', {'form': form, 'action': 'Add Product'})


@user_passes_test(_is_seller)
@require_http_methods(['GET', 'POST'])
def seller_edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save(seller=request.user)
            messages.success(request, 'Product updated')
            return redirect('seller_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'seller_product_form.html', {'form': form, 'action': 'Edit Product', 'product': product})


@user_passes_test(_is_seller)
@require_http_methods(['GET', 'POST'])
def seller_delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted')
        return redirect('seller_dashboard')
    return render(request, 'seller_confirm_delete.html', {'product': product})


@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    from django.db.models import Sum
    
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    from django.contrib.auth import get_user_model
    User = get_user_model()
    total_users = User.objects.count()
    
    # Calculate total sales (sum of all order totals)
    total_sales = 0
    for order in Order.objects.all():
        total_sales += float(order.total)
    
    pending_orders = Order.objects.filter(status='pending').count()
    
    return render(request, 'admin_dashboard.html', {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'total_sales': total_sales,
        'pending_orders': pending_orders,
    })


@user_passes_test(_is_seller)
def seller_update_order_status(request, pk):
    # seller may update status for orders that include their products
    order = get_object_or_404(Order, pk=pk)
    allowed = order.items.filter(product__seller=request.user).exists()
    if not allowed:
        messages.error(request, 'Not authorized')
        return redirect('seller_dashboard')
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.ORDER_STATUS).keys():
            order.status = new_status
            order.save()
            messages.success(request, f'Order {order.order_number} updated to {new_status}')
    # redirect with cache-busting to ensure fresh page load
    response = redirect('seller_dashboard')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


