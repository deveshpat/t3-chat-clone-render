"""
Simplified views for PythonAnywhere deployment (no WebSockets)
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from .models import Conversation, Message
import json
import openai
from django.conf import settings
import asyncio
import time

def home(request):
    """Main chat interface"""
    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(
            user_id=str(request.user.id)
        ).order_by('-last_activity')[:10]
        
        return render(request, 'chat/simple_chat.html', {
            'conversations': conversations
        })
    else:
        return render(request, 'chat/landing.html')

def register_view(request):
    """User registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request):
    """Send a message and get AI response"""
    try:
        data = json.loads(request.body)
        message_content = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        model = data.get('model', 'openai/gpt-4o-mini')
        
        if not message_content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    user_id=str(request.user.id)
                )
            except Conversation.DoesNotExist:
                conversation = Conversation.objects.create_conversation(
                    user_id=str(request.user.id),
                    title=message_content[:50] + "..." if len(message_content) > 50 else message_content
                )
        else:
            conversation = Conversation.objects.create_conversation(
                user_id=str(request.user.id),
                title=message_content[:50] + "..." if len(message_content) > 50 else message_content
            )
        
        # Save user message
        user_message = Message.objects.create(
            conversation=conversation,
            role='user',
            content=message_content
        )
        
        # Get API key from session or settings
        api_key = request.session.get('openrouter_api_key') or settings.OPENROUTER_API_KEY
        
        if not api_key:
            return JsonResponse({
                'error': 'OpenRouter API key not configured. Please add it in settings.',
                'conversation_id': str(conversation.id)
            }, status=400)
        
        # Generate AI response
        try:
            client = openai.OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            
            # Get conversation history
            messages = []
            for msg in conversation.messages.filter(is_deleted=False).order_by('created_at')[-10:]:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Save AI message
            ai_message = Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=ai_response,
                model=model
            )
            
            return JsonResponse({
                'success': True,
                'conversation_id': str(conversation.id),
                'user_message': {
                    'id': str(user_message.id),
                    'content': message_content,
                    'timestamp': user_message.created_at.isoformat()
                },
                'ai_message': {
                    'id': str(ai_message.id),
                    'content': ai_response,
                    'model': model,
                    'timestamp': ai_message.created_at.isoformat()
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'AI API error: {str(e)}',
                'conversation_id': str(conversation.id)
            }, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_conversation(request, conversation_id):
    """Get conversation messages"""
    try:
        conversation = Conversation.objects.get(
            id=conversation_id,
            user_id=str(request.user.id)
        )
        
        messages = []
        for msg in conversation.messages.filter(is_deleted=False).order_by('created_at'):
            messages.append({
                'id': str(msg.id),
                'role': msg.role,
                'content': msg.content,
                'model': msg.model,
                'timestamp': msg.created_at.isoformat()
            })
        
        return JsonResponse({
            'conversation': {
                'id': str(conversation.id),
                'title': conversation.title,
                'created_at': conversation.created_at.isoformat()
            },
            'messages': messages
        })
        
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

@login_required
def new_conversation(request):
    """Create a new conversation"""
    conversation = Conversation.objects.create_conversation(
        user_id=str(request.user.id),
        title="New Chat"
    )
    
    return JsonResponse({
        'conversation_id': str(conversation.id),
        'title': conversation.title
    })

@login_required
@csrf_exempt
def save_api_key(request):
    """Save API key to session"""
    if request.method == 'POST':
        data = json.loads(request.body)
        api_key = data.get('api_key', '').strip()
        
        if api_key:
            request.session['openrouter_api_key'] = api_key
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'API key is required'}, status=400)
    
    return JsonResponse({'error': 'POST method required'}, status=405) 