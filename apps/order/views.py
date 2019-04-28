from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from apps.goods.models import GoodsSKU
from apps.user.models import Address
from django_redis import get_redis_connection
from utils.mixin import LoginRequireMixin

class OrderPlaceView(LoginRequireMixin, View):
    """
    提交订单页面视图
    """
    def post(self, request):
        user = request.user
        # 获取提交参数
        sku_ids = request.POST.getlist('sku_ids')

        if not sku_ids:
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            amount = sku.price * int(count)
            # 动态给sku增加count属性，保存购买商品数量
            sku.count = count
            total_count += int(count)
            # 动态给sku增加amount属性，保存购买商品小计
            sku.amount = amount
            total_price += amount
            # 添加到skus列表中
            skus.append(sku)

        # TODO： 这里偷懒的将运费写死
        transit_price = 10
        # 实际付款
        total_pay = total_price + transit_price
        # 收件地址
        addrs = Address.objects.filter(user=user)
        # 将商品id组成一个以逗号分割的字符串
        sku_ids = ','.join(sku_ids)

        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'sku_ids': sku_ids,
        }

        return render(request, 'place_order.html', context)