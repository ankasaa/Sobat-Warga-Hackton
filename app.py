from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import json

app = Flask(__name__)
CORS(app)  # Mengizinkan Dashboard HTML menarik data

DB_PATH = 'sobatwarga.db'


def get_db():
    """Membuka koneksi ke database SQLite."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Membuat database & tabel (otomatis berjalan pertama kali)."""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS laporan (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu       TEXT,
                ringkasan   TEXT,
                kategori    TEXT,
                urgensi     TEXT,
                instansi    TEXT,
                draf_pesan  TEXT
            )
        ''')


def parse_payload():
    """
    Mencoba membaca payload dari request dalam berbagai format:
    1. JSON via Content-Type: application/json
    2. JSON yang dikirim sebagai teks biasa (dicoba di-parse)
    3. Form data (application/x-www-form-urlencoded)
    4. Teks bebas — seluruhnya masuk ke kolom 'ringkasan'

    Selalu mengembalikan dict dengan kunci yang lengkap, tidak pernah None.
    """
    DEFAULT = {
        "ringkasan": "-",
        "kategori": "Umum",
        "urgensi": "Reguler",
        "instansi": "Kantor Kelurahan",
        "draf_pesan": "-",
    }

    # --- Coba baca sebagai JSON terlebih dahulu ---
    try:
        data = request.get_json(force=True, silent=True)
        if isinstance(data, dict) and data:
            # Tangani jika nilai-nilai di dalam dict adalah None
            hasil = DEFAULT.copy()
            for key in DEFAULT:
                if data.get(key) not in (None, ""):
                    hasil[key] = str(data[key])
            return hasil
    except Exception:
        pass

    # --- Coba baca body sebagai teks, lalu parse JSON secara manual ---
    raw = ""
    try:
        raw = request.get_data(as_text=True).strip()
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                hasil = DEFAULT.copy()
                for key in DEFAULT:
                    if parsed.get(key) not in (None, ""):
                        hasil[key] = str(parsed[key])
                return hasil
            # JSON valid tapi bukan dict (misal: list atau string)
            return {**DEFAULT, "ringkasan": raw}
    except json.JSONDecodeError:
        # Bukan JSON — perlakukan sebagai teks bebas
        if raw:
            return {**DEFAULT, "ringkasan": raw}
    except Exception:
        pass

    # --- Coba baca dari form data ---
    try:
        if request.form:
            hasil = DEFAULT.copy()
            for key in DEFAULT:
                val = request.form.get(key, "").strip()
                if val:
                    hasil[key] = val
            return hasil
    except Exception:
        pass

    # --- Fallback: kembalikan nilai default ---
    return DEFAULT


# API Endpoint 1: Menerima data dari Langflow (POST)
@app.route('/api/tambah-laporan', methods=['POST'])
def tambah_laporan():
    try:
        data = parse_payload()
        waktu_sekarang = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db() as conn:
            conn.execute(
                '''
                INSERT INTO laporan (waktu, ringkasan, kategori, urgensi, instansi, draf_pesan)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    waktu_sekarang,
                    data["ringkasan"],
                    data["kategori"],
                    data["urgensi"],
                    data["instansi"],
                    data["draf_pesan"],
                ),
            )

        return jsonify({"status": "sukses", "pesan": "Laporan berhasil masuk ke Database!"}), 201

    except Exception as e:
        # Server tidak akan pernah crash; error dikembalikan sebagai respons JSON
        return jsonify({"status": "error", "pesan": f"Gagal menyimpan laporan: {str(e)}"}), 500


# API Endpoint 2: Mengirim data ke Dashboard HTML (GET)
@app.route('/api/ambil-laporan', methods=['GET'])
def ambil_laporan():
    try:
        with get_db() as conn:
            baris_data = conn.execute(
                'SELECT * FROM laporan ORDER BY id DESC'
            ).fetchall()

        hasil = [
            {
                "id": b[0], "waktu": b[1], "ringkasan": b[2],
                "kategori": b[3], "urgensi": b[4], "instansi": b[5], "draf_pesan": b[6],
            }
            for b in baris_data
        ]
        return jsonify(hasil), 200

    except Exception as e:
        return jsonify({"status": "error", "pesan": f"Gagal mengambil laporan: {str(e)}"}), 500


if __name__ == '__main__':
    init_db()
    print("🚀 Server Backend Sobat Warga Menyala di http://localhost:5001")
    app.run(debug=True, port=5001)
