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
    # Show shared wish support section with compact spacing
    st.markdown(f"### 🎅 Message from your friend:")
    
    # Text message
    shared_message = "Merry Xmas! I just made a wish for 2026. Please share your luck and help make my wish come true!"

    # Try to create audio version
    audio_success = False
    try:
        # Convert message to audio
        tts = gTTS(text=shared_message, lang='en')
        
        # Save to BytesIO
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        
        # Display audio player
        st.markdown("<p style='margin: 5px 0; font-size: 14px;'>**🔊 Listen to the message:**</p>", unsafe_allow_html=True)
        st.audio(audio_bytes, format="audio/mp3")
        
    except Exception as e:
        # If audio fails, just show the text
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
    st.markdown("### 🎄 Make Your Own Wish?")
    st.markdown('<div class="center-content">', unsafe_allow_html=True)
    st.markdown("https://2026christmas-yourwish-mywish-elena.streamlit.app/")
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer with compact spacing
    st.markdown("---")
    st.markdown("""
    <div class="footer-compact">
        <p> <i>Hope your wish comes true in 2026! - Yours, Elena</i> </p>
    </div>
    """, unsafe_allow_html=True)

    # Add JavaScript for auto-refresh
    st.components.v1.html("""
    <script>
    // Auto-refresh every 15 seconds
    setTimeout(function() {
        window.location.reload();
    }, 15000);

    // Refresh when page becomes visible
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            setTimeout(function() {
                window.location.reload();
            }, 2000);
        }
    });
    </script>
    """)
    
    st.stop()

# ---------------------------
# Main app: create/evaluate wish
# ---------------------------
if not st.session_state.show_wish_results:
    # Compact welcome message with Christmas-themed colors for each word
    st.markdown("""
    <div class="center-content"> 
        <h3 style="margin: 10px 0;">
            <span style="color: #C41E3A; font-weight: bold;">Hi</span>
            <span style="color: #228B22; font-weight: bold;">there,</span>
            <span style="color: #FFD700; font-weight: bold;">Merry</span>
            <span style="color: #FFFFFF; text-shadow: 1px 1px 2px #000; font-weight: bold;">Xmas!</span>
        </h3>
        <p style="margin: 5px 0; font-size: 16px;">Tell me your wish for 2026, and I'll help evaluate the probability!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add snow animation CSS for textarea
    st.markdown("""
    <style>
    /* Container for the textarea with snow effect */
    .snowy-textarea-container {
        position: relative;
        overflow: visible !important;
        margin: 15px 0;
    }
    
    /* Snowflakes around the textarea */
    .snowy-textarea-container::before,
    .snowy-textarea-container::after {
        content: "❄";
        position: absolute;
        color: white;
        font-size: 12px;
        opacity: 0.7;
        animation: snowFloat 3s linear infinite;
        z-index: 10;
        pointer-events: none;
    }
    
    .snowy-textarea-container::before {
        top: -15px;
        left: 10%;
        animation-delay: 0s;
    }
    
    .snowy-textarea-container::after {
        top: -10px;
        right: 15%;
        animation-delay: 1.5s;
    }
    
    /* Additional snowflake elements */
    .snowflake {
        position: absolute;
        color: white;
        font-size: 10px;
        opacity: 0;
        animation: snowFloat 3s linear infinite;
        pointer-events: none;
        z-index: 10;
    }
    
    @keyframes snowFloat {
        0% {
            transform: translateY(-10px) rotate(0deg);
            opacity: 0;
        }
        20% {
            opacity: 0.8;
        }
        80% {
            opacity: 0.8;
        }
        100% {
            transform: translateY(40px) rotate(360deg);
            opacity: 0;
        }
    }
    
    /* Make textarea look festive */
    div[data-testid="stTextArea"] textarea {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%) !important;
        border: 2px solid #4CAF50 !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
        padding: 15px !important;
        font-size: 16px !important;
        transition: all 0.3s ease !important;
        background-image: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z' fill='%234CAF50' fill-opacity='0.05' fill-rule='evenodd'/%3E%3C/svg%3E") !important;
    }
    
    div[data-testid="stTextArea"] textarea:focus {
        border-color: #FF6B6B !important;
        box-shadow: 0 0 0 3px rgba(255, 107, 107, 0.2) !important;
        outline: none !important;
    }
    
    div[data-testid="stTextArea"] textarea::placeholder {
        color: #666 !important;
        font-style: italic !important;
    }
    </style>
    
    <div class="snowy-textarea-container">
        <!-- Snowflake elements -->
        <div class="snowflake" style="left: 5%; animation-delay: 0.5s;">❄</div>
        <div class="snowflake" style="left: 30%; animation-delay: 1s;">❄</div>
        <div class="snowflake" style="left: 70%; animation-delay: 0.2s;">❄</div>
        <div class="snowflake" style="left: 90%; animation-delay: 2s;">❆</div>
        <div class="snowflake" style="left: 50%; animation-delay: 1.2s;">❆</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Textarea with snowy effect
    wish_prompt = st.text_area("🎅 What's your wish?",
        placeholder="Example: I wish to learn Spanish fluently in 2026...",
        key="wish_input",
        height=100,
        help="Write your wish starting with 'I wish', 'I hope', or 'I want' for best results!"
    )
    
    # Center the evaluate button
    st.markdown('<div class="center-content">', unsafe_allow_html=True)
    if st.button("🎯 **Evaluate My Wish**", type="primary", use_container_width=True, key="evaluate_wish"):
        if wish_prompt and len(wish_prompt.strip()) > 3:
            # Show evaluation progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate evaluation steps
            for i in range(1, 4):
                if i == 1:
                    status_text.text("🔮 Reading your wish...")
                elif i == 2:
                    status_text.text("🎄 Consulting the Christmas elves...")
                elif i == 3:
                    status_text.text("✨ Calculating probability...")
                
                progress_bar.progress(i * 33)
                time.sleep(0.6)  # Shorter delay
            
            # Evaluate wish
            label, score = evaluate_wish_sentiment(wish_prompt)
            
            if label == 'POSITIVE':
                # Calculate base probability
                base_probability = float(60.0 + (score * 20))
                
                # Generate wish ID and save
                wish_id = generate_wish_id(wish_prompt)
                wish_data = create_or_update_wish(wish_id, wish_prompt, base_probability)
                
                # Update session state
                st.session_state.my_wish_text = wish_prompt
                st.session_state.my_wish_probability = wish_data['current_probability']
                st.session_state.wish_id = wish_id
                st.session_state.show_wish_results = True
                
                # Show success and redirect
                progress_bar.progress(100)
                status_text.text("✅ Wish evaluated successfully!")
                time.sleep(0.8)
                st.rerun()
            else:
                # Show improvement tips with compact spacing
                st.warning("### 🎄 Let's Make This Wish Even Better!")
                st.markdown(f"""
                **Your wish:** "{wish_prompt[:150]}..."
                
                **✨ Improvement Tips:**
                1. **Start with positive words** like "I wish", "I hope", "I want"
                2. **Be specific** about what you want to achieve
                3. **Focus on positive outcomes** you desire
                
                **Example transformation:**
                - Instead of: "I don't want to be stressed"
                - Try: "I wish to find peace, balance, and reduce stress in 2026"
                
                **Try rewriting your wish with a positive focus!**
                """)
        else:
            st.warning("📝 Please write your wish (at least 4 characters)")

# ---------------------------
# Show wish results
# ---------------------------
else:
    # Get latest wish data
    wish_data = get_wish_data(st.session_state.wish_id)
    
    if wish_data:
        # Update with latest probability
        current_prob = float(wish_data.get('current_probability', 0.0))
        st.session_state.my_wish_probability = current_prob
        supporters_count = len(wish_data.get('supporters', []))

        # Display wish probability with compact spacing
        st.markdown(f"""
        <div class="probability-display compact-spacing">
            <h4 style='margin: 5px 0;'>✨ Your Wish Probability</h4>
            <h1 style='font-size: 42px; margin: 10px 0;'>{current_prob:.1f}%</h1>
            <p style='margin: 5px 0; font-size: 16px;'>🎅 {supporters_count} friend{'s have' if supporters_count != 1 else ' has'} shared luck</p>
        </div>
        """, unsafe_allow_html=True)

       # Share section with compact spacing
        st.markdown("---")
        st.markdown("### 📤 **Share with Friends to Boost Your Luck!**")
        st.markdown("<p style='margin: 5px 0;'>The more friends who support your wish, the higher your probability!</p>", unsafe_allow_html=True)
        
        share_link = create_share_link(st.session_state.wish_id, st.session_state.my_wish_text, current_prob)
        
        st.markdown(f'<div class="share-box">{share_link}</div>', unsafe_allow_html=True)
        
        # Action buttons - make Check for Updates button full width
        if st.button("🔄 Check for Updates", type="primary", use_container_width=True):
            st.rerun()
                
    else:
        st.error("❌ Wish data not found. Please create a new wish.")
        if st.button("📝 Make New Wish", type="primary", use_container_width=True, key="error_new_wish"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            st.rerun()

# Footer with compact spacing
st.markdown("---")
st.markdown("""
<div class="footer-compact">
    <p> <i>Hope your wishes come true in 2026! - Yours, Elena</i> </p>
</div>
""", unsafe_allow_html=True)

# Add auto-refresh JavaScript for main page too
if st.session_state.show_wish_results:
    st.components.v1.html("""
    <script>
    // Auto-refresh every 30 seconds on wish results page
    setTimeout(function() {
        window.location.reload();
    }, 30000);
    </script>
    """)
