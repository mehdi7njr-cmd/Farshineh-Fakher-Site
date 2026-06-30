from django.contrib import admin
from .models import Category, Product, Order, OrderItem, ProductSize, ProductFeature, Brand, HeroSlider, ProductGallery, Comment

# ================= دسته‌بندی‌ها =================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'show_in_menu', 'show_in_homepage', 'is_active')
    list_editable = ('order', 'show_in_menu', 'show_in_homepage', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

# ================= برندها =================
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ('name',)}

# ================= جداول زیرمجموعه محصول =================
class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1

class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 1

class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 1

# ================= اکشن کپی کردن محصول =================
@admin.action(description='کپی کردن محصولات انتخاب شده (همراه با سایزها و ویژگی‌ها)')
def duplicate_product(modeladmin, request, queryset):
    for product in queryset:
        original_sizes = list(product.sizes.all())
        original_features = list(product.features.all())
        
        product.pk = None 
        product._state.adding = True 
        product.title = product.title + " (کپی)" 
        product.code = product.code + "-COPY" 
        product.is_active = False 
        product.save() 
        
        for size in original_sizes:
            size.pk = None
            size.product = product
            size.save()
            
        for feature in original_features:
            feature.pk = None
            feature.product = product
            feature.save()
            
    modeladmin.message_user(request, f"تعداد {queryset.count()} محصول با تمام ویژگی‌ها و سایزها با موفقیت کپی شدند.")

# ================= مدیریت محصولات اصلی =================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'category', 'discount_percent', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'code')
    list_editable = ('is_active',)
    
    inlines = [ProductSizeInline, ProductFeatureInline, ProductGalleryInline]
    actions = [duplicate_product]

    class Media:
        js = ('admin_custom.js',)

# ================= سفارشات =================
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created', 'is_paid']
    list_filter = ['is_paid', 'created']
    inlines = [OrderItemInline]

# ================= هیرو بنر (اسلایدر اصلی) =================
@admin.register(HeroSlider)
class HeroSliderAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'subtitle', 'description')

# ================= مدیریت نظرات کاربران =================
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created', 'is_active')
    list_filter = ('is_active', 'created')
    list_editable = ('is_active',)