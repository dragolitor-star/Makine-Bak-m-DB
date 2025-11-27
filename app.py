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
    page_icon="📶", # Yesim.com tarzı bir ikon
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ÖZEL CSS (YESIM.COM TARZI TASARIM) ---
def inject_custom_css():
    st.markdown("""
        <style>
            /* --- GENEL RENK PALETİ --- */
            :root {
                --primary-orange: #F6631B; /* Yesim ana rengi */
                --hover-orange: #E55A18;
                --bg-light: #F8F9FA;
                --text-dark: #222222;
            }

            /* Ana Arka Plan */
            .stApp {
                background-color: var(--bg-light);
                font-family: 'Helvetica Neue', sans-serif;
            }

            /* Üst Header Çubuğu (Beyaz ve Temiz) */
            [data-testid="stHeader"] {
                background-color: #FFFFFF;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }

            /* Başlık Stilleri */
            h1, h2, h3 {
                color: var(--text-dark);
                font-weight: 700;
                letter-spacing: -0.5px;
            }
            
            /* Özel Logo Alanı */
            .brand-header {
                display: flex;
                align-items: center;
                padding: 1rem 0;
                margin-bottom: 2rem;
            }
            .brand-logo-icon {
                font-size: 2rem;
                color: var(--primary-orange);
                margin-right: 10px;
            }
            .brand-title {
                font-size: 1.8rem;
                font-weight: 800;
                color: var(--text-dark);
            }
            .brand-title span {
                color: var(--primary-orange);
            }

            /* --- BUTON TASARIMLARI (YESIM TARZI) --- */
            /* Tüm Streamlit butonlarını hedefle */
            div.stButton > button:first-child {
                background-color: var(--primary-orange);
                color: white !important;
                border: none;
                border-radius: 12px; /* Yuvarlatılmış köşeler */
                padding: 0.75rem 1.5rem;
                font-weight: 600;
                font-size: 1rem;
                box-shadow: 0 4px 6px rgba(246, 99, 27, 0.1);
                transition: all 0.3s ease;
                width: 100%; /* Butonları kolon genişliğine yay */
            }

            /* Buton Hover (Üzerine gelince) Efekti */
            div.stButton > button:first-child:hover {
                background-color: var(--hover-orange);
                box-shadow: 0 6px 12px rgba(246, 99, 27, 0.25);
                transform: translateY(-2px); /* Hafif yukarı kalkma efekti */
                color: white !important;
            }
            
             /* "Ana Menüye Dön" butonu için özel stil (Biraz daha farklılaşması için) */
             /* Streamlit'te belirli bir butonu hedeflemek zordur, bu yüzden 
                genel stilin dışına çıkıp "secondary" tipi buton kullanıyoruz ve onu özelleştiriyoruz */
            [data-testid="baseButton-secondary"] {
                 background-color: white !important;
                 color: var(--primary-orange) !important;
                 border: 2px solid var(--primary-orange) !important;
                 box-shadow: none !important;
            }
             [data-testid="baseButton-secondary"]:hover {
                 background-color: #FFF5F0 !important; /* Çok açık turuncu arka plan */
                 transform: translateY(-1px);
            }

            /* Giriş Kutuları */
            .stTextInput input {
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                padding: 12px;
                background-color: white;
            }
            .stTextInput input:focus {
                border-color: var(--primary-orange);
                box-shadow: 0 0 0 1px var(--primary-orange);
            }

            /* Kart Görünümü için Konteynerler */
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
                 background-color: white;
                 padding: 2rem;
                 border-radius: 16px;
                 box-shadow: 0 2px 12px rgba(0,0,0,0.03);
            }

        </style>
    """, unsafe_allow_html=True)

# CSS'i en başta yükle
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
            "permissions": ["view", "search", "add", "update", "delete", "delete_table", "upload", "report", "logs", "admin_panel"]
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
    return [coll.id for coll in db.collections() if coll.id != "system_users"]

def get_columns_of_table(table_name):
    docs = db.collection(table_name).limit(1).stream()
    for doc in docs: return list(doc.to_dict().keys())
    return []

# --- NAVİGASYON FONKSİYONU ---
def sayfa_degistir(sayfa_adi):
    st.session_state["aktif_sayfa"] = sayfa_adi
    st.rerun()

# --- ANA UYGULAMA ---
def main():
    # Session State Tanımları
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["permissions"] = []
        st.session_state["role"] = ""
    
    if "aktif_sayfa" not in st.session_state:
        st.session_state["aktif_sayfa"] = "Ana Sayfa"

    # --- GİRİŞ EKRANI (MODERN TASARIM) ---
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
             # Yesim tarzı Header
            st.markdown("""
                <div class="brand-header" style="justify-content: center;">
                    <span class="brand-logo-icon">📶</span>
                    <span class="brand-title">Almaxtex<span>Connect</span></span>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<h3 style='text-align: center;'>Giriş Yap</h3>", unsafe_allow_html=True)
            
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            
            st.write("") # Boşluk
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
                    else:
                        st.error("Hatalı şifre!")
                else:
                    st.error("Kullanıcı bulunamadı!")
        return

    # --- ÜST BAR (HEADER - YESIM TARZI) ---
    
    # Özel Header Alanı
    st.markdown("""
        <div class="brand-header">
            <span class="brand-logo-icon">📶</span>
            <span class="brand-title">Almaxtex<span>DB</span></span>
        </div>
    """, unsafe_allow_html=True)

    top_col1, top_col2 = st.columns([6, 1])
    with top_col1:
        st.markdown(f"👋 Hoşgeldin, **{st.session_state['username']}**")
    with top_col2:
        # Çıkış butonu için "secondary" tipini kullanıyoruz ki CSS ile onu farklı (beyaz/turuncu çerçeveli) yapabilelim
        if st.button("Çıkış Yap", type="secondary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["aktif_sayfa"] = "Ana Sayfa"
            st.rerun()
    
    st.divider()

    # --- NAVİGASYON KONTROLÜ ---
    secim = st.session_state["aktif_sayfa"]
    permissions = st.session_state["permissions"]

    # Eğer Ana Sayfadaysak, Dashboard Butonlarını Göster
    if secim == "Ana Sayfa":
        st.title("Ana Kontrol Paneli")
        st.info("Yapmak istediğiniz işlemi aşağıdan seçiniz.")
        
        # Butonları 3 sütunlu ızgaraya yerleştiriyoruz
        col1, col2, col3 = st.columns(3)
        
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

    # --- ALT SAYFALAR ---
    else:
        # Geri Dön butonu için de "secondary" tipi kullanıyoruz (Ana sayfadaki turuncu butonlardan farklı görünsün diye)
        if st.button("🏠 Ana Menüye Dön", type="secondary"):
            sayfa_degistir("Ana Sayfa")
        
        st.write("") # Biraz boşluk

        # --- 1. TABLO GÖRÜNTÜLEME ---
        if secim == "Tablo Görüntüleme":
            st.header("📂 Tablo Görüntüleme")
            tablolar = get_table_list()
            if tablolar:
                tablo = st.selectbox("Tablo Seçin:", tablolar)
                docs = list(db.collection(tablo).stream()) # List'e çevirerek uzunluğunu alıyoruz
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

        # --- 3. YENİ KAYIT EKLEME ---
        elif secim == "Yeni Kayıt Ekle":
            st.header("➕ Yeni Kayıt Ekle")
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox("Tablo:", tablolar)
                doc_id = st.text_input("ID (Opsiyonel):")
                c1, c2 = st.columns(2)
                with c1:
                    seri = st.text_input("Seri No")
                    dept = st.text_input("Departman")
                    lok = st.text_input("Lokasyon")
                    kul = st.text_input("Kullanıcı")
                    pcid = st.text_input("PC ID")
                with c2:
                    pcad = st.text_input("PC Adı")
