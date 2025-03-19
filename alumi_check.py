import streamlit as st
import google.generativeai as genai
import json
import os
import pandas as pd  # For displaying alumni table

# Configure API Key
api_key = "AIzaSyAmG3XKBwe4Tyq3tyCZfkr9WHvE9AYpbi4"
genai.configure(api_key=api_key)

# Model Configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 65536,
}

# Initialize model
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
    system_instruction=(
        "Your name is Jarvis. Your job is to help students in studies and nothing else. "
        "Other than students studies you should never reply to other queries, the subject maybe math etc or any enginnering subjects"
        "Your answers should be precise and easy to understand. you can provide external links"
    )
)

# File to store user credentials
USER_FILE = "users.json"

# ---------- User Authentication Helpers ----------
def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as file:
            return json.load(file)
    return {}

def save_users(users):
    with open(USER_FILE, "w") as file:
        json.dump(users, file)

def load_chat_history(username):
    filename = f"chat_{username}.json"
    if os.path.exists(filename):
        with open(filename, "r") as file:
            data = json.load(file)
            chats = data.get("chats", {})
            titles = data.get("titles", {})
            # Convert keys from strings to integers
            chats = {int(k): v for k, v in chats.items()}
            titles = {int(k): v for k, v in titles.items()}
            return chats, titles
    return {}, {}

def save_chat_history(username, chats, titles):
    filename = f"chat_{username}.json"
    with open(filename, "w") as file:
        json.dump({"chats": chats, "titles": titles}, file)

# ---------- Alumni Details Feature ----------
def load_alumni_data():
    filename = "alumni_data.json"
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return {}

def get_alumni_details_list(department, batch=None):
    """Return a list of alumni dictionaries for the given department and optional batch filter."""
    data = load_alumni_data()
    if department not in data:
        return []
    alumni_list = data[department]
    if batch:
        alumni_list = [alum for alum in alumni_list if str(alum.get("batch", "")).strip() == str(batch).strip()]
    return alumni_list

def format_alumni_for_table(alumni_list):
    """Format alumni details into 3 columns: Name & Batch, Role & Company, Contact Info."""
    formatted_data = []
    for alum in alumni_list:
        name_batch = f"{alum.get('name')} ({alum.get('batch')})"
        role_company = f"{alum.get('current_role')} at {alum.get('company')}"
        linkedin = alum.get("linkedin", "")
        if linkedin:
            contact = f"{alum.get('email')} | {linkedin}"
        else:
            contact = alum.get("email", "")
        formatted_data.append({
            "Name & Batch": name_batch,
            "Role & Company": role_company,
            "Contact Info": contact
        })
    return formatted_data

# ---------- Authentication Page ----------
def auth_page():
    st.title("🔒 Welcome to Jarvis Chatbot")
    users = load_users()
    if not st.session_state.get("show_signup", False):
        # LOGIN FORM
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns([0.1, 0.8])
        with col1:
            if st.button("Login"):
                if username in users and users[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    chats, titles = load_chat_history(username)
                    st.session_state.chats = chats if chats else {}
                    st.session_state.titles = titles if titles else {}
                    if not st.session_state.chats:
                        st.session_state.chats[1] = []
                        st.session_state.titles[1] = "New Chat"
                        st.session_state.current_chat = 1
                    else:
                        if "current_chat" not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
                            st.session_state.current_chat = max(st.session_state.chats.keys())
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid credentials! Please try again.")
        with col2:
            if st.button("Sign Up", help="Create a new account"):
                st.session_state.show_signup = True
                st.rerun()
    else:
        # SIGN-UP FORM
        st.subheader("📝 Create an Account")
        new_username = st.text_input("Choose a Username")
        new_password = st.text_input("Choose a Password", type="password")
        col1, col2 = st.columns([0.1, 0.7])
        with col1:
            if st.button("Sign Up"):
                if new_username in users:
                    st.error("Username already taken! Try a different one.")
                else:
                    users[new_username] = new_password
                    save_users(users)
                    st.session_state.logged_in = True
                    st.session_state.username = new_username
                    st.session_state.chats = {1: []}
                    st.session_state.titles = {1: "New Chat"}
                    st.session_state.current_chat = 1
                    save_chat_history(new_username, st.session_state.chats, st.session_state.titles)
                    st.success("Account created successfully! Logging you in...")
                    st.rerun()
        with col2:
            if st.button("Back to Login"):
                st.session_state.show_signup = False
                st.rerun()

# ---------- Chatbot Page ----------
def chatbot():
    st.set_page_config(page_title="Jarvis - AI Study Assistant", layout="wide")
    st.title("🤖 Jarvis - AI Study Assistant")
    if "chats" not in st.session_state:
        st.session_state.chats = {}
    if "titles" not in st.session_state:
        st.session_state.titles = {}
    if "current_chat" not in st.session_state:
        st.session_state.current_chat = max(st.session_state.chats.keys(), default=1) if st.session_state.chats else 1
    if not st.session_state.chats:
        st.session_state.chats = {1: []}
        st.session_state.titles = {1: "New Chat"}
        st.session_state.current_chat = 1

    st.sidebar.markdown("### 🗂 Chat History")
    
    # Improved Alumni Details Section in Sidebar using a neat table
    with st.sidebar.expander("🎓 Alumni Details", expanded=True):
        dept = st.selectbox("Select Department", ["CSE", "AI&DS"], key="alumni_dept")
        batch = st.text_input("Enter Batch (optional)", key="alumni_batch")
        if st.button("Get Alumni Info", key="alumni_btn"):
            alumni_list = get_alumni_details_list(dept, batch.strip() if batch.strip() else None)
            if alumni_list:
                formatted_data = format_alumni_for_table(alumni_list)
                df = pd.DataFrame(formatted_data)
                st.table(df)
            else:
                st.warning("No alumni found for the specified criteria.")
    
    # Function to generate chat title
    def generate_chat_title(chat_id):
        if chat_id in st.session_state.chats and st.session_state.chats[chat_id]:
            all_messages = " ".join([msg for _, msg in st.session_state.chats[chat_id]])
            title_prompt = f"Generate a short and relevant 2-3 word title for this conversation: {all_messages}"
            title_response = model.generate_content(title_prompt)
            return title_response.text.strip()[:20] if title_response else "Chat"
        return "Chat"
    
    # New Chat Button
    if st.sidebar.button("➕ Start New Chat", key="new_chat", use_container_width=True):
        prev_chat_id = st.session_state.current_chat
        new_chat_id = max(st.session_state.chats.keys(), default=0) + 1
        if st.session_state.titles.get(prev_chat_id, "New Chat") == "New Chat":
            st.session_state.titles[prev_chat_id] = generate_chat_title(prev_chat_id)
        st.session_state.chats[new_chat_id] = []
        st.session_state.titles[new_chat_id] = "New Chat"
        st.session_state.current_chat = new_chat_id
        save_chat_history(st.session_state.username, st.session_state.chats, st.session_state.titles)
        st.rerun()
    
    st.sidebar.markdown("---")
    # Display previous chats in sidebar
    for chat_id, title in sorted(st.session_state.titles.items(), key=lambda x: int(x[0]), reverse=True):
        with st.sidebar.container():
            col1, col2 = st.sidebar.columns([0.85, 0.15])
            with col1:
                if st.button(f"📌 {title}", key=f"chat_{chat_id}", use_container_width=True):
                    st.session_state.current_chat = chat_id
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"delete_{chat_id}"):
                    if chat_id in st.session_state.chats:
                        del st.session_state.chats[chat_id]
                    if chat_id in st.session_state.titles:
                        del st.session_state.titles[chat_id]
                    if st.session_state.chats:
                        st.session_state.current_chat = max(st.session_state.chats.keys())
                    else:
                        st.session_state.chats = {1: []}
                        st.session_state.titles = {1: "New Chat"}
                        st.session_state.current_chat = 1
                    save_chat_history(st.session_state.username, st.session_state.chats, st.session_state.titles)
                    st.rerun()
    
    st.sidebar.markdown("---")
    # Logout Button in Sidebar
    if st.sidebar.button("🚪 Logout", key="logout", use_container_width=True):
        save_chat_history(st.session_state.username, st.session_state.chats, st.session_state.titles)
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.titles = {}
        st.rerun()
    
    st.sidebar.markdown("---")
    # Ensure current_chat is valid before displaying messages
    chat_id = st.session_state.current_chat
    if chat_id not in st.session_state.chats:
        st.session_state.current_chat = max(st.session_state.chats.keys(), default=1)
        chat_id = st.session_state.current_chat
    
    st.subheader(f"📌 {st.session_state.titles.get(chat_id, 'Chat')}")
    for role, text in st.session_state.chats.get(chat_id, []):
        st.chat_message("user" if role == "You" else "assistant").write(text)
    
    # Chat Input: process user messages and check for alumni queries
    user_input = st.chat_input("Type your message...")
    if user_input:
        st.session_state.chats[chat_id].append(("You", user_input))
        if any(keyword in user_input.lower() for keyword in ["alumni", "graduate", "alumini"]):
            # Attempt to extract department and batch from the query
            dept_query = None
            if "cse" in user_input.lower():
                dept_query = "CSE"
            elif "ai&ds" in user_input.lower() or "aids" in user_input.lower():
                dept_query = "AI&DS"
            batch_query = None
            for word in user_input.split():
                if word.isdigit():
                    batch_query = word
                    break
            if dept_query:
                alumni_list = get_alumni_details_list(dept_query, batch_query)
                if alumni_list:
                    formatted_response = "\n".join(
                        [f"{alum.get('name')} ({alum.get('batch')}) - {alum.get('current_role')} at {alum.get('company')}"
                         for alum in alumni_list]
                    )
                    bot_response = formatted_response
                else:
                    bot_response = "No alumni details found for the specified criteria."
            else:
                bot_response = "Please specify the department (CSE or AI&DS) for alumni details."
        else:
            response = model.generate_content(user_input)
            bot_response = response.text if response else "I'm not sure, can you clarify?"
        st.session_state.chats[chat_id].append(("Jarvis", bot_response))
        save_chat_history(st.session_state.username, st.session_state.chats, st.session_state.titles)
        st.rerun()

# ---------- Main App Flow ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    chatbot()
else:
    auth_page()
