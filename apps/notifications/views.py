from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
def notification_bell_data(request):
    """AJAX — returns unread count + latest 8 notifications."""
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:8]
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({
        'unread': unread,
        'items': [{
            'id': n.pk, 'title': n.title, 'message': n.message[:120],
            'link': n.link, 'is_read': n.is_read,
            'type': n.type,
            'created': n.created_at.strftime('%d %b, %H:%M'),
        } for n in notifs]
    })


@login_required
def mark_notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    notif = Notification.objects.filter(pk=pk, user=request.user).first()
    if notif and notif.link:
        return redirect(notif.link)
    return redirect('dashboard')


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
def notification_list(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    return render(request, 'notifications/list.html', {'notifs': notifs})

@csrf_exempt
def ai_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body    = json.loads(request.body)
        message = body.get('message', '').strip()
        if not message:
            return JsonResponse({'error': 'Empty message'}, status=400)
        from .ai_assistant import get_ai_response
        reply = get_ai_response(message, request.user if request.user.is_authenticated else None)
        return JsonResponse({'reply': reply})
    except Exception as e:
        return JsonResponse({'reply': "Sorry, I couldn't process that. Please try again."}, status=200)