import copy
from .models import Product

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    # اینجا size و quantity رو اضافه کردیم
    def add(self, product, quantity=1, size=None):
        cart_key = f"{product.id}_{size.id}" if size else str(product.id)
        
        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'product_id': product.id,
                'size_name': size.name if size else '',
                'quantity': int(quantity),
                'price': str(size.get_discounted_price()) if size else str(product.get_discounted_price())
            }
        else:
            self.cart[cart_key]['quantity'] += int(quantity)
            
        self.save()

    def save(self):
        self.session.modified = True

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def __iter__(self):
        product_ids = [item['product_id'] for item in self.cart.values() if 'product_id' in item]
        products = Product.objects.filter(id__in=product_ids)
        
        # کلید حل مشکل اینجاست! یک کپی کاملاً عمیق و جداگانه از سبد میگیریم
        cart = copy.deepcopy(self.cart)
        
        for key, item in list(cart.items()):
            if 'product_id' not in item:
                del self.cart[key] # از سبد اصلی پاکش میکنه
                self.save()
                continue
                
            # اطلاعات رو فقط به اون "کپی" میچسبونیم تا سبد اصلی دست‌نخورده بمونه
            item['product'] = products.get(id=item['product_id'])
            item['unique_key'] = key 
            
            item['total_price'] = int(item['price']) * item['quantity']
            item['price_formatted'] = f"{int(item['price']):,}"
            item['total_price_formatted'] = f"{item['total_price']:,}"
            yield item

    def get_total_price(self):
        return sum(int(item['price']) * item['quantity'] for item in self.cart.values())

    def get_total_price_formatted(self):
        return f"{self.get_total_price():,}"

    # برای حذف کردن به همون کلید یونیک نیاز داریم
    def remove(self, unique_key):
        if unique_key in self.cart:
            del self.cart[unique_key]
            self.save()