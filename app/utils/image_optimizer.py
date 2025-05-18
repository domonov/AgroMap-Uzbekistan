"""Image optimization utilities for AgroMap."""
from PIL import Image
import os
from io import BytesIO

def optimize_image(image_path, output_path=None, max_size=800, quality=85):
    """
    Optimize an image by:
    1. Resizing if larger than max_size
    2. Converting to WebP format
    3. Optimizing quality
    """
    try:
        with Image.open(image_path) as img:
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # Calculate new size while maintaining aspect ratio
            width, height = img.size
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Determine output path
            if not output_path:
                dirname, filename = os.path.split(image_path)
                basename, _ = os.path.splitext(filename)
                output_path = os.path.join(dirname, f"{basename}.webp")
            
            # Save as WebP with optimization
            img.save(output_path, 'WEBP', quality=quality, optimize=True)
            return output_path
    except Exception as e:
        print(f"Error optimizing image {image_path}: {e}")
        return None

def create_responsive_images(image_path, output_dir=None, sizes=[192, 512, 1024]):
    """Create responsive image versions for different screen sizes."""
    try:
        if not output_dir:
            output_dir = os.path.dirname(image_path)
        
        with Image.open(image_path) as img:
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            basename = os.path.splitext(os.path.basename(image_path))[0]
            results = []
            
            for size in sizes:
                # Resize maintaining aspect ratio
                width, height = img.size
                if width > height:
                    new_width = size
                    new_height = int(height * (size / width))
                else:
                    new_height = size
                    new_width = int(width * (size / height))
                
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                output_path = os.path.join(output_dir, f"{basename}-{size}.webp")
                resized.save(output_path, 'WEBP', quality=85, optimize=True)
                results.append(output_path)
            
            return results
    except Exception as e:
        print(f"Error creating responsive images for {image_path}: {e}")
        return []

def get_image_srcset(image_path, sizes=[192, 512, 1024]):
    """Generate srcset string for responsive images."""
    try:
        results = create_responsive_images(image_path, sizes=sizes)
        srcset = []
        for path in results:
            size = path.split('-')[-1].split('.')[0]
            srcset.append(f"{path} {size}w")
        return ', '.join(srcset)
    except Exception as e:
        print(f"Error generating srcset for {image_path}: {e}")
        return ''
