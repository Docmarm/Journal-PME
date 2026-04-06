import os
import time
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


# =============================================================================
# CONFIG
# =============================================================================

st.set_page_config(
    page_title="Journal Comptable PME",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)

MOIS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

CATEGORIES = {
    "Vente / Recette": "recette",
    "Entrée Caisse": "caisse_entree",
    "Sortie Caisse": "caisse_sortie",
    "Entrée Banque": "banque_entree",
    "Sortie Banque": "banque_sortie",
    "Salaire": "salaire",
    "Fournitures & Services": "fourniture",
    "Matières Premières": "matiere_premiere",
    "Loyer": "loyer",
    "Transport": "transport",
    "Frais Bancaires": "frais_bancaires",
    "Autre Coût": "autre_cout",
    "Investissement": "investissement",
}
CAT_LABELS = {v: k for k, v in CATEGORIES.items()}
CAT_COSTS = {
    "salaire",
    "fourniture",
    "matiere_premiere",
    "loyer",
    "transport",
    "frais_bancaires",
    "autre_cout",
}

INVESTMENT_LIVES = {
    "Bâtiment commercial": 25,
    "Bâtiment habitation": 75,
    "Matériel & Outillage": 7,
    "Matériel de Transport": 4,
    "Mobilier": 7,
    "Frais Immobilisés": 3,
    "Informatique / IT": 4,
    "Équipement réseau / télécom": 5,
}

DEFAULT_CONFIG = {
    "nom": "Mon Entreprise",
    "adresse": "",
    "tel": "",
    "rc": "",
    "email": "",
    "banque": "",
    "devise": "FCFA",
    "taux_is": 30,
    "solde_initial_caisse": 0.0,
    "solde_initial_banque": 0.0,
}

BILAN_FIELDS = [
    ("Immobilisations Incorporelles", "immo_incorp"),
    ("Matériel & Équipements", "immo_corp"),
    ("Mobilier de Bureau", "mobilier"),
    ("Immobilisations Financières", "immo_fin"),
    ("Stocks", "stocks"),
    ("Créances Clients", "creances"),
    ("Capital Social", "capital"),
    ("Réserves & Report à Nouveau", "reserves"),
    ("Emprunts MLT", "dettes_mlt"),
    ("Dettes Fournisseurs", "dettes_fourn"),
    ("Dettes Fiscales & Sociales", "dettes_fisc"),
]

BUDGET_REVENUE_FIELDS = [
    ("Trésorerie Initiale", "b_treso_init"),
    ("Apports en Capital", "b_apport_cap"),
    ("Apports Compte Courant", "b_apport_cc"),
    ("Emprunts", "b_emprunt"),
    ("Subventions", "b_subvention"),
    ("Chiffre d'Affaires Prévu", "b_ca"),
]

BUDGET_EXPENSE_FIELDS = [
    ("Investissements", "b_d_invest"),
    ("Achats Marchandises / Mat. 1ère", "b_d_achats"),
    ("Emballages", "b_d_emballage"),
    ("Remboursement Emprunt (K+I)", "b_d_remb"),
    ("Matières & Fournitures", "b_d_mat"),
    ("Consommables", "b_d_conso"),
    ("Services Extérieurs", "b_d_ext"),
    ("Loyer", "b_d_loyer"),
    ("Transport", "b_d_transport"),
    ("Communication", "b_d_comm"),
    ("Salaires & Charges Sociales", "b_d_salaires"),
    ("Impôts & Taxes", "b_d_impots"),
    ("Amortissements", "b_d_amort"),
    ("Autres Dépenses", "b_d_autres"),
]


def get_runtime_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


FIREBASE_API_KEY = get_runtime_setting("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID = get_runtime_setting("FIREBASE_PROJECT_ID")
FIRESTORE_BASE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
    f"/databases/(default)/documents"
) if FIREBASE_PROJECT_ID else ""


# =============================================================================
# SESSION / UI
# =============================================================================

def init_session_state() -> None:
    defaults = {
        "backend_status": "",
        "auth_error": "",
        "firebase_id_token": "",
        "firebase_refresh_token": "",
        "firebase_token_expires_at": 0.0,
        "user": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f8fafc;
            color: #0f172a;
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
        }
        [data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] small,
        [data-testid="stSidebar"] p {
            color: #cbd5e1 !important;
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(148, 163, 184, 0.22);
        }
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 12px;
            font-weight: 700;
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25);
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
        }
        [data-testid="stSidebar"] .stButton > button:disabled {
            background: #334155;
            color: #cbd5e1 !important;
            opacity: 1;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="base-input"] > div {
            background: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(148, 163, 184, 0.32) !important;
            border-radius: 12px !important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] input,
        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="select"] div,
        [data-testid="stSidebar"] [data-baseweb="base-input"] input {
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] [data-baseweb="radio"] label {
            border-radius: 10px;
            padding: 0.2rem 0.35rem;
        }
        [data-testid="stSidebar"] [data-baseweb="radio"] label:hover {
            background: rgba(255, 255, 255, 0.06);
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] {
            background: rgba(245, 158, 11, 0.16);
            border: 1px solid rgba(245, 158, 11, 0.35);
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] * {
            color: #fef3c7 !important;
        }

        .app-card {
            background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 16px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
            height: 100%;
        }

        .app-card .kpi-label {
            color: #94a3b8;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin-bottom: .35rem;
        }

        .app-card .kpi-value {
            color: #f8fafc;
            font-size: 1.55rem;
            font-weight: 700;
            line-height: 1.1;
        }

        .app-card .kpi-sub {
            color: #94a3b8;
            font-size: 0.83rem;
            margin-top: .3rem;
        }

        .section-title {
            margin-top: .3rem;
            margin-bottom: .75rem;
            padding-bottom: .4rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            color: #334155;
            font-size: 1.08rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .08em;
        }

        [data-testid="stAlert"] {
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.2);
        }
        [data-testid="stAlert"] * {
            color: #0f172a !important;
        }
        [data-testid="stInfo"] {
            background: #dbeafe;
            border-left: 4px solid #2563eb;
        }
        [data-testid="stSuccess"] {
            background: #dcfce7;
            border-left: 4px solid #16a34a;
        }
        [data-testid="stWarning"] {
            background: #fef3c7;
            border-left: 4px solid #d97706;
        }
        [data-testid="stError"] {
            background: #fee2e2;
            border-left: 4px solid #dc2626;
        }
        .stDataFrame, .stTable {
            border-radius: 14px;
            overflow: hidden;
        }
        .stMarkdown, .stText, p, label {
            color: #0f172a;
        }

        .info-chip {
            display: inline-block;
            padding: .25rem .6rem;
            border-radius: 999px;
            font-size: .78rem;
            font-weight: 600;
            background: #eef2ff;
            color: #3730a3;
            margin-right: .4rem;
            margin-bottom: .4rem;
        }

        .state-ok {
            background: #dcfce7;
            color: #166534;
            padding: .3rem .7rem;
            border-radius: 999px;
            font-weight: 600;
            font-size: .8rem;
        }

        .state-bad {
            background: #fee2e2;
            color: #991b1b;
            padding: .3rem .7rem;
            border-radius: 999px;
            font-weight: 600;
            font-size: .8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="app-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def require_backend_config() -> None:
    if not FIREBASE_API_KEY or not FIREBASE_PROJECT_ID:
        st.error(
            "Configuration Firebase manquante. "
            "Ajoute FIREBASE_API_KEY et FIREBASE_PROJECT_ID dans st.secrets ou les variables d'environnement."
        )
        st.stop()


def set_backend_status(message: str = "") -> None:
    st.session_state["backend_status"] = message


def invalidate_caches() -> None:
    st.cache_data.clear()


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def fmt_amount(n: Any, devise: str = "FCFA") -> str:
    try:
        return f"{int(round(float(n))):,} {devise}".replace(",", " ")
    except Exception:
        return f"0 {devise}"


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def safe_int(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def month_name_from_date(dt_value: Any) -> str:
    if pd.isna(dt_value):
        return ""
    try:
        return MOIS[pd.to_datetime(dt_value).month - 1]
    except Exception:
        return ""


def current_user() -> Optional[Dict[str, Any]]:
    return st.session_state.get("user")


def current_user_id() -> Optional[str]:
    user = current_user()
    return user.get("uid") if user else None


def user_collection(name: str, user_uid: Optional[str] = None) -> str:
    uid = user_uid or current_user_id()
    if not uid:
        return name
    return f"users/{uid}/{name}"


# =============================================================================
# FIREBASE AUTH
# =============================================================================

def parse_firebase_auth_error(response: requests.Response) -> str:
    try:
        code = response.json().get("error", {}).get("message", "")
    except Exception:
        code = ""

    mapping = {
        "EMAIL_EXISTS": "Un compte existe déjà avec cet email.",
        "INVALID_LOGIN_CREDENTIALS": "Email ou mot de passe invalide.",
        "INVALID_PASSWORD": "Email ou mot de passe invalide.",
        "EMAIL_NOT_FOUND": "Email ou mot de passe invalide.",
        "USER_DISABLED": "Ce compte est désactivé.",
        "WEAK_PASSWORD": "Le mot de passe doit contenir au moins 6 caractères.",
        "OPERATION_NOT_ALLOWED": "Active le fournisseur Email/Mot de passe dans Firebase Authentication.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Trop de tentatives. Réessaie plus tard.",
        "TOKEN_EXPIRED": "Session expirée. Reconnecte-toi.",
        "INVALID_ID_TOKEN": "Session invalide. Reconnecte-toi.",
    }
    return mapping.get(code, f"Erreur Firebase Auth: {code or response.status_code}")


def firebase_identity_request(endpoint: str, payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    url = f"https://identitytoolkit.googleapis.com/v1/{endpoint}?key={FIREBASE_API_KEY}"
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code != 200:
            return None, parse_firebase_auth_error(response)
        return response.json(), None
    except requests.RequestException:
        return None, "Impossible de contacter Firebase Authentication."


def clear_auth_session() -> None:
    for key in [
        "user",
        "firebase_id_token",
        "firebase_refresh_token",
        "firebase_token_expires_at",
        "auth_error",
    ]:
        st.session_state[key] = "" if "token" in key or key == "auth_error" else None
    st.session_state["firebase_token_expires_at"] = 0.0


def set_authenticated_user(
    user_info: Dict[str, Any],
    id_token: str,
    refresh_token: str = "",
    expires_at: Optional[float] = None,
) -> None:
    st.session_state["user"] = {
        "uid": user_info.get("uid", ""),
        "email": normalize_email(user_info.get("email", "")),
        "display_name": user_info.get("display_name", ""),
        "photo_url": user_info.get("photo_url", ""),
        "provider": user_info.get("provider", "password"),
    }
    st.session_state["firebase_id_token"] = id_token or ""
    st.session_state["firebase_refresh_token"] = refresh_token or ""
    st.session_state["firebase_token_expires_at"] = expires_at or (time.time() + 3300)


def fetch_firebase_user(id_token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data, error = firebase_identity_request("accounts:lookup", {"idToken": id_token})
    if error:
        return None, error

    users = data.get("users", [])
    if not users:
        return None, "Utilisateur Firebase introuvable."

    user = users[0]
    providers = user.get("providerUserInfo", [])
    provider_id = providers[0].get("providerId", "password") if providers else "password"

    return {
        "uid": user.get("localId", ""),
        "email": normalize_email(user.get("email", "")),
        "display_name": user.get("displayName", "") or normalize_email(user.get("email", "")).split("@")[0],
        "photo_url": user.get("photoUrl", ""),
        "provider": provider_id,
    }, None


def refresh_firebase_session() -> Optional[str]:
    refresh_token = st.session_state.get("firebase_refresh_token", "")
    if not refresh_token:
        return None

    expires_at = safe_float(st.session_state.get("firebase_token_expires_at"), 0.0)
    if expires_at and time.time() < expires_at - 120:
        return st.session_state.get("firebase_id_token") or None

    url = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
    try:
        response = requests.post(
            url,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=15,
        )
        if response.status_code != 200:
            clear_auth_session()
            return None
        data = response.json()
        st.session_state["firebase_id_token"] = data.get("id_token", "")
        st.session_state["firebase_refresh_token"] = data.get("refresh_token", refresh_token)
        st.session_state["firebase_token_expires_at"] = time.time() + int(data.get("expires_in", 3600))
        return st.session_state["firebase_id_token"]
    except requests.RequestException:
        return st.session_state.get("firebase_id_token") or None


def get_current_id_token() -> Optional[str]:
    token = st.session_state.get("firebase_id_token", "")
    if not token:
        return None
    return refresh_firebase_session() or token


def firebase_sign_in_with_password(email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data, error = firebase_identity_request(
        "accounts:signInWithPassword",
        {
            "email": normalize_email(email),
            "password": password,
            "returnSecureToken": True,
        },
    )
    if error:
        return None, error

    user_info, error = fetch_firebase_user(data.get("idToken", ""))
    if error:
        return None, error

    return {
        "user_info": user_info,
        "id_token": data.get("idToken", ""),
        "refresh_token": data.get("refreshToken", ""),
        "expires_at": time.time() + int(data.get("expiresIn", 3600)),
    }, None


def firebase_register_with_password(email: str, password: str, display_name: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data, error = firebase_identity_request(
        "accounts:signUp",
        {
            "email": normalize_email(email),
            "password": password,
            "returnSecureToken": True,
        },
    )
    if error:
        return None, error

    id_token = data.get("idToken", "")
    if display_name.strip():
        update_data, update_error = firebase_identity_request(
            "accounts:update",
            {
                "idToken": id_token,
                "displayName": display_name.strip(),
                "returnSecureToken": True,
            },
        )
        if not update_error and update_data:
            data = update_data
            id_token = data.get("idToken", id_token)

    user_info, error = fetch_firebase_user(id_token)
    if error:
        return None, error

    return {
        "user_info": user_info,
        "id_token": id_token,
        "refresh_token": data.get("refreshToken", ""),
        "expires_at": time.time() + int(data.get("expiresIn", 3600)),
    }, None


def restore_user_from_session() -> None:
    if current_user():
        return
    token = st.session_state.get("firebase_id_token", "")
    if not token:
        return
    token = get_current_id_token()
    if not token:
        return
    user_info, error = fetch_firebase_user(token)
    if error or not user_info:
        clear_auth_session()
        return
    st.session_state["user"] = user_info


# =============================================================================
# FIRESTORE
# =============================================================================

def _to_fs(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    return {"stringValue": str(value)}


def _from_fs(field_value: Dict[str, Any]) -> Any:
    for key in ["stringValue", "integerValue", "doubleValue", "booleanValue", "nullValue"]:
        if key in field_value:
            value = field_value[key]
            if key == "integerValue":
                return int(value)
            if key == "doubleValue":
                return float(value)
            return value
    return None


def request_firestore(method: str, url: str, expected_statuses: Tuple[int, ...] = (200,), **kwargs) -> Optional[requests.Response]:
    try:
        headers = kwargs.pop("headers", {})
        token = get_current_id_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if headers:
            kwargs["headers"] = headers
        kwargs.setdefault("timeout", 20)

        response = requests.request(method, url, **kwargs)
        if response.status_code not in expected_statuses:
            set_backend_status(f"Synchronisation Firebase indisponible ({response.status_code}).")
            return None

        set_backend_status("")
        return response
    except requests.RequestException:
        set_backend_status("Synchronisation Firebase indisponible. Vérifie la connexion.")
        return None


def fs_list_documents(collection_path: str, page_size: int = 500) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    while True:
        params = {"key": FIREBASE_API_KEY, "pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token

        url = f"{FIRESTORE_BASE_URL}/{collection_path}"
        response = request_firestore("GET", url, expected_statuses=(200, 404), params=params)
        if response is None:
            break
        if response.status_code == 404:
            break

        payload = response.json()
        for doc in payload.get("documents", []):
            row = {k: _from_fs(v) for k, v in doc.get("fields", {}).items()}
            row["_id"] = doc["name"].split("/")[-1]
            docs.append(row)

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return docs


def fs_get_document(doc_path: str) -> Dict[str, Any]:
    url = f"{FIRESTORE_BASE_URL}/{doc_path}"
    response = request_firestore("GET", url, expected_statuses=(200, 404), params={"key": FIREBASE_API_KEY})
    if response is None or response.status_code == 404:
        return {}
    payload = response.json()
    return {k: _from_fs(v) for k, v in payload.get("fields", {}).items()}


def fs_create_document(collection_path: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> bool:
    doc_id = doc_id or str(uuid.uuid4()).replace("-", "")
    url = f"{FIRESTORE_BASE_URL}/{collection_path}"
    payload = {"fields": {k: _to_fs(v) for k, v in data.items()}}
    response = request_firestore(
        "POST",
        url,
        expected_statuses=(200, 201),
        params={"documentId": doc_id, "key": FIREBASE_API_KEY},
        json=payload,
    )
    return response is not None


def fs_update_document(collection_path: str, doc_id: str, data: Dict[str, Any]) -> bool:
    url = f"{FIRESTORE_BASE_URL}/{collection_path}/{doc_id}"
    payload = {"fields": {k: _to_fs(v) for k, v in data.items()}}
    response = request_firestore(
        "PATCH",
        url,
        expected_statuses=(200,),
        params={"key": FIREBASE_API_KEY},
        json=payload,
    )
    return response is not None


def fs_set_document(doc_path: str, data: Dict[str, Any]) -> bool:
    url = f"{FIRESTORE_BASE_URL}/{doc_path}"
    payload = {"fields": {k: _to_fs(v) for k, v in data.items()}}
    response = request_firestore(
        "PATCH",
        url,
        expected_statuses=(200,),
        params={"key": FIREBASE_API_KEY},
        json=payload,
    )
    return response is not None


def fs_delete_document(collection_path: str, doc_id: str) -> bool:
    url = f"{FIRESTORE_BASE_URL}/{collection_path}/{doc_id}"
    response = request_firestore(
        "DELETE",
        url,
        expected_statuses=(200,),
        params={"key": FIREBASE_API_KEY},
    )
    return response is not None


def sync_user_profile(user_info: Dict[str, Any]) -> None:
    existing = fs_get_document(f"users/{user_info['uid']}")
    payload = {
        "email": user_info.get("email", ""),
        "display_name": user_info.get("display_name", ""),
        "photo_url": user_info.get("photo_url", ""),
        "provider": user_info.get("provider", "password"),
        "last_login_at": now_iso(),
    }
    if not existing:
        payload["created_at"] = payload["last_login_at"]
    fs_set_document(f"users/{user_info['uid']}", payload)
    invalidate_caches()


# =============================================================================
# DATA LOADERS
# =============================================================================

def normalize_operations_df(df: pd.DataFrame) -> pd.DataFrame:
    required_defaults = {
        "_id": "",
        "date": None,
        "piece_no": "",
        "libelle": "",
        "categorie": "",
        "montant": 0.0,
        "notes": "",
        "mois": "",
        "annee": 0,
        "asset_family": "",
        "useful_life_years": 0,
        "created_at": "",
        "updated_at": "",
    }

    if df.empty:
        return pd.DataFrame([required_defaults]).iloc[0:0]

    for col, default in required_defaults.items():
        if col not in df.columns:
            df[col] = default

    for col in ["piece_no", "libelle", "categorie", "notes", "mois", "asset_family", "created_at", "updated_at"]:
        df[col] = df[col].fillna("").astype(str)

    df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0.0)
    df["useful_life_years"] = pd.to_numeric(df["useful_life_years"], errors="coerce").fillna(0).astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce").fillna(0).astype(int)

    missing_month = df["mois"].eq("") & df["date"].notna()
    df.loc[missing_month, "mois"] = df.loc[missing_month, "date"].apply(month_name_from_date)

    missing_year = (df["annee"] == 0) & df["date"].notna()
    df.loc[missing_year, "annee"] = df.loc[missing_year, "date"].dt.year.astype(int)

    df = df.sort_values(["date", "created_at"], na_position="last").reset_index(drop=True)
    return df


@st.cache_data(ttl=30, show_spinner=False)
def load_operations(user_uid: str) -> pd.DataFrame:
    docs = fs_list_documents(user_collection("operations", user_uid))
    return normalize_operations_df(pd.DataFrame(docs))


@st.cache_data(ttl=30, show_spinner=False)
def load_bilan_items(user_uid: str) -> List[Dict[str, Any]]:
    return fs_list_documents(user_collection("bilan_items", user_uid))


@st.cache_data(ttl=30, show_spinner=False)
def load_budget_items(user_uid: str) -> List[Dict[str, Any]]:
    return fs_list_documents(user_collection("budget_items", user_uid))


@st.cache_data(ttl=30, show_spinner=False)
def load_company_config(user_uid: str) -> Dict[str, Any]:
    data = fs_get_document(f"users/{user_uid}/config/entreprise")
    merged = DEFAULT_CONFIG.copy()
    merged.update(data or {})
    merged["taux_is"] = safe_float(merged.get("taux_is", 30), 30)
    merged["solde_initial_caisse"] = safe_float(merged.get("solde_initial_caisse", 0), 0)
    merged["solde_initial_banque"] = safe_float(merged.get("solde_initial_banque", 0), 0)
    return merged


def save_company_config(user_uid: str, data: Dict[str, Any]) -> bool:
    payload = DEFAULT_CONFIG.copy()
    payload.update(data)
    ok = fs_set_document(f"users/{user_uid}/config/entreprise", payload)
    if ok:
        invalidate_caches()
    return ok


def upsert_key_value_items(collection_path: str, existing_items: List[Dict[str, Any]], data_map: Dict[str, Any]) -> bool:
    existing_by_key = {item.get("key"): item.get("_id") for item in existing_items}
    success = True
    for key, value in data_map.items():
        payload = {"key": key, "value": float(value)}
        if key in existing_by_key:
            success = fs_update_document(collection_path, existing_by_key[key], payload) and success
        else:
            success = fs_create_document(collection_path, payload) and success
    if success:
        invalidate_caches()
    return success


# =============================================================================
# ANALYTICS
# =============================================================================

def filter_df(df: pd.DataFrame, annee: Optional[int] = None, mois: Optional[str] = None, search: str = "") -> pd.DataFrame:
    if df.empty:
        return df.copy()

    data = df.copy()
    if annee:
        data = data[data["annee"] == annee]
    if mois and mois != "Tous":
        data = data[data["mois"] == mois]

    if search.strip():
        q = search.strip().lower()
        mask = (
            data["libelle"].str.lower().str.contains(q, na=False)
            | data["categorie"].str.lower().str.contains(q, na=False)
            | data["piece_no"].str.lower().str.contains(q, na=False)
            | data["notes"].str.lower().str.contains(q, na=False)
        )
        data = data[mask]

    return data.reset_index(drop=True)


def get_cat(df: pd.DataFrame, *cats: str) -> float:
    if df.empty or "categorie" not in df.columns:
        return 0.0
    return float(df[df["categorie"].isin(cats)]["montant"].sum())


def monthly_summary(df_all: pd.DataFrame, year: int) -> pd.DataFrame:
    rows = []
    df_year = filter_df(df_all, year, None)
    for m in MOIS:
        dm = df_year[df_year["mois"] == m]
        recettes = get_cat(dm, "recette")
        couts = get_cat(dm, *CAT_COSTS)
        invest = get_cat(dm, "investissement")
        rows.append({
            "Mois": m,
            "Recettes": recettes,
            "Coûts": couts,
            "Investissements": invest,
            "Marge": recettes - couts,
            "Résultat opérationnel": recettes - couts - invest,
        })
    return pd.DataFrame(rows)


def running_balance_table(df: pd.DataFrame, entry_cat: str, exit_cat: str, opening_balance: float, devise: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Date", "N° Pièce", "Libellé", "Entrée", "Sortie", "Solde", "_entry_num", "_exit_num", "_solde_num"])

    source = df[df["categorie"].isin([entry_cat, exit_cat])].copy().sort_values("date")
    rows = []
    solde = safe_float(opening_balance, 0)

    for _, row in source.iterrows():
        entree = row["montant"] if row["categorie"] == entry_cat else 0
        sortie = row["montant"] if row["categorie"] == exit_cat else 0
        solde += entree - sortie
        rows.append({
            "Date": row["date"].strftime("%d/%m/%Y") if pd.notna(row["date"]) else "",
            "N° Pièce": row.get("piece_no", ""),
            "Libellé": row.get("libelle", ""),
            "Entrée": fmt_amount(entree, devise) if entree else "—",
            "Sortie": fmt_amount(sortie, devise) if sortie else "—",
            "Solde": fmt_amount(solde, devise),
            "_entry_num": entree,
            "_exit_num": sortie,
            "_solde_num": solde,
        })

    return pd.DataFrame(rows)


def investment_useful_life(row: pd.Series) -> int:
    direct = safe_int(row.get("useful_life_years", 0), 0)
    if direct > 0:
        return direct

    family = str(row.get("asset_family", "")).strip()
    if family in INVESTMENT_LIVES:
        return INVESTMENT_LIVES[family]

    notes = str(row.get("notes", "")).lower()
    for label, years in INVESTMENT_LIVES.items():
        if label.lower() in notes:
            return years

    return 7


def build_depreciation_schedule(df_all: pd.DataFrame, year: int, devise: str) -> pd.DataFrame:
    df_inv = df_all[df_all["categorie"] == "investissement"].copy()
    if df_inv.empty:
        return pd.DataFrame(columns=[
            "Désignation", "Date acquisition", "Catégorie", "Coût",
            "Durée (ans)", "Amort./an", "Amort. cumulé", "Valeur résiduelle"
        ])

    rows = []
    for _, row in df_inv.iterrows():
        montant = safe_float(row.get("montant"), 0.0)
        life = investment_useful_life(row)
        annual_dep = montant / life if life > 0 else 0.0

        if pd.notna(row["date"]):
            years_elapsed = max(0, year - row["date"].year + 1)
        else:
            years_elapsed = 0

        years_elapsed = min(years_elapsed, life)
        accumulated = annual_dep * years_elapsed
        residual = max(0.0, montant - accumulated)

        rows.append({
            "Désignation": row.get("libelle", ""),
            "Date acquisition": row["date"].strftime("%d/%m/%Y") if pd.notna(row["date"]) else "",
            "Catégorie": row.get("asset_family", "") or "Investissement",
            "Coût": fmt_amount(montant, devise),
            "Durée (ans)": life,
            "Amort./an": fmt_amount(annual_dep, devise),
            "Amort. cumulé": fmt_amount(accumulated, devise),
            "Valeur résiduelle": fmt_amount(residual, devise),
            "_annual_dep": annual_dep,
        })

    return pd.DataFrame(rows)


def compute_income_statement(df: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, float]:
    ca = get_cat(df, "recette")
    achats_mat = get_cat(df, "matiere_premiere")
    marge_brute = ca - achats_mat

    fournitures = get_cat(df, "fourniture")
    loyer = get_cat(df, "loyer")
    transport = get_cat(df, "transport")
    frais_banc = get_cat(df, "frais_bancaires")
    autres = get_cat(df, "autre_cout")
    salaires = get_cat(df, "salaire")

    dep_amort = 0.0
    df_inv = df[df["categorie"] == "investissement"].copy()
    if not df_inv.empty:
        for _, row in df_inv.iterrows():
            life = investment_useful_life(row)
            dep_amort += safe_float(row.get("montant"), 0) / life if life > 0 else 0.0

    total_charges = fournitures + loyer + transport + frais_banc + autres + salaires + dep_amort
    resultat_brut = marge_brute - total_charges

    taux_is = safe_float(cfg.get("taux_is", 30), 30) / 100
    impot = max(0.0, resultat_brut * taux_is)
    resultat_net = resultat_brut - impot
    cash_flow = resultat_net + dep_amort

    return {
        "ca": ca,
        "achats_mat": achats_mat,
        "marge_brute": marge_brute,
        "fournitures": fournitures,
        "loyer": loyer,
        "transport": transport,
        "frais_banc": frais_banc,
        "autres": autres,
        "salaires": salaires,
        "dep_amort": dep_amort,
        "total_charges": total_charges,
        "resultat_brut": resultat_brut,
        "taux_is": taux_is,
        "impot": impot,
        "resultat_net": resultat_net,
        "cash_flow": cash_flow,
    }


def compute_year_options(df_all: pd.DataFrame) -> List[int]:
    years = set()
    if not df_all.empty and "annee" in df_all.columns:
        years |= set(df_all["annee"].dropna().astype(int).tolist())
    current_year = datetime.utcnow().year
    years |= set(range(current_year - 2, current_year + 4))
    return sorted(y for y in years if y > 0)


# =============================================================================
# AUTH PAGE
# =============================================================================

def show_auth_page() -> None:
    st.title("Accès sécurisé")
    st.caption("Connexion unique par email et mot de passe avec Firebase Authentication.")

    auth_error = st.session_state.pop("auth_error", "")
    if auth_error:
        st.error(auth_error)

    tab_login, tab_register = st.tabs(["Connexion", "Créer un compte"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="vous@entreprise.com")
            password = st.text_input("Mot de passe", type="password")
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)

            if submitted:
                if "@" not in email or "." not in email:
                    st.error("Veuillez saisir un email valide.")
                elif not password:
                    st.error("Le mot de passe est obligatoire.")
                else:
                    session, error = firebase_sign_in_with_password(email, password)
                    if error:
                        st.error(error)
                    else:
                        set_authenticated_user(
                            session["user_info"],
                            session["id_token"],
                            session["refresh_token"],
                            session["expires_at"],
                        )
                        sync_user_profile(session["user_info"])
                        st.rerun()

    with tab_register:
        with st.form("register_form"):
            display_name = st.text_input("Nom complet", placeholder="Fatmata Diallo")
            email = st.text_input("Email", placeholder="vous@entreprise.com")
            password = st.text_input("Mot de passe", type="password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")
            submitted = st.form_submit_button("Créer le compte", use_container_width=True)

            if submitted:
                if "@" not in email or "." not in email:
                    st.error("Veuillez saisir un email valide.")
                elif len(password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                elif password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    session, error = firebase_register_with_password(email, password, display_name)
                    if error:
                        st.error(error)
                    else:
                        set_authenticated_user(
                            session["user_info"],
                            session["id_token"],
                            session["refresh_token"],
                            session["expires_at"],
                        )
                        sync_user_profile(session["user_info"])
                        st.success("Compte créé avec succès.")
                        st.rerun()

    st.info("Active le fournisseur Email/Mot de passe dans Firebase Authentication si nécessaire.")
    st.stop()


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar(cfg: Dict[str, Any], user: Dict[str, Any], df_all: pd.DataFrame) -> Tuple[str, int, str]:
    year_options = compute_year_options(df_all)
    default_year = datetime.utcnow().year
    default_index = year_options.index(default_year) if default_year in year_options else max(0, len(year_options) - 1)

    with st.sidebar:
        st.markdown("## 📒 Journal PME")
        st.markdown(f"**{cfg.get('nom') or 'Mon Entreprise'}**")
        if cfg.get("rc"):
            st.caption(cfg.get("rc"))
        st.caption(f"Connecté : {user.get('display_name') or user.get('email')}")
        if st.session_state.get("backend_status"):
            st.warning(st.session_state["backend_status"])

        if st.button("Se déconnecter", use_container_width=True):
            clear_auth_session()
            invalidate_caches()
            st.rerun()

        st.markdown("---")

        page = st.radio(
            "Navigation",
            [
                "🏠 Tableau de Bord",
                "📝 Saisie des Opérations",
                "💵 Caisse",
                "🏦 Banque",
                "📊 Coûts & Charges",
                "🏗️ Investissements",
                "📈 Compte de Résultat",
                "⚖️ Bilan",
                "📅 Clôture Mensuelle",
                "🎯 Budget Prévisionnel",
                "⚙️ Paramètres",
            ],
        )

        st.markdown("---")
        annee_filtre = st.selectbox("Année", year_options, index=default_index)
        mois_filtre = st.selectbox("Mois", ["Tous"] + MOIS)

    return page, annee_filtre, mois_filtre


# =============================================================================
# PAGES
# =============================================================================

def page_dashboard(df_all: pd.DataFrame, df: pd.DataFrame, cfg: Dict[str, Any], year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Tableau de Bord")
    st.caption(f"Période : {month} {year}")

    total_recettes = get_cat(df, "recette")
    total_couts = get_cat(df, *CAT_COSTS)
    marge = total_recettes - total_couts

    cash_open = safe_float(cfg.get("solde_initial_caisse", 0), 0)
    bank_open = safe_float(cfg.get("solde_initial_banque", 0), 0)

    solde_caisse = cash_open + get_cat(df, "caisse_entree") - get_cat(df, "caisse_sortie")
    solde_banque = bank_open + get_cat(df, "banque_entree") - get_cat(df, "banque_sortie")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi("Recettes", fmt_amount(total_recettes, devise), "Chiffre d'affaires")
    with c2:
        render_kpi("Coûts", fmt_amount(total_couts, devise), "Charges totales")
    with c3:
        render_kpi("Marge", fmt_amount(marge, devise), "Résultat opérationnel")
    with c4:
        render_kpi("Solde Caisse", fmt_amount(solde_caisse, devise), "Ouverture incluse")
    with c5:
        render_kpi("Solde Banque", fmt_amount(solde_banque, devise), "Ouverture incluse")

    st.markdown("")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">Évolution mensuelle</div>', unsafe_allow_html=True)
        summary = monthly_summary(df_all, year)
        fig = go.Figure()
        fig.add_bar(name="Recettes", x=summary["Mois"].str[:3], y=summary["Recettes"], marker_color="#22c55e")
        fig.add_bar(name="Coûts", x=summary["Mois"].str[:3], y=summary["Coûts"], marker_color="#ef4444")
        fig.add_scatter(
            name="Marge",
            x=summary["Mois"].str[:3],
            y=summary["Marge"],
            mode="lines+markers",
            line=dict(color="#3b82f6", width=3),
        )
        fig.update_layout(
            barmode="group",
            height=340,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Répartition des coûts</div>', unsafe_allow_html=True)
        cost_map = {
            "Salaires": get_cat(df, "salaire"),
            "Fournitures": get_cat(df, "fourniture"),
            "Mat. Premières": get_cat(df, "matiere_premiere"),
            "Loyer": get_cat(df, "loyer"),
            "Transport": get_cat(df, "transport"),
            "Frais Bancaires": get_cat(df, "frais_bancaires"),
            "Autres": get_cat(df, "autre_cout"),
        }
        cost_df = pd.DataFrame([(k, v) for k, v in cost_map.items() if v > 0], columns=["Catégorie", "Montant"])
        if cost_df.empty:
            st.info("Aucun coût enregistré sur la période.")
        else:
            fig2 = px.pie(
                cost_df,
                names="Catégorie",
                values="Montant",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig2.update_layout(
                height=340,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Dernières opérations</div>', unsafe_allow_html=True)
    if df.empty:
        st.info("Aucune opération enregistrée pour cette période.")
        return

    recent = df.sort_values("date", ascending=False).head(12).copy()
    recent["Date"] = recent["date"].dt.strftime("%d/%m/%Y")
    recent["Catégorie"] = recent["categorie"].map(CAT_LABELS).fillna(recent["categorie"])
    recent["Montant"] = recent["montant"].apply(lambda x: fmt_amount(x, devise))
    st.dataframe(
        recent[["Date", "piece_no", "libelle", "Catégorie", "Montant", "notes"]].rename(
            columns={
                "piece_no": "N° Pièce",
                "libelle": "Libellé",
                "notes": "Notes",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def page_operations(df_all: pd.DataFrame, df: pd.DataFrame, cfg: Dict[str, Any], user_uid: str, year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    collection = user_collection("operations", user_uid)

    st.title("Saisie des Opérations")
    tab1, tab2 = st.tabs(["➕ Nouvelle opération", "📋 Gérer les opérations"])

    with tab1:
        with st.form("form_op", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                op_date = st.date_input("Date", value=date.today())
                op_piece = st.text_input("N° Pièce", placeholder="FAC-001")
            with c2:
                op_cat_label = st.selectbox("Catégorie", list(CATEGORIES.keys()))
                op_montant = st.number_input("Montant", min_value=0.0, step=1000.0)
            with c3:
                op_libelle = st.text_input("Libellé", placeholder="Description de l'opération")
                op_notes = st.text_input("Notes", placeholder="Optionnel")

            submitted = st.form_submit_button("Enregistrer l'opération", type="primary", use_container_width=True)

            if submitted:
                if not op_libelle.strip():
                    st.error("Le libellé est obligatoire.")
                elif op_montant <= 0:
                    st.error("Le montant doit être supérieur à 0.")
                else:
                    payload = {
                        "date": op_date.isoformat(),
                        "piece_no": op_piece.strip(),
                        "libelle": op_libelle.strip(),
                        "categorie": CATEGORIES[op_cat_label],
                        "montant": int(op_montant),
                        "notes": op_notes.strip(),
                        "mois": MOIS[op_date.month - 1],
                        "annee": op_date.year,
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    }
                    ok = fs_create_document(collection, payload)
                    if ok:
                        invalidate_caches()
                        st.success("Opération enregistrée.")
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement.")

    with tab2:
        st.caption(f"Filtre actif : {month} {year}")
        search = st.text_input("🔎 Rechercher", placeholder="Libellé, catégorie, pièce, notes")
        dfd = filter_df(df, None, None, search)

        if dfd.empty:
            st.info("Aucune opération trouvée.")
            return

        dfd = dfd.sort_values("date", ascending=False)
        for _, row in dfd.iterrows():
            label = row["categorie"]
            label = CAT_LABELS.get(label, label)
            title = (
                f"📄 {row['date'].strftime('%d/%m/%Y') if pd.notna(row['date']) else '—'}"
                f" | {row.get('piece_no', '—') or '—'}"
                f" | {row.get('libelle', '')}"
                f" | {label}"
                f" | {fmt_amount(row.get('montant', 0), devise)}"
            )

            with st.expander(title):
                with st.form(f"edit_{row['_id']}"):
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        edit_date = st.date_input(
                            "Date",
                            value=row["date"].date() if pd.notna(row["date"]) else date.today(),
                            key=f"date_{row['_id']}",
                        )
                        edit_piece = st.text_input(
                            "N° Pièce",
                            value=row.get("piece_no", ""),
                            key=f"piece_{row['_id']}",
                        )
                    with e2:
                        cat_keys = list(CATEGORIES.keys())
                        current_label = CAT_LABELS.get(row.get("categorie", ""), cat_keys[0])
                        current_index = cat_keys.index(current_label) if current_label in cat_keys else 0
                        edit_cat_label = st.selectbox(
                            "Catégorie",
                            cat_keys,
                            index=current_index,
                            key=f"cat_{row['_id']}",
                        )
                        edit_montant = st.number_input(
                            "Montant",
                            min_value=0.0,
                            step=1000.0,
                            value=float(row.get("montant", 0) or 0),
                            key=f"montant_{row['_id']}",
                        )
                    with e3:
                        edit_libelle = st.text_input(
                            "Libellé",
                            value=row.get("libelle", ""),
                            key=f"lib_{row['_id']}",
                        )
                        edit_notes = st.text_input(
                            "Notes",
                            value=row.get("notes", ""),
                            key=f"notes_{row['_id']}",
                        )

                    c_save, c_delete = st.columns([3, 1])
                    save_clicked = c_save.form_submit_button("💾 Enregistrer les modifications", type="primary", use_container_width=True)
                    delete_clicked = c_delete.form_submit_button("🗑️ Supprimer", use_container_width=True)

                    if save_clicked:
                        if not edit_libelle.strip():
                            st.error("Le libellé est obligatoire.")
                        elif edit_montant <= 0:
                            st.error("Le montant doit être supérieur à 0.")
                        else:
                            payload = {
                                "date": edit_date.isoformat(),
                                "piece_no": edit_piece.strip(),
                                "libelle": edit_libelle.strip(),
                                "categorie": CATEGORIES[edit_cat_label],
                                "montant": int(edit_montant),
                                "notes": edit_notes.strip(),
                                "mois": MOIS[edit_date.month - 1],
                                "annee": edit_date.year,
                                "asset_family": row.get("asset_family", ""),
                                "useful_life_years": safe_int(row.get("useful_life_years", 0), 0),
                                "created_at": row.get("created_at", now_iso()),
                                "updated_at": now_iso(),
                            }
                            ok = fs_update_document(collection, row["_id"], payload)
                            if ok:
                                invalidate_caches()
                                st.success("Opération mise à jour.")
                                st.rerun()
                            else:
                                st.error("Impossible de mettre à jour l'opération.")

                    if delete_clicked:
                        ok = fs_delete_document(collection, row["_id"])
                        if ok:
                            invalidate_caches()
                            st.success("Opération supprimée.")
                            st.rerun()
                        else:
                            st.error("Suppression impossible pour le moment.")


def page_cash(df: pd.DataFrame, cfg: Dict[str, Any]) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Gestion de Caisse")

    opening = safe_float(cfg.get("solde_initial_caisse", 0), 0)
    table = running_balance_table(df, "caisse_entree", "caisse_sortie", opening, devise)

    entrees = get_cat(df, "caisse_entree")
    sorties = get_cat(df, "caisse_sortie")
    solde = opening + entrees - sorties

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Solde initial", fmt_amount(opening, devise), "Défini dans Paramètres")
    with c2:
        render_kpi("Entrées", fmt_amount(entrees, devise))
    with c3:
        render_kpi("Sorties", fmt_amount(sorties, devise))
    with c4:
        render_kpi("Solde caisse", fmt_amount(solde, devise))

    st.markdown('<div class="section-title">Mouvements de caisse</div>', unsafe_allow_html=True)
    if table.empty:
        st.info("Aucun mouvement de caisse sur la période.")
        return

    st.dataframe(
        table[["Date", "N° Pièce", "Libellé", "Entrée", "Sortie", "Solde"]],
        use_container_width=True,
        hide_index=True,
    )

    fig = go.Figure()
    fig.add_bar(name="Entrées", x=table["Date"], y=table["_entry_num"], marker_color="#22c55e")
    fig.add_bar(name="Sorties", x=table["Date"], y=table["_exit_num"], marker_color="#ef4444")
    fig.add_scatter(name="Solde", x=table["Date"], y=table["_solde_num"], mode="lines+markers", line=dict(color="#3b82f6", width=3))
    fig.update_layout(
        barmode="group",
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)


def page_bank(df: pd.DataFrame, cfg: Dict[str, Any]) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Gestion Banque")

    opening = safe_float(cfg.get("solde_initial_banque", 0), 0)
    table = running_balance_table(df, "banque_entree", "banque_sortie", opening, devise)

    credits = get_cat(df, "banque_entree")
    debits = get_cat(df, "banque_sortie")
    solde = opening + credits - debits

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Solde initial", fmt_amount(opening, devise), "Défini dans Paramètres")
    with c2:
        render_kpi("Crédits", fmt_amount(credits, devise))
    with c3:
        render_kpi("Débits", fmt_amount(debits, devise))
    with c4:
        render_kpi("Solde banque", fmt_amount(solde, devise))

    st.markdown('<div class="section-title">Relevé bancaire</div>', unsafe_allow_html=True)
    if table.empty:
        st.info("Aucun mouvement bancaire sur la période.")
        return

    st.dataframe(
        table[["Date", "N° Pièce", "Libellé", "Entrée", "Sortie", "Solde"]].rename(columns={"Entrée": "Crédit", "Sortie": "Débit"}),
        use_container_width=True,
        hide_index=True,
    )

    fig = go.Figure()
    fig.add_bar(name="Crédits", x=table["Date"], y=table["_entry_num"], marker_color="#22c55e")
    fig.add_bar(name="Débits", x=table["Date"], y=table["_exit_num"], marker_color="#ef4444")
    fig.add_scatter(name="Solde", x=table["Date"], y=table["_solde_num"], mode="lines+markers", line=dict(color="#8b5cf6", width=3))
    fig.update_layout(
        barmode="group",
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)


def page_costs(df_all: pd.DataFrame, df: pd.DataFrame, cfg: Dict[str, Any], year: int) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Coûts & Charges")

    cost_map = {
        "Salaires": get_cat(df, "salaire"),
        "Fournitures & Services": get_cat(df, "fourniture"),
        "Matières Premières": get_cat(df, "matiere_premiere"),
        "Loyer": get_cat(df, "loyer"),
        "Transport": get_cat(df, "transport"),
        "Frais Bancaires": get_cat(df, "frais_bancaires"),
        "Autres Charges": get_cat(df, "autre_cout"),
    }
    total_cost = sum(cost_map.values())

    c1, c2 = st.columns([1.1, 1])

    with c1:
        st.markdown('<div class="section-title">Détail des charges</div>', unsafe_allow_html=True)
        if total_cost <= 0:
            st.info("Aucune charge enregistrée.")
        else:
            for label, value in cost_map.items():
                pct = value / total_cost if total_cost else 0
                a, b = st.columns([3, 1])
                with a:
                    st.markdown(f"**{label}**")
                    st.progress(float(pct))
                with b:
                    st.markdown(f"<div style='text-align:right;padding-top:.4rem'>{fmt_amount(value, devise)}</div>", unsafe_allow_html=True)

            st.markdown(f"### Total charges : {fmt_amount(total_cost, devise)}")

    with c2:
        st.markdown('<div class="section-title">Répartition</div>', unsafe_allow_html=True)
        pie_df = pd.DataFrame([(k, v) for k, v in cost_map.items() if v > 0], columns=["Catégorie", "Montant"])
        if pie_df.empty:
            st.info("Aucune donnée à représenter.")
        else:
            fig = px.pie(pie_df, names="Catégorie", values="Montant", hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Détail des opérations de charges</div>', unsafe_allow_html=True)
    df_costs = df[df["categorie"].isin(CAT_COSTS)].copy()
    if df_costs.empty:
        st.info("Aucune charge enregistrée pour cette période.")
    else:
        df_costs["Date"] = df_costs["date"].dt.strftime("%d/%m/%Y")
        df_costs["Catégorie"] = df_costs["categorie"].map(CAT_LABELS).fillna(df_costs["categorie"])
        df_costs["Montant"] = df_costs["montant"].apply(lambda x: fmt_amount(x, devise))
        st.dataframe(
            df_costs[["Date", "piece_no", "libelle", "Catégorie", "Montant", "notes"]].rename(
                columns={"piece_no": "N° Pièce", "libelle": "Libellé", "notes": "Notes"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown('<div class="section-title">Évolution mensuelle des charges</div>', unsafe_allow_html=True)
    df_year = filter_df(df_all, year, None)
    evol_rows = []
    for m in MOIS:
        dm = df_year[df_year["mois"] == m]
        evol_rows.append({
            "Mois": m[:3],
            "Salaires": get_cat(dm, "salaire"),
            "Fournitures": get_cat(dm, "fourniture"),
            "Mat. Premières": get_cat(dm, "matiere_premiere"),
            "Autres": get_cat(dm, "loyer", "transport", "frais_bancaires", "autre_cout"),
        })
    evol_df = pd.DataFrame(evol_rows)

    fig2 = px.bar(
        evol_df,
        x="Mois",
        y=["Salaires", "Fournitures", "Mat. Premières", "Autres"],
        barmode="stack",
        color_discrete_sequence=["#ef4444", "#f97316", "#eab308", "#94a3b8"],
    )
    fig2.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig2, use_container_width=True)


def page_investments(df_all: pd.DataFrame, cfg: Dict[str, Any], user_uid: str, year: int) -> None:
    devise = cfg.get("devise", "FCFA")
    collection = user_collection("operations", user_uid)

    st.title("Investissements")
    df_inv = df_all[df_all["categorie"] == "investissement"].copy()

    total_inv = get_cat(df_inv, "investissement")
    schedule = build_depreciation_schedule(df_all, year, devise)
    annual_dep = schedule["_annual_dep"].sum() if not schedule.empty and "_annual_dep" in schedule.columns else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Total investi", fmt_amount(total_inv, devise))
    with c2:
        render_kpi("Nb. d'acquisitions", str(len(df_inv)))
    with c3:
        render_kpi("Amortissement annuel", fmt_amount(annual_dep, devise))

    tab1, tab2 = st.tabs(["📋 Liste des investissements", "📉 Amortissements"])

    with tab1:
        with st.form("form_inv", clear_on_submit=True):
            st.markdown("#### Ajouter un investissement")
            c1, c2, c3 = st.columns(3)

            with c1:
                inv_date = st.date_input("Date", value=date.today())
                inv_libelle = st.text_input("Désignation", placeholder="Ordinateur portable")
            with c2:
                inv_montant = st.number_input("Coût d'acquisition", min_value=0.0, step=5000.0)
                asset_family = st.selectbox("Famille d'actif", list(INVESTMENT_LIVES.keys()))
            with c3:
                inv_piece = st.text_input("N° Pièce")
                inv_notes = st.text_input("Notes")

            useful_life = INVESTMENT_LIVES[asset_family]
            st.caption(f"Durée d'amortissement proposée : {useful_life} ans")

            submit = st.form_submit_button("Enregistrer", type="primary")
            if submit:
                if not inv_libelle.strip():
                    st.error("La désignation est obligatoire.")
                elif inv_montant <= 0:
                    st.error("Le coût doit être supérieur à 0.")
                else:
                    payload = {
                        "date": inv_date.isoformat(),
                        "piece_no": inv_piece.strip(),
                        "libelle": inv_libelle.strip(),
                        "categorie": "investissement",
                        "montant": int(inv_montant),
                        "notes": inv_notes.strip(),
                        "mois": MOIS[inv_date.month - 1],
                        "annee": inv_date.year,
                        "asset_family": asset_family,
                        "useful_life_years": useful_life,
                        "created_at": now_iso(),
                        "updated_at": now_iso(),
                    }
                    ok = fs_create_document(collection, payload)
                    if ok:
                        invalidate_caches()
                        st.success("Investissement enregistré.")
                        st.rerun()
                    else:
                        st.error("Enregistrement impossible pour le moment.")

        if df_inv.empty:
            st.info("Aucun investissement enregistré.")
        else:
            view = df_inv.copy()
            view["Date"] = view["date"].dt.strftime("%d/%m/%Y")
            view["Famille"] = view["asset_family"].replace("", "Investissement")
            view["Montant"] = view["montant"].apply(lambda x: fmt_amount(x, devise))
            st.dataframe(
                view[["Date", "piece_no", "libelle", "Famille", "Montant", "notes"]].rename(
                    columns={
                        "piece_no": "N° Pièce",
                        "libelle": "Désignation",
                        "notes": "Notes",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with tab2:
        st.markdown('<div class="section-title">Table des amortissements</div>', unsafe_allow_html=True)
        if schedule.empty:
            st.info("Aucune immobilisation à amortir.")
        else:
            st.dataframe(
                schedule.drop(columns=["_annual_dep"]),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown('<div class="section-title">Durées de référence</div>', unsafe_allow_html=True)
        ref_df = pd.DataFrame(
            [(label, f"{years} ans") for label, years in INVESTMENT_LIVES.items()],
            columns=["Bien", "Durée"],
        )
        st.dataframe(ref_df, use_container_width=True, hide_index=True)


def page_income_statement(df: pd.DataFrame, cfg: Dict[str, Any], year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Compte de Résultat")
    st.caption(f"Période : {month} {year}")

    data = compute_income_statement(df, cfg)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("CA", fmt_amount(data["ca"], devise))
    with c2:
        render_kpi("Marge brute", fmt_amount(data["marge_brute"], devise))
    with c3:
        render_kpi("Résultat net", fmt_amount(data["resultat_net"], devise))
    with c4:
        render_kpi("Cash flow", fmt_amount(data["cash_flow"], devise))

    rows = [
        ("Chiffre d'Affaires", data["ca"]),
        ("Achats de Matières Premières", -data["achats_mat"]),
        ("Marge Brute", data["marge_brute"]),
        ("Fournitures & Services", -data["fournitures"]),
        ("Loyer", -data["loyer"]),
        ("Transport", -data["transport"]),
        ("Frais Bancaires", -data["frais_banc"]),
        ("Autres Charges", -data["autres"]),
        ("Salaires", -data["salaires"]),
        ("Dotations aux Amortissements", -data["dep_amort"]),
        ("Résultat Brut", data["resultat_brut"]),
        (f"Impôt sur le Résultat ({int(data['taux_is'] * 100)}%)", -data["impot"]),
        ("Résultat Net", data["resultat_net"]),
        ("Cash Flow", data["cash_flow"]),
    ]
    cr_df = pd.DataFrame(rows, columns=["Rubrique", "Montant"])
    cr_df["Montant"] = cr_df["Montant"].apply(lambda x: fmt_amount(x, devise))

    col1, col2 = st.columns([1.25, 1])

    with col1:
        st.markdown('<div class="section-title">Compte de résultat</div>', unsafe_allow_html=True)
        st.dataframe(cr_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown('<div class="section-title">Synthèse visuelle</div>', unsafe_allow_html=True)
        chart_df = pd.DataFrame({
            "Indicateur": ["CA", "Marge brute", "Résultat brut", "Résultat net", "Cash flow"],
            "Valeur": [
                data["ca"],
                data["marge_brute"],
                data["resultat_brut"],
                data["resultat_net"],
                data["cash_flow"],
            ]
        })
        fig = go.Figure(go.Bar(
            x=chart_df["Indicateur"],
            y=chart_df["Valeur"],
            marker_color=["#22c55e", "#3b82f6", "#f97316", "#22c55e" if data["resultat_net"] >= 0 else "#ef4444", "#8b5cf6"],
        ))
        fig.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        margin_pct = (data["resultat_net"] / data["ca"] * 100) if data["ca"] > 0 else 0.0
        state_class = "state-ok" if margin_pct >= 0 else "state-bad"
        st.markdown(
            f"<div class='{state_class}'>Rentabilité nette : {margin_pct:.1f}%</div>",
            unsafe_allow_html=True,
        )


def page_balance_sheet(df_all: pd.DataFrame, cfg: Dict[str, Any], user_uid: str, year: int) -> None:
    devise = cfg.get("devise", "FCFA")
    collection = user_collection("bilan_items", user_uid)
    existing_items = load_bilan_items(user_uid)
    saved = {item.get("key"): safe_float(item.get("value"), 0) for item in existing_items}

    st.title("Bilan Comptable")
    st.caption("Les rubriques manuelles sont sauvegardées dans Firebase.")

    values: Dict[str, float] = {}
    tab_actif, tab_passif = st.tabs(["📦 Actif", "💼 Passif"])

    with tab_actif:
        st.markdown("#### Actif immobilisé")
        c1, c2 = st.columns(2)
        with c1:
            values["immo_incorp"] = st.number_input("Immobilisations Incorporelles", value=float(saved.get("immo_incorp", 0)), step=1000.0)
            values["immo_corp"] = st.number_input("Matériel & Équipements", value=float(saved.get("immo_corp", 0)), step=1000.0)
        with c2:
            values["mobilier"] = st.number_input("Mobilier de Bureau", value=float(saved.get("mobilier", 0)), step=1000.0)
            values["immo_fin"] = st.number_input("Immobilisations Financières", value=float(saved.get("immo_fin", 0)), step=1000.0)

        total_immo = values["immo_incorp"] + values["immo_corp"] + values["mobilier"] + values["immo_fin"]
        st.success(f"Total Actif Immobilisé : {fmt_amount(total_immo, devise)}")

        st.markdown("#### Actif circulant")
        c1, c2 = st.columns(2)
        with c1:
            values["stocks"] = st.number_input("Stocks", value=float(saved.get("stocks", 0)), step=1000.0)
        with c2:
            values["creances"] = st.number_input("Créances Clients", value=float(saved.get("creances", 0)), step=1000.0)

        total_circ = values["stocks"] + values["creances"]
        st.success(f"Total Actif Circulant : {fmt_amount(total_circ, devise)}")

        df_year = filter_df(df_all, year, None)
        solde_caisse = safe_float(cfg.get("solde_initial_caisse", 0), 0) + get_cat(df_year, "caisse_entree") - get_cat(df_year, "caisse_sortie")
        solde_banque = safe_float(cfg.get("solde_initial_banque", 0), 0) + get_cat(df_year, "banque_entree") - get_cat(df_year, "banque_sortie")

        st.info(f"Caisse calculée : {fmt_amount(solde_caisse, devise)} | Banque calculée : {fmt_amount(solde_banque, devise)}")
        total_actif = total_immo + total_circ + solde_caisse + solde_banque
        st.markdown(f"### Total Actif : {fmt_amount(total_actif, devise)}")

    with tab_passif:
        st.markdown("#### Capitaux propres")
        c1, c2 = st.columns(2)
        with c1:
            values["capital"] = st.number_input("Capital Social", value=float(saved.get("capital", 0)), step=1000.0)
            values["reserves"] = st.number_input("Réserves & Report à Nouveau", value=float(saved.get("reserves", 0)), step=1000.0)
        with c2:
            result_net = compute_income_statement(filter_df(df_all, year, None), cfg)["resultat_net"]
            st.info(f"Résultat net calculé : {fmt_amount(result_net, devise)}")

        total_cp = values["capital"] + values["reserves"] + result_net
        st.success(f"Total Capitaux Propres : {fmt_amount(total_cp, devise)}")

        st.markdown("#### Dettes")
        c1, c2, c3 = st.columns(3)
        with c1:
            values["dettes_mlt"] = st.number_input("Emprunts MLT", value=float(saved.get("dettes_mlt", 0)), step=1000.0)
        with c2:
            values["dettes_fourn"] = st.number_input("Dettes Fournisseurs", value=float(saved.get("dettes_fourn", 0)), step=1000.0)
        with c3:
            values["dettes_fisc"] = st.number_input("Dettes Fiscales & Sociales", value=float(saved.get("dettes_fisc", 0)), step=1000.0)

        total_dettes = values["dettes_mlt"] + values["dettes_fourn"] + values["dettes_fisc"]
        total_passif = total_cp + total_dettes
        st.markdown(f"### Total Passif : {fmt_amount(total_passif, devise)}")

        ecart = total_actif - total_passif
        if abs(ecart) < 1:
            st.success("✅ Bilan équilibré")
        else:
            st.warning(f"Écart Actif - Passif : {fmt_amount(ecart, devise)}")

    if st.button("💾 Sauvegarder le bilan", type="primary"):
        ok = upsert_key_value_items(collection, existing_items, values)
        if ok:
            st.success("Bilan sauvegardé.")
        else:
            st.error("Impossible de sauvegarder le bilan.")


def page_monthly_close(df_all: pd.DataFrame, cfg: Dict[str, Any], year: int) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Clôture & Synthèse Mensuelle")

    summary = monthly_summary(df_all, year).copy()
    summary["Salaires"] = 0.0
    summary["Fournitures"] = 0.0
    summary["Mat. Prem."] = 0.0
    summary["Autres Chg."] = 0.0

    df_year = filter_df(df_all, year, None)
    for idx, month in enumerate(MOIS):
        dm = df_year[df_year["mois"] == month]
        summary.loc[idx, "Salaires"] = get_cat(dm, "salaire")
        summary.loc[idx, "Fournitures"] = get_cat(dm, "fourniture")
        summary.loc[idx, "Mat. Prem."] = get_cat(dm, "matiere_premiere")
        summary.loc[idx, "Autres Chg."] = get_cat(dm, "loyer", "transport", "frais_bancaires", "autre_cout")

    display = summary.copy()
    total_row = {"Mois": "TOTAL"}
    for col in display.columns[1:]:
        total_row[col] = display[col].sum()
    display = pd.concat([display, pd.DataFrame([total_row])], ignore_index=True)

    for col in display.columns[1:]:
        display[col] = display[col].apply(lambda x: fmt_amount(x, devise) if isinstance(x, (int, float)) else x)

    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Évolution CA & Coûts</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_bar(name="Recettes", x=summary["Mois"].str[:3], y=summary["Recettes"], marker_color="#22c55e")
    fig.add_bar(name="Coûts", x=summary["Mois"].str[:3], y=summary["Coûts"], marker_color="#ef4444")
    fig.add_scatter(name="Marge", x=summary["Mois"].str[:3], y=summary["Marge"], mode="lines+markers", line=dict(color="#3b82f6", width=3))
    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)

    export_df = monthly_summary(df_all, year)
    csv = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Exporter la synthèse mensuelle",
        data=csv,
        file_name=f"cloture_mensuelle_{year}.csv",
        mime="text/csv",
    )


def page_budget(df_all: pd.DataFrame, cfg: Dict[str, Any], user_uid: str, year: int) -> None:
    devise = cfg.get("devise", "FCFA")
    collection = user_collection("budget_items", user_uid)
    existing_items = load_budget_items(user_uid)
    saved = {item.get("key"): safe_float(item.get("value"), 0) for item in existing_items}

    st.title("Budget Prévisionnel")
    values: Dict[str, float] = {}

    st.markdown("### Recettes prévisionnelles")
    cols = st.columns(3)
    for i, (label, key) in enumerate(BUDGET_REVENUE_FIELDS):
        with cols[i % 3]:
            values[key] = st.number_input(label, value=float(saved.get(key, 0)), step=10000.0, key=f"budget_{key}")

    total_rec = sum(values[key] for _, key in BUDGET_REVENUE_FIELDS)

    st.markdown("### Dépenses prévisionnelles")
    cols = st.columns(3)
    for i, (label, key) in enumerate(BUDGET_EXPENSE_FIELDS):
        with cols[i % 3]:
            values[key] = st.number_input(label, value=float(saved.get(key, 0)), step=10000.0, key=f"budget_{key}")

    total_dep = sum(values[key] for _, key in BUDGET_EXPENSE_FIELDS)
    treso_finale = total_rec - total_dep

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Recettes prévues", fmt_amount(total_rec, devise))
    with c2:
        render_kpi("Dépenses prévues", fmt_amount(total_dep, devise))
    with c3:
        render_kpi("Trésorerie finale prévue", fmt_amount(treso_finale, devise))

    st.markdown('<div class="section-title">Réel vs budget</div>', unsafe_allow_html=True)
    df_year = filter_df(df_all, year, None)

    reel_rec = get_cat(df_year, "recette")
    reel_costs = get_cat(df_year, *CAT_COSTS)
    reel_invest = get_cat(df_year, "investissement")

    budget_operating_expenses = (
        total_dep
        - values.get("b_d_invest", 0)
        - values.get("b_d_remb", 0)
        - values.get("b_d_impots", 0)
        - values.get("b_d_amort", 0)
    )

    comp_df = pd.DataFrame({
        "Catégorie": ["Recettes", "Charges d'exploitation", "Investissements", "Marge"],
        "Budget": [
            values.get("b_ca", 0),
            budget_operating_expenses,
            values.get("b_d_invest", 0),
            values.get("b_ca", 0) - budget_operating_expenses,
        ],
        "Réel": [
            reel_rec,
            reel_costs,
            reel_invest,
            reel_rec - reel_costs,
        ],
    })
    comp_df["Écart"] = comp_df["Réel"] - comp_df["Budget"]
    comp_df["Écart %"] = comp_df.apply(
        lambda r: round((r["Écart"] / r["Budget"] * 100), 1) if r["Budget"] else 0.0,
        axis=1,
    )

    view = comp_df.copy()
    for col in ["Budget", "Réel", "Écart"]:
        view[col] = view[col].apply(lambda x: fmt_amount(x, devise))
    view["Écart %"] = view["Écart %"].astype(str) + " %"
    st.dataframe(view, use_container_width=True, hide_index=True)

    fig = go.Figure()
    fig.add_bar(name="Budget", x=comp_df["Catégorie"], y=comp_df["Budget"], marker_color="#94a3b8")
    fig.add_bar(name="Réel", x=comp_df["Catégorie"], y=comp_df["Réel"], marker_color="#3b82f6")
    fig.update_layout(
        barmode="group",
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, use_container_width=True)

    if st.button("💾 Sauvegarder le budget", type="primary"):
        ok = upsert_key_value_items(collection, existing_items, values)
        if ok:
            st.success("Budget sauvegardé.")
        else:
            st.error("Impossible de sauvegarder le budget.")


def page_settings(df_all: pd.DataFrame, cfg: Dict[str, Any], user_uid: str) -> None:
    st.title("Paramètres de l'Entreprise")

    with st.form("form_config"):
        c1, c2 = st.columns(2)

        with c1:
            nom = st.text_input("Nom de l'entreprise", value=cfg.get("nom", ""))
            adresse = st.text_input("Adresse", value=cfg.get("adresse", ""))
            tel = st.text_input("Téléphone", value=cfg.get("tel", ""))
            solde_initial_caisse = st.number_input(
                "Solde initial caisse",
                value=float(cfg.get("solde_initial_caisse", 0)),
                step=1000.0,
            )

        with c2:
            rc = st.text_input("RC / NINEA", value=cfg.get("rc", ""))
            email = st.text_input("Email", value=cfg.get("email", ""))
            banque = st.text_input("Banque domiciliataire", value=cfg.get("banque", ""))
            solde_initial_banque = st.number_input(
                "Solde initial banque",
                value=float(cfg.get("solde_initial_banque", 0)),
                step=1000.0,
            )

        devise = st.selectbox("Devise", ["FCFA", "EUR", "USD"], index=["FCFA", "EUR", "USD"].index(cfg.get("devise", "FCFA")))
        taux_is = st.slider("Taux IS (%)", 0, 40, int(safe_float(cfg.get("taux_is", 30), 30)))

        submitted = st.form_submit_button("💾 Sauvegarder", type="primary")
        if submitted:
            ok = save_company_config(
                user_uid,
                {
                    "nom": nom.strip(),
                    "adresse": adresse.strip(),
                    "tel": tel.strip(),
                    "rc": rc.strip(),
                    "email": email.strip(),
                    "banque": banque.strip(),
                    "devise": devise,
                    "taux_is": taux_is,
                    "solde_initial_caisse": solde_initial_caisse,
                    "solde_initial_banque": solde_initial_banque,
                },
            )
            if ok:
                st.success("Paramètres sauvegardés.")
                st.rerun()
            else:
                st.error("Impossible de sauvegarder les paramètres.")

    st.markdown("---")
    st.markdown("### Données")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Actualiser le cache"):
            invalidate_caches()
            st.success("Cache actualisé.")

    with col2:
        if not df_all.empty:
            csv = df_all.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 Exporter toutes les données",
                data=csv,
                file_name=f"journal_pme_{datetime.utcnow().year}.csv",
                mime="text/csv",
            )

    st.markdown(f"**Total opérations en base :** {len(df_all)}")
    st.markdown(f"**Firebase Project :** `{FIREBASE_PROJECT_ID}`")


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    init_session_state()
    inject_css()
    require_backend_config()
    restore_user_from_session()

    if not current_user():
        show_auth_page()

    user = current_user()
    user_uid = user["uid"]

    df_all = load_operations(user_uid)
    cfg = load_company_config(user_uid)
    page, annee_filtre, mois_filtre = render_sidebar(cfg, user, df_all)
    df = filter_df(df_all, annee_filtre, mois_filtre)

    if page == "🏠 Tableau de Bord":
        page_dashboard(df_all, df, cfg, annee_filtre, mois_filtre)

    elif page == "📝 Saisie des Opérations":
        page_operations(df_all, df, cfg, user_uid, annee_filtre, mois_filtre)

    elif page == "💵 Caisse":
        page_cash(df, cfg)

    elif page == "🏦 Banque":
        page_bank(df, cfg)

    elif page == "📊 Coûts & Charges":
        page_costs(df_all, df, cfg, annee_filtre)

    elif page == "🏗️ Investissements":
        page_investments(df_all, cfg, user_uid, annee_filtre)

    elif page == "📈 Compte de Résultat":
        page_income_statement(df, cfg, annee_filtre, mois_filtre)

    elif page == "⚖️ Bilan":
        page_balance_sheet(df_all, cfg, user_uid, annee_filtre)

    elif page == "📅 Clôture Mensuelle":
        page_monthly_close(df_all, cfg, annee_filtre)

    elif page == "🎯 Budget Prévisionnel":
        page_budget(df_all, cfg, user_uid, annee_filtre)

    elif page == "⚙️ Paramètres":
        page_settings(df_all, cfg, user_uid)


if __name__ == "__main__":
    main()
