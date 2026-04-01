from django.urls import path
from .views import (
    live_chat_view,
    CreateChatRoomView,
    ChatRoomListView,
    SendMessageView,
    RoomMessagesView,
)

urlpatterns = [
    path('live/', live_chat_view, name='live-chat'),
    path('create-room/', CreateChatRoomView.as_view()),
    path('rooms/', ChatRoomListView.as_view()),
    path('send-message/', SendMessageView.as_view()),
    path('room-messages/<int:room_id>/', RoomMessagesView.as_view()),
]
