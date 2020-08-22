from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from .models import AudioTrack
from spotify.forms import MusicEntry

from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def track_detail_page(request, track_id):
    obj = AudioTrack.objects.get(id=track_id)
    template_name = 'track/track_detail.html'
    context = {"object": obj}
    return render(request, template_name, context)


def add_track(request):
    template_name = 'track/track_create.html'
    if request.method == "POST":
        form = MusicEntry(request.POST, request.FILES)
        if form.is_valid():
            form.save()
    else:
        form = MusicEntry()
    context = {"form": form,
               "title": "add music",
               }
    return render(request, template_name, context)


def delete_track(request, track_id):
    obj = get_object_or_404(AudioTrack, id=track_id)
    template_name = 'track/track_delete.html'
    if request.method == "POST":
        obj.delete()
        return redirect("/home/")
    context = {"object": obj}
    return render(request, template_name, context)


def modify_track(request, track_id):
    obj = get_object_or_404(AudioTrack, id=track_id)
    template_name = 'track/track_update.html'
    print('pt1')
    form = MusicEntry(request.POST or None, instance=obj)
    print('pt2')
    if form.is_valid() and request == 'POST':
        print('pt3')
        form.save()
        print('saved')
    context = {"title": f"Update {obj.title}",
               "form": form}
    print('lol u outta condition')
    return render(request, template_name, context)