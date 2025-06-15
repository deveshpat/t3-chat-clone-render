import json
import time
import logging
import traceback
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from rest_framework import status

logger = logging.getLogger('chat')

class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Comprehensive error handling middleware with structured error responses
    """
    
    def process_exception(self, request, exception):
        """Handle exceptions and return structured error responses"""
        
        # Log the error with full context
        error_id = f"error_{int(time.time() * 1000)}"
        logger.error(
            f"Error ID: {error_id} | Path: {request.path} | Method: {request.method} | "
            f"User: {getattr(request.user, 'id', 'Anonymous')} | "
            f"Exception: {str(exception)} | Traceback: {traceback.format_exc()}"
        )
        
        # Determine if this is an API request
        is_api_request = (
            request.path.startswith('/api/') or 
            request.content_type == 'application/json' or
            'application/json' in request.META.get('HTTP_ACCEPT', '')
        )
        
        if is_api_request:
            # Return structured JSON error response
            error_response = {
                'error': True,
                'error_id': error_id,
                'message': 'An unexpected error occurred',
                'timestamp': int(time.time()),
            }
            
            # Add debug information in development
            if settings.DEBUG:
                error_response.update({
                    'debug': {
                        'exception_type': type(exception).__name__,
                        'exception_message': str(exception),
                        'traceback': traceback.format_exc().split('\n')
                    }
                })
            
            return JsonResponse(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                safe=False
            )
        
        # Let Django handle non-API errors normally
        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Advanced request logging and performance monitoring middleware
    """
    
    def process_request(self, request):
        """Log incoming requests and start performance tracking"""
        request._start_time = time.time()
        
        # Log API requests
        if request.path.startswith('/api/'):
            logger.info(
                f"API Request | Method: {request.method} | Path: {request.path} | "
                f"User: {getattr(request.user, 'id', 'Anonymous')} | "
                f"IP: {self.get_client_ip(request)} | "
                f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')[:100]}"
            )
    
    def process_response(self, request, response):
        """Log response details and performance metrics"""
        
        # Calculate request duration
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # Log API responses
            if request.path.startswith('/api/'):
                logger.info(
                    f"API Response | Method: {request.method} | Path: {request.path} | "
                    f"Status: {response.status_code} | Duration: {duration:.3f}s | "
                    f"User: {getattr(request.user, 'id', 'Anonymous')}"
                )
                
                # Track slow requests
                if duration > 2.0:  # Log slow requests (>2 seconds)
                    logger.warning(
                        f"Slow Request | Duration: {duration:.3f}s | "
                        f"Path: {request.path} | Method: {request.method}"
                    )
                
                # Store performance metrics in cache
                self.store_performance_metrics(request.path, duration, response.status_code)
        
        return response
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def store_performance_metrics(self, path, duration, status_code):
        """Store performance metrics in Redis for monitoring"""
        try:
            # Create metrics key
            metrics_key = f"performance_metrics:{path.replace('/', '_')}"
            
            # Get existing metrics or create new
            metrics = cache.get(metrics_key, {
                'total_requests': 0,
                'total_duration': 0,
                'avg_duration': 0,
                'max_duration': 0,
                'min_duration': float('inf'),
                'status_codes': {},
                'last_updated': time.time()
            })
            
            # Update metrics
            metrics['total_requests'] += 1
            metrics['total_duration'] += duration
            metrics['avg_duration'] = metrics['total_duration'] / metrics['total_requests']
            metrics['max_duration'] = max(metrics['max_duration'], duration)
            metrics['min_duration'] = min(metrics['min_duration'], duration)
            metrics['status_codes'][str(status_code)] = metrics['status_codes'].get(str(status_code), 0) + 1
            metrics['last_updated'] = time.time()
            
            # Store updated metrics (expire after 1 hour)
            cache.set(metrics_key, metrics, 3600)
            
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {str(e)}")


class SecurityMiddleware(MiddlewareMixin):
    """
    Enhanced security middleware for API protection
    """
    
    def process_request(self, request):
        """Apply security checks to incoming requests"""
        
        # Rate limiting check (basic implementation)
        if request.path.startswith('/api/'):
            client_ip = self.get_client_ip(request)
            rate_limit_key = f"rate_limit:{client_ip}"
            
            # Get current request count
            current_count = cache.get(rate_limit_key, 0)
            
            # Check if rate limit exceeded
            if current_count >= 1000:  # 1000 requests per hour
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JsonResponse({
                    'error': True,
                    'message': 'Rate limit exceeded. Please try again later.',
                    'retry_after': 3600
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Increment counter
            cache.set(rate_limit_key, current_count + 1, 3600)
        
        return None
    
    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CacheMiddleware(MiddlewareMixin):
    """
    Intelligent caching middleware for API responses
    """
    
    CACHEABLE_PATHS = [
        '/api/models/',
        '/api/health/',
    ]
    
    def process_request(self, request):
        """Check for cached responses"""
        if request.method == 'GET' and any(request.path.startswith(path) for path in self.CACHEABLE_PATHS):
            cache_key = f"api_cache:{request.path}:{request.GET.urlencode()}"
            cached_response = cache.get(cache_key)
            
            if cached_response:
                logger.debug(f"Cache hit for: {request.path}")
                return JsonResponse(cached_response, safe=False)
        
        return None
    
    def process_response(self, request, response):
        """Cache successful GET responses"""
        if (request.method == 'GET' and 
            response.status_code == 200 and
            any(request.path.startswith(path) for path in self.CACHEABLE_PATHS)):
            
            try:
                cache_key = f"api_cache:{request.path}:{request.GET.urlencode()}"
                response_data = json.loads(response.content.decode('utf-8'))
                cache.set(cache_key, response_data, 300)  # Cache for 5 minutes
                logger.debug(f"Cached response for: {request.path}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # Skip caching if response is not JSON
        
        return response


class HealthCheckMiddleware(MiddlewareMixin):
    """
    Health check middleware for monitoring and load balancing
    """
    
    def process_request(self, request):
        """Handle health check requests"""
        if request.path == '/health/':
            health_data = {
                'status': 'healthy',
                'timestamp': int(time.time()),
                'version': '1.0.0',
                'services': {
                    'database': self.check_database(),
                    'cache': self.check_cache(),
                    'celery': self.check_celery(),
                }
            }
            
            # Determine overall health
            all_healthy = all(service['status'] == 'healthy' for service in health_data['services'].values())
            if not all_healthy:
                health_data['status'] = 'degraded'
            
            status_code = 200 if all_healthy else 503
            return JsonResponse(health_data, status=status_code)
        
        return None
    
    def check_database(self):
        """Check database connectivity"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {'status': 'healthy', 'response_time': 0.001}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    def check_cache(self):
        """Check Redis cache connectivity"""
        try:
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            if result == 'ok':
                return {'status': 'healthy', 'response_time': 0.001}
            else:
                return {'status': 'unhealthy', 'error': 'Cache test failed'}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    def check_celery(self):
        """Check Celery worker connectivity"""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            if stats:
                return {'status': 'healthy', 'workers': len(stats)}
            else:
                return {'status': 'unhealthy', 'error': 'No workers available'}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)} 