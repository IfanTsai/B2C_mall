from django.shortcuts import render, HttpResponse, redirect
from apps.user.models import User
from django.views.generic import View
from django.core.urlresolvers import reverse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.contrib.auth import authenticate, login
from celery_tasks.tasks import send_register_active_email
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
            send_register_active_email.delay(email, username, token)

            return redirect(reverse('user:login'))
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
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            return redirect(reverse('user:login'))

        # 过期后会触发SignatureExpired异常
        except SignatureExpired:
            return HttpResponse('激活链接已过期')

class LoginView(View):
    """
    用户登陆视图
    """
    def get(self, request):
        username = ''
        checked = ''
        if 'username' in request.COOKIES:
            username = request.COOKIES['username']
            checked = 'checked'
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')
        print(remember)

        if not all([username, password]):
            return render(request, 'login.html', {'error': '用户名或密码填写不完整'})

        # 使用Django内置的用户认证系统来进行账号密码验证
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                # 使用Django内置的用户认证系统来记录用户登陆状态
                login(request, user)

                response = redirect(reverse('goods:index'))
                # 记住用户名

                if remember == 'on':
                    response.set_cookie('username', username)
                else:
                    response.delete_cookie('username')
                # 重定向到首页
                return response
            else:
                return render(request, 'login.html', {'error': '账户未激活'})
        else:
            return render(request, 'login.html', {'error': '用户名或密码错误'})
