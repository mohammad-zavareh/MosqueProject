from django.urls import path
from .views import UserLoginView, UserLogoutView, UserListView, UserCreateView

app_name = 'account'

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path(
        "users/",
        UserListView.as_view(),
        name="user_list",
    ),
    path(
        "users/create/",
        UserCreateView.as_view(),
        name="user_create",
    ),
]