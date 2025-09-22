#!/usr/bin/env python3
"""
Job 13: Script de monitoring avec limitation d'envoi de mails
Reprendre le script précédent en modifiant pour l'envoi du mail:
ne pas envoyer plus d'un mail par heure à l'administrateur
Toujours en tâche planifiée toutes les 5 min
"""

import paramiko
import os
import time
import json
from datetime import datetime, timedelta

# ========== SEUILS D'ALERTE - MODIFIABLES ==========
SEUILS_ALERTE = {
    'CPU_MAX': 70.0,
    'RAM_MAX': 80.0,  
    'DISK_MAX': 90.0,
    'LOAD_MAX': 5.0
}

CONFIG_MAIL = {
    'destinataire': 'admin@datateam.local',
    'expediteur': 'monitoring@datateam.local',
    'intervalle_min_minutes': 60  # Minimum 60 minutes entre les mails
}

# Fichier pour tracker les envois de mails
FICHIER_TRACKING_MAIL = "/tmp/psmm_last_mail.json"
# ===================================================

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

def peut_envoyer_mail():
    """
    Vérifier si on peut envoyer un mail (pas envoyé dans la dernière heure)
    """
    try:
        # Lire le fichier de tracking
        if os.path.exists(FICHIER_TRACKING_MAIL):
            with open(FICHIER_TRACKING_MAIL, 'r') as f:
                tracking_data = json.load(f)
            
            # Récupérer la dernière date d'envoi
            derniere_date_str = tracking_data.get('dernier_envoi', '')
            if derniere_date_str:
                derniere_date = datetime.fromisoformat(derniere_date_str)
                maintenant = datetime.now()
                
                # Calculer la différence en minutes
                diff_minutes = (maintenant - derniere_date).total_seconds() / 60
                
                print(f"ℹ️ Dernier mail envoyé il y a {int(diff_minutes)} minutes")
                
                if diff_minutes < CONFIG_MAIL['intervalle_min_minutes']:
                    temps_restant = CONFIG_MAIL['intervalle_min_minutes'] - int(diff_minutes)
                    print(f"🚫 Throttling actif - Prochain mail possible dans {temps_restant} minutes")
                    return False, temps_restant
                else:
                    print("✅ Délai respecté - Mail autorisé")
                    return True, 0
            else:
                print("ℹ️ Aucun mail précédent enregistré")
                return True, 0
        else:
            print("ℹ️ Premier mail du système")
            return True, 0
            
    except Exception as e:
        print(f"⚠️ Erreur lecture tracking: {e}")
        return True, 0  # En cas d'erreur, autoriser l'envoi

def enregistrer_envoi_mail():
    """
    Enregistrer la date/heure du dernier envoi de mail
    """
    try:
        tracking_data = {
            'dernier_envoi': datetime.now().isoformat(),
            'nombre_envois_total': 1
        }
        
        # Si le fichier existe, récupérer le compteur
        if os.path.exists(FICHIER_TRACKING_MAIL):
            with open(FICHIER_TRACKING_MAIL, 'r') as f:
                ancien_data = json.load(f)
                tracking_data['nombre_envois_total'] = ancien_data.get('nombre_envois_total', 0) + 1
        
        # Sauvegarder
        with open(FICHIER_TRACKING_MAIL, 'w') as f:
            json.dump(tracking_data, f)
        
        print(f"📝 Envoi #{tracking_data['nombre_envois_total']} enregistré")
        
    except Exception as e:
        print(f"⚠️ Erreur enregistrement tracking: {e}")

def collecter_metriques_rapide(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Version allégée de la collecte de métriques pour Job 13
    """
    metriques = {
        'serveur_nom': nom_serveur,
        'serveur_ip': ip_serveur,
        'alertes': []
    }
    
    print(f"🔍 {nom_serveur}:", end=" ")
    
    # CPU
    commande_cpu = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
    succes, cpu_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_cpu, mot_de_passe_sudo)
    
    if succes and cpu_output:
        try:
            cpu_usage = float(cpu_output.replace(',', '.'))
            if cpu_usage > SEUILS_ALERTE['CPU_MAX']:
                metriques['alertes'].append(f"CPU {cpu_usage}%")
            print(f"CPU {cpu_usage}%", end=" | ")
        except:
            pass
    
    # RAM
    commande_ram = "free -m | awk 'NR==2{printf \"%.1f\", $3*100/$2}'"
    succes, ram_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_ram, mot_de_passe_sudo)
    
    if succes and ram_output:
        try:
            ram_usage = float(ram_output)
            if ram_usage > SEUILS_ALERTE['RAM_MAX']:
                metriques['alertes'].append(f"RAM {ram_usage}%")
            print(f"RAM {ram_usage}%", end=" | ")
        except:
            pass
    
    # Disk
    commande_disk = "df / | awk 'NR==2{print $5}' | sed 's/%//'"
    succes, disk_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_disk, mot_de_passe_sudo)
    
    if succes and disk_output:
        try:
            disk_usage = float(disk_output)
            if disk_usage > SEUILS_ALERTE['DISK_MAX']:
                metriques['alertes'].append(f"DISK {disk_usage}%")
            print(f"DISK {disk_usage}%", end="")
        except:
            pass
    
    if metriques['alertes']:
        print(f" 🚨 ALERTES: {', '.join(metriques['alertes'])}")
    else:
        print(" ✅")
    
    return metriques

def envoyer_alerte_mail_avec_throttling(alertes_globales, temps_restant=None):
    """
    Envoyer une alerte mail en respectant la limitation d'envoi
    """
    if not alertes_globales:
        return
    
    # Vérifier si on peut envoyer le mail
    peut_envoyer, temps_attente = peut_envoyer_mail()
    
    if not peut_envoyer:
        print(f"\n🚫 MAIL SUPPRIMÉ - Throttling actif")
        print(f"   Prochain mail autorisé dans {temps_attente} minutes")
        
        # Logger la suppression
        message_log = f"Mail supprimé par throttling - {len(alertes_globales)} alertes en attente"
        logger_action_mail(message_log, "THROTTLED")
        return False
    
    # Mail autorisé - Envoyer
    print(f"\n✅ ENVOI ALERTE MAIL AUTORISÉ")
    
    date_alerte = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    contenu_mail = f"""
🚨 ALERTE SYSTÈME DATATEAM - SEUILS DÉPASSÉS 🚨

Date: {date_alerte}
Nombre de serveurs en alerte: {len(alertes_globales)}

ALERTES ACTUELLES:
"""
    
    for serveur, alertes in alertes_globales.items():
        contenu_mail += f"\n🔴 {serveur}: {', '.join(alertes)}"
    
    contenu_mail += f"""

SEUILS CONFIGURÉS:
CPU > {SEUILS_ALERTE['CPU_MAX']}% | RAM > {SEUILS_ALERTE['RAM_MAX']}% | DISK > {SEUILS_ALERTE['DISK_MAX']}%

ACTIONS IMMÉDIATES:
1. Vérifier les processus consommateurs
2. Libérer l'espace disque si nécessaire  
3. Redémarrer les services problématiques
4. Surveiller l'évolution dans les prochaines minutes

---
Monitoring PSMM - Intervalle mail: {CONFIG_MAIL['intervalle_min_minutes']}min
"""
    
    # Simulation d'envoi
    print("="*50)
    print(f"À: {CONFIG_MAIL['destinataire']}")
    print(f"Sujet: [URGENT] Alerte système - {len(alertes_globales)} serveur(s)")
    print("="*50)
    print(contenu_mail)
    print("="*50)
    
    # Enregistrer l'envoi
    enregistrer_envoi_mail()
    
    # Logger l'envoi
    message_log = f"Mail alerte envoyé - {len(alertes_globales)} serveur(s) en dépassement"
    logger_action_mail(message_log, "SENT")
    
    return True

def logger_action_mail(message, status):
    """
    Logger les actions de mail en base de données
    """
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    date_action = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    commande_log = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO ftp_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source) VALUES ('{date_action}', 'MAIL_THROTTLING', '127.0.0.1', '{status}', '{message}', 'MONITORING');\""
    
    ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_log, mot_de_passe_sudo)

def afficher_statistiques_throttling():
    """
    Afficher les statistiques des mails envoyés/supprimés
    """
    print(f"\n📊 STATISTIQUES THROTTLING:")
    
    # Lire les stats du fichier
    if os.path.exists(FICHIER_TRACKING_MAIL):
        try:
            with open(FICHIER_TRACKING_MAIL, 'r') as f:
                data = json.load(f)
            
            print(f"   Mails envoyés au total: {data.get('nombre_envois_total', 0)}")
            print(f"   Dernier envoi: {data.get('dernier_envoi', 'Jamais')}")
            print(f"   Intervalle configuré: {CONFIG_MAIL['intervalle_min_minutes']} minutes")
        except:
            print("   Aucune donnée disponible")
    else:
        print("   Aucun mail envoyé encore")

def main():
    """
    Fonction principale - Monitoring avec throttling des mails
    """
    print(f"Monitoring avec limitation mail - Job 13")
    print(f"Throttling: Max 1 mail par {CONFIG_MAIL['intervalle_min_minutes']} minutes")
    print("")
    
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139", 
        "datateam-mariadb": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    try:
        alertes_globales = {}
        
        # Monitoring rapide de chaque serveur
        for nom_serveur, ip_serveur in serveurs.items():
            metriques = collecter_metriques_rapide(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo)
            
            if metriques['alertes']:
                alertes_globales[nom_serveur] = metriques['alertes']
        
        # Gestion des alertes avec throttling
        if alertes_globales:
            print(f"\n⚠️ {len(alertes_globales)} serveur(s) en dépassement de seuils")
            mail_envoye = envoyer_alerte_mail_avec_throttling(alertes_globales)
        else:
            print(f"\n✅ Tous les serveurs dans les seuils normaux")
            mail_envoye = False
        
        # Statistiques
        afficher_statistiques_throttling()
        
        # Configuration cron
        print(f"\n📅 CRON CONFIGURATION:")
        print(f"*/5 * * * * /usr/bin/python3 /root/ssh_system_mail_throttled.py")
        
        print(f"\n" + "="*60)
        print(f"JOB 13 TERMINÉ")
        print(f"Alertes: {len(alertes_globales)} | Mail envoyé: {'Oui' if mail_envoye else 'Non'}")
        
    except Exception as e:
        print(f"❌ Erreur Job 13: {e}")

if __name__ == "__main__":
    main()
