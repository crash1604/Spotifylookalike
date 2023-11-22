from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User


from rest_framework.decorators import api_view, authentication_classes , permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated


from .serializers import UserSerializer

def home_page(request):
    return HttpResponse("Welcome to Spotify home page")
