# AWS Video Streaming Platform

Platform streaming video berbasis cloud yang dibangun menggunakan layanan AWS dengan arsitektur asynchronous dan event-driven.

Project ini memungkinkan pengguna untuk mengunggah video MP4, memproses video secara asynchronous menggunakan server worker, mengubah video menjadi format HLS yang dapat di-streaming, serta menampilkan status pemrosesan video kepada pengguna.

## Arsitektur

<img width="622" height="753" alt="image_2_rf4fyp" src="https://github.com/user-attachments/assets/44b03a59-e57c-4987-aff6-49a969bfb8fc" />


### AWS Services

- **Amazon EC2** - Menjalankan Web Server dan Worker Server.
- **Amazon S3** - Menyimpan video mentah dan hasil pemrosesan video.
- **Amazon SQS** - Menyimpan dan membuat antrian pekerjaan pemrosesan video.
- **Amazon DynamoDB** - Menyimpan metadata dan status pemrosesan video.
- **Amazon VPC** - Menyediakan lingkungan jaringan untuk resource EC2.
- **AWS IAM** - Mengatur permission dan akses antar-resource AWS.

### Teknologi

- Python
- Flask
- FFmpeg
- HLS (HTTP Live Streaming)
- AWS SDK
- Linux

---

## Cara Kerja

Project ini memiliki beberapa tahapan utama, mulai dari upload video hingga video siap untuk di-streaming.

### 1. Web Server

Web Server berjalan pada Amazon EC2 menggunakan Flask dan bertanggung jawab untuk menangani interaksi dengan pengguna.

Ketika pengguna mengunggah file MP4:

1. Web Server menerima file dari pengguna.
2. File diunggah ke **Input S3 Bucket**.
3. Informasi video disimpan ke DynamoDB.
4. Status awal video ditetapkan sebagai **"Queued"**.


### 2. S3 Event dan SQS Queue

Setelah video berhasil masuk ke Input S3 Bucket, Amazon S3 secara otomatis mengirimkan event notification ke Amazon SQS.

SQS digunakan sebagai buffer untuk menyimpan pekerjaan pemrosesan video hingga Worker Server siap memprosesnya.

### 3. Worker Server

Worker Server berjalan pada EC2 terpisah dan bertanggung jawab untuk
melakukan pemrosesan video.

Worker Server secara berkala melakukan polling terhadap SQS Queue.

Ketika terdapat pekerjaan:

1. Worker mengambil message dari SQS.
2. Worker mengidentifikasi video yang perlu diproses.
3. Video mentah di-download dari Input S3 Bucket.
4. FFmpeg digunakan untuk mengubah video MP4 menjadi format HLS.
5. Hasil pemrosesan berupa file .m3u8 dan video chunks di-upload ke
6. Output S3 Bucket.
7. Status video pada DynamoDB diperbarui menjadi "Ready".


### 4. Video Player

Setelah proses pemrosesan selesai, status video pada DynamoDB berubah menjadi
"Ready".

Web application kemudian dapat mengetahui bahwa video telah siap untuk
diputar.

Browser mengambil video HLS dari Output S3 Bucket dan melakukan streaming kepada pengguna.

### Tampilan Website
<img width="1917" height="907" alt="Screenshot 2026-09-09 083512" src="https://github.com/user-attachments/assets/7d583a25-6e30-4e94-a574-9fc713377bcf" />
<img width="1917" height="908" alt="Screenshot 2026-09-09 082754" src="https://github.com/user-attachments/assets/085a1f30-4560-49ed-8ad4-9931c57900ae" />
