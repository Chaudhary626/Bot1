# /bot/utils/ai_moderation.py

# In a real-world scenario, this would use a proper content moderation API.
# For this example, we'll use a simple keyword-based filter.

FORBIDDEN_KEYWORDS = [
    "18+", "adult", "nsfw", "xxx", "crypto", "scam", "hack",
    "free money", "get rich quick", "misleading"
]

def scan_text(text: str) -> bool:
    """
    Scans text for forbidden keywords.
    Returns:
        True if content is safe.
        False if content is unsafe.
    """
    if not text:
        return True
    
    lower_text = text.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in lower_text:
            return False
    return True

async def scan_content(title: str, description: str = "", thumbnail_data: bytes = None) -> bool:
    """
    Main moderation function.
    In the future, thumbnail_data could be sent to an image moderation API.
    """
    if not scan_text(title) or not scan_text(description):
        return False
        
    # Placeholder for image analysis
    if thumbnail_data:
        # E.g., call Google Vision API, AWS Rekognition, etc.
        pass
        
    return True
