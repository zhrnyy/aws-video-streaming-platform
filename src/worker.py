import boto3, json, os, subprocess, re
from urllib.parse import unquote_plus

INPUT_BUCKET = "lab-video-input-lightcoffee26"
OUTPUT_BUCKET = "lab-video-output-lightcoffee26"
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/637423198678/VideoQueue"
REGION = "us-east-1"

sqs = boto3.client('sqs', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)
table = boto3.resource('dynamodb', region_name=REGION).Table('VideoCatalog')

def get_duration(file):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file]
    return float(subprocess.check_output(cmd))

def process():
    print("Worker started. Listening...")
    while True:
        resp = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20)
        if 'Messages' in resp:
            msg = resp['Messages'][0]
            body = json.loads(msg['Body'])
            local_in = None

            try:
                if 'Event' in body and body['Event'] == 's3:TestEvent':
                    print("Received S3 Test Event. Clearing...")
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
                    continue

                key = unquote_plus(body['Records'][0]['s3']['object']['key'])
                vid = key.split('.')[0].replace(' ', '_')
                local_in, out_dir = f"in_{vid}.mp4", f"out_{vid}"

                print(f"\n--- Processing: {key} ---")
                s3.download_file(INPUT_BUCKET, key, local_in)
                os.makedirs(out_dir, exist_ok=True)

                dur = get_duration(local_in)
                cmd = ['ffmpeg', '-i', local_in, '-profile:v', 'baseline', '-level', '3.0', '-f', 'hls', f'{out_dir}/playlist.m3u8']

                proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
                for line in proc.stderr:
                    if "time=" in line:
                        m = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                        if m:
                            h, mins, s = map(float, m.groups())
                            pct = min(int(((h*3600 + mins*60 + s) / dur) * 90), 90)
                            print(f"   > Progress: {pct}%", end="\r")
                            table.update_item(Key={'video_id':vid}, UpdateExpression="SET #s=:s, progress=:p", ExpressionAttributeNames={'#s':'status'}, ExpressionAttributeValues={':s':'Processing', ':p':pct})
                proc.wait()
                for f in os.listdir(out_dir): s3.upload_file(f"{out_dir}/{f}", OUTPUT_BUCKET, f"{vid}/{f}")
                table.put_item(Item={'video_id':vid, 'status':'Ready', 'progress':100})
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=msg['ReceiptHandle'])
                print(f"\n--- Finished: {vid} ---")

            except Exception as e: 
                print(f"Error: {e}")
            finally:
                if local_in and os.path.exists(local_in): 
                    os.remove(local_in)

process()
