from django.shortcuts import render

# Create your views here.
from .models import Track
from spotify.forms import MusicEntry


def track_detail_page(request, post_id):
    obj = Track.objects.get(id=post_id)
    template_name = 'track/track_detail.html'
    context = {"object": obj}
    return render(request, template_name, context)


def add_track(request):
    template_name = 'track/track_create.html'
    form = MusicEntry(request.POST)
    if request.method == 'POST':
        print(request.POST)
        form = MusicEntry()
        # form.save()
    context = {"form": form,
               "title": "add music"
               }
    return render(request, template_name, context)
