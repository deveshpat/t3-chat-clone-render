from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Conversation, Message
import logging

logger = logging.getLogger(__name__)

# UserProfile signals removed as the model doesn't exist

@receiver(post_save, sender=Message)
def update_conversation_timestamp(sender, instance, created, **kwargs):
    """
    Update conversation's updated_at timestamp when a new message is added
    """
    if created and instance.conversation:
        instance.conversation.updated_at = timezone.now()
        instance.conversation.save(update_fields=['updated_at'])
        
        # Update conversation title if it's the first user message
        if (instance.role == 'user' and 
            instance.conversation.title == 'New Chat' and
            instance.content):
            # Use first 50 characters of the message as title
            title = instance.content[:50]
            if len(instance.content) > 50:
                title += "..."
            instance.conversation.title = title
            instance.conversation.save(update_fields=['title'])

@receiver(pre_delete, sender=Conversation)
def log_conversation_deletion(sender, instance, **kwargs):
    """
    Log when a conversation is deleted
    """
    message_count = instance.messages.count()
    logger.info(f"Deleting conversation '{instance.title}' with {message_count} messages for user {instance.user.username}")

@receiver(pre_delete, sender=Message)
def log_message_deletion(sender, instance, **kwargs):
    """
    Log when a message is deleted
    """
    logger.info(f"Deleting message from conversation '{instance.conversation.title}' by user {instance.conversation.user.username}")

@receiver(post_save, sender=Message)
def calculate_token_count(sender, instance, created, **kwargs):
    """
    Calculate and store token count for messages
    """
    if created and instance.content and not instance.token_count:
        # Simple token estimation (roughly 4 characters per token)
        estimated_tokens = len(instance.content) // 4
        instance.token_count = max(1, estimated_tokens)
        instance.save(update_fields=['token_count']) 