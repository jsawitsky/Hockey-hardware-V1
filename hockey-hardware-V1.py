#!/usr/bin/env python3

import sys
import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
import spidev

# Check if the LCD library exists in the current directory
LCD_LIBRARY = "LCD_1inch3.py"
if not os.path.exists(LCD_LIBRARY):
    print(f"Error: {LCD_LIBRARY} not found in current directory.")
    print("Please install the Waveshare LCD library:")
    print("1. git clone https://github.com/waveshare/LCD_Module_RPI.git")
    print("2. cd LCD_Module_RPI/RaspberryPi/python/")
    print(f"3. cp {LCD_LIBRARY} /path/to/your/project/")
    sys.exit(1)

# Import the LCD library from the local directory
import LCD_1inch3

def check_spi():
    """
    Check if SPI is enabled on the Raspberry Pi
    """
    try:
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.close()
        return True
    except Exception as e:
        print("Error: SPI interface not enabled.")
        print("Please enable SPI using:")
        print("1. sudo raspi-config")
        print("2. Navigate to 'Interface Options' -> 'SPI' -> Enable")
        return False

def fetch_nhl_scores(date_str):
    """
    Fetch NHL scores for a given date in YYYY-MM-DD format 
    from the NHL Stats API.
    """
    url = f"https://statsapi.web.nhl.com/api/v1/schedule?startDate={date_str}&endDate={date_str}"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        return data
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def parse_nhl_scores(data):
    """
    Parse the JSON to extract a list of final (or in-progress) scores.
    Return a list of tuples: [(away_team, away_score, home_team, home_score, status), ...]
    """
    scores = []
    if not data or 'dates' not in data:
        return scores

    for date_info in data['dates']:
        for game in date_info['games']:
            away_team = game['teams']['away']['team']['name']
            away_score = game['teams']['away']['score']
            home_team = game['teams']['home']['team']['name']
            home_score = game['teams']['home']['score']
            status = game['status']['abstractGameState']  # e.g., "Final", "Live", etc.
            scores.append((away_team, away_score, home_team, home_score, status))
    return scores

def display_scores_on_lcd(scores):
    """
    Use the Waveshare LCD Python driver to display hockey scores.
    This function will:
     1. Initialize the LCD.
     2. Create a blank image using Pillow.
     3. Draw the scores onto the image.
     4. Send the image to the display.
    """
    try:
        # 1) Initialize the LCD
        disp = LCD_1inch3.LCD_1inch3()
        disp.Init()
        disp.clear()

        # 2) Create a blank image
        width, height = 240, 240  # Adjust if your LCD is a different resolution
        image = Image.new("RGB", (width, height), "WHITE")
        draw = ImageDraw.Draw(image)

        # 3) Try to load the default system font, fall back to a basic font if not found
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
        except OSError:
            print("Warning: DejaVuSans font not found, using default font")
            font = ImageFont.load_default()

        # We'll write each game in a new line
        x, y = 10, 10
        line_spacing = 20

        if not scores:
            draw.text((x, y), "No games found.", font=font, fill=(0, 0, 0))
        else:
            for (away_team, away_score, home_team, home_score, status) in scores:
                line = f"{away_team} {away_score} @ {home_team} {home_score} ({status})"
                draw.text((x, y), line, font=font, fill=(0, 0, 0))
                y += line_spacing
                if y > (height - line_spacing):  # If we run out of space
                    break

        # 4) Send image to display
        disp.ShowImage(image)
        time.sleep(2)

    except Exception as e:
        print(f"Error displaying scores: {e}")
        raise

def main():
    # Check SPI interface first
    if not check_spi():
        sys.exit(1)

    # Example: fetch today's date automatically or hard-code it.
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")

    try:
        # 1) Fetch data
        data = fetch_nhl_scores(today_str)
        # 2) Parse scores
        scores = parse_nhl_scores(data)
        # 3) Display on LCD
        display_scores_on_lcd(scores)
    except Exception as e:
        print(f"Error in main execution: {e}")
    finally:
        # Cleanup
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
        GPIO.cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        GPIO.cleanup()
        sys.exit(1)
