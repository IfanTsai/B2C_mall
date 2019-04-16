from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "B2C_mall.settings")
django.setup()

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