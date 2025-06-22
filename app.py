import os
from flask import Flask, request, jsonify, send_file, send_from_directory, after_this_request
import yt_dlp
import requests
import subprocess
import uuid

app = Flask(__name__, static_folder='.')

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/baixar', methods=['POST'])
def baixar():
    session_id = str(uuid.uuid4())
    temp_filename_base = f"temp_{session_id}"
    
    audio_file = None
    cover_file = None
    mp4_file_path = None

    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({"message": "URL não fornecida"}), 400

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{temp_filename_base}.%(ext)s',
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            thumbnail_url = info.get('thumbnail')
            title = info.get('title', 'musica')
            ext = info.get('ext', 'webm')

        audio_file = f"{temp_filename_base}.{ext}"

        img_data = requests.get(thumbnail_url).content
        cover_file = f'{temp_filename_base}.jpg'
        with open(cover_file, 'wb') as f:
            f.write(img_data)

        download_name = f"{title}.mp4"
        mp4_file_path = f"{temp_filename_base}.mp4"

        ffmpeg_cmd = [
            'ffmpeg', '-y', '-loop', '1', '-i', cover_file, '-i', audio_file,
            '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac',
            '-b:a', '192k', '-pix_fmt', 'yuv420p', '-shortest', mp4_file_path
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        @after_this_request
        def cleanup(response):
            try:
                if mp4_file_path and os.path.exists(mp4_file_path):
                    os.remove(mp4_file_path)
                    print(f"Arquivo final removido: {mp4_file_path}")
            except Exception as e:
                print(f"Erro ao limpar arquivo final: {e}")
            return response

        return send_file(mp4_file_path, as_attachment=True, download_name=download_name, mimetype='video/mp4')

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode('utf-8') if e.stderr else str(e)
        return jsonify({"message": f"Erro no FFmpeg: {error_message}"}), 500
    except Exception as e:
        return jsonify({"message": f"Erro: {str(e)}"}), 500
    finally:
        print("Limpando arquivos de origem...")
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)
        if cover_file and os.path.exists(cover_file):
            os.remove(cover_file)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
