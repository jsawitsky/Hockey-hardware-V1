#!/usr/bin/env python3

import sys
import os
import time
import socket
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

def check_internet():
    """
    Test internet connectivity
    """
    try:
        # Try to connect to a reliable server (Google's DNS)
        test_socket = socket.create_connection(("8.8.8.8", 53), timeout=3)
        test_socket.close()
        return True
    except OSError:
        print("Warning: No internet connection detected")
        return False

def fetch_ncaa_scores():
    """
    Fetch NCAA football scores from the API
    """
    if not check_internet():
        print("No internet connection - using test data")
        return {
            "games": [{
                "away_team": "Test Away",
                "away_points": 21,
                "home_team": "Test Home",
                "home_points": 14,
                "status": "FINAL"
            }]
        }

    url = "https://ncaa-api.henrygd.me/scoreboard/football/fbs"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        # Debug: Print the structure of the first game
        print("\nAPI Response Structure:")
        if 'games' in data and len(data['games']) > 0:
            print("First game data structure:")
            print(data['games'][0])
        return data
    except requests.RequestException as e:
        print(f"Error fetching NCAA data: {e}")
        return None

def parse_ncaa_scores(data):
    """
    Parse the NCAA football scores with updated field names
    """
    scores = []
    if not data or 'games' not in data:
        print("No valid NCAA data found")
        return scores

    print(f"Found {len(data['games'])} games")
    for game in data['games']:
        try:
            # Debug print for this specific game
            print("\nProcessing game:")
            print(game)
            
            # Extract the team names and scores based on actual API structure
            away_team = game.get('teams', {}).get('away', {}).get('name', 'Unknown')
            home_team = game.get('teams', {}).get('home', {}).get('name', 'Unknown')
            away_score = game.get('teams', {}).get('away', {}).get('score', 0)
            home_score = game.get('teams', {}).get('home', {}).get('score', 0)
            status = game.get('status', {}).get('type', 'Unknown')
            
            scores.append((away_team, away_score, home_team, home_score, status))
        except Exception as e:
            print(f"Error parsing game data: {e}")
            print(f"Problematic game data: {game}")
            continue
    
    return scores

def display_scores_on_lcd(scores):
    """
    Display scores on the LCD screen with enhanced error handling
    """
    try:
        print("Initializing display...")  # Debug print
        
        # Initialize display
        display = LCD_1inch3.LCD_1inch3()
        
        print("Calling display.Init()...")  # Debug print
        display.Init()
        
        print("Clearing display...")  # Debug print
        display.clear()

        # Create a blank image
        width, height = 240, 240
        print(f"Creating image with dimensions {width}x{height}")  # Debug print
        image = Image.new("RGB", (width, height), "WHITE")
        draw = ImageDraw.Draw(image)

        # Try to load font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
            print("Loaded DejaVuSans font")  # Debug print
        except OSError:
            print("Using default font")  # Debug print
            font = ImageFont.load_default()

        # Draw scores
        x, y = 10, 10
        line_spacing = 20

        if not scores:
            print("No scores to display")  # Debug print
            draw.text((x, y), "No games found.", font=font, fill=(0, 0, 0))
        else:
            print(f"Displaying {len(scores)} scores")  # Debug print
            for (away_team, away_score, home_team, home_score, status) in scores:
                line = f"{away_team[:10]} {away_score}"  # Truncate team names to fit
                draw.text((x, y), line, font=font, fill=(0, 0, 0))
                y += line_spacing
                line = f"{home_team[:10]} {home_score}"
                draw.text((x, y), line, font=font, fill=(0, 0, 0))
                y += line_spacing
                if y > (height - line_spacing):
                    break

        print("Showing image on display...")  # Debug print
        display.ShowImage(image)
        time.sleep(2)
        print("Display complete")  # Debug print

    except Exception as e:
        print(f"Error displaying scores: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        raise

def main():
    # Initialize GPIO first
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    if not check_spi():
        sys.exit(1)

    print("Starting score display loop...")
    try:
        while True:
            try:
                # Fetch and display scores
                print("\nFetching NCAA scores...")
                data = fetch_ncaa_scores()
                scores = parse_ncaa_scores(data)
                display_scores_on_lcd(scores)
                
                # Wait for 60 seconds before next update
                print("Waiting 60 seconds before next update...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Error in update loop: {e}")
                time.sleep(10)  # Wait a bit before retrying on error
                
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        print("Cleaning up GPIO...")
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
