# Run this script to generate extension icons
# Requires Pillow: pip install Pillow

from PIL import Image, ImageDraw

def create_icon(size, output_path):
    """Create a simple gradient icon with a brain/AI symbol."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background circle with gradient-like effect
    margin = size // 8
    for i in range(size // 2):
        # Purple to blue gradient
        r = int(102 + (118 - 102) * i / (size / 2))
        g = int(126 + (75 - 126) * i / (size / 2))
        b = int(234 + (162 - 234) * i / (size / 2))
        
        draw.ellipse(
            [margin + i // 2, margin + i // 2, size - margin - i // 2, size - margin - i // 2],
            fill=(r, g, b, 255)
        )
    
    # Draw a simple "AI" or brain-like symbol
    center = size // 2
    radius = size // 4
    
    # White circle in center
    draw.ellipse(
        [center - radius // 2, center - radius // 2, 
         center + radius // 2, center + radius // 2],
        fill=(255, 255, 255, 200)
    )
    
    # Connection dots
    dot_size = max(2, size // 16)
    positions = [
        (center - radius, center - radius // 2),
        (center + radius, center - radius // 2),
        (center - radius, center + radius // 2),
        (center + radius, center + radius // 2),
        (center, center - radius),
        (center, center + radius),
    ]
    for x, y in positions:
        draw.ellipse([x - dot_size, y - dot_size, x + dot_size, y + dot_size], 
                     fill=(255, 255, 255, 180))
    
    img.save(output_path)
    print(f"Created: {output_path}")

if __name__ == "__main__":
    create_icon(16, "chrome-extension/icons/icon16.png")
    create_icon(48, "chrome-extension/icons/icon48.png")
    create_icon(128, "chrome-extension/icons/icon128.png")
    print("Icons generated successfully!")
