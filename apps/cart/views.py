from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from utils.mixin import LoginRequireMixin

class CartAddView(View):
    """
    添加购物车视图
    """
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': -1, 'error': '用户未登录'})

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({'res': -2, 'error': '数据不完整'})

        try:
            count = int(count)
        except Exception:
            return JsonResponse({'res': -3, 'error': '商品数量错误'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': -4, 'error': '商品不存在'})


        # 尝试获取redis中商品的值
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)

        if count > sku.stock:
            return JsonResponse({'res': -5, 'error': '商品库存不足'})

        conn.hset(cart_key, sku_id, count)

        return JsonResponse({'res': 1, 'message': '添加成功', 'count': count})

class CartInfoView(LoginRequireMixin, View):
    """
    购物车页面视图
    """
    def get(self, request):
        user = request.user

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # dict{商品id: 数量}
        cart_dict = conn.hgetall(cart_key)

        skus = []
        total_count = 0
        total_price = 0
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            # 给sku动态增加count属性  保存商品数量
            sku.count = count
            # 给sku动态增加amount属性 保存该商品总价
            sku.amount = sku.price * int(count)

            total_count += int(sku.count)
            total_price += sku.amount

            skus.append(sku)

        context = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus,
        }

        return render(request, 'cart.html', context)