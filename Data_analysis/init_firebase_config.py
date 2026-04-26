import firebase_admin
from firebase_admin import credentials, firestore

# --- INITIALIZATION ---
try:
    cred = credentials.Certificate('../firebase_cred.json')
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    exit()

# --- 1. SQUAD DEFICITS (Agent B Initial State) ---
SQUAD_DEFICIT_MAP = {
    "GOALKEEPER": 0.5,
    "FULLBACK": 0.5,
    "CENTER_BACK": 0.5,
    "MIDFIELDER": 0.5,
    "WINGER": 0.5,
    "ATTACKER": 0.5
}

# --- 2. TEAM WORST STATS (Agent C Initial State) ---
TEAM_WORST_STATS = {
    "Saves": False,
    "Saves Insidebox": False,
    "Cleansheets": False,
    "Accurate Passes Percentage": False,
    "Accurate Passes": False,
    "Long Balls Won": False,
    "Clearances": False,
    "Duels Won Percentage": False,
    "Interceptions": False,
    "Ball Recovery": False,
    "Passes In Final Third": False,
    "Successful Crosses Percentage": False,
    "Accurate Crosses": False,
    "Successful Dribbles": False,
    "Key Passes": False,
    "Chances Created": False,
    "Shots Blocked": False,
    "Shots On Target": False,
    "Aerials Won Percentage": False,
    "Tacles Won Percentage": False,
    "Tackles Won Percentage": False,
}

print("Pushing 'u_config' documents to Firestore...")
db.collection('u_config').document('squad_deficits').set(SQUAD_DEFICIT_MAP)
db.collection('u_config').document('team_worst_stats').set(TEAM_WORST_STATS)
print("Successfully initialized 'squad_deficits' and 'team_worst_stats' in the database!")