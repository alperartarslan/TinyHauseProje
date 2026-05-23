# Tiny House Rezervasyon Sistemi - ER Diyagramı ve Veritabanı Yapısı

Bu doküman, projede oluşturduğumuz `TinyHaosueDB` veritabanının varlık-ilişki (ER) yapısını açıklar. Proje raporunuza eklemek üzere bu yapıyı bir çizim aracıyla (Draw.io, Lucidchart vb.) görselleştirebilirsiniz.

## Tablolar ve İlişkiler

### 1. Roles (Roller) Tablosu
Sistemdeki kullanıcı yetkilerini belirler.
- `RoleId` (PK) - INT
- `RoleName` - NVARCHAR (Admin, Ev Sahibi, Kiraci)

### 2. Users (Kullanıcılar) Tablosu
Sisteme kayıtlı olan tüm kullanıcıları tutar.
- `UserId` (PK) - INT
- `RoleId` (FK) -> `Roles(RoleId)` (1'e Çok İlişki: Bir rolün birden çok kullanıcısı olabilir)
- `FirstName`, `LastName`, `Email`, `PasswordHash`, `IsActive`, `CreatedAt`

### 3. Houses (Evler/İlanlar) Tablosu
Ev sahiplerinin sisteme eklediği tiny house ilanlarını tutar.
- `HouseId` (PK) - INT
- `HostId` (FK) -> `Users(UserId)` (1'e Çok İlişki: Bir kullanıcının/ev sahibinin birden fazla evi olabilir)
- `Title`, `Description`, `PricePerNight`, `Location`, `IsActive`, `CreatedAt`

### 4. Reservations (Rezervasyonlar) Tablosu
Kiracıların evler için oluşturduğu rezervasyon kayıtlarını tutar.
- `ReservationId` (PK) - INT
- `HouseId` (FK) -> `Houses(HouseId)` (1'e Çok İlişki: Bir evin birden fazla rezervasyonu olabilir)
- `TenantId` (FK) -> `Users(UserId)` (1'e Çok İlişki: Bir kiracının birden fazla rezervasyonu olabilir)
- `StartDate`, `EndDate`, `TotalPrice`, `Status` (Pending, Approved, Rejected, Cancelled)

### 5. Reviews (Yorumlar ve Puanlar) Tablosu
Kiracıların konakladıkları evlere yaptıkları değerlendirmeler.
- `ReviewId` (PK) - INT
- `ReservationId` (FK) -> `Reservations(ReservationId)` (Bire Bir İlişki: Her rezervasyon için 1 yorum yapılabilir)
- `Rating` (1-5 arası), `Comment`

### 6. ReservationLogs (Log Tablosu)
Trigger ile otomatik çalışan, rezervasyonların durum değişikliklerini (Örn: Pending -> Approved) kaydeden denetim tablosu.
- `LogId` (PK) - INT
- `ReservationId` (FK değil, referans), `OldStatus`, `NewStatus`, `LogDate`

---

## Veritabanı Nesneleri (Database Objects)

### Fonksiyonlar (Functions)
1. **`fn_CheckHouseAvailability`**: Seçilen tarih aralığında ilgili evin başka onaylanmış rezervasyonu olup olmadığını denetler. (1=Müsait, 0=Dolu).
2. **`fn_CalculateTotalIncome`**: Ev sahibinin onaylanmış rezervasyonlarından elde ettiği toplam ciroyu anlık hesaplar.

### Saklı Yordamlar (Stored Procedures)
1. **`sp_AddReservation`**: İş kuralı mantığını veritabanında çalıştırarak güvenli rezervasyon yapar. İçerisinde fiyat hesaplar ve müsaitlik fonksiyonunu çağırır. Müsait değilse RAISERROR ile hata fırlatır.
2. **`sp_UpdateUserStatus`**: Adminin kullanıcıları aktif/pasif duruma getirmesini sağlayan yordamdır.

### Tetikleyiciler (Triggers)
1. **`trg_AfterReservationUpdate`**: Rezervasyonların durumu değiştiğinde (`UPDATE` işlemi), önceki ve sonraki durumu `ReservationLogs` tablosuna kaydeder.
2. **`trg_PreventAdminDelete`**: `INSTEAD OF DELETE` yapısıyla, sistemde 'Admin' rolüne sahip kullanıcıların `DELETE` komutuyla silinmesini engeller. Hata fırlatarak sadece pasife çekilmelerini zorunlu kılar.
