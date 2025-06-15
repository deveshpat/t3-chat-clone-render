from django.db import models
import uuid
import json
import hashlib
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from cryptography.fernet import Fernet
import base64

class TimestampedModel(models.Model):
    """
    Abstract base model with timestamp fields
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        abstract = True


class EncryptedTextField(models.TextField):
    """
    Custom field for encrypted text storage
    """
    
    def __init__(self, *args, **kwargs):
        self.encrypt = kwargs.pop('encrypt', True)
        super().__init__(*args, **kwargs)
    
    def get_encryption_key(self):
        """Get or create encryption key"""
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            # Generate a key for demo purposes
            key = Fernet.generate_key()
        return key
    
    def encrypt_value(self, value):
        """Encrypt the value"""
        if not self.encrypt or not value:
            return value
        
        try:
            key = self.get_encryption_key()
            f = Fernet(key)
            encrypted = f.encrypt(value.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception:
            # Fallback to unencrypted if encryption fails
            return value
    
    def decrypt_value(self, value):
        """Decrypt the value"""
        if not self.encrypt or not value:
            return value
        
        try:
            key = self.get_encryption_key()
            f = Fernet(key)
            decoded = base64.b64decode(value.encode('utf-8'))
            decrypted = f.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception:
            # Return as-is if decryption fails (might be unencrypted)
            return value
    
    def from_db_value(self, value, expression, connection):
        """Decrypt when loading from database"""
        return self.decrypt_value(value)
    
    def to_python(self, value):
        """Convert to Python value"""
        return self.decrypt_value(value)
    
    def get_prep_value(self, value):
        """Encrypt before saving to database"""
        return self.encrypt_value(value)


class ConversationManager(models.Manager):
    """
    Custom manager for Conversation model with caching and optimization
    """
    
    def get_user_conversations(self, user_id, limit=50):
        """Get user conversations with caching"""
        cache_key = f"user_conversations:{user_id}:{limit}"
        conversations = cache.get(cache_key)
        
        if conversations is None:
            conversations = list(
                self.filter(user_id=user_id)
                .select_related()
                .prefetch_related('messages')
                .order_by('-updated_at')[:limit]
            )
            cache.set(cache_key, conversations, 300)  # Cache for 5 minutes
        
        return conversations
    
    def create_conversation(self, user_id, title=None, metadata=None):
        """Create a new conversation with proper initialization"""
        if not title:
            title = f"Chat {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        
        conversation = self.create(
            user_id=user_id,
            title=title,
            metadata=metadata or {}
        )
        
        # Invalidate cache
        cache_key = f"user_conversations:{user_id}:*"
        cache.delete_pattern(cache_key)
        
        return conversation


class Conversation(TimestampedModel):
    """
    Enhanced conversation model with metadata and performance optimizations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100, db_index=True)  # Support both User IDs and API user IDs
    title = models.CharField(max_length=255, default="New Chat")
    
    # Metadata for storing additional conversation information
    metadata = models.JSONField(default=dict, blank=True)
    
    # Performance and analytics fields
    message_count = models.PositiveIntegerField(default=0, db_index=True)
    total_tokens = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True, db_index=True)
    
    # Configuration fields
    model_config = models.JSONField(default=dict, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    is_shared = models.BooleanField(default=False)
    
    # Custom manager
    objects = ConversationManager()
    
    class Meta:
        db_table = 'chat_conversation'
        indexes = [
            models.Index(fields=['user_id', '-last_activity']),
            models.Index(fields=['user_id', 'is_archived']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.title} ({self.user_id})"
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
        
        # Update cache
        cache_key = f"conversation_activity:{self.id}"
        cache.set(cache_key, self.last_activity.timestamp(), 3600)
    
    def increment_message_count(self, tokens=0):
        """Increment message count and token usage"""
        self.message_count += 1
        self.total_tokens += tokens
        self.save(update_fields=['message_count', 'total_tokens'])
    
    def get_recent_messages(self, limit=10):
        """Get recent messages with caching"""
        cache_key = f"conversation_messages:{self.id}:{limit}"
        messages = cache.get(cache_key)
        
        if messages is None:
            messages = list(
                self.messages.select_related()
                .order_by('-created_at')[:limit]
            )
            cache.set(cache_key, messages, 300)
        
        return messages
    
    def get_summary(self):
        """Generate conversation summary"""
        return {
            'id': str(self.id),
            'title': self.title,
            'message_count': self.message_count,
            'total_tokens': self.total_tokens,
            'last_activity': self.last_activity.isoformat(),
            'created_at': self.created_at.isoformat(),
            'is_archived': self.is_archived,
            'metadata': self.metadata
        }


class MessageManager(models.Manager):
    """
    Custom manager for Message model with advanced querying
    """
    
    def create_message(self, conversation, role, content, model=None, metadata=None, tokens=0):
        """Create a message with proper relationships and caching"""
        message = self.create(
            conversation=conversation,
            role=role,
            content=content,
            model=model,
            metadata=metadata or {},
            token_count=tokens
        )
        
        # Update conversation
        conversation.increment_message_count(tokens)
        conversation.update_activity()
        
        # Invalidate relevant caches
        cache.delete(f"conversation_messages:{conversation.id}:*")
        
        return message
    
    def get_conversation_history(self, conversation_id, limit=100):
        """Get conversation history with proper ordering"""
        return self.filter(conversation_id=conversation_id).order_by('created_at')[:limit]


class Message(TimestampedModel):
    """
    Enhanced message model with encryption and metadata
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages',
        db_index=True
    )
    
    # Message content and metadata
    role = models.CharField(
        max_length=20, 
        choices=[
            ('user', 'User'),
            ('assistant', 'Assistant'),
            ('system', 'System'),
            ('tool', 'Tool'),
        ],
        db_index=True
    )
    
    # Encrypted content field
    content = EncryptedTextField()
    
    # AI model information
    model = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    token_count = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    response_time = models.FloatField(null=True, blank=True)  # Response time in seconds
    
    # Message metadata (attachments, reactions, etc.)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Message status and flags
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, db_index=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Custom manager
    objects = MessageManager()
    
    class Meta:
        db_table = 'chat_message'
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['conversation', 'role']),
            models.Index(fields=['model', 'created_at']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
    
    def get_content_hash(self):
        """Generate hash of message content for integrity checking"""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()
    
    def add_reaction(self, reaction_type, user_id):
        """Add a reaction to the message"""
        reactions = self.metadata.get('reactions', {})
        if reaction_type not in reactions:
            reactions[reaction_type] = []
        
        if user_id not in reactions[reaction_type]:
            reactions[reaction_type].append(user_id)
            self.metadata['reactions'] = reactions
            self.save(update_fields=['metadata'])
    
    def remove_reaction(self, reaction_type, user_id):
        """Remove a reaction from the message"""
        reactions = self.metadata.get('reactions', {})
        if reaction_type in reactions and user_id in reactions[reaction_type]:
            reactions[reaction_type].remove(user_id)
            if not reactions[reaction_type]:
                del reactions[reaction_type]
            self.metadata['reactions'] = reactions
            self.save(update_fields=['metadata'])
    
    def get_summary(self):
        """Get message summary for API responses"""
        return {
            'id': str(self.id),
            'role': self.role,
            'content': self.content,
            'model': self.model,
            'token_count': self.token_count,
            'response_time': self.response_time,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata,
            'is_edited': self.is_edited
        }


class FileUpload(TimestampedModel):
    """
    Model for handling file uploads with security and metadata
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='files'
    )
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='files',
        null=True, 
        blank=True
    )
    
    # File information
    original_filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    file_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hash
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    
    # Extracted content (for text files, PDFs, etc.)
    extracted_content = models.TextField(blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'chat_file_upload'
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['file_hash']),
            models.Index(fields=['content_type']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.file_size} bytes)"
    
    def get_file_url(self):
        """Get secure URL for file access"""
        # In production, this would generate a signed URL
        return f"/api/files/{self.id}/"


class ConversationShare(TimestampedModel):
    """
    Model for sharing conversations with others
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='shares'
    )
    
    # Share configuration
    share_token = models.CharField(max_length=64, unique=True, db_index=True)
    is_public = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Access control
    allowed_users = models.JSONField(default=list, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'chat_conversation_share'
    
    def __str__(self):
        return f"Share: {self.conversation.title}"
    
    def is_expired(self):
        """Check if share link is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class APIUsage(TimestampedModel):
    """
    Model for tracking API usage and analytics
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100, db_index=True)
    
    # Request information
    endpoint = models.CharField(max_length=200, db_index=True)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField(db_index=True)
    
    # Performance metrics
    response_time = models.FloatField()
    tokens_used = models.PositiveIntegerField(default=0)
    
    # Request metadata
    user_agent = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField()
    
    class Meta:
        db_table = 'chat_api_usage'
        indexes = [
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['endpoint', 'created_at']),
            models.Index(fields=['status_code', 'created_at']),
        ]
    
    @classmethod
    def log_request(cls, user_id, endpoint, method, status_code, response_time, 
                   tokens_used=0, user_agent='', ip_address=''):
        """Log API request for analytics"""
        return cls.objects.create(
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            tokens_used=tokens_used,
            user_agent=user_agent,
            ip_address=ip_address
        )
