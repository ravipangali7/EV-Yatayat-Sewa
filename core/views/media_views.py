"""
Media file serving views.

This module provides views to serve media files without requiring authentication.
This is necessary because Django admin authentication intercepts media file requests.
"""
from django.views.static import serve
from django.conf import settings


def serve_media(request, path):
    """
    Serve media files without requiring authentication.
    
    This view bypasses Django's authentication middleware to allow
    unauthenticated access to media files (images, documents, etc.).
    
    Args:
        request: The HTTP request object
        path: The path to the media file relative to MEDIA_ROOT
        
    Returns:
        HttpResponse with the file content, or Http404 if file not found
    """
    return serve(request, path, document_root=settings.MEDIA_ROOT)
