from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
import psycopg2
import random
import string
import os
import base64
app = FastAPI()

def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT", 5432)  # Mặc định cổng PostgreSQL là 5432
    )
    return conn

# Hàm tạo short link
def generate_short_link(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def base64_decode(encoded_string):
  decoded_bytes = base64.b64decode(encoded_string)
  decoded_string = decoded_bytes.decode('utf-8')
  return decoded_string
# Tạo ứng dụng FastAPI
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tạo bảng lưu thông tin IP từ API /check
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS urls (
        id SERIAL PRIMARY KEY,
        short_link VARCHAR(10) UNIQUE NOT NULL,
        long_url TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

create_tables()

@app.get("/short")
async def shorten_url(url: str):
    decoded_url = base64_decode(url)
    conn = get_db_connection()
    cursor = conn.cursor()
    # Kiểm tra nếu URL đã tồn tại
    cursor.execute("SELECT short_link FROM urls WHERE long_url = %s", (decoded_url,))
    result = cursor.fetchone()
    if result:
        short_link = result[0]
        conn.close()
        return {"url": f"https://binh.store/{short_link}"}

    # Tạo short link
    short_link = generate_short_link()
    while True:
        cursor.execute("SELECT 1 FROM urls WHERE short_link = %s", (short_link,))
        if not cursor.fetchone():  # Nếu không có short_link nào trùng
            break
        short_link = generate_short_link()

    # Lưu vào database
    cursor.execute("INSERT INTO urls (short_link, long_url) VALUES (%s, %s)", (short_link, decoded_url))
    conn.commit()
    conn.close()

    return {"url": f"https://binh.store/{short_link}"}

@app.get("/{short_link}")
async def redirect_to_long_url(short_link: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tra cứu short link
    cursor.execute("SELECT long_url FROM urls WHERE short_link = %s", (short_link,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="Short link not found")

    long_url = result[0]
    response = RedirectResponse(url=long_url)
    response.headers["X-Custom-Title"] = "Welcome to LopThayBinh"
    return response

if __name__ == "__main__":
    import uvicorn
    # Chạy ứng dụng trên cổng 10000, cổng mặc định trên Render
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
