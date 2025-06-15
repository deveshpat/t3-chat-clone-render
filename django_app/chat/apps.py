from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'T3 Chat Clone'
    
    def ready(self):
        """
        Initialize the app when Django starts
        """
        # Import signal handlers
        try:
            import chat.signals
        except ImportError:
            pass
        
        # Initialize any background tasks or services
        self.initialize_services()
    
    def initialize_services(self):
        """
        Initialize background services and tasks
        """
        # This could include starting background workers,
        # initializing caches, or other startup tasks
        pass
