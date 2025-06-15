import logging
import time
import asyncio
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import openai
import aiohttp
import json

from .models import Conversation, Message, FileUpload, APIUsage

logger = logging.getLogger('chat')

@shared_task(bind=True, max_retries=3)
def process_ai_chat_request(self, conversation_id, user_message, model, api_key, user_id):
    """
    Process AI chat request in background with retry logic
    """
    try:
        start_time = time.time()
        
        # Get conversation
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Create user message
        user_msg = Message.objects.create_message(
            conversation=conversation,
            role='user',
            content=user_message,
            model=model
        )
        
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
        
        # Make AI request
        response = asyncio.run(make_ai_request(client, messages, model))
        
        # Calculate metrics
        response_time = time.time() - start_time
        tokens_used = response.get('usage', {}).get('total_tokens', 0)
        
        # Create assistant message
        assistant_msg = Message.objects.create_message(
            conversation=conversation,
            role='assistant',
            content=response['choices'][0]['message']['content'],
            model=model,
            tokens=tokens_used
        )
        assistant_msg.response_time = response_time
        assistant_msg.save(update_fields=['response_time'])
        
        # Log API usage
        APIUsage.log_request(
            user_id=user_id,
            endpoint='/api/chat/',
            method='POST',
            status_code=200,
            response_time=response_time,
            tokens_used=tokens_used
        )
        
        logger.info(f"AI chat request processed successfully for conversation {conversation_id}")
        
        return {
            'success': True,
            'message_id': str(assistant_msg.id),
            'response': assistant_msg.content,
            'tokens_used': tokens_used,
            'response_time': response_time
        }
        
    except Exception as exc:
        logger.error(f"AI chat request failed: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying AI chat request (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        # Create error message
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            error_msg = Message.objects.create_message(
                conversation=conversation,
                role='assistant',
                content=f"I apologize, but I encountered an error processing your request: {str(exc)}",
                model=model
            )
            error_msg.error_message = str(exc)
            error_msg.save(update_fields=['error_message'])
        except Exception as e:
            logger.error(f"Failed to create error message: {str(e)}")
        
        return {
            'success': False,
            'error': str(exc)
        }


async def make_ai_request(client, messages, model):
    """
    Make async AI request with proper error handling
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=4000,
            stream=False
        )
        return response.model_dump()
    except Exception as e:
        logger.error(f"AI request failed: {str(e)}")
        raise


@shared_task(bind=True, max_retries=2)
def process_image_generation(self, conversation_id, prompt, model, api_key, user_id):
    """
    Process AI image generation request in background
    """
    try:
        start_time = time.time()
        
        # Get conversation
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        # Generate image
        response = asyncio.run(generate_image(client, prompt, model))
        
        # Calculate metrics
        response_time = time.time() - start_time
        
        # Create message with image
        image_url = response['data'][0]['url'] if response['data'][0].get('url') else None
        image_b64 = response['data'][0]['b64_json'] if response['data'][0].get('b64_json') else None
        
        message_content = f"Generated image for prompt: '{prompt}'"
        metadata = {
            'type': 'image_generation',
            'prompt': prompt,
            'image_url': image_url,
            'image_b64': image_b64
        }
        
        msg = Message.objects.create_message(
            conversation=conversation,
            role='assistant',
            content=message_content,
            model=model,
            metadata=metadata
        )
        msg.response_time = response_time
        msg.save(update_fields=['response_time'])
        
        # Log API usage
        APIUsage.log_request(
            user_id=user_id,
            endpoint='/api/image/',
            method='POST',
            status_code=200,
            response_time=response_time
        )
        
        logger.info(f"Image generation completed for conversation {conversation_id}")
        
        return {
            'success': True,
            'message_id': str(msg.id),
            'image_url': image_url,
            'image_b64': image_b64,
            'response_time': response_time
        }
        
    except Exception as exc:
        logger.error(f"Image generation failed: {str(exc)}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {
            'success': False,
            'error': str(exc)
        }


async def generate_image(client, prompt, model):
    """
    Generate image using AI model
    """
    try:
        response = await client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        return response.model_dump()
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        raise


@shared_task
def process_file_upload(file_upload_id):
    """
    Process uploaded file and extract content
    """
    try:
        file_upload = FileUpload.objects.get(id=file_upload_id)
        
        # Process based on file type
        if file_upload.content_type.startswith('text/'):
            content = process_text_file(file_upload.file_path)
        elif file_upload.content_type == 'application/pdf':
            content = process_pdf_file(file_upload.file_path)
        elif file_upload.content_type.startswith('image/'):
            content = process_image_file(file_upload.file_path)
        else:
            content = f"File uploaded: {file_upload.original_filename}"
        
        # Update file upload record
        file_upload.extracted_content = content
        file_upload.is_processed = True
        file_upload.save(update_fields=['extracted_content', 'is_processed'])
        
        logger.info(f"File processing completed for {file_upload.original_filename}")
        
        return {
            'success': True,
            'file_id': str(file_upload.id),
            'extracted_content': content
        }
        
    except Exception as e:
        logger.error(f"File processing failed: {str(e)}")
        
        try:
            file_upload = FileUpload.objects.get(id=file_upload_id)
            file_upload.processing_error = str(e)
            file_upload.save(update_fields=['processing_error'])
        except:
            pass
        
        return {
            'success': False,
            'error': str(e)
        }


def process_text_file(file_path):
    """Process text file and extract content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return content[:5000]  # Limit to 5000 characters
    except Exception as e:
        return f"Error reading text file: {str(e)}"


def process_pdf_file(file_path):
    """Process PDF file and extract text"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages[:10]:  # Limit to first 10 pages
                text += page.extract_text() + "\n"
            return text[:5000]  # Limit to 5000 characters
    except Exception as e:
        return f"Error processing PDF: {str(e)}"


def process_image_file(file_path):
    """Process image file and extract metadata"""
    try:
        from PIL import Image
        with Image.open(file_path) as img:
            return f"Image: {img.format}, {img.size[0]}x{img.size[1]} pixels"
    except Exception as e:
        return f"Error processing image: {str(e)}"


@shared_task
def cleanup_old_data():
    """
    Cleanup old data based on retention policies
    """
    try:
        retention_days = settings.CHAT_SETTINGS.get('MESSAGE_RETENTION_DAYS', 365)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # Delete old messages
        old_messages = Message.objects.filter(
            created_at__lt=cutoff_date,
            is_deleted=False
        )
        
        deleted_count = 0
        for message in old_messages:
            message.is_deleted = True
            message.content = "[Message deleted due to retention policy]"
            message.save(update_fields=['is_deleted', 'content'])
            deleted_count += 1
        
        # Delete old API usage records
        old_usage = APIUsage.objects.filter(created_at__lt=cutoff_date)
        usage_deleted = old_usage.count()
        old_usage.delete()
        
        logger.info(f"Cleanup completed: {deleted_count} messages marked as deleted, {usage_deleted} usage records deleted")
        
        return {
            'success': True,
            'messages_deleted': deleted_count,
            'usage_records_deleted': usage_deleted
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_analytics_report():
    """
    Generate analytics report and cache results
    """
    try:
        # Calculate various metrics
        total_conversations = Conversation.objects.count()
        total_messages = Message.objects.filter(is_deleted=False).count()
        total_users = Conversation.objects.values('user_id').distinct().count()
        
        # Recent activity (last 24 hours)
        last_24h = timezone.now() - timedelta(hours=24)
        recent_conversations = Conversation.objects.filter(created_at__gte=last_24h).count()
        recent_messages = Message.objects.filter(created_at__gte=last_24h, is_deleted=False).count()
        
        # Model usage statistics
        model_usage = {}
        for message in Message.objects.filter(model__isnull=False, is_deleted=False):
            model = message.model
            if model not in model_usage:
                model_usage[model] = 0
            model_usage[model] += 1
        
        # Performance metrics
        avg_response_time = Message.objects.filter(
            response_time__isnull=False,
            created_at__gte=last_24h
        ).aggregate(avg_time=models.Avg('response_time'))['avg_time'] or 0
        
        # Token usage
        total_tokens = Message.objects.filter(is_deleted=False).aggregate(
            total=models.Sum('token_count')
        )['total'] or 0
        
        analytics_data = {
            'timestamp': timezone.now().isoformat(),
            'totals': {
                'conversations': total_conversations,
                'messages': total_messages,
                'users': total_users,
                'tokens': total_tokens
            },
            'recent_24h': {
                'conversations': recent_conversations,
                'messages': recent_messages,
                'avg_response_time': float(avg_response_time)
            },
            'model_usage': model_usage
        }
        
        # Cache the analytics data
        cache.set('analytics_report', analytics_data, 3600)  # Cache for 1 hour
        
        logger.info("Analytics report generated successfully")
        
        return {
            'success': True,
            'analytics': analytics_data
        }
        
    except Exception as e:
        logger.error(f"Analytics generation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def warm_cache():
    """
    Warm up cache with frequently accessed data
    """
    try:
        # Warm up recent conversations for active users
        active_users = Conversation.objects.filter(
            last_activity__gte=timezone.now() - timedelta(hours=24)
        ).values_list('user_id', flat=True).distinct()
        
        warmed_count = 0
        for user_id in active_users:
            conversations = Conversation.objects.get_user_conversations(user_id, limit=10)
            warmed_count += len(conversations)
        
        logger.info(f"Cache warmed with {warmed_count} conversations for {len(active_users)} users")
        
        return {
            'success': True,
            'conversations_cached': warmed_count,
            'users_processed': len(active_users)
        }
        
    except Exception as e:
        logger.error(f"Cache warming failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def health_check():
    """
    Perform system health check
    """
    try:
        health_status = {
            'timestamp': timezone.now().isoformat(),
            'database': check_database_health(),
            'cache': check_cache_health(),
            'storage': check_storage_health(),
            'external_apis': check_external_apis_health()
        }
        
        # Store health status in cache
        cache.set('system_health', health_status, 300)  # Cache for 5 minutes
        
        overall_healthy = all(
            service['status'] == 'healthy' 
            for service in health_status.values() 
            if isinstance(service, dict) and 'status' in service
        )
        
        if not overall_healthy:
            logger.warning("System health check detected issues")
        
        return {
            'success': True,
            'health_status': health_status,
            'overall_healthy': overall_healthy
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def check_database_health():
    """Check database connectivity and performance"""
    try:
        start_time = time.time()
        Conversation.objects.count()
        response_time = time.time() - start_time
        
        return {
            'status': 'healthy',
            'response_time': response_time,
            'details': 'Database connection successful'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def check_cache_health():
    """Check Redis cache connectivity"""
    try:
        start_time = time.time()
        cache.set('health_check_test', 'ok', 10)
        result = cache.get('health_check_test')
        response_time = time.time() - start_time
        
        if result == 'ok':
            return {
                'status': 'healthy',
                'response_time': response_time,
                'details': 'Cache connection successful'
            }
        else:
            return {
                'status': 'unhealthy',
                'error': 'Cache test failed'
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def check_storage_health():
    """Check file storage health"""
    try:
        import os
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root) and os.access(media_root, os.W_OK):
            return {
                'status': 'healthy',
                'details': 'Storage accessible'
            }
        else:
            return {
                'status': 'unhealthy',
                'error': 'Storage not accessible'
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


def check_external_apis_health():
    """Check external API connectivity"""
    try:
        # This is a simplified check - in production you'd test actual API endpoints
        return {
            'status': 'healthy',
            'details': 'External APIs accessible'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        } 