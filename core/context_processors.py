from django.db.models import Count

def sidebar_info(request):
    """Provide profile info and sidebar counts for templates.

    Returns:
      - sidebar_orders_count: number of orders where user is buyer
      - sidebar_sales_total: total sales amount for seller (sum of order totals containing their products)
      - sidebar_phone: user's default phone_number
      - sidebar_address: user's default_address
    """
    data = {
        'sidebar_orders_count': 0,
        'sidebar_sales_total': 0,
        'sidebar_phone': '',
        'sidebar_address': '',
    }

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return data

    try:
        # Lazy import models to avoid startup issues when migrations haven't been applied
        from .models import Order

        # Orders where the current user is the buyer
        data['sidebar_orders_count'] = user.orders.count()

        # If user is a seller, compute total sales amount from DELIVERED orders containing their products
        if getattr(user, 'is_seller', False):
            orders = Order.objects.filter(items__product__seller=user, status='delivered').distinct()
            total = sum(float(order.total) for order in orders)
            data['sidebar_sales_total'] = round(total, 2)

        # Profile quick info
        data['sidebar_phone'] = getattr(user, 'phone_number', '') or ''
        data['sidebar_address'] = getattr(user, 'default_address', '') or ''
    except Exception:
        # In dev environment (migrations pending) importing or querying DB might fail; fall back to safe defaults
        pass

    return data
