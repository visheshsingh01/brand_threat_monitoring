"""
Social Media Impersonation Detection System

This program helps identify potential impersonators across social media platforms by:
1. Collecting data from user profiles
2. Using image comparison for profile pictures 
3. Analyzing text similarity between profiles
4. Reporting potential impersonators
"""

import os
import requests
import json
import numpy as np
import pandas as pd
from PIL import Image
import face_recognition
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stalkre.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("stalkre")

class SocialMediaAPI:
    """Base class for social media platform APIs"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def get_profile(self, user_id: str) -> Dict:
        """Get profile data - to be implemented by child classes"""
        raise NotImplementedError
    
    def get_profile_picture(self, user_id: str) -> str:
        """Get profile picture URL - to be implemented by child classes"""
        raise NotImplementedError
    
    def download_image(self, url: str, save_path: str) -> str:
        """Download an image from URL and save to disk"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as image_file:
                for chunk in response.iter_content(chunk_size=8192):
                    image_file.write(chunk)
            
            return save_path
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return ""

class FacebookAPI(SocialMediaAPI):
    """Facebook API implementation"""
    
    def get_profile(self, user_id: str) -> Dict:
        endpoint = f"https://graph.facebook.com/v18.0/{user_id}"
        params = {
            "fields": "id,name,about,bio,link,username,emails"
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Facebook profile: {e}")
            return {}
    
    def get_profile_picture(self, user_id: str) -> str:
        endpoint = f"https://graph.facebook.com/v18.0/{user_id}/picture"
        params = {"type": "large", "redirect": "false"}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("url", "")
        except Exception as e:
            logger.error(f"Error fetching Facebook profile picture: {e}")
            return ""

class InstagramAPI(SocialMediaAPI):
    """Instagram API implementation"""
    
    def get_profile(self, username: str) -> Dict:
        endpoint = f"https://graph.instagram.com/v18.0/{username}"
        params = {
            "fields": "id,username,biography,full_name,profile_picture_url"
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Instagram profile: {e}")
            return {}
    
    def get_profile_picture(self, user_id: str) -> str:
        profile = self.get_profile(user_id)
        return profile.get("profile_picture_url", "")

class TwitterAPI(SocialMediaAPI):
    """Twitter API implementation"""
    
    def get_profile(self, username: str) -> Dict:
        endpoint = f"https://api.twitter.com/2/users/by/username/{username}"
        params = {
            "user.fields": "id,name,username,description,profile_image_url"
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("data", {})
        except Exception as e:
            logger.error(f"Error fetching Twitter profile: {e}")
            return {}
    
    def get_profile_picture(self, username: str) -> str:
        profile = self.get_profile(username)
        # Replace _normal with _400x400 for higher resolution
        profile_pic_url = profile.get("profile_image_url", "")
        if profile_pic_url:
            return profile_pic_url.replace("_normal", "_400x400")
        return ""

class LinkedInAPI(SocialMediaAPI):
    """LinkedIn API implementation"""
    
    def get_profile(self, user_id: str) -> Dict:
        endpoint = f"https://api.linkedin.com/v2/people/{user_id}"
        params = {
            "fields": "id,firstName,lastName,headline,summary,profilePicture"
        }
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching LinkedIn profile: {e}")
            return {}
    
    def get_profile_picture(self, user_id: str) -> str:
        endpoint = f"https://api.linkedin.com/v2/people/{user_id}/profilePicture"
        params = {"displaySize": "maximal"}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("displayImage~", {}).get("elements", [{}])[-1].get("identifiers", [{}])[0].get("identifier", "")
        except Exception as e:
            logger.error(f"Error fetching LinkedIn profile picture: {e}")
            return ""

class FaceComparison:
    """Compare faces in images"""
    
    @staticmethod
    def get_face_encodings(image_path: str) -> List:
        """Extract face encodings from an image"""
        try:
            image = face_recognition.load_image_file(image_path)
            face_encodings = face_recognition.face_encodings(image)
            return face_encodings
        except Exception as e:
            logger.error(f"Error extracting face encodings: {e}")
            return []
    
    @staticmethod
    def compare_faces(known_encoding: np.ndarray, face_encoding: np.ndarray, tolerance: float = 0.6) -> bool:
        """Compare faces and return True if they match"""
        try:
            match = face_recognition.compare_faces([known_encoding], face_encoding, tolerance=tolerance)[0]
            return match
        except Exception as e:
            logger.error(f"Error comparing faces: {e}")
            return False
    
    @staticmethod
    def compute_face_distance(known_encoding: np.ndarray, face_encoding: np.ndarray) -> float:
        """Compute distance between faces (lower = more similar)"""
        try:
            distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
            return distance
        except Exception as e:
            logger.error(f"Error computing face distance: {e}")
            return 1.0  # Return max distance on error

class TextAnalysis:
    """Text analysis utilities"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text for comparison"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # Remove special characters and extra whitespace
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def compute_text_similarity(text1: str, text2: str) -> float:
        """Compute cosine similarity between two text strings"""
        if not text1 or not text2:
            return 0.0
        
        clean_text1 = TextAnalysis.clean_text(text1)
        clean_text2 = TextAnalysis.clean_text(text2)
        
        if not clean_text1 or not clean_text2:
            return 0.0
        
        try:
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([clean_text1, clean_text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing text similarity: {e}")
            return 0.0

class ProfileData:
    """Profile data container"""
    
    def __init__(
        self, 
        platform: str,
        user_id: str, 
        username: str, 
        full_name: str,
        bio_text: str,
        profile_pic_path: str,
        profile_url: str,
        face_encodings: List = None
    ):
        self.platform = platform
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.bio_text = bio_text
        self.profile_pic_path = profile_pic_path
        self.profile_url = profile_url
        self.face_encodings = face_encodings or []

class ImpersonatorDetector:
    """Main detector class for finding potential impersonators"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize the detector with API configurations"""
        self.config = self._load_config(config_path)
        self.apis = self._initialize_apis()
        self.data_dir = self._create_data_dir()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as config_file:
                return json.load(config_file)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, using default empty config")
            return {
                "api_keys": {
                    "facebook": "",
                    "instagram": "",
                    "twitter": "",
                    "linkedin": ""
                },
                "similarity_thresholds": {
                    "face": 0.6,
                    "text": 0.7,
                    "username": 0.8
                }
            }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
            
    def _initialize_apis(self) -> Dict:
        """Initialize API clients for each platform"""
        api_keys = self.config.get("api_keys", {})
        
        return {
            "facebook": FacebookAPI(api_keys.get("facebook", "")),
            "instagram": InstagramAPI(api_keys.get("instagram", "")),
            "twitter": TwitterAPI(api_keys.get("twitter", "")),
            "linkedin": LinkedInAPI(api_keys.get("linkedin", ""))
        }
    
    def _create_data_dir(self) -> str:
        """Create data directory for storing profile images"""
        data_dir = os.path.join(os.getcwd(), "profile_data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    
    def fetch_original_profile(self, platform: str, identifier: str) -> Optional[ProfileData]:
        """Fetch original user profile data"""
        logger.info(f"Fetching original profile from {platform}: {identifier}")
        
        api = self.apis.get(platform.lower())
        if not api:
            logger.error(f"Unsupported platform: {platform}")
            return None
        
        profile_data = api.get_profile(identifier)
        if not profile_data:
            logger.error(f"Could not fetch profile data for {identifier} on {platform}")
            return None
        
        # Extract profile information based on platform
        if platform.lower() == "facebook":
            user_id = profile_data.get("id", "")
            username = profile_data.get("username", "")
            full_name = profile_data.get("name", "")
            bio_text = profile_data.get("about", "") + " " + profile_data.get("bio", "")
            profile_url = profile_data.get("link", "")
            
        elif platform.lower() == "instagram":
            user_id = profile_data.get("id", "")
            username = profile_data.get("username", "")
            full_name = profile_data.get("full_name", "")
            bio_text = profile_data.get("biography", "")
            profile_url = f"https://instagram.com/{username}"
            
        elif platform.lower() == "twitter":
            user_id = profile_data.get("id", "")
            username = profile_data.get("username", "")
            full_name = profile_data.get("name", "")
            bio_text = profile_data.get("description", "")
            profile_url = f"https://twitter.com/{username}"
            
        elif platform.lower() == "linkedin":
            user_id = profile_data.get("id", "")
            first_name = profile_data.get("firstName", {}).get("localized", {}).get("en_US", "")
            last_name = profile_data.get("lastName", {}).get("localized", {}).get("en_US", "")
            username = f"{first_name.lower()}{last_name.lower()}"
            full_name = f"{first_name} {last_name}"
            bio_text = profile_data.get("headline", {}).get("localized", {}).get("en_US", "") + " " + \
                      profile_data.get("summary", {}).get("localized", {}).get("en_US", "")
            profile_url = f"https://linkedin.com/in/{username}"
        else:
            return None
        
        # Get and download profile picture
        profile_pic_url = api.get_profile_picture(identifier)
        profile_pic_path = ""
        if profile_pic_url:
            pic_filename = f"{platform.lower()}_{user_id}_original.jpg"
            profile_pic_path = os.path.join(self.data_dir, pic_filename)
            api.download_image(profile_pic_url, profile_pic_path)
        
        # Extract face encodings if profile picture exists
        face_encodings = []
        if os.path.exists(profile_pic_path):
            face_encodings = FaceComparison.get_face_encodings(profile_pic_path)
        
        return ProfileData(
            platform=platform,
            user_id=user_id,
            username=username,
            full_name=full_name,
            bio_text=bio_text,
            profile_pic_path=profile_pic_path,
            profile_url=profile_url,
            face_encodings=face_encodings
        )
    
    def search_potential_impersonators(
        self, 
        original_profile: ProfileData, 
        platform: str, 
        search_params: Dict
    ) -> List[Dict]:
        """Search for potential impersonators on specified platform"""
        logger.info(f"Searching for impersonators on {platform}")
        
        api = self.apis.get(platform.lower())
        if not api:
            logger.error(f"Unsupported platform: {platform}")
            return []
        
        # Different platforms have different search endpoints and parameters
        # This is a simplified example - actual implementation would depend on platform APIs
        search_results = []
        
        # Example search implementation (varies by platform)
        if platform.lower() == "facebook":
            # Search for profiles with similar names
            endpoint = "https://graph.facebook.com/v18.0/search"
            params = {
                "q": original_profile.full_name,
                "type": "user",
                "limit": search_params.get("limit", 20)
            }
            
            try:
                response = requests.get(endpoint, headers=api.headers, params=params)
                response.raise_for_status()
                search_results = response.json().get("data", [])
            except Exception as e:
                logger.error(f"Error searching Facebook: {e}")
                
        elif platform.lower() == "twitter":
            # Search for users with similar names
            endpoint = "https://api.twitter.com/2/users/search"
            params = {
                "query": original_profile.full_name,
                "max_results": search_params.get("limit", 20),
                "user.fields": "id,name,username,description,profile_image_url"
            }
            
            try:
                response = requests.get(endpoint, headers=api.headers, params=params)
                response.raise_for_status()
                search_results = response.json().get("data", [])
            except Exception as e:
                logger.error(f"Error searching Twitter: {e}")
        
        # Similar patterns for Instagram and LinkedIn
        # ...
        
        return search_results
    
    def analyze_potential_impersonator(
        self,
        original_profile: ProfileData,
        suspect_data: Dict,
        platform: str
    ) -> Dict:
        """Analyze a potential impersonator and return similarity scores"""
        logger.info(f"Analyzing potential impersonator: {suspect_data.get('username', 'unknown')}")
        
        api = self.apis.get(platform.lower())
        if not api:
            return {
                "platform": platform,
                "is_potential_impersonator": False,
                "similarity_scores": {
                    "face": 0.0,
                    "name": 0.0,
                    "username": 0.0,
                    "bio": 0.0,
                    "overall": 0.0
                },
                "suspect_data": {}
            }
        
        # Extract data from suspect profile based on platform
        if platform.lower() == "facebook":
            suspect_id = suspect_data.get("id", "")
            suspect_username = suspect_data.get("username", "")
            suspect_name = suspect_data.get("name", "")
            suspect_bio = suspect_data.get("about", "") + " " + suspect_data.get("bio", "")
            suspect_url = suspect_data.get("link", "")
        elif platform.lower() == "twitter":
            suspect_id = suspect_data.get("id", "")
            suspect_username = suspect_data.get("username", "")
            suspect_name = suspect_data.get("name", "")
            suspect_bio = suspect_data.get("description", "")
            suspect_url = f"https://twitter.com/{suspect_username}"
        # Similar patterns for other platforms
        # ...
        else:
            return {
                "platform": platform,
                "is_potential_impersonator": False,
                "similarity_scores": {},
                "suspect_data": {}
            }
        
        # Skip if this is the original profile
        if suspect_id == original_profile.user_id:
            return {
                "platform": platform,
                "is_potential_impersonator": False,
                "similarity_scores": {},
                "suspect_data": suspect_data,
                "skip_reason": "This is the original profile"
            }
        
        # Get and download profile picture
        suspect_pic_url = api.get_profile_picture(suspect_id)
        suspect_pic_path = ""
        if suspect_pic_url:
            pic_filename = f"{platform.lower()}_{suspect_id}_suspect.jpg"
            suspect_pic_path = os.path.join(self.data_dir, pic_filename)
            api.download_image(suspect_pic_url, suspect_pic_path)
        
        # Calculate similarity scores
        face_similarity = 0.0
        if original_profile.face_encodings and os.path.exists(suspect_pic_path):
            suspect_face_encodings = FaceComparison.get_face_encodings(suspect_pic_path)
            if suspect_face_encodings and original_profile.face_encodings:
                # Use best match if multiple faces detected
                best_similarity = 0.0
                for orig_encoding in original_profile.face_encodings:
                    for suspect_encoding in suspect_face_encodings:
                        face_distance = FaceComparison.compute_face_distance(orig_encoding, suspect_encoding)
                        # Convert distance to similarity (1 - distance)
                        similarity = 1.0 - face_distance
                        best_similarity = max(best_similarity, similarity)
                face_similarity = best_similarity
        
        # Text similarity scores
        name_similarity = TextAnalysis.compute_text_similarity(
            original_profile.full_name, suspect_name
        )
        
        username_similarity = TextAnalysis.compute_text_similarity(
            original_profile.username, suspect_username
        )
        
        bio_similarity = TextAnalysis.compute_text_similarity(
            original_profile.bio_text, suspect_bio
        )
        
        # Calculate overall similarity score (weighted average)
        weights = {
            "face": 0.4,
            "name": 0.25,
            "username": 0.25,
            "bio": 0.1
        }
        
        similarity_scores = {
            "face": face_similarity,
            "name": name_similarity,
            "username": username_similarity,
            "bio": bio_similarity
        }
        
        overall_similarity = sum(
            score * weights[key] for key, score in similarity_scores.items()
        )
        
        # Determine if this is a potential impersonator based on thresholds
        thresholds = self.config.get("similarity_thresholds", {})
        face_threshold = thresholds.get("face", 0.6)
        text_threshold = thresholds.get("text", 0.7)
        username_threshold = thresholds.get("username", 0.8)
        
        # Logic to determine if this is a potential impersonator
        is_potential_impersonator = (
            (face_similarity >= face_threshold and name_similarity >= text_threshold) or
            (username_similarity >= username_threshold and name_similarity >= text_threshold) or
            overall_similarity >= 0.7  # Overall threshold
        )
        
        return {
            "platform": platform,
            "is_potential_impersonator": is_potential_impersonator,
            "similarity_scores": {
                "face": face_similarity,
                "name": name_similarity,
                "username": username_similarity,
                "bio": bio_similarity,
                "overall": overall_similarity
            },
            "suspect_data": {
                "id": suspect_id,
                "username": suspect_username,
                "name": suspect_name,
                "bio": suspect_bio,
                "profile_url": suspect_url,
                "profile_pic_path": suspect_pic_path
            }
        }
    
    def generate_report(self, 
                       original_profile: ProfileData, 
                       impersonator_results: List[Dict]) -> Dict:
        """Generate a comprehensive report of potential impersonators"""
        logger.info("Generating impersonator report")
        
        # Filter to confirmed potential impersonators
        potential_impersonators = [
            result for result in impersonator_results 
            if result.get("is_potential_impersonator", False)
        ]
        
        # Sort by overall similarity score (descending)
        potential_impersonators.sort(
            key=lambda x: x.get("similarity_scores", {}).get("overall", 0), 
            reverse=True
        )
        
        # Group by platform
        grouped_results = {}
        for result in potential_impersonators:
            platform = result.get("platform")
            if platform not in grouped_results:
                grouped_results[platform] = []
            grouped_results[platform].append(result)
        
        # Generate report data
        report = {
            "original_profile": {
                "platform": original_profile.platform,
                "user_id": original_profile.user_id,
                "username": original_profile.username,
                "full_name": original_profile.full_name,
                "profile_url": original_profile.profile_url,
                "profile_pic_path": original_profile.profile_pic_path
            },
            "summary": {
                "total_impersonators": len(potential_impersonators),
                "platforms": list(grouped_results.keys()),
                "impersonators_by_platform": {
                    platform: len(results) 
                    for platform, results in grouped_results.items()
                }
            },
            "potential_impersonators": potential_impersonators
        }
        
        return report

    def save_report(self, report: Dict, output_path: str = "impersonator_report.json") -> str:
        """Save the report to a JSON file"""
        try:
            with open(output_path, 'w') as report_file:
                json.dump(report, report_file, indent=2)
            logger.info(f"Report saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving report: {e}")
            return ""
    
    def run_detection(self, 
                     original_platform: str, 
                     original_identifier: str,
                     target_platforms: List[str] = None) -> Dict:
        """Run the full impersonator detection process"""
        if target_platforms is None:
            target_platforms = ["facebook", "instagram", "twitter", "linkedin"]
        
        logger.info(f"Starting impersonator detection for {original_identifier} on {original_platform}")
        
        # Fetch original profile
        original_profile = self.fetch_original_profile(original_platform, original_identifier)
        if not original_profile:
            logger.error("Failed to fetch original profile")
            return {"error": "Failed to fetch original profile"}
        
        # Search and analyze potential impersonators across platforms
        all_results = []
        
        for platform in target_platforms:
            # Skip the platform of the original profile if it's in the target list
            if platform.lower() == original_platform.lower():
                continue
                
            # Search for potential matches
            search_params = {"limit": 20}  # Adjust as needed
            search_results = self.search_potential_impersonators(
                original_profile, platform, search_params
            )
            
            # Analyze each result
            for suspect_data in search_results:
                analysis_result = self.analyze_potential_impersonator(
                    original_profile, suspect_data, platform
                )
                
                if "skip_reason" not in analysis_result:
                    all_results.append(analysis_result)
        
        # Generate and save report
        report = self.generate_report(original_profile, all_results)
        report_path = self.save_report(report)
        
        return {
            "status": "success",
            "original_profile": {
                "platform": original_profile.platform,
                "user_id": original_profile.user_id,
                "username": original_profile.username
            },
            "report_path": report_path,
            "summary": report["summary"]
        }

def main():
    """Main entry point"""
    # Example usage
    detector = ImpersonatorDetector()
    
    # Run detection for a user
    result = detector.run_detection(
        original_platform="instagram",
        original_identifier="example_user",
        target_platforms=["facebook", "twitter", "linkedin"]
    )
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()