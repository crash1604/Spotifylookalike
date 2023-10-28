from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.models import User

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token


from .serializers import UserSerializer


@api_view(['POST'])
def login(request):
    return Response({202})

@api_view(['POST'])
def signup(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        user = User.objects.get(username=request.data['username'])
        user.set_password(request.data['password'])
        user.save()
        token = Token.objects.create(user=user)
        return Response({'token': token.key, 'user': serializer.data})
    return Response(serializer.errors, status=status.HTTP_200_OK)

@api_view(['GET'])
def test_token(request):
    return Response({201})

def home_page(request):
    return HttpResponse("Welcome to Spotify home page")
