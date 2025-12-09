import streamlit as st
from transformers import pipeline
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
if 'force_reload_flag' not in st.session_state:
    st.session_state.force_reload_flag = False

# File to store wishes (shared across all users)
WISHES_FILE = "wishes_data.json"
WISHES_LOCK_FILE = "wishes_data.json.lock"

# ---------------------------
# Enhanced storage helper functions with locking
# ---------------------------
def load_wishes_with_lock():
    """Load wishes from file with file locking."""
    import fcntl
    try:
        if os.path.exists(WISHES_FILE):
            with open(WISHES_FILE, 'r') as f:
                # Try to acquire a shared lock
                try:
                    fcntl.flock(f, fcntl.LOCK_SH)
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"load_wishes_with_lock error: {e}")
        # Fallback to regular load
        if os.path.exists(WISHES_FILE):
            with open(WISHES_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    return {}

def save_wishes_with_lock(wishes_data):
    """Save wishes to file with file locking."""
    import fcntl
    try:
        with open(WISHES_FILE, 'w') as f:
            # Try to acquire an exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(wishes_data, f, indent=2)
                return True
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"save_wishes_with_lock error: {e}")
        # Fallback to regular save
        with open(WISHES_FILE, 'w') as f:
            json.dump(wishes_data, f, indent=2)
        return True
    return False

def get_wish_data(wish_id):
    """Get wish data with automatic refresh."""
    # Force refresh every 5 seconds or if reload flag is set
    current_time = time.time()
    force_refresh = st.session_state.get('force_reload_flag', False)
    
    if force_refresh or (current_time - st.session_state.last_refresh_time > 5):
        st.session_state.last_refresh_time = current_time
        st.session_state.refresh_counter += 1
        st.session_state.force_reload_flag = False
        
        # Clear cache to force fresh load
        if 'wishes_cache' in st.session_state:
            del st.session_state.wishes_cache
    
    # Use caching to avoid repeated file reads
    if 'wishes_cache' not in st.session_state:
        st.session_state.wishes_cache = load_wishes_with_lock()
    
    return st.session_state.wishes_cache.get(wish_id)

def create_or_update_wish(wish_id, wish_text, initial_probability):
    """Create or update a wish in shared storage."""
    wishes_data = load_wishes_with_lock()
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
        # Update if needed
        wishes_data[wish_id]['wish_text'] = wish_text
        wishes_data[wish_id]['last_updated'] = now
        wishes_data[wish_id]['version'] = wishes_data[wish_id].get('version', 0) + 1
    
    save_wishes_with_lock(wishes_data)
    
    # Update cache
    if 'wishes_cache' in st.session_state:
        st.session_state.wishes_cache = wishes_data
    
    return wishes_data[wish_id]

def update_wish_probability(wish_id, increment, supporter_id):
    """Update wish probability in shared storage."""
    wishes_data = load_wishes_with_lock()
    
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
        
        # Save and update cache
        save_wishes_with_lock(wishes_data)
        if 'wishes_cache' in st.session_state:
            st.session_state.wishes_cache = wishes_data
        
        # Set force reload flag for all sessions
        st.session_state.force_reload_flag = True
        
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
    """Evaluate sentiment using transformers sentiment-analysis pipeline."""
    try:
        pipe = pipeline("sentiment-analysis")
        result = pipe(wish_text[:512])[0]
        
        has_wish_keyword = any(keyword in wish_text.lower() for keyword in ['wish', 'hope', 'want', 'dream'])
        if result.get('label') == 'POSITIVE' and result.get('score', 0.0) > 0.6:
            return 'POSITIVE', result.get('score', 0.0)
        elif has_wish_keyword:
            return 'POSITIVE', max(result.get('score', 0.0), 0.7)
        else:
            return result.get('label'), result.get('score', 0.0)
    except Exception as e:
        print(f"Model error: {e}")
        return 'POSITIVE', 0.7

# ---------------------------
# Page config & CSS
# ---------------------------
st.set_page_config(
    page_title="🎄 Christmas Wish 2026",
    page_icon="🎄",
    layout="centered"
)

st.markdown("""
<style>
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: bold;
    }
    .share-box {
        background-color: #f0f2f6;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        font-family: monospace;
        word-break: break-all;
    }
    .wish-quote {
        font-style: italic;
        font-size: 18px;
        color: #333;
        margin: 20px 0;
        padding: 15px;
        background-color: #f9f9f9;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
    }
    .probability-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .update-notification {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        animation: fadeIn 0.5s;
    }
    .refresh-indicator {
        background-color: #e3f2fd;
        border: 1px solid #bbdefb;
        border-radius: 8px;
        padding: 8px;
        margin: 10px 0;
        font-size: 12px;
        text-align: center;
        color: #1976d2;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Auto-refresh mechanism
# ---------------------------
def setup_auto_refresh():
    """Set up auto-refresh using Streamlit's experimental features."""
    current_time = time.time()
    
    # Create a refresh trigger based on time
    if 'auto_refresh_last' not in st.session_state:
        st.session_state.auto_refresh_last = current_time
    
    # Check if 5 seconds have passed
    if current_time - st.session_state.auto_refresh_last > 5:
        st.session_state.auto_refresh_last = current_time
        
        # Force a rerun to refresh data
        if st.session_state.get('force_reload_flag', False):
            st.session_state.force_reload_flag = False
            st.rerun()
        
        # Also rerun every 15 seconds to check for updates
        if current_time - st.session_state.get('last_full_refresh', 0) > 15:
            st.session_state.last_full_refresh = current_time
            st.rerun()

# ---------------------------
# Main title
# ---------------------------
st.title("🎄 Christmas Wish 2026")

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

# Setup auto-refresh
setup_auto_refresh()

# ---------------------------
# Shared-wish page (if any)
# ---------------------------
if shared_wish_id:
    # Show refresh indicator
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 3])
        with col2:
            refresh_btn = st.button("🔄", help="Refresh page")
            if refresh_btn:
                st.session_state.force_reload_flag = True
                st.rerun()
    
    # Show shared wish support section
    st.markdown("""
    **Message from your friend:**
    *"Merry Christmas! I just made a wish for 2026. 
    Please click the button below to share your Christmas luck and help make my wish come true!"*
    """)

    # Decode wish text
    decoded_wish = ""
    if shared_wish_text:
        decoded_wish = safe_decode_wish(shared_wish_text)
        if decoded_wish:
            st.markdown(f'<div class="wish-quote">"{decoded_wish}"</div>', unsafe_allow_html=True)

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
                📈 **Update!** Probability increased from {st.session_state.last_seen_prob:.1f}% to {current_prob:.1f}%
            </div>
            """, unsafe_allow_html=True)
            st.session_state.last_seen_prob = current_prob
        
        # Display probability with visual progress
        st.markdown(f"""
        <div class="probability-display">
            <h3>Current Wish Probability</h3>
            <h1>{current_prob:.1f}%</h1>
            <p>🎅 Supported by {supporters_count} friend{'s' if supporters_count != 1 else ''}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show progress bar
        st.progress(current_prob / 100.0)
        
        # Auto-refresh indicator
        st.markdown(f"""
        <div class="refresh-indicator">
            🔄 Auto-refreshing • Last checked: {datetime.now().strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.error("Wish not found. The link might be invalid.")

    # Support button
    increment = get_random_increment()
    
    st.markdown("---")
    st.markdown(f"### Add Your Christmas Luck! 🍀")
    st.markdown(f"*Click below to add **+{increment}%** to this wish*")
    
    if st.button(f"🌟 I believe in this wish too! (+{increment}%)", type="primary", use_container_width=True):
        success, new_probability = update_wish_probability(
            shared_wish_id,
            increment,
            st.session_state.supporter_id
        )
        
        if success:
            # Immediate visual feedback
            with st.spinner("✨ Adding your Christmas luck..."):
                time.sleep(1)
            
            st.balloons()
            st.success(f"""
            🎄 **Thank you!** You added **+{increment}%** Christmas luck!
            
            **New Probability: {new_probability:.1f}%**
            
            *Your kindness will return to you in 2026!*
            """)
            
            # Force immediate refresh
            st.session_state.force_reload_flag = True
            st.session_state.last_seen_prob = new_probability
            
            # Auto-refresh after 2 seconds
            time.sleep(2)
            st.rerun()
        else:
            st.info("You've already shared your Christmas luck for this wish. Thank you! 🎅")

    # Additional refresh button
    st.markdown("---")
    if st.button("🔄 Refresh Page to See Latest Updates", use_container_width=True):
        st.session_state.force_reload_flag = True
        st.rerun()

    # Make your own wish
    st.markdown("---")
    st.markdown("### ✨ Make Your Own Wish!")
    st.markdown("Create your own Christmas wish and share it with friends!")
    if st.button("🎄 Make My Wish", use_container_width=True):
        # Clear query params to go to main page
        st.query_params.clear()
        st.rerun()
    
    st.stop()

# ---------------------------
# Main app: create/evaluate wish
# ---------------------------
if not st.session_state.show_wish_results:
    st.markdown("### Hi there, Merry Christmas! 🎄")
    wish_prompt = st.text_area(
        "🎅 Tell me your wish for 2026, and I'll assess how likely it is to come true:",
        placeholder="E.g., I wish to learn a new language in 2026...",
        key="wish_input",
        height=100
    )

    with st.expander("💡 Tips for better wishes"):
        st.markdown("""
        **Start your wish with:**
        - I wish to...
        - I hope to...
        - I want to...
        - My dream is to...
        - I would love to...
        
        **Examples of good wishes:**
        - I wish to learn Spanish in 2026
        - I hope to get a promotion at work
        - My dream is to travel around the world
        - I want to improve my health
        """)

    if st.button("🎯 Evaluate My Wish", type="primary"):
        if wish_prompt and len(wish_prompt.strip()) > 3:
            with st.spinner("🔮 The magic elves are evaluating your wish..."):
                time.sleep(1.5)
                try:
                    label, score = evaluate_wish_sentiment(wish_prompt)
                    if label == 'POSITIVE':
                        base_probability = float(60.0 + (score * 20))
                        wish_id = generate_wish_id(wish_prompt)
                        wish_data = create_or_update_wish(wish_id, wish_prompt, base_probability)
                        st.session_state.my_wish_text = wish_prompt
                        st.session_state.my_wish_probability = wish_data['current_probability']
                        st.session_state.wish_id = wish_id
                        st.session_state.show_wish_results = True
                        st.rerun()
                    else:
                        st.warning("### 🎄 Let's Make This Wish Even Better!")
                        st.markdown(f"""
                        **Your wish:** "{wish_prompt[:150]}..."
                        
                        **Tips to improve:**
                        1. **Start with positive words** like "I wish", "I hope", "I want"
                        2. **Be specific** about what you want
                        3. **Focus on positive outcomes**
                        
                        **Example:** Instead of "I don't want to be stressed", try "I wish to find peace and balance in 2026"
                        """)
                except Exception as e:
                    st.error(f"⚠️ Technical issue: {str(e)[:200]}")
                    # Fallback
                    base_probability = 65.0
                    wish_id = generate_wish_id(wish_prompt)
                    wish_data = create_or_update_wish(wish_id, wish_prompt, base_probability)
                    st.session_state.my_wish_text = wish_prompt
                    st.session_state.my_wish_probability = base_probability
                    st.session_state.wish_id = wish_id
                    st.session_state.show_wish_results = True
                    st.rerun()
        else:
            st.warning("📝 Please write your wish (at least 4 characters)")

# ---------------------------
# Show wish results
# ---------------------------
else:
    # Get latest wish data
    wish_data = get_wish_data(st.session_state.wish_id)
    
    if wish_data:
        # Update session state with latest probability
        current_prob = float(wish_data.get('current_probability', 0.0))
        st.session_state.my_wish_probability = current_prob
        supporters_count = len(wish_data.get('supporters', []))

        st.markdown(f"""
        <div class="probability-display">
            <h3>Your Wish Probability</h3>
            <h1>{current_prob:.1f}%</h1>
            <p>🎅 {supporters_count} friend{'s have' if supporters_count != 1 else ' has'} shared luck</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.progress(current_prob / 100.0)

        # Share section
        st.markdown("---")
        st.markdown("### 📤 Share with friends to get more Christmas luck!")
        share_link = create_share_link(st.session_state.wish_id, st.session_state.my_wish_text, current_prob)
        st.markdown(f'<div class="share-box">{share_link}</div>', unsafe_allow_html=True)
        
        # Copy button
        st.code(share_link, language="text")
        
        # Refresh button
        if st.button("🔄 Check for Updates", key="check_updates"):
            st.session_state.force_reload_flag = True
            st.rerun()
        
        # Make new wish button
        if st.button("✨ Make Another Wish", key="new_wish"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            st.rerun()
            
    else:
        st.error("Wish data not found. Please make a new wish.")
        if st.button("📝 Make New Wish", type="primary"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            st.rerun()

# Footer
st.markdown("---")
st.markdown("🎄 *Hope you will have fun with this app! - Yours, Elena* 🎄")

# Auto-refresh script using JavaScript
st.components.v1.html("""
<script>
// Auto-refresh every 10 seconds
setTimeout(function() {
    window.location.reload();
}, 10000);

// Also refresh when page becomes visible again
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        setTimeout(function() {
            window.location.reload();
        }, 1000);
    }
});
</script>
""")
