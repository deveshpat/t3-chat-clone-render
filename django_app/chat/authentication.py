import logging
from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication, exceptions
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('chat')

class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom API Key authentication for secure access to chat endpoints
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using API key
        """
        api_key = self.get_api_key_from_request(request)
        
        if not api_key:
            return None
        
        # Validate API key
        user = self.authenticate_api_key(api_key, request)
        if user:
            return (user, api_key)
        
        return None
    
    def get_api_key_from_request(self, request):
        """
        Extract API key from request headers or query parameters
        """
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # Check X-API-Key header
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            return api_key
        
        # Check query parameter (less secure, for development only)
        if hasattr(request, 'GET'):
            api_key = request.GET.get('api_key')
            if api_key:
                return api_key
        
        return None
    
    def authenticate_api_key(self, api_key, request):
        """
        Validate API key and return associated user
        """
        try:
            # Check cache first for performance
            cache_key = f"api_key_auth:{api_key[:10]}"  # Use first 10 chars for security
            cached_result = cache.get(cache_key)
            
            if cached_result:
                if cached_result == 'invalid':
                    return None
                return cached_result
            
            # For demo purposes, we'll create a simple validation
            # In production, you'd validate against a database
            if self.is_valid_api_key(api_key):
                # Create a pseudo-user for API access
                user = APIUser(api_key=api_key)
                
                # Cache the result for 5 minutes
                cache.set(cache_key, user, 300)
                
                # Log successful authentication
                logger.info(f"API key authentication successful for key: {api_key[:10]}...")
                
                return user
            else:
                # Cache invalid result for 1 minute to prevent brute force
                cache.set(cache_key, 'invalid', 60)
                logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
                return None
                
        except Exception as e:
            logger.error(f"API key authentication error: {str(e)}")
            return None
    
    def is_valid_api_key(self, api_key):
        """
        Validate API key format and authenticity
        """
        # Basic validation - in production, check against database
        if not api_key or len(api_key) < 20:
            return False
        
        # For demo, accept any key starting with 'sk-' (OpenAI format)
        if api_key.startswith('sk-'):
            return True
        
        # Accept any key starting with 'tvly-' (Tavily format)
        if api_key.startswith('tvly-'):
            return True
        
        return False


class APIUser:
    """
    Pseudo-user class for API key authentication
    """
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.id = f"api_user_{hash(api_key) % 10000}"
        self.username = f"api_user_{self.id}"
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False
        self.is_staff = False
        self.is_superuser = False
        self.last_login = timezone.now()
        self.date_joined = timezone.now()
    
    def __str__(self):
        return f"APIUser({self.username})"
    
    def has_perm(self, perm, obj=None):
        """Check if user has specific permission"""
        # API users have limited permissions
        api_permissions = [
            'chat.add_conversation',
            'chat.view_conversation',
            'chat.add_message',
            'chat.view_message',
        ]
        return perm in api_permissions
    
    def has_perms(self, perm_list, obj=None):
        """Check if user has all permissions in list"""
        return all(self.has_perm(perm, obj) for perm in perm_list)
    
    def has_module_perms(self, package_name):
        """Check if user has permissions for a module"""
        return package_name == 'chat'
    
    def get_username(self):
        """Return username"""
        return self.username


class SessionAuthentication(authentication.SessionAuthentication):
    """
    Enhanced session authentication with additional security
    """
    
    def authenticate(self, request):
        """
        Authenticate using Django sessions with enhanced security
        """
        result = super().authenticate(request)
        
        if result:
            user, auth = result
            
            # Additional security checks
            if not self.is_session_valid(request, user):
                logger.warning(f"Invalid session detected for user: {user.username}")
                return None
            
            # Update last activity
            self.update_last_activity(request, user)
            
            return result
        
        return None
    
    def is_session_valid(self, request, user):
        """
        Perform additional session validation
        """
        # Check session age
        session_age = request.session.get('session_created')
        if session_age:
            max_age = timezone.now() - timedelta(hours=24)  # 24 hour max session
            if session_age < max_age.timestamp():
                return False
        
        # Check IP consistency (optional, can be problematic with mobile users)
        # stored_ip = request.session.get('ip_address')
        # current_ip = self.get_client_ip(request)
        # if stored_ip and stored_ip != current_ip:
        #     return False
        
        return True
    
    def update_last_activity(self, request, user):
        """
        Update user's last activity timestamp
        """
        request.session['last_activity'] = timezone.now().timestamp()
        
        # Store in cache for quick access
        cache_key = f"user_activity:{user.id}"
        cache.set(cache_key, timezone.now().timestamp(), 3600)
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 