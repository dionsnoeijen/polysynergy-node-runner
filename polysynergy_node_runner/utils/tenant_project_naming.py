import os
import hashlib
from typing import Tuple, Optional, List


def get_tenant_project_ids() -> Tuple[str, str]:
    """Get tenant and project IDs from environment variables."""
    tenant_id = os.environ.get('TENANT_ID', 'default')
    project_id = os.environ.get('PROJECT_ID', 'default')
    return tenant_id, project_id


def get_short_identifier(identifier: str, max_length: int = 8) -> str:
    """Get shortened version of identifier using MD5 hash if needed."""
    if len(identifier) > max_length:
        return hashlib.md5(identifier.encode()).hexdigest()[:max_length]
    return identifier


def get_tenant_project_prefix(separator: str = "-") -> str:
    """Get tenant-project prefix for naming resources."""
    tenant_id, project_id = get_tenant_project_ids()
    tenant_short = get_short_identifier(tenant_id)
    project_short = get_short_identifier(project_id)
    return f"{tenant_short}{separator}{project_short}"


def get_prefixed_name(
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
    separator: str = "-",
    max_length: Optional[int] = None,
    normalize: bool = True
) -> str:
    """
    Generic helper to create tenant-project resource names.
    
    Args:
        prefix: Optional prefix (default: None)
        suffix: Optional suffix  
        separator: Separator between parts (default: "-")
        max_length: Maximum total length. If exceeded, will shorten hashes
        normalize: Whether to normalize (lowercase, replace underscores) (default: True)
    
    Returns:
        Formatted resource name
        
    Examples:
        get_prefixed_name()  
        # -> "51da7b43-bd58c895"
        
        get_prefixed_name(suffix="media")
        # -> "51da7b43-bd58c895-media"
        
        get_prefixed_name(prefix="polysynergy", suffix="media") 
        # -> "polysynergy-51da7b43-bd58c895-media"
        
        get_prefixed_name(prefix="myapp", suffix="queue", max_length=50)
        # -> "myapp-51da7b-bd58c8-queue" (shortened if needed)
    """
    parts: List[str] = []
    
    # Add prefix if provided
    if prefix:
        parts.append(prefix)
    
    # Always add tenant-project (this is the core)
    tenant_project = get_tenant_project_prefix(separator)
    parts.append(tenant_project)
    
    # Add suffix if provided
    if suffix:
        parts.append(suffix)
    
    # Join parts
    result = separator.join(parts)
    
    # Normalize if requested
    if normalize:
        result = result.lower().replace('_', separator)
    
    # Handle max length by shortening tenant/project hashes if needed
    if max_length and len(result) > max_length:
        # Rebuild with shorter hashes
        parts_short: List[str] = []
        
        if prefix:
            # Shorten prefix if it's the default
            short_prefix = "poly" if prefix == "polysynergy" else prefix[:4]
            parts_short.append(short_prefix)
        
        # Shorter tenant-project hashes
        tenant_id, project_id = get_tenant_project_ids()
        tenant_short = get_short_identifier(tenant_id, 6)
        project_short = get_short_identifier(project_id, 6)
        parts_short.append(f"{tenant_short}{separator}{project_short}")
        
        if suffix:
            parts_short.append(suffix)
        
        result = separator.join(parts_short)
        
        if normalize:
            result = result.lower().replace('_', separator)
    
    return result