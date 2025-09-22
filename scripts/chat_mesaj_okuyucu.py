#!/usr/bin/env python3
"""
Google Chat mesajlarını okuma ve gösterme
"""
import os
from datetime import datetime

MESAJ_DOSYASI = "/tmp/google_chat_mesajlar.log"

def mesajlari_oku():
    """
    Gelen mesajları terminalde göster
    """
    print("📱 Google Chat Mesajları:")
    print("=" * 50)
    
    if os.path.exists(MESAJ_DOSYASI):
        with open(MESAJ_DOSYASI, 'r', encoding='utf-8') as f:
            mesajlar = f.readlines()
        
        if mesajlar:
            for mesaj in mesajlar[-10:]:  # Son 10 mesaj
                print(mesaj.strip())
        else:
            print("Henüz mesaj yok")
    else:
        print("Mesaj dosyası bulunamadı")
    
    print("=" * 50)

def mesaj_gonder_yanit(yanit_metni):
    """
    Ana bilgisayara yanıt göndermek için mevcut script'i kullan
    """
    from ssh_google_chat_real import envoyer_vers_google_chat
    
    yanit_mesaji = f"🤖 PSMM Yanıt: {yanit_metni}\n\n⏰ {datetime.now().strftime('%H:%M:%S')}"
    return envoyer_vers_google_chat(yanit_mesaji)

def interaktif_sohbet():
    """
    İnteraktif sohbet modu
    """
    print("🎯 İnteraktif Sohbet Modu")
    print("'quit' yazarak çıkabilirsin")
    
    while True:
        # Gelen mesajları kontrol et
        mesajlari_oku()
        
        # Yanıt ver
        yanit = input("\n💬 Yanıt yaz (veya 'quit'): ")
        
        if yanit.lower() == 'quit':
            break
        
        if yanit.strip():
            mesaj_gonder_yanit(yanit)
            print("✅ Yanıt gönderildi!")
        
        print("\n" + "-" * 30)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "oku":
            mesajlari_oku()
        elif sys.argv[1] == "sohbet":
            interaktif_sohbet()
        elif sys.argv[1] == "yanit":
            mesaj_gonder_yanit(" ".join(sys.argv[2:]))
    else:
        mesajlari_oku()
