from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import redirect, render
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NotificationPreference
from .serializers import NotificationPreferenceSerializer, RegisterSerializer

User = get_user_model()
ROLE_CUSTOMER = "CUSTOMER"
ROLE_ADMIN = "ADMIN"


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


def _is_admin_identity(user):
    return user.is_staff or user.is_superuser or getattr(user, "role", "") == ROLE_ADMIN


def login_view(request):
    if request.user.is_authenticated:
        return redirect("civic-chat")

    preferred_language = request.session.get("preferred_language") or request.COOKIES.get("preferred_language") or "en"

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        preferred_language = request.POST.get("language", preferred_language)
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password")
        else:
            if _is_admin_identity(user):
                messages.error(request, "This login is for customer accounts only.")
            else:
                login(request, user)
                if hasattr(user, "profile") and user.profile.language:
                    preferred_language = user.profile.language
                if preferred_language and hasattr(user, "profile"):
                    user.profile.language = preferred_language
                    user.profile.chat_language = preferred_language
                    user.profile.save(update_fields=["language", "chat_language", "updated_at"])
                request.session["preferred_language"] = preferred_language
                response = redirect("civic-chat")
                response.set_cookie("preferred_language", preferred_language, max_age=60 * 60 * 24 * 365)
                return response

    return render(request, "registration/login.html", {"preferred_language": preferred_language})


def logout_view(request):
    logout(request)
    return redirect("login")


def register_view(request):
    if request.user.is_authenticated:
        return redirect("civic-chat")

    preferred_language = request.session.get("preferred_language") or request.COOKIES.get("preferred_language") or "en"

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        preferred_language = request.POST.get("language", "en")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        else:
            user = User.objects.create_user(username=username, password=password, role=ROLE_CUSTOMER)
            request.session["preferred_language"] = preferred_language
            if hasattr(user, "profile"):
                user.profile.language = preferred_language
                user.profile.chat_language = preferred_language
                user.profile.save(update_fields=["language", "chat_language", "updated_at"])
            messages.success(request, "Account created successfully")
            response = redirect("login")
            response.set_cookie("preferred_language", preferred_language, max_age=60 * 60 * 24 * 365)
            return response

    return render(request, "users/register.html", {"preferred_language": preferred_language})


class NotificationPreferenceApiView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs).data)

    def patch(self, request):
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
