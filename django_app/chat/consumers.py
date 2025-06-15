import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from .models import Conversation, Message
from .tasks import process_ai_chat_request

logger = logging.getLogger('chat')

class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user_id = self.get_user_id()
        
        # Validate conversation access
        if not await self.can_access_conversation():
            await self.close(code=4003)
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Track active connection
        await self.track_connection()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'conversation_id': self.conversation_id,
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(f"WebSocket connected: user {self.user_id}, conversation {self.conversation_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Remove connection tracking
        await self.untrack_connection()
        
        logger.info(f"WebSocket disconnected: user {self.user_id}, conversation {self.conversation_id}, code {close_code}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing_start':
                await self.handle_typing_start(data)
            elif message_type == 'typing_stop':
                await self.handle_typing_stop(data)
            elif message_type == 'ping':
                await self.handle_ping(data)
            elif message_type == 'message_reaction':
                await self.handle_message_reaction(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"WebSocket receive error: {str(e)}")
            await self.send_error("Internal server error")
    
    async def handle_chat_message(self, data):
        """Handle incoming chat messages"""
        try:
            content = data.get('content', '').strip()
            model = data.get('model', 'openai/gpt-4o-mini')
            api_key = data.get('api_key')
            
            if not content:
                await self.send_error("Message content cannot be empty")
                return
            
            if not api_key:
                await self.send_error("API key is required")
                return
            
            # Create user message immediately
            message = await self.create_user_message(content, model)
            
            # Broadcast user message to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_broadcast',
                    'message': await self.serialize_message(message),
                    'sender_id': self.user_id
                }
            )
            
            # Process AI response asynchronously
            task_result = process_ai_chat_request.delay(
                conversation_id=self.conversation_id,
                user_message=content,
                model=model,
                api_key=api_key,
                user_id=self.user_id
            )
            
            # Send task ID for tracking
            await self.send(text_data=json.dumps({
                'type': 'processing_started',
                'task_id': task_result.id,
                'message_id': str(message.id)
            }))
            
        except Exception as e:
            logger.error(f"Chat message handling error: {str(e)}")
            await self.send_error("Failed to process message")
    
    async def handle_typing_start(self, data):
        """Handle typing start indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user_id,
                'is_typing': True,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def handle_typing_stop(self, data):
        """Handle typing stop indicator"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user_id,
                'is_typing': False,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def handle_ping(self, data):
        """Handle ping for connection keepalive"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': timezone.now().isoformat()
        }))
    
    async def handle_message_reaction(self, data):
        """Handle message reactions"""
        try:
            message_id = data.get('message_id')
            reaction_type = data.get('reaction_type')
            action = data.get('action', 'add')  # 'add' or 'remove'
            
            if not message_id or not reaction_type:
                await self.send_error("Message ID and reaction type are required")
                return
            
            # Update message reaction
            success = await self.update_message_reaction(message_id, reaction_type, action)
            
            if success:
                # Broadcast reaction update
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'reaction_update',
                        'message_id': message_id,
                        'reaction_type': reaction_type,
                        'action': action,
                        'user_id': self.user_id
                    }
                )
            else:
                await self.send_error("Failed to update reaction")
                
        except Exception as e:
            logger.error(f"Reaction handling error: {str(e)}")
            await self.send_error("Failed to process reaction")
    
    # WebSocket event handlers
    async def chat_message_broadcast(self, event):
        """Broadcast chat message to WebSocket"""
        # Don't send back to sender
        if event.get('sender_id') != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message': event['message']
            }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send back to sender
        if event.get('user_id') != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'is_typing': event['is_typing'],
                'timestamp': event['timestamp']
            }))
    
    async def reaction_update(self, event):
        """Send reaction update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'reaction_type': event['reaction_type'],
            'action': event['action'],
            'user_id': event['user_id']
        }))
    
    async def ai_response_ready(self, event):
        """Send AI response when ready"""
        await self.send(text_data=json.dumps({
            'type': 'ai_response',
            'message': event['message'],
            'task_id': event.get('task_id')
        }))
    
    # Helper methods
    def get_user_id(self):
        """Get user ID from WebSocket scope"""
        user = self.scope.get('user')
        if hasattr(user, 'id'):
            return str(user.id)
        elif hasattr(user, 'username'):
            return user.username
        else:
            return 'anonymous'
    
    @database_sync_to_async
    def can_access_conversation(self):
        """Check if user can access the conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            # For now, allow access if conversation exists
            # In production, implement proper access control
            return True
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def create_user_message(self, content, model):
        """Create user message in database"""
        conversation = Conversation.objects.get(id=self.conversation_id)
        return Message.objects.create_message(
            conversation=conversation,
            role='user',
            content=content,
            model=model
        )
    
    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for WebSocket transmission"""
        return {
            'id': str(message.id),
            'role': message.role,
            'content': message.content,
            'model': message.model,
            'timestamp': message.created_at.isoformat(),
            'metadata': message.metadata
        }
    
    @database_sync_to_async
    def update_message_reaction(self, message_id, reaction_type, action):
        """Update message reaction in database"""
        try:
            message = Message.objects.get(id=message_id)
            if action == 'add':
                message.add_reaction(reaction_type, self.user_id)
            else:
                message.remove_reaction(reaction_type, self.user_id)
            return True
        except Message.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Reaction update error: {str(e)}")
            return False
    
    async def track_connection(self):
        """Track active WebSocket connection"""
        cache_key = f"ws_connections:{self.conversation_id}"
        connections = cache.get(cache_key, set())
        connections.add(self.user_id)
        cache.set(cache_key, connections, 3600)  # 1 hour expiry
    
    async def untrack_connection(self):
        """Remove connection tracking"""
        cache_key = f"ws_connections:{self.conversation_id}"
        connections = cache.get(cache_key, set())
        connections.discard(self.user_id)
        if connections:
            cache.set(cache_key, connections, 3600)
        else:
            cache.delete(cache_key)
    
    async def send_error(self, message):
        """Send error message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': timezone.now().isoformat()
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for system notifications and updates
    """
    
    async def connect(self):
        """Handle notification WebSocket connection"""
        self.user_id = self.get_user_id()
        self.room_group_name = f'notifications_{self.user_id}'
        
        # Join notification group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'notification_connected',
            'user_id': self.user_id,
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(f"Notification WebSocket connected: user {self.user_id}")
    
    async def disconnect(self, close_code):
        """Handle notification WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"Notification WebSocket disconnected: user {self.user_id}")
    
    async def receive(self, text_data):
        """Handle incoming notification messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
            
        except json.JSONDecodeError:
            pass  # Ignore invalid JSON
    
    # Notification event handlers
    async def system_notification(self, event):
        """Send system notification"""
        await self.send(text_data=json.dumps({
            'type': 'system_notification',
            'title': event['title'],
            'message': event['message'],
            'level': event.get('level', 'info'),
            'timestamp': timezone.now().isoformat()
        }))
    
    async def task_completed(self, event):
        """Send task completion notification"""
        await self.send(text_data=json.dumps({
            'type': 'task_completed',
            'task_id': event['task_id'],
            'task_type': event['task_type'],
            'result': event['result'],
            'timestamp': timezone.now().isoformat()
        }))
    
    def get_user_id(self):
        """Get user ID from WebSocket scope"""
        user = self.scope.get('user')
        if hasattr(user, 'id'):
            return str(user.id)
        elif hasattr(user, 'username'):
            return user.username
        else:
            return 'anonymous' 