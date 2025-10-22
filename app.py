# --- 2. FIREBASE & GOOGLE AI INITIALIZATION ---

# Initialize Firebase
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
            
            # --- START: FINAL ROBUST FIX ---
            # The error "InvalidLength(1621)" means the key body is being passed
            # without the header/footer. We will rebuild the key manually.
            if 'private_key' in creds_dict:
                pk_body = creds_dict['private_key'].replace('\\n', '\n').replace('\n', '')
                creds_dict['private_key'] = (
                    "-----BEGIN PRIVATE KEY-----\n"
                    + pk_body
                    + "\n-----END PRIVATE KEY-----\n"
                )
            # --- END: FINAL ROBUST FIX ---

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
