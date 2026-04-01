from django.urls import re_path

from .consumers import CivicChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/civic/chat/(?P<session_id>\d+)/$", CivicChatConsumer.as_asgi()),
]
