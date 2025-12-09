import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from google.cloud.firestore_v1.field_path import FieldPath 
import datetime
import traceback
import os
import hashlib
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Almaxtex Envanter",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- DİL SÖZLÜĞÜ (GÜNCELLENDİ) ---
TRANS = {
    "tr": {
        "login_title": "Giriş Yap",
        "username": "Kullanıcı Adı",
        "password": "Şifre",
        "email": "E-Posta Adresi",
        "login_btn": "Giriş Yap",
        "logout_btn": "Çıkış Yap",
        "forgot_pass": "Şifremi Unuttum / Sıfırla",
        "send_reset_link": "Yeni Şifre Gönder",
        "reset_success": "✅ Yeni şifreniz e-posta adresinize gönderildi!",
        "reset_fail": "❌ Kullanıcı bulunamadı veya e-posta eşleşmedi.",
        "email_error": "E-posta gönderilirken hata oluştu. Lütfen yöneticiye başvurun.",
        "welcome": "Hoşgeldin",
        "dashboard": "Kontrol Paneli",
        "dashboard_desc": "Yapmak istediğiniz işlemi seçiniz.",
        "back_home": "🏠 Ana Menüye Dön",
        "err_pass": "Hatalı şifre!",
        "err_user": "Kullanıcı bulunamadı!",
        "success_login": "Giriş Başarılı!",
        "menu_view": "📂 Tablo Görüntüleme",
        "menu_search": "🔍 Arama & Filtreleme",
        "menu_add": "➕ Yeni Kayıt Ekle",
        "menu_update": "✏️ Kayıt Güncelle",
        "menu_delete": "🗑️ Kayıt Silme",
        "menu_transfer": "🚚 Makine Transferi",
        "menu_upload": "📤 Excel Yükle",
        "menu_report": "📊 Raporlar",
        "menu_logs": "📝 Log Kayıtları",
        "menu_del_table": "💣 Tablo Silme",
        "menu_admin": "👑 Kullanıcı Yönetimi",
        "select_table": "Tablo Seçin:",
        "total_records": "Toplam Kayıt:",
        "save": "Kaydet",
        "delete": "Sil",
        "success": "İşlem Başarılı!",
        "error": "Hata oluştu:",
        "warning_empty": "Bu tablo boş.",
        "new_user_title": "Yeni Kullanıcı Ekle",
        "role": "Rol",
        "perms": "Yetkiler",
        "create_user": "Kullanıcıyı Oluştur",
        "user_list": "Kullanıcı Listesi",
        "delete_user": "Kullanıcıyı Sil",
        "err_self_del": "Kendinizi silemezsiniz.",
        "mail_subject": "Almaxtex - Yeni Şifreniz",
        "mail_body": "Merhaba,\n\nHesabınız için şifre sıfırlama talebi aldık.\n\nKullanıcı Adı: {}\nYeni Şifreniz: {}\n\nLütfen giriş yaptıktan sonra güvenliğiniz için şifrenizi değiştirmeyi unutmayın.",
        "no_email_config": "Sistemde e-posta ayarları yapılmamış. Lütfen yönetici ile görüşün."
    },
    "en": {
        "login_title": "Login",
        "username": "Username",
        "password": "Password",
        "email": "Email Address",
        "login_btn": "Login",
        "logout_btn": "Logout",
        "forgot_pass": "Forgot Password / Reset",
        "send_reset_link": "Send New Password",
        "reset_success": "✅ New password has been sent to your email!",
        "reset_fail": "❌ User not found or email mismatch.",
        "email_error": "Error sending email. Please contact admin.",
        "welcome": "Welcome",
        "dashboard": "Dashboard",
        "dashboard_desc": "Select an operation below.",
        "back_home": "🏠 Back to Home",
        "err_pass": "Wrong password!",
        "err_user": "User not found!",
        "success_login": "Login Successful!",
        "menu_view": "📂 View Tables",
        "menu_search": "🔍 Search & Filter",
        "menu_add": "➕ Add New Record",
        "menu_update": "✏️ Update Record",
        "menu_delete": "🗑️ Delete Record",
        "menu_transfer": "🚚 Machine Transfer",
        "menu_upload": "📤 Upload Excel",
        "menu_report": "📊 Reports",
        "menu_logs": "📝 Logs",
        "menu_del_table": "💣 Delete Table",
        "menu_admin": "👑 User Management",
        "select_table": "Select Table:",
        "total_records": "Total Records:",
        "save": "Save",
        "delete": "Delete",
        "success": "Operation Successful!",
        "error": "Error occurred:",
        "warning_empty": "This table is empty.",
        "new_user_title": "Add New User",
        "role": "Role",
        "perms": "Permissions",
        "create_user": "Create User",
        "user_list": "User List",
        "delete_user": "Delete User",
        "err_self_del": "You cannot delete yourself.",
        "mail_subject": "Almaxtex - Your New Password",
        "mail_body": "Hello,\n\nWe received a password reset request for your account.\n\nUsername: {}\nNew Password: {}\n\nPlease remember to change your password after logging in.",
        "no_email_config": "Email settings not configured. Contact admin."
    },
    "ar": {
        "login_title": "تسجيل الدخول",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "email": "البريد الإلكتروني",
        "login_btn": "دخول",
        "logout_btn": "خروج",
        "forgot_pass": "نسيت كلمة المرور",
        "send_reset_link": "إرسال كلمة مرور جديدة",
        "reset_success": "✅ تم إرسال كلمة المرور الجديدة إلى بريدك الإلكتروني!",
        "reset_fail": "❌ المستخدم غير موجود أو البريد الإلكتروني غير متطابق.",
        "email_error": "حدث خطأ أثناء إرسال البريد. اتصل بالمسؤول.",
        "welcome": "أهلاً بك",
        "dashboard": "لوحة التحكم",
        "dashboard_desc": "اختر عملية من الأسفل.",
        "back_home": "🏠 العودة للرئيسية",
        "err_pass": "كلمة المرور خاطئة!",
        "err_user": "المستخدم غير موجود!",
        "success_login": "تم الدخول بنجاح!",
        "menu_view": "📂 عرض الجداول",
        "menu_search": "🔍 بحث وتصفية",
        "menu_add": "➕ إضافة سجل جديد",
        "menu_update": "✏️ تحديث سجل",
        "menu_delete": "🗑️ حذف سجل",
        "menu_transfer": "🚚 نقل الماكينات",
        "menu_upload": "📤 رفع إكسل",
        "menu_report": "📊 التقارير",
        "menu_logs": "📝 السجلات",
        "menu_del_table": "💣 حذف الجدول",
        "menu_admin": "👑 إدارة المستخدمين",
        "select_table": "اختر الجدول:",
        "total_records": "إجمالي السجلات:",
        "save": "حفظ",
        "delete": "حذف",
        "success": "تمت العملية بنجاح!",
        "error": "حدث خطأ:",
        "warning_empty": "هذا الجدول فارغ.",
        "new_user_title": "إضافة مستخدم جديد",
        "role": "الدور",
        "perms": "الصلاحيات",
        "create_user": "إنشاء مستخدم",
        "user_list": "قائمة المستخدمين",
        "delete_user": "حذف المستخدم",
        "err_self_del": "لا يمكنك حذف نفسك.",
        "mail_subject": "Almaxtex - كلمة المرور الجديدة",
        "mail_body": "مرحباً،\n\nلقد تلقينا طلب إعادة تعيين كلمة المرور لحسابك.\n\nاسم المستخدم: {}\nكلمة المرور الجديدة: {}\n\nيرجى تغيير كلمة المرور بعد تسجيل الدخول.",
        "no_email_config": "إعدادات البريد الإلكتروني غير متوفرة."
    }
}

if "lang" not in st.session_state:
    st.session_state["lang"] = "tr"

def t(key):
    lang = st.session_state["lang"]
    return TRANS.get(lang, TRANS["tr"]).get(key, key)

# --- ÖZEL CSS ---
def inject_custom_css():
    rtl_css = "direction: rtl; text-align: right;" if st.session_state["lang"] == "ar" else ""
    st.markdown(f"""
        <style>
            :root {{ --primary-color: #93022E; --bg-color: #151515; --secondary-bg: #1E1E1E; --text-color: #E0E0E0; }}
            .stApp {{ background-color: var(--bg-color); color: var(--text-color); {rtl_css} }}
            [data-testid="stHeader"] {{ background-color: var(--bg-color); }}
            h1, h2, h3 {{ color: white !important; font-weight: 700; }}
            div.stButton > button:first-child {{ background-color: var(--primary-color); color: white !important; border: 1px solid var(--primary-color); border-radius: 6px; padding: 0.75rem 1.5rem; font-weight: 600; transition: all 0.2s ease; width: 100%; }}
            div.stButton > button:first-child:hover {{ background-color: #B00338; border-color: #B00338; box-shadow: 0 0 10px rgba(147, 2, 46, 0.6); }}
            div[data-testid="column"] button {{ padding: 0.2rem 0.5rem !important; font-size: 0.8rem; }}
            [data-testid="baseButton-secondary"] {{ background-color: transparent !important; color: #FFFFFF !important; border: 1px solid #555 !important; }}
            [data-testid="baseButton-secondary"]:hover {{ border-color: var(--primary-color) !important; color: var(--primary-color) !important; }}
            .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stDateInput input {{ background-color: #252525 !important; color: white !important; border: 1px solid #444 !important; border-radius: 6px; {rtl_css} }}
            [data-testid="stDataFrame"] {{ background-color: #1E1E1E; border: 1px solid #333; border-radius: 6px; }}
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {{ background-color: var(--secondary-bg); padding: 1.5rem; border-radius: 8px; border: 1px solid #333; }}
            .streamlit-expanderHeader {{ background-color: #252525 !important; color: white !important; }}
            .stCheckbox label {{ color: white !important; }}
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- ŞİFRELEME ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# --- E-POSTA GÖNDERİM FONKSİYONU ---
def send_email(to_email, username, new_password):
    if "email" not in st.secrets:
        return False, t("no_email_config")
    
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    
    subject = t("mail_subject")
    body = t("mail_body").format(username, new_password)
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True, "OK"
    except Exception as e:
        return False, str(e)

# --- DB BAĞLANTISI ---
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
                st.error(f"Secrets: {e}")
                st.stop()
        elif os.path.exists('license-machinerydb-firebase-adminsdk-fbsvc-7458edd97c.json'):
            cred = credentials.Certificate('license-machinerydb-firebase-adminsdk-fbsvc-7458edd97c.json')
            firebase_admin.initialize_app(cred)
        else:
            st.error("Lisans yok!")
            st.stop()
    return firestore.client()

try:
    db = init_db()
except Exception as e:
    st.error(f"DB Error: {e}")
    st.stop()

# --- İLK KURULUM ---
def update_or_create_admin():
    users_ref = db.collection('system_users')
    doc = users_ref.document("admin").get()
    full_perms = ["view", "search", "add", "update", "delete", "delete_table", "upload", "report", "logs", "transfer", "admin_panel"]
    if not doc.exists:
        # Varsayılan admin e-postası boş
        admin_data = {"username": "admin", "password": make_hashes("123456"), "email": "admin@example.com", "role": "admin", "permissions": full_perms}
        users_ref.document("admin").set(admin_data)
    else:
        current_data = doc.to_dict()
        current_perms = current_data.get("permissions", [])
        if "transfer" not in current_perms:
            users_ref.document("admin").update({"permissions": full_perms})

update_or_create_admin()

# --- LOG ---
def log_kayit_ekle(islem_turu, fonksiyon_adi, mesaj, teknik_detay="-"):
    kullanici = st.session_state.get("username", "System")
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

# --- HELPERS ---
def get_table_list():
    return [coll.id for coll in db.collections() if coll.id not in ["system_users", "system_settings", "transfer_loglari"]]

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

def sayfa_degistir(sayfa_adi):
    st.session_state["aktif_sayfa"] = sayfa_adi
    st.rerun()

def set_lang(lang_code):
    st.session_state["lang"] = lang_code
    st.rerun()

def generate_temp_password(length=8):
    """Rastgele geçici şifre oluşturur"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for i in range(length))

# --- ANA UYGULAMA ---
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["permissions"] = []
        st.session_state["role"] = ""
    
    if "aktif_sayfa" not in st.session_state:
        st.session_state["aktif_sayfa"] = "Ana Sayfa"

    # --- DİL BUTONLARI ---
    h1, h2 = st.columns([8, 2])
    with h2:
        c_tr, c_ar, c_en = st.columns(3)
        if c_tr.button("TR 🇹🇷"): set_lang("tr")
        if c_ar.button("ARB 🇪🇬"): set_lang("ar")
        if c_en.button("ENG 🇺🇸"): set_lang("en")

    # --- GİRİŞ EKRANI & ŞİFRE SIFIRLAMA ---
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; color: #93022E;'>ALMAXTEX</h1>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='text-align: center;'>{t('login_title')}</h4>", unsafe_allow_html=True)
            st.write("")
            
            # Giriş Sekmesi ve Şifre Sıfırlama Sekmesi
            tab_login, tab_reset = st.tabs([t("login_title"), t("forgot_pass")])
            
            with tab_login:
                username = st.text_input(t("username"))
                password = st.text_input(t("password"), type="password")
                st.write("")
                if st.button(t("login_btn"), use_container_width=True):
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
                            st.success(t("success_login"))
                            st.rerun()
                        else: st.error(t("err_pass"))
                    else: st.error(t("err_user"))
            
            with tab_reset:
                st.info("Kullanıcı adınızı ve e-posta adresinizi girin.")
                r_user = st.text_input(t("username"), key="r_user")
                r_email = st.text_input(t("email"), key="r_email")
                
                if st.button(t("send_reset_link"), use_container_width=True):
                    if r_user and r_email:
                        user_ref = db.collection("system_users").document(r_user)
                        user_doc = user_ref.get()
                        
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            # E-Posta Kontrolü (Veritabanındaki ile eşleşiyor mu?)
                            stored_email = user_data.get("email", "")
                            
                            if stored_email == r_email:
                                # 1. Yeni Geçici Şifre Oluştur
                                new_pass = generate_temp_password()
                                # 2. DB'yi Güncelle
                                user_ref.update({"password": make_hashes(new_pass)})
                                # 3. E-Posta Gönder
                                success, msg = send_email(r_email, r_user, new_pass)
                                
                                if success:
                                    st.success(t("reset_success"))
                                else:
                                    st.error(f"{t('email_error')} ({msg})")
                            else:
                                st.error(t("reset_fail"))
                        else:
                            st.error(t("reset_fail"))
                    else:
                        st.warning("Lütfen alanları doldurun.")

        return

    # --- HEADER ---
    top_col1, top_col2 = st.columns([6, 1])
    with top_col1:
        st.markdown(f"### 👋 **{st.session_state['username']}**")
    with top_col2:
        if st.button(t("logout_btn"), type="secondary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["aktif_sayfa"] = "Ana Sayfa"
            st.rerun()
    st.divider()

    secim = st.session_state["aktif_sayfa"]
    permissions = st.session_state["permissions"]

    # --- DASHBOARD ---
    if secim == "Ana Sayfa":
        st.title(t("dashboard"))
        st.info(t("dashboard_desc"))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if "view" in permissions:
                if st.button(t("menu_view"), use_container_width=True): sayfa_degistir("Tablo Görüntüleme")
            if "update" in permissions:
                if st.button(t("menu_update"), use_container_width=True): sayfa_degistir("Kayıt Güncelle")
            if "upload" in permissions:
                if st.button(t("menu_upload"), use_container_width=True): sayfa_degistir("Toplu Tablo Yükle (Excel)")
            if "admin_panel" in permissions:
                if st.button(t("menu_admin"), use_container_width=True): sayfa_degistir("Kullanıcı Yönetimi (Admin)")

        with col2:
            if "search" in permissions:
                if st.button(t("menu_search"), use_container_width=True): sayfa_degistir("Arama & Filtreleme")
            if "transfer" in permissions: 
                if st.button(t("menu_transfer"), use_container_width=True): sayfa_degistir("Makine Transferi")
            if "delete" in permissions:
                if st.button(t("menu_delete"), use_container_width=True): sayfa_degistir("Kayıt Silme")
            if "report" in permissions:
                if st.button(t("menu_report"), use_container_width=True): sayfa_degistir("Raporlar")

        with col3:
            if "add" in permissions:
                if st.button(t("menu_add"), use_container_width=True): sayfa_degistir("Yeni Kayıt Ekle")
            if "delete_table" in permissions:
                if st.button(t("menu_del_table"), use_container_width=True): sayfa_degistir("Tablo Silme")
            if "logs" in permissions:
                if st.button(t("menu_logs"), use_container_width=True): sayfa_degistir("Log Kayıtları")

    # --- ALT SAYFALAR ---
    else:
        if st.button(t("back_home"), type="secondary"):
            sayfa_degistir("Ana Sayfa")
        st.write("")

        # 1. TABLO GÖRÜNTÜLEME
        if secim == "Tablo Görüntüleme":
            st.header(t("menu_view"))
            tablolar = get_table_list()
            if tablolar:
                tablo = st.selectbox(t("select_table"), tablolar)
                docs = list(db.collection(tablo).stream())
                data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                if data: 
                    st.info(f"{t('total_records')} {len(data)}")
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                else: st.warning(t("warning_empty"))
            else: st.warning(t("warning_no_table"))

        # 2. ARAMA VE FİLTRELEME
        elif secim == "Arama & Filtreleme":
            st.header(t("menu_search"))
            tablolar = get_table_list()
            if tablolar:
                secilen_tablo = st.selectbox(t("select_table"), tablolar)
                docs = db.collection(secilen_tablo).stream()
                data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                if data:
                    df = pd.DataFrame(data)
                    c1, c2 = st.columns(2)
                    with c1:
                        cols = [c for c in df.columns if "Unnamed" not in str(c) and c != "Dokuman_ID"]
                        secilen_sutun = st.selectbox(t("col_search"), cols)
                    with c2:
                        aranan = st.text_input(t("val_search"))
                    if aranan:
                        try:
                            res = df[df[secilen_sutun].astype(str).str.contains(aranan, case=False, na=False)]
                            st.success(f"{len(res)} {t('res_found')}")
                            st.dataframe(res, use_container_width=True)
                        except: st.error(t("error"))
                    else: st.dataframe(df, use_container_width=True)
            else: st.warning(t("warning_no_table"))

        # 3. MAKİNE TRANSFERİ
        elif secim == "Makine Transferi":
            st.header(t("menu_transfer"))
            
            transfer_docs = list(db.collection('transfer_loglari').stream())
            transfer_data = [d.to_dict() for d in transfer_docs]
            if transfer_data:
                df_transfer = pd.DataFrame(transfer_data)
                bugun = datetime.date.today()
                df_transfer['Geri_Alim_Tarihi'] = pd.to_datetime(df_transfer['Geri_Alim_Tarihi']).dt.date
                
                gecikenler = df_transfer[df_transfer['Geri_Alim_Tarihi'] < bugun]
                yaklasanlar = df_transfer[(df_transfer['Geri_Alim_Tarihi'] > bugun) & (df_transfer['Geri_Alim_Tarihi'] <= bugun + datetime.timedelta(days=3))]
                
                uc1, uc2 = st.columns(2)
                if not gecikenler.empty:
                    uc1.error(f"{t('late_alert')} {len(gecikenler)}")
                    with uc1.expander("Detay"): st.dataframe(gecikenler[['Makine_Info', 'Hedef_Lokasyon']])
                if not yaklasanlar.empty:
                    uc2.info(f"{t('soon_alert')} {len(yaklasanlar)}")
                
                st.subheader(t("transfer_log_title"))
                st.dataframe(df_transfer, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer) as writer: df_transfer.to_excel(writer, index=False)
                st.download_button(t("download_excel"), data=buffer.getvalue(), file_name="Transfer_Log.xlsx", mime="application/vnd.ms-excel")
                st.divider()

            with st.expander(t("loc_mgmt")):
                loc_list = get_locations()
                c1, c2 = st.columns(2)
                with c1:
                    nl = st.text_input(t("new_loc"))
                    if st.button(t("add")) and add_location(nl): st.rerun()
                with c2:
                    dl = st.selectbox(t("delete"), loc_list)
                    if st.button(t("delete")) and remove_location(dl): st.rerun()
            
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox(t("select_table"), tablolar)
                docs = db.collection(target).stream()
                data = [{"Dokuman_ID": doc.id, "Seç": False, **doc.to_dict()} for doc in docs]
                if data:
                    df = pd.DataFrame(data)
                    if 'Lokasyon' not in df.columns: df['Lokasyon'] = "-"
                    cols = ['Seç', 'Lokasyon'] + [c for c in df.columns if c not in ['Seç', 'Lokasyon', 'Dokuman_ID']]
                    edited = st.data_editor(df[cols + ['Dokuman_ID']], column_config={"Seç": st.column_config.CheckboxColumn(default=False), "Dokuman_ID": st.column_config.TextColumn(disabled=True), "Lokasyon": st.column_config.TextColumn(disabled=True)}, disabled=[c for c in df.columns if c != 'Seç'], hide_index=True, use_container_width=True)
                    
                    sel = edited[edited['Seç'] == True]
                    if not sel.empty:
                        st.info(f"{t('select_rows')} {len(sel)}")
                        c_d1, c_d2, c_l = st.columns(3)
                        with c_d1: gt = st.date_input(t("date_send"), datetime.date.today())
                        with c_d2: dt = st.date_input(t("date_return"), datetime.date.today() + datetime.timedelta(days=7))
                        with c_l: tl = st.selectbox(t("target_loc"), get_locations())
                        
                        sure = (dt - gt).days
                        if sure < 0: st.error(t("err_date"))
                        else:
                            st.write(f"{t('duration')} **{sure}**")
                            if st.button(t("transfer_btn")):
                                prog = st.progress(0)
                                cnt = 0
                                for i, r in sel.iterrows():
                                    db.collection(target).document(r['Dokuman_ID']).update({'Lokasyon': tl})
                                    log_ref = db.collection('transfer_loglari').document()
                                    log_ref.set({
                                        "Makine_ID": r['Dokuman_ID'],
                                        "Makine_Info": r.get('Seri No', r['Dokuman_ID']),
                                        "Hedef_Lokasyon": tl,
                                        "Gonderim_Tarihi": str(gt),
                                        "Geri_Alim_Tarihi": str(dt),
                                        "Transfer_Eden": st.session_state["username"]
                                    })
                                    cnt+=1
                                    prog.progress(cnt/len(sel))
                                st.success(t("transfer_success"))
                                st.rerun()
                else: st.warning(t("warning_empty"))

        # 4. YENİ KAYIT EKLEME
        elif secim == "Yeni Kayıt Ekle":
            st.header(t("menu_add"))
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox(t("select_table"), tablolar)
                doc_id = st.text_input("ID (Opsiyonel):")
                c1, c2 = st.columns(2)
                with c1:
                    seri = st.text_input("Seri No")
                    dept = st.text_input("Departman")
                    lok = st.selectbox("Lokasyon", get_locations())
                    kul = st.text_input("Kullanıcı")
                    pcid = st.text_input("PC ID")
                with c2:
                    pcad = st.text_input("PC Adı")
                    ver = st.text_input("Versiyon")
                    durum = st.text_input("Son Durum")
                    notlar = st.text_input("Notlar")
                    icerik = st.text_input("İçerik")
                if st.button(t("save")):
                    data = {"Seri No": seri, "Departman": dept, "Lokasyon": lok, "Kullanıcı": kul, "Kullanıcı PC ID": pcid, "Kullanıcı PC Adı": pcad, "Versiyon": ver, "Son Durum": durum, "Notlar": notlar, "İçerik": icerik, "Kayit_Tarihi": datetime.datetime.now().strftime("%d.%m.%Y")}
                    try:
                        if doc_id: db.collection(target).document(doc_id).set(data)
                        else: db.collection(target).add(data)
                        st.success(t("success"))
                        log_kayit_ekle("EKLEME", "add", f"Kayıt Eklendi", f"Tablo: {target}")
                    except Exception as e: st.error(f"{t('error')} {e}")

        # 5. KAYIT GÜNCELLEME
        elif secim == "Kayıt Güncelle":
            st.header(t("menu_update"))
            st.info(t("excel_mode_info"))
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox(t("select_table"), tablolar)
                docs = db.collection(target).stream()
                data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                if data:
                    edited = st.data_editor(pd.DataFrame(data), num_rows="fixed", column_config={"Dokuman_ID": st.column_config.TextColumn(disabled=True)}, use_container_width=True)
                    if st.button(t("save_changes")):
                        prog = st.progress(0)
                        for i, row in edited.iterrows():
                            db.collection(target).document(row['Dokuman_ID']).set(row.drop('Dokuman_ID').to_dict(), merge=True)
                            prog.progress((i+1)/len(edited))
                        st.success(t("success"))
                        log_kayit_ekle("GÜNCELLEME", "update", f"Tablo Güncellendi: {target}")
                        st.rerun()

        # 6. KAYIT SİLME
        elif secim == "Kayıt Silme":
            st.header(t("menu_delete"))
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox(t("select_table"), tablolar)
                docs = db.collection(target).stream()
                data = [{"Dokuman_ID": doc.id, "Seç": False, **doc.to_dict()} for doc in docs]
                if data:
                    df = pd.DataFrame(data)
                    cols = ['Seç'] + [c for c in df.columns if c != 'Seç']
                    edited = st.data_editor(df[cols], column_config={"Seç": st.column_config.CheckboxColumn(default=False), "Dokuman_ID": st.column_config.TextColumn(disabled=True)}, disabled=[c for c in df.columns if c != 'Seç'], hide_index=True, use_container_width=True)
                    silinecekler = edited[edited['Seç']==True]
                    if not silinecekler.empty:
                        st.error(f"{t('select_rows')} {len(silinecekler)}")
                        if st.button(t("del_selected")):
                            prog = st.progress(0)
                            for i, row in silinecekler.iterrows():
                                db.collection(target).document(row['Dokuman_ID']).delete()
                                prog.progress((i+1)/len(silinecekler))
                            st.success(t("success"))
                            log_kayit_ekle("SİLME", "delete", f"{len(silinecekler)} Kayıt Silindi", f"Tablo: {target}")
                            st.rerun()

        # 7. TABLO SİLME
        elif secim == "Tablo Silme":
            st.header(t("menu_del_table"))
            st.error(t("del_warning"))
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox(t("select_table"), tablolar)
                docs = list(db.collection(target).stream())
                st.warning(f"{t('total_records')} {len(docs)}")
                if len(docs) > 0:
                    if st.text_input(f"{t('confirm_del_table')} '{target}'") == target:
                        if st.button(t("delete")):
                            prog = st.progress(0)
                            for i, doc in enumerate(docs):
                                doc.reference.delete()
                                prog.progress((i+1)/len(docs))
                            st.success(t("success"))
                            log_kayit_ekle("KRITIK_SILME", "delete_table", f"Tablo Silindi: {target}")
                            st.rerun()
                else:
                    if st.button("Boş Tabloyu Kaldır"):
                        st.success(t("success"))
                        st.rerun()

        # 8. EXCEL YÜKLEME
        elif secim == "Toplu Tablo Yükle (Excel)":
            st.header(t("menu_upload"))
            file = st.file_uploader("Dosya:", type=["xlsx", "xls"])
            if file and st.button("Başlat"):
                try:
                    sheets = pd.read_excel(file, sheet_name=None)
                    prog = st.progress(0)
                    for i, (name, df) in enumerate(sheets.items()):
                        st.write(f"Yükleniyor: {name}")
                        df = df.dropna(how='all', axis=1).dropna(how='all', axis=0).fillna('None')
                        df.columns = df.columns.astype(str).str.strip()
                        batch = db.batch()
                        count = 0
                        for _, row in df.iterrows():
                            batch.set(db.collection(name).document(), row.to_dict())
                            count += 1
                            if count % 400 == 0:
                                batch.commit()
                                batch = db.batch()
                        batch.commit()
                        prog.progress((i+1)/len(sheets))
                    st.success(t("success"))
                    log_kayit_ekle("YUKLEME", "upload", "Excel Yüklendi", f"Dosya: {file.name}")
                except Exception as e: st.error(f"{t('error')} {e}")

        # 9. RAPORLAR
        elif secim == "Raporlar":
            st.header(t("menu_report"))
            tablo = st.selectbox(t("select_table"), get_table_list())
            if st.button("Analiz Et"):
                docs = db.collection(tablo).stream()
                data = [doc.to_dict() for doc in docs]
                if data:
                    df = pd.DataFrame(data).fillna("-")
                    st.write(f"{t('total_records')} {len(df)}")
                    c1, c2 = st.columns(2)
                    with c1:
                        sutun = st.selectbox("Grupla:", df.columns)
                        if sutun: st.bar_chart(df[sutun].value_counts())
                    with c2:
                        if 'Versiyon' in df.columns:
                            st.bar_chart(df['Versiyon'].value_counts(), horizontal=True)
                    import io
                    buff = io.BytesIO()
                    with pd.ExcelWriter(buff) as writer: df.to_excel(writer, index=False)
                    st.download_button(t("download_excel"), data=buff.getvalue(), file_name=f"Rapor_{tablo}.xlsx", mime="application/vnd.ms-excel")

        # 10. LOGLAR
        elif secim == "Log Kayıtları":
            st.header(t("menu_logs"))
            if os.path.exists("Sistem_Loglari.xlsx"):
                st.dataframe(pd.read_excel("Sistem_Loglari.xlsx").sort_index(ascending=False), use_container_width=True)
            else: st.info("Log yok.")

        # 11. ADMIN PANELİ
        elif secim == "Kullanıcı Yönetimi (Admin)":
            st.header(t("menu_admin"))
            with st.expander(t("new_user_title"), expanded=True):
                with st.form("add_user"):
                    nu = st.text_input(t("username"))
                    np = st.text_input(t("password"), type="password")
                    # YENİ ALAN: E-POSTA
                    ne = st.text_input(t("email")) 
                    nr = st.selectbox(t("role"), ["user", "admin"])
                    st.write(t("perms"))
                    c1, c2, c3, c4 = st.columns(4)
                    perms = []
                    if c1.checkbox("Gör", True): perms.append("view")
                    if c1.checkbox("Ara", True): perms.append("search")
                    if c1.checkbox("Rapor"): perms.append("report")
                    if c2.checkbox("Ekle"): perms.append("add")
                    if c2.checkbox("Güncelle"): perms.append("update")
                    if c2.checkbox("Yükle"): perms.append("upload")
                    if c3.checkbox("Sil (Kayıt)"): perms.append("delete")
                    if c3.checkbox("Sil (Tablo)"): perms.append("delete_table")
                    if c4.checkbox("Log"): perms.append("logs")
                    if c4.checkbox("Transfer"): perms.append("transfer")
                    if nr == "admin": perms.append("admin_panel")
                    
                    if st.form_submit_button(t("create_user")):
                        if nu and np and ne:
                            db.collection("system_users").document(nu).set({
                                "username": nu, 
                                "password": make_hashes(np), 
                                "email": ne, # E-posta kaydediliyor
                                "role": nr, 
                                "permissions": perms
                            })
                            st.success(t("success"))
                            log_kayit_ekle("ADMIN", "create_user", f"Kullanıcı Eklendi: {nu}")
                        else: st.error("Tüm alanları doldurun (Kullanıcı Adı, Şifre, E-posta).")
            
            st.subheader(t("user_list"))
            users = [u.to_dict() for u in db.collection("system_users").stream()]
            if users:
                udf = pd.DataFrame(users).drop(columns=["password"], errors="ignore")
                st.dataframe(udf, use_container_width=True)
                c_del1, c_del2 = st.columns([3,1])
                with c_del1: to_del = st.selectbox(t("delete_user"), udf['username'])
                with c_del2:
                    if st.button(t("delete"), type="secondary", use_container_width=True):
                        if to_del != st.session_state["username"]:
                            db.collection("system_users").document(to_del).delete()
                            st.success(t("success"))
                            st.rerun()
                        else: st.error(t("err_self_del"))

if __name__ == "__main__":
    main()
