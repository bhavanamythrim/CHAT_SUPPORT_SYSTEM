from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView

from .views import NotificationPreferenceApiView, RegisterView

urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='api-login'),
    path('register/', RegisterView.as_view(), name='api-register'),
    path('notification-preferences/', NotificationPreferenceApiView.as_view(), name='api-notification-preferences'),
]
