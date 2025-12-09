import streamlit as st
import urllib.parse
import time
import random
import json
import os
import hashlib
from datetime import datetime

# ---------------------------
# Session state initialization
# ---------------------------
if 'supported_wishes' not in st.session_state:
    st.session_state.supported_wishes = {}
if 'my_wish_probability' not in st.session_state:
    st.session_state.my_wish_probability = 0.0
if 'my_wish_text' not in st.session_state:
    st.session_state.my_wish_text = ""
if 'wish_id' not in st.session_state:
    st.session_state.wish_id = None
if 'show_wish_results' not in st.session_state:
    st.session_state.show_wish_results = False
if 'supporter_id' not in st.session_state:
    # Keep a stable supporter id per session
    st.session_state.supporter_id = f"supporter_{random.randint(1000, 9999)}_{int(time.time())}"
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = time.time()
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0
# NEW: Add session state for success message persistence
if 'show_success_message' not in st.session_state:
    st.session_state.show_success_message = False
if 'success_data' not in st.session_state:
    st.session_state.success_data = {}
if 'success_timestamp' not in st.session_state:
    st.session_state.success_timestamp = 0

# File to store wishes (shared across all users)
WISHES_FILE = "wishes_data.json"

# ---------------------------
# Storage helper functions
# ---------------------------
def load_wishes():
    """Load wishes from file."""
    try:
        if os.path.exists(WISHES_FILE):
            with open(WISHES_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"load_wishes error: {e}")
    return {}

def save_wishes(wishes_data):
    """Save wishes to file."""
    try:
        with open(WISHES_FILE, 'w') as f:
            json.dump(wishes_data, f, indent=2)
        return True
    except Exception as e:
        print(f"save_wishes error: {e}")
        return False

def get_wish_data(wish_id):
    """Get wish data."""
    wishes_data = load_wishes()
    return wishes_data.get(wish_id)

def create_or_update_wish(wish_id, wish_text, initial_probability):
    """Create or update a wish in shared storage."""
    wishes_data = load_wishes()
    now = time.time()
    
    if wish_id not in wishes_data:
        wishes_data[wish_id] = {
            'wish_text': wish_text,
            'initial_probability': float(initial_probability),
            'current_probability': float(initial_probability),
            'supporters': [],
            'total_luck_added': 0.0,
            'created_at': now,
            'last_updated': now,
            'version': 1
        }
    else:
        # Update text and timestamp
        wishes_data[wish_id]['wish_text'] = wish_text
        wishes_data[wish_id]['last_updated'] = now
    
    save_wishes(wishes_data)
    return wishes_data[wish_id]

def update_wish_probability(wish_id, increment, supporter_id):
    """Update wish probability in shared storage."""
    wishes_data = load_wishes()
    
    if wish_id in wishes_data:
        wish_data = wishes_data[wish_id]
        
        # Initialize supporters list if not exists
        if 'supporters' not in wish_data:
            wish_data['supporters'] = []
        
        # Check if supporter already supported
        if supporter_id in wish_data['supporters']:
            return False, wish_data.get('current_probability', 0.0)
        
        # Add supporter and update probability
        wish_data['supporters'].append(supporter_id)
        new_probability = min(99.9, float(wish_data.get('current_probability', 0.0)) + float(increment))
        wish_data['current_probability'] = float(new_probability)
        wish_data['total_luck_added'] = float(wish_data.get('total_luck_added', 0.0)) + float(increment)
        wish_data['last_updated'] = time.time()
        wish_data['version'] = wish_data.get('version', 0) + 1
        
        save_wishes(wishes_data)
        return True, new_probability
    
    return False, None

# ---------------------------
# Utilities
# ---------------------------
def get_random_increment():
    return round(random.uniform(1.0, 10.0), 1)

def generate_wish_id(wish_text):
    unique_str = f"{wish_text}_{time.time()}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:10]

def create_share_link(wish_id, wish_text, probability=None):
    """Create shareable link."""
    base_url = "https://2026christmas-yourwish-mywish-elena.streamlit.app"
    short_wish = wish_text[:80]
    clean_wish = short_wish.replace('\n', ' ').replace('\r', ' ').replace('"', "'").replace('  ', ' ')
    encoded_wish = urllib.parse.quote_plus(clean_wish)
    
    if probability is None:
        probability = st.session_state.get('my_wish_probability', 0.0)
    
    prob_val = f"&prob={float(probability):.1f}"
    full_url = f"{base_url}/?wish_id={wish_id}&wish={encoded_wish}{prob_val}"
    return full_url.strip()

def safe_decode_wish(encoded_wish):
    """Safely decode wish text from URL param."""
    try:
        decoded = urllib.parse.unquote_plus(encoded_wish)
        return decoded
    except Exception:
        try:
            return urllib.parse.unquote(encoded_wish)
        except Exception:
            return encoded_wish

def evaluate_wish_sentiment(wish_text):
    """Simple sentiment analysis without transformers."""
    # Convert to lowercase for easier matching
    text_lower = wish_text.lower()
    
    # Positive keywords
    positive_keywords = [
        'wish', 'hope', 'want', 'dream', 'would love', 'desire', 'aspire',
        'achieve', 'accomplish', 'succeed', 'happy', 'joy', 'peace', 'love',
        'learn', 'improve', 'grow', 'develop', 'better', 'health', 'travel',
        'success', 'prosper', 'thrive', 'flourish', 'excel', 'master'
    ]
    
    # Negative keywords (to avoid)
    negative_keywords = [
        'not', "don't", "won't", "can't", "cannot", "never", "no", "stop",
        "quit", "avoid", "hate", "terrible", "awful", "bad", "worst"
    ]
    
    # Check for wish starters
    wish_starters = ['i wish', 'i hope', 'i want', 'my dream', 'i would love', 'i aspire']
    
    # Score calculation
    score = 0.5  # Base score
    
    # Check for wish starters
    for starter in wish_starters:
        if starter in text_lower:
            score += 0.3
            break
    
    # Check positive keywords
    positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
    score += min(0.3, positive_count * 0.05)
    
    # Check negative keywords
    negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
    score -= min(0.3, negative_count * 0.05)
    
    # Ensure score is between 0 and 1
    score = max(0.1, min(0.95, score))
    
    # Determine label
    if score >= 0.6:
        return 'POSITIVE', score
    elif score >= 0.4:
        return 'NEUTRAL', score
    else:
        return 'NEGATIVE', score

# ---------------------------
# Page config & CSS - REMOVED DEFAULT PADDING
# ---------------------------
st.set_page_config(
    page_title="Wish for 2026",
    page_icon="🎄",
    layout="centered",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default
)

st.markdown("""
<style>
    /* Remove default Streamlit padding/margin */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Compact header styling */
    .compact-header {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 10px;
        font-weight: bold;
        font-size: 16px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #FF5252;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .share-box {
        background-color: #f8f9fa;
        border: 2px dashed #dee2e6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        font-family: 'Courier New', monospace;
        word-break: break-all;
        font-size: 14px;
    }
    .wish-quote {
        font-style: italic;
        font-size: 20px;
        color: #2c3e50;
        margin: 15px 0;
        padding: 15px;
        background: linear-gradient(135deg, #fdfcfb 0%, #e2d1c3 100%);
        border-radius: 15px;
        border-left: 5px solid #e74c3c;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .probability-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 15px 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .update-notification {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        border: none;
        color: white;
        border-radius: 10px;
        padding: 12px;
        margin: 10px 0;
        animation: fadeIn 0.5s;
        text-align: center;
        font-weight: bold;
    }
    .refresh-indicator {
        background-color: rgba(231, 76, 60, 0.1);
        border: 2px solid #e74c3c;
        border-radius: 8px;
        padding: 8px;
        margin: 10px 0;
        font-size: 12px;
        text-align: center;
        color: #e74c3c;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .pulse {
        animation: pulse 2s infinite;
    }
    .success-message {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 15px 0;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        animation: fadeIn 0.5s;
        border: 3px solid rgba(255,255,255,0.5);
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
    }
    .stTextArea textarea {
        border-radius: 10px;
        border: 2px solid #dee2e6;
        padding: 12px;
        font-size: 16px;
        margin: 10px 0;
    }
    h1, h2, h3 {
        color: #2c3e50;
        margin: 0.5rem 0;
    }
    .stale-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 8px;
        border-radius: 6px;
        margin: 8px 0;
        font-size: 12px;
    }
    /* Compact spacing for elements */
    .compact-spacing {
        margin: 8px 0;
    }
    /* Reduce space between sections */
    .section-divider {
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Auto-refresh mechanism
# ---------------------------
def check_and_refresh():
    """Check if we should refresh the page."""
    current_time = time.time()
    
    # Check every 5 seconds
    if current_time - st.session_state.last_refresh_time > 5:
        st.session_state.last_refresh_time = current_time
        st.session_state.refresh_counter += 1
        
        # Auto-refresh every 15 seconds (3 checks)
        if st.session_state.refresh_counter % 3 == 0:
            # Use JavaScript to refresh
            st.components.v1.html("""
            <script>
            setTimeout(function() {
                window.location.reload();
            }, 100);
            </script>
            """)

# ---------------------------
# Query params handling
# ---------------------------
query_params = st.query_params
shared_wish_id = query_params.get("wish_id", None)
shared_wish_text = query_params.get("wish", None)
prob_param = query_params.get("prob", None)

# Parse URL-provided probability
url_prob = None
if prob_param:
    try:
        cleaned = str(prob_param).strip().rstrip('%').replace(',', '')
        url_prob = max(0.0, min(99.9, float(cleaned)))
    except Exception:
        url_prob = None

# Check for auto-refresh
check_and_refresh()

# ---------------------------
# Shared-wish page (if any)
# ---------------------------
if shared_wish_id:
    # Clear success message if it's older than 10 seconds
    if st.session_state.show_success_message:
        if time.time() - st.session_state.success_timestamp > 10:
            st.session_state.show_success_message = False
    
    # Show success message if it exists
    if st.session_state.show_success_message and st.session_state.success_data:
        increment = st.session_state.success_data.get('increment', 0)
        new_probability = st.session_state.success_data.get('new_probability', 0)
        
        st.markdown(f"""
        <div class="success-message compact-spacing">
            <h3>🎄 Thank You!</h3>
            <p style="font-size: 18px;">You added <b>+{increment}%</b> Christmas luck!</p>
            <p style="font-size: 22px; margin: 10px 0;"><b>New Probability: {new_probability:.1f}%</b></p>
            <p style="font-size: 14px;"><i>Your kindness will return to you in 2026! ✨</i></p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show refresh button (compact)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # Show shared wish support section (compact)
    st.markdown("""
    <div style='text-align: center; padding: 15px; background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); 
    border-radius: 12px; margin: 10px 0;'>
    <h3 style='margin: 5px 0;'>🎅 Message from your friend:</h3>
    <p style='font-size: 16px; margin: 5px 0;'><i>"Merry Christmas! I just made a wish for 2026. 
    Please click the button below to share your Christmas luck and help make my wish come true!"</i></p>
    </div>
    """, unsafe_allow_html=True)

    # Decode wish text
    decoded_wish = ""
    if shared_wish_text:
        decoded_wish = safe_decode_wish(shared_wish_text)
        if decoded_wish:
            st.markdown(f'<div class="wish-quote compact-spacing">"{decoded_wish}"</div>', unsafe_allow_html=True)
