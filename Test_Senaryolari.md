# Tiny House Rezervasyon Sistemi - Test Senaryoları

Bu doküman, geliştirilen uygulamanın gereksinimleri karşıladığını kanıtlamak amacıyla hazırlanan test senaryolarını içerir.

## TS-01: Admin Rolü - Kullanıcı Yönetimi Testi
- **Açıklama:** Adminin kullanıcı durumunu değiştirebilmesi ve silebilmesi.
- **Test Adımları:** 
  1. Admin hesabıyla giriş yap.
  2. Kullanıcılar menüsüne tıkla.
  3. Aktif bir kiracı kullanıcısı için "Pasife Çek" butonuna tıkla.
  4. Kullanıcı için "Sil" butonuna tıkla.
- **Beklenen Sonuç:** Kullanıcı durumu güncellenmeli (veritabanında `IsActive=0` olmalı) ve admin bilgilendirilmelidir. İlişkili verisi (rezervasyon) olmayan kullanıcılar başarıyla silinmelidir.

## TS-02: Trigger Testi - Admin Silinemez Kuralı
- **Açıklama:** Veritabanı tetikleyicisinin (trigger), bir adminin silinmesini engelleme testi.
- **Test Adımları:** 
  1. Admin hesabıyla giriş yap.
  2. Kullanıcılar sayfasında, başka bir Admin hesabı (veya kendi hesabı) için "Sil" butonuna tıkla.
- **Beklenen Sonuç:** Ekranda `Silme işlemi başarısız. Bu kullanıcının veritabanında ilişkili kayıtları bulunmaktadır.` veya `Admin yetkisine sahip kullanıcılar silinemez` hatası dönmeli ve işlem veritabanı tarafından iptal edilmelidir.

## TS-03: Ev Sahibi Rolü - İlan Yönetimi Testi
- **Açıklama:** Ev sahibinin yeni bir ilan ekleyebilmesi ve ardından düzenleyebilmesi.
- **Test Adımları:**
  1. Ev sahibi hesabıyla giriş yap.
  2. "Yeni İlan Ekle" formunu doldurup kaydet.
  3. İlanlarım menüsünde "Düzenle" butonuna tıkla, fiyatı değiştir ve kaydet.
- **Beklenen Sonuç:** Yeni ilan `Houses` tablosuna eklenmeli ve fiyat değişikliği veritabanına başarıyla yansımalıdır. (Check kısıtlamasına göre 0'dan küçük fiyat girilirse DB reddetmelidir).

## TS-04: Kiracı Rolü - Çift Rezervasyon (Müsaitlik) Engelleme Testi (Function + SP)
- **Açıklama:** Kiracının, daha önce onaylanmış/bekleyen bir tarihe tekrar rezervasyon yapmaya çalışması.
- **Test Adımları:**
  1. Kiracı olarak giriş yap.
  2. Herhangi bir evin detayına gel ve "10 Eylül - 15 Eylül" için rezervasyon oluştur (Başarılı olur).
  3. Ardından aynı ev için tekrar "12 Eylül - 18 Eylül" arasını seçip rezervasyon isteği yolla.
- **Beklenen Sonuç:** `sp_AddReservation` yordamı içerisindeki `fn_CheckHouseAvailability` fonksiyonu evin dolu olduğunu tespit etmeli, `RAISERROR` ile hata fırlatmalı ve ekranda "Seçilen tarihler dolu veya geçersiz" uyarısı çıkmalıdır.

## TS-05: Rezervasyon Durumu Güncelleme Testi
- **Açıklama:** Ev sahibinin gelen talebi onaylaması ve adminin bunu görebilmesi.
- **Test Adımları:**
  1. Ev sahibi paneline girip, yeni gelen talebi "Onayla" (Approved) durumuna getir.
  2. Admin paneline gir ve rezervasyonlar listesini kontrol et.
- **Beklenen Sonuç:** Ev sahibi onayladığı an, `Reservations` tablosundaki `Status` güncellenmeli. `trg_AfterReservationUpdate` tetikleyicisi bu durumu `ReservationLogs` tablosuna kaydetmeli. Admin ekranında durum yeşil renkli "Onaylandı" olarak görünmelidir.

## TS-06: Kiracı - Değerlendirme Ekleme Testi
- **Açıklama:** Kiracının onaylanmış ve geçmiş bir rezervasyonuna yorum/puan eklemesi.
- **Test Adımları:**
  1. Kiracı paneline gir ve "Değerlendirmelerim" sayfasına tıkla.
  2. Bekleyen formda puan (5 yıldız) ve yorum girip "Gönder" de.
  3. Ev sahibi hesabına girerek "Yorumlar" sayfasını kontrol et.
- **Beklenen Sonuç:** Yorum `Reviews` tablosuna başarıyla kaydedilmeli, puan check constraint kuralını geçmeli ve ev sahibinin yorumlar ekranında doğrudan görüntülenmelidir.
