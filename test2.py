import sys
import requests
import re
import pandas as pd
import time
import argparse
import json
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Union, Optional
from dataclasses import dataclass
from datetime import datetime
from google_play_scraper import app as gplay_app
from google_play_scraper import search as gplay_search
from urllib.parse import quote_plus

# Custom data classes to represent app information
@dataclass
class AppStoreApp:
    app_id: str
    name: str
    developer_name: str
    developer_id: str
    rating: float
    reviews_count: int
    description: str
    release_date: str
    last_updated: str
    version: str
    size: str
    price: str
    content_rating: str
    developer_website: Optional[str] = None
    developer_email: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    
@dataclass
class PlayStoreApp:
    app_id: str
    name: str
    developer_name: str
    developer_id: str
    rating: float
    reviews_count: int
    description: str
    release_date: str
    last_updated: str
    version: str
    size: str
    price: str
    content_rating: str
    installs: str
    developer_address: Optional[str] = None
    developer_website: Optional[str] = None
    developer_email: Optional[str] = None
    privacy_policy_url: Optional[str] = None

class FakeAppDetector:
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.headers = {"User-Agent": self.user_agent}
        
        # Risk factors with weights
        self.risk_factors = {
            "developer_inconsistency": 3.0,        # High weight for inconsistent developer info
            "low_rating": 1.5,                     # Moderate weight for low ratings
            "few_reviews": 1.5,                    # Moderate weight for few reviews
            "recent_release": 1.0,                 # Lower weight for recently released apps
            "missing_privacy_policy": 2.0,         # High weight for missing privacy policy
            "suspicious_description": 2.0,         # High weight for suspicious text in description
            "similar_to_popular": 2.5,             # High weight for copying popular app names
            "generic_developer_name": 1.5,         # Moderate weight for generic developer names
            "price_discrepancy": 2.0,              # High weight for price discrepancies
            "multiple_similar_apps": 2.5           # High weight for developers with many similar apps
        }
        
        # Keywords for suspicious descriptions
        self.suspicious_keywords = [
            "100% free", "best app", "official app", "legit", "genuine", "authentic",
            "fast approval", "instant loan", "quick cash", "easy money", "guaranteed",
            "miracle", "secret", "hack", "crack", "unlimited", "free coins", "free money",
        ]
        
        # List of popular apps that fakes often imitate
        self.popular_apps = [
            "facebook", "messenger", "instagram", "whatsapp", "tiktok", 
            "snapchat", "twitter", "youtube", "netflix", "spotify", 
            "amazon", "uber", "paypal", "cash app", "venmo", "zelle",
            "gmail", "google", "outlook", "microsoft", "apple", "iphone"
        ]
        
        # Generic developer name patterns
        self.generic_dev_patterns = [
            r"app\s*dev(eloper)?s?",
            r"tech\s*solutions?",
            r"mobile\s*apps?",
            r"software\s*solutions?",
            r"digital\s*tech",
            r"studio\s*\w+",
            r"\w+\s*studio",
            r"global\s*tech",
            r"smart\s*apps?",
            r"infotech",
            r"innovation\s*tech",
        ]

    def search_app_store(self, query: str, country: str = "us", limit: int = 20) -> List[Dict]:
        """Search for apps on the App Store"""
        try:
            # Apple's Search API
            url = f"https://itunes.apple.com/search?term={quote_plus(query)}&country={country}&entity=software&limit={limit}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"Error searching App Store: {e}")
            return []

    def search_play_store(self, query: str, country: str = "us", limit: int = 20) -> List[Dict]:
        """Search for apps on the Google Play Store"""
        try:
            results = gplay_search(
                query,
                lang="en",
                country=country,
                n_hits=limit
            )
            return results
        except Exception as e:
            print(f"Error searching Play Store: {e}")
            return []
            
    def get_app_store_details(self, app_id: str, country: str = "us") -> Optional[AppStoreApp]:
        """Get detailed information about an App Store app"""
        try:
            url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            if not data.get("results"):
                return None
                
            app_data = data["results"][0]
            
            # Extract developer website and privacy policy URL
            developer_website = app_data.get("sellerUrl")
            privacy_policy_url = app_data.get("trackViewUrl", "")
            
            # Try to extract developer email through seller website if available
            developer_email = None
            if developer_website:
                try:
                    seller_page = requests.get(developer_website, headers=self.headers, timeout=5)
                    if seller_page.status_code == 200:
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        emails = re.findall(email_pattern, seller_page.text)
                        if emails:
                            developer_email = emails[0]
                except:
                    pass
            
            return AppStoreApp(
                app_id=str(app_data.get("trackId", "")),
                name=app_data.get("trackName", ""),
                developer_name=app_data.get("artistName", ""),
                developer_id=str(app_data.get("artistId", "")),
                rating=float(app_data.get("averageUserRating", 0.0)),
                reviews_count=int(app_data.get("userRatingCount", 0)),
                description=app_data.get("description", ""),
                release_date=app_data.get("releaseDate", ""),
                last_updated=app_data.get("currentVersionReleaseDate", ""),
                version=app_data.get("version", ""),
                size=f"{round(float(app_data.get('fileSizeBytes', 0)) / (1024*1024), 2)} MB",
                price=f"${app_data.get('price', 0)}",
                content_rating=app_data.get("contentAdvisoryRating", ""),
                developer_website=developer_website,
                developer_email=developer_email,
                privacy_policy_url=privacy_policy_url
            )
        except Exception as e:
            print(f"Error getting App Store details for {app_id}: {e}")
            return None
            
    def get_play_store_details(self, app_id: str) -> Optional[PlayStoreApp]:
        """Get detailed information about a Google Play Store app"""
        try:
            app_data = gplay_app(app_id)
            
            # Try to extract developer email and address from the developer website
            developer_email = None
            developer_address = None
            
            if app_data.get("developerWebsite"):
                try:
                    dev_page = requests.get(app_data["developerWebsite"], headers=self.headers, timeout=5)
                    if dev_page.status_code == 200:
                        # Look for email addresses
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        emails = re.findall(email_pattern, dev_page.text)
                        if emails:
                            developer_email = emails[0]
                            
                        # Look for potential addresses
                        address_pattern = r'\d+\s+[A-Za-z\s,.]+(Road|Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Lane|Ln|Place|Pl|Court|Ct|Way|Circle|Cir|Highway|Hwy)[,.\s]+[A-Za-z\s,.]+\d{5}'
                        addresses = re.findall(address_pattern, dev_page.text)
                        if addresses:
                            developer_address = addresses[0]
                except:
                    pass
            
            # Convert price to string format
            price = "Free" if app_data.get("free") else f"${app_data.get('price', 0)}"
            
            # Convert install count
            installs = app_data.get("installs", "0+")
            
            return PlayStoreApp(
                app_id=app_data.get("appId", ""),
                name=app_data.get("title", ""),
                developer_name=app_data.get("developer", ""),
                developer_id=app_data.get("developerId", ""),
                rating=float(app_data.get("score", 0.0)),
                reviews_count=int(app_data.get("reviews", 0)),
                description=app_data.get("description", ""),
                release_date=app_data.get("released", ""),
                last_updated=app_data.get("updated", ""),
                version=app_data.get("version", ""),
                size=app_data.get("size", ""),
                price=price,
                content_rating=app_data.get("contentRating", ""),
                installs=installs,
                developer_address=developer_address,
                developer_website=app_data.get("developerWebsite"),
                developer_email=developer_email,
                privacy_policy_url=app_data.get("privacyPolicy")
            )
        except Exception as e:
            print(f"Error getting Play Store details for {app_id}: {e}")
            return None
    
    def analyze_app_store_app(self, app: AppStoreApp) -> Tuple[float, Dict[str, float]]:
        """Analyze an App Store app and return risk score with breakdown"""
        risk_score = 0
        risk_breakdown = {}
        
        # Check for low rating
        if app.rating < 3.0:
            risk_factor = self.risk_factors["low_rating"]
            risk_score += risk_factor
            risk_breakdown["low_rating"] = risk_factor
        
        # Check for few reviews (potentially suspicious)
        if app.reviews_count < 50:
            risk_factor = self.risk_factors["few_reviews"]
            risk_score += risk_factor
            risk_breakdown["few_reviews"] = risk_factor
        
        # Check for recent release date (less than 30 days)
        try:
            release_date = datetime.strptime(app.release_date, "%Y-%m-%dT%H:%M:%SZ")
            days_since_release = (datetime.now() - release_date).days
            if days_since_release < 30:
                risk_factor = self.risk_factors["recent_release"]
                risk_score += risk_factor
                risk_breakdown["recent_release"] = risk_factor
        except:
            pass
        
        # Check for missing privacy policy
        if not app.privacy_policy_url:
            risk_factor = self.risk_factors["missing_privacy_policy"]
            risk_score += risk_factor
            risk_breakdown["missing_privacy_policy"] = risk_factor
        
        # Check for suspicious keywords in description
        for keyword in self.suspicious_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', app.description.lower()):
                risk_factor = self.risk_factors["suspicious_description"]
                risk_score += risk_factor
                risk_breakdown["suspicious_description"] = risk_factor
                break
        
        # Check if app name is similar to popular apps
        for popular_app in self.popular_apps:
            if popular_app in app.name.lower() or self._calculate_similarity(popular_app, app.name.lower()) > 0.7:
                risk_factor = self.risk_factors["similar_to_popular"]
                risk_score += risk_factor
                risk_breakdown["similar_to_popular"] = risk_factor
                break
        
        # Check for generic developer name
        for pattern in self.generic_dev_patterns:
            if re.search(pattern, app.developer_name.lower()):
                risk_factor = self.risk_factors["generic_developer_name"]
                risk_score += risk_factor
                risk_breakdown["generic_developer_name"] = risk_factor
                break
        
        return risk_score, risk_breakdown
    
    def analyze_play_store_app(self, app: PlayStoreApp) -> Tuple[float, Dict[str, float]]:
        """Analyze a Google Play Store app and return risk score with breakdown"""
        risk_score = 0
        risk_breakdown = {}
        
        # Check for low rating
        if app.rating < 3.0:
            risk_factor = self.risk_factors["low_rating"]
            risk_score += risk_factor
            risk_breakdown["low_rating"] = risk_factor
        
        # Check for few reviews (potentially suspicious)
        if app.reviews_count < 100:
            risk_factor = self.risk_factors["few_reviews"]
            risk_score += risk_factor
            risk_breakdown["few_reviews"] = risk_factor
        
        # Check for recent release date (less than 30 days)
        try:
            release_date = datetime.strptime(app.release_date, "%b %d, %Y")
            days_since_release = (datetime.now() - release_date).days
            if days_since_release < 30:
                risk_factor = self.risk_factors["recent_release"]
                risk_score += risk_factor
                risk_breakdown["recent_release"] = risk_factor
        except:
            pass
        
        # Check for missing privacy policy
        if not app.privacy_policy_url:
            risk_factor = self.risk_factors["missing_privacy_policy"]
            risk_score += risk_factor
            risk_breakdown["missing_privacy_policy"] = risk_factor
        
        # Check for suspicious keywords in description
        for keyword in self.suspicious_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', app.description.lower()):
                risk_factor = self.risk_factors["suspicious_description"]
                risk_score += risk_factor
                risk_breakdown["suspicious_description"] = risk_factor
                break
        
        # Check if app name is similar to popular apps
        for popular_app in self.popular_apps:
            if popular_app in app.name.lower() or self._calculate_similarity(popular_app, app.name.lower()) > 0.7:
                risk_factor = self.risk_factors["similar_to_popular"]
                risk_score += risk_factor
                risk_breakdown["similar_to_popular"] = risk_factor
                break
        
        # Check for generic developer name
        for pattern in self.generic_dev_patterns:
            if re.search(pattern, app.developer_name.lower()):
                risk_factor = self.risk_factors["generic_developer_name"]
                risk_score += risk_factor
                risk_breakdown["generic_developer_name"] = risk_factor
                break
        
        # Check for low number of installs
        try:
            installs = app.installs.replace("+", "").replace(",", "")
            if int(installs) < 1000:
                risk_factor = self.risk_factors["few_reviews"]
                risk_score += risk_factor
                risk_breakdown["few_installs"] = risk_factor
        except:
            pass
        
        return risk_score, risk_breakdown
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using Levenshtein distance"""
        # Simple implementation of Levenshtein distance
        m, n = len(str1), len(str2)
        if m < n:
            return self._calculate_similarity(str2, str1)
        if not n:
            return 0
        
        prev = list(range(n + 1))
        current = [0] * (n + 1)
        
        for i in range(1, m + 1):
            current[0] = i
            for j in range(1, n + 1):
                if str1[i-1] == str2[j-1]:
                    current[j] = prev[j-1]
                else:
                    current[j] = min(prev[j], current[j-1], prev[j-1]) + 1
            prev, current = current, prev
        
        # Convert to similarity score (0 to 1, where 1 is exact match)
        max_len = max(m, n)
        if max_len == 0:
            return 1.0
        return 1 - (prev[n] / max_len)
    
    def check_developer_consistency(self, app_name: str) -> Tuple[bool, List[Dict]]:
        """Check if the developer has multiple similar apps"""
        apps_found = []
        is_consistent = True
        
        # Search for the app on both stores
        app_store_results = self.search_app_store(app_name)
        play_store_results = self.search_play_store(app_name)
        
        # Find apps with the same developer on App Store
        if app_store_results:
            main_app = app_store_results[0]
            developer_id = main_app.get("artistId")
            developer_name = main_app.get("artistName")
            
            # Look for more apps by the same developer
            url = f"https://itunes.apple.com/lookup?id={developer_id}&entity=software"
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("resultCount", 0) > 5:
                        # Check if developer has many similar apps
                        apps = data.get("results", [])[1:]  # Skip the first result (developer)
                        similar_apps_count = 0
                        for app in apps:
                            if app_name.lower() in app.get("trackName", "").lower() or \
                               self._calculate_similarity(app_name.lower(), app.get("trackName", "").lower()) > 0.6:
                                similar_apps_count += 1
                                apps_found.append({
                                    "name": app.get("trackName"),
                                    "store": "App Store",
                                    "developer": app.get("artistName"),
                                    "id": app.get("trackId")
                                })
                        
                        if similar_apps_count > 3:
                            is_consistent = False
            except:
                pass
        
        # Find apps with the same developer on Play Store
        if play_store_results:
            main_app = play_store_results[0]
            developer_id = main_app.get("developerId")
            
            # This would require additional scraping as there's no direct API for this
            # For demonstration purposes, we'll assume the check is performed
            
        return is_consistent, apps_found
    
    def classify_app(self, app_id: str, store: str, detailed_info=None) -> Dict:
        """Classify an app as potentially fake or genuine"""
        result = {
            "store": store,
            "app_id": app_id,
            "app_name": "",
            "developer_name": "",
            "risk_score": 0,
            "risk_classification": "",
            "suspicious_factors": [],
            "recommendation": ""
        }
        
        # Get app details based on store
        if store == "app_store":
            app_details = self.get_app_store_details(app_id) if not detailed_info else detailed_info
            if app_details:
                risk_score, risk_factors = self.analyze_app_store_app(app_details)
                
                result.update({
                    "app_name": app_details.name,
                    "developer_name": app_details.developer_name,
                    "developer_id": app_details.developer_id,
                    "rating": app_details.rating,
                    "reviews": app_details.reviews_count,
                    "risk_score": risk_score,
                    "risk_factors": risk_factors,
                    "developer_website": app_details.developer_website,
                    "developer_email": app_details.developer_email,
                    "privacy_policy": app_details.privacy_policy_url,
                    "suspicious_factors": list(risk_factors.keys())
                })
        
        elif store == "play_store":
            app_details = self.get_play_store_details(app_id) if not detailed_info else detailed_info
            if app_details:
                risk_score, risk_factors = self.analyze_play_store_app(app_details)
                
                result.update({
                    "app_name": app_details.name,
                    "developer_name": app_details.developer_name,
                    "developer_id": app_details.developer_id,
                    "rating": app_details.rating,
                    "reviews": app_details.reviews_count,
                    "installs": app_details.installs,
                    "risk_score": risk_score,
                    "risk_factors": risk_factors,
                    "developer_website": app_details.developer_website,
                    "developer_email": app_details.developer_email,
                    "developer_address": app_details.developer_address,
                    "privacy_policy": app_details.privacy_policy_url,
                    "suspicious_factors": list(risk_factors.keys())
                })
        
        # Classify the risk level
        if result["risk_score"] >= 7.0:
            result["risk_classification"] = "High Risk - Likely Fake"
            result["recommendation"] = "Avoid downloading this app. It shows multiple signs of being potentially fake or fraudulent."
        elif result["risk_score"] >= 4.0:
            result["risk_classification"] = "Medium Risk - Exercise Caution"
            result["recommendation"] = "Proceed with caution. This app shows some suspicious characteristics that warrant careful consideration."
        elif result["risk_score"] > 0:
            result["risk_classification"] = "Low Risk - Likely Genuine with Minor Concerns"
            result["recommendation"] = "This app appears to be genuine but has some minor risk factors to be aware of."
        else:
            result["risk_classification"] = "Very Low Risk - Genuine"
            result["recommendation"] = "This app appears to be genuine with no obvious risk factors detected."
        
        return result

    def search_and_analyze(self, keyword: str, limit: int = 15, store: str = "both", output_file: str = None) -> List[Dict]:
        """Search for apps with the given keyword and analyze them all"""
        print(f"Searching for apps with keyword: '{keyword}'...")
        results = []
        
        # Get apps from App Store
        if store.lower() in ["both", "app_store", "apple"]:
            print(f"Searching Apple App Store...")
            app_store_results = self.search_app_store(keyword, limit=limit)
            print(f"Found {len(app_store_results)} apps on App Store")
            
            for idx, app in enumerate(app_store_results):
                print(f"Analyzing App Store app {idx+1}/{len(app_store_results)}: {app.get('trackName')}")
                app_id = str(app.get("trackId"))
                try:
                    app_details = self.get_app_store_details(app_id)
                    if app_details:
                        result = self.classify_app(app_id, "app_store", app_details)
                        results.append(result)
                except Exception as e:
                    print(f"  Error analyzing app {app_id}: {e}")
                time.sleep(0.5)
        
        # Get apps from Play Store
        if store.lower() in ["both", "play_store", "google"]:
            print(f"Searching Google Play Store...")
            play_store_results = self.search_play_store(keyword, limit=limit)
            print(f"Found {len(play_store_results)} apps on Play Store")
            
            for idx, app in enumerate(play_store_results):
                print(f"Analyzing Play Store app {idx+1}/{len(play_store_results)}: {app.get('title')}")
                app_id = app.get("appId")
                try:
                    app_details = self.get_play_store_details(app_id)
                    if app_details:
                        result = self.classify_app(app_id, "play_store", app_details)
                        results.append(result)
                except Exception as e:
                    print(f"  Error analyzing app {app_id}: {e}")
                time.sleep(0.5)
        
        # Sort results by risk score (highest first)
        results.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
        
        # Save to JSON if output file specified
        if output_file and results:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {output_file}")
        
        # Display summary
        if results:
            high_risk = sum(1 for app in results if 'High Risk' in app.get('risk_classification', ''))
            medium_risk = sum(1 for app in results if 'Medium Risk' in app.get('risk_classification', ''))
            low_risk = sum(1 for app in results if 'Low Risk' in app.get('risk_classification', ''))
            very_low_risk = sum(1 for app in results if 'Very Low Risk' in app.get('risk_classification', ''))
            
            print("\n==== ANALYSIS SUMMARY ====")
            print(f"Total apps analyzed: {len(results)}")
            print(f"High Risk apps: {high_risk}")
            print(f"Medium Risk apps: {medium_risk}")
            print(f"Low Risk apps: {low_risk}")
            print(f"Very Low Risk apps: {very_low_risk}")
        else:
            print("No apps were found or analysis returned no results.")
        
        return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python fake_app_detector.py \"search term\" [--store both] [--limit 15]")
        print("Example: python fake_app_detector.py \"crypto wallet\" --store play_store --limit 10")
        sys.exit(1)
    
    # Parse command-line arguments
    keyword = sys.argv[1]
    store = "both"
    limit = 15
    
    # Process optional arguments
    args = sys.argv[2:]
    for i in range(len(args)):
        if args[i] == "--store" and i+1 < len(args):
            store = args[i+1].lower()
        elif args[i] == "--limit" and i+1 < len(args):
            try:
                limit = int(args[i+1])
            except ValueError:
                print("Invalid limit value, using default 15")

    # Generate safe filename
    safe_keyword = re.sub(r'[^\w-]', '_', keyword).lower()[:50]
    output_file = f"{safe_keyword}.json"
    
    detector = FakeAppDetector()
    results = detector.search_and_analyze(keyword, limit=limit, store=store, output_file=output_file)
    
    # Display top results if no output file specified
    if results and not output_file:
        print("\n==== TOP HIGH-RISK APPS ====")
        print("{:<40} {:<25} {:<10} {:<10} {:<25} {}".format(
            "App Name", "Developer", "Store", "Risk Score", "Risk Classification", "Suspicious Factors"))
        for app in results[:10]:
            factors = ", ".join(app.get('suspicious_factors', []))[:40]
            print("{:<40} {:<25} {:<10} {:<10.1f} {:<25} {}".format(
                app.get('app_name', '')[:38],
                app.get('developer_name', '')[:23],
                app.get('store', '')[:8],
                app.get('risk_score', 0),
                app.get('risk_classification', '')[:23],
                factors
            ))

if __name__ == "__main__":
    main()