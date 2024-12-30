#!/usr/bin/env python3

import sys
import time
import requests
from PIL import Image, ImageDraw, ImageFont
import RPi.GPIO as GPIO
import spidev

# -- If your Waveshare library is called LCD_1inch3, import it here
import LCD_1inch3

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

    # 1) Initialize the LCD
    disp = LCD_1inch3.LCD_1inch3()
    disp.Init()
    disp.clear()

    # 2) Create a blank image
    width, height = 240, 240  # Adjust if your LCD is a different resolution
    image = Image.new("RGB", (width, height), "WHITE")
    draw = ImageDraw.Draw(image)

    # 3) Load a TTF font (adjust path/size as needed)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)

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

def main():
    # Example: fetch today’s date automatically or hard-code it.
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1) Fetch data
    data = fetch_nhl_scores(today_str)
    # 2) Parse scores
    scores = parse_nhl_scores(data)
    # 3) Display on LCD
    display_scores_on_lcd(scores)

    # Cleanup
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()
        sys.exit()