import json
from google_play_scraper import search
import requests

def scrape_google_play(search_query):
    """
    Fetch app details from the Google Play Store using google-play-scraper.
    Returns a list of apps with title, developer, and link.
    """
    apps = []
    try:
        results = search(search_query, lang="en", country="us", n_hits=10)
        for app in results:
            apps.append({
                "title": app["title"],
                "developer": app["developer"],
                "link": f"https://play.google.com/store/apps/details?id={app['appId']}",
                "score": app.get("score", "N/A"),
                "free": app.get("free", "N/A"),
            })
    except Exception as e:
        print(f"Error fetching Google Play data: {e}")
    return apps

def scrape_apple_app_store(search_query):
    """
    Use the iTunes Search API to get app details from the Apple App Store.
    Returns a list of apps with title, developer, and link.
    """
    api_url = f"https://itunes.apple.com/search?term={search_query}&entity=software"
    response = requests.get(api_url)
    apps = []
    if response.status_code == 200:
        data = response.json()
        for result in data.get("results", []):
            apps.append({
                "title": result.get("trackName", ""),
                "developer": result.get("sellerName", ""),
                "link": result.get("trackViewUrl", "")
            })
    else:
        print("Error fetching Apple App Store data.")
    return apps

if __name__ == "__main__":
    search_term = "root"  # Example popular app name

    print("Scraping Google Play Store...")
    google_play_apps = scrape_google_play(search_term)
    print(f"Found {len(google_play_apps)} apps on Google Play:")
    for app in google_play_apps:
        print(app)

    print("\nScraping Apple App Store...")
    apple_apps = scrape_apple_app_store(search_term)
    print(f"Found {len(apple_apps)} apps on Apple App Store:")
    for app in apple_apps:
        print(app)

    # Combine data from both sources if needed
    all_apps = {
        "google_play": google_play_apps,
        "apple_app_store": apple_apps
    }

    # Save the results to a JSON file
    with open("fake_apps_data.json", "w", encoding="utf-8") as f:
        json.dump(all_apps, f, ensure_ascii=False, indent=4)

    print("\n✅ Data saved successfully to 'fake_apps_data.json'")
