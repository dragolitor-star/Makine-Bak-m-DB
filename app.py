import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from google.cloud.firestore_v1.base_query import FieldFilter
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

# --- VERİTABANI BAĞLANTISI (Önbellekli) ---
@st.cache_resource
def init_db():
    if not firebase_admin._apps:
        # Önce Streamlit Secrets içinde 'firebase' bilgisi var mı diye bakar (Bulut için)
        if "firebase" in st.secrets:
            # Secrets'tan gelen veriyi sözlük (dict) olarak alır
            firebase_creds = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_creds)
        
        # Yoksa yerel dosya var mı diye bakar (Localhost için)
        elif os.path.exists('license-machinerydb-firebase-adminsdk-fbsvc-7458edd97c.json'):
            cred = credentials.Certificate('license-machinerydb-firebase-adminsdk-fbsvc-7458edd97c.json')
        
        else:
            st.error("Firebase lisans anahtarı bulunamadı!")
            st.stop()
            
        firebase_admin.initialize_app(cred)

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
    except Exception as e:
        # Web ortamında print yerine st.error kullanılabilir ama akışı bozmamak için pass geçiyoruz
        pass

# --- YARDIMCI FONKSİYONLAR ---
def get_table_list():
    """Mevcut koleksiyonları listeler"""
    koleksiyonlar = db.collections()
    return [coll.id for coll in koleksiyonlar]

def get_columns_of_table(table_name):
    """Bir tablonun sütun isimlerini çeker"""
    docs = db.collection(table_name).limit(1).stream()
    for doc in docs:
        return list(doc.to_dict().keys())
    return []

# --- ANA UYGULAMA ---
def main():
    st.title("🏭 Almaxtex Konfeksiyon Makine Bakım Veritabanı")
    
    # --- YAN MENÜ ---
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
                    data = []
                    for doc in docs:
                        d = doc.to_dict()
                        d['Dokuman_ID'] = doc.id
                        data.append(d)
                    
                    if data:
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True)
                        st.info(f"Toplam {len(df)} kayıt listelendi.")
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
                sutunlar = get_columns_of_table(secilen_tablo)
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
                        
                        docs = db.collection(secilen_tablo).where(filter=FieldFilter(secilen_sutun, "==", val)).stream()
                        data = []
                        for doc in docs:
                            d = doc.to_dict()
                            d['Dokuman_ID'] = doc.id
                            data.append(d)
                        
                        if data:
                            df = pd.DataFrame(data)
                            st.success(f"{len(df)} sonuç bulundu.")
                            st.dataframe(df, use_container_width=True)
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
                versiyon = st.text_input("Versiyon") # Sayısal işlem gerekirse st.number_input
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

    # 4. KAYIT GÜNCELLEME
    elif secim == "Kayıt Güncelle":
        st.header("✏️ Kayıt Güncelleme")
        st.info("Önce tabloyu seçin, ID'yi bulun, ardından güncellemek istediğiniz alanı girin.")
        
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Tablo Seçin:", tablolar)
            
            # Kullanıcıya kolaylık olsun diye önce verileri gösterelim
            with st.expander("Tablodaki Verileri Görüntüle (ID Bulmak İçin)"):
                docs = db.collection(target_table).limit(50).stream()
                data = [{"Dokuman_ID": doc.id, **doc.to_dict()} for doc in docs]
                if data:
                    st.dataframe(pd.DataFrame(data))

            col1, col2 = st.columns(2)
            with col1:
                doc_id = st.text_input("Değiştirilecek Dokuman ID'sini yapıştırın:")
            with col2:
                sutunlar = get_columns_of_table(target_table)
                field_name = st.selectbox("Değiştirilecek Sütun:", sutunlar) if sutunlar else st.text_input("Sütun Adı:")

            new_val = st.text_input("Yeni Değer:")

            if st.button("Güncelle"):
                if doc_id and field_name:
                    try:
                        # Sayısal dönüşüm denemesi
                        try:
                            val_to_write = float(new_val)
                        except:
                            val_to_write = new_val

                        doc_ref = db.collection(target_table).document(doc_id)
                        if doc_ref.get().exists:
                            from google.cloud.firestore import FieldPath
                            doc_ref.update({FieldPath(field_name): val_to_write})
                            st.success("Güncelleme Başarılı!")
                            log_kayit_ekle("GÜNCELLEME", "web_modify", f"Kayıt Güncellendi: {doc_id}", f"{field_name} -> {new_val}")
                        else:
                            st.error("Bu ID'ye sahip döküman bulunamadı.")
                    except Exception as e:
                        st.error(f"Hata: {e}")

    # 5. KAYIT SİLME
    elif secim == "Kayıt Silme":
        st.header("🗑️ Kayıt Silme")
        st.warning("Bu işlem geri alınamaz!")
        
        tablolar = get_table_list()
        if tablolar:
            target_table = st.selectbox("Tablo Seçin:", tablolar)
            doc_id = st.text_input("Silinecek Dokuman ID:")
            
            if st.button("Kaydı Sil"):
                if doc_id:
                    try:
                        db.collection(target_table).document(doc_id).delete()
                        st.success("Kayıt silindi.")
                        log_kayit_ekle("SİLME", "web_remove", f"Kayıt Silindi: {doc_id}", f"Tablo: {target_table}")
                    except Exception as e:
                        st.error(f"Silme hatası: {e}")

    # 6. EXCEL'DEN TOPLU YÜKLEME
    elif secim == "Toplu Tablo Yükle (Excel)":
        st.header("📤 Excel'den Toplu Veri Yükleme")
        st.info("Yükleyeceğiniz Excel dosyasındaki her sayfa (sheet) ayrı bir tablo olarak kaydedilecektir.")
        
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
                        
                        # Temizlik
                        df = df.dropna(axis=1, how='all')
                        df = df.dropna(axis=0, how='all')
                        df = df.fillna('None')
                        df.columns = df.columns.astype(str).str.strip()
                        
                        # Yükleme
                        batch = db.batch()
                        count = 0
                        for _, row in df.iterrows():
                            doc_ref = db.collection(sayfa_adi).document()
                            batch.set(doc_ref, row.to_dict())
                            count += 1
                            if count % 400 == 0: # Firestore batch limiti 500
                                batch.commit()
                                batch = db.batch()
                        batch.commit()
                        
                        current_sheet += 1
                        progress_bar.progress(current_sheet / total_sheets)
                    
                    st.success("Tüm sayfalar başarıyla yüklendi!")
                    log_kayit_ekle("BİLGİ", "web_upload", "Excel Yüklendi", f"Dosya: {uploaded_file.name}")
                    
                except Exception as e:
                    st.error(f"Yükleme hatası: {e}")
                    log_kayit_ekle("HATA", "web_upload", str(e), traceback.format_exc())

    # 7. RAPORLAR
    elif secim == "Raporlar":
        st.header("📊 Raporlar ve Analizler")
        tablolar = get_table_list()
        
        if tablolar:
            target_table = st.selectbox("Analiz edilecek tablo:", tablolar)
            
            # Veriyi çek
            docs = db.collection(target_table).stream()
            data = [doc.to_dict() for doc in docs]
            
            if data:
                df = pd.DataFrame(data)
                df = df.fillna("-")
                
                st.write(f"Toplam Kayıt: {len(df)}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Sütun Bazlı Dağılım")
                    sutun = st.selectbox("Gruplanacak Sütun:", df.columns)
                    if sutun:
                        chart_data = df[sutun].value_counts()
                        st.bar_chart(chart_data)
                        st.dataframe(chart_data)
                
                with col2:
                    st.subheader("Versiyon Analizi")
                    if 'Versiyon' in df.columns:
                        pie_data = df['Versiyon'].value_counts()
                        st.write("Versiyon Dağılımı")
                        st.bar_chart(pie_data, horizontal=True) # veya st.plotly_chart ile pasta grafik
                    else:
                        st.info("Bu tabloda 'Versiyon' sütunu yok.")
                
                # Excel İndirme Butonu
                # Pandas DataFrame'i Excel bytes'a çevirme
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Rapor')
                    
                st.download_button(
                    label="📥 Bu Tabloyu Excel Olarak İndir",
                    data=buffer.getvalue(),
                    file_name=f"Rapor_{target_table}.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.warning("Tablo boş.")

    # 8. LOGLAR
    elif secim == "Log Kayıtları":
        st.header("📝 Sistem Logları")
        if os.path.exists("Sistem_Loglari.xlsx"):
            df_log = pd.read_excel("Sistem_Loglari.xlsx")
            st.dataframe(df_log.sort_index(ascending=False), use_container_width=True) # En son kayıt en üstte
        else:
            st.info("Henüz log kaydı bulunmuyor.")
            
    # ANA SAYFA
    else:
        st.markdown("""
        ### 👋 Hoşgeldiniz
        Bu panel üzerinden makine, personel ve lisans envanterini yönetebilirsiniz.
        
        **Neler Yapabilirsiniz?**
        * 🔍 **Arama:** Detaylı filtreleme ile kayıt bulun.
        * ➕ **Ekleme:** Tek tek veya Excel ile toplu veri yükleyin.
        * 📊 **Rapor:** Anlık grafiklerle durumu analiz edin.
        * 🌍 **Erişim:** Bu sayfayı tarayıcı olan her yerden kullanabilirsiniz.
        """)

if __name__ == "__main__":
    main()