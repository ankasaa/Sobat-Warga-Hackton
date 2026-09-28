from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime

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
    DEFAULT = {
        "ringkasan": "-",
        "kategori": "Umum",
        "urgensi": "Reguler",
        "instansi": "Kantor Kelurahan",
        "draf_pesan": "-",
    }

    try:
        # 1. Cek apakah ada data JSON standar dari Key-Value Langflow
        if request.is_json:
            content = request.get_json(silent=True)
            if isinstance(content, dict):
                hasil = DEFAULT.copy()
                # Cari berbagai kemungkinan nama key dari Langflow
                for k in ["ringkasan", "text", "message", "input", "data"]:
                    if content.get(k):
                        hasil["ringkasan"] = str(content[k])
                        break
                # Ambil field lain jika ada
                for key in ["kategori", "urgensi", "instansi", "draf_pesan"]:
                    if content.get(key):
                        hasil[key] = str(content[key])
                return hasil

        # 2. Baca sebagai teks mentah / form data jika dikirim langsung
        raw = request.get_data(as_text=True).strip()
        if raw:
            # Jika ada key 'ringkasan=' atau bentuk form-urlencoded
            if "ringkasan=" in raw or "text=" in raw:
                from urllib.parse import parse_qs
                parsed_form = parse_qs(raw)
                for k in ["ringkasan", "text"]:
                    if k in parsed_form and parsed_form[k][0]:
                        return {**DEFAULT, "ringkasan": parsed_form[k][0]}

            # Jika benar-benar murni teks bebas
            return {**DEFAULT, "ringkasan": raw}

    except Exception as e:
        print(f"Error parse_payload: {e}")

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
