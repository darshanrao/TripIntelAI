"""
Flight Booking Service using Stagehand for LLM-powered browser automation.

This module provides a visible browser automation system that shows the booking process
in real-time using Playwright to search flights via Google Flights.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, TimeoutError

class VisibleFlightBooker:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        
    async def initialize(self):
        """Initialize a visible browser instance."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # This makes the browser visible
            slow_mo=1500  # Slow down actions by 1.5 seconds to make them more visible
        )
        # Initialize context with no geolocation permissions
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},  # Full HD for better visibility
            permissions=[],  # Don't allow geolocation
            geolocation={'latitude': 0, 'longitude': 0}  # Set to null island
        )
        self.page = await self.context.new_page()
        return {"status": "initialized"}

    async def _safe_type(self, text: str, delay: int = 100):
        """Type text with a delay between characters."""
        for char in text:
            await self.page.keyboard.type(char)
            await asyncio.sleep(delay/1000)  # Convert ms to seconds

    async def _clear_input(self, selector: str):
        """Clear an input field completely."""
        try:
            # Click the field
            await self.page.click(selector)
            await asyncio.sleep(0.5)
            
            # Click the clear button if it exists (x button)
            try:
                await self.page.click('button[aria-label*="Clear"]', timeout=2000)
                return True
            except:
                # If no clear button, use keyboard shortcuts
                if self.page.operating_system == "darwin":
                    await self.page.keyboard.press("Meta+A")  # Cmd+A on Mac
                else:
                    await self.page.keyboard.press("Control+A")  # Ctrl+A on Windows/Linux
                await self.page.keyboard.press("Backspace")
                return True
        except Exception as e:
            print(f"Error clearing input: {str(e)}")
            return False

    async def book_flight(self, flight_info: Dict[str, Any], passenger_info: Dict[str, Any], num_people: int = 1) -> Dict[str, Any]:
        """
        Search for flights using Google Flights with specific steps.
        """
        try:
            print("Starting flight search process...")
            
            # Navigate to Google Flights
            print("Navigating to Google Flights...")
            await self.page.goto("https://www.google.com/travel/flights", wait_until="domcontentloaded")
            await asyncio.sleep(3)  # Wait for page to fully load
            
            # Find and clear origin field
            print("Clearing pre-filled origin...")
            origin_selector = '[placeholder*="Where from"], [aria-label*="From"], [aria-label*="Origin"]'
            await self._clear_input(origin_selector)
            await asyncio.sleep(1)
            
            # Enter origin
            print("Setting origin to SF...")
            await self._safe_type("SF")
            await asyncio.sleep(1)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(1)
            
            # Find and clear destination field
            print("Setting destination to LAX...")
            dest_selector = '[placeholder*="Where to"], [aria-label*="To"], [aria-label*="Destination"]'
            await self._clear_input(dest_selector)
            await asyncio.sleep(1)
            
            # Enter destination
            await self._safe_type("LAX")
            await asyncio.sleep(1)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(1)
            
            # Click to open the date picker
            print("Opening date picker...")
            date_selector = '[aria-label*="Departure"], [aria-label*="Date"], text="Departure"'
            await self.page.click(date_selector)
            await asyncio.sleep(1)
            
            # Format and enter dates
            departure_date = datetime.strptime(flight_info['departure_time'], "%Y-%m-%dT%H:%M:%S")
            date_str = departure_date.strftime("Thu %d %b")  # Format: "Thu 8 May"
            print(f"Setting departure date: {date_str}")
            
            try:
                # Try clicking the date directly
                await self.page.click(f'text="{date_str}"')
            except:
                print("Exact date not found, trying alternative date selection...")
                try:
                    # Try finding by aria-label
                    formatted_date = departure_date.strftime("%A, %B %-d")  # e.g., "Thursday, May 8"
                    await self.page.click(f'[aria-label*="{formatted_date}"]')
                except:
                    print("Could not find exact date, please check the calendar manually")
            
            await asyncio.sleep(1)
            
            # Click Done to close the date picker
            print("Clicking Done...")
            done_button = await self.page.query_selector('button:has-text("Done")')
            if done_button:
                await done_button.click()
            await asyncio.sleep(1)
            
            # Click Explore
            print("Clicking Explore to search...")
            explore_button = await self.page.query_selector('button:has-text("Explore")')
            if explore_button:
                await explore_button.click()
            else:
                # Try search button as fallback
                await self.page.click('button:has-text("Search")')
            
            # Wait for results to load
            print("Waiting for search results...")
            await self.page.wait_for_selector('[role="main"]', timeout=30000)
            await asyncio.sleep(3)
            
            # Try to find the specific flight
            flight_text = f"{flight_info['airline']} {flight_info['flight_number']}"
            print(f"Looking for flight {flight_text}...")
            
            try:
                flight_element = await self.page.wait_for_selector(f'text=/{flight_text}/i', timeout=5000)
                if flight_element:
                    print(f"Found flight {flight_text}!")
                    await flight_element.click()
                    await asyncio.sleep(1)
                    
                    # Look for booking options
                    book_button = await self.page.query_selector('text="View deal"')
                    if book_button:
                        booking_url = await book_button.get_attribute('href')
                        print(f"Found booking link: {booking_url}")
                        
                        # Open booking link in new tab
                        page = await self.context.new_page()
                        await page.goto(booking_url)
                        print("Opened booking page")
                        
                        return {
                            "status": "success",
                            "message": "Found flight and opened booking page",
                            "booking_url": booking_url,
                            "flight_found": True
                        }
            except Exception as e:
                print(f"Couldn't find exact flight: {str(e)}")
                print("Showing available flights instead")
            
            return {
                "status": "partial_success",
                "message": "Showed available flights",
                "flight_found": False
            }
            
        except TimeoutError as e:
            print(f"Timeout error: {str(e)}")
            return {
                "status": "error",
                "message": f"Timeout during search process: {str(e)}"
            }
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return {
                "status": "error",
                "message": f"Error during search process: {str(e)}"
            }

    async def close(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()

# Example usage:
async def example_visible_booking():
    """Example of using the visible flight booker."""
    flight_info = {
        "airline": "UA",
        "flight_number": "UA505",
        "departure_time": "2024-05-08T06:00:00",  # Thu May 8
        "arrival_time": "2024-05-08T07:41:00",
        "price": 199.99,
        "currency": "USD",
        "origin": "SF",  # Changed from SFO to SF
        "destination": "LAX"
    }
    
    passenger_info = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "123-456-7890",
        "date_of_birth": "1990-01-01"
    }
    
    booker = VisibleFlightBooker()
    try:
        result = await booker.book_flight(flight_info, passenger_info, num_people=1)
        print(f"Booking result: {result}")
    finally:
        await booker.close()

if __name__ == "__main__":
    asyncio.run(example_visible_booking()) 