from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# ==========================================
# VERİTABANI BAĞLANTI AYARLARI
# ==========================================
# Kendi bilgisayarındaki SQL Server adını buraya yazmalısın.
# Örneğin: 'localhost\SQLEXPRESS' veya sadece 'localhost'
SERVER_NAME = r'ARTARSLAN\MSSQLSERVER01'   
DATABASE_NAME = 'TinyHaosueDB'

def get_db_connection():
    try:
        # Windows Authentication (Trusted_Connection=yes)
        connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};Trusted_Connection=yes;'
        conn = pyodbc.connect(connection_string)
        return conn
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

# ==========================================
# ROTALAR (ROUTES)
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Güvenlik için parametrik sorgu (SQL Injection'ı önler)
        cursor.execute("SELECT UserId, RoleId, FirstName, LastName FROM Users WHERE Email = ? AND PasswordHash = ? AND IsActive = 1", (email, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['role_id'] = user[1]
            session['name'] = f"{user[2]} {user[3]}"
            
            # Rollere göre yönlendirme
            if user[1] == 1: # Admin
                return redirect('/admin')
            elif user[1] == 2: # Ev Sahibi
                return redirect('/host')
            elif user[1] == 3: # Kiracı
                return redirect('/tenant')
        else:
            flash("Hatalı e-posta veya şifre!")
            return redirect('/')
    else:
        flash("Veritabanına bağlanılamadı.")
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- DASHBOARD ROTALARI ---

@app.route('/admin')
def admin_dashboard():
    if session.get('role_id') != 1: return redirect('/')
    stats = {'users': 0, 'houses': 0, 'reservations': 0, 'income': 0}
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users")
        stats['users'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Houses WHERE IsActive=1")
        stats['houses'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Reservations WHERE Status='Pending'")
        stats['reservations'] = cursor.fetchone()[0]
        cursor.execute("SELECT ISNULL(SUM(TotalPrice), 0) FROM Reservations WHERE Status='Approved'")
        stats['income'] = cursor.fetchone()[0]
        conn.close()
    return render_template('dashboard_admin.html', name=session.get('name'), stats=stats)

# --- ADMIN ROUTES ---
@app.route('/admin/users')
def admin_users():
    if session.get('role_id') != 1: return redirect('/')
    users = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT U.UserId, U.FirstName, U.LastName, U.Email, R.RoleName, U.IsActive 
            FROM Users U JOIN Roles R ON U.RoleId = R.RoleId
            ORDER BY U.UserId
        """)
        users = cursor.fetchall()
        conn.close()
    return render_template('admin_users.html', name=session.get('name'), users=users)

@app.route('/admin/houses')
def admin_houses():
    if session.get('role_id') != 1: return redirect('/')
    houses = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT H.HouseId, H.Title, H.Location, H.PricePerNight, H.IsActive, 
                   U.FirstName + ' ' + U.LastName AS HostName
            FROM Houses H JOIN Users U ON H.HostId = U.UserId
            ORDER BY H.HouseId
        """)
        houses = cursor.fetchall()
        conn.close()
    return render_template('admin_houses.html', name=session.get('name'), houses=houses)

@app.route('/admin/reservations')
def admin_reservations():
    if session.get('role_id') != 1: return redirect('/')
    reservations = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT R.ReservationId, H.Title, U.FirstName + ' ' + U.LastName AS TenantName,
                   R.StartDate, R.EndDate, R.Status
            FROM Reservations R
            JOIN Houses H ON R.HouseId = H.HouseId
            JOIN Users U ON R.TenantId = U.UserId
            ORDER BY R.CreatedAt DESC
        """)
        reservations = cursor.fetchall()
        conn.close()
    return render_template('admin_reservations.html', name=session.get('name'), reservations=reservations)

@app.route('/admin/payments')
def admin_payments():
    if session.get('role_id') != 1: return redirect('/')
    payments = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT R.ReservationId, H.Title, U.FirstName + ' ' + U.LastName AS TenantName,
                   R.TotalPrice, R.Status, R.StartDate, R.EndDate
            FROM Reservations R
            JOIN Houses H ON R.HouseId = H.HouseId
            JOIN Users U ON R.TenantId = U.UserId
            ORDER BY R.CreatedAt DESC
        """)
        payments = cursor.fetchall()
        conn.close()
    return render_template('admin_payments.html', name=session.get('name'), payments=payments)

@app.route('/admin/update_user_status', methods=['POST'])
def admin_update_user_status():
    if session.get('role_id') != 1: return redirect('/')
    user_id = request.form.get('user_id')
    is_active = request.form.get('is_active')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("EXEC sp_UpdateUserStatus @UserId=?, @IsActive=?", (user_id, is_active))
            conn.commit()
            flash("Kullanıcı durumu güncellendi.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    return redirect('/admin/users')

@app.route('/admin/delete_user', methods=['POST'])
def admin_delete_user():
    if session.get('role_id') != 1: return redirect('/')
    user_id = request.form.get('user_id')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Users WHERE UserId=?", (user_id,))
            conn.commit()
            flash("Kullanıcı silindi.", "success")
        except pyodbc.Error as e:
            conn.rollback()
            flash("Silme işlemi başarısız. Bu kullanıcının veritabanında ilişkili kayıtları bulunmaktadır. Önce pasife çekmeyi deneyin.", "error")
        finally:
            conn.close()
    return redirect('/admin/users')

@app.route('/admin/cancel_reservation', methods=['POST'])
def admin_cancel_reservation():
    if session.get('role_id') != 1: return redirect('/')
    res_id = request.form.get('reservation_id')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Reservations SET Status='Cancelled' WHERE ReservationId=?", (res_id,))
            conn.commit()
            flash("Rezervasyon iptal edildi.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    return redirect('/admin/reservations')

@app.route('/admin/toggle_house_status', methods=['POST'])
def admin_toggle_house_status():
    if session.get('role_id') != 1: return redirect('/')
    house_id = request.form.get('house_id')
    is_active = request.form.get('is_active')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Houses SET IsActive=? WHERE HouseId=?", (is_active, house_id))
            conn.commit()
            flash("İlan durumu güncellendi.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    return redirect('/admin/houses')



@app.route('/host')
def host_dashboard():
    if session.get('role_id') != 2: return redirect('/')
    host_id = session.get('user_id')
    stats = {'total_houses': 0, 'active_houses': 0, 'pending_requests': 0, 'income': 0}
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Houses WHERE HostId=?", (host_id,))
        stats['total_houses'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM Houses WHERE HostId=? AND IsActive=1", (host_id,))
        stats['active_houses'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM Reservations R 
            JOIN Houses H ON R.HouseId = H.HouseId 
            WHERE H.HostId=? AND R.Status='Pending'
        """, (host_id,))
        stats['pending_requests'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT dbo.fn_CalculateTotalIncome(?)
        """, (host_id,))
        stats['income'] = cursor.fetchone()[0]
        conn.close()
    return render_template('dashboard_host.html', name=session.get('name'), stats=stats)

# --- HOST ROUTES ---
@app.route('/host/houses')
def host_houses():
    if session.get('role_id') != 2: return redirect('/')
    host_id = session.get('user_id')
    houses = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT HouseId, Title, Location, PricePerNight, IsActive FROM Houses WHERE HostId = ?", (host_id,))
        houses = cursor.fetchall()
        conn.close()
    return render_template('host_houses.html', name=session.get('name'), houses=houses)

@app.route('/host/add_house', methods=['GET', 'POST'])
def host_add_house():
    if session.get('role_id') != 2: return redirect('/')
    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        price = request.form.get('price')
        description = request.form.get('description')
        host_id = session.get('user_id')
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO Houses (HostId, Title, Description, PricePerNight, Location) VALUES (?, ?, ?, ?, ?)",
                               (host_id, title, description, price, location))
                conn.commit()
                flash("İlan başarıyla eklendi.", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Hata: {str(e)}", "danger")
            finally:
                conn.close()
        return redirect('/host/houses')
        
    return render_template('host_add_house.html', name=session.get('name'))

@app.route('/host/edit_house/<int:house_id>', methods=['GET', 'POST'])
def host_edit_house(house_id):
    if session.get('role_id') != 2: return redirect('/')
    host_id = session.get('user_id')
    conn = get_db_connection()
    
    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        price = request.form.get('price')
        description = request.form.get('description')
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE Houses SET Title=?, Location=?, PricePerNight=?, Description=? 
                    WHERE HouseId=? AND HostId=?
                """, (title, location, price, description, house_id, host_id))
                conn.commit()
                flash("İlan başarıyla güncellendi.", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Hata: {str(e)}", "danger")
            finally:
                conn.close()
            return redirect('/host/houses')
            
    house = None
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT HouseId, Title, Description, PricePerNight, Location FROM Houses WHERE HouseId=? AND HostId=?", (house_id, host_id))
        house = cursor.fetchone()
        conn.close()
        
    if not house:
        flash("İlan bulunamadı.", "danger")
        return redirect('/host/houses')
        
    return render_template('host_edit_house.html', name=session.get('name'), house=house)

@app.route('/host/toggle_house_status', methods=['POST'])
def host_toggle_house_status():
    if session.get('role_id') != 2: return redirect('/')
    house_id = request.form.get('house_id')
    is_active = request.form.get('is_active')
    host_id = session.get('user_id')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Houses SET IsActive=? WHERE HouseId=? AND HostId=?", (is_active, house_id, host_id))
            conn.commit()
            flash("İlan durumu güncellendi.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    return redirect('/host/houses')

@app.route('/host/delete_house', methods=['POST'])
def host_delete_house():
    if session.get('role_id') != 2: return redirect('/')
    house_id = request.form.get('house_id')
    host_id = session.get('user_id')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM Houses WHERE HouseId=? AND HostId=?", (house_id, host_id))
            conn.commit()
            flash("İlan silindi.", "success")
        except pyodbc.Error as e:
            conn.rollback()
            flash("Bu ilana ait rezervasyon kayıtları bulunduğu için tamamen silinemez. Lütfen pasife çekmeyi tercih edin.", "danger")
        finally:
            conn.close()
    return redirect('/host/houses')

@app.route('/host/reservations')
def host_reservations():
    if session.get('role_id') != 2: return redirect('/')
    host_id = session.get('user_id')
    requests = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT R.ReservationId, H.Title, U.FirstName + ' ' + U.LastName AS TenantName, 
                   R.StartDate, R.EndDate, R.TotalPrice, R.Status
            FROM Reservations R
            JOIN Houses H ON R.HouseId = H.HouseId
            JOIN Users U ON R.TenantId = U.UserId
            WHERE H.HostId = ?
            ORDER BY R.CreatedAt DESC
        """, (host_id,))
        requests = cursor.fetchall()
        conn.close()
    return render_template('host_reservations.html', name=session.get('name'), requests=requests)

@app.route('/host/update_reservation', methods=['POST'])
def host_update_reservation():
    if session.get('role_id') != 2: return redirect('/')
    reservation_id = request.form.get('reservation_id')
    action = request.form.get('action') # 'Approved' or 'Rejected'
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Reservations SET Status = ? WHERE ReservationId = ?", (action, reservation_id))
            conn.commit()
            flash("Rezervasyon durumu güncellendi.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    return redirect('/host/reservations')

@app.route('/host/reviews')
def host_reviews():
    if session.get('role_id') != 2: return redirect('/')
    host_id = session.get('user_id')
    reviews = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT RV.ReviewId, H.Title, U.FirstName + ' ' + U.LastName AS TenantName, 
                   RV.Rating, RV.Comment, RV.CreatedAt
            FROM Reviews RV
            JOIN Houses H ON RV.HouseId = H.HouseId
            JOIN Users U ON RV.TenantId = U.UserId
            WHERE H.HostId = ?
            ORDER BY RV.CreatedAt DESC
        """, (host_id,))
        reviews = cursor.fetchall()
        conn.close()
    return render_template('host_reviews.html', name=session.get('name'), reviews=reviews)

@app.route('/tenant')
def tenant_dashboard():
    if session.get('role_id') != 3: return redirect('/')
    
    houses = []
    booked_dates = {}
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT HouseId, Title, PricePerNight, Location FROM Houses WHERE IsActive = 1")
        houses = cursor.fetchall()
        
        cursor.execute("SELECT HouseId, StartDate, EndDate FROM Reservations WHERE Status IN ('Pending', 'Approved')")
        reservations = cursor.fetchall()
        for res in reservations:
            h_id = res[0]
            if h_id not in booked_dates:
                booked_dates[h_id] = []
            booked_dates[h_id].append({
                'from': res[1].strftime('%Y-%m-%d'),
                'to': res[2].strftime('%Y-%m-%d')
            })
        conn.close()
        
    return render_template('dashboard_tenant.html', name=session.get('name'), houses=houses, booked_dates=booked_dates)

# --- TENANT ROUTES ---
@app.route('/tenant/search')
def tenant_search():
    if session.get('role_id') != 3: return redirect('/')
    return render_template('tenant_search.html', name=session.get('name'))

@app.route('/tenant/reservations')
def tenant_reservations():
    if session.get('role_id') != 3: return redirect('/')
    tenant_id = session.get('user_id')
    reservations = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT R.ReservationId, H.Title, R.StartDate, R.EndDate, R.TotalPrice, R.Status 
            FROM Reservations R
            JOIN Houses H ON R.HouseId = H.HouseId
            WHERE R.TenantId = ?
            ORDER BY R.CreatedAt DESC
        """, (tenant_id,))
        reservations = cursor.fetchall()
        conn.close()
    return render_template('tenant_reservations.html', name=session.get('name'), reservations=reservations)

@app.route('/tenant/reserve', methods=['POST'])
def tenant_reserve():
    if session.get('role_id') != 3: return redirect('/')
    house_id = request.form.get('house_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    tenant_id = session.get('user_id')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Stored procedure kullanarak rezervasyon ekleme
            cursor.execute("EXEC sp_AddReservation @HouseId=?, @TenantId=?, @StartDate=?, @EndDate=?", (house_id, tenant_id, start_date, end_date))
            conn.commit()
            flash("Rezervasyon başarıyla oluşturuldu.", "success")
        except pyodbc.Error as ex:
            conn.rollback()
            # Stored procedure'den gelen RAISERROR mesajını yakala
            sqlstate = ex.args[0]
            if sqlstate == '42000':
                msg = ex.args[1].split(']')[3] if ']' in ex.args[1] else ex.args[1]
                flash(f"Hata: Seçilen tarihler dolu veya geçersiz.", "error")
            else:
                flash("Rezervasyon yapılamadı.", "error")
        finally:
            conn.close()
            
    return redirect('/tenant')

@app.route('/tenant/cancel_reservation', methods=['POST'])
def tenant_cancel_reservation():
    if session.get('role_id') != 3: return redirect('/')
    res_id = request.form.get('reservation_id')
    tenant_id = session.get('user_id')
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Reservations SET Status='Cancelled' WHERE ReservationId=? AND TenantId=?", (res_id, tenant_id))
            conn.commit()
            flash("Rezervasyonunuz iptal edildi.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    return redirect('/tenant/reservations')

@app.route('/tenant/reviews')
def tenant_reviews():
    if session.get('role_id') != 3: return redirect('/')
    tenant_id = session.get('user_id')
    past_reservations = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT R.ReservationId, H.HouseId, H.Title, R.EndDate, 
                   (SELECT COUNT(*) FROM Reviews WHERE ReservationId = R.ReservationId) AS HasReview
            FROM Reservations R
            JOIN Houses H ON R.HouseId = H.HouseId
            WHERE R.TenantId = ? AND R.Status = 'Approved'
            ORDER BY R.EndDate DESC
        """, (tenant_id,))
        past_reservations = cursor.fetchall()
        conn.close()
    return render_template('tenant_reviews.html', name=session.get('name'), past_reservations=past_reservations)

@app.route('/tenant/add_review', methods=['POST'])
def tenant_add_review():
    if session.get('role_id') != 3: return redirect('/')
    tenant_id = session.get('user_id')
    house_id = request.form.get('house_id')
    reservation_id = request.form.get('reservation_id')
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Reviews (HouseId, TenantId, ReservationId, Rating, Comment)
                VALUES (?, ?, ?, ?, ?)
            """, (house_id, tenant_id, reservation_id, rating, comment))
            conn.commit()
            flash("Değerlendirmeleriniz için teşekkürler!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Hata: {str(e)}", "danger")
        finally:
            conn.close()
    return redirect('/tenant/reviews')

if __name__ == '__main__':
    app.run(debug=True)
