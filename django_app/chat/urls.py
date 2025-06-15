from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.views.generic import TemplateView

# Create router for ViewSets
router = DefaultRouter()
router.register(r'conversations', views.ConversationViewSet, basename='conversation')

urlpatterns = [
    # ViewSet routes
    path('api/', include(router.urls)),
    
    # Chat endpoints
    path('api/chat/', views.chat_message, name='chat_message'),
    path('api/chat/stream/', views.chat_message, name='chat_message_stream'),
    
    # Image generation
    path('api/image/', views.generate_image, name='generate_image'),
    
    # File upload
    path('api/upload/', views.upload_file, name='upload_file'),
    
    # Models and configuration
    path('api/models/', views.get_models, name='get_models'),
    
    # System endpoints
    path('api/health/', views.health_check, name='health_check'),
    path('api/analytics/', views.get_analytics, name='get_analytics'),
    
    # Task management
    path('api/tasks/<str:task_id>/', views.task_status, name='task_status'),
    
    # Health check (for load balancers)
    path('health/', views.health_check, name='health_check_simple'),
    
    # Main chat interface
    path('', views.chat_interface, name='chat_interface'),
] 