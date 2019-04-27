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
        # 添加购物车按钮发起的是ajax请求，其处理都在后端进行处理，在后端不能进行页面的跳转，
        # 所以不能继承于LoginRequireMixin
        user = request.user
        if not user.is_authenticated():
            # 返回json数据给前端来跳转
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

        total_count = conn.hlen(cart_key)

        return JsonResponse({'res': 1, 'message': '添加成功', 'total_count': total_count})

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

class CartUpdateView(View):
    """
    购物车记录更新视图
    """
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            # 返回json数据给来前端来跳转
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


        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        if count > sku.stock:
            return JsonResponse({'res': -5, 'error': '商品库存不足'})

        # 更新redis中的购物车记录
        conn.hset(cart_key, sku_id, count)

        # 计算购物车中商品总数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res': 1, 'message': '更新成功', 'total_count': total_count})

class CartDeleteView(View):
    """
    购物车记录删除视图
    """
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': -1, 'error': '用户未登录'})

        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'res': -2, 'error': '商品id无效'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': -3, 'error': '商品不存在'})

        # 删除购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        conn.hdel(cart_key, sku_id)

        # 计算购物车中商品总数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({'res': 1, 'error': '删除成功', 'total_count': total_count})