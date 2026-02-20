"""
Tests for custom permission classes in core/permissions.py and API-level
permission enforcement across endpoints.

Covers:
- IsOwner: owner can write, non-owner cannot
- IsOwnerOrReadOnly: safe methods allowed for all, writes only for owner
- IsAdminOrReadOnly: safe methods for all, writes only for staff
- CanManagePlaylist: owner, collaborator, and stranger access levels
- Unauthenticated access to protected endpoints
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from rest_framework import status

from core.permissions import (
    IsOwner,
    IsOwnerOrReadOnly,
    IsAdminOrReadOnly,
    CanManagePlaylist,
)
from tests.factories import (
    UserFactory,
    PlaylistFactory,
    TrackFactory,
    GenreFactory,
    ArtistFactory,
    AlbumFactory,
)


# =============================================================================
# Unit Tests for Permission Classes
# =============================================================================

class TestIsOwner:
    """Unit tests for the IsOwner permission class."""

    def setup_method(self):
        self.permission = IsOwner()
        self.factory = APIRequestFactory()

    def _make_request(self, method='get', user=None):
        request = getattr(self.factory, method)('/')
        request.user = user or UserFactory.build()
        return request

    @pytest.mark.django_db
    def test_owner_has_write_permission(self):
        owner = UserFactory()
        request = self._make_request('put', user=owner)

        obj = PlaylistFactory.build(owner=owner)
        assert self.permission.has_object_permission(request, None, obj) is True

    @pytest.mark.django_db
    def test_non_owner_denied_write(self):
        owner = UserFactory()
        other = UserFactory()
        request = self._make_request('put', user=other)

        obj = PlaylistFactory.build(owner=owner)
        assert self.permission.has_object_permission(request, None, obj) is False

    @pytest.mark.django_db
    def test_safe_methods_allowed_for_any_user(self):
        other = UserFactory()
        request = self._make_request('get', user=other)

        owner = UserFactory()
        obj = PlaylistFactory.build(owner=owner)
        assert self.permission.has_object_permission(request, None, obj) is True

    @pytest.mark.django_db
    def test_object_with_user_field(self):
        """Also works with objects that have 'user' instead of 'owner'."""
        user = UserFactory()
        other = UserFactory()
        request = self._make_request('delete', user=other)

        # Simulate an object with .user attribute
        class ObjWithUser:
            pass
        obj = ObjWithUser()
        obj.user = user

        assert self.permission.has_object_permission(request, None, obj) is False

        request2 = self._make_request('delete', user=user)
        assert self.permission.has_object_permission(request2, None, obj) is True


class TestIsOwnerOrReadOnly:
    """Unit tests for IsOwnerOrReadOnly."""

    def setup_method(self):
        self.permission = IsOwnerOrReadOnly()
        self.factory = APIRequestFactory()

    def _make_request(self, method='get', user=None):
        request = getattr(self.factory, method)('/')
        request.user = user or UserFactory.build()
        return request

    @pytest.mark.django_db
    def test_get_allowed_for_non_owner(self):
        owner = UserFactory()
        other = UserFactory()
        request = self._make_request('get', user=other)
        obj = PlaylistFactory.build(owner=owner)
        assert self.permission.has_object_permission(request, None, obj) is True

    @pytest.mark.django_db
    def test_put_denied_for_non_owner(self):
        owner = UserFactory()
        other = UserFactory()
        request = self._make_request('put', user=other)
        obj = PlaylistFactory.build(owner=owner)
        assert self.permission.has_object_permission(request, None, obj) is False

    @pytest.mark.django_db
    def test_put_allowed_for_owner(self):
        owner = UserFactory()
        request = self._make_request('put', user=owner)
        obj = PlaylistFactory.build(owner=owner)
        assert self.permission.has_object_permission(request, None, obj) is True


class TestIsAdminOrReadOnly:
    """Unit tests for IsAdminOrReadOnly."""

    def setup_method(self):
        self.permission = IsAdminOrReadOnly()
        self.factory = APIRequestFactory()

    def _make_request(self, method='get', user=None):
        request = getattr(self.factory, method)('/')
        request.user = user or UserFactory.build()
        return request

    @pytest.mark.django_db
    def test_get_allowed_for_regular_user(self):
        user = UserFactory()
        request = self._make_request('get', user=user)
        assert self.permission.has_permission(request, None) is True

    @pytest.mark.django_db
    def test_post_denied_for_regular_user(self):
        user = UserFactory()
        request = self._make_request('post', user=user)
        assert self.permission.has_permission(request, None) is False

    @pytest.mark.django_db
    def test_post_allowed_for_staff_user(self):
        admin = UserFactory(is_staff=True)
        request = self._make_request('post', user=admin)
        assert self.permission.has_permission(request, None) is True

    @pytest.mark.django_db
    def test_delete_denied_for_regular_user(self):
        user = UserFactory()
        request = self._make_request('delete', user=user)
        assert self.permission.has_permission(request, None) is False


class TestCanManagePlaylist:
    """Unit tests for CanManagePlaylist."""

    def setup_method(self):
        self.permission = CanManagePlaylist()
        self.factory = APIRequestFactory()

    def _make_request(self, method='get', user=None, action=None):
        request = getattr(self.factory, method)('/')
        request.user = user or UserFactory.build()
        return request

    def _make_view(self, action='list'):
        view = type('MockView', (), {'action': action})()
        return view

    @pytest.mark.django_db
    def test_owner_has_full_access(self):
        owner = UserFactory()
        request = self._make_request('delete', user=owner)
        playlist = PlaylistFactory(owner=owner)
        view = self._make_view('destroy')
        assert self.permission.has_object_permission(request, view, playlist) is True

    @pytest.mark.django_db
    def test_stranger_denied_write_on_private_playlist(self):
        owner = UserFactory()
        stranger = UserFactory()
        request = self._make_request('put', user=stranger)
        playlist = PlaylistFactory(owner=owner, is_public=False)
        view = self._make_view('update')
        assert self.permission.has_object_permission(request, view, playlist) is False

    @pytest.mark.django_db
    def test_stranger_can_read_public_playlist(self):
        owner = UserFactory()
        stranger = UserFactory()
        request = self._make_request('get', user=stranger)
        playlist = PlaylistFactory(owner=owner, is_public=True)
        view = self._make_view('retrieve')
        assert self.permission.has_object_permission(request, view, playlist) is True

    @pytest.mark.django_db
    def test_collaborator_can_add_tracks(self):
        owner = UserFactory()
        collaborator = UserFactory()
        request = self._make_request('post', user=collaborator)
        playlist = PlaylistFactory(owner=owner, is_public=False)
        playlist.collaborators.add(collaborator)
        view = self._make_view('add_tracks')
        assert self.permission.has_object_permission(request, view, playlist) is True

    @pytest.mark.django_db
    def test_collaborator_cannot_delete_playlist(self):
        owner = UserFactory()
        collaborator = UserFactory()
        request = self._make_request('delete', user=collaborator)
        playlist = PlaylistFactory(owner=owner)
        playlist.collaborators.add(collaborator)
        view = self._make_view('destroy')
        assert self.permission.has_object_permission(request, view, playlist) is False


# =============================================================================
# API-level Permission Tests (via actual HTTP requests)
# =============================================================================

@pytest.mark.django_db
class TestAPIPermissionEnforcement:
    """End-to-end tests that verify permission enforcement via the HTTP API."""

    def test_unauthenticated_cannot_list_tracks(self, api_client):
        response = api_client.get('/api/v1/tracks/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_list_artists(self, api_client):
        response = api_client.get('/api/v1/artists/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regular_user_cannot_create_track(self, authenticated_client):
        """Creating a track requires admin/staff status."""
        response = authenticated_client.post('/api/v1/tracks/', {
            'title': 'Sneaky Track',
            'duration': '00:03:00',
        })
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_admin_can_create_genre(self, admin_client):
        """Admin users can create genres."""
        response = admin_client.post('/api/v1/genres/', {
            'name': 'New Genre',
            'slug': 'new-genre',
        })
        assert response.status_code in (
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
        )

    def test_user_cannot_edit_others_playlist(self, authenticated_client, other_user, db):
        """A user cannot update another user's playlist."""
        other_playlist = PlaylistFactory(owner=other_user, is_public=True)
        url = f'/api/v1/playlists/{other_playlist.id}/'
        response = authenticated_client.patch(url, {'title': 'Hijacked!'}, format='json')
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_cannot_delete_others_playlist(self, authenticated_client, other_user, db):
        """A user cannot delete another user's playlist."""
        other_playlist = PlaylistFactory(owner=other_user, is_public=True)
        url = f'/api/v1/playlists/{other_playlist.id}/'
        response = authenticated_client.delete(url)
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_can_delete_own_playlist(self, authenticated_client, user, db):
        """A user can delete their own playlist."""
        playlist = PlaylistFactory(owner=user)
        url = f'/api/v1/playlists/{playlist.id}/'
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_private_playlist_not_visible_to_others(self, authenticated_client, other_user, db):
        """A private playlist owned by another user should not appear in listings."""
        private_playlist = PlaylistFactory(owner=other_user, is_public=False)
        response = authenticated_client.get('/api/v1/playlists/')
        assert response.status_code == status.HTTP_200_OK
        ids_returned = [p['id'] for p in response.json().get('results', [])]
        assert private_playlist.id not in ids_returned
