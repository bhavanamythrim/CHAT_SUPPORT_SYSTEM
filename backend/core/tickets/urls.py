from django.urls import path
from .views import (
    TicketListCreateView,
    ticket_list_view,
    create_ticket_view,
    ticket_chat_view,
    send_message,
)

urlpatterns = [
   
    path('api/', TicketListCreateView.as_view(), name='ticket-list-create'),

    
    path('list/', ticket_list_view, name='ticket-list-view'),

    
    path('create/', create_ticket_view, name='create-ticket'),

    
    path('<int:ticket_id>/chat/', ticket_chat_view, name='ticket-chat'),

    path('chat/<int:room_id>/send/', send_message, name='send-message'),
]
