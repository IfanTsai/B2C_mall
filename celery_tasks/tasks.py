from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader
import os
#import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "B2C_mall.settings")
# django.setup()
from apps.goods.models import (
    GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
)

app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')


app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')

@app.task
def send_register_active_email(to_email, username, token):
    """
    发送激活邮件
    :param to_email:
    :param username:
    :param token:
    :return:
    """
    subject = '超级商城欢迎注册'
    message = ''
    receiver = [to_email]
    html_message = '<h1>%s，欢迎注册超级商城账号</h1>' \
                   '请点击下面链接激活您的账号<br>' \
                   '<a href=http://127.0.0.1:8000/user/active/%s>' \
                   'http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)
    sender = settings.EMAIL_FROM
    send_mail(subject, message, sender, receiver, html_message=html_message)

@app.task
def generate_static_index_html():
    """
    产生首页静态页面
    :return:
    """
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

    # 加载模板文件
    temp = loader.get_template('static_index.html')
    # 模板渲染
    static_index_html = temp.render(context)

    # 生成首页对应的静态页面文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)