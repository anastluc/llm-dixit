from PIL import Image
import os

def split_image(image_path, grid_size, output_dir, offset_x=0, offset_y=0):
    """
    Split an image into a grid of equal-sized smaller images with optional offset.
    
    Args:
        image_path (str): Path to the input image
        grid_size (tuple): Tuple of (rows, columns) for the grid
        output_dir (str): Directory to save the split images
        offset_x (int): Horizontal offset in pixels from left edge
        offset_y (int): Vertical offset in pixels from top edge
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with Image.open(image_path) as img:
        # Get image size
        width, height = img.size
        
        # Calculate tile size
        tile_width = width // grid_size[1]
        tile_height = height // grid_size[0]
        
        # Split the image into tiles
        for i in range(grid_size[0]):  # rows
            for j in range(grid_size[1]):  # columns
                # Calculate coordinates with offset
                left = offset_x + (j * tile_width)
                upper = offset_y + (i * tile_height)
                right = left + tile_width
                lower = upper + tile_height
                
                # Check if the crop area exceeds image boundaries
                if right > width or lower > height:
                    print(f"Warning: Tile {i}_{j} exceeds image boundaries, skipping...")
                    continue
                
                # Crop the image
                tile = img.crop((left, upper, right, lower))
                
                # Save the tile
                output_path = os.path.join(output_dir, f'tile_{i}_{j}.jpg')
                tile.save(output_path, quality=95)

# Example usage
if __name__ == "__main__":
    image_path = "input_image.jpg"
    grid_size = (3, 3)  # 3x3 grid
    output_dir = "split_images"
    offset_x = 100  # 100 pixels from left
    offset_y = 50   # 50 pixels from top
    
    split_image(image_path, grid_size, output_dir, offset_x, offset_y)