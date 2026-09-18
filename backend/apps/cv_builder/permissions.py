from rest_framework.permissions import BasePermission


class IsCVOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'cv'):
            return obj.cv.user == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False
