# Tiny House Rezervasyon ve Yönetim Sistemi - Proje Dokümanı

## 1. Proje Özeti
Bu proje, kullanıcıların tiny house konseptindeki evleri inceleyip rezervasyon yapabildiği, ev sahiplerinin ilanlarını yönetebildiği ve sistem yöneticisinin (Admin) tüm verileri kontrol altında tuttuğu 3 rollü (Admin, Ev Sahibi, Kiracı) bir rezervasyon yönetim sistemidir. 

## 2. Kullanılan Teknolojiler
- **Veritabanı:** Microsoft SQL Server (MSSQL).
- **Backend:** Python (Flask Framework).
- **Frontend:** HTML, CSS, JavaScript (Jinja2 ile sunucu tarafı render).

## 3. Sistem Mimarisi ve Veritabanı Yapısı
Sistem `TinyHaosueDB` adlı MSSQL veritabanı etrafında kurgulanmıştır.
Gereksinimlerde istenilen tüm veritabanı kısıtlamaları ve mantıksal kontroller veritabanı seviyesinde (SQL) yapılmıştır. Backend (Python), sadece SQL Server'dan dönen veriyi işler ve SQL hatalarını yakalar.

### Veritabanı Unsurları:
- **Normalizasyon:** 3. Normal Form (3NF) kuralına uyularak; Kullanıcılar, Roller, Evler, Rezervasyonlar, Yorumlar ve Loglar ayrıştırılmıştır.
- **Stored Procedures (SP):** `sp_AddReservation` (Rezervasyon Ekleme) ve `sp_UpdateUserStatus` (Kullanıcı Durumu Değiştirme) aktif olarak kullanıldı.
- **Functions:** `fn_CheckHouseAvailability` (Tarihsel müsaitlik kontrolü) ve `fn_CalculateTotalIncome` (Kazanç hesaplama) fonksiyonları ile backend kod yükü azaltılarak hesaplamalar veritabanına devredildi.
- **Triggers:** `trg_AfterReservationUpdate` ile onaylanan/reddedilen rezervasyonların logu tutuldu. `trg_PreventAdminDelete` ile sistem güvenliği gereği Admin yetkisindeki birinin silinmesi veritabanı motoru seviyesinde engellendi.
- **Constraints (Kısıtlamalar):** İlgili Foreign Key ve Primary Key yapılarına ek olarak; UNIQUE (Email), CHECK (PricePerNight > 0, EndDate > StartDate, Rating: 1-5) ve NOT NULL kısıtlamaları zorunlu kılındı.

## 4. Kullanıcı Rolleri ve Gerçekleştirilen İşlevler
1. **Admin:** Sistemdeki toplam veriyi ve finansal durumu dashboard üzerinde görebilir. Kullanıcıları aktif/pasif hale getirebilir veya silebilir. İlanları yayından kaldırabilir ve yapılan rezervasyonları iptal edebilir.
2. **Ev Sahibi (Host):** Sisteme yeni bir Tiny House ilanı ekleyebilir, mevcut ilanlarının açıklamasını veya fiyatını düzenleyebilir, yayından kaldırabilir. Kendisine gelen rezervasyon isteklerini onaylayabilir/reddedebilir ve misafirlerin yorumlarını inceleyebilir. Dashboard ekranında ise toplam evlerini ve net gelirini (sadece onaylanmış olanlardan) anlık olarak görebilir.
3. **Kiracı (Tenant):** Aktif ev ilanları arasında arama yapabilir. Seçtiği bir evin detayına gidip, müsait tarihlerini (çakışma kontrolü SQL üzerinden yapılarak) seçip rezervasyon yapabilir. Gerekirse geçmiş rezervasyonlarını iptal edebilir ve konakladığı eve 1-5 arası yıldız verip yorum yazabilir.

## 5. Proje Sonucu ve Kazanımlar
Bu proje ile karmaşık iş mantıklarının (business logic) uygulama (backend) katmanı yerine doğrudan veritabanı seviyesinde çözülmesinin (SP, Functions, Triggers) ne kadar güvenli ve tutarlı olduğu pratikte deneyimlenmiştir. Arayüz tarafında da modern ve responsive bir HTML/CSS yapısı tercih edilerek rol bazlı güvenli erişim mimarisi başarıyla uygulanmıştır.
