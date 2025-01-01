#!/usr/bin/env python3

import sys
import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
import spidev

# Ensure we're in the correct directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import LCD modules directly
import lcdconfig
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
            status = game['status']['abstractGameState']
            scores.append((away_team, away_score, home_team, home_score, status))
    return scores

def display_scores_on_lcd(scores):
    """
    Display hockey scores on the LCD screen
    """
    try:
        # Initialize display
        display = LCD_1inch3.LCD_1inch3()
        
        # Print available methods for debugging
        print("Available LCD methods:", dir(display))
        
        # Initialize the display
        display.Init()
        display.clear()

        # Create a blank image
        width, height = 240, 240
        image = Image.new("RGB", (width, height), "WHITE")
        draw = ImageDraw.Draw(image)

        # Try to load font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
        except OSError:
            print("Warning: DejaVuSans font not found, using default font")
            font = ImageFont.load_default()

        # Draw scores
        x, y = 10, 10
        line_spacing = 20

        if not scores:
            draw.text((x, y), "No games found.", font=font, fill=(0, 0, 0))
        else:
            for (away_team, away_score, home_team, home_score, status) in scores:
                line = f"{away_team} {away_score} @ {home_team} {home_score}"
                draw.text((x, y), line, font=font, fill=(0, 0, 0))
                y += line_spacing
                if y > (height - line_spacing):
                    break

        # Show the image on the LCD
        display.ShowImage(image)
        time.sleep(2)

    except Exception as e:
        print(f"Error displaying scores: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        raise

def main():
    if not check_spi():
        sys.exit(1)

    try:
        # Get today's date
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Fetch and display scores
        data = fetch_nhl_scores(today_str)
        scores = parse_nhl_scores(data)
        display_scores_on_lcd(scores)

    except Exception as e:
        print(f"Error in main execution: {e}")
    finally:
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
