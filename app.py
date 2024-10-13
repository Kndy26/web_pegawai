from flask import Flask, render_template, \
    request, redirect, url_for, session

from werkzeug.utils import secure_filename
import pymysql.cursors, os
import datetime
from flask import jsonify

application = Flask(__name__)

conn = cursor = None

#fungsi koneksi ke basis data
def openDb():
    global conn, cursor
    conn = pymysql.connect(db="db_pegawai", user="root", passwd="",host="localhost",port=3306,autocommit=True)
    cursor = conn.cursor()	

#fungsi menutup koneksi
def closeDb():
    global conn, cursor
    cursor.close()
    conn.close()

application.secret_key = 'your_secret_key'  # Ganti dengan secret key yang aman

# Contoh data pengguna (dalam aplikasi nyata, gunakan database)
users = {'user': 'password'}

#halaman login
@application.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        openDb()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        closeDb()

        if user and check_password(password, user[2]):  # Assuming password is stored in column index 2
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            error = 'Invalid username or password.'
            return render_template('login.html', error=error)
    else:
        return render_template('login.html')

#fungsi view home()
@application.route('/home')
def home():
    if 'logged_in' in session and session['logged_in']:
        username = session.get('username')
        return render_template('home.html', username=username)
    else:
        return redirect(url_for('login'))

# --- SIGN UP ---
@application.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        openDb()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hash_password(password)))
        conn.commit()
        closeDb()

        return redirect(url_for('login'))  # Redirect to login after signup
    else:
        return render_template('signup.html')

# --- LOGOUT ---
@application.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))


# --- FORGOT PASSWORD ---
@application.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            error = 'New password and confirm password do not match.'
            return render_template('forgot_password.html', error=error)

        openDb()
        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hash_password(new_password), username))
        conn.commit()
        closeDb()

        return redirect(url_for('login'))  # Redirect to login after password reset
    else:
        return render_template('forgot_password.html')

# --- PASSWORD HASHING (Add this) ---
import hashlib

def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed_password):
    """Verifies a password against its hash."""
    return hash_password(password) == hashed_password

#fungsi view index() untuk menampilkan data dari basis data
@application.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:   
        openDb()
        container = []
        sql = "SELECT * FROM pegawai ORDER BY NIK DESC;"
        cursor.execute(sql)
        results = cursor.fetchall()
        for data in results:
            container.append(data)
        closeDb()
        username = session.get('username') # Ambil username dari session
        return render_template('index.html', container=container, username=username)
    else:
        return redirect(url_for('login'))

#fungsi membuat NIK otomatis
def generate_nik():
    # mendefinisikan fungsi openDb(), cursor, dan closeDb() 
    openDb()

    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    
    # Mengambil empat digit terakhir dari tahun
    year_str = str(current_year).zfill(2)
    
    # Mengambil dua digit dari bulan
    current_month_str = str(current_month).zfill(2)

    # Membuat format NIK tanpa nomor urut terlebih dahulu
    base_nik_without_number = f"P-{year_str}{current_month_str}"

    # Mencari NIK terakhir dari database untuk mendapatkan nomor urut
    cursor.execute("SELECT nik FROM pegawai WHERE nik LIKE %s ORDER BY nik DESC LIMIT 1", (f"{base_nik_without_number}%",))
    last_nik = cursor.fetchone()

    if last_nik:
        last_number = int(last_nik[0].split("-")[-1])  # Mengambil nomor urut terakhir
        next_number = last_number + 1
        # Membuat NIK lengkap dengan nomor urut
        next_nik = f"P-{str(next_number).zfill(3)}"
    else:
        next_number = 1  # Jika belum ada data, mulai dari 1
        # Membuat NIK lengkap dengan nomor urut
        next_nik = f"{base_nik_without_number}{str(next_number).zfill(3)}"
    
    closeDb()  # untuk menutup koneksi database 
    
    return next_nik

#fungsi untuk menyimpan lokasi foto
UPLOAD_FOLDER = '/web_pegawai/crud/static/foto/'
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app = Flask(__name__, static_folder='static')

#fungsi view tambah() untuk membuat form tambah data
@application.route('/tambah', methods=['GET','POST'])
def tambah():
    generated_nik = generate_nik()  # Memanggil fungsi untuk mendapatkan NIK otomatis
    
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        alamat = request.form['alamat']
        tgllahir = request.form['tgllahir']
        jeniskelamin = request.form['jeniskelamin']
        status = request.form['status']
        gaji = request.form['gaji']
        foto = request.form['nik']

        # Pastikan direktori upload ada
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # Simpan foto dengan nama NIK
        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename != '':
                foto.save(os.path.join(application.config['UPLOAD_FOLDER'], f"{nik}.jpg"))

        openDb()
        sql = "INSERT INTO pegawai (nik,nama,alamat,tgllahir,jeniskelamin,status,gaji,foto) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        val = (nik,nama,alamat,tgllahir,jeniskelamin,status,gaji,foto)
        cursor.execute(sql, val)
        conn.commit()
        closeDb()
        return redirect(url_for('index'))        
    else:
        return render_template('tambah.html', nik=generated_nik)  # Mengirimkan NIK otomatis ke template
    
#fungsi view edit() untuk form edit data
@application.route('/edit/<nik>', methods=['GET','POST'])
def edit(nik):
    openDb()
    cursor.execute('SELECT * FROM pegawai WHERE nik=%s', (nik,))
    data = cursor.fetchone()
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        alamat = request.form['alamat']
        tgllahir = request.form['tgllahir']
        jeniskelamin = request.form['jeniskelamin']
        status = request.form['status']
        gaji = request.form['gaji']

        # Cek apakah foto baru diunggah
        foto_baru = request.files.get('foto')
        if foto_baru and foto_baru.filename != '':
            foto_filename = secure_filename(foto_baru.filename)
            foto_path = os.path.join(application.config['UPLOAD_FOLDER'], f"{nik}.jpg")
            foto_baru.save(foto_path)

        # Update data di database
        sql = "UPDATE pegawai SET nama=%s, alamat=%s, tgllahir=%s, jeniskelamin=%s, status=%s, gaji=%s WHERE nik=%s"
        val = (nama, alamat, tgllahir, jeniskelamin, status, gaji, nik)
        cursor.execute(sql, val)
        conn.commit()
        closeDb()
        return redirect(url_for('index'))
    else:
        closeDb()
        return render_template('edit.html', data=data)

#fungsi menghapus data
@application.route('/hapus/<nik>', methods=['GET','POST'])
def hapus(nik):
    openDb()
    cursor.execute('DELETE FROM pegawai WHERE nik=%s', (nik,))
    # Hapus foto berdasarkan NIK
    path_to_photo = os.path.join(application.root_path, '/web_pegawai/crud/static/foto', f'{nik}.jpg')
    if os.path.exists(path_to_photo):
        os.remove(path_to_photo)

    conn.commit()
    closeDb()
    return redirect(url_for('index'))

# Fungsi untuk menghapus akun dari database
@application.route('/delete_account', methods=['POST'])
def delete_account():
    if 'logged_in' in session and session['logged_in']:
        username = session.get('username')
        
        openDb()
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        closeDb()
        
        session.pop('logged_in', None)
        session.pop('username', None)
        return redirect(url_for('login'))  # Redirect to login after account deletion
    else:
        return redirect(url_for('login'))
    
#fungsi cetak ke PDF
@application.route('/get_employee_data/<nik>', methods=['GET'])
def get_employee_data(nik):
    # Koneksi ke database
    connection = pymysql.connect(host='localhost',
                                 user='root',
                                 password='',  # Password Anda (jika ada)
                                 db='db_pegawai',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            # Query untuk mengambil data pegawai berdasarkan NIK
            sql = "SELECT * FROM pegawai WHERE nik = %s"
            cursor.execute(sql, (nik,))
            employee_data = cursor.fetchone()  # Mengambil satu baris data pegawai

            # Log untuk melihat apakah permintaan diterima dengan benar
            print("Menerima permintaan untuk NIK:", nik)

            # Log untuk melihat data yang dikirim ke klien
            print("Data yang dikirim:", employee_data)

            return jsonify(employee_data)  # Mengembalikan data sebagai JSON

    except Exception as e:
        print("Error:", e)
        return jsonify({'error': 'Terjadi kesalahan saat mengambil data'}), 500

    finally:
        connection.close()  # Menutup koneksi database setelah selesai

#fungsi view untuk mengurutkan data
@application.route('/sort/<column>/<order>')
def sort(column, order):
    if 'logged_in' in session and session['logged_in']:
        openDb()
        container = []

        session['sort_column'] = column
        session['sort_order'] = order

        sql = f"SELECT * FROM pegawai ORDER BY {column} {'ASC' if order == 'asc' else 'DESC'}"
        cursor.execute(sql)
        results = cursor.fetchall()
        for data in results:
            container.append(data)
        closeDb()
        username = session.get('username')
        return render_template('index.html', container=container, username=username, sort_column=column, sort_order=order)
    else:
        return redirect(url_for('login'))
    
#Program utama      
if __name__ == '__main__':
    application.run(debug=True)