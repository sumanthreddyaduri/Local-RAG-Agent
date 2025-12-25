import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the Root of Trust
# All file operations must be contained within this directory
ACTIVE_WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
SAFE_ROOT = os.path.join(ACTIVE_WORKSPACE_ROOT, "uploaded_files")

# Ensure it exists
os.makedirs(SAFE_ROOT, exist_ok=True)

# Actions that require Human Approval
DESTRUCTIVE_ACTIONS = {
    "delete_document",
    "delete_file",
    "overwrite_file",
    "delete_all_files"
}

def is_safe_path(path):
    """
    Verifies that a path is strictly within the SAFE_ROOT.
    Prevents Directory Traversal Attacks (e.g. ../../../Windows).
    """
    try:
        # Resolve user path to absolute
        # If input is just 'file.txt', join with root
        if not os.path.isabs(path):
            abs_path = os.path.abspath(os.path.join(SAFE_ROOT, path))
        else:
            abs_path = os.path.abspath(path)

        # Common path check
        # 'commonpath' raises ValueError if paths are on different drives (Windows)
        # or just returns the common prefix
        common = os.path.commonpath([abs_path, SAFE_ROOT])
        
        # On Windows, paths are case-insensitive, but commonpath usually handles canonicalization
        # We ensure the common prefix is EXACTLY the SAFE_ROOT
        return common == SAFE_ROOT
    except Exception as e:
        logger.error(f"Security check failed for path {path}: {e}")
        return False

def analyze_tool_call(tool_name, args):
    """
    analyzes a tool call to determine if it requires approval.
    Returns: (requires_approval: bool, reason: str)
    """
    if tool_name in DESTRUCTIVE_ACTIONS:
        return True, f"Action '{tool_name}' is destructive."
    
    # Path checking for file operations
    if "filename" in args:
        if not is_safe_path(args["filename"]):
            raise PermissionError(f"Access Denied: {args['filename']} is outside the safe sandbox.")
            
    return False, "Safe"
