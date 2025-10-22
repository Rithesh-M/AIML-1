# app.py
import os
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
import bcrypt  # <-- This is our new, reliable password library

# --- 1. PAGE CONFIGURATION ---
# The theme is now set in your new .streamlit/config.toml file
st.set_page_config(page_title="NutriPlan AI", page_icon="🧑‍⚕️", layout="wide")

# --- 2. FIREBASE & GOOGLE AI INITIALIZATION ---

# Initialize Firebase
# --- START: NEW FIREBASE INIT ---

# Define the database URL (from your firebase project)
DATABASE_URL = "https://aiml-pbl-default-rtdb.firebaseio.com/"

try:
    # Try to get the app, if it's already initialized
    app = firebase_admin.get_app()
except ValueError:
    # If not initialized, try to initialize it
    try:
        # 1. Check if credentials are in Streamlit secrets (for deployment)
        if 'firebase' in st.secrets:
            creds_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(creds_dict)
        else:
            # 2. If not, check for the local file (for local testing)
            if os.path.exists("firebase-key.json"):
                cred = credentials.Certificate("firebase-key.json")
            else:
                raise FileNotFoundError("Firebase credentials not found. Please add 'firebase-key.json' or set st.secrets['firebase'].")

        # Initialize the Firebase app
        firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

    except FileNotFoundError as e:
        st.error(e)
        st.stop()
    except Exception as e:
        st.error(f"Firebase initialization error: {e}")
        st.stop()
# --- END: NEW FIREBASE INIT ---

# Initialize Firestore database
db = firestore.client()

# Initialize Google Generative AI
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-pro')
except Exception as e:
    st.error("Google AI initialization error. Please check your API key in Streamlit secrets.")
    st.stop()

# --- 3. SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'user_profile' not in st.session_state:
    st.session_state['user_profile'] = {}

# --- 4. PASSWORD HASHING & CHECKING ---
# These are our new, reliable functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- 5. THE APPLICATION ---

def run_app():
    # --- A. LOGIN / SIGN UP VIEW ---
    if not st.session_state['logged_in']:
        st.title("Welcome to 🧑‍⚕️ NutriPlan AI")
        st.markdown("Your intelligent partner for personalized meal planning.")
        
        choice = st.selectbox("Login or Sign Up", ["Login", "Sign Up"], label_visibility="collapsed")

        if choice == "Login":
            st.subheader("Login to Your Account")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if st.button("Login", type="primary"):
                user_ref = db.collection("users").document(username).get()
                if user_ref.exists:
                    user_data = user_ref.to_dict()
                    # Use our new, reliable check_password function
                    if check_password(password, user_data['password_hash']):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.session_state['user_profile'] = user_data
                        st.rerun()
                    else:
                        st.error("Incorrect username or password.")
                else:
                    st.error("Incorrect username or password.")
        
        elif choice == "Sign Up":
            st.subheader("Create a New Account")
            new_name = st.text_input("Your Name")
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type="password")

            if st.button("Sign Up", type="primary"):
                if not new_name or not new_username or not new_password:
                    st.warning("Please fill out all fields.")
                else:
                    user_ref = db.collection("users").document(new_username).get()
                    if user_ref.exists:
                        st.error("Username already taken. Please choose another.")
                    else:
                        # Use our new, reliable hash_password function
                        hashed_password = hash_password(new_password)
                        user_data = {
                            "name": new_name,
                            "username": new_username, # We will use this as the document ID
                            "password_hash": hashed_password,
                            # Initialize all profile fields as requested
                            "age": None, "height": None, "weight": None, "country": "",
                            "cuisine": "", "food_availability": "", "goals": [], 
                            "health_issues": "", "feedback": []
                        }
                        # Save the new user in the "users" collection with their username as the key
                        db.collection("users").document(new_username).set(user_data)
                        st.success("Account created successfully! Please login.")
                        st.balloons()
    
    # --- B. MAIN APPLICATION VIEW (AFTER LOGIN) ---
    else:
        st.sidebar.header(f"Welcome, {st.session_state['user_profile']['name']}!")
        
        page = st.sidebar.radio("Navigation", ["My Profile", "Meal Planner"])

        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.session_state['user_profile'] = {}
            st.rerun()

        # --- MY PROFILE PAGE ---
        if page == "My Profile":
            st.header("👤 My Profile")
            st.write("Keep your details updated for the most accurate meal plans.")
            
            profile = st.session_state['user_profile']
            
            with st.form("profile_form"):
                st.subheader("Personal Details")
                col1, col2, col3 = st.columns(3)
                with col1:
                    age = st.number_input("Age", min_value=1, max_value=120, value=profile.get("age") or 25)
                with col2:
                    height = st.number_input("Height (cm)", min_value=50, max_value=250, value=profile.get("height") or 170)
                with col3:
                    weight = st.number_input("Weight (kg)", min_value=10, max_value=300, value=profile.get("weight") or 70)

                st.subheader("Location & Preferences")
                col1, col2 = st.columns(2)
                with col1:
                    country = st.text_input("Country of Residence", value=profile.get("country") or "India")
                with col2:
                    cuisine = st.text_input("Preferred Cuisine (e.g., South Indian, Italian)", value=profile.get("cuisine") or "")
                
                food_availability = st.text_area("What foods are easily available to you? (e.g., rice, lentils, chicken, spinach)", value=profile.get("food_availability") or "")

                st.subheader("Health Goals & Conditions")
                goals_options = [
                    "Lose Fat", "Gain Muscle", "Maintain Weight", "Improve Flexibility",
                    "Manage Diabetes", "Support Kidney Health (Urinary)", "Stay Lean", "Lose Only Fat"
                ]
                goals = st.multiselect("Select Your Goals", goals_options, default=profile.get("goals") or [])
                
                health_issues = st.text_area("List allergies or health issues (e.g., Peanut allergy, Type 2 Diabetes, high uric acid)", value=profile.get("health_issues") or "")

                if st.form_submit_button("Save Profile", type="primary"):
                    updated_profile_data = {
                        "name": profile['name'], "password_hash": profile['password_hash'], "username": st.session_state['username'],
                        "age": age, "height": height, "weight": weight, "country": country,
                        "cuisine": cuisine, "food_availability": food_availability, 
                        "goals": goals, "health_issues": health_issues,
                        "feedback": profile.get("feedback", []) # Keep existing feedback
                    }
                    db.collection("users").document(st.session_state['username']).set(updated_profile_data)
                    st.session_state['user_profile'] = updated_profile_data
                    st.success("Profile updated successfully!")

        # --- MEAL PLANNER PAGE ---
        elif page == "Meal Planner":
            st.header("🧑‍⚕️ Your AI Meal Planner")
            profile = st.session_state['user_profile']

            if not profile.get("age"):
                st.warning("Please complete your profile first to get a meal plan.")
            else:
                if st.button("Generate Today's Meal Plan", type="primary"):
                    with st.spinner("Your personal AI chef is crafting your plan..."):
                        
                        prompt = f"""
                        You are an expert nutritionist and world-class chef. Create a 1-day meal plan for a user with the following profile:
                        - Name: {profile['name']}
                        - Age: {profile['age']}
                        - Height: {profile['height']} cm
                        - Weight: {profile['weight']} kg
                        - Country of Residence: {profile['country']}
                        - Preferred Cuisine: {profile['cuisine']}
                        - Foods easily available: {profile['food_availability']}
                        - Health Goals: {', '.join(profile['goals'])}
                        - Other Health Issues/Allergies: {profile['health_issues']}

                        Your task:
                        1.  **Analyze the profile**: Briefly state the user's primary goal (e.g., "Weight Loss for a Diabetic User").
                        2.  **Create a 3-meal plan**: Breakfast, Lunch, and Dinner.
                        3.  **For each meal**:
                            -   Provide a recipe name that fits their preferred cuisine.
                            -   List simple ingredients, focusing on the foods they have available.
                            -   Provide a clickable hyperlink to a real recipe search (e.g., `https://www.google.com/search?q=healthy+palak+paneer+recipe`).
                            -   In one sentence, state the **Advantages** of this meal for their goal.
                            -   In one sentence, state the potential **Side Effects/Cautions** (e.g., "Monitor portion size due to...").
                        4.  **Format the entire response** using clear Markdown with headings, bold text, and bullet points.
                        """
                        try:
                            response = model.generate_content(prompt)
                            st.markdown(response.text)

                            with st.expander("Give Feedback on this Meal Plan"):
                                st.write("Your feedback helps the AI learn!")
                                feedback_text = st.text_area("What did you like or dislike?", key="feedback_box")
                                if st.button("Submit Feedback"):
                                    # Save feedback to the database
                                    new_feedback = {"plan": response.text, "feedback": feedback_text}
                                    db.collection("users").document(st.session_state['username']).update({
                                        "feedback": firestore.ArrayUnion([new_feedback])
                                    })
                                    st.success("Thank you for your feedback! It has been saved to your profile.")

                        except Exception as e:
                            st.error(f"An error occurred while generating the plan: {e}")

# This runs the app
if __name__ == "__main__":
    run_app()
