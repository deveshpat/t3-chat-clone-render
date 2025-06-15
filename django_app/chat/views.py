from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
import openai
from tavily import TavilyClient
import json
import logging
import time
import asyncio
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.core.files.storage import default_storage
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django_ratelimit.decorators import ratelimit
from channels.layers import get_channel_layer
import hashlib
import uuid
import os

from .models import Conversation, Message, FileUpload, APIUsage
from .serializers import ConversationSerializer, MessageSerializer, FileUploadSerializer
from .tasks import process_ai_chat_request, process_image_generation, process_file_upload
from .authentication import APIKeyAuthentication

logger = logging.getLogger('chat')
channel_layer = get_channel_layer()

# Set OpenAI API key
openai.api_key = settings.OPENAI_API_KEY

# Initialize Tavily client if key is provided
tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None

class ConversationViewSet(viewsets.ModelViewSet):
    """
    Enhanced ViewSet for managing conversations with caching and optimization
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def get_queryset(self):
        """Get conversations for the current user with caching"""
        user_id = self.get_user_id()
        cache_key = f"user_conversations:{user_id}"
        
        conversations = cache.get(cache_key)
        if conversations is None:
            conversations = Conversation.objects.filter(
                user_id=user_id,
                is_archived=False
            ).order_by('-last_activity')
            cache.set(cache_key, conversations, 300)  # Cache for 5 minutes
        
        return conversations
    
    def create(self, request):
        """Create a new conversation with enhanced features"""
        try:
            user_id = self.get_user_id()
            title = request.data.get('title', f"Chat {time.strftime('%Y-%m-%d %H:%M')}")
            metadata = request.data.get('metadata', {})
            
            conversation = Conversation.objects.create_conversation(
                user_id=user_id,
                title=title,
                metadata=metadata
            )
            
            # Invalidate cache
            cache.delete(f"user_conversations:{user_id}")
            
            serializer = self.get_serializer(conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Conversation creation failed: {str(e)}")
            return Response(
                {'error': 'Failed to create conversation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a conversation"""
        try:
            conversation = self.get_object()
            conversation.is_archived = True
            conversation.save(update_fields=['is_archived'])
            
            # Invalidate cache
            user_id = self.get_user_id()
            cache.delete(f"user_conversations:{user_id}")
            
            return Response({'status': 'archived'})
            
        except Exception as e:
            logger.error(f"Conversation archiving failed: {str(e)}")
            return Response(
                {'error': 'Failed to archive conversation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages for a conversation with pagination"""
        try:
            conversation = self.get_object()
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 50))
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Get messages with caching
            cache_key = f"conversation_messages:{pk}:{page}:{page_size}"
            messages_data = cache.get(cache_key)
            
            if messages_data is None:
                messages = Message.objects.filter(
                    conversation=conversation,
                    is_deleted=False
                ).order_by('created_at')[offset:offset + page_size]
                
                messages_data = [msg.get_summary() for msg in messages]
                cache.set(cache_key, messages_data, 300)  # Cache for 5 minutes
            
            return Response({
                'messages': messages_data,
                'page': page,
                'page_size': page_size,
                'has_more': len(messages_data) == page_size
            })
            
        except Exception as e:
            logger.error(f"Message retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve messages'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get conversation analytics"""
        try:
            conversation = self.get_object()
            
            # Calculate analytics
            total_messages = conversation.message_count
            total_tokens = conversation.total_tokens
            
            # Get model usage breakdown
            model_usage = {}
            for message in conversation.messages.filter(model__isnull=False, is_deleted=False):
                model = message.model
                if model not in model_usage:
                    model_usage[model] = {'count': 0, 'tokens': 0}
                model_usage[model]['count'] += 1
                model_usage[model]['tokens'] += message.token_count
            
            # Average response time
            avg_response_time = conversation.messages.filter(
                response_time__isnull=False
            ).aggregate(avg_time=models.Avg('response_time'))['avg_time'] or 0
            
            analytics_data = {
                'conversation_id': str(conversation.id),
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'model_usage': model_usage,
                'avg_response_time': float(avg_response_time),
                'created_at': conversation.created_at.isoformat(),
                'last_activity': conversation.last_activity.isoformat()
            }
            
            return Response(analytics_data)
            
        except Exception as e:
            logger.error(f"Analytics retrieval failed: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve analytics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_user_id(self):
        """Get user ID from request"""
        user = self.request.user
        if hasattr(user, 'id'):
            return str(user.id)
        elif hasattr(user, 'username'):
            return user.username
        else:
            return 'anonymous'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='60/m', method='POST')
def chat_message(request):
    """
    Enhanced chat message endpoint with streaming support
    """
    try:
        data = request.data
        conversation_id = data.get('conversation_id')
        message = data.get('message', '').strip()
        model = data.get('model', 'openai/gpt-4o-mini')
        stream = data.get('stream', False)
        api_key = data.get('api_key')
        
        # Validation
        if not conversation_id or not message:
            return Response(
                {'error': 'Conversation ID and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not api_key:
            return Response(
                {'error': 'API key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get user ID
        user_id = get_user_id_from_request(request)
        
        if stream:
            # Return streaming response
            return StreamingHttpResponse(
                stream_chat_response(conversation, message, model, api_key, user_id),
                content_type='text/event-stream'
            )
        else:
            # Process asynchronously with Celery
            task_result = process_ai_chat_request.delay(
                conversation_id=str(conversation_id),
                user_message=message,
                model=model,
                api_key=api_key,
                user_id=user_id
            )
            
            return Response({
                'task_id': task_result.id,
                'status': 'processing',
                'message': 'Request is being processed'
            }, status=status.HTTP_202_ACCEPTED)
    
    except Exception as e:
        logger.error(f"Chat message processing failed: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def stream_chat_response(conversation, message, model, api_key, user_id):
    """
    Generator function for streaming chat responses
    """
    try:
        # Create user message
        user_msg = Message.objects.create_message(
            conversation=conversation,
            role='user',
            content=message,
            model=model
        )
        
        # Send user message event
        yield f"data: {json.dumps({'type': 'user_message', 'message': user_msg.get_summary()})}\n\n"
        
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Get conversation history
        messages = []
        for msg in conversation.get_recent_messages(limit=20):
            messages.append({
                'role': msg.role,
                'content': msg.content
            })
        
        # Stream AI response
        start_time = time.time()
        full_response = ""
        
        async def stream_ai_response():
            nonlocal full_response
            
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=0.7,
                max_tokens=4000
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
        
        # Run async generator
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async_gen = stream_ai_response()
        try:
            while True:
                chunk = loop.run_until_complete(async_gen.__anext__())
                yield chunk
        except StopAsyncIteration:
            pass
        finally:
            loop.close()
        
        # Calculate metrics
        response_time = time.time() - start_time
        
        # Create assistant message
        assistant_msg = Message.objects.create_message(
            conversation=conversation,
            role='assistant',
            content=full_response,
            model=model,
            tokens=len(full_response.split())  # Rough token estimate
        )
        assistant_msg.response_time = response_time
        assistant_msg.save(update_fields=['response_time'])
        
        # Send completion event
        yield f"data: {json.dumps({'type': 'complete', 'message': assistant_msg.get_summary()})}\n\n"
        
        # Log API usage
        APIUsage.log_request(
            user_id=user_id,
            endpoint='/api/chat/stream/',
            method='POST',
            status_code=200,
            response_time=response_time,
            tokens_used=len(full_response.split())
        )
        
    except Exception as e:
        logger.error(f"Streaming response failed: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='10/m', method='POST')
def generate_image(request):
    """
    Enhanced image generation endpoint
    """
    try:
        data = request.data
        conversation_id = data.get('conversation_id')
        prompt = data.get('prompt', '').strip()
        model = data.get('model', 'stability-ai/stable-diffusion-3-medium')
        api_key = data.get('api_key')
        
        # Validation
        if not conversation_id or not prompt:
            return Response(
                {'error': 'Conversation ID and prompt are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not api_key:
            return Response(
                {'error': 'API key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get user ID
        user_id = get_user_id_from_request(request)
        
        # Process asynchronously
        task_result = process_image_generation.delay(
            conversation_id=str(conversation_id),
            prompt=prompt,
            model=model,
            api_key=api_key,
            user_id=user_id
        )
        
        return Response({
            'task_id': task_result.id,
            'status': 'processing',
            'message': 'Image generation started'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@ratelimit(key='user', rate='20/m', method='POST')
def upload_file(request):
    """
    Enhanced file upload endpoint with processing
    """
    try:
        conversation_id = request.data.get('conversation_id')
        uploaded_file = request.FILES.get('file')
        
        # Validation
        if not conversation_id or not uploaded_file:
            return Response(
                {'error': 'Conversation ID and file are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate file
        max_size = settings.CHAT_SETTINGS.get('MAX_FILE_SIZE', 10 * 1024 * 1024)
        allowed_types = settings.CHAT_SETTINGS.get('ALLOWED_FILE_TYPES', [])
        
        if uploaded_file.size > max_size:
            return Response(
                {'error': f'File size exceeds maximum allowed size of {max_size} bytes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if allowed_types and uploaded_file.content_type not in allowed_types:
            return Response(
                {'error': f'File type {uploaded_file.content_type} is not allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate file hash
        file_content = uploaded_file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        uploaded_file.seek(0)  # Reset file pointer
        
        # Check for duplicate
        existing_file = FileUpload.objects.filter(file_hash=file_hash).first()
        if existing_file:
            return Response({
                'file_id': str(existing_file.id),
                'message': 'File already exists',
                'extracted_content': existing_file.extracted_content
            })
        
        # Save file
        file_path = default_storage.save(
            f'uploads/{uuid.uuid4()}_{uploaded_file.name}',
            uploaded_file
        )
        
        # Create file upload record
        file_upload = FileUpload.objects.create(
            conversation=conversation,
            original_filename=uploaded_file.name,
            file_path=file_path,
            file_size=uploaded_file.size,
            content_type=uploaded_file.content_type,
            file_hash=file_hash
        )
        
        # Process file asynchronously
        task_result = process_file_upload.delay(str(file_upload.id))
        
        return Response({
            'file_id': str(file_upload.id),
            'task_id': task_result.id,
            'status': 'processing',
            'message': 'File uploaded and processing started'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_models(request):
    """
    Get available AI models with caching
    """
    cache_key = 'available_models'
    models_data = cache.get(cache_key)
    
    if models_data is None:
        models_data = {
            'text_models': [
                {
                    'id': 'openai/gpt-4o-mini',
                    'name': 'GPT-4O Mini',
                    'provider': 'OpenAI',
                    'description': 'Fast and efficient model for most tasks'
                },
                {
                    'id': 'google/gemini-flash-1.5',
                    'name': 'Gemini Flash 1.5',
                    'provider': 'Google',
                    'description': 'Fast multimodal model'
                },
                {
                    'id': 'anthropic/claude-3.5-sonnet',
                    'name': 'Claude 3.5 Sonnet',
                    'provider': 'Anthropic',
                    'description': 'Advanced reasoning and analysis'
                },
                {
                    'id': 'meta-llama/llama-3.1-70b-instruct',
                    'name': 'Llama 3.1 70B',
                    'provider': 'Meta',
                    'description': 'Open source large language model'
                }
            ],
            'image_models': [
                {
                    'id': 'stability-ai/stable-diffusion-3-medium',
                    'name': 'Stable Diffusion 3 Medium',
                    'provider': 'Stability AI',
                    'description': 'High-quality image generation'
                },
                {
                    'id': 'openai/dall-e-3',
                    'name': 'DALL-E 3',
                    'provider': 'OpenAI',
                    'description': 'Advanced image generation'
                }
            ]
        }
        cache.set(cache_key, models_data, 3600)  # Cache for 1 hour
    
    return Response(models_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Comprehensive health check endpoint
    """
    health_data = cache.get('system_health', {})
    
    if not health_data:
        health_data = {
            'status': 'unknown',
            'timestamp': time.time(),
            'message': 'Health data not available'
        }
    
    status_code = 200 if health_data.get('status') == 'healthy' else 503
    return JsonResponse(health_data, status=status_code)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analytics(request):
    """
    Get system analytics with caching
    """
    analytics_data = cache.get('analytics_report')
    
    if not analytics_data:
        analytics_data = {
            'message': 'Analytics data not available',
            'timestamp': time.time()
        }
    
    return Response(analytics_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_status(request, task_id):
    """
    Get Celery task status
    """
    try:
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': result.status,
            'ready': result.ready(),
        }
        
        if result.ready():
            if result.successful():
                response_data['result'] = result.result
            else:
                response_data['error'] = str(result.result)
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"Task status check failed: {str(e)}")
        return Response(
            {'error': 'Failed to check task status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_user_id_from_request(request):
    """Helper function to get user ID from request"""
    user = request.user
    if hasattr(user, 'id'):
        return str(user.id)
    elif hasattr(user, 'username'):
        return user.username
    else:
        return 'anonymous'


# Error handlers
def handler404(request, exception):
    """Custom 404 handler"""
    return JsonResponse({
        'error': 'Not found',
        'message': 'The requested resource was not found',
        'status_code': 404
    }, status=404)


def handler500(request):
    """Custom 500 handler"""
    return JsonResponse({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'status_code': 500
    }, status=500)


def chat_interface(request):
    """
    Serve the main chat interface
    """
    from django.shortcuts import render
    return render(request, 'chat/index.html')
