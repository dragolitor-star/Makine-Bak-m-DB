import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from google.cloud.firestore_v1.field_path import FieldPath 
import datetime
import traceback
import os

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Almaxtex Envanter Yönetimi",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# --- LOGLAMA FONKSİYONU ---
def log_kayit_ekle(islem_turu, fonksiyon_adi, mesaj, teknik_detay="-"):
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
    return [coll.id for coll in db.collections()]

def get_columns_of_table(table_name):
    docs = db.collection(table_name).limit(1).stream()
    for doc in docs: return list(doc.to_dict().keys())
    return []

# --- ANA UYGULAMA ---
def main():
    st.title("🏭 Almaxtex Konfeksiyon Makine Bakım Veritabanı")
    st.sidebar.header("İşlem Menüsü")
    
    # MENÜYE "Tablo Silme" EKLENDİ
    secim = st.sidebar.radio("İşlem Seçin:", 
                             ["Ana Sayfa", "Tablo Görüntüleme", "Arama & Filtreleme", 
                              "Yeni Kayıt Ekle", "Kayıt Güncelle", "Kayıt Silme", 
                              "Tablo Silme", # YENİ
                              "Toplu Tablo Yükle (Excel)", "Raporlar", "Log Kayıtları"])

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
                else:
                    st.dataframe(df, use_container_width=True)
            else: st.warning("Bu tablo boş.")
        else: st.warning("Tablo yok.")

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
                    total = len(edited_df)
                    for i, row in edited_df.iterrows():
                        db.collection(target).document(row['Dokuman_ID']).set(row.drop('Dokuman_ID').to_dict(), merge=True)
                        prog.progress((i + 1) / total)
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

    # 6. TABLO SİLME (YENİ EKLENDİ)
    elif secim == "Tablo Silme":
        st.header("💣 Tablo Silme (Tüm Veri)")
        st.error("DİKKAT: Bu işlem geri alınamaz! Seçilen tabloyu ve içindeki tüm verileri kalıcı olarak siler.")
        
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Silinecek Tabloyu Seçin:", tablolar)
            
            # Veri sayısını gösterelim
            docs = list(db.collection(target_table).stream())
            kayit_sayisi = len(docs)
            st.warning(f"Seçilen Tablo: **{target_table}** | İçindeki Kayıt Sayısı: **{kayit_sayisi}**")
            
            if kayit_sayisi > 0:
                # Güvenlik Onayı: Tablo adını yazdır
                confirmation = st.text_input(f"Onaylamak için tablonun adını ({target_table}) aynen yazın:")
                
                if st.button("TABLOYU KALICI OLARAK SİL"):
                    if confirmation == target_table:
                        try:
                            progress_bar = st.progress(0)
                            batch = db.batch()
                            deleted_count = 0
                            
                            for doc in docs:
                                doc.reference.delete()
                                deleted_count += 1
                                # Görsel ilerleme
                                progress_bar.progress(deleted_count / kayit_sayisi)
                            
                            st.success(f"'{target_table}' tablosu başarıyla silindi.")
                            log_kayit_ekle("KRİTİK_SİLME", "web_delete_table", f"Tablo Silindi: {target_table}", f"Silinen Kayıt: {deleted_count}")
                            
                            st.rerun()
                        except Exception as e:
                            st.error(f"Silme hatası: {e}")
                    else:
                        st.error("Tablo adı eşleşmedi. İşlem iptal edildi.")
            else:
                # Boş tablo (Aslında Firestore'da boş tablo olmaz ama yine de)
                if st.button("Boş Tabloyu Temizle"):
                     # Boş olsa bile streamlit listesinde görünüyorsa önbellek temizlenmeli
                     st.success("Tablo zaten boş.")
                     st.rerun()
        else:
            st.warning("Silinecek tablo bulunamadı.")

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
                        doc_ref = db.collection(name).document()
                        batch.set(doc_ref, row.to_dict())
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
        tablolar = get_table_list()
        if tablolar:
            tablo = st.selectbox("Tablo:", tablolar)
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
        else: st.warning("Tablo yok.")

    # 9. LOGLAR
    elif secim == "Log Kayıtları":
        st.header("📝 Loglar")
        if os.path.exists("Sistem_Loglari.xlsx"):
            st.dataframe(pd.read_excel("Sistem_Loglari.xlsx").sort_index(ascending=False), use_container_width=True)
        else: st.info("Log yok.")
    
    else: st.markdown("### 👋 Hoşgeldiniz")

if __name__ == "__main__":
    main()
