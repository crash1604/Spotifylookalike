"""
Custom permission classes for the API.
"""

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permission check that ensures users can only modify their own resources.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an `owner` or `user` attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Instance must have an owner attribute
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access to any user, but write access only to admin users.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsArtistOwner(permissions.BasePermission):
    """
    Permission for artist management - only allows the artist owner
    or admins to modify artist data.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admins can modify any artist
        if request.user.is_staff:
            return True

        # Check if user is associated with this artist
        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class CanManagePlaylist(permissions.BasePermission):
    """
    Permission for playlist management.
    - Owner can do anything
    - Collaborators can add/remove tracks (if collaboration feature exists)
    - Others can only view public playlists
    """

    def has_object_permission(self, request, view, obj):
        # Owner has full access
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True

        # Read-only for public playlists
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'is_public') and obj.is_public:
                return True

        # Check collaborators if the feature exists
        if hasattr(obj, 'collaborators'):
            if request.user in obj.collaborators.all():
                # Collaborators can modify track list but not delete playlist
                if view.action in ['add_tracks', 'remove_tracks']:
                    return True

        return False
