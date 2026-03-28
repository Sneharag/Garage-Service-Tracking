from django.urls import path
from . import views

urlpatterns = [
    path('login/',views.user_login,name='login'),
    path('logout/',views.user_logout,name='logout'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
    path('add-user/', views.add_user, name='add_user'),
    path('users/', views.user_list, name='user_list'),
    path('user/<int:id>/', views.user_detail, name='user_detail'),
    path('edituser/<int:pk>/', views.user_edit, name='user_edit'),
    path('deleteuser/<int:pk>/', views.user_delete, name='user_delete'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
]