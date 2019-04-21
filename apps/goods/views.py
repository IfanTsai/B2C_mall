from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django_redis import get_redis_connection
from django.core.cache import cache
from apps.order.models import OrderGoods
from django.core.paginator import Paginator
from apps.goods.models import (
    GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU,
)

class IndexView(View):
    """
    首页视图
    """
    def get(self, request):
        # 尝试从缓存中获取数据
        context = cache.get('index_page_data')
        # 未获取到缓存
        #if context is None:
        # 获取商品种类信息
        goods_types = GoodsType.objects.all()

        # 获取轮播商品信息
        goods_banners = IndexGoodsBanner.objects.all().order_by('index')

        # 获取促销活动信息
        promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

        # 获取分类商品展示信息
        for goods_type in goods_types:
            image_banners = IndexTypeGoodsBanner.objects.filter(type=goods_type, display_type=1).order_by('index')
            title_banners = IndexTypeGoodsBanner.objects.filter(type=goods_type, display_type=0).order_by('index')

            # 动态给GoodsType对象增加属性，分别表示首页分类商品的图片展示信息和文字展示信息
            goods_type.image_banners = image_banners
            goods_type.title_banners = title_banners

        context = {
            'goods_types': goods_types,
            'goods_banners': goods_banners,
            'promotion_banners': promotion_banners,
        }

        # 设置缓存      key            value  缓存时间
        #cache.set('index_page_data', context, 3600)

        # 判断用户是否登陆，来决定是否获取用户购物车中商品的数量
        user = request.user
        cart_goods_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_goods_count = conn.hlen(cart_key)

        context.update({'cart_goods_count': cart_goods_count})

        return render(request, 'index.html', context)

class DetailView(View):
    """
    商品详情页视图
    """
    def get(self, request, goods_id):
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        # 商品不存在
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 获取商品分类信息
        goods_types = GoodsType.objects.all()

        # 获取商品评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取同一个SPU的其他规格商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 判断用户是否登陆，来决定是否获取用户购物车中商品的数量
        user = request.user
        cart_goods_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_goods_count = conn.hlen(cart_key)

            # 添加用户浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            # 移除该商品的浏览记录
            conn.lrem(history_key, 0, goods_id)
            # 将该商品插入redis list左侧
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的5条记录
            conn.ltrim(history_key, 0, 4)

        context = {
            'sku': sku,
            'goods_types': goods_types,
            'sku_orders': sku_orders,
            'new_skus': new_skus,
            'cart_goods_count': cart_goods_count,
            'same_spu_skus': same_spu_skus,
        }

        return render(request, 'detail.html', context)

class ListView(View):
    """
    列表页视图
    """
    def get(self, request, type_id, page):

        # 获取种类信息
        try:
            goods_type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 获取商品分类信息
        goods_types = GoodsType.objects.all()

        # 获取排序方式
        sort_type = request.GET.get('sort', 'default')
        sort = {
            'default': '-id',
            'price': 'price',
            'hot': '-sales',
        }.get(sort_type, '-id')

        # 获取分类商品信息
        skus = GoodsSKU.objects.filter(type=goods_type).order_by(sort)

        # 对数据进行分页
        paginator = Paginator(skus, 1)

        try:
            page = int(page)
        except Exception:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        skus_page = paginator.page(page)

        # 页码控制，页面上最多显示5个页码
        # 获取总页数
        num_pages = paginator.num_pages
        # 总页数小于5，页面上显示所有页码
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        # 下面是总页数大于5页的情况
        # 当前页是前三页，显示前5页
        elif page <= 3:
            pages = range(1, 6)
        # 当前页是后三页，显示后5页
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        # 其他情况，显示当前页的前2页和当前页的后2页
        else:
            pages = range(page - 2, page + 3)


        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=goods_type).order_by('-create_time')[:2]

        # 判断用户是否登陆，来决定是否获取用户购物车中商品的数量
        user = request.user
        cart_goods_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_goods_count = conn.hlen(cart_key)

        context = {
            'goods_type': goods_type,
            'goods_types': goods_types,
            'skus_page': skus_page,
            'pages': pages,
            'new_skus': new_skus,
            'cart_goods_count': cart_goods_count,
            'sort': sort_type,
        }

        return render(request, 'list.html', context)
