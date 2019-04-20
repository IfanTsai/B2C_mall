from django.shortcuts import render
from django.views.generic import View
from django_redis import get_redis_connection
from django.core.cache import cache
from apps.goods.models import (
   GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner,
)

class IndexView(View):
   """
   首页视图
   """
   def get(self, request):
      # 尝试从缓存中获取数据
      context = cache.get('index_page_data')
      # 未获取到缓存
      if context is None:
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
         cache.set('index_page_data', context, 3600)

      # 判断用户是否登陆，来决定是否获取用户购物车中商品的数量
      user = request.user
      cart_goods_count = 0
      if user.is_authenticated():
         conn = get_redis_connection('default')
         cart_key = 'cart_%d' % user.id
         cart_goods_count = conn.hlen(cart_key)

      context.update({'cart_goods_count': cart_goods_count})

      return render(request, 'index.html', context)