from django.shortcuts import render, HttpResponse, redirect
from apps.user.models import User, Address
from apps.goods.models import GoodsSKU
from django.views.generic import View
from django.core.urlresolvers import reverse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from celery_tasks.tasks import send_register_active_email
from utils.mixin import LoginRequireMixin
from django_redis import get_redis_connection
import re

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

        # 获取登陆后所要跳转的地址，默认跳转到首页
        next_url = request.GET.get('next', reverse('goods:index'))

        if not all([username, password]):
            return render(request, 'login.html', {'error': '用户名或密码填写不完整'})

        # 使用Django内置的用户认证系统来进行账号密码验证
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                # 使用Django内置的用户认证系统来记录用户登陆状态
                login(request, user)

                response = redirect(next_url)
                # 记住用户名

                if remember == 'on':
                    response.set_cookie('username', username)
                else:
                    response.delete_cookie('username')

                # 重定向到首页
                # 从文档中可知，如果使用了Django自带的认证系统，Django会自动把request.user传递给模板
                # 所以在模板中可以获取user.username
                return response
            else:
                return render(request, 'login.html', {'error': '账户未激活'})
        else:
            return render(request, 'login.html', {'error': '用户名或密码错误'})

class LogoutView(View):
    """
    退出登陆视图
    """
    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))

class UserInfoView(LoginRequireMixin, View):
    """
    用户中心-信息页
    """
    def get(self, request):

        user = request.user

        # 获取用户的个人信息
        address = Address.objects.get_default_addr(user)

        # 获取用户的历史浏览记录
        # 'default'表示使用的是settings.py中配置的redis
        conn = get_redis_connection('default')
        history_key = 'history_%d' % user.id
        sku_ids = conn.lrange(history_key, 0, 4)

        goods_li = []
        for sku_id in sku_ids:
            goods_li.append(GoodsSKU.objects.get(id=sku_id))

        context = {
            'page': 'info',
            'user': user,
            'address': address,
            'goods_li': goods_li,
        }

        return render(request, 'user_center_info.html', context)

class UserOrderView(LoginRequireMixin, View):
    """
     用户中心-订单页
    """
    def get(self, request):

        # 获取用户的订单信息

        return render(request, 'user_center_order.html', {'page': 'order'})

class AddressView(LoginRequireMixin, View):
    """
    用户中心-地址页
    """
    def get(self, request):

        # 获取用户的默认收货地址
        address = Address.objects.get_default_addr(request.user)

        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        """
        添加收货人信息
        :param request:
        :return:
        """
        receiver = request.POST['receiver']
        addr = request.POST['addr']
        zip_code = request.POST['zip_code']
        phone = request.POST['phone']

        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'error': '收货人信息填写不完整'})

        if not re.match(r'^1[34578]\d{9}$', phone):
            return render(request, 'user_center_site.html', {'error': '手机号码格式不正确'})

        # 如果用户已存在默认收货地址，添加的地址则不作为默认收货地址，否则作为默认收货地址

        address = Address.objects.get_default_addr(request.user)
        is_default = False if address else True

        # 添加地址
        Address.objects.create(user=request.user, addr=addr,
                               receiver=receiver, zip_code=zip_code,
                               phone=phone, is_default=is_default)

        return redirect(reverse('user:address'))