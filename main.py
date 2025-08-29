import streamlit as st
import requests
import json
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright
from google import genai

# Page config
st.set_page_config(
    page_title="Places Search",
    page_icon="🔍",
    layout="wide"
)

# Title and header
st.title("🔍 Places Search")
st.markdown("Search for any type of business or place using Google Places API")

# Input fields
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input(
        "Search Query", 
        placeholder="e.g., coffee shops in houston, pizza restaurants in austin, gyms near me",
        help="Enter what you're looking for and where"
    )

with col2:
    st.write("")  # Add some spacing
    search_clicked = st.button("🔍 Search", type="primary")

# API key input (collapsed by default)
with st.expander("⚙️ API Settings"):
    api_key = st.text_input("Google Places API Key", 
                           value="YOUR_API_KEY", 
                           type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")

# API endpoint
url = 'https://places.googleapis.com/v1/places:searchText'

def search_places(query, api_key):
    """Search for places using Google Places API"""
    
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'places.displayName,places.formattedAddress,places.priceLevel,places.websiteUri'
    }
    
    data = {
        "textQuery": query
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            return result, None
        else:
            error_msg = f"Request failed with status code: {response.status_code}\nError: {response.text}"
            return None, error_msg
            
    except requests.exceptions.RequestException as e:
        return None, f"An error occurred: {str(e)}"

def process_places(places):
    """Process places data and add website status"""
    processed_places = []
    
    for place in places:
        # Check if website exists
        has_website = 'websiteUri' in place and place['websiteUri']
        
        processed_place = {
            'Name': place.get('displayName', {}).get('text', 'Unknown'),
            'Address': place.get('formattedAddress', 'N/A'),
            'Price Level': place.get('priceLevel', 'N/A'),
            'Has Website': 'Yes' if has_website else 'No',
            'Website': place.get('websiteUri', 'N/A') if has_website else 'N/A'
        }
        processed_places.append(processed_place)
    
    return processed_places

def generate_ui(business_name, gemini_key):
    """Generate UI using Gemini API following uigeneration.py logic"""
    client = genai.Client(api_key=gemini_key)

    prompt = f"""Generate the first half of a premium landing page for a business called "{business_name}". The design should feel luxurious and modern. Use the Inter font for all text. 

Layout:
- Full-width hero section.
- Background: either a subtle gradient or a high-quality themed image with a transparent overlay so text is readable.
- Large, elegant heading: "Welcome to {business_name}" in a premium serif style.
- Subheading: "Your premier destination" in smaller Inter font.
- Call-to-action button: "Learn More" with subtle hover effects.
- Include a small, subtle navigation bar at the top with links: Home, Services, About, Contact.
- Make the design responsive and visually balanced. Include gentle shadows and spacing to give a premium feel.
- Use clean, modern CSS. Keep the code readable and minimal, with HTML5 semantic tags.
- Only code the first half of the landing page (hero section + navigation), do not include the full page or footer.
- Include inline CSS for the styling so the page works standalone.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    html_code = response.text

    # Save the HTML to a file
    file_path = Path("hello_world.html")
    file_path.write_text(html_code, encoding="utf-8")

    # Render webpage and take screenshot
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file://{file_path.resolve()}")
        page.screenshot(path="screenshot.png", full_page=True)
        browser.close()

    return file_path, Path("screenshot.png")

# Main search logic
if search_clicked:
    if not search_query:
        st.error("Please enter a search query")
    elif not api_key:
        st.error("Please provide your Google Places API key in the settings above")
    else:
        with st.spinner(f'Searching for "{search_query}"...'):
            result, error = search_places(search_query, api_key)
        
        if error:
            st.error(f"❌ {error}")
        elif result and 'places' in result:
            places = result['places']
            
            if places:
                st.success(f"✅ Found {len(places)} result(s) for '{search_query}'")
                
                # Process places data
                processed_places = process_places(places)
                
                # Sort places: businesses without websites first
                processed_places.sort(key=lambda x: x['Has Website'] == 'Yes')
                
                # Display results in expandable cards
                st.subheader("📍 Results")
                
                for i, place_data in enumerate(processed_places):
                    with st.expander(f"🏪 {place_data['Name']}", expanded=True):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Address:** {place_data['Address']}")
                            st.write(f"**Price Level:** {place_data['Price Level']}")
                            
                            if place_data['Has Website'] == 'Yes':
                                st.write(f"**Website:** [{place_data['Website']}]({place_data['Website']})")
                            else:
                                st.write("**Website:** No website available")
                        
                        with col2:
                            # Website status badge
                            if place_data['Has Website'] == 'Yes':
                                st.success("✅ Has Website")
                            else:
                                st.error("❌ No Website")
                
                # Display as DataFrame
                st.subheader("📊 Summary Table")
                df = pd.DataFrame(processed_places)
                st.dataframe(df, use_container_width=True)
                
                # Download button for CSV
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=csv,
                    file_name=f"search_results_{search_query.replace(' ', '_')}.csv",
                    mime="text/csv"
                )
                
                
                # Show raw JSON data in expander
                with st.expander("🔍 View Raw JSON Response"):
                    st.json(result)
                    
            else:
                st.warning(f"No results found for '{search_query}'")
        else:
            st.warning("No results returned from the API")

# Instructions (only show when no search has been made)
if not search_clicked:
    st.info("""
    ### How to use:
    1. Enter your search query (e.g., "coffee shops in houston", "pizza restaurants near me")
    2. Expand API Settings to add your Google Places API key if needed
    3. Click "Search" to find results
    
    ### Example searches:
    - `coffee shops in austin texas`
    - `italian restaurants in new york`
    - `gyms near downtown chicago`
    - `bookstores in san francisco`
    - `hair salons in miami`
    
    ### Features:
    - 🔍 Flexible search - any business type, any location
    - 📊 View results in table format
    - 📥 Download results as CSV
    - 🌐 Check website availability
    - 📱 Clean, responsive design
    """)

# Footer
st.markdown("---")
