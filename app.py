import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from google.cloud.firestore_v1.field_path import FieldPath 
import datetime
import traceback
import os
import hashlib

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Almaxtex Envanter",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ÖZEL CSS (KOYU TEMA: #93022E & #151515) ---
def inject_custom_css():
    st.markdown("""
        <style>
            :root {
                --primary-color: #93022E;    /* İstenilen Bordo/Kırmızı */
                --bg-color: #151515;         /* İstenilen Koyu Arka Plan */
                --secondary-bg: #1E1E1E;     /* Biraz daha açık koyu ton (Kartlar için) */
                --text-color: #E0E0E0;       /* Açık Gri Yazı */
            }

            /* Ana Arka Plan */
            .stApp {
                background-color: var(--bg-color);
                color: var(--text-color);
            }

            /* Header (Üst Çubuk) */
            [data-testid="stHeader"] {
                background-color: var(--bg-color);
            }

            /* Başlıklar */
            h1, h2, h3 {
                color: white !important;
                font-weight: 700;
            }

            /* --- BUTON TASARIMLARI --- */
            div.stButton > button:first-child {
                background-color: var(--primary-color);
                color: white !important;
                border: 1px solid var(--primary-color);
                border-radius: 6px; /* Daha keskin, endüstriyel hatlar */
                padding: 0.75rem 1.5rem;
                font-weight: 600;
                transition: all 0.2s ease;
                width: 100%;
            }

            div.stButton > button:first-child:hover {
                background-color: #B00338; /* Hover olunca biraz daha açığı */
                border-color: #B00338;
                box-shadow: 0 0 10px rgba(147, 2, 46, 0.6);
            }

            /* İkincil Butonlar (Geri Dön / Çıkış) */
            [data-testid="baseButton-secondary"] {
                background-color: transparent !important;
                color: #FFFFFF !important;
                border: 1px solid #555 !important;
            }
            [data-testid="baseButton-secondary"]:hover {
                border-color: var(--primary-color) !important;
                color: var(--primary-color) !important;
            }

            /* --- GİRİŞ KUTULARI (INPUTS) --- */
            .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
                background-color: #252525 !important;
                color: white !important;
                border: 1px solid #444 !important;
                border-radius: 6px;
            }
            
            /* Dataframe (Tablo) Stilleri */
            [data-testid="stDataFrame"] {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 6px;
            }

            /* Kart Görünümü (Containers) */
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
                 background-color: var(--secondary-bg);
                 padding: 1.5rem;
                 border-radius: 8px;
                 border: 1px solid #333;
            }
            
            /* Expander (Açılır Kutu) Başlığı */
            .streamlit-expanderHeader {
                background-color: #252525 !important;
                color: white !important;
            }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- ŞİFRELEME FONKSİYONLARI ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- VERİTABANI BAĞLANTISI ---
@st.cache_resource
def init_db():
    if not firebase_admin._apps:
        if "firebase" in st.secrets:
            try:
                firebase_creds = dict(st.secrets["firebase"])
                if "private_key" in firebase_creds:
                    firebase_creds["private_key"] = firebase_creds["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(firebase_creds)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                st.error(f"Secrets hatası: {e}")
                st.stop()
        elif os.path.exists('license-machinerydb-firebase-adminsdk-fbsvc-7458edd97c.json'):
            cred = credentials.Certificate('license-machinerydb-firebase-adminsdk-fbsvc-7458edd97c.json')
            firebase_admin.initialize_app(cred)
        else:
            st.error("Firebase lisansı bulunamadı!")
            st.stop()
    return firestore.client()

try:
    db = init_db()
except Exception as e:
    st.error(f"Veritabanı hatası: {e}")
    st.stop()

# --- İLK KURULUM (DEFAULT ADMIN) ---
def create_default_admin():
    users_ref = db.collection('system_users')
    docs = users_ref.limit(1).stream()
    if not list(docs):
        admin_data = {
            "username": "admin",
            "password": make_hashes("123456"),
            "role": "admin",
            "permissions": ["view", "search", "add", "update", "delete", "delete_table", "upload", "report", "logs", "transfer", "admin_panel"]
        }
        users_ref.document("admin").set(admin_data)

create_default_admin()

# --- LOGLAMA ---
def log_kayit_ekle(islem_turu, fonksiyon_adi, mesaj, teknik_detay="-"):
    kullanici = st.session_state.get("username", "Bilinmeyen")
    mesaj = f"[{kullanici}] {mesaj}"
    log_dosya_adi = "Sistem_Loglari.xlsx"
    zaman = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    yeni_kayit = {"Tarih_Saat": [zaman], "İşlem_Türü": [islem_turu], "Fonksiyon": [fonksiyon_adi], "Mesaj": [mesaj], "Teknik_Detay": [teknik_detay]}
    try:
        if os.path.exists(log_dosya_adi):
            pd.concat([pd.read_excel(log_dosya_adi), pd.DataFrame(yeni_kayit)], ignore_index=True).to_excel(log_dosya_adi, index=False)
        else:
            pd.DataFrame(yeni_kayit).to_excel(log_dosya_adi, index=False)
    except: pass

# --- YARDIMCI FONKSİYONLAR ---
def get_table_list():
    return [coll.id for coll in db.collections() if coll.id not in ["system_users", "system_settings"]]

def get_columns_of_table(table_name):
    docs = db.collection(table_name).limit(1).stream()
    for doc in docs: return list(doc.to_dict().keys())
    return []

# --- LOKASYON YÖNETİMİ ---
def get_locations():
    doc = db.collection('system_settings').document('locations').get()
    if doc.exists: return sorted(doc.to_dict().get('list', []))
    else:
        defaults = ["Bursa", "Mısır", "Mardin", "İstanbul", "Depo"]
        db.collection('system_settings').document('locations').set({'list': defaults})
        return sorted(defaults)

def add_location(new_loc):
    current_locs = get_locations()
    if new_loc and new_loc not in current_locs:
        current_locs.append(new_loc)
        db.collection('system_settings').document('locations').set({'list': current_locs})
        return True
    return False

def remove_location(loc_to_remove):
    current_locs = get_locations()
    if loc_to_remove in current_locs:
        current_locs.remove(loc_to_remove)
        db.collection('system_settings').document('locations').set({'list': current_locs})
        return True
    return False

# --- NAVİGASYON ---
def sayfa_degistir(sayfa_adi):
    st.session_state["aktif_sayfa"] = sayfa_adi
    st.rerun()

# --- ANA UYGULAMA ---
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["permissions"] = []
        st.session_state["role"] = ""
    
    if "aktif_sayfa" not in st.session_state:
        st.session_state["aktif_sayfa"] = "Ana Sayfa"

    # --- GİRİŞ EKRANI ---
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; color: #93022E;'>ALMAXTEX</h1>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center;'>Envanter Yönetim Sistemi</h4>", unsafe_allow_html=True)
            st.write("")
            
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            st.write("")
            
            if st.button("Giriş Yap", use_container_width=True):
                user_ref = db.collection("system_users").document(username)
                user_doc = user_ref.get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    if check_hashes(password, user_data['password']):
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username
                        st.session_state["role"] = user_data.get("role", "user")
                        st.session_state["permissions"] = user_data.get("permissions", [])
                        st.session_state["aktif_sayfa"] = "Ana Sayfa"
                        st.success("Giriş Başarılı!")
                        st.rerun()
                    else: st.error("Hatalı şifre!")
                else: st.error("Kullanıcı bulunamadı!")
        return

    # --- HEADER ---
    top_col1, top_col2 = st.columns([6, 1])
    with top_col1:
        st.markdown(f"### 👋 **{st.session_state['username']}**")
    with top_col2:
        if st.button("Çıkış", type="secondary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["aktif_sayfa"] = "Ana Sayfa"
            st.rerun()
    st.divider()

    # --- NAVİGASYON KONTROLÜ ---
    secim = st.session_state["aktif_sayfa"]
    permissions = st.session_state["permissions"]

    if secim == "Ana Sayfa":
        st.title("Kontrol Paneli")
        st.info("Yapmak istediğiniz işlemi seçiniz.")
        
        col1, col2, col3 = st.columns(3)
        
        # BUTON IZGARASI
        with col1:
            if "view" in permissions:
                if st.button("📂 Tablo Görüntüleme", use_container_width=True): sayfa_degistir("Tablo Görüntüleme")
            if "update" in permissions:
                if st.button("✏️ Kayıt Güncelle", use_container_width=True): sayfa_degistir("Kayıt Güncelle")
            if "upload" in permissions:
                if st.button("📤 Excel Yükle", use_container_width=True): sayfa_degistir("Toplu Tablo Yükle (Excel)")
            if "admin_panel" in permissions:
                if st.button("👑 Kullanıcı Yönetimi", use_container_width=True): sayfa_degistir("Kullanıcı Yönetimi (Admin)")

        with col2:
            if "search" in permissions:
                if st.button("🔍 Arama & Filtreleme", use_container_width=True): sayfa_degistir("Arama & Filtreleme")
            # YENİ EKLENEN BUTON BURADA
            if "transfer" in permissions: 
                if st.button("🚚 Makine Transferi", use_container_width=True): sayfa_degistir("Makine Transferi")
            if "delete" in permissions:
                if st.button("🗑️ Kayıt Silme", use_container_width=True): sayfa_degistir("Kayıt Silme")
            if "report" in permissions:
                if st.button("📊 Raporlar", use_container_width=True): sayfa_degistir("Raporlar")

        with col3:
            if "add" in permissions:
                if st.button("➕ Yeni Kayıt Ekle", use_container_width=True): sayfa_degistir("Yeni Kayıt Ekle")
            if "delete_table" in permissions:
                if st.button("💣 Tablo Silme", use_container_width=True): sayfa_degistir("Tablo Silme")
            if "logs" in permissions:
                if st.button("📝 Log Kayıtları", use_container_width=True): sayfa_degistir("Log Kayıtları")

    else:
        # Geri Dön Butonu
        if st.button("⬅️ Geri Dön", type="secondary"):
            sayfa_degistir("Ana Sayfa")
        st.write("")

        # --- 1. TABLO GÖRÜNTÜLEME ---
        if secim == "Tablo Görüntüleme":
            st.header("📂 Tablo Görüntüleme")
            tablolar = get_table_list()
            if tablolar:
                tablo = st.selectbox("Tablo Seçin:", tablolar)
                docs = list(db.collection(tablo).stream())
                data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                if data: 
                    st.info(f"Toplam Kayıt: {len(data)}")
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                else: st.warning("Tablo boş.")
            else: st.warning("Tablo yok.")

        # --- 2. ARAMA VE FİLTRELEME ---
        elif secim == "Arama & Filtreleme":
            st.header("🔍 Dinamik Arama")
            tablolar = get_table_list()
            if tablolar:
                secilen_tablo = st.selectbox("Tablo:", tablolar)
                docs = db.collection(secilen_tablo).stream()
                data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                if data:
                    df = pd.DataFrame(data)
                    c1, c2 = st.columns(2)
                    with c1:
                        cols = [c for c in df.columns if "Unnamed" not in str(c) and c != "Dokuman_ID"]
                        secilen_sutun = st.selectbox("Sütun:", cols)
                    with c2:
                        aranan = st.text_input("Aranan:")
                    if aranan:
                        try:
                            res = df[df[secilen_sutun].astype(str).str.contains(aranan, case=False, na=False)]
                            st.success(f"{len(res)} sonuç.")
                            st.dataframe(res, use_container_width=True)
                        except: st.error("Hata.")
                    else: st.dataframe(df, use_container_width=True)
            else: st.warning("Tablo yok.")

        # --- 3. MAKİNE TRANSFERİ ---
        elif secim == "Makine Transferi":
            st.header("🚚 Makine Transferi")
            with st.expander("⚙️ Lokasyon Yönetimi", expanded=False):
                loc_list = get_locations()
                st.write(
