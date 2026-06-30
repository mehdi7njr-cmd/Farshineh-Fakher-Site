from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # اتصال مسیرهای اپلیکیشن فروشگاه
    path('', include('shop.urls')), 
]

# این دو خط برای اینه که در حالت توسعه (Development) بتونیم عکس‌های محصولات رو ببینیم
if settings.DEBUG or not settings.DEBUG: 
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'shop.views.custom_404'