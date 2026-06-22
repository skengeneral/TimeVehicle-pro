import os
import sys
import time
import re
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

def get_stored_api_key():
    if getattr(sys, 'frozen', False):
        current_dir = Path(sys.executable).parent
    else:
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    key_file_path = current_dir / "serp_api.txt"
    if key_file_path.exists():
        try:
            with open(key_file_path, "r", encoding="utf-8") as file:
                return file.read().strip()
        except: pass
    return os.environ.get("SERPAPI_KEY")

def extract_emails_from_text(text_content):
    """Parses text segments using clean regular expressions to harvest target emails."""
    if not text_content:
        return None
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}'
    raw_emails = re.findall(email_pattern, text_content)
    
    mailto_emails = re.findall(r'href=["\']mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6})', text_content, re.IGNORECASE)
    all_found = raw_emails + mailto_emails
    
    if all_found:
        clean_emails = []
        for e in all_found:
            e_lower = e.lower()
            garbage_keywords = ['sentry', 'wixpress', 'example', 'yourdomain', 'template', 'email', 'domain', 'magicpin', 'baidyanath', 'dfat.gov']
            asset_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.html')
            
            if not e_lower.endswith(asset_extensions):
                if not any(bad_word in e_lower for bad_word in garbage_keywords):
                    clean_emails.append(e_lower)
        if clean_emails:
            clean_emails.sort(key=len)
            return clean_emails[0]
    return None

def extract_social_from_text(text_content, platform):
    """Scans text snippet variations to find matching social media profile links or handles."""
    if not text_content:
        return None
    
    patterns = {
        "Facebook": r'(https?://(?:www\.)?facebook\.com/[a-zA-Z0-9_\-\.]+)',
        "Instagram": r'(https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_\-\.]+)',
        "LinkedIn": r'(https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_\-\.]+)',
        "Twitter/X": r'(https?://(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9_\-\.]+)'
    }
    
    match = re.search(patterns[platform], text_content, re.IGNORECASE)
    if match:
        return match.group(1)
        
    handle_match = re.search(r'@([a-zA-Z0-9_\-\.]+)', text_content)
    if handle_match:
        base_urls = {
            "Facebook": "https://facebook.com/", "Instagram": "https://instagram.com/",
            "LinkedIn": "https://linkedin.com/in/", "Twitter/X": "https://x.com/"
        }
        return f"{base_urls[platform]}{handle_match.group(1)}"
        
    return None

def fetch_email_via_google_search(api_key, business_name, full_address=None, target_city=None):
    """Executes a multi-stage search fallback using both the live address and dashboard entries."""
    endpoint = "https://serpapi.com/search.json"
    
    geo_tail = ""
    if full_address and full_address != "Not Provided":
        address_parts = [p.strip() for p in full_address.split(',')]
        if len(address_parts) >= 2:
            geo_tail = f"{address_parts[-2]}, {address_parts[-1]}"
            
    if not geo_tail and target_city:
        geo_tail = target_city.strip()
        
    if not geo_tail:
        geo_tail = "USA"
        
    search_query = f"{business_name}, {geo_tail} email id"
    print(f"🔍 Executing Smart Fallback Search: '{search_query}'...")
    
    params = {"engine": "google", "q": search_query, "api_key": api_key}
    try:
        response = requests.get(endpoint, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            answer_box = data.get("answer_box", {})
            answer_text = str(answer_box.get("answer") or answer_box.get("snippet") or "")
            found = extract_emails_from_text(answer_text)
            if found: return found
                
            organic_results = data.get("organic_results", [])
            for result in organic_results[:4]:
                found = extract_emails_from_text(result.get("snippet", ""))
                if found: return found
    except: pass
    return "Not Provided"

def fetch_social_via_google_search(api_key, business_name, platform, target_city=None):
    """Executes a secondary geo-targeted organic Google Search query to exploit AI Overviews for Socials."""
    endpoint = "https://serpapi.com/search.json"
    city_clean = target_city.strip().lower() if target_city else ""
    
    if "noida" in city_clean or "india" in city_clean:
        geo_tail = "noida, india"
    elif "brisbane" in city_clean or "australia" in city_clean:
        geo_tail = "brisbane, australia"
    else:
        geo_tail = f"{target_city.strip()}" if target_city else ""
        
    search_query = f"{business_name}, {geo_tail} {platform.lower()} handle"
    print(f"📱 Social Fallback Search [{platform}]: '{search_query}'...")
    
    params = {"engine": "google", "q": search_query, "api_key": api_key}
    
    try:
        response = requests.get(endpoint, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            answer_box = data.get("answer_box", {})
            answer_text = str(answer_box.get("answer") or answer_box.get("snippet") or "")
            found = extract_social_from_text(answer_text, platform)
            if found:
                print(f"   🎯 SUCCESS! Found {platform} in AI Overview: {found}")
                return found
                
            organic_results = data.get("organic_results", [])
            for result in organic_results[:3]:
                found = extract_social_from_text(result.get("link", "") + " " + result.get("snippet", ""), platform)
                if found:
                    print(f"   🎯 SUCCESS! Found {platform} in Search Snippet: {found}")
                    return found
    except: pass
    return "Not Provided"

def scrape_page_with_requests(target_url):
    """High-speed lightweight HTML requester using standard network sessions instead of heavy browser frameworks."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    try:
        response = requests.get(target_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
    except:
        pass
    return None

def extract_contact_metrics_from_website(website_url):
    socials = {
        "Facebook": "Not Provided", "Instagram": "Not Provided", 
        "LinkedIn": "Not Provided", "Twitter/X": "Not Provided",
        "Email ID": "Not Provided"
    }
    if not website_url or "No Website" in website_url or not website_url.startswith("http"):
        return socials
        
    if website_url.startswith("http://"):
        website_url = website_url.replace("http://", "https://", 1)
        
    try:
        homepage_html = scrape_page_with_requests(website_url)
        if not homepage_html:
            return socials
            
        found_email = extract_emails_from_text(homepage_html)
        if found_email: socials["Email ID"] = found_email
            
        fb_match = re.search(r'href=["\'](https?://(?:www\.)?facebook\.com/[a-zA-Z0-9_\-\.]+)/?["\']', homepage_html, re.IGNORECASE)
        ig_match = re.search(r'href=["\'](https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_\-\.]+)/?["\']', homepage_html, re.IGNORECASE)
        li_match = re.search(r'href=["\'](https?://(?:www\.)?linkedin\.com/(?:in|company)/[a-zA-Z0-9_\-\.]+)/?["\']', homepage_html, re.IGNORECASE)
        tw_match = re.search(r'href=["\'](https?://(?:www\.)?(?:twitter|x)\.com/[a-zA-Z0-9_\-\.]+)/?["\']', homepage_html, re.IGNORECASE)
        
        if fb_match: socials["Facebook"] = fb_match.group(1)
        if ig_match: socials["Instagram"] = ig_match.group(1)
        if li_match: socials["LinkedIn"] = li_match.group(1)
        if tw_match: socials["Twitter/X"] = tw_match.group(1)
        
        if socials["Email ID"] == "Not Provided":
            contact_links = set()
            raw_links = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', homepage_html, re.IGNORECASE)
            for link in raw_links:
                if any(k in link.lower() for k in ['contact', 'about', 'register', 'info', 'reach']):
                    contact_links.add(link)
            parsed_base = urlparse(website_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            
            if len(contact_links) == 0:
                for route in ['/contact-us', '/contact', '/about-us', '/about']:
                    contact_links.add(route)
            processed_subpages = set()
            for link in contact_links:
                full_subpage_url = urljoin(website_url, link) if (link.startswith('/') or link.startswith('http')) else f"{base_domain.rstrip('/')}/{link.lstrip('/')}"
                if base_domain in full_subpage_url and full_subpage_url not in processed_subpages:
                    processed_subpages.add(full_subpage_url)
                    subpage_html = scrape_page_with_requests(full_subpage_url)
                    if subpage_html:
                        sub_email = extract_emails_from_text(subpage_html)
                        if sub_email:
                            socials["Email ID"] = sub_email
                            break
    except: pass
    return socials

def extract_local_leads(search_query, allowed_ratings, target_city=None):
    api_key = get_stored_api_key()
    if not api_key:
        print("❌ ERROR: No API key found inside your 'serp_api.txt' file.")
        return {"data": [], "columns_layout": None}
        
    filtered_leads = []
    processed_titles = set()
    
    endpoint = "https://serpapi.com/search.json"
    current_page = 1
    max_pages = 5                  
    results_per_page = 20

    print("🚀 Initializing Master Automation Scraper Engine...")

    while current_page <= max_pages:
        start_offset = (current_page - 1) * results_per_page
        full_search_string = search_query
        if target_city and target_city.strip():
            full_search_string = f"{search_query}, {target_city.strip()}"
            
        params = {
            "engine": "google_maps",
            "q": full_search_string,
            "type": "search",
            "api_key": api_key,
            "start": start_offset
        }

        print(f"\n📄 Scraping Page {current_page} of {max_pages}...")
        try:
            response = requests.get(endpoint, params=params, timeout=20)
            if response.status_code != 200: break
                
            data = response.json()
            raw_results = data.get("local_results", [])
            if not raw_results: break
                
            for biz in raw_results:
                title = biz.get("title") or biz.get("name") or "Unknown Firm"
                
                if title.lower().strip() in processed_titles:
                    continue
                    
                raw_rating = biz.get("rating", 0)
                try: rating_val = float(raw_rating)
                except: rating_val = 0.0
                
                rating_matches = False
                if "ALL" in allowed_ratings:
                    rating_matches = True
                else:
                    for selected_rate in allowed_ratings:
                        try:
                            target_int = int(selected_rate)
                            if target_int == 5 and rating_val == 5.0:
                                rating_matches = True
                                break
                            elif target_int <= rating_val < (target_int + 1):
                                rating_matches = True
                                break
                        except ValueError: continue
                
                if rating_matches:
                    processed_titles.add(title.lower().strip())
                    website_link = biz.get("website") or "No Website"
                    full_address = biz.get("address", "") or "Not Provided"
                    
                    # Step 1: Standard website HTML session crawl
                    found_metrics = extract_contact_metrics_from_website(website_link)
                    
                    email_id = found_metrics["Email ID"]
                    fb_id = found_metrics["Facebook"]
                    ig_id = found_metrics["Instagram"]
                    li_id = found_metrics["LinkedIn"]
                    tw_id = found_metrics["Twitter/X"]
                    
                    # Step 2: Multi-Layer Google Search Fallback Engine (Exhaustive Search Mode)
                    if email_id == "Not Provided":
                        email_id = fetch_email_via_google_search(api_key, title, full_address, target_city)
                    if fb_id == "Not Provided":
                        fb_id = fetch_social_via_google_search(api_key, title, "Facebook", target_city)
                    if ig_id == "Not Provided":
                        ig_id = fetch_social_via_google_search(api_key, title, "Instagram", target_city)
                    if li_id == "Not Provided":
                        li_id = fetch_social_via_google_search(api_key, title, "LinkedIn", target_city)
                    if tw_id == "Not Provided":
                        tw_id = fetch_social_via_google_search(api_key, title, "Twitter/X", target_city)
                    
                    gps_hours = biz.get("operating_hours", {})
                    hours_string = " | ".join([f"{day.capitalize()}: {t}" for day, t in gps_hours.items()]) if (isinstance(gps_hours, dict) and gps_hours) else "Not Provided"
                    
                    lead_card = {
                        "Business Name": title, "Google Rating": rating_val, 
                        "Complete Address": full_address, "Operating Hours Matrix": hours_string, 
                        "Website Link": website_link, "Email ID": email_id,
                        "Phone Number": biz.get("phone") or "Not Provided",
                        "Facebook Handle": fb_id, "Instagram Handle": ig_id,
                        "LinkedIn Handle": li_id, "Twitter/X Handle": tw_id
                    }
                    filtered_leads.append(lead_card)
            
            serp_pagination = data.get("serpapi_pagination", {})
            if "next" not in serp_pagination: break
            current_page += 1
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            break

    return {"data": filtered_leads, "columns_layout": None}
