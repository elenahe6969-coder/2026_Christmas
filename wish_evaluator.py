import streamlit as st
import urllib.parse
import time
import random
import json
import os
import hashlib
from datetime import datetime

# ==================== SIMPLE SENTIMENT ANALYSIS ====================
def simple_sentiment_analysis(wish_text):
    """Super simple sentiment analysis without any external dependencies"""
    text = wish_text.lower()
    
    # Check for positive starters
    positive_starters = ['i wish', 'i hope', 'i want', 'i dream', 'i would love']
    for starter in positive_starters:
        if starter in text:
            return 'POSITIVE', 0.8
    
    # Check for negative words
    negative_words = ['not', "don't", "won't", "can't", "never", "no"]
    for word in negative_words:
        if f" {word} " in f" {text} ":
            return 'NEGATIVE', 0.3
    
    # Default to positive
    return 'POSITIVE', 0.7

# ==================== SESSION STATE ====================
if 'my_wish_probability' not in st.session_state:
    st.session_state.my_wish_probability = 0.0
if 'my_wish_text' not in st.session_state:
    st.session_state.my_wish_text = ""
if 'wish_id' not in st.session_state:
    st.session_state.wish_id = None
if 'show_wish_results' not in st.session_state:
    st.session_state.show_wish_results = False
if 'supporter_id' not in st.session_state:
    st.session_state.supporter_id = f"user_{random.randint(1000, 9999)}"
if 'last_update_check' not in st.session_state:
    st.session_state.last_update_check = time.time()

# ==================== DATA STORAGE ====================
WISHES_FILE = "wishes_data.json"

def load_wishes():
    """Load wishes from JSON file"""
    try:
        if os.path.exists(WISHES_FILE):
            with open(WISHES_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except:
        pass
    return {}

def save_wishes(data):
    """Save wishes to JSON file"""
    try:
        with open(WISHES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

def get_wish(wish_id):
    """Get a specific wish by ID"""
    wishes = load_wishes()
    return wishes.get(wish_id)

def update_wish_probability_in_file(wish_id, increment, supporter_id):
    """Update probability in the shared file"""
    wishes = load_wishes()
    
    if wish_id not in wishes:
        return False, 0.0
    
    wish = wishes[wish_id]
    
    # Check if user already supported
    if 'supporters' not in wish:
        wish['supporters'] = []
    
    if supporter_id in wish['supporters']:
        return False, wish.get('current_probability', 0.0)
    
    # Add supporter
    wish['supporters'].append(supporter_id)
    
    # Update probability
    current = wish.get('current_probability', 0.0)
    new_prob = min(99.9, current + increment)
    wish['current_probability'] = new_prob
    wish['last_updated'] = time.time()
    
    # Save
    save_wishes(wishes)
    
    return True, new_prob

def create_wish(wish_id, wish_text, initial_prob):
    """Create a new wish"""
    wishes = load_wishes()
    
    wishes[wish_id] = {
        'text': wish_text,
        'current_probability': initial_prob,
        'initial_probability': initial_prob,
        'supporters': [],
        'created_at': time.time(),
        'last_updated': time.time()
    }
    
    save_wishes(wishes)
    return wishes[wish_id]

# ==================== STREAMLIT APP ====================
st.set_page_config(
    page_title="🎄 Christmas Wish 2026",
    page_icon="🎄",
    layout="centered"
)

# Add CSS for better styling
st.markdown("""
<style>
    .probability-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .wish-text {
        font-style: italic;
        font-size: 18px;
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        margin: 15px 0;
    }
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        border: none;
        padding: 12px 24px;
        margin: 5px;
    }
    .update-alert {
        background-color: #d4edda;
        color: #155724;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 10px 0;
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== MAIN APP LOGIC ====================
st.title("🎄 Christmas Wish 2026")

# Get query parameters
query_params = st.experimental_get_query_params()
shared_wish_id = query_params.get("wish_id", [None])[0]
shared_wish_text = query_params.get("wish", [""])[0]
shared_prob = query_params.get("prob", [None])[0]

# ==================== SUPPORT PAGE ====================
if shared_wish_id:
    # Decode wish text
    if shared_wish_text:
        try:
            decoded_wish = urllib.parse.unquote_plus(shared_wish_text)
        except:
            decoded_wish = shared_wish_text
    else:
        decoded_wish = "A Christmas wish for 2026!"
    
    # Get current probability from URL or file
    current_prob = 60.0
    if shared_prob:
        try:
            current_prob = float(shared_prob)
        except:
            current_prob = 60.0
    
    # Load wish from file
    wish_data = get_wish(shared_wish_id)
    
    if wish_data:
        current_prob = wish_data.get('current_probability', current_prob)
        supporters = len(wish_data.get('supporters', []))
    else:
        # Create wish if it doesn't exist
        wish_data = create_wish(shared_wish_id, decoded_wish, current_prob)
        supporters = 0
    
    # Display the wish
    st.markdown(f'<div class="wish-text">"{decoded_wish}"</div>', unsafe_allow_html=True)
    
    # Display current probability
    st.markdown(f"""
    <div class="probability-box">
        <h3>Current Probability</h3>
        <h1 style="font-size: 64px; margin: 10px 0;">{current_prob:.1f}%</h1>
        <p>🎅 Supported by {supporters} friend{'s' if supporters != 1 else ''}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate random increment
    increment = round(random.uniform(1.0, 5.0), 1)
    
    # Support button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(f"🎄 Add +{increment}% Christmas Luck", use_container_width=True):
            success, new_prob = update_wish_probability_in_file(
                shared_wish_id, 
                increment, 
                st.session_state.supporter_id
            )
            
            if success:
                st.balloons()
                st.success(f"✨ Thank you! You added +{increment}% luck!")
                st.info(f"New probability: **{new_prob:.1f}%**")
                
                # Force refresh after 2 seconds
                time.sleep(2)
                st.experimental_rerun()
            else:
                st.info("You've already supported this wish. Thank you! 🎅")
    
    # Refresh button
    if st.button("🔄 Refresh Page", key="refresh_btn"):
        st.experimental_rerun()
    
    # Auto-refresh every 10 seconds using JavaScript
    st.markdown(f"""
    <script>
    setTimeout(function() {{
        window.location.reload();
    }}, 10000);
    </script>
    <div style='text-align: center; color: #666; font-size: 12px; margin-top: 20px;'>
        Page auto-refreshes every 10 seconds
    </div>
    """, unsafe_allow_html=True)
    
    # Link to create own wish
    st.markdown("---")
    st.markdown("### Make Your Own Wish!")
    if st.button("✨ Create My Wish", key="create_wish_from_shared"):
        st.experimental_set_query_params()
        st.experimental_rerun()
    
    st.stop()

# ==================== MAIN WISH CREATION PAGE ====================
if not st.session_state.show_wish_results:
    st.markdown("### Create Your Christmas Wish 🎅")
    
    wish_input = st.text_area(
        "What's your wish for 2026?",
        placeholder="Example: I wish to learn a new language...",
        height=100
    )
    
    if st.button("🎯 Evaluate My Wish", type="primary"):
        if wish_input and len(wish_input.strip()) > 3:
            with st.spinner("✨ Analyzing your wish..."):
                time.sleep(1)
                
                # Simple sentiment analysis
                label, score = simple_sentiment_analysis(wish_input)
                
                if label == 'POSITIVE':
                    # Generate wish ID
                    wish_id = hashlib.md5(f"{wish_input}_{time.time()}".encode()).hexdigest()[:10]
                    
                    # Calculate initial probability
                    base_prob = 60 + (score * 20)
                    
                    # Create wish
                    wish_data = create_wish(wish_id, wish_input, base_prob)
                    
                    # Store in session
                    st.session_state.my_wish_text = wish_input
                    st.session_state.my_wish_probability = base_prob
                    st.session_state.wish_id = wish_id
                    st.session_state.show_wish_results = True
                    
                    st.experimental_rerun()
                else:
                    st.warning("Try starting your wish with 'I wish', 'I hope', or 'I want' for better results!")
        else:
            st.warning("Please enter a wish (at least 4 characters)")

# ==================== WISH RESULTS PAGE ====================
else:
    # Get current wish data
    wish_data = get_wish(st.session_state.wish_id)
    
    if wish_data:
        current_prob = wish_data.get('current_probability', st.session_state.my_wish_probability)
        supporters = len(wish_data.get('supporters', []))
        
        st.markdown(f"""
        <div class="probability-box">
            <h3>Your Wish Probability</h3>
            <h1 style="font-size: 64px; margin: 10px 0;">{current_prob:.1f}%</h1>
            <p>🎅 {supporters} friend{'s have' if supporters != 1 else ' has'} supported you</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f'<div class="wish-text">"{st.session_state.my_wish_text}"</div>', unsafe_allow_html=True)
        
        # Create shareable link
        encoded_wish = urllib.parse.quote_plus(st.session_state.my_wish_text[:100])
        share_url = f"https://2026christmas-yourwish-mywish-elena.streamlit.app/?wish_id={st.session_state.wish_id}&wish={encoded_wish}&prob={current_prob:.1f}"
        
        st.markdown("### 📤 Share with Friends")
        st.code(share_url, language="text")
        
        # Refresh button
        if st.button("🔄 Check for Updates"):
            st.experimental_rerun()
        
        # New wish button
        if st.button("✨ Make New Wish"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            st.experimental_rerun()
    
    else:
        st.error("Wish not found. Please create a new one.")
        if st.button("📝 Create New Wish"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("*Made with ❤️ for Christmas 2026*")
