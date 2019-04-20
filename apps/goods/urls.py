from django.conf.urls import url
from apps.goods.views import IndexView

urlpatterns = [
    url("^index$", IndexView.as_view(), name='index'),
]
