import streamlit as st
from transformers import pipeline
import urllib.parse
import time
import random
import json
import os

# ---------------------------
# Compatibility helper
# ---------------------------
def safe_rerun():
    """Try to rerun the Streamlit script in a compatibility-safe way."""
    try:
        # preferred (older + many current versions)
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass

    try:
        # newer API in some versions
        if hasattr(st, "script_request_rerun"):
            st.script_request_rerun()
            return
    except Exception:
        pass

    # final safe fallback: stop current run (session_state persists)
    try:
        st.stop()
    except Exception:
        # If even st.stop() fails (very unlikely), just return
        return

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
if 'support_clicks' not in st.session_state:
    st.session_state.support_clicks = {}
if 'all_wishes' not in st.session_state:
    st.session_state.all_wishes = []
if 'show_wish_results' not in st.session_state:
    st.session_state.show_wish_results = False
if 'supporter_id' not in st.session_state:
    # Keep a stable supporter id per session
    st.session_state.supporter_id = f"supporter_{random.randint(1000, 9999)}_{int(time.time())}"
# flag to force a reload after updates
if 'force_reload' not in st.session_state:
    st.session_state.force_reload = False

# File to store wishes (shared across all users)
WISHES_FILE = "wishes_data.json"

# ---------------------------
# Storage helper functions
# ---------------------------
def load_wishes():
    """Load wishes from file (returns dict)."""
    try:
        if os.path.exists(WISHES_FILE):
            with open(WISHES_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception as e:
        print("load_wishes error:", e)
    return {}

def save_wishes(wishes_data):
    """Save wishes to file (returns True/False)."""
    try:
        with open(WISHES_FILE, 'w') as f:
            json.dump(wishes_data, f, indent=2)
        return True
    except Exception as e:
        print("save_wishes error:", e)
        return False

def get_wish_data(wish_id):
    wishes_data = load_wishes()
    return wishes_data.get(wish_id)

def create_or_update_wish(wish_id, wish_text, initial_probability):
    """Create or update a wish in shared storage and return the wish dict."""
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
            'last_updated': now
        }
    else:
        # Update text & last_updated, keep existing current_probability unless overwritten elsewhere
        wishes_data[wish_id]['wish_text'] = wish_text
        wishes_data[wish_id]['last_updated'] = now

    save_wishes(wishes_data)
    return wishes_data[wish_id]

def update_wish_probability(wish_id, increment, supporter_id):
    """Update wish probability in shared storage (adds supporter if new)."""
    wishes_data = load_wishes()
    if wish_id in wishes_data:
        wish_data = wishes_data[wish_id]
        if 'supporters' not in wish_data:
            wish_data['supporters'] = []
        if supporter_id in wish_data['supporters']:
            return False, wish_data.get('current_probability', 0.0)

        wish_data['supporters'].append(supporter_id)
        new_probability = min(99.9, float(wish_data.get('current_probability', 0.0)) + float(increment))
        wish_data['current_probability'] = float(new_probability)
        wish_data['total_luck_added'] = float(wish_data.get('total_luck_added', 0.0)) + float(increment)
        wish_data['last_updated'] = time.time()
        save_wishes(wishes_data)
        return True, new_probability
    return False, None

# ---------------------------
# Utilities
# ---------------------------
def get_random_increment():
    return round(random.uniform(1.0, 10.0), 1)

def generate_wish_id(wish_text):
    import hashlib
    unique_str = f"{wish_text}_{time.time()}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:10]

def create_share_link(wish_id, wish_text):
    """Create shareable link including current probability from session (if available)."""
    # Put your actual deployed domain here
    base_url = "https://2026christmas-yourwish-mywish-elena.streamlit.app"
    short_wish = wish_text[:80]
    clean_wish = short_wish.replace('\n', ' ').replace('\r', ' ').replace('"', "'").replace('  ', ' ')
    encoded_wish = urllib.parse.quote_plus(clean_wish)

    prob = ""
    try:
        prob_val = float(st.session_state.get('my_wish_probability', 0.0))
        prob = f"&prob={prob_val:.1f}"
    except Exception:
        prob = ""

    full_url = f"{base_url}/?wish_id={wish_id}&wish={encoded_wish}{prob}"
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
        st.session_state.all_wishes.append({
            'text': wish_text[:100],
            'label': result.get('label'),
            'score': result.get('score')
        })
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
    page_title="Christmas Wish 2026",
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
    .positive-wish {
        border-left: 5px solid #28a745;
        padding-left: 15px;
        margin: 10px 0;
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
    .friends-support {
        background-color: #e8f5e8;
        border: 1px solid #c8e6c9;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
    }
    .update-notification {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.8; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Main title
# ---------------------------
st.title("Christmas Wish 2026")

# ---------------------------
# Query params handling
# ---------------------------
query_params = st.query_params
shared_wish_id = query_params.get("wish_id", None)
shared_wish_text = query_params.get("wish", None)
prob_param = query_params.get("prob", None)

# Parse URL-provided probability if present
url_prob = None
if prob_param:
    try:
        cleaned = str(prob_param).strip().rstrip('%').replace(',', '')
        url_prob = max(0.0, min(99.9, float(cleaned)))
    except Exception:
        url_prob = None

# If a forced reload flag is set, clear it (used to force UI to show fresh data)
if st.session_state.get('force_reload', False):
    st.session_state.force_reload = False
    # no-op: clearing the flag is sufficient; subsequent loads will re-read from disk

# ---------------------------
# Shared-wish page (if any)
# ---------------------------
if shared_wish_id:
    # Show shared wish support section
    st.markdown("""
    **Message from your friend:**
    *"Merry Christmas! I just made a wish for 2026. 
    Please click the button below to share your Christmas luck and help make my wish come true!"*
    """)

    # Decode and show the wish text from URL (if provided)
    if shared_wish_text:
        decoded_wish = safe_decode_wish(shared_wish_text)
        if decoded_wish:
            st.markdown(f'<div class="wish-quote">"{decoded_wish}"</div>', unsafe_allow_html=True)

    # Load wish from disk (always re-read from disk here)
    wish_data = get_wish_data(shared_wish_id)

    # If wish exists on disk and URL provided a probability, synchronize if they differ
    if wish_data and url_prob is not None:
        try:
            stored_prob = float(wish_data.get('current_probability', 0.0))
            if abs(stored_prob - url_prob) > 0.05:
                wishes_data = load_wishes()
                if shared_wish_id in wishes_data:
                    wishes_data[shared_wish_id]['current_probability'] = round(url_prob, 1)
                    wishes_data[shared_wish_id]['last_updated'] = time.time()
                    wishes_data[shared_wish_id]['current_probability'] = max(0.0, min(99.9, wishes_data[shared_wish_id]['current_probability']))
                    save_wishes(wishes_data)
                    wish_data = wishes_data.get(shared_wish_id)
        except Exception as e:
            print("sync url_prob -> storage error:", e)

    # If wish not on disk, create it using the URL-provided probability if available
    if not wish_data and shared_wish_text:
        decoded_wish = safe_decode_wish(shared_wish_text)
        if decoded_wish:
            initial_prob = url_prob if url_prob is not None else 60.0
            wish_data = create_or_update_wish(shared_wish_id, decoded_wish, initial_prob)

    # Display current probability if we have wish_data now
    if wish_data:
        current_prob = float(wish_data.get('current_probability', 0.0))
        supporters_count = len(wish_data.get('supporters', []))
        st.markdown(f"""
        <div class="probability-display">
            <h3>Current Probability</h3>
            <h1>{current_prob:.1f}%</h1>
            <p>Supported by {supporters_count} friend{'s' if supporters_count != 1 else ''} 🎄</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("Shared wish not found and no wish text provided in the URL.")

    # Support button
    increment = get_random_increment()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(f"🍀 **Click to Add +{increment}% Christmas Luck**", type="primary", use_container_width=True):
            success, new_probability = update_wish_probability(
                shared_wish_id,
                increment,
                st.session_state.supporter_id
            )
            if success:
                # Immediately reload from disk to get the fresh record
                reloaded = load_wishes().get(shared_wish_id)
                if reloaded:
                    # update session state so main page can use this value if the user navigates back
                    st.session_state.my_wish_probability = reloaded.get('current_probability', st.session_state.my_wish_probability)
                # set a flag to ensure next run uses fresh data
                st.session_state.force_reload = True
                with st.spinner("🎅 Sending your Christmas luck..."):
                    time.sleep(1)
                st.balloons()
                st.success(f"""
                **Thank you for sharing your Christmas luck! 🎄**
                
                *You added +{increment}% to your friend's wish!*
                
                **New probability: {new_probability:.1f}%**
                
                *May your kindness return to you in 2026!*
                """)
                # rerun immediately in a compatibility-safe way
                safe_rerun()
            else:
                st.info("🌟 You've already shared your Christmas luck for this wish! Thank you!")

    # Options for the supporter / link to main app
    st.markdown("---")
    st.markdown("### Your Turn to Make a Wish! 🎄")
    st.markdown("📝 https://2026wisheval-elena-python.streamlit.app/")
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
                        # ensure fresh view on rerun
                        st.session_state.force_reload = True
                        safe_rerun()
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
                    # Fallback to a reasonable probability & continue
                    base_probability = 65.0
                    wish_id = generate_wish_id(wish_prompt)
                    wish_data = create_or_update_wish(wish_id, wish_prompt, base_probability)
                    st.session_state.my_wish_text = wish_prompt
                    st.session_state.my_wish_probability = base_probability
                    st.session_state.wish_id = wish_id
                    st.session_state.show_wish_results = True
                    st.session_state.force_reload = True
                    safe_rerun()
        else:
            st.warning("📝 Please write your wish (at least 4 characters)")

# ---------------------------
# Show wish results
# ---------------------------
else:
    # Reload latest from disk for freshest values
    wish_data = load_wishes().get(st.session_state.wish_id)
    if wish_data:
        # update session-state with freshest probability
        st.session_state.my_wish_probability = wish_data.get('current_probability', st.session_state.my_wish_probability)
        current_prob = float(st.session_state.my_wish_probability)
        supporters_count = len(wish_data.get('supporters', []))

        st.markdown(f"""
        <div class="probability-display">
            <h3>Your Wish Probability</h3>
            <h1>{current_prob:.1f}%</h1>
            <p>{supporters_count} friend{'s have' if supporters_count != 1 else ' has'} shared luck</p>
        </div>
        """, unsafe_allow_html=True)

        # Share section
        st.markdown("---")
        st.markdown("### 📤 Share with friends to get more Christmas luck!")
        share_link = create_share_link(st.session_state.wish_id, st.session_state.my_wish_text)
        st.markdown(f'<div class="share-box">{share_link}</div>', unsafe_allow_html=True)

        if st.button("🔄 Fetch latest probability"):
            # Force reload from disk and refresh UI
            reloaded = load_wishes().get(st.session_state.wish_id)
            if reloaded:
                st.session_state.my_wish_probability = reloaded.get('current_probability', st.session_state.my_wish_probability)
            st.session_state.force_reload = True
            safe_rerun()
    else:
        st.error("Wish data not found. Please make a new wish.")
        if st.button("📝 Make New Wish", type="primary"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            safe_rerun()

# Footer
st.markdown("---")
st.markdown("Hope you will have fun with this app! - Yours, Elena")
