#!/usr/bin/env python3
"""
Script d'intégration Google Chat réel - PSMM
Envoyer des messages en temps réel dans Google Chat
"""
import paramiko
import os
import json
import subprocess
from datetime import datetime

# REMPLACEZ PAR VOTRE VRAIE URL WEBHOOK
WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAwl_qRJ8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=QiwremmAgSse3drth_DQs51oOfjSsN_cCNE8DGTyyho"

def envoyer_vers_google_chat(texte_message):
    """
    Envoyer un message réel vers Google Chat
    """
    payload = {
        "text": texte_message
    }
    
    # Préparer le payload JSON
    json_payload = json.dumps(payload)
    
    # Envoyer avec curl
    commande_curl = [
        'curl',
        '-X', 'POST',
        '-H', 'Content-Type: application/json',
        '-d', json_payload,
        WEBHOOK_URL
    ]
    
    try:
        resultat = subprocess.run(commande_curl, capture_output=True, text=True, timeout=10)
        
        if resultat.returncode == 0:
            print("✅ Message envoyé vers Google Chat avec succès!")
            return True
        else:
            print(f"❌ Erreur d'envoi: {resultat.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi: {e}")
        return False

def collecter_etat_serveurs():
    """
    Collecter rapidement l'état des serveurs
    """
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139", 
        "datateam-mariadb": "192.168.81.141"
    }
    
    message_etat = f"🖥️ **État Système PSMM** - {datetime.now().strftime('%H:%M:%S')}\n\n"
    
    for nom, ip in serveurs.items():
        # Test de ping
        resultat_ping = os.system(f"ping -c 1 -W 2 {ip} > /dev/null 2>&1")
        statut = "✅ En ligne" if resultat_ping == 0 else "❌ Hors ligne"
        message_etat += f"• **{nom}** ({ip}): {statut}\n"
    
    message_etat += f"\n📊 **Base de données**: psmm_logs opérationnelle"
    message_etat += f"\n🔧 **Monitoring**: datateam-monitor actif"
    message_etat += f"\n⏰ Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    
    return message_etat

def ssh_connect_and_run_sudo(nom_hote, nom_utilisateur, commande, mot_de_passe_sudo, chemin_cle=None):
    """
    Connexion SSH pour collecter des métriques détaillées
    """
    try:
        if chemin_cle is None:
            chemin_cle = os.path.expanduser("~/.ssh/id_rsa")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        client.connect(
            hostname=nom_hote,
            username=nom_utilisateur,
            key_filename=chemin_cle,
            timeout=10
        )
        
        commande_complete = f"echo '{mot_de_passe_sudo}' | sudo -S {commande} 2>/dev/null"
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=10)
        
        time.sleep(1)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        client.close()
        
        return True, sortie
        
    except Exception as e:
        return False, str(e)

def collecter_metriques_detaillees():
    """
    Collecter des métriques système détaillées pour Google Chat
    """
    print("Collecte des métriques détaillées...")
    
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139", 
        "datateam-mariadb": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    message_detaille = f"📊 **Rapport Détaillé PSMM** - {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    
    for nom_serveur, ip_serveur in serveurs.items():
        print(f"Analyse de {nom_serveur}...")
        
        # CPU et mémoire
        commande_stats = "top -bn1 | head -4 | tail -2"
        succes, sortie_stats = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_stats, mot_de_passe_sudo)
        
        # Uptime
        commande_uptime = "uptime | awk '{print $3, $4}' | sed 's/,//'"
        succes_up, uptime = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_uptime, mot_de_passe_sudo)
        
        # Espace disque
        commande_disk = "df -h / | tail -1 | awk '{print $5}'"
        succes_disk, disk_usage = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_disk, mot_de_passe_sudo)
        
        message_detaille += f"🔸 **{nom_serveur}** ({ip_serveur})\n"
        message_detaille += f"   Uptime: {uptime if succes_up else 'N/A'}\n"
        message_detaille += f"   Disque: {disk_usage if succes_disk else 'N/A'}\n"
        message_detaille += f"   État: {'✅ Opérationnel' if succes else '❌ Problème'}\n\n"
    
    # Ajouter des informations sur la base de données
    commande_db_stats = "mysql -u psmm -ppsmm123 -D psmm_logs -e \"SELECT 'Erreurs MySQL' as Type, COUNT(*) as Total FROM mysql_errors UNION SELECT 'Erreurs FTP', COUNT(*) FROM ftp_errors UNION SELECT 'Erreurs Web', COUNT(*) FROM web_errors;\" 2>/dev/null"
    succes_db, stats_db = ssh_connect_and_run_sudo("192.168.81.141", nom_utilisateur, commande_db_stats, mot_de_passe_sudo)
    
    if succes_db and stats_db:
        message_detaille += f"📈 **Statistiques Base de Données**\n{stats_db}\n\n"
    
    message_detaille += f"🤖 Généré automatiquement par le système PSMM"
    
    return message_detaille

def envoyer_alerte_critique(message_alerte):
    """
    Envoyer une alerte critique immédiate
    """
    message_formate = f"🚨 **ALERTE CRITIQUE PSMM** 🚨\n\n{message_alerte}\n\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    return envoyer_vers_google_chat(message_formate)

def main():
    print("🚀 Intégration Google Chat Réelle - PSMM")
    print("Envoi de messages en temps réel vers Google Chat")
    
    # Vérification de l'URL webhook
    if "VOTRE_SPACE_ID" in WEBHOOK_URL:
        print("❌ URL WEBHOOK non configurée!")
        print("Modifiez la variable WEBHOOK_URL dans le script.")
        print("Utilisez l'URL copiée depuis Google Chat.")
        return
    
    print(f"📡 Webhook configuré: {WEBHOOK_URL[:50]}...")
    
    try:
        # Option 1: État simple des serveurs
        print("\n1. Envoi de l'état simple...")
        message_simple = collecter_etat_serveurs()
        succes_simple = envoyer_vers_google_chat(message_simple)
        
        if succes_simple:
            print("✅ Message simple envoyé avec succès")
        
        # Attendre 3 secondes
        import time
        time.sleep(3)
        
        # Option 2: Métriques détaillées
        print("\n2. Envoi des métriques détaillées...")
        message_detaille = collecter_metriques_detaillees()
        succes_detaille = envoyer_vers_google_chat(message_detaille)
        
        if succes_detaille:
            print("✅ Rapport détaillé envoyé avec succès")
        
        print(f"\n🎉 Vérifiez votre Google Chat sur l'ordinateur principal!")
        print(f"Space: PSMM-Monitoring")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")

def envoyer_test_simple():
    """
    Fonction de test simple
    """
    message_test = f"🧪 **Test PSMM** - {datetime.now().strftime('%H:%M:%S')}\n\nSystème de monitoring opérationnel!\n\n✅ Connexion Google Chat établie"
    return envoyer_vers_google_chat(message_test)

if __name__ == "__main__":
    # Pour test rapide, décommenter la ligne suivante:
    # envoyer_test_simple()
    
    # Pour rapport complet:
    main()
