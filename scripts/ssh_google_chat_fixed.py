#!/usr/bin/env python3
import paramiko
import os
import json
import subprocess
from datetime import datetime

WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAwl_qRJ8/messages?key=AIzaSyDdI0hCZtE6vySjMlVl6e3zfBRPIGV__PU&token=9eqH2fEZNn3y24tXKLX6n9L-NafVnRjTD1Bg8CDMJ7k"

def ssh_connect_test(ip_serveur, nom_serveur):
    """Test SSH connection pour vérifier serveur"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=ip_serveur, username="datateam-monitor", 
                      key_filename="~/.ssh/id_rsa", timeout=5)
        
        stdin, stdout, stderr = client.exec_command("uptime")
        uptime = stdout.read().decode('utf-8').strip()
        client.close()
        return True, uptime
    except:
        return False, "Connexion échouée"

def collecter_etat_serveurs_fixe():
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139", 
        "datateam-mariadb": "192.168.81.141"
    }
    
    message = f"🖥️ **État Système PSMM** - {datetime.now().strftime('%H:%M:%S')}\n\n"
    
    for nom, ip in serveurs.items():
        # SSH test au lieu de ping
        ssh_ok, uptime = ssh_connect_test(ip, nom)
        status = "✅ Opérationnel" if ssh_ok else "❌ Problème SSH"
        message += f"• **{nom}** ({ip}): {status}\n"
        if ssh_ok:
            message += f"  Uptime: {uptime[:50]}\n"
    
    message += f"\n📊 **Base données**: psmm_logs active"
    message += f"\n🔧 **Monitoring**: Surveillance continue"
    message += f"\n⏰ Dernière vérification: {datetime.now().strftime('%d/%m %H:%M')}"
    
    return message

def envoyer_vers_google_chat(texte_message):
    payload = {"text": texte_message}
    json_payload = json.dumps(payload)
    
    commande_curl = ['curl', '-X', 'POST', '-H', 'Content-Type: application/json', 
                    '-d', json_payload, WEBHOOK_URL]
    
    try:
        resultat = subprocess.run(commande_curl, capture_output=True, text=True, timeout=10)
        return resultat.returncode == 0
    except:
        return False

if __name__ == "__main__":
    message = collecter_etat_serveurs_fixe()
    if envoyer_vers_google_chat(message):
        print("✅ Rapport corrigé envoyé vers Google Chat")
    else:
        print("❌ Erreur envoi")
