from django.shortcuts import render, HttpResponse
from apps.user.models import User
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.core.mail import send_mail
import re

# Create your views here.

class RegisterView(View):
    """
    用户注册视图
    """
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 获取表单信息
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cpassword = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据非空校验
        if not all([username, password, cpassword, email]):
            return render(request, 'register.html', {'error': '填写信息不能为空'})

        # 确认密码
        if password != cpassword:
            return render(request, 'register.html', {'error': '密码不一致'})

        # 校验邮箱格式
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'error': '邮箱格式不正确'})

        # 校验协议是否勾选
        if allow != 'on':
            return render(request, 'register.html', {'error': '请同意协议'})

        # 判断该用户名是否注册
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 该用户未注册
            user = None

        if user is None:
            # 注册用户
            user = User.objects.create_user(username, email, password)
            # 默认状态，邮箱未激活
            user.is_active = False
            user.save()

            # 加密用户信息
            serializer = Serializer(settings.SECRET_KEY, 3600)
            info = {'confirm': user.id}
            token = serializer.dumps(info)
            token = token.decode()

            # 发送邮件
            subject = '超级商城欢迎注册'
            message = ''
            receiver = [email]
            html_message = '<h1>%s，欢迎注册超级商城账号</h1>' \
                           '请点击下面链接激活您的账号<br>' \
                           '<a href=http://127.0.0.1:8000/user/active/%s>' \
                           'http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)
            sender = settings.EMAIL_FROM
            send_mail(subject, message, sender, receiver, html_message=html_message)

            return HttpResponse('OK')
        else:
            return render(request, 'register.html', {'error': '该用户已注册'})

class ActiveView(View):
    """
    用户激活视图
    """
    def get(self, request, token):
        # 解密用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            id = info['confirm']
            user = User.objects.get(id=id)
            user.is_active = True
            user.save()
            return HttpResponse('OK')

        # 过期后会触发SignatureExpired异常
        except SignatureExpired:
            return HttpResponse('激活链接已过期')
