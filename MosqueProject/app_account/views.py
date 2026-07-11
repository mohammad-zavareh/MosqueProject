from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from .forms import UserCreateForm, PasswordChangeForm

User = get_user_model()


class UserLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('core:dashboard')


class UserLogoutView(View):

    def get(self, request):
        logout(request)
        return redirect('account:login')



class UserListView(LoginRequiredMixin, TemplateView):
    template_name = "user_list.html"

    def get(self, request, *args, **kwargs):
        q  = request.GET.get("q", "").strip()
        qs = User.objects.all().order_by("username")

        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )

        ctx = {
            "users":       qs,
            "total":       qs.count(),
            "q":           q,
            "has_filters": bool(q),
        }
        return self.render_to_response(ctx)


class UserCreateView(LoginRequiredMixin, TemplateView):
    template_name = "user_form.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response({"form": UserCreateForm()})

    def post(self, request, *args, **kwargs):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"کاربر «{user.username}» با موفقیت ایجاد شد.",
            )
            return redirect("account:user_list")
        return self.render_to_response({"form": form})


class PasswordChangeView(LoginRequiredMixin, TemplateView):
    template_name = "change_password.html"

    def get(self, request, *args, **kwargs):
        return self.render_to_response({"form": PasswordChangeForm(request.user)})

    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # جلوگیری از logout شدن کاربر بعد از تغییر رمز
            update_session_auth_hash(request, request.user)
            messages.success(request, "رمز عبور شما با موفقیت تغییر کرد.")
            return redirect("core:dashboard")
        return self.render_to_response({"form": form})