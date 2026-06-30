from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random


# ================= مدل دسته‌بندی =================
class Category(models.Model):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='دسته اصلی (پدر)')
    name = models.CharField(max_length=100, verbose_name='نام دسته‌بندی')
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True, verbose_name='آدرس لینک (Slug)')
    
    # فیلدهای جدید برای کنترل نمایش
    show_in_menu = models.BooleanField(default=False, verbose_name='نمایش در منوی بالای سایت')
    show_in_homepage = models.BooleanField(default=False, verbose_name='ساخت اسلایدر در صفحه اصلی')
    order = models.PositiveIntegerField(default=1, verbose_name='ترتیب نمایش (۱ بالاترین)')
    
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
        ordering = ['order']

    def __str__(self):
        # این کد تو پنل ادمین نشون میده که این دسته زیرشاخه کدوم دسته‌ست
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name
        
    def get_absolute_url(self):
        return reverse('shop:category_detail', args=[self.slug])
    
class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام برند')
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)

    class Meta:
        verbose_name = 'برند'
        verbose_name_plural = 'برندها'

    def __str__(self):
        return self.name

    # این تابع اضافه شد
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('shop:brand_detail', args=[self.slug])
# ================= پروفایل دائمی کاربر =================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    national_code = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
# ================= مدل محصول =================
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='دسته‌بندی')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='برند')
    title = models.CharField(max_length=200, verbose_name='عنوان محصول')
    code = models.CharField(max_length=50, verbose_name='کد محصول')
    image = models.ImageField(upload_to='products/%Y/%m/', verbose_name='عکس محصول')
    is_active = models.BooleanField(default=True, verbose_name='موجود/ناموجود')
    created = models.DateTimeField(auto_now_add=True)
    views_count = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    sales_count = models.PositiveIntegerField(default=0, verbose_name='تعداد فروش')
    description = models.TextField(blank=True, null=True, verbose_name='توضیحات کامل محصول')

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ['-created'] # محصولات جدیدتر اول نمایش داده میشن

    def __str__(self):
        return f"{self.title} - {self.code}"
    @property
    def first_size(self):
        return self.sizes.first()

    @property
    def discount_percent(self):
        if self.first_size:
            return self.first_size.discount_percent
        return 0

    def get_price_formatted(self):
        if self.first_size:
            return f"{self.first_size.price:,}"
        return "0"

    def get_discounted_price_formatted(self):
        if self.first_size:
            # اون اشتباه تایپی (دو تا نقطه) اینجا اصلاح شد
            return f"{self.first_size.get_discounted_price():,}"
        return "0"
        
    def get_discounted_price(self):
        if self.first_size:
            return self.first_size.get_discounted_price()
        return 0
    
    @property
    def is_available(self):
        # اگر تیک محصول برداشته شده باشه، کلاً ناموجوده
        if not self.is_active:
            return False
        # در غیر این صورت، چک میکنه آیا حداقل یکی از سایزهاش موجودی داره یا نه
        return any(size.stock > 0 for size in self.sizes.all())
    

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('shop:product_detail', args=[self.id])

class Order(models.Model):
    # این انتخاب‌ها رو اضافه کن
    SHIPPING_CHOICES = (
        ('tipax', 'تیپاکس (پس‌کرایه)'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    first_name = models.CharField(max_length=50, verbose_name='نام')
    last_name = models.CharField(max_length=50, verbose_name='نام خانوادگی')
    national_code = models.CharField(max_length=10, verbose_name='کد ملی')
    mobile = models.CharField(max_length=11, verbose_name='شماره موبایل')
    address = models.TextField(verbose_name='آدرس دقیق پستی')
    postal_code = models.CharField(max_length=10, verbose_name='کد پستی')

    # === این دو فیلد جدید اضافه شدند ===
    shipping_method = models.CharField(max_length=20, choices=SHIPPING_CHOICES, default='tipax', verbose_name='روش ارسال')
    shipping_cost = models.PositiveIntegerField(default=0, verbose_name='هزینه ارسال')
    # ==================================

    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت سفارش')
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده؟')
    
    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        ordering = ['-created']

    def __str__(self):
        return f"سفارش شماره {self.id} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.pk: 
            while True:
                # یک عدد تصادفی ۸ رقمی میسازه
                random_id = random.randint(10000000, 99999999)
                if not Order.objects.filter(id=random_id).exists():
                    self.id = random_id
                    break
        super().save(*args, **kwargs)
    
    def get_total_cost(self):
        # === اینجا هزینه ارسال به جمع کل اضافه شد ===
        items_cost = sum(item.price * item.quantity for item in self.items.all())
        return items_cost + self.shipping_cost

    def get_total_cost_formatted(self):
        return f"{self.get_total_cost():,}"



# ================= مدل آیتم‌های داخل یک سفارش =================
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='محصول')
    price = models.PositiveIntegerField(verbose_name='قیمت در زمان خرید')
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')

    def __str__(self):
        return str(self.id)
    
    # ================= مدل ابعاد و سایزهای محصول =================
class ProductSize(models.Model):
    product = models.ForeignKey(Product, related_name='sizes', on_delete=models.CASCADE, verbose_name='محصول')
    name = models.CharField(max_length=100, verbose_name='نام سایز (مثلا ۱۲ متری)')
    price = models.PositiveIntegerField(verbose_name='قیمت این سایز (تومان)')
    discount_percent = models.PositiveIntegerField(default=0, verbose_name='درصد تخفیف این سایز')
    stock = models.PositiveIntegerField(default=10, verbose_name='موجودی این سایز')

    def __str__(self):
        return f"{self.product.title} - {self.name}"

    def get_price_formatted(self):
        return f"{self.price:,}"
    def get_discounted_price(self):
        if self.discount_percent > 0:
            discount_amount = (self.price * self.discount_percent) / 100
            return int(self.price - discount_amount)
        return self.price
    
class ProductFeature(models.Model):
    product = models.ForeignKey(Product, related_name='features', on_delete=models.CASCADE)
    feature_key = models.CharField(max_length=100, verbose_name='نام ویژگی (مثلا جنس)')
    feature_value = models.CharField(max_length=255, verbose_name='مقدار (مثلا مخمل ترک)')
    show_in_top = models.BooleanField(default=False, verbose_name='نمایش در لیست کوتاه بالای صفحه')


    def __str__(self):
        return f"{self.feature_key}: {self.feature_value}"
    
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='کاربر')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='محصول')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'علاقه‌مندی'
        verbose_name_plural = 'علاقه‌مندی‌ها'
        # هر کاربر یک محصول رو فقط یکبار میتونه لایک کنه
        unique_together = ('user', 'product') 

    def __str__(self):
        return f"{self.user.username} - {self.product.title}"
    
class HeroSlider(models.Model):
    image = models.ImageField(
        upload_to='sliders/%Y/%m/',
        verbose_name='عکس بنر'
    )
    subtitle = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='متن کوچک بالای عنوان'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='عنوان اصلی'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='توضیحات'
    )
    button_text = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='متن دکمه'
    )
    button_link = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='لینک دکمه'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال؟'
    )
    order = models.PositiveIntegerField(
        default=1,
        verbose_name='ترتیب نمایش'
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'هیرو بنر'
        verbose_name_plural = 'هیرو بنرها'
        ordering = ['order', '-created']

    def __str__(self):
        return self.title
    
    # ================= گالری تصاویر محصول =================
class ProductGallery(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery', verbose_name='محصول')
    image = models.ImageField(upload_to='products/gallery/%Y/%m/', verbose_name='عکس')

    class Meta:
        verbose_name = 'عکس گالری'
        verbose_name_plural = 'گالری تصاویر'

    def __str__(self):
        return f"عکس برای {self.product.title}"

# ================= نظرات کاربران =================
class Comment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments', verbose_name='محصول')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر')
    body = models.TextField(verbose_name='متن نظر')
    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    is_active = models.BooleanField(default=False, verbose_name='تایید شده / نمایش داده شود؟')

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ['-created']

    def __str__(self):
        return f"نظر {self.user.username} روی {self.product.title}"