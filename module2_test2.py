import json
import re
from google_play_scraper import search
import requests

def parse_installs(installs_str):
    """
    Convert installs string (e.g., '1,000,000+', '50,000') to a number.
    This function also handles 'M' or 'B' if present.
    """
    try:
        # Remove commas and plus signs
        value = installs_str.replace(",", "").replace("+", "")
        if "M" in installs_str:
            return float(value) * 1_000_000
        elif "B" in installs_str:
            return float(value) * 1_000_000_000
        return float(value)
    except Exception as e:
        return 0

def scrape_google_play(search_query):
    """
    Fetch app details from the Google Play Store using google-play-scraper.
    Determines the official app by the highest install count.
    Returns a list of apps that are suspected to be fake (i.e. with a different developer).
    """
    fake_apps = []
    try:
        results = search(search_query, lang="en", country="us", n_hits=20)
        if not results:
            return fake_apps
        
        # Determine the official app by the highest installs.
        official_app = max(results, key=lambda app: parse_installs(app.get("installs", "0")))
        official_dev = official_app["developer"]
        print("Assumed official developer on Google Play:", official_dev)
        
        # Now, flag apps whose developer differs from the official developer.
        for app in results:
            app_data = {
                "title": app["title"],
                "developer": app["developer"],
                "link": f"https://play.google.com/store/apps/details?id={app['appId']}",
                "score": app.get("score", "N/A"),
                "installs": app.get("installs", "N/A"),
                "free": app.get("free", "N/A")
            }
            if app_data["developer"] != official_dev:
                fake_apps.append(app_data)
    except Exception as e:
        print(f"Error fetching Google Play data: {e}")
    return fake_apps

def scrape_apple_app_store(search_query):
    """
    Use the iTunes Search API to get app details from the Apple App Store.
    Determines the official app as the first result.
    Returns a list of apps with a developer different from the official one.
    """
    fake_apps = []
    api_url = f"https://itunes.apple.com/search?term={search_query}&entity=software"
    response = requests.get(api_url)
    
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        if not results:
            return fake_apps
        
        # Assume the first result is the official app.
        official_dev = results[0].get("sellerName", "")
        print("Assumed official developer on Apple App Store:", official_dev)
        
        for result in results:
            app_data = {
                "title": result.get("trackName", ""),
                "developer": result.get("sellerName", ""),
                "link": result.get("trackViewUrl", "")
            }
            if app_data["developer"] != official_dev:
                fake_apps.append(app_data)
    else:
        print("Error fetching Apple App Store data.")
    return fake_apps

if __name__ == "__main__":
    search_term = "facebook"  # Example app name
    
    print("Detecting Fake Apps on Google Play Store...")
    google_play_fake_apps = scrape_google_play(search_term)
    print(f"Found {len(google_play_fake_apps)} suspicious apps on Google Play:")
    for app in google_play_fake_apps:
        print(app)
    
    print("\nDetecting Fake Apps on Apple App Store...")
    apple_fake_apps = scrape_apple_app_store(search_term)
    print(f"Found {len(apple_fake_apps)} suspicious apps on Apple App Store:")
    for app in apple_fake_apps:
        print(app)
    
    # Combine fake app data
    fake_apps_data = {
        "google_play": google_play_fake_apps,
        "apple_app_store": apple_fake_apps
    }
    
    # Save the results to a JSON file
    with open("fake_apps_data.json", "w", encoding="utf-8") as f:
        json.dump(fake_apps_data, f, ensure_ascii=False, indent=4)
    
    print("\n✅ Fake apps data saved to 'fake_apps_data.json'")
