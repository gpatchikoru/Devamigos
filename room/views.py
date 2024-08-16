from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.db.models import Count
from .models import Message, Room, Open_room, JoinRequest
from .forms import InvitationForm, JoinRequestForm

@login_required
def rooms(request):
    rooms = Room.objects.all()
    if request.method == "GET":
        rn = request.GET.get('rname')
        if rn is not None:
            rooms = Room.objects.filter(name__icontains=rn)
    return render(request, 'room/rooms.html', {'rooms': rooms})

@login_required
def enter_room(request):
    if request.method == 'POST':
        room_name = request.POST['room_name']
        password = request.POST['password']
        try:
            room = Room.objects.get(name=room_name)
            if request.user == room.owner or request.user in room.members.all() or room.password == password:
                if request.user not in room.members.all():
                    room.members.add(request.user)
                messages = Message.objects.filter(room=room).order_by('date_added')
                return render(request, 'room/room.html', {'room': room, 'messages': messages})
        except Room.DoesNotExist:
            return redirect('join_room')
    return redirect('join_room')

@login_required
def exit_room(request, room_name):
    try:
        room = Room.objects.get(name=room_name)
        if request.user in room.members.all():
            room.members.remove(request.user)
    except Room.DoesNotExist:
        return redirect('rooms')
    return redirect('rooms')

@login_required
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST['room_name']
        password = request.POST['password']
        owner = request.user
        newroom = Room(name=room_name, password=password, owner=owner)
        newroom.save()
        return redirect('rooms')
    return render(request, 'room/create_room.html')

@login_required
def search_rooms(request):
    query = request.GET.get('q')
    if query:
        rooms = Room.objects.annotate(match_count=Count('name')).filter(name__icontains=query).order_by('-match_count')
        all_rooms = Room.objects.exclude(name__icontains=query)
    else:
        rooms = Room.objects.none()
        all_rooms = Room.objects.all()
    return render(request, 'room/rooms.html', {'rooms': rooms, 'all_rooms': all_rooms})

@login_required
def open_rooms(request):
    open_rooms = Open_room.objects.all()
    if request.method == "GET":
        rn = request.GET.get('open_name')
        if rn is not None:
            open_rooms = Open_room.objects.filter(name__icontains=rn)
    return render(request, 'room/open_rooms.html', {'open_rooms': open_rooms})

@login_required
def create_open_room(request):
    if request.method == 'POST':
        room_name = request.POST['room_name']
        newroom = Open_room(name=room_name, owner=request.user)
        newroom.save()
        return redirect('open_rooms')
    return render(request, 'room/create_open_room.html')

@login_required
def enter_open_room(request):
    if request.method == 'POST':
        room_name = request.POST['room_name']
        try:
            open_room = Open_room.objects.get(name=room_name)
            messages = Message.objects.filter(open_room=open_room).order_by('date_added')
            return render(request, 'room/open_room.html', {'open_room': open_room, 'messages': messages})
        except Open_room.DoesNotExist:
            return redirect('open_rooms')
    return redirect('open_rooms')

@login_required
def exit_open_room(request, room_name):
    try:
        open_room = Open_room.objects.get(name=room_name)
    except Open_room.DoesNotExist:
        return redirect('open_rooms')

    return redirect('open_rooms')

@login_required
def my_rooms(request):
    my_rooms = Room.objects.filter(owner=request.user)
    rooms = Room.objects.all()
    user = request.user
    if request.method == "GET":
        mrn = request.GET.get('mrname')
        if mrn is not None:
            my_rooms = Room.objects.filter(name__icontains=mrn)
    return render(request, 'room/my_rooms.html', {'my_rooms': my_rooms, 'user': user, 'rooms': rooms})

@login_required
def invite_users(request):
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            chat_room = form.cleaned_data['chat_room']
            invitees = form.cleaned_data['invitees']
            recipients = User.objects.filter(id__in=invitees.values_list('id', flat=True))
            subject = f'Invitation to join {chat_room} chat room'
            message = f'Hi,\n\nYou are invited to join the chat room "{chat_room}" with password "{password}".\n\n Please do not share this password with any other users.\n\n Thank You.'
            recipient_emails = recipients.values_list('email', flat=True)
            rooms = Room.objects.filter(owner=request.user)
            send_mail(subject, message, 'headmail0607@gmail.com', recipient_emails)
            return redirect('my_rooms')
    else:
        form = InvitationForm()
    return render(request, 'room/invite_users.html', {'form': form})

@login_required
def join_room(request):
    if request.method == 'POST':
        form = JoinRequestForm(request.POST)
        if form.is_valid():
            req_room = form.cleaned_data['req_room']
            password = form.cleaned_data['password']
            room = Room.objects.get(name=req_room)
            join_request = JoinRequest(sender=request.user, room=room)
            join_request.save()
            return HttpResponse('Done')
    else:
        form = JoinRequestForm()
    rooms = Room.objects.all()
    if request.method == "GET":
        rn = request.GET.get('rname')
        if rn is not None:
            rooms = Room.objects.filter(name__icontains=rn)
    return render(request, 'room/rooms.html', {'rooms': rooms, 'form': form})

@login_required
def manage_join_requests(request):
    join_requests = JoinRequest.objects.filter(room__owner=request.user, status='pending')
    if request.method == 'POST':
        for join_request in join_requests:
            stat = request.POST.get(str(join_request.id))
            if stat == 'accept':
                join_request.status = 'accepted'
                join_request.save()
                join_request.room.members.add(join_request.sender)
            elif stat == 'reject':
                join_request.status = 'rejected'
                join_request.save()
    return render(request, 'room/manage_join_requests.html', {'join_requests': join_requests})

@login_required
def clear_room_data(request):
    if request.user.is_superuser:
        Message.objects.all().delete()
        JoinRequest.objects.all().delete()
        Room.objects.all().delete()
        Open_room.objects.all().delete()
        return redirect('rooms')
    else:
        return HttpResponse("Unauthorized", status=401)
