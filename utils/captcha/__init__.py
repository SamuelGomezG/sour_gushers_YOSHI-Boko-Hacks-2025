from PIL import Image, ImageDraw, ImageFont
import random
import string

'''
def generate_captcha(text: str = None, width: int = 200, height: int = 80) -> Image:

    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    draw.rectangle([0, 0, width-1, height-1], outline=(200, 200, 200))
    
    font = ImageFont.load_default()
    
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) // 2 - text_bbox[0]  
    y = (height - text_height) // 2 - text_bbox[1]  
    
    draw.text((x, y), text, font=font, fill=(0, 0, 0))
    
    return image
'''

def generate_captcha(text: str = None, width: int = 200, height: int = 80) -> Image:
    # If no text is provided, generate random alphanumeric text
    if text is None:
        text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    # Create a new image with white background
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Add some noise: draw random lines and dots on the image
    for _ in range(3):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)), width=1)
    
    for _ in range(100):
        x, y = random.randint(0, width), random.randint(0, height)
        draw.point((x, y), fill=(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)))
    
    # Draw a rectangle around the image
    draw.rectangle([0, 0, width-1, height-1], outline=(200, 200, 200))

    # Use a basic font
    font = ImageFont.load_default()

    # Calculate text width and height, and center it on the image
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Slight distortion of text: randomize position slightly
    x = (width - text_width) // 2 - random.randint(-5, 5)  
    y = (height - text_height) // 2 - random.randint(-5, 5)  
    
    # Draw the captcha text on the image with black color
    draw.text((x, y), text, font=font, fill=(0, 0, 0))
    
    return image