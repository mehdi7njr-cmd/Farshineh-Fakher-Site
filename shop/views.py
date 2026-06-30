import random
from django.shortcuts import render, get_object_or_404, redirect
from .models import Category, Product, Order, OrderItem, ProductSize, HeroSlider, Brand, ProductFeature, Comment
from django.db.models import Prefetch
from django.db.models import Min, F, IntegerField, ExpressionWrapper, Q, Subquery, OuterRef
from .cart import Cart
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from django.conf import settings
from django.conf import settings
from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from .models import Favorite

def home_page(request):
    sliders = HeroSlider.objects.all().order_by('order', '-created')
    active_products = Product.objects.all()
    
    # دسته‌بندی‌های فعال رو میگیریم و محصولاتشون رو هم بهشون می‌چسبونیم (برای سرعت بیشتر دیتابیس)
    categories = Category.objects.filter(show_in_homepage=True).order_by('order').prefetch_related(
        Prefetch('products', queryset=active_products)
    )

    context = {
        'categories': categories,
        'sliders': sliders,
    }
    return render(request, 'index.html', context)

def filter_products(request, products):
    if request.GET.get('in_stock') == 'true':
        products = products.filter(is_active=True, sizes__stock__gt=0).distinct()

    # 2. فیلتر برندها
    brand_ids = request.GET.getlist('brand')
    if brand_ids:
        products = products.filter(brand__id__in=brand_ids)

    # 3. محاسبه قیمت برای فیلتر و مرتب‌سازی
    size_discounted_price = ExpressionWrapper(
        F('price') - (F('price') * F('discount_percent') / 100),
        output_field=IntegerField()
    )

    # یک زیرکوئری مینویسیم که فقط و فقط قیمت سایز اول هر فرش رو بکشه بیرون
    first_size_price_subquery = ProductSize.objects.filter(
        product=OuterRef('pk')
    ).annotate(
        calculated_price=size_discounted_price
    ).values('calculated_price')[:1]

    # حالا این قیمت رو به فرش میچسبونیم تا مرتب‌سازی و فیلتر دقیقاً بر اساس این عدد انجام بشه
    products = products.annotate(effective_price=Subquery(first_size_price_subquery))
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price and min_price.isdigit():
        products = products.filter(effective_price__gte=int(min_price))
    if max_price and max_price.isdigit():
        products = products.filter(effective_price__lte=int(max_price))

    # 4. فیلتر ویژگی‌های پویا
    for key, values in request.GET.lists():
        if key.startswith('f_'):
            feature_name = key.replace('f_', '')
            products = products.filter(
                features__feature_key=feature_name,
                features__feature_value__in=values
            )

    # 5. مرتب‌سازی (Sort)
    sort = request.GET.get('sort', 'newest')
    if sort == 'cheapest':
        products = products.order_by('effective_price', '-created')
    elif sort == 'expensive':
        products = products.order_by('-effective_price', '-created')
    elif sort == 'popular':
        products = products.order_by('-views_count', '-created')
    elif sort == 'bestseller':
        products = products.order_by('-sales_count', '-created')
    else: # newest
        products = products.order_by('-created')

    return products.distinct()

def get_filter_data(products):
    """ استخراج برندها و ویژگی‌های مشخص فقط برای همین لیست محصولات """
    brands = Brand.objects.filter(product__in=products).distinct()
    
    # تغییر مهم: اینجا به دیتابیس گفتیم فقط ویژگی‌ای رو بیار که اسمش دقیقا "جنس" باشه
    all_features = ProductFeature.objects.filter(
        product__in=products, 
        feature_key='جنس'  # <--- این شرط اضافه شد
    ).values('feature_key', 'feature_value').distinct()
    
    features_dict = {}
    for f in all_features:
        k, v = f['feature_key'], f['feature_value']
        if k not in features_dict:
            features_dict[k] = set()
        features_dict[k].add(v)
        
    return brands, features_dict

def category_detail(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    base_products = category.products.all()
    
    # گرفتن دیتای فیلترها (قبل از اعمال فیلتر) تا سایدبار کامل لود بشه
    brands, features_dict = get_filter_data(base_products)
    
    # اعمال فیلترها
    products_list = filter_products(request, base_products)
    
    paginator = Paginator(products_list, 20)
    page = request.GET.get('page')
    try: products = paginator.page(page)
    except PageNotAnInteger: products = paginator.page(1)
    except EmptyPage: products = paginator.page(paginator.num_pages)

    context = {
        'category': category,
        'products': products,
        'categories': Category.objects.all(),
        'brands': brands,
        'features_dict': features_dict,
    }
    return render(request, 'category_detail.html', context)


def all_products(request):
    base_products = Product.objects.all()
    
    brands, features_dict = get_filter_data(base_products)
    products_list = filter_products(request, base_products)
    
    paginator = Paginator(products_list, 20)
    page = request.GET.get('page')
    try: products = paginator.page(page)
    except PageNotAnInteger: products = paginator.page(1)
    except EmptyPage: products = paginator.page(paginator.num_pages)

    context = {
        'products': products,
        'categories': Category.objects.all(),
        'page_title': 'همه محصولات فروشگاه',
        'brands': brands,
        'features_dict': features_dict,
    }
    return render(request, 'category_detail.html', context)

from .models import Brand

def brand_detail(request, brand_slug):
    # برند مورد نظر رو پیدا میکنیم
    brand = get_object_or_404(Brand, slug=brand_slug)
    
    # فقط محصولات فعالِ همین برند رو میگیریم
    base_products = Product.objects.filter(brand=brand)
    
    # گرفتن دیتای فیلترها (برای سایدبار سمت راست)
    brands, features_dict = get_filter_data(base_products)
    
    # اعمال فیلترهایی که کاربر ممکنه از سایدبار انتخاب کنه
    products_list = filter_products(request, base_products)
    
    # صفحه‌بندی
    paginator = Paginator(products_list, 20)
    page = request.GET.get('page')
    try: products = paginator.page(page)
    except PageNotAnInteger: products = paginator.page(1)
    except EmptyPage: products = paginator.page(paginator.num_pages)

    context = {
        'products': products,
        'categories': Category.objects.all(),
        'page_title': f'محصولات برند {brand.name}', # عنوان بالای صفحه
        'brands': brands,
        'features_dict': features_dict,
    }
    # باز هم از همون قالب یکپارچه استفاده میکنیم
    return render(request, 'category_detail.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.views_count += 1
    product.save()
    if request.method == 'POST' and request.user.is_authenticated:
        comment_body = request.POST.get('body')
        if comment_body:
            Comment.objects.create(product=product, user=request.user, body=comment_body)
            messages.success(request, 'نظر شما با موفقیت ثبت شد و پس از تایید مدیریت نمایش داده می‌شود.')
            return redirect('shop:product_detail', product_id=product.id)
    comments = product.comments.filter(is_active=True)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:6]
    categories = Category.objects.all()

    context = {
        'product': product,
        'related_products': related_products,
        'comments': comments,
        'categories': categories
    }
    return render(request, 'product_detail.html', context)

def search_products(request):
    # کلمه‌ای که کاربر سرچ کرده رو میگیریم
    query = request.GET.get('q', '')
    
    # اول همه محصولات فعال رو میگیریم
    products = Product.objects.all()
    
    # اگر چیزی سرچ کرده بود، فیلترش میکنیم
    if query:
        # icontains یعنی: شامل این کلمه باشه (حساس به حروف بزرگ و کوچک هم نیست)
        products = products.filter(
            Q(title__icontains=query) | Q(code__icontains=query)
        )
        
    categories = Category.objects.all()

    context = {
        'products': products,
        'query': query,
        'categories': categories,
    }
    return render(request, 'search.html', context)

def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    # جلوگیری از خرید محصولی که تیکش برداشته شده
    if not product.is_active:
        messages.error(request, 'این محصول در حال حاضر قابل سفارش نیست.')
        return redirect('shop:product_detail', product_id=product.id)

    size_id = request.POST.get('size_id')
    quantity = int(request.POST.get('quantity', 1))
    
    if not size_id:
        messages.error(request, 'لطفا یک سایز را انتخاب کنید.')
        return redirect('shop:product_detail', product_id=product.id)

    size = get_object_or_404(ProductSize, id=size_id)
    stock_to_check = size.stock

    cart_key = f"{product.id}_{size.id}"
    current_qty = cart.cart.get(cart_key, {}).get('quantity', 0)
    
    if stock_to_check > 0:
        if (current_qty + quantity) <= stock_to_check:
            cart.add(product=product, quantity=quantity, size=size)
            messages.success(request, 'محصول به سبد خرید اضافه شد.')
        else:
            messages.error(request, 'موجودی انبار برای این تعداد کافی نیست!')
    else:
        messages.error(request, 'این سایز ناموجود است.')
        
    return redirect('shop:product_detail', product_id=product.id)

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart_detail.html', {'cart': cart})

def cart_remove(request, unique_key):
    cart = Cart(request)
    cart.remove(unique_key)
    return redirect('shop:cart_detail')

def cart_update(request, unique_key, action):
    cart = Cart(request)
    
    # اگر کلید در سبد خرید نبود، هیچ کاری نکن
    if unique_key not in cart.cart:
        return redirect('shop:cart_detail')
        
    item = cart.cart[unique_key]
    current_qty = int(item['quantity'])
    
    # ما کلید سبد خرید رو قبلا به شکل productid_sizeid ساخته بودیم
    # پس باید جداشون کنیم تا بفهمیم کدوم سایز بوده که موجودیش رو چک کنیم
    parts = unique_key.split('_')
    product_id = parts[0]
    size_id = parts[1] if len(parts) > 1 else None
    
    # پیدا کردن موجودی سایز
    max_stock = 0
    if size_id:
        size = get_object_or_404(ProductSize, id=size_id)
        max_stock = size.stock

    if action == 'increase':
        if current_qty < max_stock:
            cart.cart[unique_key]['quantity'] += 1
            cart.save()
        else:
            messages.error(request, 'موجودی انبار برای این کالا کافی نیست!')
            
    elif action == 'decrease':
        if current_qty > 1:
            cart.cart[unique_key]['quantity'] -= 1
            cart.save()
        else:
            # اگر تعداد 1 بود و روی منفی زد، محصول رو از سبد پاک میکنه
            cart.remove(unique_key)
            messages.success(request, 'محصول از سبد خرید شما حذف شد.')

    return redirect('shop:cart_detail')

# تابع لاگین (ورود)
# ================= تابع ورود (با موبایل) =================
def send_otp_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        
        # تولید کد ۵ رقمی
        otp_code = random.randint(10000, 99999)
        
        # ذخیره موقت در حافظه سشن سرور
        request.session['temp_phone'] = phone
        request.session['otp_code'] = str(otp_code)
        
        # ================= ارسال پیامک با کاوه‌نگار =================
        try:
            # چاپ در کنسول برای تست زمان برنامه‌نویسی
            print("\n" + "="*40)
            print(f"کد تایید (مخصوص تست برنامه‌نویس): {otp_code}")
            print("="*40 + "\n")

            url = 'https://rest.payamak-panel.com/api/SendSMS/BaseServiceNumber'
            data = {
                'username': settings.MELIPAYAMAK_USERNAME,
                'password': settings.MELIPAYAMAK_PASSWORD,
                'text': str(otp_code),  # متغیری که در الگو قرار می‌گیرد
                'to': phone,
                'bodyId': settings.MELIPAYAMAK_BODY_ID
            }
            
            # ارسال درخواست به سرور ملی‌پیامک
            response = requests.post(url, json=data)
            result = response.json()
            
            # بررسی موفقیت آمیز بودن ارسال
            # ملی‌پیامک اگر موفق باشه RetStatus رو برابر 1 برمیگردونه
            if result.get('RetStatus') == 1:
                print("پیامک با موفقیت ارسال شد. شناسه پیگیری:", result.get('Value'))
            else:
                print("خطا از سمت ملی‌پیامک:", result.get('StrRetStatus'))
                
        except Exception as e: 
            print("خطای ارتباط با سرور ملی‌پیامک:", e)
        # =========================================================
        
        return redirect('shop:verify_otp')
        
    return render(request, 'login.html')

# ================= 2. تایید کد و ورود کاربر =================
def verify_otp_view(request):
    # اگر کسی بدون زدن شماره موبایل مستقیم اومد تو این صفحه، برگرده به صفحه قبل
    if 'temp_phone' not in request.session:
        return redirect('shop:login')

    if request.method == 'POST':
        user_code = request.POST.get('otp_code')
        real_code = request.session.get('otp_code')
        phone = request.session.get('temp_phone')
        
        if user_code == real_code:
            # گت میکنیم، اگر کاربری با این موبایل نبود یکی جدید میسازیمش
            user, created = User.objects.get_or_create(username=phone)
            
            # ورود کاربر به سایت
            login(request, user)
            
            # پاک کردن سشن‌های موقت برای امنیت
            del request.session['otp_code']
            del request.session['temp_phone']
            
            if created:
                messages.success(request, 'به فرشینه فاخر خوش آمدید، حساب شما ساخته شد.')
            else:
                messages.success(request, 'با موفقیت وارد شدید.')
                
            return redirect('shop:home')
        else:
            messages.error(request, 'کد وارد شده اشتباه است!')
            
    return render(request, 'verify_otp.html')

# ================= 3. خروج =================
def logout_view(request):
    logout(request)
    messages.success(request, 'از حساب کاربری خود خارج شدید.')
    return redirect('shop:home')

@login_required(login_url='shop:login')
def checkout_view(request):
    cart = Cart(request)
    if len(cart) == 0: return redirect('shop:cart_detail')

    profile = request.user.profile
    
    if request.method == 'POST':
        f_name = request.POST.get('first_name')
        l_name = request.POST.get('last_name')
        n_code = request.POST.get('national_code')
        mob = request.POST.get('mobile')
        addr = request.POST.get('address')
        p_code = request.POST.get('postal_code')
        
        # === روش ارسال و هزینه ثابت شدند ===
        s_method = 'tipax'
        s_cost = 0  # صفر است چون پس‌کرایه است

        request.user.first_name = f_name
        request.user.last_name = l_name
        request.user.save()

        profile.national_code = n_code
        profile.address = addr
        profile.postal_code = p_code
        profile.save()

        # === ذخیره سفارش در دیتابیس ===
        order = Order.objects.create(
            user=request.user, first_name=f_name, last_name=l_name,
            national_code=n_code, mobile=mob, address=addr, postal_code=p_code,
            shipping_method=s_method, shipping_cost=s_cost
        )
        for item in cart:
            OrderItem.objects.create(order=order, product=item['product'], price=item['price'], quantity=item['quantity'])

        cart.cart.clear()
        cart.save()
        request.session['order_id'] = order.id
        
        if order.get_total_cost() >= 10000000:
            return redirect('shop:bank_transfer')
        else:
            return redirect('shop:payment_request')

    context = {
        'profile': profile,
        'cart': cart,
    }
    return render(request, 'checkout.html', context)

@login_required(login_url='shop:login')
def bank_transfer(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('shop:home')
        
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'bank_transfer.html', {'order': order})

@login_required(login_url='shop:login')
def payment_request(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('shop:cart_detail')
        
    order = get_object_or_404(Order, id=order_id)
    
    # بیت‌پی مبلغ رو به ریال میخواد
    total_price = order.get_total_cost()
    amount_in_rial = total_price * 10
    
    # آدرس بازگشت (کال‌بک) - حتما https باشه
    CALLBACK_URL = 'https://farshinefakher.ir/payment/verify'

    # آدرس جدید API طبق مستندات
    url = 'https://bitpay.ir/payment/gateway-send'
    
    data = {
        'api': settings.BITPAY_API_KEY.strip(),  # حذف فاصله‌های اضافی احتمالی
        'amount': str(amount_in_rial),           # تبدیل قطعی به رشته
        'redirect': CALLBACK_URL,
        'factorId': str(order.id),               # تبدیل قطعی به رشته
        'name': f"{order.first_name} {order.last_name}",
        'email': 'info@farshinefakher.ir',
        'description': f"پرداخت سفارش شماره {order.id}"
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        
        # خروجی باید یک عدد (شناسه پرداخت) باشد
        result = response.text
        
        # طبق مستندات، اگر عدد بزرگتر از 0 بود، ریدایرکت میکنیم
        if result.lstrip('-').isdigit() and int(result) > 0:
            # فرمت جدید ریدایرکت طبق مستندات (کلمه get- در انتها اضافه شده است)
            return redirect(f'https://bitpay.ir/payment/gateway-{result}-get')
        else:
            return HttpResponse(f"خطا از سمت درگاه بیت‌پی. کد خطا: {result}")
            
    except Exception as e:
        return HttpResponse(f"خطای شبکه در ارتباط با سرور بیت‌پی: {e}")


# ================= 2. تایید پرداخت (بازگشت از بانک) =================

@csrf_exempt
def payment_verify(request):
    trans_id = request.POST.get('trans_id') or request.GET.get('trans_id')
    id_get = request.POST.get('id_get') or request.GET.get('id_get')
    
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('shop:home')
        
    order = get_object_or_404(Order, id=order_id)

    if trans_id and id_get:
        url = 'https://bitpay.ir/payment/gateway-result-second'
        data = {
            'api': settings.BITPAY_API_KEY.strip(),
            'trans_id': str(trans_id),
            'id_get': str(id_get),
            'json': 1
        }
        
        try:
            response = requests.post(url, data=data, timeout=15)
            print("پاسخ سرور بیت‌پی به درخواست تایید:", response.text)
            
            if not response.text:
                 return render(request, 'order_failed.html', {'order_id': order.id})
                 
            try:
                result_data = response.json()
            except ValueError:
                if response.text.strip() == '1':
                    result_data = {'status': 1}
                else:
                    return render(request, 'order_failed.html', {'order_id': order.id})
            
            # بررسی استاتوس پرداخت (1 یعنی موفق)
            if str(result_data.get('status')) == '1':
                if not order.is_paid:
                    order.is_paid = True
                    order.save()
                    
                    # آپدیت آمار فروش محصولات
                    for item in order.items.all():
                        product = item.product
                        product.sales_count += item.quantity
                        product.save()
                        
                    # خالی کردن سبد خرید
                    cart = Cart(request)
                    cart.cart.clear()
                    cart.save()
                        
                card_num = result_data.get('cardNum', 'نامشخص')
                return render(request, 'order_success.html', {
                    'order_id': order.id, 
                    'ref_id': trans_id,
                    'card_num': card_num 
                })
            
            else:
                return render(request, 'order_failed.html', {'order_id': order.id})
                
        except Exception:
            return render(request, 'order_failed.html', {'order_id': order.id})
             
    return render(request, 'order_failed.html', {'order_id': order.id})


@login_required(login_url='shop:login')
def user_profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created')
    favorites = Favorite.objects.filter(user=request.user).select_related('product')

    context = {
        'orders': orders,
        'favorites': favorites
    }
    return render(request, 'profile.html', context)

# ================= نمایش جزئیات یک فاکتور =================
@login_required(login_url='shop:login')
def order_detail(request, order_id):
    # چک میکنه که این فاکتور حتما مالِ همین کاربری باشه که الان لاگین کرده
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})

# ================= صفحه پیگیری سفارش =================
def track_order(request):
    order = None
    error_msg = None
    
    if request.method == 'GET' and 'order_id' in request.GET:
        order_id = request.GET.get('order_id')
        try:
            # اگر شماره سفارش و موبایل درست بود پیداش میکنه
            order = Order.objects.get(id=order_id)
            # برای امنیت، چک میکنه که کسی فاکتور بقیه رو نبینه
            if request.user.is_authenticated and order.user == request.user:
                pass # اگر مال خودش بود اوکیه
            else:
                error_msg = 'شما دسترسی به این سفارش را ندارید یا شماره سفارش اشتباه است.'
                order = None
        except Order.DoesNotExist:
            error_msg = 'سفارشی با این شماره یافت نشد.'
            
    return render(request, 'track_order.html', {'order': order, 'error_msg': error_msg})

def toggle_favorite(request, product_id):
    if not request.user.is_authenticated:
        # اگر کاربر لاگین نبود، به جاوااسکریپت میگیم بفرستش صفحه لاگین
        return JsonResponse({'status': 'login_required'})
        
    product = get_object_or_404(Product, id=product_id)
    
    # میگردیم ببینیم لایک کرده یا نه
    fav = Favorite.objects.filter(user=request.user, product=product).first()
    
    if fav:
        fav.delete() # اگر بود، پاکش کن (دیس‌لایک)
        return JsonResponse({'status': 'removed'})
    else:
        Favorite.objects.create(user=request.user, product=product) # اگر نبود، بسازش (لایک)
        return JsonResponse({'status': 'added'})
    
def custom_404(request, exception):
    return render(request, '404.html', status=404)