from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminUserOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and (request.user.is_staff or request.user.is_superuser or getattr(request.user, "role", "") == "ADMIN"))


class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser or getattr(request.user, "role", "") == "ADMIN":
            return True
        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner == request.user
        session = getattr(obj, "session", None)
        if session is not None:
            return session.user == request.user
        created_by = getattr(obj, "created_by", None)
        if created_by is not None:
            return created_by == request.user
        return False
