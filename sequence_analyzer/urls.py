from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='sequence_analyzer/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('submit/', views.submit_sequence, name='submit_sequence'),
    path('submissions/', views.view_submissions, name='view_submissions'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
]
