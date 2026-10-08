from slowapi import Limiter
from starlette.requests import Request
from functools import wraps

class CustomLimiter(Limiter):
    def limit(self, limit_string: str, key_func=None):
        def decorator(func):
            # Get the original decorator from the parent class
            original_decorator = super(CustomLimiter, self).limit(limit_string, key_func=key_func)
            
            # Apply the original decorator to the function
            limited_func = original_decorator(func)

            @wraps(func)
            async def wrapper(*args, **kwargs):
                request: Request = None
                if "request" in kwargs:
                    request = kwargs["request"]
                else:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                if request and request.method.lower() == "options":
                    # If it's an OPTIONS request, bypass the rate limiter
                    return await func(*args, **kwargs)
                
                # Otherwise, call the rate-limited function
                return await limited_func(*args, **kwargs)

            return wrapper
        return decorator
