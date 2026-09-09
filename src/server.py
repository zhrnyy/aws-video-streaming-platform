from flask import Flask, render_template_string, jsonify, Response, stream_with_context, request, redirect
import boto3, os

app = Flask(__name__)

INPUT_BUCKET = "lab-video-input-lightcoffee26"
OUTPUT_BUCKET = "lab-video-output-lightcoffee26"
REGION = "us-east-1"

s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table('VideoCatalog')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>KodeTube</title>
    <link href="https://vjs.zencdn.net/7.20.3/video-js.css" rel="stylesheet" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #1e293b 100%); color: #f1f5f9; min-height: 100vh; }
        .navbar { display: flex; justify-content: space-between; align-items: center; padding: 20px 60px; background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(20px); border-bottom: 1px solid rgba(99, 102, 241, 0.2); position: sticky; top: 0; z-index: 100; }
        .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #6366f1, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .btn { background: linear-gradient(135deg, #6366f1, #ec4899); border: none; color: white; padding: 12px 28px; border-radius: 12px; cursor: pointer; font-weight: 600; transition: all 0.3s; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4); }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 25px rgba(99, 102, 241, 0.6); }
        .container { max-width: 1400px; margin: 50px auto; padding: 0 40px; }
        .video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; }
        .card { background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(10px); border-radius: 20px; border: 1px solid rgba(99, 102, 241, 0.2); cursor: pointer; transition: all 0.4s; position: relative; overflow: hidden; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); }
        .card:hover { border-color: #6366f1; transform: translateY(-8px); box-shadow: 0 20px 60px rgba(99, 102, 241, 0.4); }
        .thumb { height: 200px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(236, 72, 153, 0.2)); display: flex; align-items: center; justify-content: center; font-size: 64px; }
        .info { padding: 20px; }
        .info strong { display: block; font-size: 16px; font-weight: 700; margin-bottom: 8px; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status-ready { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }
        .status-processing { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid #f59e0b; }
        .delete-btn { position: absolute; top: 12px; right: 12px; background: rgba(239, 68, 68, 0.9); color: white; border: none; border-radius: 50%; width: 36px; height: 36px; cursor: pointer; z-index: 10; opacity: 0; transition: all 0.3s; font-size: 20px; }
        .card:hover .delete-btn { opacity: 1; }
        .delete-btn:hover { transform: scale(1.1) rotate(90deg); }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(10px); z-index: 1000; justify-content: center; align-items: center; }
        .modal-content { background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(20px); padding: 40px; border-radius: 24px; width: 90%; max-width: 900px; border: 1px solid rgba(99, 102, 241, 0.3); text-align: center; }
        .modal-content h2 { font-size: 28px; font-weight: 700; margin-bottom: 30px; background: linear-gradient(135deg, #6366f1, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .video-js { width: 100% !important; height: auto !important; aspect-ratio: 16/9; border-radius: 16px; }
        #uploadingState { display: none; }
        .spinner { border: 5px solid rgba(99, 102, 241, 0.1); border-top: 5px solid #6366f1; border-radius: 50%; width: 60px; height: 60px; animation: spin 0.8s linear infinite; margin: 30px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        input[type="file"] { margin: 20px 0; padding: 15px; background: rgba(99, 102, 241, 0.1); border: 2px dashed rgba(99, 102, 241, 0.4); border-radius: 12px; color: #f1f5f9; width: 100%; cursor: pointer; transition: all 0.3s; }
        input[type="file"]:hover { border-color: #6366f1; background: rgba(99, 102, 241, 0.2); }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="logo">lightcoffee</div>
        <button class="btn" onclick="openUpload()">+ UPLOAD VIDEO</button>
    </div>
    <div class="container"><div class="video-grid" id="grid"></div></div>

    <div id="uploadModal" class="modal" onclick="document.getElementById('uploadModal').style.display='none';">
        <div class="modal-content" style="max-width: 400px;" onclick="event.stopPropagation()">
            <button onclick="document.getElementById('uploadModal').style.display='none';" style="position: absolute; top: 15px; right: 15px; background: rgba(239, 68, 68, 0.9); color: white; border: none; border-radius: 50%; width: 32px; height: 32px; cursor: pointer; font-size: 18px; transition: all 0.3s;">&times;</button>
            <div id="formState">
                <h2>New Deployment</h2>
                <form id="uploadForm">
                    <input type="file" id="fileInput" name="file" accept=".mp4" style="margin:20px 0; color:#ccc;" required><br>
                    <button type="submit" class="btn">START UPLOAD</button>
                </form>
            </div>
            <div id="uploadingState">
                <div class="spinner"></div>
                <p>Transferring to S3...</p>
            </div>
        </div>
    </div>

    <div id="playerModal" class="modal" onclick="closePlayer()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <video id="my-video" class="video-js vjs-big-play-centered" controls preload="auto"></video>
            <h3 id="videoTitle" style="margin-top:20px; color: var(--kk-cyan);"></h3>
        </div>
    </div>

    <script src="https://vjs.zencdn.net/7.20.3/video.min.js"></script>
    <script>
        function openUpload() { document.getElementById('uploadModal').style.display = 'flex'; }

        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const file = document.getElementById('fileInput').files[0];
            if(!file) return;

            document.getElementById('formState').style.display = 'none';
            document.getElementById('uploadingState').style.display = 'block';

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                if (response.ok) {
                    document.getElementById('uploadModal').style.display = 'none';
                    document.getElementById('uploadingState').style.display = 'none';
                    document.getElementById('formState').style.display = 'block';
                    document.getElementById('fileInput').value = '';
                    loadVideos();
                } else { alert("Upload failed on server."); }
            } catch (err) { alert("Error connecting to server."); }
        };

        function loadVideos() {
            fetch('/api/videos?t=' + Date.now()).then(r => r.json()).then(videos => {
                const grid = document.getElementById('grid');
                if (videos.length === 0) {
                    grid.innerHTML = `
                        <div style="grid-column: 1/-1; text-align: center; padding: 80px 20px;">
                            <div style="font-size: 120px; margin-bottom: 20px; opacity: 0.3;">🎬</div>
                            <h2 style="font-size: 32px; font-weight: 700; margin-bottom: 15px; background: linear-gradient(135deg, #6366f1, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">No Videos Yet</h2>
                            <p style="color: #94a3b8; font-size: 18px; margin-bottom: 30px;">Upload your first video to get started</p>
                            <button class="btn" onclick="openUpload()" style="font-size: 16px; padding: 14px 32px;">+ Upload Video</button>
                        </div>`;
                    return;
                }
                grid.innerHTML = '';
                videos.forEach(v => {
                    const isReady = v.status === 'Ready';
                    const statusClass = isReady ? 'status-ready' : 'status-processing';
                    const icon = isReady ? '▶' : '⚙';
                    grid.innerHTML += `
                        <div class="card" onclick="playVideo('${v.video_id}', '${v.status}')">
                            <button class="delete-btn" onclick="event.stopPropagation(); deleteVideo('${v.video_id}')">&times;</button>
                            <div class="thumb"><span class="thumb-icon">${icon}</span></div>
                            <div class="info">
                                <strong>${v.video_id}</strong>
                                <span class="status-badge ${statusClass}">${v.status} ${v.progress || 0}%</span>
                            </div>
                        </div>`;
                });
            });
        }

        function playVideo(id, status) {
            if (status !== 'Ready') return;
            const player = videojs('my-video');
            player.src({ type: 'application/x-mpegURL', src: '/stream/' + encodeURIComponent(id) + '/playlist.m3u8' });
            document.getElementById('videoTitle').innerText = id;
            document.getElementById('playerModal').style.display = 'flex';
            player.play();
        }

        function closePlayer() { document.getElementById('playerModal').style.display = 'none'; videojs('my-video').pause(); }

        async function deleteVideo(id) {
            if (!confirm("Delete this video?")) return;
            await fetch('/api/delete/' + encodeURIComponent(id), { method: 'POST' });
            loadVideos();
        }

        loadVideos();
        setInterval(loadVideos, 3000); 
    </script>
</body>
</html>
"""

@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/api/videos')
def list_videos():
    items = table.scan().get('Items', [])
    items.sort(key=lambda x: x['video_id'])
    return jsonify(items)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if file:
        s3.upload_fileobj(file, INPUT_BUCKET, file.filename)
        video_id = file.filename.split('.')[0].replace(' ', '_').replace('+', '_')
        table.put_item(Item={'video_id': video_id, 'status': 'Queued', 'progress': 0})
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 400

@app.route('/stream/<video_id>/<path:filename>')
def stream(video_id, filename):
    key = f"{video_id}/{filename}"
    content_type = 'application/x-mpegURL' if filename.endswith('.m3u8') else 'video/MP2T'
    try:
        s3_obj = s3.get_object(Bucket=OUTPUT_BUCKET, Key=key)
        return Response(stream_with_context(s3_obj['Body'].iter_chunks(chunk_size=4096)), mimetype=content_type)
    except: return Response("Not Found", status=404)

@app.route('/api/delete/<video_id>', methods=['POST'])
def delete_video(video_id):
    table.delete_item(Key={'video_id': video_id})
    objs = s3.list_objects_v2(Bucket=OUTPUT_BUCKET, Prefix=f"{video_id}/")
    if 'Contents' in objs:
        s3.delete_objects(Bucket=OUTPUT_BUCKET, Delete={'Objects': [{'Key': o['Key']} for o in objs['Contents']]})
    return jsonify({"status": "deleted"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
