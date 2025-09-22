#!/usr/bin/env python3
"""
Google Chat mesajlarını yakalama servisi
Ana bilgisayardan gelen mesajları dinler ve PSMM'de görüntüler
"""
from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

# Gelen mesajları saklamak için dosya
MESAJ_DOSYASI = "/tmp/google_chat_mesajlar.log"

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Google Chat'tan gelen mesajları yakala
    """
    try:
        # JSON verisini al
        veri = request.get_json()
        
        if veri:
            # Mesaj bilgilerini çıkar
            mesaj_metni = veri.get('message', {}).get('text', '')
            gonderen = veri.get('message', {}).get('sender', {}).get('displayName', 'Bilinmeyen')
            zaman = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Log dosyasına yaz
            log_satiri = f"[{zaman}] {gonderen}: {mesaj_metni}\n"
            
            with open(MESAJ_DOSYASI, 'a', encoding='utf-8') as f:
                f.write(log_satiri)
            
            print(f"✅ Yeni mesaj: {gonderen} - {mesaj_metni}")
            
            # Google Chat'e yanıt gönder (opsiyonel)
            yanit = {
                "text": f"PSMM Sistemi: Mesajınız alındı - {zaman}"
            }
            return jsonify(yanit)
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return jsonify({"text": "Hata oluştu"}), 500
    
    return jsonify({"text": "OK"}), 200

@app.route('/mesajlar', methods=['GET'])
def mesajlari_gor():
    """
    Son mesajları göster
    """
    try:
        if os.path.exists(MESAJ_DOSYASI):
            with open(MESAJ_DOSYASI, 'r', encoding='utf-8') as f:
                mesajlar = f.readlines()[-10:]  # Son 10 mesaj
            
            return "<br>".join(mesajlar)
        else:
            return "Henüz mesaj yok"
    except:
        return "Mesajlar okunamadı"

if __name__ == '__main__':
    print("🚀 Google Chat Webhook Receiver başlatılıyor...")
    print("📡 Port 5000'de dinleniyor")
    print("🔗 Webhook URL: http://SUNUCU_IP:5000/webhook")
    print("👀 Mesajları görmek için: http://SUNUCU_IP:5000/mesajlar")
    
    # 0.0.0.0 ile tüm network interface'lerden erişim
    app.run(host='0.0.0.0', port=5000, debug=False)
