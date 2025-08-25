import re
import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

# ==========================================================
# Opens a Google Street View URL, takes a screenshot and extracts the image capture date
# ==========================================================

def capture_streetview(driver, url, output_file="streetview.png"):
    try:
        driver.get(url)  # Access the Street View URL
        
        # Try to accept cookies if the button appears
        try:
            accept_button = driver.find_element(By.CSS_SELECTOR, 'div.VtwTSb button')
            accept_button.click()
            print("Cookies accepted.")
        except Exception:
            print("No cookie button found or error when clicking.")
        
        # Waits up to 5 seconds for page load
        time.sleep(5)
        
        # Extract the image date (if available)
        try:
            # Attempt to get content from any element containing "/" in the text
            date_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '/')]")
            
            # If any elements are found
            if date_elements:
                # Join the text of all elements containing "/"
                date_text = " ".join([element.text for element in date_elements])
                
                # Use regex to extract the date in mm/yyyy format only
                date_match = re.search(r'\b\d{2}/\d{4}\b', date_text)
                if date_match:
                    date_text = date_match.group(0)
                    print(f"Date found: {date_text}")
                else:
                    print("Date format mm/yyyy not found.")
                    date_text = None  # Set as None if no date found
            else:
                print("No element with '/' found.")
                date_text = None  # Set as None if no date found
        except Exception as e:
            print(f"Error extracting date or element not found: {e}")
            date_text = None  # Set as None if an error occurs
        
        # Hide all divs except the one containing the Street View image
        driver.execute_script(""" 
            // Select all divs on the page
            var allDivs = document.getElementsByTagName('div');
            
            // Loop through all the divs and hide those that do not contain the Street View image
            for (var i = 0; i < allDivs.length; i++) {
                // Check if the div contains the Street View image (canvas with the 'widget-scene-canvas' class)
                if (!allDivs[i].querySelector('.widget-scene-canvas')) {
                    allDivs[i].style.display = 'none'; // Hide the div
                }
            }
        """)

        # Capture and save the screenshot only if the date exists
        if date_text:
            driver.save_screenshot(output_file)
            print(f"Image saved as {output_file}")
            return date_text  # Return the extracted date
        else:
            print("No date found, skipping image capture.")
            return None  # Skip capturing the image if no date is found

    except Exception as e:
        print(f"Error capturing image: {e}")
        return False


def main():
    # File paths
    csv_file = r"C:/GSV/lisbon_streetview_urls.csv"
    output_folder = r"C:/GSV/images"
    output_csv = r"C:/GSV/lisbon_streetview_urls_with_status_data.csv"

    os.makedirs(output_folder, exist_ok=True)  # Ensure the destination folder exists
    
    # Load the CSV
    df = pd.read_csv(csv_file)
    
    # Ensure the 'Image_Name' column is a string to avoid '.0'
    df["Image_Name"] = df["Image_Name"].apply(lambda x: str(int(x)) if isinstance(x, float) else str(x))
    
    if "Image_URL" not in df.columns or "Image_Name" not in df.columns:
        print("CSV is missing required columns: 'Image_URL' and 'Image_Name'.")
        return

    # Add columns for download status and image capture date
    df["Image_Download_Status"] = "Not downloaded"
    df["Image_Date"] = "Unavailable"

    # Selenium browser configuration
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run browser in headless mode (no GUI)
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    # Start the browser
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Apply stealth techniques to avoid being blocked
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine")

    # Loop through each row in the DataFrame
    for index, row in df.iterrows():
        image_url = row["Image_URL"]
        image_name = row["Image_Name"]
        
        # Modify the URL to include a pitch if necessary
        if "&pitch=" not in image_url:
            image_url += "&pitch=0"
        
        output_file = os.path.join(output_folder, f"{image_name}.png")

        # Try to capture the image and get the date
        try:
            date_text = capture_streetview(driver, url=image_url, output_file=output_file)
            
            if date_text:
                df.at[index, "Image_Date"] = date_text
                df.at[index, "Image_Download_Status"] = "Downloaded"
            else:
                df.at[index, "Image_Date"] = "No date"  # No date for images without one
                df.at[index, "Image_Download_Status"] = "Not downloaded"  # Mark as not downloaded if no date
            
        except Exception as e:
            print(f"Error capturing image for {image_url}: {e}")
            df.at[index, "Image_Download_Status"] = "Failed"

        # Save the updated CSV continuously to avoid data loss
        try:
            df.to_csv(output_csv, index=False)
            print(f"CSV file updated: {output_csv}")
        except Exception as e:
            print(f"Error saving the CSV: {e}")

    driver.quit()  # Close the browser
    print("Process completed.")

if __name__ == "__main__":
    main()

