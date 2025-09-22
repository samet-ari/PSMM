#!/usr/bin/env python3
"""
Job 12: Script de monitoring avec alertes par mail
Reprendre le script précédent en ajoutant l'envoi de mail si seuils dépassés:
- CPU > 70%, Disk > 90%, RAM > 80%
Les valeurs doivent être modifiables facilement dans le script
Prévoir en tâche planifiée toutes les 5 min
"""

import paramiko
import os
import time
import re
from datetime import datetime, timedelta

# ========== SEUILS D'ALERTE - MODIFIABLES ==========
SEUILS_ALERTE = {
    'CPU_MAX': 70.0,      # Seuil CPU en %
    'RAM_MAX': 80.0,      # Seuil RAM en %  
    'DISK_MAX': 90.0,     # Seuil Disk en %
    'LOAD_MAX': 5.0       # Seuil Load Average
}

# Configuration mail
CONFIG_MAIL = {
    'destinataire': 'admin@datateam.local',
    'expediteur': 'monitoring@datateam.local'
}
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

def collecter_metriques_avec_alertes(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Collecter les métriques et détecter les dépassements de seuils
    """
    print(f"Monitoring: {nom_serveur} ({ip_serveur})")
    
    metriques = {
        'serveur_nom': nom_serveur,
        'serveur_ip': ip_serveur,
        'date_mesure': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'alertes': []  # Liste des alertes déclenchées
    }
    
    # 1. CPU Usage
    commande_cpu = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
    succes, cpu_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_cpu, mot_de_passe_sudo)
    
    if succes and cpu_output:
        try:
            cpu_usage = float(cpu_output.replace(',', '.'))
            metriques['cpu_usage'] = cpu_usage
            
            # Vérification seuil CPU
            if cpu_usage > SEUILS_ALERTE['CPU_MAX']:
                alerte = f"🔴 CPU CRITIQUE: {cpu_usage}% > {SEUILS_ALERTE['CPU_MAX']}%"
                metriques['alertes'].append(alerte)
                print(f"  ⚠️ {alerte}")
            else:
                print(f"  ✅ CPU: {cpu_usage}% (OK)")
        except:
            metriques['cpu_usage'] = 0.0
    else:
        metriques['cpu_usage'] = 0.0
    
    # 2. RAM Usage  
    commande_ram = "free -m | awk 'NR==2{printf \"%.2f %.0f\", $3*100/$2, $2}'"
    succes, ram_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_ram, mot_de_passe_sudo)
    
    if succes and ram_output:
        try:
            ram_parts = ram_output.split()
            ram_usage = float(ram_parts[0])
            ram_total = int(ram_parts[1])
            metriques['ram_usage'] = ram_usage
            metriques['ram_total_mb'] = ram_total
            
            # Vérification seuil RAM
            if ram_usage > SEUILS_ALERTE['RAM_MAX']:
                alerte = f"🟠 RAM ÉLEVÉE: {ram_usage}% > {SEUILS_ALERTE['RAM_MAX']}% ({ram_total}MB)"
                metriques['alertes'].append(alerte)
                print(f"  ⚠️ {alerte}")
            else:
                print(f"  ✅ RAM: {ram_usage}% ({ram_total}MB) (OK)")
        except:
            metriques['ram_usage'] = 0.0
            metriques['ram_total_mb'] = 0
    else:
        metriques['ram_usage'] = 0.0
        metriques['ram_total_mb'] = 0
    
    # 3. Disk Usage
    commande_disk = "df -h / | awk 'NR==2{print $5 \" \" $2}' | sed 's/%//'"
    succes, disk_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_disk, mot_de_passe_sudo)
    
    if succes and disk_output:
        try:
            disk_parts = disk_output.split()
            disk_usage = float(disk_parts[0])
            disk_total_str = disk_parts[1].replace('G', '').replace(',', '.')
            disk_total = float(disk_total_str)
            metriques['disk_usage'] = disk_usage
            metriques['disk_total_gb'] = disk_total
            
            # Vérification seuil DISK
            if disk_usage > SEUILS_ALERTE['DISK_MAX']:
                alerte = f"🔴 DISQUE CRITIQUE: {disk_usage}% > {SEUILS_ALERTE['DISK_MAX']}% ({disk_total}GB)"
                metriques['alertes'].append(alerte)
                print(f"  ⚠️ {alerte}")
            else:
                print(f"  ✅ Disque: {disk_usage}% ({disk_total}GB) (OK)")
        except:
            metriques['disk_usage'] = 0.0
            metriques['disk_total_gb'] = 0.0
    else:
        metriques['disk_usage'] = 0.0
        metriques['disk_total_gb'] = 0.0
    
    # 4. Load Average
    commande_load = "uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1"
    succes, load_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_load, mot_de_passe_sudo)
    
    if succes and load_output:
        try:
            load_1min = float(load_output.strip())
            metriques['load_average'] = f"{load_1min}"
            
            # Vérification seuil LOAD
            if load_1min > SEUILS_ALERTE['LOAD_MAX']:
                alerte = f"🟡 LOAD ÉLEVÉ: {load_1min} > {SEUILS_ALERTE['LOAD_MAX']}"
                metriques['alertes'].append(alerte)
                print(f"  ⚠️ {alerte}")
            else:
                print(f"  ✅ Load: {load_1min} (OK)")
        except:
            metriques['load_average'] = "0.0"
    else:
        metriques['load_average'] = "0.0"
    
    # 5. Uptime (information seulement)
    commande_uptime = "cat /proc/uptime | awk '{print int($1)}'"
    succes, uptime_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_uptime, mot_de_passe_sudo)
    
    if succes and uptime_output:
        try:
            metriques['uptime_seconds'] = int(uptime_output)
            heures = metriques['uptime_seconds'] // 3600
            print(f"  ℹ️ Uptime: {heures}h")
        except:
            metriques['uptime_seconds'] = 0
    else:
        metriques['uptime_seconds'] = 0
    
    return metriques

def stocker_metriques_database(metriques):
    """
    Stocker les métriques en base de données (réutilise la table du Job 11)
    """
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    valeurs = (
        metriques['date_mesure'],
        metriques['serveur_nom'][:50],
        metriques['serveur_ip'][:45],
        metriques['cpu_usage'],
        metriques['ram_usage'],
        metriques['ram_total_mb'],
        metriques['disk_usage'],
        metriques['disk_total_gb'],
        metriques['load_average'][:50],
        metriques['uptime_seconds']
    )
    
    commande_insertion = f"""mysql -u psmm -ppsmm123 -D psmm_logs -e "
    INSERT INTO system_monitoring 
    (date_mesure, serveur_nom, serveur_ip, cpu_usage, ram_usage, ram_total_mb, disk_usage, disk_total_gb, load_average, uptime_seconds)
    VALUES ('{valeurs[0]}', '{valeurs[1]}', '{valeurs[2]}', {valeurs[3]}, {valeurs[4]}, {valeurs[5]}, {valeurs[6]}, {valeurs[7]}, '{valeurs[8]}', {valeurs[9]});
    "
    """
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_insertion, mot_de_passe_sudo)
    
    return succes

def envoyer_alerte_mail(alertes_globales):
    """
    Envoyer un mail d'alerte si des seuils sont dépassés
    """
    if not alertes_globales:
        return
    
    print(f"\n=== ENVOI D'ALERTE MAIL ===")
    
    # Construire le contenu du mail
    date_alerte = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    contenu_mail = f"""
🚨 ALERTE SYSTÈME DATATEAM - SEUILS DÉPASSÉS 🚨

Date: {date_alerte}
Nombre d'alertes: {len(alertes_globales)}

SEUILS CONFIGURÉS:
- CPU Maximum: {SEUILS_ALERTE['CPU_MAX']}%
- RAM Maximum: {SEUILS_ALERTE['RAM_MAX']}%  
- Disque Maximum: {SEUILS_ALERTE['DISK_MAX']}%
- Load Average Maximum: {SEUILS_ALERTE['LOAD_MAX']}

ALERTES DÉCLENCHÉES:
"""
    
    for serveur, alertes in alertes_globales.items():
        contenu_mail += f"\n📍 SERVEUR: {serveur}\n"
        for alerte in alertes:
            contenu_mail += f"   {alerte}\n"
    
    contenu_mail += f"""
ACTIONS RECOMMANDÉES:
1. Vérifier les processus consommateurs de ressources
2. Redémarrer les services si nécessaire  
3. Nettoyer les fichiers temporaires (disque plein)
4. Augmenter les ressources si le problème persiste

---
Système de monitoring PSMM - {date_alerte}
Serveur: datateam-monitor
Base de données: psmm_logs
"""
    
    # Simulation d'envoi mail
    print("SIMULATION ENVOI MAIL D'ALERTE:")
    print("="*60)
    print(f"À: {CONFIG_MAIL['destinataire']}")
    print(f"De: {CONFIG_MAIL['expediteur']}")
    print(f"Sujet: [ALERTE CRITIQUE] Seuils système dépassés - {datetime.now().strftime('%H:%M')}")
    print("="*60)
    print(contenu_mail)
    print("="*60)
    
    # Logger l'alerte
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    message_log = f"ALERTE: {len(alertes_globales)} serveur(s) en dépassement de seuils"
    date_envoi = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    commande_log = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO ftp_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source) VALUES ('{date_envoi}', 'SYSTEM_ALERT', '127.0.0.1', 'Alerte Seuils', '{message_log}', 'MONITORING');\""
    
    ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_log, mot_de_passe_sudo)
    
    print("✅ Alerte mail envoyée et loggée")

def main():
    """
    Fonction principale - Monitoring avec alertes automatiques
    """
    print("Monitoring système avec alertes - Job 12")
    print(f"Seuils: CPU>{SEUILS_ALERTE['CPU_MAX']}%, RAM>{SEUILS_ALERTE['RAM_MAX']}%, Disk>{SEUILS_ALERTE['DISK_MAX']}%")
    print("")
    
    # Serveurs à monitorer
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139", 
        "datateam-mariadb": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    try:
        alertes_globales = {}
        
        # Monitoring de chaque serveur
        for nom_serveur, ip_serveur in serveurs.items():
            metriques = collecter_metriques_avec_alertes(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo)
            
            # Stocker en base
            stocker_metriques_database(metriques)
            
            # Collecter les alertes
            if metriques['alertes']:
                alertes_globales[nom_serveur] = metriques['alertes']
            
            print("")
        
        # Envoyer mail d'alerte si nécessaire
        if alertes_globales:
            envoyer_alerte_mail(alertes_globales)
        else:
            print("✅ Tous les serveurs dans les seuils normaux")
        
        # Configuration cron
        print("\n" + "="*50)
        print("CONFIGURATION CRON RECOMMANDÉE:")
        print("*/5 * * * * /usr/bin/python3 /root/ssh_system_mail.py >> /var/log/psmm_monitoring.log 2>&1")
        print("(Toutes les 5 minutes)")
        
        print("\n" + "="*60)
        print("JOB 12 TERMINÉ")
        print(f"Alertes déclenchées: {len(alertes_globales)} serveur(s)")
        
    except Exception as e:
        print(f"❌ Erreur Job 12: {e}")

if __name__ == "__main__":
    main()
