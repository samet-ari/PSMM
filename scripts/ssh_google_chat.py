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
    commande_sql = "mysql -u psmm -ppsmm123 -D psmm_logs -e \"SELECT 'MySQL Error' as type, nom_compte as user, adresse_ip as ip, date_erreur as date_event FROM mysql_errors WHERE date_erreur >= DATE_SUB(NOW(), INTERVAL 4 HOUR) ORDER BY date_erreur DESC LIMIT 5;\" 2>/dev/null"
    
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
    
    message = f"RAPPORT SYSTÈME DATATEAM - PSMM\\n"
    message += f"Date: {timestamp}\\n\\n"
    message += f"ÉTAT DES SERVEURS ({serveurs_ok}/{total_serveurs} opérationnels)\\n"
    
    for serveur in resume_serveurs:
        status_emoji = "OK" if serveur['status'] == 'Opérationnel' else "ERREUR"
        message += f"• {serveur['nom']} ({serveur['ip']}): {status_emoji}\\n"
        message += f"  Uptime: {serveur['uptime']}\\n"
    
    message += f"\\nACTIVITÉ RÉCENTE:\\n"
    
    if evenements and evenements != "Aucun événement récent":
        message += "Événements détectés:\\n"
        lignes_evenements = evenements.strip().split('\n')
        for ligne in lignes_evenements[:3]:  # Limiter à 3 événements
            if ligne.strip():
                message += f"• {ligne}\\n"
    else:
        message += "Aucun incident récent\\n"
    
    message += f"\\nSERVICES MONITORÉS:\\n"
    message += f"• MySQL/MariaDB, FTP, Web Apache\\n"
    message += f"• Ressources système (CPU/RAM/Disk)\\n"
    message += f"\\nGénéré automatiquement par PSMM"
    
    return message

def envoyer_message_google_chat(message):
    """
    Simuler l'envoi d'un message dans Google Chat
    """
    print("=== Simulation Google Chat ===")
    
    webhook_url = "https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY"
    espace_chat = "DataTeam-PSMM-Monitoring"
    
    print(f"Espace Google Chat: {espace_chat}")
    print(f"Webhook: {webhook_url}")
    print("")
    print("=" * 60)
    print("MESSAGE GOOGLE CHAT")
    print("=" * 60)
    print(message.replace('\\n', '\n'))
    print("=" * 60)
    
    print("Message envoyé dans Google Chat (simulation)")
    
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

def creer_guide_configuration():
    """
    Créer un guide pour configurer Google Chat
    """
    guide_text = "# CONFIGURATION GOOGLE CHAT - GUIDE\\n"
    guide_text += "# 1. Créer un Google Space\\n"
    guide_text += "# 2. Configurer un Webhook\\n" 
    guide_text += "# 3. Modifier le script Python\\n"
    guide_text += "# 4. Tester l'envoi\\n"
    guide_text += "# 5. Planifier avec cron\\n"
    
    with open("/root/google_chat_setup.txt", "w") as f:
        f.write(guide_text.replace('\\n', '\n'))
    
    print(f"Guide configuration sauvegardé: /root/google_chat_setup.txt")

def main():
    """
    Fonction principale - Envoyer le rapport système dans Google Chat
    """
    print("Intégration Google Chat - Job 15 (FINAL)")
    print("Génération du rapport système pour Google Space")
    print("")
    
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
        creer_guide_configuration()
        
        # 6. Résumé final
        print("")
        print("=" * 60)
        print("PROJET PSMM TERMINÉ AVEC SUCCÈS !")
        print("=" * 60)
        print("Job 15 (Google Chat) complété")
        print("Tous les 15 jobs du projet PSMM sont terminés")
        print("")
        print("RÉCAPITULATIF DU PROJET:")
        print("• 4 VM Debian configurées")
        print("• 3 serveurs monitorés")
        print("• 15 scripts Python développés")
        print("• Base de données centralisée")
        print("• Système d'alertes par mail")
        print("• Sauvegardes automatiques")
        print("• Monitoring ressources système")
        print("• Intégration Google Chat")
        print("")
        print("Le système PSMM est maintenant opérationnel !")
        
    except Exception as e:
        print(f"Erreur lors du Job 15: {e}")

if __name__ == "__main__":
    main()
