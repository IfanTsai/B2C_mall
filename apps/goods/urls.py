from django.conf.urls import url
from apps.goods.views import IndexView

urlpatterns = [
    url("^$", IndexView.as_view(), name='index'),
]
