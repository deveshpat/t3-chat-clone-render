from rest_framework import serializers
from .models import Conversation, Message, FileUpload, ConversationShare, APIUsage

class ConversationSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for Conversation model
    """
    message_count = serializers.ReadOnlyField()
    total_tokens = serializers.ReadOnlyField()
    last_activity = serializers.ReadOnlyField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'user_id', 'title', 'metadata', 'message_count',
            'total_tokens', 'last_activity', 'model_config',
            'is_archived', 'is_shared', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user_id', 'created_at', 'updated_at']
    
    def validate_title(self, value):
        """Validate conversation title"""
        if len(value.strip()) < 1:
            raise serializers.ValidationError("Title cannot be empty")
        if len(value) > 255:
            raise serializers.ValidationError("Title cannot exceed 255 characters")
        return value.strip()
    
    def validate_metadata(self, value):
        """Validate metadata field"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a valid JSON object")
        return value


class MessageSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for Message model
    """
    conversation_id = serializers.UUIDField(source='conversation.id', read_only=True)
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation_id', 'role', 'content', 'content_preview',
            'model', 'token_count', 'response_time', 'metadata',
            'is_edited', 'is_deleted', 'error_message', 'created_at'
        ]
        read_only_fields = [
            'id', 'conversation_id', 'token_count', 'response_time',
            'is_edited', 'is_deleted', 'error_message', 'created_at'
        ]
    
    def get_content_preview(self, obj):
        """Get a preview of the message content"""
        if len(obj.content) <= 100:
            return obj.content
        return obj.content[:97] + "..."
    
    def validate_content(self, value):
        """Validate message content"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        
        max_length = 10000  # From settings
        if len(value) > max_length:
            raise serializers.ValidationError(f"Message content cannot exceed {max_length} characters")
        
        return value.strip()
    
    def validate_role(self, value):
        """Validate message role"""
        valid_roles = ['user', 'assistant', 'system', 'tool']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Role must be one of: {', '.join(valid_roles)}")
        return value


class FileUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for FileUpload model
    """
    conversation_id = serializers.UUIDField(source='conversation.id', read_only=True)
    file_url = serializers.SerializerMethodField()
    processing_status = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'conversation_id', 'original_filename', 'file_size',
            'content_type', 'file_hash', 'is_processed', 'processing_error',
            'extracted_content', 'metadata', 'file_url', 'processing_status',
            'created_at'
        ]
        read_only_fields = [
            'id', 'conversation_id', 'file_hash', 'is_processed',
            'processing_error', 'extracted_content', 'created_at'
        ]
    
    def get_file_url(self, obj):
        """Get secure file URL"""
        return obj.get_file_url()
    
    def get_processing_status(self, obj):
        """Get file processing status"""
        if obj.processing_error:
            return 'error'
        elif obj.is_processed:
            return 'completed'
        else:
            return 'processing'


class ConversationShareSerializer(serializers.ModelSerializer):
    """
    Serializer for ConversationShare model
    """
    conversation_title = serializers.CharField(source='conversation.title', read_only=True)
    is_expired = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationShare
        fields = [
            'id', 'conversation_title', 'share_token', 'is_public',
            'expires_at', 'allowed_users', 'view_count', 'is_expired',
            'share_url', 'created_at'
        ]
        read_only_fields = [
            'id', 'share_token', 'view_count', 'created_at'
        ]
    
    def get_is_expired(self, obj):
        """Check if share is expired"""
        return obj.is_expired()
    
    def get_share_url(self, obj):
        """Get share URL"""
        return f"/share/{obj.share_token}/"


class APIUsageSerializer(serializers.ModelSerializer):
    """
    Serializer for API usage analytics
    """
    
    class Meta:
        model = APIUsage
        fields = [
            'id', 'user_id', 'endpoint', 'method', 'status_code',
            'response_time', 'tokens_used', 'user_agent', 'ip_address',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ConversationSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for conversation summaries
    """
    recent_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'message_count', 'last_activity',
            'is_archived', 'recent_message'
        ]
    
    def get_recent_message(self, obj):
        """Get the most recent message preview"""
        recent_msg = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if recent_msg:
            return {
                'role': recent_msg.role,
                'content_preview': recent_msg.content[:50] + "..." if len(recent_msg.content) > 50 else recent_msg.content,
                'created_at': recent_msg.created_at
            }
        return None


class MessageCreateSerializer(serializers.Serializer):
    """
    Serializer for creating messages via API
    """
    conversation_id = serializers.UUIDField()
    content = serializers.CharField(max_length=10000)
    model = serializers.CharField(max_length=100, required=False, default='openai/gpt-4o-mini')
    api_key = serializers.CharField(max_length=200)
    stream = serializers.BooleanField(default=False)
    
    def validate_content(self, value):
        """Validate message content"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty")
        return value.strip()
    
    def validate_api_key(self, value):
        """Validate API key format"""
        if not value or len(value) < 20:
            raise serializers.ValidationError("Invalid API key format")
        return value


class ImageGenerationSerializer(serializers.Serializer):
    """
    Serializer for image generation requests
    """
    conversation_id = serializers.UUIDField()
    prompt = serializers.CharField(max_length=1000)
    model = serializers.CharField(max_length=100, required=False, default='stability-ai/stable-diffusion-3-medium')
    api_key = serializers.CharField(max_length=200)
    size = serializers.ChoiceField(choices=['512x512', '1024x1024', '1024x1792'], default='1024x1024')
    
    def validate_prompt(self, value):
        """Validate image generation prompt"""
        if not value or not value.strip():
            raise serializers.ValidationError("Prompt cannot be empty")
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Prompt must be at least 3 characters long")
        return value.strip()


class FileUploadCreateSerializer(serializers.Serializer):
    """
    Serializer for file upload requests
    """
    conversation_id = serializers.UUIDField()
    file = serializers.FileField()
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(f"File size cannot exceed {max_size} bytes")
        
        # Check file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/markdown',
            'application/json', 'text/csv'
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(f"File type {value.content_type} is not allowed")
        
        return value


class AnalyticsSerializer(serializers.Serializer):
    """
    Serializer for analytics data
    """
    timestamp = serializers.DateTimeField(read_only=True)
    totals = serializers.DictField(read_only=True)
    recent_24h = serializers.DictField(read_only=True)
    model_usage = serializers.DictField(read_only=True)
    performance_metrics = serializers.DictField(read_only=True)


class HealthCheckSerializer(serializers.Serializer):
    """
    Serializer for health check data
    """
    status = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)
    services = serializers.DictField(read_only=True)
    version = serializers.CharField(read_only=True)


class TaskStatusSerializer(serializers.Serializer):
    """
    Serializer for Celery task status
    """
    task_id = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    ready = serializers.BooleanField(read_only=True)
    result = serializers.JSONField(read_only=True, required=False)
    error = serializers.CharField(read_only=True, required=False) 