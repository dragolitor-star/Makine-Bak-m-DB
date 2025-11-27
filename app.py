import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
# --- İMPORT DÜZELTMESİ (Kesin Çözüm) ---
# FieldPath'i direkt çağırmak yerine modül olarak alıyoruz
from google.cloud import firestore as gc_firestore
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
        # 1. Streamlit Secrets Kontrolü
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
        
        # 2. Local Dosya Kontrolü
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
        "Tarih_Saat": [zaman],
        "İşlem_Türü": [islem_turu],
        "Fonksiyon": [fonksiyon_adi],
        "Mesaj": [mesaj],
        "Teknik_Detay": [teknik_detay]
    }
    df_yeni = pd.DataFrame(yeni_kayit)
    try:
        if os.path.exists(log_dosya_adi):
            df_eski = pd.read_excel(log_dosya_adi)
            df_guncel = pd.concat([df_eski, df_yeni], ignore_index=True)
            df_guncel.to_excel(log_dosya_adi, index=False)
        else:
            df_yeni.to_excel(log_dosya_adi, index=False)
    except:
        pass

# --- YARDIMCI FONKSİYONLAR ---
def get_table_list():
    koleksiyonlar = db.collections()
    return [coll.id for coll in koleksiyonlar]

def get_columns_of_table(table_name):
    docs = db.collection(table_name).limit(1).stream()
    for doc in docs:
        return list(doc.to_dict().keys())
    return []

# --- ANA UYGULAMA ---
def main():
    st.title("🏭 Almaxtex Konfeksiyon Makine Bakım Veritabanı")
    
    st.sidebar.header("İşlem Menüsü")
    secim = st.sidebar.radio("Yapmak İstediğiniz İşlem:", 
        ["Ana Sayfa", "Tablo Görüntüleme", "Arama & Filtreleme", 
         "Yeni Kayıt Ekle", "Kayıt Güncelle", "Kayıt Silme", 
         "Toplu Tablo Yükle (Excel)", "Raporlar", "Log Kayıtları"])

    # 1. TABLO GÖRÜNTÜLEME
    if secim == "Tablo Görüntüleme":
        st.header("📂 Tablo Görüntüleme")
        tablolar = get_table_list()
        if tablolar:
            secilen_tablo = st.selectbox("Görüntülemek istediğiniz tabloyu seçin:", tablolar)
            if st.button("Tabloyu Getir"):
                with st.spinner('Veriler çekiliyor...'):
                    docs = db.collection(secilen_tablo).stream()
                    data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                    if data:
                        st.dataframe(pd.DataFrame(data), use_container_width=True)
                    else:
                        st.warning("Bu tablo boş.")
        else:
            st.warning("Veritabanında henüz tablo yok.")

    # 2. ARAMA VE FİLTRELEME
    elif secim == "Arama & Filtreleme":
        st.header("🔍 Arama ve Filtreleme")
        tablolar = get_table_list()
        if tablolar:
            col1, col2 = st.columns(2)
            with col1:
                secilen_tablo = st.selectbox("Tablo Seçin:", tablolar)
            with col2:
                raw_sutunlar = get_columns_of_table(secilen_tablo)
                # Unnamed sütunları gizle
                sutunlar = [col for col in raw_sutunlar if "Unnamed" not in str(col)]
                secilen_sutun = st.selectbox("Hangi Sütunda Arama Yapılacak?", sutunlar) if sutunlar else None
            
            aranan_deger = st.text_input("Aranacak Değeri Girin:")
            
            if st.button("Ara / Filtrele"):
                if secilen_sutun and aranan_deger:
                    try:
                        # Sayısal kontrol
                        try:
                            val = float(aranan_deger)
                        except ValueError:
                            val = aranan_deger
                        
                        # --- DÜZELTME BURADA ---
                        # gc_firestore.FieldPath(...) kullanarak güvenli çağırma yapıyoruz.
                        docs = db.collection(secilen_tablo).where(gc_firestore.FieldPath(secilen_sutun), "==", val).stream()
                        
                        data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                        
                        if data:
                            st.success(f"{len(data)} sonuç bulundu.")
                            st.dataframe(pd.DataFrame(data), use_container_width=True)
                        else:
                            st.warning("Kriterlere uygun kayıt bulunamadı.")
                    except Exception as e:
                        st.error(f"Hata: {e}")
        else:
            st.warning("Tablo bulunamadı.")

    # 3. YENİ KAYIT EKLEME
    elif secim == "Yeni Kayıt Ekle":
        st.header("➕ Yeni Kayıt Ekle")
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Hangi tabloya eklenecek?", tablolar)
            doc_id_input = st.text_input("Kayıt ID (Boş bırakırsanız otomatik atanır):")
            
            st.subheader("Kayıt Bilgileri")
            col1, col2 = st.columns(2)
            with col1:
                seri_no = st.text_input("Seri No")
                departman = st.text_input("Departman")
                lokasyon = st.text_input("Lokasyon")
                kullanici = st.text_input("Kullanıcı")
                pc_id = st.text_input("Kullanıcı PC ID")
            with col2:
                pc_adi = st.text_input("Kullanıcı PC Adı")
                versiyon = st.text_input("Versiyon")
                son_durum = st.text_input("Son Durum")
                notlar = st.text_input("Notlar")
                icerik = st.text_input("İçerik")

            if st.button("Kaydı Veritabanına Ekle"):
                new_data = {
                    "Seri No": seri_no, "Departman": departman, "Lokasyon": lokasyon,
                    "Kullanıcı": kullanici, "Kullanıcı PC ID": pc_id, "Kullanıcı PC Adı": pc_adi,
                    "Versiyon": versiyon, "Son Durum": son_durum, "Notlar": notlar, "İçerik": icerik,
                    "Kayit_Tarihi": datetime.datetime.now().strftime("%d.%m.%Y")
                }
                try:
                    if doc_id_input:
                        db.collection(target_table).document(doc_id_input).set(new_data)
                    else:
                        db.collection(target_table).add(new_data)
                    st.success("Kayıt başarıyla eklendi!")
                    log_kayit_ekle("EKLEME", "web_add_new", "Yeni Kayıt Eklendi", f"Tablo: {target_table}")
                except Exception as e:
                    st.error(f"Kayıt eklenirken hata oluştu: {e}")

    # 4. KAYIT GÜNCELLEME (EXCEL MODU)
    elif secim == "Kayıt Güncelle":
        st.header("✏️ Kayıt Güncelleme (Excel Modu)")
        st.info("Tablo üzerindeki verileri değiştirip 'Değişiklikleri Kaydet' butonuna basın.")
        
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Tablo Seçin:", tablolar)
            docs = db.collection(target_table).stream()
            data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
            
            if data:
                df = pd.DataFrame(data)
                edited_df = st.data_editor(
                    df,
                    key="data_editor",
                    num_rows="fixed",
                    column_config={
                        "Dokuman_ID": st.column_config.TextColumn("Sistem ID", disabled=True)
                    },
                    use_container_width=True,
                    height=500
                )

                if st.button("💾 Değişiklikleri Kaydet"):
                    try:
                        progress_bar = st.progress(0)
                        total_rows = len(edited_df)
                        updated_count = 0
                        
                        for index, row in edited_df.iterrows():
                            doc_id = row['Dokuman_ID']
                            update_data = row.drop('Dokuman_ID').to_dict()
                            db.collection(target_table).document(doc_id).set(update_data, merge=True)
                            updated_count += 1
                            progress_bar.progress((index + 1) / total_rows)
                            
                        st.success(f"İşlem Tamamlandı! {updated_count} satır kontrol edildi ve güncellendi.")
                        log_kayit_ekle("GÜNCELLEME", "web_modify_bulk", f"Tablo Düzenlendi: {target_table}", "")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Güncelleme hatası: {e}")
            else:
                st.warning("Bu tablo boş.")

    # 5. KAYIT SİLME (CHECKBOX MODU)
    elif secim == "Kayıt Silme":
        st.header("🗑️ Kayıt Silme (Çoklu Seçim)")
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Tablo Seçin:", tablolar)
            docs = db.collection(target_table).stream()
            data = []
            for doc in docs:
                d = doc.to_dict()
                d['Dokuman_ID'] = doc.id
                d['Seç'] = False
                data.append(d)
            
            if data:
                df = pd.DataFrame(data)
                cols = ['Seç'] + [col for col in df.columns if col != 'Seç']
                df = df[cols]

                st.info("Silmek istediğiniz kayıtların başındaki kutucuğu işaretleyin.")
                
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Seç": st.column_config.CheckboxColumn("Sil?", default=False),
                        "Dokuman_ID": st.column_config.TextColumn("ID", disabled=True)
                    },
                    disabled=[col for col in df.columns if col != 'Seç'],
                    hide_index=True,
                    use_container_width=True
                )

                silinecekler = edited_df[edited_df['Seç'] == True]
                
                if not silinecekler.empty:
                    st.error(f"DİKKAT: Toplam {len(silinecekler)} kayıt seçildi.")
                    with st.expander("Silinecek Kayıtları Gör"):
                        st.dataframe(silinecekler.drop('Seç', axis=1))
                    
                    if st.button(f"SEÇİLİ {len(silinecekler)} KAYDI SİL"):
                        try:
                            progress_bar = st.progress(0)
                            count = 0
                            for index, row in silinecekler.iterrows():
                                db.collection(target_table).document(row['Dokuman_ID']).delete()
                                count += 1
                                progress_bar.progress(count / len(silinecekler))
                            
                            st.success(f"{count} kayıt silindi.")
                            log_kayit_ekle("SİLME", "web_remove_bulk", f"{count} Kayıt Silindi", f"Tablo: {target_table}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Silme hatası: {e}")
            else:
                st.warning("Kayıt yok.")

    # 6. EXCEL YÜKLEME
    elif secim == "Toplu Tablo Yükle (Excel)":
        st.header("📤 Excel'den Toplu Veri Yükleme")
        uploaded_file = st.file_uploader("Excel Dosyasını Sürükleyip Bırakın", type=["xlsx", "xls"])
        
        if uploaded_file:
            if st.button("Yüklemeyi Başlat"):
                try:
                    tum_sayfalar = pd.read_excel(uploaded_file, sheet_name=None)
                    progress_bar = st.progress(0)
                    total_sheets = len(tum_sayfalar)
                    current_sheet = 0

                    for sayfa_adi, df in tum_sayfalar.items():
                        st.write(f"İşleniyor: {sayfa_adi}...")
                        df = df.dropna(axis=1, how='all').dropna(axis=0, how='all').fillna('None')
                        df.columns = df.columns.astype(str).str.strip()
                        
                        batch = db.batch()
                        count = 0
                        for _, row in df.iterrows():
                            doc_ref = db.collection(sayfa_adi).document()
                            batch.set(doc_ref, row.to_dict())
                            count += 1
                            if count % 400 == 0:
                                batch.commit()
                                batch = db.batch()
                        batch.commit()
                        current_sheet += 1
                        progress_bar.progress(current_sheet / total_sheets)
                    
                    st.success("Yükleme Tamamlandı!")
                    log_kayit_ekle("BİLGİ", "web_upload", "Excel Yüklendi", f"Dosya: {uploaded_file.name}")
                except Exception as e:
                    st.error(f"Hata: {e}")

    # 7. RAPORLAR
    elif secim == "Raporlar":
        st.header("📊 Raporlar")
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Analiz edilecek tablo:", tablolar)
            docs = db.collection(target_table).stream()
            data = [doc.to_dict() for doc in docs]
            
            if data:
                df = pd.DataFrame(data).fillna("-")
                st.write(f"Toplam Kayıt: {len(df)}")
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Sütun Bazlı Dağılım")
                    sutun = st.selectbox("Gruplanacak Sütun:", df.columns)
                    if sutun:
                        st.bar_chart(df[sutun].value_counts())
                with col2:
                    st.subheader("Versiyon Analizi")
                    if 'Versiyon' in df.columns:
                        st.bar_chart(df['Versiyon'].value_counts(), horizontal=True)
                    else:
                        st.info("'Versiyon' sütunu yok.")
                
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Rapor')
                st.download_button("📥 Excel Olarak İndir", data=buffer.getvalue(), file_name=f"Rapor_{target_table}.xlsx", mime="application/vnd.ms-excel")
            else:
                st.warning("Tablo boş.")

    # 8. LOGLAR
    elif secim == "Log Kayıtları":
        st.header("📝 Loglar")
        if os.path.exists("Sistem_Loglari.xlsx"):
            st.dataframe(pd.read_excel("Sistem_Loglari.xlsx").sort_index(ascending=False), use_container_width=True)
        else:
            st.info("Log yok.")

    else:
        st.markdown("### 👋 Hoşgeldiniz\nSoldaki menüden işlem seçebilirsiniz.")

if __name__ == "__main__":
    main()
