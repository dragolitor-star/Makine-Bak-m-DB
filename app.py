import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from google.cloud.firestore_v1.field_path import FieldPath 
import datetime
import traceback
import os
import hashlib
import io # Excel indirme için

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
            :root { --primary-color: #93022E; --bg-color: #151515; --secondary-bg: #1E1E1E; --text-color: #E0E0E0; }
            .stApp { background-color: var(--bg-color); color: var(--text-color); }
            [data-testid="stHeader"] { background-color: var(--bg-color); }
            h1, h2, h3 { color: white !important; font-weight: 700; }
            div.stButton > button:first-child { background-color: var(--primary-color); color: white !important; border: 1px solid var(--primary-color); border-radius: 6px; padding: 0.75rem 1.5rem; font-weight: 600; transition: all 0.2s ease; width: 100%; }
            div.stButton > button:first-child:hover { background-color: #B00338; border-color: #B00338; box-shadow: 0 0 10px rgba(147, 2, 46, 0.6); }
            [data-testid="baseButton-secondary"] { background-color: transparent !important; color: #FFFFFF !important; border: 1px solid #555 !important; }
            [data-testid="baseButton-secondary"]:hover { border-color: var(--primary-color) !important; color: var(--primary-color) !important; }
            .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stDateInput input { background-color: #252525 !important; color: white !important; border: 1px solid #444 !important; border-radius: 6px; }
            [data-testid="stDataFrame"] { background-color: #1E1E1E; border: 1px solid #333; border-radius: 6px; }
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] { background-color: var(--secondary-bg); padding: 1.5rem; border-radius: 8px; border: 1px solid #333; }
            .streamlit-expanderHeader { background-color: #252525 !important; color: white !important; }
            .stCheckbox label { color: white !important; }
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

# --- İLK KURULUM ---
def update_or_create_admin():
    users_ref = db.collection('system_users')
    doc = users_ref.document("admin").get()
    full_perms = ["view", "search", "add", "update", "delete", "delete_table", "upload", "report", "logs", "transfer", "admin_panel"]
    if not doc.exists:
        admin_data = {"username": "admin", "password": make_hashes("123456"), "role": "admin", "permissions": full_perms}
        users_ref.document("admin").set(admin_data)
    else:
        current_data = doc.to_dict()
        current_perms = current_data.get("permissions", [])
        if "transfer" not in current_perms:
            users_ref.document("admin").update({"permissions": full_perms})

update_or_create_admin()

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

    secim = st.session_state["aktif_sayfa"]
    permissions = st.session_state["permissions"]

    # --- DASHBOARD ---
    if secim == "Ana Sayfa":
        st.title("Kontrol Paneli")
        st.info("Yapmak istediğiniz işlemi seçiniz.")
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

    # --- ALT SAYFALAR ---
    else:
        if st.button("⬅️ Geri Dön", type="secondary"):
            sayfa_degistir("Ana Sayfa")
        st.write("")

        # 1. TABLO GÖRÜNTÜLEME
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

        # 2. ARAMA VE FİLTRELEME
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

        # 3. MAKİNE TRANSFERİ (GELİŞTİRİLMİŞ)
        elif secim == "Makine Transferi":
            st.header("🚚 Makine Transfer Takip Sistemi")
            
            # --- BİLGİLENDİRME VE UYARILAR KISMI ---
            # Aktif transferleri 'transfer_loglari' koleksiyonundan çekelim
            # Bu koleksiyonu transfer yapıldıkça oluşturacağız
            transfer_docs = list(db.collection('transfer_loglari').stream())
            transfer_data = [d.to_dict() for d in transfer_docs]
            
            if transfer_data:
                df_transfer = pd.DataFrame(transfer_data)
                
                # Bugünün tarihi
                bugun = datetime.date.today()
                
                # Tarih dönüşümleri (String -> Date)
                df_transfer['Geri_Alim_Tarihi'] = pd.to_datetime(df_transfer['Geri_Alim_Tarihi']).dt.date
                df_transfer['Gonderim_Tarihi'] = pd.to_datetime(df_transfer['Gonderim_Tarihi']).dt.date
                
                # Durum Analizi
                gecikenler = df_transfer[df_transfer['Geri_Alim_Tarihi'] < bugun]
                bugun_donus = df_transfer[df_transfer['Geri_Alim_Tarihi'] == bugun]
                yaklasanlar = df_transfer[(df_transfer['Geri_Alim_Tarihi'] > bugun) & (df_transfer['Geri_Alim_Tarihi'] <= bugun + datetime.timedelta(days=3))]
                
                # UYARI KARTLARI
                uc1, uc2, uc3 = st.columns(3)
                if not gecikenler.empty:
                    uc1.error(f"🚨 GECİKEN TRANSFERLER: {len(gecikenler)} Adet")
                    with uc1.expander("Detaylar"):
                        st.dataframe(gecikenler[['Makine_Info', 'Hedef_Lokasyon', 'Geri_Alim_Tarihi']])
                else:
                    uc1.success("Geciken transfer yok.")
                    
                if not bugun_donus.empty:
                    uc2.warning(f"⚠️ BUGÜN DÖNMESİ GEREKEN: {len(bugun_donus)} Adet")
                    with uc2.expander("Detaylar"):
                        st.dataframe(bugun_donus[['Makine_Info', 'Hedef_Lokasyon']])
                else:
                    uc2.info("Bugün dönüşü planlanan yok.")
                    
                if not yaklasanlar.empty:
                    uc3.info(f"📅 Yakında Dönecekler (3 Gün): {len(yaklasanlar)} Adet")
                else:
                    uc3.info("Yakın tarihte dönüş yok.")
                
                st.divider()
                
                # TRANSFER GEÇMİŞİ TABLOSU
                st.subheader("📋 Tüm Transfer Kayıtları")
                
                # Süre hesaplamaları (Görselleştirme için)
                df_transfer['Kalan_Gun'] = (df_transfer['Geri_Alim_Tarihi'] - bugun).apply(lambda x: x.days)
                df_transfer['Durum'] = df_transfer['Kalan_Gun'].apply(lambda x: "Gecikti" if x < 0 else ("Bugün" if x == 0 else f"{x} Gün Kaldı"))
                
                st.dataframe(df_transfer, use_container_width=True)
                
                # Excel İndir
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_transfer.to_excel(writer, index=False, sheet_name='Transferler')
                st.download_button("📥 Transfer Listesini İndir (Excel)", data=buffer.getvalue(), file_name=f"Transfer_Listesi_{bugun}.xlsx", mime="application/vnd.ms-excel")
                
                st.divider()

            # --- YENİ TRANSFER İŞLEMİ ---
            st.subheader("Yeni Transfer Başlat")
            
            # Lokasyon Yönetimi
            with st.expander("⚙️ Lokasyon Yönetimi"):
                loc_list = get_locations()
                c1, c2 = st.columns(2)
                with c1:
                    nl = st.text_input("Yeni Lokasyon:")
                    if st.button("Ekle") and add_location(nl): st.rerun()
                with c2:
                    dl = st.selectbox("Silinecek:", loc_list)
                    if st.button("Sil") and remove_location(dl): st.rerun()
            
            tablolar = get_table_list()
            if tablolar:
                target_table = st.selectbox("Transfer Yapılacak Tablo:", tablolar)
                docs = db.collection(target_table).stream()
                data = [{"Dokuman_ID": doc.id, "Seç": False, **doc.to_dict()} for doc in docs]
                
                if data:
                    df = pd.DataFrame(data)
                    if 'Lokasyon' not in df.columns: df['Lokasyon'] = "-"
                    
                    # Makine Seçim Tablosu
                    cols = ['Seç', 'Lokasyon'] + [c for c in df.columns if c not in ['Seç', 'Lokasyon', 'Dokuman_ID']]
                    edited = st.data_editor(
                        df[cols + ['Dokuman_ID']], 
                        column_config={
                            "Seç": st.column_config.CheckboxColumn("Transfer?", default=False),
                            "Dokuman_ID": st.column_config.TextColumn(disabled=True),
                            "Lokasyon": st.column_config.TextColumn(disabled=True)
                        },
                        disabled=[c for c in df.columns if c != 'Seç'],
                        hide_index=True, 
                        use_container_width=True
                    )
                    
                    sel = edited[edited['Seç'] == True]
                    
                    if not sel.empty:
                        st.info(f"{len(sel)} kayıt seçildi. Transfer detaylarını giriniz:")
                        
                        c_date1, c_date2, c_loc = st.columns(3)
                        with c_date1:
                            gonderim_tar = st.date_input("Gönderim Tarihi", datetime.date.today())
                        with c_date2:
                            donus_tar = st.date_input("Tahmini Geri Alım Tarihi", datetime.date.today() + datetime.timedelta(days=7))
                        with c_loc:
                            hedef_lokasyon = st.selectbox("Hedef Lokasyon:", get_locations())
                        
                        # Süre Hesabı
                        sure = (donus_tar - gonderim_tar).days
                        if sure < 0:
                            st.error("Hata: Dönüş tarihi gönderim tarihinden önce olamaz!")
                        else:
                            st.success(f"⏱️ Görevlendirilen Süre: **{sure} Gün**")
                            
                            if st.button(f"TRANSFERİ ONAYLA ({len(sel)} Makine)"):
                                try:
                                    prog = st.progress(0)
                                    cnt = 0
                                    batch = db.batch()
                                    
                                    for i, r in sel.iterrows():
                                        doc_id = r['Dokuman_ID']
                                        
                                        # 1. Ana Tabloda Lokasyonu Güncelle
                                        doc_ref = db.collection(target_table).document(doc_id)
                                        doc_ref.update({'Lokasyon': hedef_lokasyon})
                                        
                                        # 2. Transfer Loguna Kayıt At (Takip İçin)
                                        log_ref = db.collection('transfer_loglari').document()
                                        # Makineyi tanımlayacak bir bilgi bulalım (Seri No varsa onu, yoksa ID)
                                        makine_info = r.get('Seri No', r.get('Makine Adı', doc_id))
                                        
                                        transfer_data = {
                                            "Tablo": target_table,
                                            "Makine_ID": doc_id,
                                            "Makine_Info": makine_info,
                                            "Kaynak_Lokasyon": r.get('Lokasyon', '-'),
                                            "Hedef_Lokasyon": hedef_lokasyon,
                                            "Gonderim_Tarihi": str(gonderim_tar),
                                            "Geri_Alim_Tarihi": str(donus_tar),
                                            "Gorev_Suresi_Gun": sure,
                                            "Transfer_Eden": st.session_state["username"],
                                            "Islem_Zamani": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        }
                                        log_ref.set(transfer_data)
                                        
                                        cnt += 1
                                        prog.progress(cnt / len(sel))
                                    
                                    st.success(f"Transfer Tamamlandı! {cnt} makine '{hedef_lokasyon}' konumuna atandı.")
                                    log_kayit_ekle("TRANSFER", "machine_transfer", f"{cnt} Makine -> {hedef_lokasyon} ({sure} Gün)", f"Tablo: {target_table}")
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Transfer sırasında hata: {e}")
                    else:
                        st.info("Transfer edilecek makineleri listeden seçiniz.")
                else: st.warning("Boş.")

        # 4. YENİ KAYIT EKLEME
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
                    lok = st.selectbox("Lokasyon", get_locations())
                    kul = st.text_input("Kullanıcı")
                    pcid = st.text_input("PC ID")
                with c2:
                    pcad = st.text_input("PC Adı")
                    ver = st.text_input("Versiyon")
                    durum = st.text_input("Son Durum")
                    notlar = st.text_input("Notlar")
                    icerik = st.text_input("İçerik")
                if st.button("Kaydet"):
                    data = {"Seri No": seri, "Departman": dept, "Lokasyon": lok, "Kullanıcı": kul, "Kullanıcı PC ID": pcid, "Kullanıcı PC Adı": pcad, "Versiyon": ver, "Son Durum": durum, "Notlar": notlar, "İçerik": icerik, "Kayit_Tarihi": datetime.datetime.now().strftime("%d.%m.%Y")}
                    try:
                        if doc_id: db.collection(target).document(doc_id).set(data)
                        else: db.collection(target).add(data)
                        st.success("Eklendi!")
                        log_kayit_ekle("EKLEME", "add", f"Kayıt Eklendi", f"Tablo: {target}")
                    except Exception as e: st.error(f"Hata: {e}")

        # 5. KAYIT GÜNCELLEME
        elif secim == "Kayıt Güncelle":
            st.header("✏️ Kayıt Güncelleme")
            st.info("Değişiklik yapıp 'Kaydet'e basın.")
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox("Tablo:", tablolar)
                docs = db.collection(target).stream()
                data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                if data:
                    edited = st.data_editor(pd.DataFrame(data), num_rows="fixed", column_config={"Dokuman_ID": st.column_config.TextColumn(disabled=True)}, use_container_width=True)
                    if st.button("💾 Değişiklikleri Kaydet"):
                        prog = st.progress(0)
                        for i, row in edited.iterrows():
                            db.collection(target).document(row['Dokuman_ID']).set(row.drop('Dokuman_ID').to_dict(), merge=True)
                            prog.progress((i+1)/len(edited))
                        st.success("Güncellendi!")
                        log_kayit_ekle("GÜNCELLEME", "update", f"Tablo Güncellendi: {target}")
                        st.rerun()

        # 6. KAYIT SİLME
        elif secim == "Kayıt Silme":
            st.header("🗑️ Kayıt Silme")
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox("Tablo:", tablolar)
                docs = db.collection(target).stream()
                data = [{"Dokuman_ID": doc.id, "Seç": False, **doc.to_dict()} for doc in docs]
                if data:
                    df = pd.DataFrame(data)
                    cols = ['Seç'] + [c for c in df.columns if c != 'Seç']
                    edited = st.data_editor(df[cols], column_config={"Seç": st.column_config.CheckboxColumn(default=False), "Dokuman_ID": st.column_config.TextColumn(disabled=True)}, disabled=[c for c in df.columns if c != 'Seç'], hide_index=True, use_container_width=True)
                    silinecekler = edited[edited['Seç']==True]
                    if not silinecekler.empty:
                        st.error(f"{len(silinecekler)} kayıt seçildi.")
                        if st.button("SEÇİLİLERİ SİL"):
                            prog = st.progress(0)
                            for i, row in silinecekler.iterrows():
                                db.collection(target).document(row['Dokuman_ID']).delete()
                                prog.progress((i+1)/len(silinecekler))
                            st.success("Silindi!")
                            log_kayit_ekle("SİLME", "delete", f"{len(silinecekler)} Kayıt Silindi", f"Tablo: {target}")
                            st.rerun()

        # 7. TABLO SİLME
        elif secim == "Tablo Silme":
            st.header("💣 Tablo Silme")
            st.error("Dikkat: Geri alınamaz!")
            tablolar = get_table_list()
            if tablolar:
                target = st.selectbox("Tablo:", tablolar)
                docs = list(db.collection(target).stream())
                st.warning(f"Kayıt Sayısı: {len(docs)}")
                if len(docs) > 0:
                    if st.text_input(f"Onay için '{target}' yazın:") == target:
                        if st.button("SİL"):
                            prog = st.progress(0)
                            for i, doc in enumerate(docs):
                                doc.reference.delete()
                                prog.progress((i+1)/len(docs))
                            st.success("Tablo Silindi.")
                            log_kayit_ekle("KRITIK_SILME", "delete_table", f"Tablo Silindi: {target}")
                            st.rerun()
                else:
                    if st.button("Boş Tabloyu Kaldır"):
                        st.success("Temizlendi.")
                        st.rerun()

        # 8. EXCEL YÜKLEME
        elif secim == "Toplu Tablo Yükle (Excel)":
            st.header("📤 Excel Yükle")
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
                    st.success("Tamamlandı!")
                    log_kayit_ekle("YUKLEME", "upload", "Excel Yüklendi", f"Dosya: {file.name}")
                except Exception as e: st.error(f"Hata: {e}")

        # 9. RAPORLAR
        elif secim == "Raporlar":
            st.header("📊 Raporlar")
            tablo = st.selectbox("Tablo:", get_table_list())
            if st.button("Analiz Et"):
                docs = db.collection(tablo).stream()
                data = [doc.to_dict() for doc in docs]
                if data:
                    df = pd.DataFrame(data).fillna("-")
                    st.write(f"Toplam: {len(df)}")
                    c1, c2 = st.columns(2)
                    with c1:
                        sutun = st.selectbox("Grupla:", df.columns)
                        if sutun: st.bar_chart(df[sutun].value_counts())
                    with c2:
                        if 'Versiyon' in df.columns:
                            st.write("Versiyon Dağılımı")
                            st.bar_chart(df['Versiyon'].value_counts(), horizontal=True)
                    import io
                    buff = io.BytesIO()
                    with pd.ExcelWriter(buff) as writer: df.to_excel(writer, index=False)
                    st.download_button("Excel İndir", data=buff.getvalue(), file_name=f"Rapor_{tablo}.xlsx", mime="application/vnd.ms-excel")

        # 10. LOGLAR
        elif secim == "Log Kayıtları":
            st.header("📝 Loglar")
            if os.path.exists("Sistem_Loglari.xlsx"):
                st.dataframe(pd.read_excel("Sistem_Loglari.xlsx").sort_index(ascending=False), use_container_width=True)
            else: st.info("Log yok.")

        # 11. ADMIN PANELİ
        elif secim == "Kullanıcı Yönetimi (Admin)":
            st.header("👑 Kullanıcı Yönetimi")
            with st.expander("Yeni Kullanıcı Ekle", expanded=True):
                with st.form("add_user"):
                    nu = st.text_input("Kullanıcı Adı")
                    np = st.text_input("Şifre", type="password")
                    nr = st.selectbox("Rol", ["user", "admin"])
                    st.write("Yetkiler:")
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
                    if st.form_submit_button("Oluştur"):
                        if nu and np:
                            db.collection("system_users").document(nu).set({"username": nu, "password": make_hashes(np), "role": nr, "permissions": perms})
                            st.success(f"{nu} eklendi.")
                            log_kayit_ekle("ADMIN", "create_user", f"Kullanıcı Eklendi: {nu}")
                        else: st.error("Eksik bilgi.")
            st.subheader("Kullanıcı Listesi")
            users = [u.to_dict() for u in db.collection("system_users").stream()]
            if users:
                udf = pd.DataFrame(users).drop(columns=["password"], errors="ignore")
                st.dataframe(udf, use_container_width=True)
                c_del1, c_del2 = st.columns([3,1])
                with c_del1: to_del = st.selectbox("Silinecek Kullanıcı:", udf['username'])
                with c_del2:
                    if st.button("Kullanıcıyı Sil", type="secondary", use_container_width=True):
                        if to_del != st.session_state["username"]:
                            db.collection("system_users").document(to_del).delete()
                            st.success("Silindi.")
                            st.rerun()
                        else: st.error("Kendinizi silemezsiniz.")

if __name__ == "__main__":
    main()
