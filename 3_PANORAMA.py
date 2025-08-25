import os
import pandas as pd
import cv2

# Disable OpenCL usage in OpenCV
cv2.ocl.setUseOpenCL(False)

# Folder paths
images_folder = r"C:\GSV\images"
panoramas_folder = r"C:\GSV\panoramas"
excel_file = r"C:\GSV\panoramas_metadata.xlsx"  # Path to the Excel file

# Load the CSV file with coordinates and status
csv_file = r'C:\GSV\lisbon_streetview_urls_with_status_data.csv'
df = pd.read_csv(csv_file)

# Filter rows with non-null Image_Date
df_filtered = df[df['Image_Date'].notnull()]

# Function to create panorama from images using OpenCV
def create_panorama_with_opencv(image_paths):
    
    # Load images with OpenCV
    images = [cv2.imread(image_path) for image_path in image_paths]
    
    # Check if the images were loaded correctly
    if any(img is None for img in images):
        print(f"Error loading one or more images. Please check the files.")
        return None
    
    # Use OpenCV's Stitcher to create a panorama
    stitcher = cv2.Stitcher_create()  # Using createStitcher for version 4.x
    status, panorama = stitcher.stitch(images)
    if status == cv2.Stitcher_OK:
        return panorama
    else:
        print(f"Failed to create panorama with OpenCV. Status: {status}")
        return None

# Create the panoramas folder if it doesn't exist
if not os.path.exists(panoramas_folder):
    os.makedirs(panoramas_folder)

# Counter for panorama filenames
panorama_counter = 1

# List to store panorama data
panorama_metadata = []

# Group images by the same coordinates and date
for (lat, lon, date), group in df_filtered.groupby(['Latitude', 'Longitude', 'Image_Date']):
    
    # List to store image paths
    image_paths = [] 
    
    # Iterate over image names (Image_Name column)
    for _, row in group.iterrows():
        image_name = row['Image_Name']  # Image name as per the Image_Name field
        image_path = os.path.join(images_folder, f"{image_name}.png")  # Check the file with .png extension       
        # Check if the image exists in the folder
        if os.path.exists(image_path):
            image_paths.append(image_path)
        else:
            print(f"Image not found: {image_path}")  
                
    # Create the panorama if there are 4 images
    if len(image_paths) == 4:
        panorama = create_panorama_with_opencv(image_paths)       
        if panorama is not None:
            
            # Sequential panorama filename (1.png, 2.png, etc.)
            panorama_filename = f"{panorama_counter}.png"
                        
            # Path to save the panorama
            panorama_path = os.path.join(panoramas_folder, panorama_filename) 
                      

            # Save the panorama
            cv2.imwrite(panorama_path, panorama)
            print(f"Panorama created and saved at: {panorama_path}")   
                     
            # Add panorama data to the DataFrame
            panorama_metadata.append({
                'Latitude': lat,
                'Longitude': lon,
                'Image_Name': panorama_filename,
                'Image_Date': date
            })           
            
            # Increment the counter for the next panorama
            panorama_counter += 1
        else:
            print(f"Failed to create panorama for: {lat}, {lon}, {date}")
    else:
        print(f"Missing images for the panorama at {lat}, {lon}, {date}. Incomplete images.")

# Create a DataFrame with panorama data
panorama_df = pd.DataFrame(panorama_metadata)

# Save the DataFrame as an Excel file
panorama_df.to_excel(excel_file, index=False)

print(f"Excel file with coordinates and panorama data saved at: {excel_file}")
