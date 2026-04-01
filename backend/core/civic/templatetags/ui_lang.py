from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def ui_lang(context):
    request = context.get("request")
    if not request:
        return "en"

    lang = request.session.get("preferred_language")
    if lang:
        return lang

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        profile = getattr(user, "profile", None)
        if profile and getattr(profile, "language", None):
            return profile.language

    return "en"
