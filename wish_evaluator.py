import streamlit as st
from transformers import pipeline
import urllib.parse
import time
import random
import json
import os
import hashlib

# --------------------------
# Initialize session state
# --------------------------
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
if 'supporter_id' not in st.session_state:
    st.session_state.supporter_id = f"supporter_{random.randint(1000, 9999)}_{int(time.time())}"

# --------------------------
# File to store wishes
# --------------------------
WISHES_FILE = "wishes_data.json"

# --------------------------
# Utility functions
# --------------------------
def load_wishes():
    try:
        if os.path.exists(WISHES_FILE):
            with open(WISHES_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print("load_wishes error:", e)
    return {}

def save_wishes(wishes_data):
    try:
        with open(WISHES_FILE, 'w') as f:
            json.dump(wishes_data, f)
        return True
    except Exception as e:
        print("save_wishes error:", e)
        return False

def update_wish_probability(wish_id, increment, supporter_id):
    wishes_data = load_wishes()
    if wish_id in wishes_data:
        wish_data = wishes_data[wish_id]
        if 'supporters' not in wish_data:
            wish_data['supporters'] = []
        if supporter_id in wish_data['supporters']:
            return False, wish_data['current_probability']
        wish_data['supporters'].append(supporter_id)
        new_probability = min(99.9, wish_data['current_probability'] + increment)
        wish_data['current_probability'] = new_probability
        if 'total_luck_added' not in wish_data:
            wish_data['total_luck_added'] = 0
        wish_data['total_luck_added'] += increment
        wish_data['last_updated'] = time.time()
        save_wishes(wishes_data)
        return True, new_probability
    return False, None

def get_wish_data(wish_id):
    wishes_data = load_wishes()
    return wishes_data.get(wish_id)

def create_or_update_wish(wish_id, wish_text, initial_probability):
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
        wishes_data[wish_id]['wish_text'] = wish_text
        wishes_data[wish_id]['last_updated'] = time.time()
    save_wishes(wishes_data)
    return wishes_data[wish_id]

def safe_decode_wish(encoded_wish):
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

def generate_wish_id(wish_text):
    unique_str = f"{wish_text}_{time.time()}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:10]

def get_random_increment():
    return round(random.uniform(1.0, 10.0), 1)

def create_share_link(wish_id, wish_text, probability=None):
    try:
        base_url = "https://2026christmas-yourwish-mywish-elena.streamlit.app"
    except:
        base_url = "http://localhost:8501"
    short_wish = wish_text[:80].replace('\n',' ').replace('\r',' ').replace('"', "'").replace('  ',' ')
    encoded_wish = urllib.parse.quote_plus(short_wish)
    prob_param = f"&prob={probability:.1f}" if probability is not None else ""
    return f"{base_url}/?wish_id={wish_id}&wish={encoded_wish}{prob_param}".strip()

def evaluate_wish_sentiment(wish_text):
    try:
        pipe = pipeline("sentiment-analysis")
        result = pipe(wish_text[:512])[0]
        st.session_state.all_wishes.append({
            'text': wish_text[:100],
            'label': result['label'],
            'score': result['score']
        })
        has_wish_keyword = any(k in wish_text.lower() for k in ['wish','hope','want','dream'])
        if result['label'] == 'POSITIVE' and result['score'] > 0.6:
            return 'POSITIVE', result['score']
        elif has_wish_keyword:
            return 'POSITIVE', max(result['score'],0.7)
        else:
            return result['label'], result['score']
    except Exception as e:
        print("Model error:", e)
        return 'POSITIVE',0.7

# --------------------------
# Page setup
# --------------------------
st.set_page_config(page_title="🎄 Christmas Wish 2026", page_icon="🎄", layout="centered")

# --------------------------
# Custom CSS
# --------------------------
st.markdown("""
<style>
.stButton>button{background-color:#FF6B6B;color:white;border:none;padding:10px 20px;border-radius:10px;font-weight:bold;}
.wish-quote{font-style:italic;font-size:18px;color:#333;margin:20px 0;padding:15px;background-color:#f9f9f9;border-radius:10px;border-left:4px solid #4CAF50;}
.probability-display{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px;border-radius:15px;text-align:center;margin:20px 0;box-shadow:0 4px 6px rgba(0,0,0,0.1);}
.share-box{background-color:#f0f2f6;border:2px solid #dee2e6;border-radius:8px;padding:15px;margin:10px 0;font-family:monospace;word-break:break-all;}
</style>
""", unsafe_allow_html=True)

# --------------------------
# Main title
# --------------------------
st.title("Christmas Wish 2026")

# --------------------------
# Handle shared wish
# --------------------------
query_params = st.query_params
shared_wish_id = query_params.get("wish_id", [None])[0]
shared_wish_text = query_params.get("wish", [None])[0]
shared_prob_param = query_params.get("prob", [None])[0]
url_prob = None
if shared_prob_param:
    try:
        url_prob = max(0.0,min(99.9,float(str(shared_prob_param).strip().rstrip('%'))))
    except: url_prob=None

if shared_wish_id:
    # Show message and wish
    st.markdown("""**Message from your friend:**\n*\"Merry Christmas! I just made a wish for 2026. Please click the button below to share your Christmas luck!\"*""")
    if shared_wish_text:
        decoded_wish = safe_decode_wish(shared_wish_text)
        st.markdown(f'<div class="wish-quote">"{decoded_wish}"</div>', unsafe_allow_html=True)
    
    wish_data = get_wish_data(shared_wish_id)

    # If not exists, create with URL probability
    if not wish_data and shared_wish_text:
        initial_prob = url_prob if url_prob is not None else 60.0
        wish_data = create_or_update_wish(shared_wish_id, decoded_wish, initial_prob)

    # Sync probability with URL param
    if wish_data and url_prob is not None:
        if abs(wish_data['current_probability'] - url_prob) > 0.05:
            wish_data['current_probability'] = url_prob
            wish_data['last_updated'] = time.time()
            wishes = load_wishes()
            wishes[shared_wish_id] = wish_data
            save_wishes(wishes)

    # Display probability
    def display_shared_probability(wish_data):
        st.markdown(f"""
        <div class="probability-display">
        <h3>Current Probability</h3>
        <h1>{wish_data['current_probability']:.1f}%</h1>
        <p>Supported by {len(wish_data.get('supporters',[]))} friend{'s' if len(wish_data.get('supporters',[]))!=1 else ''} 🎄</p>
        </div>
        """, unsafe_allow_html=True)

    display_shared_probability(wish_data)

    # Add support button
    increment = get_random_increment()
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button(f"🍀 Click to Add +{increment}% Christmas Luck"):
            success,new_prob = update_wish_probability(shared_wish_id, increment, st.session_state.supporter_id)
            if success:
                # reload fresh wish_data
                wish_data = get_wish_data(shared_wish_id)
                st.session_state.my_wish_probability = wish_data['current_probability']
                display_shared_probability(wish_data)
                st.balloons()
                st.success(f"**Thank you! You added +{increment}% luck. New probability: {wish_data['current_probability']:.1f}%**")
            else:
                st.info("🌟 You've already shared your luck for this wish!")

    st.markdown("---\n### Your Turn to Make a Wish! 🎄\n📝 https://2026wisheval-elena-python.streamlit.app/")
    st.stop()

# --------------------------
# Main wish input and evaluation
# --------------------------
if not st.session_state.show_wish_results:
    st.markdown("### Hi there, Merry Christmas! 🎄")
    wish_prompt = st.text_area("🎅 Tell me your wish for 2026:", placeholder="E.g., I wish to learn a new language in 2026...", height=100)
    with st.expander("💡 Tips for better wishes"):
        st.markdown("""
        - Start with: I wish..., I hope..., I want...
        - Be specific and positive
        - Examples: I wish to learn Spanish in 2026, My dream is to travel...
        """)

    if st.button("🎯 Evaluate My Wish"):
        if wish_prompt and len(wish_prompt.strip())>3:
            label, score = evaluate_wish_sentiment(wish_prompt)
            if label=='POSITIVE':
                base_prob = 60.0 + score*20
                wish_id = generate_wish_id(wish_prompt)
                wish_data = create_or_update_wish(wish_id, wish_prompt, base_prob)
                st.session_state.my_wish_text = wish_prompt
                st.session_state.my_wish_probability = wish_data['current_probability']
                st.session_state.wish_id = wish_id
                st.session_state.show_wish_results = True
                st.experimental_rerun()
            else:
                st.warning("Please make your wish more positive and specific.")
        else:
            st.warning("📝 Write your wish (at least 4 characters)")

# --------------------------
# Show results
# --------------------------
else:
    wish_data = get_wish_data(st.session_state.wish_id)
    if wish_data:
        st.session_state.my_wish_probability = wish_data['current_probability']
        current_prob = st.session_state.my_wish_probability
        supporters_count = len(wish_data.get('supporters',[]))
        st.markdown(f"""
        <div class="probability-display">
        <h3>Your Wish Probability</h3>
        <h1>{current_prob:.1f}%</h1>
        <p>{supporters_count} friend{'s have' if supporters_count!=1 else ' has'} shared luck</p>
        </div>
        """, unsafe_allow_html=True)

        # Share section
        st.markdown("---\n### 📤 Share with friends to get more Christmas luck!")
        share_link = create_share_link(st.session_state.wish_id, st.session_state.my_wish_text, current_prob)
        st.markdown(f'<div class="share-box">{share_link}</div>', unsafe_allow_html=True)

        # Refresh button
        if st.button("🔄 Fetch latest probability"):
            wish_data = get_wish_data(st.session_state.wish_id)
            st.session_state.my_wish_probability = wish_data['current_probability']
            st.experimental_rerun()
    else:
        st.error("Wish data not found. Please make a new wish.")
        if st.button("📝 Make New Wish"):
            st.session_state.show_wish_results = False
            st.session_state.my_wish_text = ""
            st.session_state.wish_id = None
            st.experimental_rerun()

# --------------------------
# Footer
# --------------------------
st.markdown("---")
st.markdown("Hope you will have fun with this app! - Yours, Elena")
