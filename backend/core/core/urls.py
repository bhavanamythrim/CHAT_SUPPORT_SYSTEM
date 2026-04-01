"""
URL configuration for core project.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.views import login_view, logout_view, register_view

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='civic-landing', permanent=False)),
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),

    path('civic/', include('civic.urls')),
    path('chat/', include('chat.urls')),
    path('tickets/', include('tickets.urls')),

    path('api/users/', include('users.urls')),
    path('api/civic/', include('civic.api_urls')),
    path('notifications/', include('notifications.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
