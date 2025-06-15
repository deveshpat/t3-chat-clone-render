from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Conversation, Message, FileUpload, ConversationShare, APIUsage

# UserProfile admin removed as it's not in the models

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['created_at', 'token_count']
    fields = ['role', 'content_preview', 'model', 'token_count', 'created_at']
    
    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:100]
            if len(obj.content) > 100:
                preview += "..."
            return preview
        return "-"
    content_preview.short_description = 'Content Preview'

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user_id', 'message_count', 'created_at', 'updated_at', 'is_archived']
    list_filter = ['created_at', 'updated_at', 'is_archived']
    search_fields = ['title', 'user_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'message_count']
    inlines = [MessageInline]
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('messages')

class FileUploadInline(admin.TabularInline):
    model = FileUpload
    extra = 0
    readonly_fields = ['created_at', 'file_size_display']
    fields = ['original_filename', 'content_type', 'file_size_display', 'created_at']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = 'File Size'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation_title', 'role', 'content_preview', 'model', 'token_count', 'created_at']
    list_filter = ['role', 'model', 'created_at']
    search_fields = ['content', 'conversation__title', 'conversation__user_id']
    readonly_fields = ['id', 'created_at', 'token_count', 'conversation_link']
    inlines = [FileUploadInline]
    
    fieldsets = (
        (None, {
            'fields': ('conversation_link', 'role', 'model')
        }),
        ('Content', {
            'fields': ('content',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('token_count', 'created_at'),
            'classes': ('collapse',)
        })
    )
    
    def conversation_title(self, obj):
        return obj.conversation.title
    conversation_title.short_description = 'Conversation'
    conversation_title.admin_order_field = 'conversation__title'
    
    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:150]
            if len(obj.content) > 150:
                preview += "..."
            return preview
        return "-"
    content_preview.short_description = 'Content Preview'
    
    def conversation_link(self, obj):
        if obj.conversation:
            url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
            return format_html('<a href="{}">{}</a>', url, obj.conversation.title)
        return "-"
    conversation_link.short_description = 'Conversation'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('conversation')

@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'content_type', 'file_size_display', 'message_preview', 'created_at']
    list_filter = ['content_type', 'created_at']
    search_fields = ['original_filename', 'message__content', 'message__conversation__title']
    readonly_fields = ['created_at', 'file_size_display', 'message_link']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = 'File Size'
    
    def message_preview(self, obj):
        if obj.message and obj.message.content:
            preview = obj.message.content[:100]
            if len(obj.message.content) > 100:
                preview += "..."
            return preview
        return "-"
    message_preview.short_description = 'Message Preview'
    
    def message_link(self, obj):
        if obj.message:
            url = reverse('admin:chat_message_change', args=[obj.message.id])
            return format_html('<a href="{}">View Message</a>', url)
        return "-"
    message_link.short_description = 'Message'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'message__conversation')

@admin.register(ConversationShare)
class ConversationShareAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'share_token', 'is_public', 'expires_at', 'created_at']
    list_filter = ['is_public', 'created_at', 'expires_at']
    search_fields = ['conversation__title', 'share_token']
    readonly_fields = ['share_token', 'created_at']

@admin.register(APIUsage)
class APIUsageAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'endpoint', 'tokens_used', 'status_code', 'created_at']
    list_filter = ['endpoint', 'created_at']
    search_fields = ['user_id', 'endpoint']
    readonly_fields = ['created_at']

# Custom admin site configuration
admin.site.site_header = "T3 Chat Clone Administration"
admin.site.site_title = "T3 Chat Admin"
admin.site.index_title = "Welcome to T3 Chat Administration"
