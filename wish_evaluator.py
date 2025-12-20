import streamlit as st
import urllib.parse
import time
import random
import json
import os
import hashlib
from datetime import datetime

# ---------------------------s
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
# Page config & CSS
# ---------------------------
st.set_page_config(
    page_title="Wish for 2026",
    page_icon="🎄",
    layout="centered"
)

st.markdown("""
<style>
    /* Reduce top padding and margin */
    .stApp {
        margin-top: -50px !important;
        padding-top: 10px !important;
    }
    
    /* Adjust main container */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Adjust header spacing */
    h1, h2, h3 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
        padding-top: 0 !important;
    }
    
    /* Reduce spacing in probability display */
    .compact-spacing {
        padding: 15px !important;
        margin: 15px 0 !important;
    }
    
    .compact-spacing h1 {
        font-size: 42px !important;
        margin: 10px 0 !important;
    }
    
    .compact-spacing h3 {
        margin: 5px 0 !important;
    }
    
    /* Compact wish quote */
    .compact-wish-quote {
        font-style: italic;
        font-size: 18px;
        color: #2c3e50;
        margin: 15px 0;
        padding: 15px;
        background: linear-gradient(135deg, #fdfcfb 0%, #e2d1c3 100%);
        border-radius: 12px;
        border-left: 4px solid #e74c3c;
        box-shadow: 0 3px 5px rgba(0,0,0,0.1);
    }
    
    /* Compact buttons */
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 16px;
        transition: all 0.3s;
        width: 100% !important;
        margin: 5px 0 !important;
    }
    
    .stButton > button:hover {
        background-color: #FF5252;
        transform: translateY(-1px);
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
    }
    
    /* Compact share box */
    .share-box {
        background-color: #f8f9fa;
        border: 2px dashed #dee2e6;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        font-family: 'Courier New', monospace;
        word-break: break-all;
        font-size: 13px;
    }
    
    /* Compact probability display */
    .probability-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 15px 0;
        box-shadow: 0 5px 12px rgba(0,0,0,0.15);
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
        font-size: 14px;
    }
    
    .refresh-indicator {
        background-color: rgba(231, 76, 60, 0.1);
        border: 2px solid #e74c3c;
        border-radius: 8px;
        padding: 8px;
        margin: 10px 0;
        font-size: 13px;
        text-align: center;
        color: #e74c3c;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.03); }
        100% { transform: scale(1); }
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    
    .success-message {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
        padding: 15px;
        border-radius: 12px;
        margin: 15px 0;
        animation: fadeIn 0.5s;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
    }
    
    .stTextArea textarea {
        border-radius: 8px;
        border: 2px solid #dee2e6;
        padding: 12px;
        font-size: 16px;
        margin: 5px 0;
    }
    
    /* Reduce spacing for text elements */
    p {
        margin: 5px 0 !important;
        padding: 2px 0 !important;
    }
    
    /* Adjust hr spacing */
    hr {
        margin: 15px 0 !important;
    }
    
    /* Footer adjustments */
    .footer-compact {
        text-align: center;
        padding: 10px !important;
        margin-top: 10px !important;
        color: #666;
        font-size: 14px;
    }
    
    /* Center alignment helper */
    .center-content {
        text-align: center;
        padding: 5px 0;
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
    try:
        # Import for audio functionality
        from io import BytesIO
        from gtts import gTTS
    except ImportError:
        # Fallback if gTTS is not available
        pass

    # Show shared wish support section with compact spacing
    st.markdown(f"### 🎅 Message from your friend:")
    
    # Text message
    shared_message = "Merry Xmas! I just made a wish for 2026. Please share your luck and help make my wish come true!"

    try:
        # Try to create audio version
        from io import BytesIO
        from gtts import gTTS
        
        # Convert message to audio
        tts = gTTS(text=shared_message, lang='en')
        
        # Save to BytesIO
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        
        # Display with compact spacing
        st.markdown(f'<div style="margin: 8px 0; font-size: 14px;"><i>"{shared_message}"</i></div>', unsafe_allow_html=True)
        st.markdown("<p style='margin: 5px 0; font-size: 14px;'>**🔊 Listen to the message:**</p>", unsafe_allow_html=True)
        st.audio(audio_bytes, format="audio/mp3")
        
    except Exception as e:
        # Fallback without audio
        st.markdown(f"""
        <div style="padding: 12px; background: #fff3cd; border-radius: 8px; margin: 8px 0; font-size: 14px;">
            <i>"{shared_message}"</i>
        </div>
        """, unsafe_allow_html=True)

    # Decode wish text
    decoded_wish = ""
    if shared_wish_text:
        decoded_wish = safe_decode_wish(shared_wish_text)
        if decoded_wish:
            st.markdown(f'<div class="compact-wish-quote">"{decoded_wish}"</div>', unsafe_allow_html=True)

    # Get current wish data
    wish_data = get_wish_data(shared_wish_id)

    # Create wish if it doesn't exist
    if not wish_data and decoded_wish:
        initial_prob = url_prob if url_prob is not None else 60.0
        wish_data = create_or_update_wish(shared_wish_id, decoded_wish, initial_prob)

    # If we have wish data, display it
    if wish_data:
        current_prob = float(wish_data.get('current_probability', 0.0))
        supporters_count = len(wish_data.get('supporters', []))

        # Store last seen probability for comparison
        if 'last_seen_prob' not in st.session_state:
            st.session_state.last_seen_prob = current_prob

        # Check for updates
        if abs(current_prob - st.session_state.last_seen_prob) > 0.01:
            st.markdown(f"""
            <div class="update-notification">
                🎉 **Probability Updated!** 
                From {st.session_state.last_seen_prob:.1f}% to {current_prob:.1f}%
            </div>
            """, unsafe_allow_html=True)
            st.session_state.last_seen_prob = current_prob

    else:
        st.error("❌ Wish not found. The link might be invalid or expired.")

    # Support button with compact spacing
    increment = get_random_increment()
    button_key = f"support_button_{shared_wish_id}"

    st.markdown('<div class="center-content">', unsafe_allow_html=True)
    if st.button(f"✨ Add Your Luck! (+{increment}%)", 
                 type="primary", 
                 use_container_width=True,
                 key=button_key):
        success, new_probability = update_wish_probability(
            shared_wish_id,
            increment,
            st.session_state.supporter_id
        )
        if success:
            st.markdown(f"""
            <div class="success-message">
                <h4 style="margin: 5px 0;">🎄 Thank You!</h4>
                <p style="margin: 5px 0; font-size: 14px;">You added <b>+{increment}%</b> luck to your friend's wish! Your kindness will return to you in 2026!</p>
            </div>
            """, unsafe_allow_html=True)
            st.balloons()
            st.session_state.last_seen_prob = new_probability
        else:
            st.info("🎅 You've already shared your luck for this wish. Thank you!")

    # Make your own wish section with compact spacing
    st.markdown("---")
