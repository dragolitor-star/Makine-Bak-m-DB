import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from google.cloud.firestore_v1.field_path import FieldPath 
import datetime
import traceback
import os
import hashlib # Şifreleme için

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Almaxtex Envanter Yönetimi",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ŞİFRELEME FONKSİYONU ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

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
    st.error(f"Veritabanı bağlantı hatası: {e}")
    st.stop()

# --- OTOMATİK İLK KULLANICI OLUŞTURMA (KURULUM) ---
def create_default_admin():
    users_ref = db.collection('system_users')
    docs = users_ref.limit(1).stream()
    if not list(docs): # Eğer hiç kullanıcı yoksa
        admin_data = {
            "username": "admin",
            "password": make_hashes("123456"),
            "role": "admin",
            "permissions": ["view", "search", "add", "update", "delete", "upload", "report", "logs", "admin_panel"]
        }
        users_ref.document("admin").set(admin_data)
        return True
    return False

# Kurulum kontrolü
create_default_admin()

# --- LOGLAMA FONKSİYONU ---
def log_kayit_ekle(islem_turu, fonksiyon_adi, mesaj, teknik_detay="-"):
    # Loglarda kullanıcının kim olduğunu da tutalım
    kullanici = st.session_state.get("username", "Bilinmeyen")
    mesaj = f"[{kullanici}] {mesaj}"
    
    log_dosya_adi = "Sistem_Loglari.xlsx"
    zaman = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    yeni_kayit = {
        "Tarih_Saat": [zaman], "İşlem_Türü": [islem_turu],
        "Fonksiyon": [fonksiyon_adi], "Mesaj": [mesaj], "Teknik_Detay": [teknik_detay]
    }
    try:
        if os.path.exists(log_dosya_adi):
            pd.concat([pd.read_excel(log_dosya_adi), pd.DataFrame(yeni_kayit)], ignore_index=True).to_excel(log_dosya_adi, index=False)
        else:
            pd.DataFrame(yeni_kayit).to_excel(log_dosya_adi, index=False)
    except: pass

# --- YARDIMCI FONKSİYONLAR ---
def get_table_list():
    # system_users tablosunu listede gösterme
    return [coll.id for coll in db.collections() if coll.id != "system_users"]

def get_columns_of_table(table_name):
    docs = db.collection(table_name).limit(1).stream()
    for doc in docs: return list(doc.to_dict().keys())
    return []

# --- ANA UYGULAMA ---
def main():
    # Session State Başlatma
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["permissions"] = []
        st.session_state["role"] = ""

    # --- GİRİŞ EKRANI ---
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.title("🔐 Giriş Yap")
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            
            if st.button("Giriş"):
                user_ref = db.collection("system_users").document(username)
                user_doc = user_ref.get()
                
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    if check_hashes(password, user_data['password']):
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username
                        st.session_state["role"] = user_data.get("role", "user")
                        st.session_state["permissions"] = user_data.get("permissions", [])
                        st.success("Giriş Başarılı!")
                        st.rerun()
                    else:
                        st.error("Hatalı şifre!")
                else:
                    st.error("Kullanıcı bulunamadı!")
        return # Giriş yapılmadıysa aşağıyı çalıştırma

    # --- GİRİŞ YAPILMIŞSA BURADAN DEVAM ET ---
    
    # Kullanıcı Bilgisi ve Çıkış Butonu
    with st.sidebar:
        st.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
        if st.button("Çıkış Yap"):
            st.session_state["logged_in"] = False
            st.rerun()
        st.divider()

    st.title("🏭 Almaxtex Konfeksiyon Makine Bakım Veritabanı")
    st.sidebar.header("İşlem Menüsü")
    
    # --- DİNAMİK MENÜ (YETKİYE GÖRE) ---
    menu_options = ["Ana Sayfa"]
    permissions = st.session_state["permissions"]
    
    if "view" in permissions: menu_options.append("Tablo Görüntüleme")
    if "search" in permissions: menu_options.append("Arama & Filtreleme")
    if "add" in permissions: menu_options.append("Yeni Kayıt Ekle")
    if "update" in permissions: menu_options.append("Kayıt Güncelle")
    if "delete" in permissions: menu_options.append("Kayıt Silme")
    if "delete_table" in permissions: menu_options.append("Tablo Silme")
    if "upload" in permissions: menu_options.append("Toplu Tablo Yükle (Excel)")
    if "report" in permissions: menu_options.append("Raporlar")
    if "logs" in permissions: menu_options.append("Log Kayıtları")
    if "admin_panel" in permissions: menu_options.append("Kullanıcı Yönetimi (Admin)")

    secim = st.sidebar.radio("İşlem Seçin:", menu_options)

    # --- İŞLEM BLOKLARI ---

    # 1. TABLO GÖRÜNTÜLEME
    if secim == "Tablo Görüntüleme":
        st.header("📂 Tablo Görüntüleme")
        tablolar = get_table_list()
        if tablolar:
            tablo = st.selectbox("Tablo Seçin:", tablolar)
            if st.button("Tabloyu Getir"):
                with st.spinner('Veriler yükleniyor...'):
                    docs = db.collection(tablo).stream()
                    data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                    if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
                    else: st.warning("Tablo boş.")
        else: st.warning("Tablo yok.")

    # 2. ARAMA VE FİLTRELEME
    elif secim == "Arama & Filtreleme":
        st.header("🔍 Dinamik Arama ve Filtreleme")
        st.info("Tabloyu seçin, bir sütun belirleyin ve yazmaya başlayın.")
        tablolar = get_table_list()
        if tablolar:
            secilen_tablo = st.selectbox("Tablo Seçin:", tablolar)
            docs = db.collection(secilen_tablo).stream()
            data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
            if data:
                df = pd.DataFrame(data)
                c1, c2 = st.columns(2)
                with c1:
                    cols = [c for c in df.columns if "Unnamed" not in str(c) and c != "Dokuman_ID"]
                    secilen_sutun = st.selectbox("Hangi Sütunda Arama Yapılacak?", cols)
                with c2:
                    aranan = st.text_input("Aranacak Değer:")
                if aranan:
                    try:
                        df_filtered = df[df[secilen_sutun].astype(str).str.contains(aranan, case=False, na=False)]
                        st.success(f"{len(df_filtered)} sonuç bulundu.")
                        st.dataframe(df_filtered, use_container_width=True)
                    except Exception as e: st.error(f"Hata: {e}")
                else: st.dataframe(df, use_container_width=True)
            else: st.warning("Bu tablo boş.")

    # 3. YENİ KAYIT EKLEME
    elif secim == "Yeni Kayıt Ekle":
        st.header("➕ Yeni Kayıt Ekle")
        tablolar = get_table_list()
        if tablolar:
            target = st.selectbox("Tablo:", tablolar)
            doc_id = st.text_input("ID (Boşsa otomatik):")
            st.subheader("Bilgiler")
            c1, c2 = st.columns(2)
            with c1:
                seri = st.text_input("Seri No")
                dept = st.text_input("Departman")
                lok = st.text_input("Lokasyon")
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
                    st.success("Kaydedildi!")
                    log_kayit_ekle("EKLEME", "web_add", "Kayıt Eklendi", f"Tablo: {target}")
                except Exception as e: st.error(f"Hata: {e}")

    # 4. KAYIT GÜNCELLEME
    elif secim == "Kayıt Güncelle":
        st.header("✏️ Kayıt Güncelleme")
        st.info("Hücreleri değiştirip 'Kaydet' butonuna basın.")
        tablolar = get_table_list()
        if tablolar:
            target = st.selectbox("Tablo:", tablolar)
            docs = db.collection(target).stream()
            data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
            if data:
                edited_df = st.data_editor(pd.DataFrame(data), key="editor", num_rows="fixed", column_config={"Dokuman_ID": st.column_config.TextColumn("ID", disabled=True)}, use_container_width=True)
                if st.button("💾 Kaydet"):
                    prog = st.progress(0)
                    for i, row in edited_df.iterrows():
                        db.collection(target).document(row['Dokuman_ID']).set(row.drop('Dokuman_ID').to_dict(), merge=True)
                        prog.progress((i + 1) / len(edited_df))
                    st.success("Güncellendi!")
                    log_kayit_ekle("GÜNCELLEME", "web_update", f"Tablo: {target}", "")
                    st.rerun()
            else: st.warning("Veri yok.")

    # 5. KAYIT SİLME
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
                edited_df = st.data_editor(df[cols], column_config={"Seç": st.column_config.CheckboxColumn("Sil?", default=False), "Dokuman_ID": st.column_config.TextColumn("ID", disabled=True)}, disabled=[c for c in df.columns if c != 'Seç'], hide_index=True, use_container_width=True)
                
                silinecekler = edited_df[edited_df['Seç'] == True]
                if not silinecekler.empty:
                    st.error(f"{len(silinecekler)} kayıt seçildi.")
                    if st.button("SEÇİLİ KAYITLARI SİL"):
                        prog = st.progress(0)
                        count = 0
                        for i, row in silinecekler.iterrows():
                            db.collection(target).document(row['Dokuman_ID']).delete()
                            count += 1
                            prog.progress(count / len(silinecekler))
                        st.success("Silindi!")
                        log_kayit_ekle("SİLME", "web_delete", f"{count} Kayıt Silindi", f"Tablo: {target}")
                        st.rerun()
            else: st.warning("Veri yok.")

    # 6. TABLO SİLME
    elif secim == "Tablo Silme":
        st.header("💣 Tablo Silme")
        st.error("DİKKAT: Bu işlem geri alınamaz!")
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Silinecek Tablo:", tablolar)
            docs = list(db.collection(target_table).stream())
            st.warning(f"Kayıt Sayısı: {len(docs)}")
            if len(docs) > 0:
                if st.text_input(f"Onay için '{target_table}' yazın:") == target_table:
                    if st.button("SİL"):
                        prog = st.progress(0)
                        count = 0
                        for doc in docs:
                            doc.reference.delete()
                            count += 1
                            prog.progress(count / len(docs))
                        st.success("Tablo Silindi.")
                        log_kayit_ekle("KRİTİK_SİLME", "web_delete_table", f"Tablo Silindi: {target_table}", "")
                        st.rerun()
            else:
                if st.button("Boş Tabloyu Kaldır"):
                    st.success("Temizlendi.")
                    st.rerun()

    # 7. EXCEL YÜKLEME
    elif secim == "Toplu Tablo Yükle (Excel)":
        st.header("📤 Excel Yükle")
        file = st.file_uploader("Dosya Seç", type=["xlsx", "xls"])
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
                    prog.progress((i + 1) / len(sheets))
                st.success("Tamamlandı!")
                log_kayit_ekle("YÜKLEME", "web_upload", "Excel Yüklendi", f"Dosya: {file.name}")
            except Exception as e: st.error(f"Hata: {e}")

    # 8. RAPORLAR
    elif secim == "Raporlar":
        st.header("📊 Raporlar")
        tablo = st.selectbox("Tablo:", get_table_list())
        if st.button("Raporu Getir"):
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
            else: st.warning("Veri yok.")

    # 9. LOGLAR
    elif secim == "Log Kayıtları":
        st.header("📝 Loglar")
        if os.path.exists("Sistem_Loglari.xlsx"):
            st.dataframe(pd.read_excel("Sistem_Loglari.xlsx").sort_index(ascending=False), use_container_width=True)
        else: st.info("Log yok.")

    # 10. ADMIN PANELİ (KULLANICI YÖNETİMİ)
    elif secim == "Kullanıcı Yönetimi (Admin)":
        st.header("👑 Kullanıcı Yönetimi")
        
        # Yeni Kullanıcı Ekle
        with st.expander("Yeni Kullanıcı Ekle", expanded=True):
            with st.form("add_user_form"):
                new_user = st.text_input("Kullanıcı Adı")
                new_pass = st.text_input("Şifre", type="password")
                new_role = st.selectbox("Rol", ["user", "admin"])
                st.write("Yetkiler:")
                c1, c2, c3 = st.columns(3)
                perms = []
                if c1.checkbox("Görüntüleme", value=True): perms.append("view")
                if c1.checkbox("Arama", value=True): perms.append("search")
                if c1.checkbox("Raporlama"): perms.append("report")
                if c2.checkbox("Ekleme"): perms.append("add")
                if c2.checkbox("Güncelleme"): perms.append("update")
                if c2.checkbox("Excel Yükleme"): perms.append("upload")
                if c3.checkbox("Silme (Kayıt)"): perms.append("delete")
                if c3.checkbox("Silme (Tablo)"): perms.append("delete_table")
                if c3.checkbox("Log Görme"): perms.append("logs")
                if new_role == "admin": perms.append("admin_panel")

                if st.form_submit_button("Kullanıcıyı Oluştur"):
                    if new_user and new_pass:
                        user_data = {
                            "username": new_user,
                            "password": make_hashes(new_pass),
                            "role": new_role,
                            "permissions": perms
                        }
                        db.collection("system_users").document(new_user).set(user_data)
                        st.success(f"{new_user} oluşturuldu.")
                        log_kayit_ekle("ADMIN", "user_create", f"Kullanıcı Eklendi: {new_user}", "")
                    else:
                        st.error("Kullanıcı adı ve şifre gerekli.")

        # Mevcut Kullanıcıları Listele ve Sil
        st.subheader("Mevcut Kullanıcılar")
        users = db.collection("system_users").stream()
        user_list = [u.to_dict() for u in users]
        
        if user_list:
            user_df = pd.DataFrame(user_list)
            # Şifreleri gizle
            if "password" in user_df.columns: user_df = user_df.drop(columns=["password"])
            
            st.dataframe(user_df, use_container_width=True)
            
            user_to_delete = st.selectbox("Silinecek Kullanıcı:", [u['username'] for u in user_list])
            if st.button("Kullanıcıyı Sil"):
                if user_to_delete != st.session_state["username"]: # Kendini silemezsin
                    db.collection("system_users").document(user_to_delete).delete()
                    st.success("Silindi.")
                    st.rerun()
                else:
                    st.error("Kendinizi silemezsiniz.")

    else:
        st.markdown("### 👋 Hoşgeldiniz")

if __name__ == "__main__":
    main()
