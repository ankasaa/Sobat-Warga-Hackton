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
        raw = request.get_data(as_text=True).strip()
        if not raw:
            return DEFAULT

        # Coba ambil teks mentahnya (baik dari JSON maupun teks murni)
        teks_analisis = raw
        if request.is_json:
            content = request.get_json(silent=True)
            if isinstance(content, dict):
                # Ambil teks dari key apa pun yang dikirim Langflow
                for k in ["ringkasan", "text", "message", "input", "data"]:
                    if content.get(k):
                        teks_analisis = str(content[k])
                        break

        # Mulai salin default
        hasil = DEFAULT.copy()
        hasil["ringkasan"] = teks_analisis

        # --- FITUR CERDAS: Ekstraksi Kategori & Urgensi Otomatis dari Teks AI ---
        teks_lower = teks_analisis.lower()

        # 1. Deteksi Urgensi
        if "darurat" in teks_lower or "fatal" in teks_lower or "korban jiwa" in teks_lower:
            hasil["urgensi"] = "Darurat"
        else:
            hasil["urgensi"] = "Reguler"

        # 2. Deteksi Kategori
        if "infrastruktur" in teks_lower or "jalan" in teks_lower or "jembatan" in teks_lower or "pencahayaan" in teks_lower:
            hasil["kategori"] = "Infrastruktur & Fasilitas Umum"
        elif "kebencanaan" in teks_lower or "kecelakaan" in teks_lower or "pohon tumbang" in teks_lower or "rumah roboh" in teks_lower:
            hasil["kategori"] = "Ketertiban, Keamanan, & Kebencanaan"
        elif "kebersihan" in teks_lower or "sampah" in teks_lower:
            hasil["kategori"] = "Kebersihan & Lingkungan Hidup"
        else:
            hasil["kategori"] = "Layanan Umum"

        # 3. Deteksi Instansi Terkait (Opsional sederhana)
        if "pupr" in teks_lower:
            hasil["instansi"] = "Dinas PUPR Badung"
        elif "bpbd" in teks_lower or "polisi" in teks_lower or "bhabinkamtibmas" in teks_lower:
            hasil["instansi"] = "BPBD & Kepolisian / Bhabinkamtibmas"
        elif "dlhk" in teks_lower:
            hasil["instansi"] = "DLHK Badung"

        return hasil

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


# API Endpoint 3: Menghapus laporan berdasarkan ID (DELETE)
@app.route('/api/hapus-laporan/<int:id>', methods=['DELETE'])
def hapus_laporan(id):
    try:
        with get_db() as conn:
            hasil = conn.execute('DELETE FROM laporan WHERE id = ?', (id,))
            if hasil.rowcount == 0:
                return jsonify({"status": "error", "pesan": f"Laporan dengan ID {id} tidak ditemukan."}), 404

        return jsonify({"status": "sukses", "pesan": f"Laporan ID {id} berhasil dihapus."}), 200

    except Exception as e:
        return jsonify({"status": "error", "pesan": f"Gagal menghapus laporan: {str(e)}"}), 500


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
