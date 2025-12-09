import streamlit as st
from transformers import pipeline
import urllib.parse
import time
import random
import json
import os

# Initialize session state
if 'supported_wishes' not in st.session_state:
    st.session_state.supported_wishes = {}
if 'my_wish_probability' not in st.session_state:
    st.session_state.my_wish_probability = 0
if 'my_wish_text' not in st.session_state:
    st.session_state.my_wish_text = ""
if 'wish_id' not in st.session_state:
    st.session_state.wish_id = None
if 'support_clicks' not in st.session_state:
    st.session_state.support_clicks = {}
if 'all_wishes' not in st.session_state:
    st.session_state.all_wishes = []
if 'show_wish_results' not in st.session_state:
    st.session_state.show_wish_results = False  # Track if we should show results

# File to store wishes (shared across all users)
WISHES_FILE = "wishes_data.json"

# Functions to manage shared wish data
def load_wishes():
    """Load wishes from file"""
    try:
        if os.path.exists(WISHES_FILE):
            with open(WISHES_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        # Print server-side error for debugging (won't show to users)
        print("load_wishes error:", e)
    return {}

def save_wishes(wishes_data):
    """Save wishes to file"""
    try:
        with open(WISHES_FILE, 'w') as f:
            json.dump(wishes_data, f)
        return True
    except Exception as e:
        print("save_wishes error:", e)
        return False

def update_wish_probability(wish_id, increment, supporter_id):
    """Update wish probability in shared storage"""
    wishes_data = load_wishes()
    
    if wish_id in wishes_data:
        wish_data = wishes_data[wish_id]
        
        # Check if supporter already supported
        if 'supporters' not in wish_data:
            wish_data['supporters'] = []
        
        if supporter_id in wish_data['supporters']:
            return False, wish_data['current_probability']
        
        # Add supporter
        wish_data['supporters'].append(supporter_id)
        
        # Update probability (max 99.9%)
        new_probability = min(99.9, wish_data['current_probability'] + increment)
        wish_data['current_probability'] = new_probability
        
        if 'total_luck_added' not in wish_data:
            wish_data['total_luck_added'] = 0
        wish_data['total_luck_added'] += increment
        
        wish_data['last_updated'] = time.time()
        
        # Save back to file
        save_wishes(wishes_data)
        return True, new_probability
    
    return False, None

def get_wish_data(wish_id):
    """Get wish data from shared storage"""
    wishes_data = load_wishes()
    return wishes_data.get(wish_id)

def create_or_update_wish(wish_id, wish_text, initial_probability):
    """Create or update a wish in shared storage"""
    wishes_data = load_wishes()
    
    if wish_id not in wishes_data:
        wishes_data[wish_id] = {
            'wish_text': wish_text,
            'initial_probability': initial_probability,
            'current_probability': initial_probability,
            'supporters': [],
            'total_luck_added': 0,
            'created_at': time.time(),
            'last_updated': time.time()
        }
    else:
        # Update existing wish
        wishes_data[wish_id]['wish_text'] = wish_text
        wishes_data[wish_id]['last_updated'] = time.time()
    
    save_wishes(wishes_data)
    return wishes_data[wish_id]

st.set_page_config(
    page_title="🎄 Christmas Wish 2026",
    page_icon="🎄",
    layout="centered"
)

# Custom CSS
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

# Helper functions
def get_random_increment():
    return round(random.uniform(1.0, 10.0), 1)

def generate_wish_id(wish_text):
    import hashlib
    unique_str = f"{wish_text}_{time.time()}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:10]

def create_share_link(wish_id, wish_text):
    """Create a shareable link"""
    try:
        base_url = "https://2026christmas-yourwish-mywish-elena."
    except:
        base_url = "http://localhost:8501"
    
    # Use a shorter version of the wish for URL
    short_wish = wish_text[:80]
    clean_wish = short_wish.replace('\n', ' ').replace('\r', ' ').replace('"', "'").replace('  ', ' ')
    encoded_wish = urllib.parse.quote_plus(clean_wish)
    
    full_url = f"{base_url}/?wish_id={wish_id}&wish={encoded_wish}"
    return full_url.strip()

def safe_decode_wish(encoded_wish):
    """Safely decode wish text"""
    try:
        decoded = urllib.parse.unquote_plus(encoded_wish)
        decoded = decoded.replace('+', ' ')
        return decoded
    except:
        try:
            decoded = urllib.parse.unquote(encoded_wish)
            return decoded
        except:
            return encoded_wish

def evaluate_wish_sentiment(wish_text):
    """Custom function to evaluate wish sentiment"""
    try:
        pipe = pipeline("sentiment-analysis")
        result = pipe(wish_text[:512])[0]
        
        st.session_state.all_wishes.append({
            'text': wish_text[:100],
            'label': result['label'],
            'score': result['score']
        })
        
        has_wish_keyword = any(keyword in wish_text.lower() for keyword in ['wish', 'hope', 'want', 'dream'])
        
        if result['label'] == 'POSITIVE' and result['score'] > 0.6:
            return 'POSITIVE', result['score']
        elif has_wish_keyword:
            return 'POSITIVE', max(result['score'], 0.7)
        else:
            return result['label'], result['score']
            
    except Exception as e:
        print(f"Model error: {e}")
        return 'POSITIVE', 0.7


# Main title at the TOP (always visible)
st.title("Christmas Wish 2026")

# Check for shared wish
query_params = st.query_params
shared_wish_id = query_params.get("wish_id", [None])[0]
shared_wish_text = query_params.get("wish", [None])[0]

# If viewing a shared wish, show support page FIRST
if shared_wish_id:
    # Generate unique supporter ID for this user
    if 'supporter_id' not in st.session_state:
        st.session_state.supporter_id = f"supporter_{random.randint(1000, 9999)}_{int(time.time())}"
    
    # Show shared wish support section
    st.markdown("""
    **Message from your friend:**
    *"Merry Christmas! I just made a wish for 2026. 
    Please click the button below to share your Christmas luck and help make my wish come true!"*
    """)
    
    # Decode and show the wish
    if shared_wish_text:
        decoded_wish = safe_decode_wish(shared_wish_text)
        if decoded_wish and decoded_wish != shared_wish_text:
            st.markdown(f'<div class="wish-quote">"{decoded_wish}"</div>', unsafe_allow_html=True)
    
    # Get current wish data FROM SHARED STORAGE
    wish_data = get_wish_data(shared_wish_id)
    
    # If wish doesn't exist in storage, create it from the URL data
    if not wish_data and shared_wish_text:
        # Create a temporary wish from the URL data
        decoded_wish = safe_decode_wish(shared_wish_text)
        if decoded_wish:
            # Use a default probability for shared wishes
            wish_data = create_or_update_wish(shared_wish_id, decoded_wish, 60.0)
    
    # Show current probability
    if wish_data:
        current_prob = wish_data['current_probability']
        supporters_count = len(wish_data.get('supporters', []))
        
        st.markdown(f"""
        <div class="probability-display">
            <h3>Current Probability</h3>
            <h1>{current_prob:.1f}%</h1>
            <p>Supported by {supporters_count} friend{'s' if supporters_count != 1 else ''} 🎄</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Generate random increment
    increment = get_random_increment()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(f"🍀 **Click to Add +{increment}% Christmas Luck**", type="primary", use_container_width=True):
            # Add support and get updated probability FROM SHARED STORAGE
            success, new_probability = update_wish_probability(
                shared_wish_id, 
                increment,
                st.session_state.supporter_id
            )
            
            if success:
                with st.spinner("🎅 Sending your Christmas luck..."):
                    time.sleep(1)
                
                st.balloons()
                st.success(f"""
                **Thank you for sharing your Christmas luck! 🎄**
                
                *You added +{increment}% to your friend's wish!*
                
                **New probability: {new_probability:.1f}%**
                
                *May your kindness return to you in 2026!*
                """)
                
                # Update the display immediately: reload from disk and update session state, then rerun
                reloaded = load_wishes().get(shared_wish_id)
                if reloaded:
                    st.session_state.my_wish_probability = reloaded.get('current_probability', st.session_state.my_wish_probability)
                st.rerun()
            else:
                st.info("🌟 You've already shared your Christmas luck for this wish! Thank you!")
    
    # Options for the supporter
    st.markdown("---")
    # Show appropriate greeting based on whether viewing a shared wish
    st.markdown("### Your Turn to Make a Wish! 🎄")
    st.markdown("📝 https://2026wisheval-elena-python.streamlit.app/")
    # Don't show the regular wish input when supporting
    st.stop()

# Main app logic - Show wish input OR results
if not st.session_state.show_wish_results:
    # Show wish input form
    st.markdown("### Hi there, Merry Christmas! 🎄")
    
    wish_prompt = st.text_area(
        "🎅 Tell me your wish for 2026, and I'll assess how likely it is to come true:",
        placeholder="E.g., I wish to learn a new language in 2026...",
        key="wish_input",
        height=100
    )
    
    # Add tips for better wishes
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
                        base_probability = 60.0 + (score * 20)
                        
                        # Generate wish ID
                        wish_id = generate_wish_id(wish_prompt)
                        
                        # Save wish to SHARED STORAGE
                        wish_data = create_or_update_wish(wish_id, wish_prompt, base_probability)
                        
                        # Save to session state
                        st.session_state.my_wish_text = wish_prompt
                        st.session_state.my_wish_probability = wish_data['current_probability']
                        st.session_state.wish_id = wish_id
                        st.session_state.show_wish_results = True
                        
                        # Rerun to show results
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
                    st.error(f"⚠️ Technical issue: {str(e)[:100]}")
                    # Fallback
                    base_probability = 65.0
                    wish_id = generate_wish_id(wish_prompt)
                    
                    # Save wish to SHARED STORAGE
                    wish_data = create_or_update_wish(wish_id, wish_prompt, base_probability)
                    
                    # Save to session state
                    st.session_state.my_wish_text = wish_prompt
                    st.session_state.my_wish_probability = base_probability
                    st.session_state.wish_id = wish_id
                    st.session_state.show_wish_results = True
                    
                    # Rerun to show results
                    st.rerun()
        else:
            st.warning("📝 Please write your wish (at least 4 characters)")

# Show wish results (when show_wish_results is True)
else:
    # ALWAYS reload latest from disk to show freshest values
    wish_data = load_wishes().get(st.session_state.wish_id)
    
    if wish_data:
        # Sync latest current_probability into session state so UI shows fresh value
        st.session_state.my_wish_probability = wish_data.get('current_probability', st.session_state.my_wish_probability)
        current_prob = st.session_state.my_wish_probability
        supporters_count = len(wish_data.get('supporters', []))
        
        # Display probability (from session_state which was just updated from disk)
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
        
        # Display the link
        st.markdown(f'<div class="share-box">{share_link}</div>', unsafe_allow_html=True)
        
        # Add a refresh button to explicitly fetch latest from disk
        if st.button("🔄 Fetch latest probability"):
            reloaded = load_wishes().get(st.session_state.wish_id)
            if reloaded:
                st.session_state.my_wish_probability = reloaded.get('current_probability', st.session_state.my_wish_probability)
            # use correct API to rerun
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
st.markdown("Hope you will have fun with this app! - Yours, Elena")
