from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from apps.goods.models import GoodsSKU
from apps.user.models import Address
from apps.order.models import OrderInfo, OrderGoods
from django_redis import get_redis_connection
from utils.mixin import LoginRequireMixin
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from datetime import datetime
from alipay import AliPay
import os
import time

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

        # 这里偷懒的将运费写死
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

class OrderCommitView(View):
    """
    创建订单视图
    """
    # 用transaction.atomic装饰的函数里所有数据库操作都放在一个事务里
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': -1, 'error': '用户未登录'})

        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': -2, 'error': '数据不完整'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': -3, 'error': '非法的支付方式'})

        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': -4, 'error': '非法的地址'})

        # 订单id格式：年月日时分秒+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总价
        total_count = 0
        total_price = 0

        # 设置事务保存点
        save_id = transaction.savepoint()

        try:
            # 向order_info表中添加一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            # 用户的订单有几个商品，就需要在order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 乐观锁，尝试三次
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                        # 加上悲观锁   等效SQL语句：select * from goods_sku where id=sku_id for update;
                        # 当rollback或者commit后，自动释放锁
                        #sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                    except:
                        # 回滚到保存点
                        transaction.rollback(save_id)
                        return JsonResponse({'res': -5, 'error': '商品不存在'})

                    # 从redis中获取用户所需要购买的商品数量
                    count = conn.hget(cart_key, sku_id)

                    # 判断商品库存
                    if int(count) > sku.stock:
                        # 回滚到保存点
                        transaction.rollback(save_id)
                        return JsonResponse({'res': -6, 'error': '商品库存不足'})

                    # 更新商品库存和销量
                    # sku.stock -= int(count)
                    # sku.sales += int(count)
                    # sku.save()

                    orign_stock = sku.stock
                    new_stock = orign_stock - int(count)
                    new_sales = sku.sales + int(count)
                    # 乐观锁，等效SQL语句：
                    # update goods_sku set stock=new_stock, sales=new_sales where id=sku_id and stock=origin_stock;
                    # 返回受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orign_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        # 尝试到第三次还是失败的情况
                        if i == 2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': -7, 'error': '下单失败'})
                        continue

                    # order_goods表中加入记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # 累加计算订单商品总数和总价
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount

                    break

            # 更新订单信息表中的商品总数和总价
            order.total_count = total_count
            order.total_price = total_price
            order.save()

        except Exception:
            # 回滚到保存点
            transaction.rollback(save_id)
            return JsonResponse({'res': -7, 'error': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # 清除用户购物车中对应记录
        # *sku_ids: 将列表拆包
        conn.hdel(cart_key, *sku_ids)

        return JsonResponse({'res': 1, 'msg': '创建成功'})

class OrderPayView(View):
    """
    订单支付视图
    """
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': -1, 'error': '用户未登录'})

        order_id = request.POST.get('order_id')

        if not order_id:
            return JsonResponse({'res': -2, 'error': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': -3, 'error': '订单错误'})

        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()

        alipay = AliPay(
            appid="2016100100636673",
            # 默认回调url
            app_notify_url=None,
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            # RSA 或者 RSA2
            sign_type="RSA2",
            # 正式环境使用False，沙箱环境使用True
            debug=True,
        )

        subject = "超级商城%s" % order_id
        total_pay = order.total_price + order.transit_price
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject=subject,
            return_url=None,
            notify_url=None,
        )

        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 1, 'pay_url': pay_url})

class OrderCheckPayView(View):
    """
    查看订单支付结果视图
    """
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': -1, 'error': '用户未登录'})

        order_id = request.POST.get('order_id')

        if not order_id:
            return JsonResponse({'res': -2, 'error': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': -3, 'error': '订单错误'})

        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()

        alipay = AliPay(
            appid="2016100100636673",
            # 默认回调url
            app_notify_url=None,
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            # RSA 或者 RSA2
            sign_type="RSA2",
            # 正式环境使用False，沙箱环境使用True
            debug=True,
        )

        while True:
            # 调用支付宝的交易查询接口
            response = alipay.api_alipay_trade_query(order_id)
            code = response.get('code')
            if code == '10000':
                # 支付成功
                if response.get('trade_status') == 'TRADE_SUCCESS':
                    trade_no = response.get('trade_no')
                    order.trade_no = trade_no
                    order.order_status = 4
                    order.save()
                    return JsonResponse({'res': 1, 'message': '支付成功'})
                # 等待支付
                elif response.get('trade_status') == 'WAIT_BUYER_PAY':
                    time.sleep(5)
                # 支付失败
                else:
                    return JsonResponse({'res': -1, 'error': '支付失败'})
            # 业务处理失败，可能一会后就会成功
            elif code == '40004':
                time.sleep(5)

class OrderCommentView(View):
    """
    订单评论页面视图
    """
    def get(self, request, order_id):
        user = request.user

        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 根据订单状态获取订单状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品小计
            amount = order_sku.count * order_sku.price
            # 给order_sku增加amount属性 保存商品小计
            order_sku.amount = amount

        # 给order增加order_sku属性，保存订单商品信息
        order.order_skus = order_skus

        return render(request, 'order_comment.html', {'order': order})

    def post(self, request, order_id):
        user = request.user

        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i)  # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '')  # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5  # 已完成
        order.save()

        return redirect(reverse("user:order", kwargs={"page": 1}))



