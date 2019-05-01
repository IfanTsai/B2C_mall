from django.conf.urls import url
from apps.order.views import (
    OrderPlaceView, OrderCommitView, OrderPayView, OrderCheckPayView, OrderCommentView
)

urlpatterns = [
    url(r'^place$', OrderPlaceView.as_view(), name='place'),
    url(r'^commit$', OrderCommitView.as_view(), name='commit'),
    url(r'^pay$', OrderPayView.as_view(), name='pay'),
    url(r'^check$', OrderCheckPayView.as_view(), name='check'),
    url(r'^comment/(?P<order_id>.+)$', OrderCommentView.as_view(), name='commit')
]
