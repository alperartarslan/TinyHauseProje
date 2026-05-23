-- 0. VERİTABANI OLUŞTURMA
IF NOT EXISTS (SELECT name FROM master.dbo.sysdatabases WHERE name = N'TinyHaosueDB')
BEGIN
    CREATE DATABASE TinyHaosueDB;
END
GO

USE TinyHaosueDB;
GO

-- =========================================
-- 1. ESKİ TABLOLARI SİL (FOREIGN KEY SIRASINA GÖRE)
-- =========================================
-- Önce Foreign Key içeren tabloları siliyoruz ki hata vermesin
IF OBJECT_ID('ReservationLogs', 'U') IS NOT NULL DROP TABLE ReservationLogs;
IF OBJECT_ID('Reviews', 'U') IS NOT NULL DROP TABLE Reviews;
IF OBJECT_ID('Reservations', 'U') IS NOT NULL DROP TABLE Reservations;
IF OBJECT_ID('Houses', 'U') IS NOT NULL DROP TABLE Houses;
IF OBJECT_ID('Users', 'U') IS NOT NULL DROP TABLE Users;
IF OBJECT_ID('Roles', 'U') IS NOT NULL DROP TABLE Roles;
GO

-- =========================================
-- 2. TABLOLAR VE KISITLAMALAR (CONSTRAINTS)
-- =========================================

-- Roller Tablosu
CREATE TABLE Roles (
    RoleId INT IDENTITY(1,1) PRIMARY KEY,
    RoleName NVARCHAR(50) NOT NULL UNIQUE
);
GO

-- Varsayılan Rolleri Ekle
INSERT INTO Roles (RoleName) VALUES ('Admin'), ('Ev Sahibi'), ('Kiraci');
GO

-- Kullanıcılar Tablosu
CREATE TABLE Users (
    UserId INT IDENTITY(1,1) PRIMARY KEY,
    RoleId INT NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(255) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Users_Roles FOREIGN KEY (RoleId) REFERENCES Roles(RoleId)
);
GO

-- Evler (Tiny Houses) Tablosu
CREATE TABLE Houses (
    HouseId INT IDENTITY(1,1) PRIMARY KEY,
    HostId INT NOT NULL,
    Title NVARCHAR(100) NOT NULL,
    Description NVARCHAR(MAX),
    PricePerNight DECIMAL(10,2) NOT NULL,
    Location NVARCHAR(200) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Houses_Users FOREIGN KEY (HostId) REFERENCES Users(UserId),
    CONSTRAINT CHK_Price CHECK (PricePerNight > 0)
);
GO

-- Rezervasyonlar Tablosu
CREATE TABLE Reservations (
    ReservationId INT IDENTITY(1,1) PRIMARY KEY,
    HouseId INT NOT NULL,
    TenantId INT NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL,
    TotalPrice DECIMAL(10,2) NOT NULL,
    Status NVARCHAR(50) DEFAULT 'Pending', -- Pending, Approved, Rejected, Cancelled
    CreatedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Reservations_Houses FOREIGN KEY (HouseId) REFERENCES Houses(HouseId),
    CONSTRAINT FK_Reservations_Users FOREIGN KEY (TenantId) REFERENCES Users(UserId),
    CONSTRAINT CHK_Dates CHECK (EndDate > StartDate)
);
GO

-- Yorumlar Tablosu
CREATE TABLE Reviews (
    ReviewId INT IDENTITY(1,1) PRIMARY KEY,
    ReservationId INT NOT NULL,
    Rating INT NOT NULL,
    Comment NVARCHAR(MAX),
    CreatedAt DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Reviews_Reservations FOREIGN KEY (ReservationId) REFERENCES Reservations(ReservationId),
    CONSTRAINT CHK_Rating CHECK (Rating >= 1 AND Rating <= 5)
);
GO

-- Log Tablosu (Trigger için)
CREATE TABLE ReservationLogs (
    LogId INT IDENTITY(1,1) PRIMARY KEY,
    ReservationId INT,
    OldStatus NVARCHAR(50),
    NewStatus NVARCHAR(50),
    LogDate DATETIME DEFAULT GETDATE()
);
GO


-- =========================================
-- 3. FUNCTIONS (FONKSİYONLAR)
-- =========================================

-- Fonksiyon 1: Belirli tarihler arasında evin uygunluğunu kontrol eder
IF OBJECT_ID('fn_CheckHouseAvailability', 'FN') IS NOT NULL DROP FUNCTION fn_CheckHouseAvailability;
GO
CREATE FUNCTION fn_CheckHouseAvailability (
    @HouseId INT,
    @StartDate DATE,
    @EndDate DATE
)
RETURNS BIT
AS
BEGIN
    DECLARE @IsAvailable BIT = 1;
    
    IF EXISTS (
        SELECT 1 FROM Reservations 
        WHERE HouseId = @HouseId 
        AND Status IN ('Pending', 'Approved')
        AND (
            (@StartDate >= StartDate AND @StartDate < EndDate) OR
            (@EndDate > StartDate AND @EndDate <= EndDate) OR
            (@StartDate <= StartDate AND @EndDate >= EndDate)
        )
    )
    BEGIN
        SET @IsAvailable = 0; -- Dolu
    END
    
    RETURN @IsAvailable;
END;
GO

-- Fonksiyon 2: Ev sahibinin onaylanmış rezervasyonlardan elde ettiği toplam geliri hesaplar
IF OBJECT_ID('fn_CalculateTotalIncome', 'FN') IS NOT NULL DROP FUNCTION fn_CalculateTotalIncome;
GO
CREATE FUNCTION fn_CalculateTotalIncome (
    @HostId INT
)
RETURNS DECIMAL(10,2)
AS
BEGIN
    DECLARE @TotalIncome DECIMAL(10,2) = 0;
    
    SELECT @TotalIncome = ISNULL(SUM(R.TotalPrice), 0)
    FROM Reservations R
    INNER JOIN Houses H ON R.HouseId = H.HouseId
    WHERE H.HostId = @HostId AND R.Status = 'Approved';
    
    RETURN @TotalIncome;
END;
GO


-- =========================================
-- 4. STORED PROCEDURES (SAKLI YORDAMLAR)
-- =========================================

-- Procedure 1: Yeni Rezervasyon Ekleme (Uygunluk kontrolü yaparak)
IF OBJECT_ID('sp_AddReservation', 'P') IS NOT NULL DROP PROCEDURE sp_AddReservation;
GO
CREATE PROCEDURE sp_AddReservation
    @HouseId INT,
    @TenantId INT,
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Ev uygun mu kontrol et
    IF dbo.fn_CheckHouseAvailability(@HouseId, @StartDate, @EndDate) = 1
    BEGIN
        DECLARE @Days INT = DATEDIFF(DAY, @StartDate, @EndDate);
        DECLARE @PricePerNight DECIMAL(10,2);
        
        -- Evin gecelik fiyatını al
        SELECT @PricePerNight = PricePerNight FROM Houses WHERE HouseId = @HouseId;
        
        DECLARE @TotalPrice DECIMAL(10,2) = @Days * @PricePerNight;
        
        INSERT INTO Reservations (HouseId, TenantId, StartDate, EndDate, TotalPrice, Status)
        VALUES (@HouseId, @TenantId, @StartDate, @EndDate, @TotalPrice, 'Pending');
        
        PRINT 'Rezervasyon başarıyla oluşturuldu.';
    END
    ELSE
    BEGIN
        RAISERROR('Seçilen tarihlerde ev dolu!', 16, 1);
    END
END;
GO

-- Procedure 2: Kullanıcı Durumunu Güncelleme (Admin için)
IF OBJECT_ID('sp_UpdateUserStatus', 'P') IS NOT NULL DROP PROCEDURE sp_UpdateUserStatus;
GO
CREATE PROCEDURE sp_UpdateUserStatus
    @UserId INT,
    @IsActive BIT
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE Users
    SET IsActive = @IsActive
    WHERE UserId = @UserId;
    
    PRINT 'Kullanıcı durumu güncellendi.';
END;
GO


-- =========================================
-- 5. TRIGGERS (TETİKLEYİCİLER)
-- =========================================

-- Trigger 1: Rezervasyon durumu değiştiğinde log tutar
IF OBJECT_ID('trg_AfterReservationUpdate', 'TR') IS NOT NULL DROP TRIGGER trg_AfterReservationUpdate;
GO
CREATE TRIGGER trg_AfterReservationUpdate
ON Reservations
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    IF UPDATE(Status)
    BEGIN
        INSERT INTO ReservationLogs (ReservationId, OldStatus, NewStatus)
        SELECT 
            i.ReservationId,
            d.Status,
            i.Status
        FROM inserted i
        INNER JOIN deleted d ON i.ReservationId = d.ReservationId
        WHERE i.Status <> d.Status;
    END
END;
GO

-- Trigger 2: Admin kullanıcısının silinmesini engeller
IF OBJECT_ID('trg_PreventAdminDelete', 'TR') IS NOT NULL DROP TRIGGER trg_PreventAdminDelete;
GO
CREATE TRIGGER trg_PreventAdminDelete
ON Users
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS (
        SELECT 1 FROM deleted d
        INNER JOIN Roles r ON d.RoleId = r.RoleId
        WHERE r.RoleName = 'Admin'
    )
    BEGIN
        RAISERROR('Admin yetkisine sahip kullanıcılar silinemez. Sadece pasife çekilebilir!', 16, 1);
        ROLLBACK TRANSACTION;
    END
    ELSE
    BEGIN
        DELETE FROM Users WHERE UserId IN (SELECT UserId FROM deleted);
    END
END;
GO
