from django.contrib.auth.views import LoginView
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.shortcuts import redirect

class UserLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('core:dashboard')


class UserLogoutView(View):

    def get(self, request):
        logout(request)
        return redirect('account:login')