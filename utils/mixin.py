from django.contrib.auth.decorators import login_required

class LoginRequireMinin(object):
    @classmethod
    def as_view(cls, **initkwargs):
       view = super(LoginRequireMinin, cls).as_view(**initkwargs)
       return login_required(view)
