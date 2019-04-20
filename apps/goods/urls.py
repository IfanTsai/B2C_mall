from django.conf.urls import url
from apps.goods.views import IndexView, DetailView

urlpatterns = [
    url("^index$", IndexView.as_view(), name='index'),
    url("^goods/(?P<goods_id>\d+)$", DetailView.as_view(), name='detail'),
]
