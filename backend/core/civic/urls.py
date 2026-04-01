from django.urls import path

from .views import (
    agent_dashboard,
    chat_page,
    delete_account,
    end_chat_session,
    export_data,
    landing_page,
    profile_page,
    send_chat_message,
    settings_page,
    settings_toggle,
)

urlpatterns = [
    path("", landing_page, name="civic-landing"),
    path("chat/", chat_page, name="civic-chat"),
    path("chat/send/", send_chat_message, name="civic-chat-send"),
    path("chat/end/", end_chat_session, name="civic-chat-end"),
    path("profile/", profile_page, name="civic-profile"),
    path("settings/", settings_page, name="civic-settings"),
    path("settings/toggle/", settings_toggle, name="civic-settings-toggle"),
    path("settings/export/", export_data, name="civic-export-data"),
    path("settings/delete-account/", delete_account, name="civic-delete-account"),
    path("agent/", agent_dashboard, name="agent-dashboard"),
]
