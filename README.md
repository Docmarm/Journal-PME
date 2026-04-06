# 📒 Journal Comptable PME — Application Streamlit

Application professionnelle de journalisation comptable avec Firebase Firestore comme base de données.

## Utilisateurs & Securite

- L'application gere maintenant plusieurs utilisateurs.
- La connexion se fait uniquement par email et mot de passe avec Firebase Authentication.
- Chaque compte dispose de ses propres donnees, stockees sous `users/{user_id}/...`.
- Les anciennes donnees globales deja presentes dans Firestore ne sont pas migrees automatiquement.

### Collections utilisees

- `users/{user_id}` : profil utilisateur
- `users/{user_id}/operations` : journal comptable
- `users/{user_id}/bilan_items` : donnees du bilan
- `users/{user_id}/budget_items` : budget previsionnel
- `users/{user_id}/config/entreprise` : parametres entreprise

### Configuration recommandee

L'application peut lire la configuration Firebase depuis `st.secrets` ou depuis les variables d'environnement :

- `FIREBASE_API_KEY`
- `FIREBASE_PROJECT_ID`

Exemple `.streamlit/secrets.toml` :

```toml
FIREBASE_API_KEY = "votre-cle-api"
FIREBASE_PROJECT_ID = "votre-projet"
```

## 🚀 Installation & Lancement

### 1. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 2. Lancer l'application
```bash
streamlit run app.py
```

L'app s'ouvre automatiquement sur `http://localhost:8501`

---

## 📋 Fonctionnalités

| Module | Description |
|--------|-------------|
| 🏠 **Tableau de Bord** | KPIs en temps réel, graphiques évolution CA/Coûts, dernières opérations |
| 📝 **Saisie des Opérations** | Formulaire de saisie + liste complète avec suppression |
| 💵 **Caisse** | Entrées/Sorties/Solde caisse avec relevé chronologique |
| 🏦 **Banque** | Relevé bancaire, débits/crédits, solde courant |
| 📊 **Coûts & Charges** | Détail par catégorie : salaires, matières, fournitures, loyer, transport... |
| 🏗️ **Investissements** | Gestion des acquisitions + table d'amortissements SYSCOHADA |
| 📈 **Compte de Résultat** | CA → Marge Brute → Résultat Net → Cash Flow |
| ⚖️ **Bilan** | Actif / Passif avec saisie manuelle et calculs automatiques |
| 📅 **Clôture Mensuelle** | Tableau récapitulatif tous les mois de l'année |
| 🎯 **Budget Prévisionnel** | Saisie budget + comparaison Réel vs Budget |
| ⚙️ **Paramètres** | Infos entreprise, taux IS, export CSV |

---

## 🗂️ Catégories d'Opérations

- **Vente / Recette** → Chiffre d'affaires
- **Entrée / Sortie Caisse** → Mouvements espèces
- **Entrée / Sortie Banque** → Mouvements bancaires
- **Salaire** → Charges de personnel
- **Fournitures & Services** → Charges externes
- **Matières Premières** → Achats matières
- **Loyer** → Charges immobilières
- **Transport** → Frais de déplacement
- **Frais Bancaires** → Frais de tenue de compte
- **Investissement** → Acquisitions d'immobilisations

---

## 🔥 Firebase (Firestore)

Collections utilisées :
- `users/{user_id}` — Profil utilisateur
- `users/{user_id}/operations` — Journal des opérations
- `users/{user_id}/bilan_items` — Données du bilan
- `users/{user_id}/budget_items` — Budget prévisionnel
- `users/{user_id}/config/entreprise` — Paramètres entreprise

**Projet :** `fatmata-app`

---

## 📦 Structure des données (opération)

```json
{
  "date": "2026-01-15",
  "piece_no": "FAC-001",
  "libelle": "Vente de produits",
  "categorie": "recette",
  "montant": 500000,
  "notes": "",
  "mois": "Janvier",
  "annee": 2026
}
```
