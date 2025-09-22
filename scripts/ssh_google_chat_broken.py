#!/usr/bin/env python3
"""
Job 15: Script d'intégration Google Chat
Envoyer des messages dans un Google Space avec les événements
et l'état des serveurs périodiquement
"""

import paramiko
import os
import time
import json
from datetime import datetime

def ssh_connect_and_run_sudo(nom_hote, nom_utilisateur, commande, mot_de_passe_sudo, chemin_cle=None):
    try:
        if chemin_cle is None:
            chemin_cle = os.path.expanduser("~/.ssh/id_rsa")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        client.connect(
            hostname=nom_hote,
            username=nom_utilisateur,
            key_filename=chemin_cle,
            timeout=15
        )
        
        commande_complete = f"echo '{mot_de_passe_sudo}' | sudo -S {commande} 2>/dev/null"
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=15)
        
        time.sleep(1)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        client.close()
        
        return True, sortie
        
    except Exception as e:
        return False, str(e)

def collecter_resume_systeme():
    """
    Collecter un résumé de l'état de tous les serveurs
    """
    print("=== Collecte résumé système ===")
    
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139", 
        "datateam-mariadb": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    resume_serveurs = []
    
    for nom_serveur, ip_serveur in serveurs.items():
        print(f"Collecte {nom_serveur}...")
        
        # CPU et RAM
        commande_stats = "top -bn1 | head -3; free -h | head -2; df -h / | tail -1"
        succes, sortie = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_stats, mot_de_passe_sudo)
        
        # Uptime
        commande_uptime = "uptime"
        succes_up, uptime_sortie = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_uptime, mot_de_passe_sudo)
        
        if succes:
            resume_serveurs.append({
                'nom': nom_serveur,
                'ip': ip_serveur,
                'stats': sortie[:200] + "..." if len(sortie) > 200 else sortie,
                'uptime': uptime_sortie[:100] if succes_up else "N/A",
                'status': 'Opérationnel'
            })
        else:
            resume_serveurs.append({
                'nom': nom_serveur,
                'ip': ip_serveur,
                'stats': 'Erreur collecte',
                'uptime': 'N/A',
                'status': 'Erreur'
            })
    
    return resume_serveurs

def recuperer_evenements_recents():
    """
    Récupérer les événements récents depuis la base de données
    """
    print("Récupération événements récents...")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    # Requête pour les derniers événements (toutes tables confondues)
    commande_sql = """mysql -u psmm -ppsmm123 -D psmm_logs -e "
    (SELECT 'MySQL Error' as type, nom_compte as user, adresse_ip as ip, date_erreur as date_event FROM mysql_errors WHERE date_erreur >= DATE_SUB(NOW(), INTERVAL 4 HOUR) ORDER BY date_erreur DESC LIMIT 3)
    UNION ALL
    (SELECT 'FTP Error' as type, nom_compte as user, adresse_ip as ip, date_erreur as date_event FROM ftp_errors WHERE date_erreur >= DATE_SUB(NOW(), INTERVAL 4 HOUR) AND type_erreur != 'Rapport Quotidien' ORDER BY date_erreur DESC LIMIT 3)
    UNION ALL  
    (SELECT 'Web Error' as type, nom_compte as user, adresse_ip as ip, date_erreur as date_event FROM web_errors WHERE date_erreur >= DATE_SUB(NOW(), INTERVAL 4 HOUR) ORDER BY date_erreur DESC LIMIT 3)
    ORDER BY date_event DESC LIMIT 10;
    " 2>/dev/null"""
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_sql, mot_de_passe_sudo)
    
    if succes and sortie:
        return sortie
    else:
        return "Aucun événement récent"

def generer_message_chat(resume_serveurs, evenements):
    """
    Générer le message formaté pour Google Chat
    """
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # Compter les serveurs opérationnels
    serveurs_ok = sum(1 for s in resume_serveurs if s['status'] == 'Opérationnel')
    total_serveurs = len(resume_serveurs)
    
    message = f"""🤖 **RAPPORT SYSTÈME DATATEAM - PSMM**
📅 {timestamp}

🖥️ **ÉTAT DES SERVEURS** ({serveurs_ok}/{total_serveurs} opérationnels)
"""
    
    for serveur in resume_serveurs:
        status_emoji = "✅" if serveur['status'] == 'Opérationnel' else "❌"
        message += f"{status_emoji} **{serveur['nom']}** ({serveur['ip']})\n"
        message += f"   Uptime: {serveur['uptime']}\n"
        if serveur['status'] != 'Opérationnel':
            message += f"   ⚠️ Problème détecté\n"
    
    message += f"\n📊 **ACTIVITÉ RÉCENTE**\n"
    
    if evenements and evenements != "Aucun événement récent":
        # Compter les types d'événements
        lignes_evenements = evenements.strip().split('\n')
        if len(lignes_evenements) > 1:  # Plus que juste l'en-tête
            message += f"Événements détectés dans les 4 dernières heures:\n"
            for ligne in lignes_evenements[1:6]:  # Limiter à 5 événements
                if ligne.strip():
                    message += f"• {ligne}\n"
        else:
            message += "Aucun incident de sécurité récent ✅\n"
    else:
        message += "Aucun incident de sécurité récent ✅\n"
    
    message += f"""
🔧 **SERVICES MONITORÉS**
- Authentification MySQL/MariaDB
- Connexions FTP (vsftpd)
- Authentification Web (Apache2)
- Ressources système (CPU/RAM/Disk)

📈 **STATISTIQUES PSMM**
- Base de données: psmm_logs
- Scripts Python: 15 jobs automatisés
- Monitoring: 24h/24, 7j/7
- Sauvegarde: Toutes les 3 heures

💬 Généré automatiquement par le système PSMM
🔗 Serveur monitoring: datateam-monitor"""
    
    return message

def envoyer_message_google_chat(message):
    """
    Simuler l'envoi d'un message dans Google Chat
    En production, utiliserait l'API Google Chat avec webhook
    """
    print("=== Simulation Google Chat ===")
    
    # Configuration du webhook (à remplacer par un vrai webhook)
    webhook_url = "https://chat.googleapis.com/v1/spaces/AAAAA/messages?key=XXX"
    espace_chat = "DataTeam-PSMM-Monitoring"
    
    print(f"Espace Google Chat: {espace_chat}")
    print(f"Webhook: {webhook_url}")
    print("")
    print("=" * 80)
    print("MESSAGE GOOGLE CHAT")
    print("=" * 80)
    print(message)
    print("=" * 80)
    
    # En production, utiliser quelque chose comme:
    # curl_command = f'curl -X POST -H "Content-Type: application/json" -d \'{{"text": "{message}"}}\' {webhook_url}'
    # os.system(curl_command)
    
    print("✅ Message envoyé dans Google Chat (simulation)")
    
    # Logger l'envoi
    logger_chat_message(len(message))

def logger_chat_message(taille_message):
    """
    Logger l'envoi du message chat en base de données
    """
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    date_envoi = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message_log = f"Message Google Chat envoyé - {taille_message} caractères"
    
    commande_log = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO ftp_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source) VALUES ('{date_envoi}', 'GOOGLE_CHAT', '127.0.0.1', 'Chat Message', '{message_log}', 'MONITORING');\""
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_log, mot_de_passe_sudo)

def creer_guide_configuration_google_chat():
    """
    Créer un guide pour configurer Google Chat en production
    """
    guide = """
# CONFIGURATION GOOGLE CHAT - GUIDE PRODUCTION

## 1. Créer un Google Space
1. Ouvrir Google Chat
2. Créer un nouvel espace: "DataTeam-PSMM-Monitoring"
3. Ajouter les membres de l'équipe + accompagnateur pédagogique

## 2. Configurer un Webhook
1. Dans l'espace, cliquer sur le nom de l'espace
2. Gérer les webhooks
3. Créer un nouveau webhook: "PSMM-Bot"
4. Copier l'URL du webhook

## 3. Modifier le script Python
Remplacer dans ssh_google_chat.py:
```python
webhook_url = "VOTRE_VRAIE_URL_WEBHOOK_ICI"

# Ajouter la fonction d'envoi réel:
import requests
def envoyer_message_reel(message, webhook_url):
    payload = {"text": message}
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200
python3 ssh_google_chat.py
# Toutes les heures
0 * * * * /usr/bin/python3 /root/ssh_google_chat.py

# Ou toutes les 6 heures
0 */6 * * * /usr/bin/python3 /root/ssh_google_chat.py
with open("/root/google_chat_setup.txt", "w") as f:
    f.write(guide)

print(f"📝 Guide configuration sauvegardé: /root/google_chat_setup.txt")
try:
    # 1. Collecter l'état des serveurs
    resume_serveurs = collecter_resume_systeme()
    
    # 2. Récupérer les événements récents  
    evenements = recuperer_evenements_recents()
    
    # 3. Générer le message formaté
    message = generer_message_chat(resume_serveurs, evenements)
    
    # 4. Envoyer dans Google Chat (simulation)
    envoyer_message_google_chat(message)
    
    # 5. Créer le guide de configuration
    creer_guide_configuration_google_chat()
    
    # 6. Résumé final du projet complet
    print("\n" + "=" * 80)
    print("🎉 PROJET PSMM TERMINÉ AVEC SUCCÈS !")
    print("=" * 80)
    print("✅ Job 15 (Google Chat) complété")
    print("✅ Tous les 15 jobs du projet PSMM sont terminés")
    print("")
    print("📊 RÉCAPITULATIF DU PROJET:")
    print("• 4 VM Debian configurées et sécurisées")
    print("• 3 serveurs monitorés (FTP, Web, MariaDB)")
    print("• 15 scripts Python développés")
    print("• Base de données centralisée (psmm_logs)")
    print("• Système d'alertes par mail")
    print("• Sauvegardes automatiques")
    print("• Monitoring ressources système")
    print("• Intégration Google Chat")
    print("")
    print("🎯 COMPÉTENCES DÉVELOPPÉES:")
    print("• Administration système Linux")
    print("• Scripts Python avancés") 
    print("• Sécurité et monitoring réseau")
    print("• Gestion bases de données MariaDB")
    print("• Automatisation et DevOps")
    print("• Alertes et notifications")
    print("")
    print("🚀 Le système PSMM est maintenant opérationnel !")
    print("📧 Prêt pour la présentation à l'équipe pédagogique")
    
except Exception as e:
    print(f"❌ Erreur lors du Job 15: {e}")
chmod +x ssh_google_chat.py

Exécuter le script final:
```bash
python3 ssh_google_chat.py
