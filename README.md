Market - Construction Materials Marketplace (MVP)

Overview
- Django-based marketplace for construction materials with buyer/seller roles, product management, cart, checkout, orders, and admin tools.

Features included in this scaffold:
- Custom user model with seller/buyer roles
- Product categories, products, multiple images
- Session-based shopping cart
- Checkout flow that creates orders with statuses
- Django admin enabled for marketplace management
- Basic Bootstrap templates for browsing, product pages, cart, checkout
- Console email backend for development (password reset / notifications)
- Stripe integration placeholder

Quick start (Windows / PowerShell)
1. Create and activate virtualenv
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```
2. Install deps
```powershell
pip install -r requirements.txt
```
3. Apply migrations and create superuser
```powershell
python manage.py migrate
python manage.py createsuperuser
```
4. Run development server
```powershell
python manage.py runserver
```
5. Open `http://127.0.0.1:8000/` in your browser.

Notes
- Media files (product images) are stored in `media/` during development.
- Payment gateways: Stripe is included as a placeholder. Replace with PayMongo integration if needed.
- Email: development uses console backend; configure SMTP in `market/settings.py` for production.

Next steps I can do for you:
- Add PayMongo integration (GCash/Maya)
- Implement advanced search & filters with Elasticsearch or PostgreSQL full-text
- Add seller payout flows and commission calculation
- Add unit tests and CI

If you'd like, I can now run migrations and create a superuser in your environment.