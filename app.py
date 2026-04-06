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
from streamlit_cookies_controller import CookieController


st.set_page_config(
    page_title="Journal Comptable PME - Partie Double",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)

MOIS = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

DEFAULT_CONFIG = {
    "nom": "Mon Entreprise",
    "adresse": "",
    "tel": "",
    "rc": "",
    "email": "",
    "banque": "",
    "devise": "FCFA",
    "taux_is": 30.0,
    "solde_initial_caisse": 0.0,
    "solde_initial_banque": 0.0,
}

DEFAULT_ACCOUNTS = [
    {"code": "101", "label": "Capital social", "statement_group": "equity", "normal_side": "credit"},
    {"code": "164", "label": "Emprunts", "statement_group": "liability", "normal_side": "credit"},
    {"code": "221", "label": "Bâtiments", "statement_group": "asset", "normal_side": "debit"},
    {"code": "2183", "label": "Matériel informatique", "statement_group": "asset", "normal_side": "debit"},
    {"code": "2184", "label": "Mobilier de bureau", "statement_group": "asset", "normal_side": "debit"},
    {"code": "241", "label": "Matériel et outillage", "statement_group": "asset", "normal_side": "debit"},
    {"code": "245", "label": "Matériel de transport", "statement_group": "asset", "normal_side": "debit"},
    {"code": "28183", "label": "Amort. matériel informatique", "statement_group": "contra_asset", "normal_side": "credit"},
    {"code": "28184", "label": "Amort. mobilier de bureau", "statement_group": "contra_asset", "normal_side": "credit"},
    {"code": "28221", "label": "Amort. bâtiments", "statement_group": "contra_asset", "normal_side": "credit"},
    {"code": "2841", "label": "Amort. matériel et outillage", "statement_group": "contra_asset", "normal_side": "credit"},
    {"code": "2845", "label": "Amort. matériel de transport", "statement_group": "contra_asset", "normal_side": "credit"},
    {"code": "401", "label": "Fournisseurs", "statement_group": "liability", "normal_side": "credit"},
    {"code": "411", "label": "Clients", "statement_group": "asset", "normal_side": "debit"},
    {"code": "431", "label": "Organismes sociaux", "statement_group": "liability", "normal_side": "credit"},
    {"code": "441", "label": "État - impôts et taxes", "statement_group": "liability", "normal_side": "credit"},
    {"code": "57", "label": "Caisse", "statement_group": "asset", "normal_side": "debit"},
    {"code": "521", "label": "Banque", "statement_group": "asset", "normal_side": "debit"},
    {"code": "601", "label": "Achats de matières premières", "statement_group": "expense", "normal_side": "debit"},
    {"code": "602", "label": "Fournitures et services extérieurs", "statement_group": "expense", "normal_side": "debit"},
    {"code": "613", "label": "Transport", "statement_group": "expense", "normal_side": "debit"},
    {"code": "614", "label": "Loyer", "statement_group": "expense", "normal_side": "debit"},
    {"code": "631", "label": "Frais bancaires", "statement_group": "expense", "normal_side": "debit"},
    {"code": "641", "label": "Salaires", "statement_group": "expense", "normal_side": "debit"},
    {"code": "671", "label": "Autres charges", "statement_group": "expense", "normal_side": "debit"},
    {"code": "681", "label": "Dotations aux amortissements", "statement_group": "expense", "normal_side": "debit"},
    {"code": "701", "label": "Ventes / Prestations", "statement_group": "revenue", "normal_side": "credit"},
    {"code": "758", "label": "Autres produits", "statement_group": "revenue", "normal_side": "credit"},
]

ASSET_CATALOG = {
    "Bâtiment": {
        "asset_account": "221",
        "asset_label": "Bâtiments",
        "depr_account": "28221",
        "depr_label": "Amort. bâtiments",
        "expense_account": "681",
        "expense_label": "Dotations aux amortissements",
        "life_years": 25,
    },
    "Matériel informatique": {
        "asset_account": "2183",
        "asset_label": "Matériel informatique",
        "depr_account": "28183",
        "depr_label": "Amort. matériel informatique",
        "expense_account": "681",
        "expense_label": "Dotations aux amortissements",
        "life_years": 4,
    },
    "Mobilier de bureau": {
        "asset_account": "2184",
        "asset_label": "Mobilier de bureau",
        "depr_account": "28184",
        "depr_label": "Amort. mobilier de bureau",
        "expense_account": "681",
        "expense_label": "Dotations aux amortissements",
        "life_years": 7,
    },
    "Matériel et outillage": {
        "asset_account": "241",
        "asset_label": "Matériel et outillage",
        "depr_account": "2841",
        "depr_label": "Amort. matériel et outillage",
        "expense_account": "681",
        "expense_label": "Dotations aux amortissements",
        "life_years": 7,
    },
    "Matériel de transport": {
        "asset_account": "245",
        "asset_label": "Matériel de transport",
        "depr_account": "2845",
        "depr_label": "Amort. matériel de transport",
        "expense_account": "681",
        "expense_label": "Dotations aux amortissements",
        "life_years": 4,
    },
}

GUIDED_TEMPLATES = [
    "Vente encaissée en caisse",
    "Vente encaissée en banque",
    "Dépense payée par caisse",
    "Dépense payée par banque",
    "Virement caisse vers banque",
    "Virement banque vers caisse",
    "Encaissement client en caisse",
    "Encaissement client en banque",
    "Paiement fournisseur par caisse",
    "Paiement fournisseur par banque",
    "Achat d'immobilisation payé en caisse",
    "Achat d'immobilisation payé en banque",
]

NATURE_MAP = {
    "💰 Vente / Prestation": {
        "payment_options": ["💵 Caisse", "🏦 Banque"],
        "templates": {
            "💵 Caisse": "Vente encaissée en caisse",
            "🏦 Banque": "Vente encaissée en banque",
        },
    },
    "💸 Dépense / Charge": {
        "payment_options": ["💵 Caisse", "🏦 Banque"],
        "templates": {
            "💵 Caisse": "Dépense payée par caisse",
            "🏦 Banque": "Dépense payée par banque",
        },
    },
    "🔄 Virement interne": {
        "payment_options": ["Caisse → Banque", "Banque → Caisse"],
        "templates": {
            "Caisse → Banque": "Virement caisse vers banque",
            "Banque → Caisse": "Virement banque vers caisse",
        },
    },
    "👤 Encaissement client": {
        "payment_options": ["💵 Caisse", "🏦 Banque"],
        "templates": {
            "💵 Caisse": "Encaissement client en caisse",
            "🏦 Banque": "Encaissement client en banque",
        },
    },
    "🏢 Paiement fournisseur": {
        "payment_options": ["💵 Caisse", "🏦 Banque"],
        "templates": {
            "💵 Caisse": "Paiement fournisseur par caisse",
            "🏦 Banque": "Paiement fournisseur par banque",
        },
    },
    "🏗️ Achat d'immobilisation": {
        "payment_options": ["💵 Caisse", "🏦 Banque"],
        "templates": {
            "💵 Caisse": "Achat d'immobilisation payé en caisse",
            "🏦 Banque": "Achat d'immobilisation payé en banque",
        },
    },
}



def get_runtime_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


FIREBASE_API_KEY = get_runtime_setting("FIREBASE_API_KEY")
FIREBASE_PROJECT_ID = get_runtime_setting("FIREBASE_PROJECT_ID")
FIRESTORE_BASE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"
    if FIREBASE_PROJECT_ID else ""
)


def init_session_state() -> None:
    if "cookie_controller" not in st.session_state:
        st.session_state["cookie_controller"] = CookieController()
        
    ctrl = st.session_state["cookie_controller"]
    defaults = {
        "backend_status": "",
        "auth_error": "",
        "firebase_id_token": ctrl.get("firebase_id_token") or "",
        "firebase_refresh_token": ctrl.get("firebase_refresh_token") or "",
        "firebase_token_expires_at": safe_float(ctrl.get("firebase_token_expires_at"), 0.0),
        "user": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
        elif "token" in key and st.session_state[key] == "":
            st.session_state[key] = value


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.5rem; 
            padding-bottom: 3rem;
        }
        /* --- SIDEBAR SOMBRE --- */
        [data-testid="stSidebar"] {
            background-color: #0f172a !important;
            border-right: 1px solid #1e293b;
        }
        /* Textes génériques et labels dans la sidebar */
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] > p,
        [data-testid="stSidebar"] label {
            color: #f8fafc !important;
        }
        /* Style spécifique pour le bouton Se Déconnecter ou autres boutons dans la sidebar */
        [data-testid="stSidebar"] button {
            background-color: #1e293b !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        [data-testid="stSidebar"] button:hover {
            border-color: #94a3b8 !important;
            background-color: #334155 !important;
            color: #ffffff !important;
        }
        /* Garder le texte du selectbox lisible (s'il s'affiche en blanc sur fond blanc) */
        [data-testid="stSidebar"] div[data-baseweb="select"] * {
            color: #0f172a !important;
        }
        
        /* --- CARTES TABLEAU DE BORD --- */
        .app-card {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            height: 100%;
            transition: all 0.2s ease;
        }
        .app-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.1);
        }
        .app-card .kpi-label {
            color: var(--text-color);
            opacity: 0.75;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }
        .app-card .kpi-value {
            color: var(--text-color);
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.2;
        }
        .app-card .kpi-sub {
            color: var(--text-color);
            opacity: 0.55;
            font-size: 0.85rem;
            margin-top: 0.4rem;
        }
        .section-title {
            margin-top: 1rem; 
            margin-bottom: 1rem; 
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--secondary-background-color);
            color: var(--text-color); 
            font-size: 1.1rem; 
            font-weight: 700;
            text-transform: uppercase; 
            letter-spacing: 0.05em;
        }
        .state-ok {
            background: rgba(34, 197, 94, 0.2); 
            color: var(--text-color); 
            padding: 0.3rem 0.7rem;
            border-radius: 999px; 
            font-weight: 600; 
            font-size: 0.85rem;
        }
        .state-bad {
            background: rgba(239, 68, 68, 0.2); 
            color: var(--text-color); 
            padding: 0.3rem 0.7rem;
            border-radius: 999px; 
            font-weight: 600; 
            font-size: 0.85rem;
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


def require_backend_config() -> None:
    if not FIREBASE_API_KEY or not FIREBASE_PROJECT_ID:
        st.error(
            "Configuration Firebase manquante. Ajoute FIREBASE_API_KEY et FIREBASE_PROJECT_ID "
            "dans st.secrets ou dans les variables d'environnement."
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


def fmt_amount(n: Any, devise: str = "FCFA") -> str:
    try:
        return f"{int(round(float(n))):,} {devise}".replace(",", " ")
    except Exception:
        return f"0 {devise}"


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
    return f"users/{uid}/{name}" if uid else name


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
    ctrl = st.session_state.get("cookie_controller")
    st.session_state["user"] = None
    st.session_state["firebase_id_token"] = ""
    st.session_state["firebase_refresh_token"] = ""
    st.session_state["firebase_token_expires_at"] = 0.0
    st.session_state["auth_error"] = ""
    if ctrl:
        ctrl.remove("firebase_id_token")
        ctrl.remove("firebase_refresh_token")
        ctrl.remove("firebase_token_expires_at")


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
    
    ctrl = st.session_state.get("cookie_controller")
    if ctrl:
        ctrl.set("firebase_id_token", st.session_state["firebase_id_token"])
        ctrl.set("firebase_refresh_token", st.session_state["firebase_refresh_token"])
        ctrl.set("firebase_token_expires_at", str(st.session_state["firebase_token_expires_at"]))



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
        new_id = data.get("id_token", "")
        new_ref = data.get("refresh_token", refresh_token)
        new_exp = time.time() + int(data.get("expires_in", 3600))
        
        st.session_state["firebase_id_token"] = new_id
        st.session_state["firebase_refresh_token"] = new_ref
        st.session_state["firebase_token_expires_at"] = new_exp
        
        ctrl = st.session_state.get("cookie_controller")
        if ctrl:
            ctrl.set("firebase_id_token", new_id)
            ctrl.set("firebase_refresh_token", new_ref)
            ctrl.set("firebase_token_expires_at", str(new_exp))
            
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
        {"email": normalize_email(email), "password": password, "returnSecureToken": True},
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
        {"email": normalize_email(email), "password": password, "returnSecureToken": True},
    )
    if error:
        return None, error
    id_token = data.get("idToken", "")
    if display_name.strip():
        update_data, update_error = firebase_identity_request(
            "accounts:update",
            {"idToken": id_token, "displayName": display_name.strip(), "returnSecureToken": True},
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
        if response is None or response.status_code == 404:
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


def normalize_df(df: pd.DataFrame, defaults: Dict[str, Any]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame([defaults]).iloc[0:0]
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    return df


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


@st.cache_data(ttl=30, show_spinner=False)
def load_accounts(user_uid: str) -> pd.DataFrame:
    docs = fs_list_documents(user_collection("accounts", user_uid))
    df = pd.DataFrame(docs)
    defaults = {
        "_id": "", "code": "", "label": "", "statement_group": "", "normal_side": "debit"
    }
    df = normalize_df(df, defaults)
    if not df.empty:
        for col in ["code", "label", "statement_group", "normal_side"]:
            df[col] = df[col].fillna("").astype(str)
        df = df.sort_values("code").reset_index(drop=True)
    return df


def ensure_default_accounts(user_uid: str) -> None:
    current = fs_list_documents(user_collection("accounts", user_uid))
    if current:
        return
    for acc in DEFAULT_ACCOUNTS:
        fs_create_document(user_collection("accounts", user_uid), acc, doc_id=acc["code"])
    invalidate_caches()


@st.cache_data(ttl=30, show_spinner=False)
def load_entries(user_uid: str) -> pd.DataFrame:
    docs = fs_list_documents(user_collection("entries", user_uid))
    df = pd.DataFrame(docs)
    defaults = {
        "_id": "", "entry_id": "", "date": None, "piece_no": "", "libelle": "", "journal": "",
        "type": "manual", "mois": "", "annee": 0, "status": "", "created_at": "", "updated_at": "",
        "asset_id": "", "fiscal_year": 0, "total_debit": 0.0, "total_credit": 0.0,
    }
    df = normalize_df(df, defaults)
    if not df.empty:
        for col in ["entry_id", "piece_no", "libelle", "journal", "type", "mois", "status", "created_at", "updated_at", "asset_id"]:
            df[col] = df[col].fillna("").astype(str)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["annee"] = pd.to_numeric(df["annee"], errors="coerce").fillna(0).astype(int)
        df["fiscal_year"] = pd.to_numeric(df["fiscal_year"], errors="coerce").fillna(0).astype(int)
        df["total_debit"] = pd.to_numeric(df["total_debit"], errors="coerce").fillna(0.0)
        df["total_credit"] = pd.to_numeric(df["total_credit"], errors="coerce").fillna(0.0)
        missing_month = df["mois"].eq("") & df["date"].notna()
        df.loc[missing_month, "mois"] = df.loc[missing_month, "date"].apply(month_name_from_date)
        missing_year = (df["annee"] == 0) & df["date"].notna()
        df.loc[missing_year, "annee"] = df.loc[missing_year, "date"].dt.year.astype(int)
        df = df.sort_values(["date", "created_at"], ascending=[False, False], na_position="last").reset_index(drop=True)
    return df


@st.cache_data(ttl=30, show_spinner=False)
def load_entry_lines(user_uid: str) -> pd.DataFrame:
    docs = fs_list_documents(user_collection("entry_lines", user_uid))
    df = pd.DataFrame(docs)
    defaults = {
        "_id": "", "entry_id": "", "account_code": "", "account_label": "", "debit": 0.0, "credit": 0.0, "memo": ""
    }
    df = normalize_df(df, defaults)
    if not df.empty:
        for col in ["entry_id", "account_code", "account_label", "memo"]:
            df[col] = df[col].fillna("").astype(str)
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0.0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0.0)
        df = df.sort_values(["entry_id", "account_code"]).reset_index(drop=True)
    return df


@st.cache_data(ttl=30, show_spinner=False)
def load_assets(user_uid: str) -> pd.DataFrame:
    docs = fs_list_documents(user_collection("assets", user_uid))
    df = pd.DataFrame(docs)
    defaults = {
        "_id": "", "asset_id": "", "name": "", "asset_family": "", "acquisition_date": None,
        "amount": 0.0, "salvage_value": 0.0, "useful_life_years": 0, "asset_account": "", "asset_label": "",
        "depr_account": "", "depr_label": "", "expense_account": "", "expense_label": "",
        "linked_entry_id": "", "status": "active", "created_at": ""
    }
    df = normalize_df(df, defaults)
    if not df.empty:
        for col in [
            "asset_id", "name", "asset_family", "asset_account", "asset_label", "depr_account", "depr_label",
            "expense_account", "expense_label", "linked_entry_id", "status", "created_at"
        ]:
            df[col] = df[col].fillna("").astype(str)
        df["acquisition_date"] = pd.to_datetime(df["acquisition_date"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["salvage_value"] = pd.to_numeric(df["salvage_value"], errors="coerce").fillna(0.0)
        df["useful_life_years"] = pd.to_numeric(df["useful_life_years"], errors="coerce").fillna(0).astype(int)
        df = df.sort_values(["acquisition_date", "name"], ascending=[False, True], na_position="last").reset_index(drop=True)
    return df


def account_map(accounts_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    if accounts_df.empty:
        return {}
    return {row["code"]: row.to_dict() for _, row in accounts_df.iterrows()}


def account_display_options(accounts_df: pd.DataFrame, prefixes: Optional[Tuple[str, ...]] = None) -> List[str]:
    if accounts_df.empty:
        return []
    df = accounts_df.copy()
    if prefixes:
        df = df[df["code"].astype(str).str.startswith(prefixes)]
    return [f"{row['code']} - {row['label']}" for _, row in df.iterrows()]


def parse_account_option(option: str) -> Tuple[str, str]:
    if " - " not in option:
        return option.strip(), option.strip()
    code, label = option.split(" - ", 1)
    return code.strip(), label.strip()


def validate_lines(lines: List[Dict[str, Any]]) -> Tuple[bool, str, float, float]:
    valid_lines = [ln for ln in lines if safe_float(ln.get("debit"), 0) > 0 or safe_float(ln.get("credit"), 0) > 0]
    if len(valid_lines) < 2:
        return False, "Une écriture doit contenir au moins deux lignes mouvementées.", 0.0, 0.0
    total_debit = round(sum(safe_float(ln.get("debit"), 0) for ln in valid_lines), 2)
    total_credit = round(sum(safe_float(ln.get("credit"), 0) for ln in valid_lines), 2)
    if total_debit <= 0 or total_credit <= 0:
        return False, "Les montants au débit et au crédit doivent être strictement positifs.", total_debit, total_credit
    if round(total_debit - total_credit, 2) != 0:
        return False, f"Écriture non équilibrée : débit {total_debit} / crédit {total_credit}", total_debit, total_credit
    for ln in valid_lines:
        if safe_float(ln.get("debit"), 0) > 0 and safe_float(ln.get("credit"), 0) > 0:
            return False, "Une ligne ne peut pas avoir à la fois un débit et un crédit.", total_debit, total_credit
    return True, "", total_debit, total_credit


def save_entry_with_lines(
    user_uid: str,
    entry_header: Dict[str, Any],
    lines: List[Dict[str, Any]],
    asset_payload: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    ok, msg, total_debit, total_credit = validate_lines(lines)
    if not ok:
        return False, msg

    entry_id = entry_header.get("entry_id") or str(uuid.uuid4()).replace("-", "")
    entry_date = pd.to_datetime(entry_header.get("date"), errors="coerce")
    if pd.isna(entry_date):
        return False, "Date d'écriture invalide."

    header = {
        "entry_id": entry_id,
        "date": entry_date.date().isoformat(),
        "piece_no": entry_header.get("piece_no", "").strip(),
        "libelle": entry_header.get("libelle", "").strip(),
        "journal": entry_header.get("journal", "OD").strip(),
        "type": entry_header.get("type", "manual").strip(),
        "status": "balanced",
        "mois": MOIS[entry_date.month - 1],
        "annee": int(entry_date.year),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "asset_id": entry_header.get("asset_id", ""),
        "fiscal_year": safe_int(entry_header.get("fiscal_year", 0), 0),
        "total_debit": total_debit,
        "total_credit": total_credit,
    }

    if not fs_create_document(user_collection("entries", user_uid), header, doc_id=entry_id):
        return False, "Impossible d'enregistrer l'entête de l'écriture."

    success = True
    for idx, line in enumerate(lines, start=1):
        debit = round(safe_float(line.get("debit"), 0), 2)
        credit = round(safe_float(line.get("credit"), 0), 2)
        if debit <= 0 and credit <= 0:
            continue
        payload = {
            "entry_id": entry_id,
            "account_code": line.get("account_code", "").strip(),
            "account_label": line.get("account_label", "").strip(),
            "debit": debit,
            "credit": credit,
            "memo": line.get("memo", "").strip(),
            "line_no": idx,
        }
        line_id = f"{entry_id}_{idx:02d}"
        success = fs_create_document(user_collection("entry_lines", user_uid), payload, doc_id=line_id) and success

    if asset_payload:
        asset_id = asset_payload.get("asset_id") or str(uuid.uuid4()).replace("-", "")
        asset_doc = dict(asset_payload)
        asset_doc["asset_id"] = asset_id
        asset_doc["linked_entry_id"] = entry_id
        asset_doc["created_at"] = now_iso()
        success = fs_create_document(user_collection("assets", user_uid), asset_doc, doc_id=asset_id) and success

    if success:
        invalidate_caches()
        return True, "Écriture enregistrée avec succès."
    return False, "Écriture partiellement enregistrée. Vérifie la base de données."


def delete_entry_with_children(user_uid: str, entry_id: str) -> Tuple[bool, str]:
    lines_df = load_entry_lines(user_uid)
    assets_df = load_assets(user_uid)
    ok = True

    if not lines_df.empty:
        to_delete = lines_df[lines_df["entry_id"] == entry_id]
        for _, row in to_delete.iterrows():
            ok = fs_delete_document(user_collection("entry_lines", user_uid), row["_id"]) and ok

    if not assets_df.empty:
        linked_assets = assets_df[assets_df["linked_entry_id"] == entry_id]
        for _, row in linked_assets.iterrows():
            ok = fs_delete_document(user_collection("assets", user_uid), row["_id"]) and ok

    ok = fs_delete_document(user_collection("entries", user_uid), entry_id) and ok
    if ok:
        invalidate_caches()
        return True, "Écriture supprimée."
    return False, "Suppression incomplète."


def ledger_df(entries_df: pd.DataFrame, lines_df: pd.DataFrame) -> pd.DataFrame:
    if entries_df.empty or lines_df.empty:
        return pd.DataFrame(columns=[
            "entry_id", "date", "piece_no", "libelle", "journal", "type", "annee", "mois",
            "account_code", "account_label", "debit", "credit", "memo", "asset_id", "fiscal_year"
        ])
    cols = ["entry_id", "date", "piece_no", "libelle", "journal", "type", "annee", "mois", "asset_id", "fiscal_year"]
    merged = lines_df.merge(entries_df[cols], on="entry_id", how="left")
    merged = merged.sort_values(["date", "entry_id", "account_code"], ascending=[False, False, True], na_position="last").reset_index(drop=True)
    return merged


def filter_entries(entries_df: pd.DataFrame, year: Optional[int], month: Optional[str], search: str = "") -> pd.DataFrame:
    if entries_df.empty:
        return entries_df.copy()
    df = entries_df.copy()
    if year:
        df = df[df["annee"] == year]
    if month and month != "Tous":
        df = df[df["mois"] == month]
    if search.strip():
        q = search.strip().lower()
        mask = (
            df["libelle"].str.lower().str.contains(q, na=False)
            | df["piece_no"].str.lower().str.contains(q, na=False)
            | df["journal"].str.lower().str.contains(q, na=False)
            | df["type"].str.lower().str.contains(q, na=False)
        )
        df = df[mask]
    return df.reset_index(drop=True)


def filter_ledger(ledger: pd.DataFrame, year: Optional[int], month: Optional[str]) -> pd.DataFrame:
    if ledger.empty:
        return ledger.copy()
    df = ledger.copy()
    if year:
        df = df[df["annee"] == year]
    if month and month != "Tous":
        df = df[df["mois"] == month]
    return df.reset_index(drop=True)


def trial_balance(accounts_df: pd.DataFrame, lines_df: pd.DataFrame) -> pd.DataFrame:
    if accounts_df.empty:
        return pd.DataFrame(columns=["code", "label", "total_debit", "total_credit", "solde_debit", "solde_credit", "statement_group", "normal_side"])

    df = accounts_df.copy()
    if lines_df.empty:
        df["total_debit"] = 0.0
        df["total_credit"] = 0.0
    else:
        agg = lines_df.groupby("account_code", as_index=False).agg(total_debit=("debit", "sum"), total_credit=("credit", "sum"))
        df = df.merge(agg, left_on="code", right_on="account_code", how="left")
        if "account_code" in df.columns:
            df = df.drop(columns=["account_code"])
        df["total_debit"] = pd.to_numeric(df["total_debit"], errors="coerce").fillna(0.0)
        df["total_credit"] = pd.to_numeric(df["total_credit"], errors="coerce").fillna(0.0)

    df["net"] = df["total_debit"] - df["total_credit"]
    df["solde_debit"] = df["net"].apply(lambda x: x if x > 0 else 0.0)
    df["solde_credit"] = df["net"].apply(lambda x: -x if x < 0 else 0.0)
    df = df.sort_values("code").reset_index(drop=True)
    return df


def account_value_from_tb(row: pd.Series) -> float:
    group = str(row.get("statement_group", ""))
    debit = safe_float(row.get("total_debit"), 0)
    credit = safe_float(row.get("total_credit"), 0)
    if group in {"asset", "expense"}:
        return max(0.0, debit - credit)
    if group in {"liability", "equity", "revenue", "contra_asset"}:
        return max(0.0, credit - debit)
    return 0.0


def compute_income_statement(tb_df: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, float]:
    if tb_df.empty:
        return {"revenue": 0.0, "expense": 0.0, "profit_before_tax": 0.0, "tax": 0.0, "net_income": 0.0}
    rev = tb_df[tb_df["statement_group"] == "revenue"].apply(account_value_from_tb, axis=1).sum()
    exp = tb_df[tb_df["statement_group"] == "expense"].apply(account_value_from_tb, axis=1).sum()
    pbt = rev - exp
    tax_rate = safe_float(cfg.get("taux_is", 30), 30) / 100
    tax = max(0.0, pbt * tax_rate)
    net = pbt - tax
    return {"revenue": rev, "expense": exp, "profit_before_tax": pbt, "tax": tax, "net_income": net}


def monthly_performance(entries_df: pd.DataFrame, lines_df: pd.DataFrame, accounts_df: pd.DataFrame, year: int) -> pd.DataFrame:
    ledger = ledger_df(entries_df, lines_df)
    if ledger.empty:
        return pd.DataFrame({"Mois": MOIS, "Produits": [0.0] * 12, "Charges": [0.0] * 12, "Résultat": [0.0] * 12})
    acc_map = account_map(accounts_df)
    rows = []
    for m in MOIS:
        lm = ledger[(ledger["annee"] == year) & (ledger["mois"] == m)].copy()
        if lm.empty:
            rows.append({"Mois": m, "Produits": 0.0, "Charges": 0.0, "Résultat": 0.0})
            continue
        lm["statement_group"] = lm["account_code"].map(lambda x: acc_map.get(x, {}).get("statement_group", ""))
        revenue = (lm[lm["statement_group"] == "revenue"]["credit"].sum() - lm[lm["statement_group"] == "revenue"]["debit"].sum())
        expense = (lm[lm["statement_group"] == "expense"]["debit"].sum() - lm[lm["statement_group"] == "expense"]["credit"].sum())
        rows.append({"Mois": m, "Produits": revenue, "Charges": expense, "Résultat": revenue - expense})
    return pd.DataFrame(rows)


def treasury_journal(ledger: pd.DataFrame, account_code: str, opening_balance: float, devise: str) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame(columns=["Date", "N° Pièce", "Libellé", "Entrée", "Sortie", "Solde", "_entry_num", "_exit_num", "_solde_num"])
    df = ledger[ledger["account_code"] == account_code].copy().sort_values(["date", "entry_id"])
    if df.empty:
        return pd.DataFrame(columns=["Date", "N° Pièce", "Libellé", "Entrée", "Sortie", "Solde", "_entry_num", "_exit_num", "_solde_num"])
    solde = safe_float(opening_balance, 0)
    rows = []
    for _, row in df.iterrows():
        entree = safe_float(row.get("debit"), 0)
        sortie = safe_float(row.get("credit"), 0)
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


def full_asset_schedule(assets_df: pd.DataFrame, year_filter: Optional[int] = None) -> pd.DataFrame:
    if assets_df.empty:
        return pd.DataFrame(columns=[
            "Asset ID", "Immobilisation", "Famille", "Exercice", "Valeur brute", "Base amortissable",
            "Durée", "Annuité", "Amortissement cumulé", "Valeur nette comptable",
            "Compte immo", "Compte amort.", "Compte dotation"
        ])
    rows = []
    for _, asset in assets_df.iterrows():
        acq_date = asset.get("acquisition_date")
        if pd.isna(acq_date):
            continue
        gross = safe_float(asset.get("amount"), 0)
        salvage = safe_float(asset.get("salvage_value"), 0)
        life = max(1, safe_int(asset.get("useful_life_years"), 1))
        base = max(0.0, gross - salvage)
        annual = base / life
        start_year = acq_date.year
        for i in range(life):
            y = start_year + i
            cumulative = min(base, annual * (i + 1))
            residual = max(salvage, gross - cumulative)
            rows.append({
                "Asset ID": asset.get("asset_id", ""),
                "Immobilisation": asset.get("name", ""),
                "Famille": asset.get("asset_family", ""),
                "Exercice": y,
                "Valeur brute": gross,
                "Base amortissable": base,
                "Durée": life,
                "Annuité": annual,
                "Amortissement cumulé": cumulative,
                "Valeur nette comptable": residual,
                "Compte immo": asset.get("asset_account", ""),
                "Compte amort.": asset.get("depr_account", ""),
                "Compte dotation": asset.get("expense_account", ""),
            })
    df = pd.DataFrame(rows)
    if year_filter:
        df = df[df["Exercice"] == year_filter]
    df = df.sort_values(["Immobilisation", "Exercice"]).reset_index(drop=True)
    return df


def depreciation_keys(entries_df: pd.DataFrame) -> set:
    if entries_df.empty:
        return set()
    dfd = entries_df[(entries_df["type"] == "depreciation") & (entries_df["asset_id"] != "") & (entries_df["fiscal_year"] > 0)]
    return set(zip(dfd["asset_id"], dfd["fiscal_year"]))


def post_depreciation_for_year(user_uid: str, entries_df: pd.DataFrame, assets_df: pd.DataFrame, year: int) -> Tuple[int, List[str]]:
    if assets_df.empty:
        return 0, []
    already = depreciation_keys(entries_df)
    created = 0
    messages: List[str] = []
    schedule = full_asset_schedule(assets_df, year_filter=year)
    if schedule.empty:
        return 0, []
    asset_lookup = {row["asset_id"]: row for _, row in assets_df.iterrows()}
    for _, row in schedule.iterrows():
        asset_id = row["Asset ID"]
        key = (asset_id, year)
        if key in already:
            continue
        asset = asset_lookup.get(asset_id)
        if asset is None:
            continue
        amount = safe_float(row["Annuité"], 0)
        if amount <= 0:
            continue
        entry_date = date(year, 12, 31)
        header = {
            "date": entry_date.isoformat(),
            "piece_no": f"DOT-{year}-{asset_id[:6]}",
            "libelle": f"Dotation amortissement {asset.get('name', '')} - {year}",
            "journal": "OD",
            "type": "depreciation",
            "asset_id": asset_id,
            "fiscal_year": year,
        }
        lines = [
            {
                "account_code": asset.get("expense_account", "681"),
                "account_label": asset.get("expense_label", "Dotations aux amortissements"),
                "debit": amount,
                "credit": 0,
                "memo": f"Dotation {year}",
            },
            {
                "account_code": asset.get("depr_account", ""),
                "account_label": asset.get("depr_label", ""),
                "debit": 0,
                "credit": amount,
                "memo": f"Amortissement cumulé {year}",
            },
        ]
        ok, msg = save_entry_with_lines(user_uid, header, lines, None)
        if ok:
            created += 1
        else:
            messages.append(f"{asset.get('name', '')}: {msg}")
    return created, messages


def show_auth_page() -> None:
    st.title("Accès sécurisé")
    st.caption("Connexion par email et mot de passe avec Firebase Authentication.")
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
            display_name = st.text_input("Nom complet")
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


def compute_year_options(entries_df: pd.DataFrame, assets_df: pd.DataFrame) -> List[int]:
    years = set(range(datetime.utcnow().year - 2, datetime.utcnow().year + 4))
    if not entries_df.empty:
        years |= set(entries_df["annee"].dropna().astype(int).tolist())
    if not assets_df.empty and "acquisition_date" in assets_df.columns:
        adf = assets_df[assets_df["acquisition_date"].notna()].copy()
        if not adf.empty:
            years |= set(adf["acquisition_date"].dt.year.astype(int).tolist())
    return sorted(y for y in years if y > 0)


def render_sidebar(cfg: Dict[str, Any], user: Dict[str, Any], entries_df: pd.DataFrame, assets_df: pd.DataFrame) -> Tuple[str, int, str]:
    year_options = compute_year_options(entries_df, assets_df)
    current_year = datetime.utcnow().year
    default_index = year_options.index(current_year) if current_year in year_options else max(0, len(year_options) - 1)
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
                "✍️ Saisie des Écritures",
                "📔 Journal Général",
                "💵 Journal de Caisse",
                "🏦 Journal de Banque",
                "🏗️ Immobilisations",
                "⚖️ Balance Générale",
                "📈 Compte de Résultat",
                "📊 Bilan",
                "📅 Tableau de Clôture",
                "⚙️ Paramètres",
            ],
        )
        st.markdown("---")
        selected_year = st.selectbox("Année", year_options, index=default_index)
        selected_month = st.selectbox("Mois", ["Tous"] + MOIS)
    return page, selected_year, selected_month


def page_dashboard(entries_df: pd.DataFrame, lines_df: pd.DataFrame, accounts_df: pd.DataFrame, cfg: Dict[str, Any], year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Tableau de Bord")
    st.caption(f"Période : {month} {year}")

    ledger = filter_ledger(ledger_df(entries_df, lines_df), year, month)
    tb = trial_balance(accounts_df, ledger)
    is_data = compute_income_statement(tb, cfg)

    cash_movement = 0.0
    bank_movement = 0.0
    if not ledger.empty:
        cash_movement = ledger[ledger["account_code"] == "57"]["debit"].sum() - ledger[ledger["account_code"] == "57"]["credit"].sum()
        bank_movement = ledger[ledger["account_code"] == "521"]["debit"].sum() - ledger[ledger["account_code"] == "521"]["credit"].sum()

    cash_balance = safe_float(cfg.get("solde_initial_caisse", 0), 0) + cash_movement
    bank_balance = safe_float(cfg.get("solde_initial_banque", 0), 0) + bank_movement

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi("Produits", fmt_amount(is_data["revenue"], devise), "Comptes classe 7")
    with c2:
        render_kpi("Charges", fmt_amount(is_data["expense"], devise), "Comptes classe 6")
    with c3:
        render_kpi("Résultat net", fmt_amount(is_data["net_income"], devise), "Après impôt théorique")
    with c4:
        render_kpi("Solde caisse", fmt_amount(cash_balance, devise), "Compte 57")
    with c5:
        render_kpi("Solde banque", fmt_amount(bank_balance, devise), "Compte 521")

    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">Performance mensuelle</div>', unsafe_allow_html=True)
        perf = monthly_performance(entries_df, lines_df, accounts_df, year)
        fig = go.Figure()
        fig.add_bar(name="Produits", x=perf["Mois"].str[:3], y=perf["Produits"], marker_color="#22c55e")
        fig.add_bar(name="Charges", x=perf["Mois"].str[:3], y=perf["Charges"], marker_color="#ef4444")
        fig.add_scatter(name="Résultat", x=perf["Mois"].str[:3], y=perf["Résultat"], mode="lines+markers", line=dict(color="#3b82f6", width=3))
        fig.update_layout(barmode="group", height=340, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Structure des charges</div>', unsafe_allow_html=True)
        expense_tb = tb[tb["statement_group"] == "expense"].copy()
        if expense_tb.empty:
            st.info("Aucune charge sur la période.")
        else:
            expense_tb["Montant"] = expense_tb.apply(account_value_from_tb, axis=1)
            expense_tb = expense_tb[expense_tb["Montant"] > 0][["label", "Montant"]].rename(columns={"label": "Compte"})
            if expense_tb.empty:
                st.info("Aucune charge sur la période.")
            else:
                fig2 = px.pie(expense_tb, names="Compte", values="Montant", hole=0.45, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig2.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Dernières écritures</div>', unsafe_allow_html=True)
    recent = filter_entries(entries_df, year, month).head(12).copy()
    if recent.empty:
        st.info("Aucune écriture enregistrée sur cette période.")
    else:
        recent["Date"] = recent["date"].dt.strftime("%d/%m/%Y")
        st.dataframe(
            recent[["Date", "piece_no", "libelle", "journal", "type", "total_debit", "total_credit"]].rename(
                columns={
                    "piece_no": "N° Pièce",
                    "libelle": "Libellé",
                    "journal": "Journal",
                    "type": "Type",
                    "total_debit": "Débit",
                    "total_credit": "Crédit",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )




def page_entry_input(user_uid: str, accounts_df: pd.DataFrame, cfg: Dict[str, Any]) -> None:
    devise = cfg.get("devise", "FCFA")

    # ── Feedback persistant après rerun ──
    if st.session_state.pop("_save_ok", False):
        st.success(f"✅ {st.session_state.pop('_save_msg', 'Écriture enregistrée.')}", icon="✅")
    if st.session_state.pop("_save_err", False):
        st.error(f"❌ {st.session_state.pop('_save_msg', 'Erreur lors de l\'enregistrement.')}")

    bs = st.session_state.get("backend_status", "")
    if bs:
        st.warning(f"⚠️ Connexion Firebase : {bs}")

    st.title("✍️ Saisie des Écritures")
    tab_guided, tab_manual = st.tabs(["✨ Assistant guidé", "🔧 Écriture manuelle"])

    revenue_options = account_display_options(accounts_df, prefixes=("7",))
    expense_options = [opt for opt in account_display_options(accounts_df, prefixes=("6",)) if not opt.startswith("681 - ")]
    if not revenue_options:
        revenue_options = ["701 - Ventes / Prestations"]
    if not expense_options:
        expense_options = ["602 - Fournitures et services extérieurs"]

    # ══════════════════════════════════════════════
    #  ONGLET 1 — ASSISTANT GUIDÉ
    # ══════════════════════════════════════════════
    with tab_guided:
        st.markdown("### Étape 1 — Nature & moyen de paiement")
        col_nat, col_pay = st.columns(2)
        with col_nat:
            nature = st.selectbox(
                "🎯 Nature de l'opération",
                list(NATURE_MAP.keys()),
                key="guided_nature_sel",
            )
        payment_options = NATURE_MAP[nature]["payment_options"]
        with col_pay:
            moyen = st.selectbox(
                "💳 Moyen de paiement",
                payment_options,
                key="guided_moyen_sel",
            )
        template = NATURE_MAP[nature]["templates"][moyen]

        # ── Aperçu dynamique de l'écriture ──
        PREVIEW_MAP = {
            "Vente encaissée en caisse":              ("57 Caisse", "701 Ventes", "🟢 Entrée argent", "#22c55e"),
            "Vente encaissée en banque":              ("521 Banque", "701 Ventes", "🟢 Entrée argent", "#22c55e"),
            "Dépense payée par caisse":               ("6xx Charge", "57 Caisse", "🔴 Sortie argent", "#ef4444"),
            "Dépense payée par banque":               ("6xx Charge", "521 Banque", "🔴 Sortie argent", "#ef4444"),
            "Virement caisse vers banque":            ("521 Banque", "57 Caisse", "🔵 Virement", "#3b82f6"),
            "Virement banque vers caisse":            ("57 Caisse", "521 Banque", "🔵 Virement", "#3b82f6"),
            "Encaissement client en caisse":          ("57 Caisse", "411 Clients", "🟢 Encaissement", "#22c55e"),
            "Encaissement client en banque":          ("521 Banque", "411 Clients", "🟢 Encaissement", "#22c55e"),
            "Paiement fournisseur par caisse":        ("401 Fournisseurs", "57 Caisse", "🔴 Paiement", "#ef4444"),
            "Paiement fournisseur par banque":        ("401 Fournisseurs", "521 Banque", "🔴 Paiement", "#ef4444"),
            "Achat d'immobilisation payé en caisse":  ("2xx Immobilisation", "57 Caisse", "🟡 Investissement", "#f59e0b"),
            "Achat d'immobilisation payé en banque":  ("2xx Immobilisation", "521 Banque", "🟡 Investissement", "#f59e0b"),
        }
        prev = PREVIEW_MAP.get(template)
        if prev:
            debit_acc, credit_acc, tag, color = prev
            st.markdown(
                f"""
                <div style="background:{'rgba(34,197,94,0.08)' if color=='#22c55e' else 'rgba(239,68,68,0.08)' if color=='#ef4444' else 'rgba(59,130,246,0.08)' if color=='#3b82f6' else 'rgba(245,158,11,0.08)'};
                            border:1px solid {color}40; border-radius:10px; padding:14px 18px; margin:10px 0;">
                  <div style="font-size:0.8rem;color:{color};font-weight:700;margin-bottom:8px;">{tag} — {template}</div>
                  <div style="display:flex;align-items:center;gap:12px;font-size:0.95rem;">
                    <span style="background:#fff2;padding:5px 10px;border-radius:6px;font-weight:600;">📤 DÉBIT<br><small style="font-weight:400">{debit_acc}</small></span>
                    <span style="font-size:1.4rem;color:{color};">→</span>
                    <span style="background:#fff2;padding:5px 10px;border-radius:6px;font-weight:600;">📥 CRÉDIT<br><small style="font-weight:400">{credit_acc}</small></span>
                  </div>
                  <div style="margin-top:8px;font-size:0.78rem;opacity:0.7;">
                    Le compte DÉBIT augmente · Le compte CRÉDIT diminue (ou est la source)
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### Étape 2 — Remplir les détails")
        with st.form("guided_entry_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                entry_date = st.date_input("📅 Date", value=date.today())
                piece_no = st.text_input("🔖 N° Pièce", placeholder="FAC-001 / DEP-001")
            with c2:
                amount = st.number_input(f"💰 Montant ({devise})", min_value=0.0, step=1000.0)
                label = st.text_input("📝 Libellé *", placeholder="Ex: Vente de produits à M. Diallo")
            with c3:
                memo = st.text_input("📌 Note / Référence", placeholder="Optionnel")

            revenue_opt = None
            expense_opt = None
            asset_family = None
            salvage_value = 0.0

            if template in {"Vente encaissée en caisse", "Vente encaissée en banque"}:
                revenue_opt = st.selectbox("💼 Compte de produit (701…)", revenue_options, index=0)

            if template in {"Dépense payée par caisse", "Dépense payée par banque"}:
                expense_opt = st.selectbox("📂 Compte de charge (6xx)", expense_options, index=0)

            if template in {"Achat d'immobilisation payé en caisse", "Achat d'immobilisation payé en banque"}:
                asset_family = st.selectbox("🏗️ Famille d'immobilisation", list(ASSET_CATALOG.keys()))
                salvage_value = st.number_input(f"Valeur résiduelle ({devise})", min_value=0.0, step=1000.0)
                if asset_family:
                    st.caption(f"⏱️ Durée amortissement : {ASSET_CATALOG[asset_family]['life_years']} ans (linéaire)")

            submitted = st.form_submit_button(
                "💾 Enregistrer l'écriture",
                type="primary",
                use_container_width=True,
            )
            if submitted:
                if amount <= 0:
                    st.error("⚠️ Le montant doit être supérieur à 0.")
                elif not label.strip():
                    st.error("⚠️ Le libellé est obligatoire.")
                else:
                    lines_to_save: List[Dict[str, Any]] = []
                    journal_code = "OD"
                    entry_type = "guided"
                    asset_payload: Optional[Dict[str, Any]] = None

                    if template == "Vente encaissée en caisse":
                        rc, rl = parse_account_option(revenue_opt)
                        lines_to_save = [
                            {"account_code": "57",  "account_label": "Caisse", "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": rc,    "account_label": rl,       "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "CAI"
                    elif template == "Vente encaissée en banque":
                        rc, rl = parse_account_option(revenue_opt)
                        lines_to_save = [
                            {"account_code": "521", "account_label": "Banque", "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": rc,    "account_label": rl,       "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "BQ"
                    elif template == "Dépense payée par caisse":
                        ec, el = parse_account_option(expense_opt)
                        lines_to_save = [
                            {"account_code": ec,   "account_label": el,       "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "57", "account_label": "Caisse", "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "CAI"
                    elif template == "Dépense payée par banque":
                        ec, el = parse_account_option(expense_opt)
                        lines_to_save = [
                            {"account_code": ec,    "account_label": el,       "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "521", "account_label": "Banque", "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "BQ"
                    elif template == "Virement caisse vers banque":
                        lines_to_save = [
                            {"account_code": "521", "account_label": "Banque", "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "57",  "account_label": "Caisse", "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "TR"
                    elif template == "Virement banque vers caisse":
                        lines_to_save = [
                            {"account_code": "57",  "account_label": "Caisse", "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "521", "account_label": "Banque", "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "TR"
                    elif template == "Encaissement client en caisse":
                        lines_to_save = [
                            {"account_code": "57",  "account_label": "Caisse",  "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "411", "account_label": "Clients", "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "CAI"
                    elif template == "Encaissement client en banque":
                        lines_to_save = [
                            {"account_code": "521", "account_label": "Banque",  "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "411", "account_label": "Clients", "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "BQ"
                    elif template == "Paiement fournisseur par caisse":
                        lines_to_save = [
                            {"account_code": "401", "account_label": "Fournisseurs", "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "57",  "account_label": "Caisse",       "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "CAI"
                    elif template == "Paiement fournisseur par banque":
                        lines_to_save = [
                            {"account_code": "401", "account_label": "Fournisseurs", "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "521", "account_label": "Banque",       "debit": 0.0,    "credit": amount, "memo": memo},
                        ]
                        journal_code = "BQ"
                    elif template == "Achat d'immobilisation payé en caisse":
                        meta = ASSET_CATALOG[asset_family]
                        lines_to_save = [
                            {"account_code": meta["asset_account"], "account_label": meta["asset_label"], "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "57",  "account_label": "Caisse", "debit": 0.0, "credit": amount, "memo": memo},
                        ]
                        journal_code = "CAI"
                        entry_type = "asset_purchase"
                        asset_payload = {
                            "name": label.strip(), "asset_family": asset_family,
                            "acquisition_date": entry_date.isoformat(), "amount": float(amount),
                            "salvage_value": float(salvage_value), "useful_life_years": meta["life_years"],
                            "asset_account": meta["asset_account"], "asset_label": meta["asset_label"],
                            "depr_account": meta["depr_account"], "depr_label": meta["depr_label"],
                            "expense_account": meta["expense_account"], "expense_label": meta["expense_label"],
                            "status": "active",
                        }
                    elif template == "Achat d'immobilisation payé en banque":
                        meta = ASSET_CATALOG[asset_family]
                        lines_to_save = [
                            {"account_code": meta["asset_account"], "account_label": meta["asset_label"], "debit": amount, "credit": 0.0, "memo": memo},
                            {"account_code": "521", "account_label": "Banque", "debit": 0.0, "credit": amount, "memo": memo},
                        ]
                        journal_code = "BQ"
                        entry_type = "asset_purchase"
                        asset_payload = {
                            "name": label.strip(), "asset_family": asset_family,
                            "acquisition_date": entry_date.isoformat(), "amount": float(amount),
                            "salvage_value": float(salvage_value), "useful_life_years": meta["life_years"],
                            "asset_account": meta["asset_account"], "asset_label": meta["asset_label"],
                            "depr_account": meta["depr_account"], "depr_label": meta["depr_label"],
                            "expense_account": meta["expense_account"], "expense_label": meta["expense_label"],
                            "status": "active",
                        }

                    if not lines_to_save:
                        st.error("❌ Erreur interne : aucune ligne générée pour ce template.")
                    else:
                        header = {
                            "date": entry_date.isoformat(),
                            "piece_no": piece_no.strip(),
                            "libelle": label.strip(),
                            "journal": journal_code,
                            "type": entry_type,
                        }
                        ok, msg = save_entry_with_lines(user_uid, header, lines_to_save, asset_payload)
                        st.session_state["_save_ok"] = ok
                        st.session_state["_save_err"] = not ok
                        st.session_state["_save_msg"] = msg
                        bs2 = st.session_state.get("backend_status", "")
                        if bs2:
                            st.session_state["_save_msg"] += f" ({bs2})"
                        st.rerun()

    # ══════════════════════════════════════════════
    #  ONGLET 2 — ÉCRITURE MANUELLE
    # ══════════════════════════════════════════════
    with tab_manual:
        st.markdown(
            """
            <div style="background:rgba(59,130,246,0.07);border:1px solid #3b82f640;border-radius:8px;padding:10px 16px;margin-bottom:12px;font-size:0.88rem;">
            📌 <strong>Rappel partie double</strong> · Somme Débits = Somme Crédits obligatoire.
            &nbsp;|&nbsp; <strong>Débit</strong> = entrée sur un actif ou une charge &nbsp;
            <strong>Crédit</strong> = sortie d'actif ou constatation d'une dette / produit
            </div>
            """,
            unsafe_allow_html=True,
        )
        options = account_display_options(accounts_df)
        with st.form("manual_entry_form", clear_on_submit=True):
            h1, h2, h3 = st.columns(3)
            with h1:
                entry_date_m = st.date_input("📅 Date", value=date.today(), key="m_date")
                piece_no_m = st.text_input("🔖 N° Pièce", key="m_piece")
            with h2:
                journal_m = st.selectbox(
                    "📒 Journal",
                    [("OD", "OD — Opérations Diverses"), ("CAI", "CAI — Caisse"), ("BQ", "BQ — Banque"), ("TR", "TR — Trésorerie")],
                    format_func=lambda x: x[1],
                    key="m_journal",
                )
                label_m = st.text_input("📝 Libellé *", key="m_label")
            with h3:
                nb_lines = st.number_input("Nb lignes", min_value=2, max_value=10, value=4, step=1, key="m_nb_lines")

            st.markdown("---")
            header_cols = st.columns([3, 2, 2, 3])
            header_cols[0].markdown("**Compte**")
            header_cols[1].markdown("**📤 Débit**")
            header_cols[2].markdown("**📥 Crédit**")
            header_cols[3].markdown("**Mémo**")

            manual_lines: List[Dict[str, Any]] = []
            for idx in range(1, int(nb_lines) + 1):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
                with c1:
                    account_opt = st.selectbox(f"", options, key=f"acc_{idx}", label_visibility="collapsed")
                with c2:
                    debit_m = st.number_input("", min_value=0.0, step=1000.0, key=f"deb_{idx}", label_visibility="collapsed")
                with c3:
                    credit_m = st.number_input("", min_value=0.0, step=1000.0, key=f"cred_{idx}", label_visibility="collapsed")
                with c4:
                    memo_m = st.text_input("", key=f"memo_{idx}", label_visibility="collapsed")
                code_m, acc_label_m = parse_account_option(account_opt)
                manual_lines.append({
                    "account_code": code_m, "account_label": acc_label_m,
                    "debit": debit_m, "credit": credit_m, "memo": memo_m,
                })

            total_d = sum(safe_float(l.get("debit"), 0) for l in manual_lines)
            total_c = sum(safe_float(l.get("credit"), 0) for l in manual_lines)
            balance_ok = round(total_d - total_c, 2) == 0 and total_d > 0

            bal_color = "#22c55e" if balance_ok else "#ef4444"
            bal_icon  = "✅" if balance_ok else "⚖️"
            st.markdown(
                f"<div style='text-align:right;font-size:0.9rem;color:{bal_color};font-weight:700;margin:6px 0;'>"
                f"{bal_icon} Débit : {fmt_amount(total_d, devise)} &nbsp;|&nbsp; Crédit : {fmt_amount(total_c, devise)}"
                f"{'&nbsp; — Équilibré' if balance_ok else '&nbsp; — ⚠️ Non équilibré'}</div>",
                unsafe_allow_html=True,
            )

            journal_code_m = journal_m[0] if isinstance(journal_m, tuple) else journal_m
            submit_manual = st.form_submit_button(
                "💾 Enregistrer l'écriture manuelle",
                type="primary",
                use_container_width=True,
                disabled=False,
            )
            if submit_manual:
                if not label_m.strip():
                    st.error("⚠️ Le libellé est obligatoire.")
                else:
                    header_m = {
                        "date": entry_date_m.isoformat(),
                        "piece_no": piece_no_m.strip(),
                        "libelle": label_m.strip(),
                        "journal": journal_code_m,
                        "type": "manual",
                    }
                    ok_m, msg_m = save_entry_with_lines(user_uid, header_m, manual_lines, None)
                    st.session_state["_save_ok"] = ok_m
                    st.session_state["_save_err"] = not ok_m
                    st.session_state["_save_msg"] = msg_m
                    bs3 = st.session_state.get("backend_status", "")
                    if bs3:
                        st.session_state["_save_msg"] += f" ({bs3})"
                    st.rerun()



def page_general_journal(
    user_uid: str,
    entries_df: pd.DataFrame,
    lines_df: pd.DataFrame,
    year: int,
    month: str,
    cfg: Dict[str, Any],
) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("📔 Journal Général")

    # ── Barre de recherche + filtre journal ──
    col_s, col_j, col_exp = st.columns([3, 2, 2])
    with col_s:
        search = st.text_input("🔎 Rechercher", placeholder="Libellé, pièce, type…")
    with col_j:
        journal_filter = st.selectbox("Filtrer par journal", ["Tous", "OD", "CAI", "BQ", "TR"])
    with col_exp:
        st.write("")
        show_lines = st.toggle("Afficher les lignes comptables", value=True)

    filtered_entries = filter_entries(entries_df, year, month, search)
    if journal_filter != "Tous":
        filtered_entries = filtered_entries[filtered_entries["journal"] == journal_filter]

    # ── KPIs ──
    n_ecr = len(filtered_entries)
    total_d = filtered_entries["total_debit"].sum() if not filtered_entries.empty else 0.0
    total_c = filtered_entries["total_credit"].sum() if not filtered_entries.empty else 0.0
    is_balanced = round(total_d - total_c, 2) == 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi("Écritures", str(n_ecr), f"{year} · {month}")
    with k2:
        render_kpi("Total Débits", fmt_amount(total_d, devise), "Mouvements débit")
    with k3:
        render_kpi("Total Crédits", fmt_amount(total_c, devise), "Mouvements crédit")
    with k4:
        bal_label = "✅ Équilibré" if is_balanced else "⚠️ Déséquilibré"
        render_kpi("Équilibre", bal_label, "Débit = Crédit ?")

    if filtered_entries.empty:
        st.info("Aucune écriture trouvée pour les filtres sélectionnés.")
        return

    csv = filtered_entries.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Exporter le journal filtré (CSV)",
        csv,
        file_name=f"journal_general_{year}_{month}.csv",
        mime="text/csv",
    )

    all_lines = ledger_df(entries_df, lines_df)

    st.markdown("")
    # ── Confirmation suppression ──
    if "confirm_delete_id" not in st.session_state:
        st.session_state["confirm_delete_id"] = None

    confirm_id = st.session_state.get("confirm_delete_id")
    if confirm_id:
        row_del = filtered_entries[filtered_entries["entry_id"] == confirm_id]
        if not row_del.empty:
            lbl = row_del.iloc[0].get("libelle", "")
            st.warning(f"⚠️ Confirmer la suppression de **{lbl}** ?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("🗑️ Oui, supprimer", type="primary", key="confirm_del_yes"):
                    ok, msg = delete_entry_with_children(user_uid, confirm_id)
                    st.session_state["confirm_delete_id"] = None
                    st.session_state["_save_ok"] = ok
                    st.session_state["_save_err"] = not ok
                    st.session_state["_save_msg"] = msg
                    st.rerun()
            with cc2:
                if st.button("✖️ Annuler", key="confirm_del_no"):
                    st.session_state["confirm_delete_id"] = None
                    st.rerun()
            st.stop()

    # ── Feedback persistant ──
    if st.session_state.pop("_save_ok", False):
        st.success(f"✅ {st.session_state.pop('_save_msg', '')}", icon="✅")
    if st.session_state.pop("_save_err", False):
        st.error(f"❌ {st.session_state.pop('_save_msg', '')}")

    # ── Liste des écritures ──
    JOURNAL_COLORS = {"CAI": "#22c55e", "BQ": "3b82f6", "TR": "#8b5cf6", "OD": "#94a3b8"}
    TYPE_LABELS    = {"guided": "✨ Assisté", "manual": "🔧 Manuel", "depreciation": "📉 Amort.", "asset_purchase": "🏗️ Immo."}

    for _, row in filtered_entries.iterrows():
        date_str  = row["date"].strftime("%d/%m/%Y") if pd.notna(row["date"]) else "—"
        piece     = row.get("piece_no", "") or "—"
        libelle   = row.get("libelle", "")
        jcode     = row.get("journal", "OD")
        type_lbl  = TYPE_LABELS.get(row.get("type", ""), row.get("type", ""))
        t_debit   = fmt_amount(row.get("total_debit", 0), devise)
        t_credit  = fmt_amount(row.get("total_credit", 0), devise)
        entry_id  = row["entry_id"]
        color     = JOURNAL_COLORS.get(jcode, "#94a3b8")

        header_html = (
            f'<span style="color:{color};font-weight:700;font-size:0.85rem;margin-right:8px;">[{jcode}]</span>'
            f'<strong>{date_str}</strong> &nbsp;·&nbsp; {piece} &nbsp;·&nbsp; {libelle}'
            f'&nbsp;<span style="opacity:0.6;font-size:0.82rem;">{type_lbl}</span>'
            f'&nbsp;&nbsp;<code style="font-size:0.8rem;">D: {t_debit} | C: {t_credit}</code>'
        )

        with st.expander(f"[{jcode}] {date_str} · {piece} · {libelle} | {t_debit}", expanded=False):
            st.markdown(header_html, unsafe_allow_html=True)

            if show_lines:
                sub = all_lines[all_lines["entry_id"] == entry_id].copy()
                if not sub.empty:
                    sub = sub.sort_values("account_code").reset_index(drop=True)
                    # Build visual table
                    rows_html = ""
                    for _, ln in sub.iterrows():
                        d_val  = fmt_amount(ln["debit"],  devise) if ln["debit"]  > 0 else "—"
                        c_val  = fmt_amount(ln["credit"], devise) if ln["credit"] > 0 else "—"
                        d_col  = "#22c55e" if ln["debit"]  > 0 else "#64748b"
                        c_col  = "#ef4444" if ln["credit"] > 0 else "#64748b"
                        memo   = ln.get("memo", "") or ""
                        rows_html += (
                            f'<tr style="border-bottom:1px solid #ffffff15">'
                            f'<td style="padding:5px 8px;font-weight:600;font-size:0.85rem;">{ln["account_code"]}</td>'
                            f'<td style="padding:5px 8px;font-size:0.85rem;">{ln["account_label"]}</td>'
                            f'<td style="padding:5px 8px;color:{d_col};font-weight:700;text-align:right;">{d_val}</td>'
                            f'<td style="padding:5px 8px;color:{c_col};font-weight:700;text-align:right;">{c_val}</td>'
                            f'<td style="padding:5px 8px;font-size:0.8rem;opacity:0.7;">{memo}</td>'
                            f'</tr>'
                        )
                    st.markdown(
                        f'<table style="width:100%;border-collapse:collapse;font-family:monospace;">'
                        f'<thead><tr style="border-bottom:2px solid #ffffff30;opacity:0.6;font-size:0.78rem;">'
                        f'<th style="padding:4px 8px;text-align:left;">Code</th>'
                        f'<th style="padding:4px 8px;text-align:left;">Compte</th>'
                        f'<th style="padding:4px 8px;text-align:right;">📤 Débit</th>'
                        f'<th style="padding:4px 8px;text-align:right;">📥 Crédit</th>'
                        f'<th style="padding:4px 8px;text-align:left;">Mémo</th>'
                        f'</tr></thead><tbody>{rows_html}</tbody></table>',
                        unsafe_allow_html=True,
                    )
                    td = sub["debit"].sum()
                    tc = sub["credit"].sum()
                    eq = "✅ Équilibré" if round(td - tc, 2) == 0 else "⚠️ Déséquilibré"
                    st.markdown(
                        f'<div style="text-align:right;font-size:0.82rem;margin-top:6px;opacity:0.8;">'
                        f'Σ Débit : <strong>{fmt_amount(td, devise)}</strong> &nbsp;|&nbsp; '
                        f'Σ Crédit : <strong>{fmt_amount(tc, devise)}</strong> &nbsp; {eq}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("")
            act1, act2, act3 = st.columns([2, 2, 1])
            with act1:
                st.caption(f"Type : {type_lbl} &nbsp;·&nbsp; Statut : {row.get('status', '')}")
            with act2:
                st.caption(f"Créé le : {row.get('created_at', '—')[:10] if row.get('created_at') else '—'}")
            with act3:
                if st.button("🗑️ Supprimer", key=f"del_{entry_id}", use_container_width=True):
                    st.session_state["confirm_delete_id"] = entry_id
                    st.rerun()


def page_cash_bank(title: str, account_code: str, entries_df: pd.DataFrame, lines_df: pd.DataFrame, cfg: Dict[str, Any], year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    opening = safe_float(cfg.get("solde_initial_caisse", 0), 0) if account_code == "57" else safe_float(cfg.get("solde_initial_banque", 0), 0)
    st.title(title)
    ledger = filter_ledger(ledger_df(entries_df, lines_df), year, month)
    journal = treasury_journal(ledger, account_code, opening, devise)
    total_entries = journal["_entry_num"].sum() if not journal.empty else 0.0
    total_exits = journal["_exit_num"].sum() if not journal.empty else 0.0
    closing = opening + total_entries - total_exits

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Solde initial", fmt_amount(opening, devise), "Paramètres")
    with c2:
        render_kpi("Entrées", fmt_amount(total_entries, devise), "Débits du compte")
    with c3:
        render_kpi("Sorties", fmt_amount(total_exits, devise), "Crédits du compte")
    with c4:
        render_kpi("Solde final", fmt_amount(closing, devise), "Solde courant")

    st.markdown('<div class="section-title">Mouvements</div>', unsafe_allow_html=True)
    if journal.empty:
        st.info("Aucun mouvement sur cette période.")
        return

    csv = journal.drop(columns=["_entry_num", "_exit_num", "_solde_num"]).to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 Exporter les mouvements", csv, file_name=f"journal_{account_code}_{year}_{month}.csv", mime="text/csv")
    st.dataframe(journal[["Date", "N° Pièce", "Libellé", "Entrée", "Sortie", "Solde"]], use_container_width=True, hide_index=True)

    fig = go.Figure()
    fig.add_bar(name="Entrées", x=journal["Date"], y=journal["_entry_num"], marker_color="#22c55e")
    fig.add_bar(name="Sorties", x=journal["Date"], y=journal["_exit_num"], marker_color="#ef4444")
    fig.add_scatter(name="Solde", x=journal["Date"], y=journal["_solde_num"], mode="lines+markers", line=dict(color="#3b82f6", width=3))
    fig.update_layout(barmode="group", height=340, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True)



def monthly_closing_table(
    entries_df: pd.DataFrame,
    lines_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
    cfg: Dict[str, Any],
    year: int,
) -> pd.DataFrame:
    """Tableau de clôture mensuel avec cumuls CA, charges, résultat et trésorerie."""
    opening_caisse = safe_float(cfg.get("solde_initial_caisse", 0), 0)
    opening_banque = safe_float(cfg.get("solde_initial_banque", 0), 0)
    ledger = ledger_df(entries_df, lines_df)
    acc_map = account_map(accounts_df)
    rows = []
    cumul_ca = 0.0
    cumul_charges = 0.0
    cumul_resultat = 0.0
    solde_caisse = opening_caisse
    solde_banque = opening_banque

    for m in MOIS:
        if ledger.empty:
            lm = pd.DataFrame()
        else:
            lm = ledger[(ledger["annee"] == year) & (ledger["mois"] == m)].copy()

        if lm.empty:
            ca = 0.0
            charges = 0.0
            mvt_caisse = 0.0
            mvt_banque = 0.0
        else:
            lm["_sg"] = lm["account_code"].map(lambda x: acc_map.get(x, {}).get("statement_group", ""))
            ca = max(0.0, lm[lm["_sg"] == "revenue"]["credit"].sum() - lm[lm["_sg"] == "revenue"]["debit"].sum())
            charges = max(0.0, lm[lm["_sg"] == "expense"]["debit"].sum() - lm[lm["_sg"] == "expense"]["credit"].sum())
            mvt_caisse = lm[lm["account_code"] == "57"]["debit"].sum() - lm[lm["account_code"] == "57"]["credit"].sum()
            mvt_banque = lm[lm["account_code"] == "521"]["debit"].sum() - lm[lm["account_code"] == "521"]["credit"].sum()

        resultat = ca - charges
        cumul_ca += ca
        cumul_charges += charges
        cumul_resultat += resultat
        solde_caisse += mvt_caisse
        solde_banque += mvt_banque

        rows.append({
            "Mois": m,
            "CA (Ventes)": ca,
            "Charges": charges,
            "Marge brute": ca - charges,
            "Résultat": resultat,
            "Solde Caisse": solde_caisse,
            "Solde Banque": solde_banque,
            "Trésorerie totale": solde_caisse + solde_banque,
            "Cumul CA": cumul_ca,
            "Cumul Charges": cumul_charges,
            "Cumul Résultat": cumul_resultat,
        })
    return pd.DataFrame(rows)


def page_closing_table(
    entries_df: pd.DataFrame,
    lines_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
    cfg: Dict[str, Any],
    year: int,
) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title(f"📅 Tableau de Clôture — {year}")
    st.caption("Récapitulatif mensuel : ventes, charges, résultat et trésorerie avec cumuls annuels.")

    df = monthly_closing_table(entries_df, lines_df, accounts_df, cfg, year)

    total_ca = df["CA (Ventes)"].sum()
    total_charges = df["Charges"].sum()
    total_resultat = df["Résultat"].sum()
    mois_positifs = int((df["Résultat"] > 0).sum())
    last_tresorerie = df["Trésorerie totale"].iloc[-1] if not df.empty else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi("CA annuel", fmt_amount(total_ca, devise), f"Exercice {year}")
    with c2:
        render_kpi("Charges annuelles", fmt_amount(total_charges, devise), f"Exercice {year}")
    with c3:
        render_kpi("Résultat annuel", fmt_amount(total_resultat, devise), "Avant IS")
    with c4:
        render_kpi("Mois bénéficiaires", f"{mois_positifs}/12", "Résultat > 0")
    with c5:
        render_kpi("Trésorerie finale", fmt_amount(last_tresorerie, devise), "Caisse + Banque")

    st.markdown("")
    st.markdown('<div class="section-title">Tableau mensuel détaillé</div>', unsafe_allow_html=True)

    # Build display dataframe with formatted amounts
    num_cols = ["CA (Ventes)", "Charges", "Marge brute", "Résultat",
                "Solde Caisse", "Solde Banque", "Trésorerie totale",
                "Cumul CA", "Cumul Charges", "Cumul Résultat"]
    display_df = df[["Mois"] + num_cols].copy()
    for col in num_cols:
        display_df[col] = display_df[col].apply(lambda x: fmt_amount(x, devise))

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # --- Graphs ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">Performances mensuelles</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_bar(name="CA (Ventes)", x=df["Mois"].str[:3], y=df["CA (Ventes)"], marker_color="#22c55e")
        fig.add_bar(name="Charges", x=df["Mois"].str[:3], y=df["Charges"], marker_color="#ef4444")
        fig.add_scatter(
            name="Résultat",
            x=df["Mois"].str[:3], y=df["Résultat"],
            mode="lines+markers",
            line=dict(color="#3b82f6", width=3),
        )
        fig.update_layout(
            barmode="group", height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Cumul CA &amp; Charges</div>', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_scatter(
            name="Cumul CA",
            x=df["Mois"].str[:3], y=df["Cumul CA"],
            mode="lines+markers",
            line=dict(color="#22c55e", width=3),
            fill="tozeroy", fillcolor="rgba(34,197,94,0.08)",
        )
        fig2.add_scatter(
            name="Cumul Charges",
            x=df["Mois"].str[:3], y=df["Cumul Charges"],
            mode="lines+markers",
            line=dict(color="#ef4444", width=2, dash="dot"),
        )
        fig2.add_scatter(
            name="Cumul Résultat",
            x=df["Mois"].str[:3], y=df["Cumul Résultat"],
            mode="lines+markers",
            line=dict(color="#3b82f6", width=2),
        )
        fig2.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Évolution de la trésorerie</div>', unsafe_allow_html=True)
    fig3 = go.Figure()
    fig3.add_scatter(
        name="Caisse", x=df["Mois"].str[:3], y=df["Solde Caisse"],
        mode="lines+markers", line=dict(color="#f59e0b", width=2),
    )
    fig3.add_scatter(
        name="Banque", x=df["Mois"].str[:3], y=df["Solde Banque"],
        mode="lines+markers", line=dict(color="#8b5cf6", width=2),
    )
    fig3.add_scatter(
        name="Trésorerie totale", x=df["Mois"].str[:3], y=df["Trésorerie totale"],
        mode="lines+markers+text",
        line=dict(color="#06b6d4", width=3),
        fill="tozeroy", fillcolor="rgba(6,182,212,0.06)",
    )
    fig3.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig3, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Exporter le tableau de clôture",
        csv,
        file_name=f"tableau_cloture_{year}.csv",
        mime="text/csv",
    )


def page_assets(user_uid: str, entries_df: pd.DataFrame, assets_df: pd.DataFrame, cfg: Dict[str, Any], year: int) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Immobilisations & Amortissements")

    gross = assets_df["amount"].sum() if not assets_df.empty else 0.0
    full_sched = full_asset_schedule(assets_df)
    year_sched = full_asset_schedule(assets_df, year_filter=year)
    annual_dep = year_sched["Annuité"].sum() if not year_sched.empty else 0.0
    net_book = year_sched["Valeur nette comptable"].sum() if not year_sched.empty else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi("Valeur brute", fmt_amount(gross, devise), "Immobilisations actives")
    with c2:
        render_kpi(f"Dotation {year}", fmt_amount(annual_dep, devise), "Tableau d'amortissement")
    with c3:
        render_kpi(f"VNC {year}", fmt_amount(net_book, devise), "Valeur nette comptable")

    tab1, tab2, tab3 = st.tabs(["Immobilisations", "Tableau complet", "Dotations automatiques"])

    with tab1:
        if assets_df.empty:
            st.info("Aucune immobilisation enregistrée. Passe par la saisie guidée pour créer un achat d'immobilisation.")
        else:
            view = assets_df.copy()
            view["Date acquisition"] = view["acquisition_date"].dt.strftime("%d/%m/%Y")
            view["Montant"] = view["amount"].apply(lambda x: fmt_amount(x, devise))
            view["Valeur résiduelle"] = view["salvage_value"].apply(lambda x: fmt_amount(x, devise))
            st.dataframe(
                view[[
                    "Date acquisition", "name", "asset_family", "Montant", "Valeur résiduelle",
                    "useful_life_years", "asset_account", "depr_account"
                ]].rename(columns={
                    "name": "Immobilisation",
                    "asset_family": "Famille",
                    "useful_life_years": "Durée (ans)",
                    "asset_account": "Compte immo",
                    "depr_account": "Compte amort.",
                }),
                use_container_width=True,
                hide_index=True,
            )

    with tab2:
        if full_sched.empty:
            st.info("Aucun tableau d'amortissement disponible.")
        else:
            view = full_sched.copy()
            for col in ["Valeur brute", "Base amortissable", "Annuité", "Amortissement cumulé", "Valeur nette comptable"]:
                view[col] = view[col].apply(lambda x: fmt_amount(x, devise))
            st.dataframe(view, use_container_width=True, hide_index=True)
            csv = full_sched.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Exporter le tableau d'amortissement", csv, file_name=f"tableau_amortissement_{year}.csv", mime="text/csv")

    with tab3:
        st.markdown("#### Génération automatique des dotations")
        st.write(
            "Cette action crée une écriture d'OD par immobilisation pour l'exercice choisi, "
            "au débit du compte 681 et au crédit du compte d'amortissement correspondant."
        )
        if st.button(f"Générer les dotations de l'exercice {year}", type="primary"):
            created, messages = post_depreciation_for_year(user_uid, entries_df, assets_df, year)
            if created:
                st.success(f"{created} dotation(s) comptabilisées.")
                st.rerun()
            elif messages:
                st.warning("Aucune nouvelle dotation créée.")
                for msg in messages:
                    st.write(f"- {msg}")
            else:
                st.info("Aucune dotation à générer ou elles existent déjà.")


def page_trial_balance(entries_df: pd.DataFrame, lines_df: pd.DataFrame, accounts_df: pd.DataFrame, cfg: Dict[str, Any], year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Balance Générale")
    ledger = filter_ledger(ledger_df(entries_df, lines_df), year, month)
    tb = trial_balance(accounts_df, ledger)
    if tb.empty:
        st.info("Aucun compte disponible.")
        return
    view = tb.copy()
    totals = {
        "Débit": tb["total_debit"].sum(),
        "Crédit": tb["total_credit"].sum(),
        "Solde Débit": tb["solde_debit"].sum(),
        "Solde Crédit": tb["solde_credit"].sum(),
    }
    for col_src, col_dst in [("total_debit", "Débit"), ("total_credit", "Crédit"), ("solde_debit", "Solde Débit"), ("solde_credit", "Solde Crédit")]:
        view[col_dst] = view[col_src].apply(lambda x: fmt_amount(x, devise) if x else "—")
    st.dataframe(
        view[["code", "label", "Débit", "Crédit", "Solde Débit", "Solde Crédit", "statement_group"]].rename(
            columns={"code": "Compte", "label": "Intitulé", "statement_group": "Groupe"}
        ),
        use_container_width=True,
        hide_index=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Total débits", fmt_amount(totals["Débit"], devise))
    with c2:
        render_kpi("Total crédits", fmt_amount(totals["Crédit"], devise))
    with c3:
        render_kpi("Soldes débiteurs", fmt_amount(totals["Solde Débit"], devise))
    with c4:
        render_kpi("Soldes créditeurs", fmt_amount(totals["Solde Crédit"], devise))

    if round(totals["Débit"] - totals["Crédit"], 2) == 0:
        st.markdown("<div class='state-ok'>Balance équilibrée</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='state-bad'>Balance non équilibrée</div>", unsafe_allow_html=True)

    csv = tb.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 Exporter la balance", csv, file_name=f"balance_generale_{year}_{month}.csv", mime="text/csv")


def page_income_statement(entries_df: pd.DataFrame, lines_df: pd.DataFrame, accounts_df: pd.DataFrame, cfg: Dict[str, Any], year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Compte de Résultat")
    st.caption(f"Période : {month} {year}")
    ledger = filter_ledger(ledger_df(entries_df, lines_df), year, month)
    tb = trial_balance(accounts_df, ledger)
    data = compute_income_statement(tb, cfg)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi("Produits", fmt_amount(data["revenue"], devise))
    with c2:
        render_kpi("Charges", fmt_amount(data["expense"], devise))
    with c3:
        render_kpi("Résultat avant impôt", fmt_amount(data["profit_before_tax"], devise))
    with c4:
        render_kpi("Résultat net", fmt_amount(data["net_income"], devise))

    rev_df = tb[tb["statement_group"] == "revenue"].copy()
    exp_df = tb[tb["statement_group"] == "expense"].copy()
    rev_df["Montant"] = rev_df.apply(account_value_from_tb, axis=1)
    exp_df["Montant"] = exp_df.apply(account_value_from_tb, axis=1)

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-title">Produits</div>', unsafe_allow_html=True)
        if rev_df.empty:
            st.info("Aucun produit.")
        else:
            rv = rev_df[rev_df["Montant"] > 0][["code", "label", "Montant"]].copy()
            rv["Montant"] = rv["Montant"].apply(lambda x: fmt_amount(x, devise))
            st.dataframe(rv.rename(columns={"code": "Compte", "label": "Intitulé"}), use_container_width=True, hide_index=True)
    with right:
        st.markdown('<div class="section-title">Charges</div>', unsafe_allow_html=True)
        if exp_df.empty:
            st.info("Aucune charge.")
        else:
            ex = exp_df[exp_df["Montant"] > 0][["code", "label", "Montant"]].copy()
            ex["Montant"] = ex["Montant"].apply(lambda x: fmt_amount(x, devise))
            st.dataframe(ex.rename(columns={"code": "Compte", "label": "Intitulé"}), use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame({
        "Indicateur": ["Produits", "Charges", "Résultat avant impôt", "IS théorique", "Résultat net"],
        "Valeur": [data["revenue"], data["expense"], data["profit_before_tax"], data["tax"], data["net_income"]],
    })
    fig = go.Figure(go.Bar(
        x=chart_df["Indicateur"],
        y=chart_df["Valeur"],
        marker_color=["#22c55e", "#ef4444", "#3b82f6", "#f59e0b", "#22c55e" if data["net_income"] >= 0 else "#ef4444"],
    ))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def page_balance_sheet(entries_df: pd.DataFrame, lines_df: pd.DataFrame, accounts_df: pd.DataFrame, cfg: Dict[str, Any], year: int, month: str) -> None:
    devise = cfg.get("devise", "FCFA")
    st.title("Bilan simplifié")
    ledger = filter_ledger(ledger_df(entries_df, lines_df), year, month)
    tb = trial_balance(accounts_df, ledger)
    result = compute_income_statement(tb, cfg)

    tb["Valeur"] = tb.apply(account_value_from_tb, axis=1)
    assets = tb[tb["statement_group"] == "asset"]["Valeur"].sum()
    contra_assets = tb[tb["statement_group"] == "contra_asset"]["Valeur"].sum()
    liabilities = tb[tb["statement_group"] == "liability"]["Valeur"].sum()
    equity = tb[tb["statement_group"] == "equity"]["Valeur"].sum() + result["net_income"]
    total_assets = assets - contra_assets
    total_passif = liabilities + equity

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-title">Actif</div>', unsafe_allow_html=True)
        act_df = tb[tb["statement_group"].isin(["asset", "contra_asset"])].copy()
        if act_df.empty:
            st.info("Aucun actif.")
        else:
            act_df = act_df[act_df["Valeur"] > 0][["code", "label", "statement_group", "Valeur"]]
            act_df["Valeur"] = act_df.apply(
                lambda r: f"- {fmt_amount(r['Valeur'], devise)}" if r["statement_group"] == "contra_asset" else fmt_amount(r["Valeur"], devise),
                axis=1,
            )
            st.dataframe(act_df.rename(columns={"code": "Compte", "label": "Intitulé", "statement_group": "Groupe"}), use_container_width=True, hide_index=True)
            st.markdown(f"### Total Actif : {fmt_amount(total_assets, devise)}")

    with right:
        st.markdown('<div class="section-title">Passif</div>', unsafe_allow_html=True)
        pass_df = tb[tb["statement_group"].isin(["liability", "equity"])].copy()
        extra = pd.DataFrame([{
            "code": "RESULTAT",
            "label": "Résultat net de la période",
            "statement_group": "equity",
            "Valeur": result["net_income"],
        }])
        pass_df = pd.concat([pass_df[["code", "label", "statement_group", "Valeur"]], extra], ignore_index=True)
        pass_df = pass_df[pass_df["Valeur"] != 0]
        if pass_df.empty:
            st.info("Aucun passif.")
        else:
            pass_df["Valeur"] = pass_df["Valeur"].apply(lambda x: fmt_amount(x, devise))
            st.dataframe(pass_df.rename(columns={"code": "Compte", "label": "Intitulé", "statement_group": "Groupe"}), use_container_width=True, hide_index=True)
            st.markdown(f"### Total Passif : {fmt_amount(total_passif, devise)}")

    if round(total_assets - total_passif, 2) == 0:
        st.markdown("<div class='state-ok'>Bilan équilibré</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='state-bad'>Écart Actif / Passif : {fmt_amount(total_assets - total_passif, devise)}</div>", unsafe_allow_html=True)


def page_settings(user_uid: str, entries_df: pd.DataFrame, lines_df: pd.DataFrame, accounts_df: pd.DataFrame, assets_df: pd.DataFrame, cfg: Dict[str, Any]) -> None:
    st.title("Paramètres")

    with st.form("company_config_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nom de l'entreprise", value=cfg.get("nom", ""))
            adresse = st.text_input("Adresse", value=cfg.get("adresse", ""))
            tel = st.text_input("Téléphone", value=cfg.get("tel", ""))
            solde_initial_caisse = st.number_input("Solde initial caisse", value=float(cfg.get("solde_initial_caisse", 0)), step=1000.0)
        with c2:
            rc = st.text_input("RC / NINEA", value=cfg.get("rc", ""))
            email = st.text_input("Email", value=cfg.get("email", ""))
            banque = st.text_input("Banque domiciliataire", value=cfg.get("banque", ""))
            solde_initial_banque = st.number_input("Solde initial banque", value=float(cfg.get("solde_initial_banque", 0)), step=1000.0)

        devise = st.selectbox("Devise", ["FCFA", "EUR", "USD"], index=["FCFA", "EUR", "USD"].index(cfg.get("devise", "FCFA")))
        taux_is = st.slider("Taux IS (%)", 0, 40, int(safe_float(cfg.get("taux_is", 30), 30)))

        submitted = st.form_submit_button("💾 Sauvegarder les paramètres", type="primary")
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
    st.markdown("### Plan comptable")
    st.dataframe(
        accounts_df[["code", "label", "statement_group", "normal_side"]].rename(
            columns={
                "code": "Compte",
                "label": "Intitulé",
                "statement_group": "Groupe",
                "normal_side": "Sens normal",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### Export des données")
    c1, c2, c3 = st.columns(3)

    with c1:
        if not entries_df.empty:
            csv = entries_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Export écritures", csv, file_name="ecritures.csv", mime="text/csv")

    with c2:
        if not lines_df.empty:
            csv = lines_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Export lignes", csv, file_name="lignes_ecritures.csv", mime="text/csv")

    with c3:
        if not assets_df.empty:
            csv = assets_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 Export immobilisations", csv, file_name="immobilisations.csv", mime="text/csv")

    st.markdown("---")
    st.markdown("### Utilitaires")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Actualiser le cache"):
            invalidate_caches()
            st.success("Cache actualisé.")
    with col_b:
        if st.button("♻️ Réinstaller le plan comptable par défaut"):
            current = fs_list_documents(user_collection("accounts", user_uid))
            if not current:
                ensure_default_accounts(user_uid)
                st.success("Plan comptable installé.")
                st.rerun()
            else:
                st.info("Le plan comptable existe déjà.")

    st.info(
        "Les soldes initiaux caisse et banque servent au calcul des journaux de trésorerie. "
        "Si tu veux une stricte comptabilité d'ouverture dans la balance, il faudra aussi passer une écriture d'à-nouveau."
    )


def main() -> None:
    init_session_state()
    inject_css()
    require_backend_config()
    restore_user_from_session()

    if not current_user():
        show_auth_page()

    user = current_user()
    user_uid = user["uid"]

    ensure_default_accounts(user_uid)

    cfg = load_company_config(user_uid)
    accounts_df = load_accounts(user_uid)
    entries_df = load_entries(user_uid)
    lines_df = load_entry_lines(user_uid)
    assets_df = load_assets(user_uid)

    page, selected_year, selected_month = render_sidebar(cfg, user, entries_df, assets_df)

    if page == "🏠 Tableau de Bord":
        page_dashboard(entries_df, lines_df, accounts_df, cfg, selected_year, selected_month)

    elif page == "✍️ Saisie des Écritures":
        page_entry_input(user_uid, accounts_df, cfg)

    elif page == "📔 Journal Général":
        page_general_journal(user_uid, entries_df, lines_df, selected_year, selected_month, cfg)

    elif page == "💵 Journal de Caisse":
        page_cash_bank("Journal de Caisse", "57", entries_df, lines_df, cfg, selected_year, selected_month)

    elif page == "🏦 Journal de Banque":
        page_cash_bank("Journal de Banque", "521", entries_df, lines_df, cfg, selected_year, selected_month)

    elif page == "🏗️ Immobilisations":
        page_assets(user_uid, entries_df, assets_df, cfg, selected_year)

    elif page == "⚖️ Balance Générale":
        page_trial_balance(entries_df, lines_df, accounts_df, cfg, selected_year, selected_month)

    elif page == "📈 Compte de Résultat":
        page_income_statement(entries_df, lines_df, accounts_df, cfg, selected_year, selected_month)

    elif page == "📊 Bilan":
        page_balance_sheet(entries_df, lines_df, accounts_df, cfg, selected_year, selected_month)

    elif page == "📅 Tableau de Clôture":
        page_closing_table(entries_df, lines_df, accounts_df, cfg, selected_year)

    elif page == "⚙️ Paramètres":
        page_settings(user_uid, entries_df, lines_df, accounts_df, assets_df, cfg)


if __name__ == "__main__":
    main()
