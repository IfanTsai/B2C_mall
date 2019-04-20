from django.contrib import admin
from celery_tasks.tasks import generate_static_index_html
from django.core.cache import cache
from apps.goods.models import (
   GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
)

class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """
        新增或更新表中数据时会被调用
        :param request:
        :param obj:
        :param form:
        :param change:
        :return:
        """
        super().save_model(request, obj, form, change)
        # 让celery重新生成首页静态页面
        generate_static_index_html.delay()
        # 清除首页缓存数据
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """
        删除表中数据时会被调用
        :param request:
        :param obj:
        :return:
        """
        super().delete_model(request, obj)
        # 让celery重新生成首页静态页面
        generate_static_index_html.delay()
        # 清除首页缓存数据
        cache.delete('index_page_data')


admin.site.register(GoodsType)
admin.site.register(IndexGoodsBanner)
admin.site.register(IndexPromotionBanner)
admin.site.register(IndexTypeGoodsBanner)
