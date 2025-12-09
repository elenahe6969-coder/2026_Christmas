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
    layout="centered"
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
# Query params handling - FIXED
# ---------------------------
query_params = st.experimental_get_query_params()
shared_wish_id = query_params.get("wish_id", [None])[0]
shared_wish_text = query_params.get("wish", [""])[0]
prob_param = query_params.get("prob", [None])[0]

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
# DEBUG: Show current state
# ---------------------------
# Remove this in production - just for debugging
# st.write(f"Debug - shared_wish_id: {shared_wish_id}")
# st.write(f"Debug - show_wish_results: {st.session_state.show_wish_results}")

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
        last_updated = wish_data.get('last_updated', time.time())
        
        # Store last seen probability for comparison
        if 'last_seen_prob' not in st.session_state:
            st.session_state.last_seen_prob = current_prob
        
        # Check for updates
        if abs(current_prob - st.session_state.last_seen_prob) > 0.01:
            st.markdown(f"""
            <div class="update-notification compact-spacing">
                🎉 **Probability Updated!** 
                From {st.session_state.last_seen_prob:.1f}% to {current_prob:.1f}%
            </div>
            """, unsafe_allow_html=True)
            st.session_state.last_seen_prob = current_prob
        
        # Check if data is stale (older than 30 seconds)
        if time.time() - last_updated > 30 and not st.session_state.show_success_message:
            st.markdown('<div class="stale-warning compact-spacing">⚠️ Data may be stale. Refresh to see latest updates.</div>', unsafe_allow_html=True)
        
        # Display probability (compact)
        st.markdown(f"""
        <div class="probability-display compact-spacing">
            <h3>Current Probability</h3>
            <h1 style='font-size: 56px; margin: 5px 0;'>{current_prob:.1f}%</h1>
            <p style='font-size: 16px;'>🎅 Supported by <b>{supporters_count}</b> friend{'s' if supporters_count != 1 else ''}</p>
            <p style='font-size: 12px; opacity: 0.8;'>Last updated: {datetime.fromtimestamp(last_updated).strftime('%H:%M:%S')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show progress bar
        st.progress(current_prob / 100.0)
        
        # Auto-refresh indicator (compact)
        next_refresh = 15 - (st.session_state.refresh_counter % 3) * 5
        st.markdown(f"""
        <div class="refresh-indicator compact-spacing">
            🔄 Auto-refreshing in {next_refresh}s • Last checked: {datetime.now().strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.error("❌ Wish not found. The link might be invalid or expired.")

    # Support button
    increment = get_random_increment()
    
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown(f"### ✨ Add Your Christmas Luck!")
    
    # Create a unique key for the button
    button_key = f"support_button_{shared_wish_id}"
    
    if st.button(f"🌟 I believe in this wish! (+{increment}%)", 
                 type="primary", 
                 use_container_width=True,
                 key=button_key):
        
        success, new_probability = update_wish_probability(
            shared_wish_id,
            increment,
            st.session_state.supporter_id
        )
        
        if success:
            # Store success data in session state
            st.session_state.show_success_message = True
            st.session_state.success_data = {
                'increment': increment,
                'new_probability': new_probability
            }
            st.session_state.success_timestamp = time.time()
            
            # Update session state
            st.session_state.last_seen_prob = new_probability
            
            # Show balloons
            st.balloons()
            
            # Don't use time.sleep() here - it blocks the UI
            # Instead, immediately rerun to show updated probability and success message
            st.experimental_rerun()
        else:
            st.info("🎅 You've already shared your Christmas luck for this wish. Thank you!")
    
    # Add manual refresh button (compact)
    if st.button("🔄 Refresh Now", key="refresh_now_btn", use_container_width=True):
        # Clear success message on manual refresh
        st.session_state.show_success_message = False
        st.experimental_rerun()
    
    # Make your own wish (compact)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("### 🎄 Make Your Own Wish")
    if st.button("✨ Create My Wish", use_container_width=True, key="create_my_wish_btn"):
        # Clear session states
        st.session_state.show_success_message = False
        st.session_state.success_data = {}
        # Clear query params to go to main page
        st.experimental_set_query_params()
        st.experimental_rerun()
    
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
# Main app: create/evaluate wish - COMPACT LAYOUT
# ---------------------------
# Title at the very top
st.markdown("<h1 style='text-align: center; margin-top: 10px;'>🎄 Christmas Wish 2026</h1>", unsafe_allow_html=True)

if not st.session_state.show_wish_results:
    # Compact header with reduced spacing
    st.markdown("""
    <div style='text-align: center; padding: 5px; margin: 5px 0;'>
        <h3 style='margin: 5px 0; color: #2c3e50;'>✨ Hi there, Merry Christmas!</h3>
        <p style='font-size: 16px; margin: 5px 0; color: #666;'>Tell me your wish for 2026, and I'll help evaluate the probability!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Wish input with reduced spacing
    wish_prompt = st.text_area("**🎅 What's your wish for 2026?**",
        placeholder="Example: I wish to learn Spanish fluently in 2026...",
        key="wish_input",
        height=100,
        help="Write your wish starting with 'I wish', 'I hope', or 'I want' for best results!"
    )

    # Compact expander
    with st.expander("💡 Tips for Magical Wishes", expanded=False):
        st.markdown("""
        **✨ Best ways to start your wish:**
        - "I wish to..."
        - "I hope to..."
        - "I want to..."
        - "My dream is to..."
        - "I would love to..."
        
        **🎯 Examples of great wishes:**
        - I wish to learn Spanish fluently
        - I hope to get a promotion at work
        - My dream is to travel to Japan
        - I want to improve my health and fitness
        
        **🌟 Make it positive and specific for best results!**
        """)

    # Evaluate button with reduced spacing
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎯 **Evaluate My Wish**", type="primary", use_container_width=True):
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
                    time.sleep(0.8)  # Shorter delay
                
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
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    # Show improvement tips (compact)
                    st.warning("### 🎄 Let's Make This Wish Even Better!")
                    st.markdown(f"""
                    **Your wish:** "{wish_prompt[:150]}..."
                    
                    **✨ Improvement Tips:**
                    1. **Start with positive words** like "I wish", "I hope", "I want"
                    2. **Be specific** about what you want to achieve
                    3. **Focus on positive outcomes** you desire
                    
                    **Example:** Instead of "I don't want to be stressed", try "I wish to find peace and balance in 2026"
                    """)
            else:
                st.warning("📝 Please write your wish (at least 4 characters)")

# ---------------------------
# Show wish results - COMPACT LAYOUT
# ---------------------------
else:
    # Get latest wish data
    wish_data = get_wish_data(st.session_state.wish_id)
    
    if wish_data:
        # Update with latest probability
        current_prob = float(wish_data.get('current_probability', 0.0))
        st.session_state.my_wish_probability = current_prob
        supporters_count = len(wish_data.get('supporters', []))

        # Display wish probability (compact)
        st.markdown(f"""
        <div class="probability-display compact-spacing">
            <h2>✨ Your Wish Probability</h2>
            <h1 style='font-size: 56px; margin: 10px 0;'>{current_prob:.1f}%</h1>
            <p style='font-size: 16px;'>🎅 {supporters_count} friend{'s have' if supporters_count != 1 else ' has'} shared luck with you!</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.progress(current_prob / 100.0)

        # Share section (compact)
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("### 📤 **Share with Friends**")
        st.markdown("The more friends who support your wish, the higher your probability!")
        
        share_link = create_share_link(st.session_state.wish_id, st.session_state.my_wish_text, current_prob)
        
        st.markdown(f'<div class="share-box compact-spacing">{share_link}</div>', unsafe_allow_html=True)
        
        # Action buttons (compact)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Check for Updates", use_container_width=True, key="check_updates_btn"):
                st.experimental_rerun()
        
        with col2:
            if st.button("✨ Make New Wish", use_container_width=True, key="new_wish_btn"):
                st.session_state.show_wish_results = False
                st.session_state.my_wish_text = ""
                st.session_state.wish_id = None
                st.experimental_rerun()
                
    else:
        st.error("❌ Wish data not found. Please create a new wish.")
        if st.button("📝 Make New Wish", type="primary", use_container_width=True, key="new_wish_error_btn"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            st.experimental_rerun()

# Compact footer
st.markdown("""
<div style='text-align: center; padding: 5px; color: #666; font-size: 14px; margin-top: 20px;'>
    <p>🎄 <i>Hope your wishes come true in 2026! - Yours, Elena</i> 🎄</p>
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
