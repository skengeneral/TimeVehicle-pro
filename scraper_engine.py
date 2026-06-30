import os
import sys
import time
import re
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Import Playwright's synchronous API
from playwright.sync_api import sync_playwright

def get_local_api_key():
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

def get_stored_api_key():
    """Maps directly to local loader to handle dynamic cross-calls flawlessly."""
    return get_local_api_key()

def decode_cloudflare_emails(html_content):
    """
    Cloudflare's email obfuscation (very common on WordPress sites and
    any site behind Cloudflare with email protection enabled) hides
    emails as: <span data-cfemail="HEXSTRING">[email protected]</span>
    The hex string is XOR-encoded against its own first byte.
    This decodes any found instances and appends them as plain text
    so the normal email regex below can pick them up.
    """
    if not html_content or 'data-cfemail' not in html_content:
        return html_content
    matches = re.findall(r'data-cfemail="([a-f0-9]+)"', html_content)
    decoded_emails = []
    for hex_str in matches:
        try:
            r = int(hex_str[:2], 16)
            decoded = ''.join(
                chr(int(hex_str[i:i+2], 16) ^ r)
                for i in range(2, len(hex_str), 2)
            )
            if '@' in decoded:
                decoded_emails.append(decoded)
        except Exception:
            continue
    if decoded_emails:
        return html_content + " " + " ".join(decoded_emails)
    return html_content

def extract_emails_from_text(text_content):
    if not text_content:
        return None

    # Decode any Cloudflare-protected emails before scanning
    text_content = decode_cloudflare_emails(text_content)

    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}'
    raw_emails = re.findall(email_pattern, text_content)
    
    mailto_emails = re.findall(r'href=["\']mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6})', text_content, re.IGNORECASE)

    # Handle human-readable obfuscation: "info (at) domain (dot) com",
    # "info[at]domain[dot]com", "info AT domain DOT com" — common on
    # small business sites trying to dodge basic email scrapers
    obfuscated_pattern = (
        r'([a-zA-Z0-9._%+-]+)\s*[\[\(]?\s*(?:at|AT)\s*[\]\)]?\s*'
        r'([a-zA-Z0-9.-]+)\s*[\[\(]?\s*(?:dot|DOT)\s*[\]\)]?\s*([a-zA-Z]{2,6})'
    )
    obfuscated_matches = re.findall(obfuscated_pattern, text_content)
    obfuscated_emails = [f"{m[0]}@{m[1]}.{m[2]}" for m in obfuscated_matches]

    all_found = raw_emails + mailto_emails + obfuscated_emails
    
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

def fetch_email_via_google_search(api_key, business_name, full_address=None,
                                   target_city=None, website_url=None):
    """
    Deep email search using Google via SerpAPI.

    Query format follows the user-discovered pattern that triggers Google
    AI Overview:  "Business Name, City - email id"

    Four attempts are made before giving up:
      Attempt 1 — AI-mode query:        "{name}, {city} - email id"
      Attempt 2 — Second AI-mode query: "{name}, {city} - what is their email address"
                  (differently worded in case the first phrasing didn't
                   trigger an AI Overview for this specific business)
      Attempt 3 — Site-restricted:      "email site:{domain}"
                  (only when we know the business's website — searches
                   Google's index of that exact site, which often
                   surfaces an email from a contact page even when our
                   own browser crawler couldn't load the site directly)
      Attempt 4 — Generic fallback:     "{name} {city} official contact email"

    Each later attempt only runs when all earlier ones find nothing, so
    extra API credits are only spent on businesses with genuinely
    hard-to-find emails.

    Every SerpAPI response field is checked:
      ai_overview → answer_box → knowledge_graph → organic snippets
    """
    endpoint = "https://serpapi.com/search.json"

    # ── Detect target country for geo-targeting ──────────────────────
    # AI Overview rollout and result relevance both depend on the gl
    # (country) parameter. Hardcoding "us" would skew results for
    # clients searching in Canada, UK, Australia, India, etc. — so we
    # detect the country from whatever location info is available and
    # fall back to "us" only when nothing can be determined.
    COUNTRY_CODES = {
        "usa": "us", "united states": "us", "america": "us",
        "canada": "ca",
        "uk": "gb", "united kingdom": "gb", "england": "gb",
        "scotland": "gb", "wales": "gb", "northern ireland": "gb",
        "australia": "au",
        "new zealand": "nz",
        "ireland": "ie",
        "india": "in",
        "south africa": "za",
        "singapore": "sg",
        "philippines": "ph",
        "malaysia": "my",
        "nigeria": "ng",
        "kenya": "ke",
        "pakistan": "pk",
        "uae": "ae", "united arab emirates": "ae",
        "jamaica": "jm",
        "trinidad": "tt", "trinidad and tobago": "tt",
        "ghana": "gh",
        "zimbabwe": "zw",
        "malta": "mt",
        "fiji": "fj",
        "sri lanka": "lk",
        "bangladesh": "bd",
        "hong kong": "hk",
    }
    location_text = f"{target_city or ''} {full_address or ''}".lower()
    detected_gl = "us"   # sensible default — AI Overview triggers most reliably here
    for country_name, code in COUNTRY_CODES.items():
        if country_name in location_text:
            detected_gl = code
            break

    # ── Clean business name for search ──────────────────────────────
    # Google Maps titles often include marketing suffixes after a dash
    # or pipe, e.g. "SF Custom Chiropractic - #1 Chiropractor Fisherman's
    # Wharf Russian Hill". These long descriptive titles break the
    # AI Overview trigger and hurt search relevance, so we use only
    # the core business name (before the first " - " or "|").
    clean_name = business_name
    for separator in [" - ", " – ", " — ", " | "]:
        if separator in clean_name:
            clean_name = clean_name.split(separator)[0].strip()
            break

    # ── Extract just the city name ─────────────────────────────────
    # target_city arrives as e.g. "Ottawa, Ontario, Canada" or "New York, NY, USA"
    # We want only the first segment: "Ottawa" / "New York"
    city_only = ""
    if target_city:
        city_only = target_city.split(',')[0].strip()
    if not city_only and full_address and full_address != "Not Provided":
        parts = [p.strip() for p in full_address.split(',')]
        # City sits roughly third-from-end in most address formats
        city_only = parts[-3] if len(parts) >= 3 else (parts[0] if parts else "")
    if not city_only:
        city_only = "USA"

    def _search_and_extract(query):
        """Run one SerpAPI Google search and scan every result field for an email."""
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "hl": "en",          # English UI — appropriate for English-speaking markets
            "gl": detected_gl,   # geo-targeted to the business's actual country
        }
        try:
            resp = requests.get(endpoint, params=params, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()

            # 1. Google AI Overview — where AI-mode answers surface
            ai_overview = data.get("ai_overview", {})
            if ai_overview:
                # Google sometimes defers AI Overview generation and only
                # returns a page_token instead of the actual content. In
                # that case we must make a follow-up call to retrieve the
                # real text — without this, the ai_overview block is just
                # an empty shell with no usable text to extract from.
                if "page_token" in ai_overview:
                    try:
                        followup_params = {
                            "engine": "google_ai_overview",
                            "page_token": ai_overview["page_token"],
                            "api_key": api_key,
                        }
                        followup_resp = requests.get(endpoint, params=followup_params, timeout=15)
                        if followup_resp.status_code == 200:
                            followup_data = followup_resp.json()
                            full_overview = followup_data.get("ai_overview", followup_data)
                            found = extract_emails_from_text(str(full_overview))
                            if found: return found
                    except Exception:
                        pass
                else:
                    found = extract_emails_from_text(str(ai_overview))
                    if found: return found

            # 2. Answer box (featured snippets, direct answers)
            answer_box = data.get("answer_box", {})
            ab_text = str(answer_box.get("answer") or answer_box.get("snippet") or "")
            found = extract_emails_from_text(ab_text)
            if found: return found

            # 3. Knowledge graph (business panels)
            found = extract_emails_from_text(str(data.get("knowledge_graph", {})))
            if found: return found

            # 4. Organic result snippets + rich snippets
            for result in data.get("organic_results", [])[:5]:
                combined = (
                    result.get("snippet", "") + " " +
                    str(result.get("rich_snippet", "")) + " " +
                    str(result.get("sitelinks", ""))
                )
                found = extract_emails_from_text(combined)
                if found: return found

        except Exception:
            pass
        return None

    # ── Attempt 1: AI-mode optimised query ──────────────────────────
    query_1 = f"{clean_name}, {city_only} - email id"
    result = _search_and_extract(query_1)
    if result:
        return result

    # ── Attempt 2: Second AI-mode query, different phrasing ─────────
    # If the first AI-mode-style query didn't trigger an overview or
    # didn't surface an email, try a differently worded query that
    # still follows the short, direct phrasing that reliably triggers
    # Google's AI Overview (as opposed to a long descriptive sentence).
    query_2 = f"{clean_name}, {city_only} - what is their email address"
    result = _search_and_extract(query_2)
    if result:
        return result

    # ── Attempt 3: Site-restricted search (only if website is known) ─
    # Searches Google's index of the exact website domain — this often
    # finds an email from a contact/about page even when our own
    # browser crawler failed to load the site (slow, JS-heavy, or
    # blocking automated browsers).
    if website_url and website_url not in ("No Website", "", None):
        try:
            domain = urlparse(
                website_url if website_url.startswith("http") else f"https://{website_url}"
            ).netloc.replace("www.", "")
        except Exception:
            domain = ""
        if domain:
            query_3 = f"email site:{domain}"
            result = _search_and_extract(query_3)
            if result:
                return result

    # ── Attempt 4: Generic contact-page organic fallback ────────────
    query_4 = f"{clean_name} {city_only} official contact email"
    result = _search_and_extract(query_4)
    if result:
        return result

    return "Not Provided"


def launch_shared_browser(playwright_instance, progress_callback=None):
    """
    Launches ONE browser for the entire search session, reused across
    every business. Previously a brand new browser was launched and
    closed for every single business (~100 times per search) — slow,
    resource-heavy, and a much larger surface area for silent failures.
    Tries Chrome first, then Edge, then bundled Chromium as last resort.
    """
    def log(m):
        if progress_callback: progress_callback(m)

    for channel in ["chrome", "msedge"]:
        try:
            browser = playwright_instance.chromium.launch(headless=True, channel=channel)
            log(f"🌐 Using {channel.capitalize()} for website scanning")
            return browser
        except Exception:
            continue
    try:
        browser = playwright_instance.chromium.launch(headless=True)
        log("🌐 Using bundled Chromium for website scanning")
        return browser
    except Exception as e:
        log(f"⚠️ Could not launch any browser — website scanning disabled this session: {str(e)[:80]}")
        return None


def scrape_page_with_browser(browser_context, target_url):
    try:
        page = browser_context.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})
        # "domcontentloaded" is more forgiving than "load" for slow or
        # JS-heavy sites — we just need the HTML structure, not every
        # asset to finish loading. Timeout raised from 12s to 20s to
        # accommodate slower small-business websites.
        response = page.goto(target_url, timeout=20000, wait_until="domcontentloaded")
        if not response or response.status != 200:
            page.close()
            return None
        time.sleep(1.5)
        rendered_content = page.content()
        page.close()
        return rendered_content
    except:
        return None

def extract_contact_metrics_from_website(browser, website_url, progress_callback=None):
    """
    browser: a single shared Playwright browser instance (launched once
             per search session) — NOT relaunched per business.
    """
    def log(msg):
        if progress_callback: progress_callback(msg)

    contact_data = {
        "Email ID": "Not Provided"
    }
    if not website_url or "No Website" in website_url or not website_url.startswith("http"):
        return contact_data

    if browser is None:
        return contact_data   # no browser available this session

    # Keep the original URL so we can fall back to it if https fails
    original_url = website_url
    if website_url.startswith("http://"):
        website_url = website_url.replace("http://", "https://", 1)

    context = None
    try:
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        homepage_html = scrape_page_with_browser(context, website_url)

        # ── HTTP fallback ──────────────────────────────────────────
        # Some older business websites (small brokers, local firms) don't
        # support HTTPS or have expired/invalid SSL certificates.
        # If the forced-HTTPS version fails, quietly retry with the
        # original HTTP URL rather than abandoning the scrape entirely.
        if not homepage_html and original_url != website_url:
            homepage_html = scrape_page_with_browser(context, original_url)
            if homepage_html:
                website_url = original_url   # keep http for subpage links too

        if not homepage_html:
            log(f"   🌐 Website unreachable — could not load page")
            context.close()
            return contact_data
            
        found_email = extract_emails_from_text(homepage_html)
        if found_email: contact_data["Email ID"] = found_email
        
        if contact_data["Email ID"] == "Not Provided":
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
                    subpage_html = scrape_page_with_browser(context, full_subpage_url)
                    if subpage_html:
                        sub_email = extract_emails_from_text(subpage_html)
                        if sub_email:
                            contact_data["Email ID"] = sub_email
                            break
            if contact_data["Email ID"] == "Not Provided":
                log(f"   🌐 Website scanned — no email found on homepage or contact pages")
        context.close()
    except Exception as e:
        log(f"   🌐 Website scan error: {str(e)[:80]}")
        if context:
            try: context.close()
            except: pass
    return contact_data


# ─────────────────────────────────────────────────────────────────
#  MAIN ENGINE
#  Changes vs previous version:
#    1. Smart title-keyword filter REMOVED — Google Maps relevance
#       is trusted to return correct business types (e.g. searching
#       "banks" will return Chase, Citibank etc. without needing the
#       word "bank" in their name).
#    2. Pagination now stops when results dry up (< results_per_page)
#       instead of checking for a "next" key that Google Maps often
#       doesn't include — this was silently capping results at 20.
#    3. max_pages raised to 10 (up to 200 potential results).
#    4. progress_callback parameter added for live UI log feed.
# ─────────────────────────────────────────────────────────────────
def extract_local_leads(search_query, allowed_ratings, target_city=None,
                        progress_callback=None, stop_callback=None):
    def log(msg):
        if progress_callback: progress_callback(msg)
        else: print(msg)

    def should_stop():
        return stop_callback and stop_callback()

    api_key = get_local_api_key()
    if not api_key:
        log("❌ ERROR: No API key found. Place your key in serp_api.txt")
        return {"data": [], "columns_layout": None}
        
    filtered_leads = []
    processed_titles = set()
    endpoint = "https://serpapi.com/search.json"
    current_page = 1
    max_pages = 10          # ← raised: supports up to 200 results
    results_per_page = 20
    total_leads = 0

    with sync_playwright() as p:
        shared_browser = launch_shared_browser(p, progress_callback)

        while current_page <= max_pages:
            start_offset = (current_page - 1) * results_per_page
            full_search_string = (
                f"{search_query}, {target_city.strip()}"
                if target_city and target_city.strip()
                else search_query
            )
            
            log(f"📡 Page {current_page}/{max_pages} — querying Google Maps (offset {start_offset})...")
            
            params = {
                "engine": "google_maps",
                "q": full_search_string,
                "type": "search",
                "api_key": api_key,
                "start": start_offset
            }

            try:
                response = requests.get(endpoint, params=params, timeout=20)
                if response.status_code != 200:
                    log(f"⚠️ API returned HTTP {response.status_code} — stopping search.")
                    break
                data = response.json()

                # ── Credit exhaustion check ────────────────────────
                error_info = data.get("error", "")
                if error_info:
                    error_str = str(error_info).lower()
                    if any(w in error_str for w in ["credit", "limit", "quota", "run out", "exceeded"]):
                        log(f"")
                        log(f"💳 SERPAPI CREDITS EXHAUSTED")
                        log(f"   Your SerpAPI search credits have run out.")
                        log(f"   {len(filtered_leads)} leads collected before credits ran out.")
                        log(f"   Please recharge at serpapi.com/plan and search again.")
                    else:
                        log(f"⚠️ API error: {error_info}")
                    break
                raw_results = data.get("local_results", [])
                
                if not raw_results:
                    log("✅ No more listings from Google — search complete.")
                    break
                    
                log(f"   ↳ {len(raw_results)} listings returned on this page.")
                
                for biz in raw_results:
                    # ── Stop check ─────────────────────────────────
                    if should_stop():
                        log("⏹️  Search stopped by user.")
                        break
                    title = biz.get("title") or biz.get("name") or "Unknown"
                    if title.lower().strip() in processed_titles:
                        continue

                    # ── Rating filter ──────────────────────────────────────
                    try: rating_val = float(biz.get("rating", 0))
                    except: rating_val = 0.0
                    
                    rating_matches = False
                    if "ALL" in allowed_ratings:
                        rating_matches = True
                    else:
                        for selected_rate in allowed_ratings:
                            try:
                                target_int = int(selected_rate)
                                if (target_int == 5 and rating_val == 5.0) or \
                                   (target_int <= rating_val < (target_int + 1)):
                                    rating_matches = True
                                    break
                            except ValueError:
                                continue

                    if not rating_matches:
                        continue

                    # ── ATM Filter ─────────────────────────────────────────
                    # Catches ATMs three ways:
                    #   1. Name contains the word "ATM"
                    #      e.g. "TD Bank ATM", "Santander Bank ATM"
                    #   2. Google Maps type field is "ATM"
                    #   3. Website URL path contains /atm- or /atm_
                    #      e.g. Bank of America locator URLs for ATM entries
                    #      even when the listing name says "Home Loans" etc.
                    biz_type     = str(biz.get("type", "")).strip()
                    biz_type_low = biz_type.lower()
                    title_words  = set(title.lower().split())
                    website_raw  = biz.get("website") or ""
                    website_low  = website_raw.lower()

                    if (
                        "atm" in title_words          or   # "TD Bank ATM"
                        "atm" in biz_type_low         or   # type: "ATM"
                        "/atm-" in website_low        or   # /atm-new-york-104542
                        "/atm_" in website_low             # alternate URL pattern
                    ):
                        log(f"⏭️  ATM skipped: {title}")
                        continue

                    # ── Accepted — begin data collection ───────────────────
                    processed_titles.add(title.lower().strip())
                    total_leads += 1
                    website_link = biz.get("website") or "No Website"
                    full_address = biz.get("address", "") or "Not Provided"
                    
                    log(f"🏢 [{total_leads}] {title}")
                    
                    found_metrics = extract_contact_metrics_from_website(
                        shared_browser, website_link, progress_callback
                    )
                    email_id = found_metrics["Email ID"]
                    
                    if email_id == "Not Provided":
                        log(f"   🔎 Searching Google for email...")
                        email_id = fetch_email_via_google_search(
                            api_key, title, full_address, target_city, website_link
                        )
                        if email_id != "Not Provided":
                            log(f"   ✅ Email found via Google: {email_id}")
                        else:
                            log(f"   ⚠️  Email not found for {title}")
                    
                    gps_hours = biz.get("operating_hours", {})
                    hours_string = (
                        " | ".join([f"{day.capitalize()}: {t}" for day, t in gps_hours.items()])
                        if isinstance(gps_hours, dict) else "Not Provided"
                    )
                    
                    lead_card = {
                        "Business Name":          title,
                        "Google Rating":          rating_val,
                        "Complete Address":        full_address,
                        "Operating Hours Matrix":  hours_string,
                        "Website Link":            website_link,
                        "Email ID":               email_id,
                        "Phone Number":            biz.get("phone") or "Not Provided",
                    }
                    filtered_leads.append(lead_card)

                # ── Pagination: stop when last page has fewer rows ─────────
                # Google Maps does not reliably include a "next" pagination
                # key, so we stop only when results drop below a full page.
                if should_stop():
                    break

                if len(raw_results) < results_per_page:
                    log("✅ Received partial page — no more results available.")
                    break

                current_page += 1
                time.sleep(1)

            except Exception as e:
                log(f"❌ Error on page {current_page}: {str(e)}")
                break

        if shared_browser:
            try: shared_browser.close()
            except: pass

    log(f"")
    if should_stop():
        log(f"⏹️  STOPPED — {len(filtered_leads)} leads saved to file.")
    else:
        log(f"🎯 DONE — {len(filtered_leads)} qualified leads collected.")
    return {"data": filtered_leads, "columns_layout": None}
