from .cart import Cart
from .models import Category
from .models import Favorite

def cart_processor(request):
    return {'cart': Cart(request)}

def category_processor(request):
    all_categories = Category.objects.filter(is_active=True).order_by('order')
    
    parent_categories = all_categories.filter(parent__isnull=True).prefetch_related('children')
    
    return {
        'all_categories': all_categories, # برای منوی افقی بالای سایت
        'parent_categories': parent_categories # برای مگامنوی کشویی
    }
def user_favorites(request):
    if request.user.is_authenticated:
        # آیدی تمام محصولاتی که این کاربر لایک کرده رو میگیریم
        favs = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        return {'user_favorites': list(favs)}
    return {'user_favorites': []}
