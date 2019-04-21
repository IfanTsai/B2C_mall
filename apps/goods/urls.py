from django.conf.urls import url
from apps.goods.views import IndexView, DetailView, ListView

urlpatterns = [
    url("^index$", IndexView.as_view(), name='index'),
    url("^goods/(?P<goods_id>\d+)$", DetailView.as_view(), name='detail'),
    url("^list/(?P<type_id>\d+)/(?P<page>\d+)$", ListView.as_view(), name='list'),
]
