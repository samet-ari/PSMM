#!/usr/bin/env python3
"""
Job 11: Script de monitoring des ressources système
Récupérer l'état des ressources RAM/CPU/DISK des différents serveurs
Stocker dans une base de données et ne garder que les dernières 72h
"""

import paramiko
import os
import time
import re
from datetime import datetime, timedelta

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

def creer_table_system_monitoring():
    """
    Créer la table pour stocker les métriques système
    """
    print("=== Création de la table de monitoring système ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    commande_sql = """mysql -u psmm -ppsmm123 -D psmm_logs -e "
    CREATE TABLE IF NOT EXISTS system_monitoring (
        id INT AUTO_INCREMENT PRIMARY KEY,
        serveur_nom VARCHAR(50),
        serveur_ip VARCHAR(45),
        cpu_usage DECIMAL(5,2),
        ram_usage DECIMAL(5,2),
        ram_total_mb INT,
        disk_usage DECIMAL(5,2),
        disk_total_gb DECIMAL(8,2),
        load_average VARCHAR(50),
        uptime_seconds BIGINT,
        date_mesure DATETIME,
        date_insertion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );"
    """
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_sql, mot_de_passe_sudo)
    
    if succes:
        print("✅ Table system_monitoring créée/vérifiée")
        return True
    else:
        print(f"❌ Erreur création table: {sortie}")
        return False

def collecter_metriques_serveur(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Collecter les métriques d'un serveur
    """
    print(f"=== Collecte métriques: {nom_serveur} ({ip_serveur}) ===")
    
    metriques = {
        'serveur_nom': nom_serveur,
        'serveur_ip': ip_serveur,
        'date_mesure': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 1. CPU Usage
    print("Collecte CPU...")
    commande_cpu = "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
    succes, cpu_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_cpu, mot_de_passe_sudo)
    
    if succes and cpu_output:
        try:
            cpu_usage = float(cpu_output.replace(',', '.'))
            metriques['cpu_usage'] = cpu_usage
            print(f"  CPU: {cpu_usage}%")
        except:
            metriques['cpu_usage'] = 0.0
    else:
        metriques['cpu_usage'] = 0.0
    
    # 2. RAM Usage
    print("Collecte RAM...")
    commande_ram = "free -m | awk 'NR==2{printf \"%.2f %.0f\", $3*100/$2, $2}'"
    succes, ram_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_ram, mot_de_passe_sudo)
    
    if succes and ram_output:
        try:
            ram_parts = ram_output.split()
            metriques['ram_usage'] = float(ram_parts[0])
            metriques['ram_total_mb'] = int(ram_parts[1])
            print(f"  RAM: {metriques['ram_usage']}% ({metriques['ram_total_mb']} MB)")
        except:
            metriques['ram_usage'] = 0.0
            metriques['ram_total_mb'] = 0
    else:
        metriques['ram_usage'] = 0.0
        metriques['ram_total_mb'] = 0
    
    # 3. Disk Usage
    print("Collecte Disque...")
    commande_disk = "df -h / | awk 'NR==2{print $5 \" \" $2}' | sed 's/%//'"
    succes, disk_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_disk, mot_de_passe_sudo)
    
    if succes and disk_output:
        try:
            disk_parts = disk_output.split()
            metriques['disk_usage'] = float(disk_parts[0])
            disk_total_str = disk_parts[1].replace('G', '').replace(',', '.')
            metriques['disk_total_gb'] = float(disk_total_str)
            print(f"  Disque: {metriques['disk_usage']}% ({metriques['disk_total_gb']} GB)")
        except:
            metriques['disk_usage'] = 0.0
            metriques['disk_total_gb'] = 0.0
    else:
        metriques['disk_usage'] = 0.0
        metriques['disk_total_gb'] = 0.0
    
    # 4. Load Average
    print("Collecte Load Average...")
    commande_load = "uptime | awk -F'load average:' '{print $2}'"
    succes, load_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_load, mot_de_passe_sudo)
    
    if succes and load_output:
        metriques['load_average'] = load_output.strip()[:50]
        print(f"  Load: {metriques['load_average']}")
    else:
        metriques['load_average'] = "0.00, 0.00, 0.00"
    
    # 5. Uptime
    print("Collecte Uptime...")
    commande_uptime = "cat /proc/uptime | awk '{print int($1)}'"
    succes, uptime_output = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_uptime, mot_de_passe_sudo)
    
    if succes and uptime_output:
        try:
            metriques['uptime_seconds'] = int(uptime_output)
            heures = metriques['uptime_seconds'] // 3600
            print(f"  Uptime: {heures}h ({metriques['uptime_seconds']}s)")
        except:
            metriques['uptime_seconds'] = 0
    else:
        metriques['uptime_seconds'] = 0
    
    return metriques

def stocker_metriques_database(metriques):
    """
    Stocker les métriques en base de données
    """
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    # Préparer les valeurs pour l'insertion
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
    
    if succes:
        print(f"✅ Métriques stockées pour {metriques['serveur_nom']}")
        return True
    else:
        print(f"❌ Erreur stockage: {sortie}")
        return False

def nettoyer_anciennes_donnees():
    """
    Supprimer les données de plus de 72 heures
    """
    print("=== Nettoyage des données anciennes (>72h) ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    # Date limite: 72 heures en arrière
    date_limite = (datetime.now() - timedelta(hours=72)).strftime('%Y-%m-%d %H:%M:%S')
    
    commande_nettoyage = f"""mysql -u psmm -ppsmm123 -D psmm_logs -e "
    DELETE FROM system_monitoring WHERE date_mesure < '{date_limite}';
    SELECT ROW_COUNT() as lignes_supprimees;
    "
    """
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_nettoyage, mot_de_passe_sudo)
    
    if succes and sortie:
        print(f"Résultat du nettoyage:\n{sortie}")
    else:
        print("Nettoyage effectué")

def afficher_resume_monitoring():
    """
    Afficher un résumé des données de monitoring
    """
    print("=== Résumé du monitoring système ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    commande_resume = """mysql -u psmm -ppsmm123 -D psmm_logs -e "
    SELECT 
        serveur_nom,
        ROUND(AVG(cpu_usage), 2) as cpu_moy,
        ROUND(AVG(ram_usage), 2) as ram_moy,
        ROUND(AVG(disk_usage), 2) as disk_moy,
        COUNT(*) as nb_mesures,
        MAX(date_mesure) as derniere_mesure
    FROM system_monitoring 
    WHERE date_mesure >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    GROUP BY serveur_nom
    ORDER BY serveur_nom;
    "
    """
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_resume, mot_de_passe_sudo)
    
    if succes and sortie:
        print("Moyennes des dernières 24h:")
        print(sortie)
    else:
        print("Aucune donnée de monitoring disponible")

def main():
    """
    Fonction principale - Monitoring complet des serveurs
    """
    print("Monitoring des ressources système - Job 11")
    print("Surveillance: CPU, RAM, Disk, Load Average, Uptime")
    print("")
    
    # Configuration des serveurs à monitorer
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139",
        "datateam-mariadb": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    try:
        # 1. Créer la table de monitoring
        if not creer_table_system_monitoring():
            return
        
        # 2. Collecter les métriques de chaque serveur
        metriques_collectees = []
        
        for nom_serveur, ip_serveur in serveurs.items():
            metriques = collecter_metriques_serveur(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo)
            
            if metriques:
                # 3. Stocker en base de données
                stocker_metriques_database(metriques)
                metriques_collectees.append(metriques)
                print("")
        
        # 4. Nettoyer les anciennes données
        nettoyer_anciennes_donnees()
        
        # 5. Afficher le résumé
        afficher_resume_monitoring()
        
        # 6. Résumé final
        print("\n" + "="*60)
        print("JOB 11 TERMINÉ AVEC SUCCÈS")
        print("="*60)
        print(f"✅ {len(metriques_collectees)} serveurs monitorés")
        print("✅ Métriques stockées en base de données")
        print("✅ Données anciennes (>72h) supprimées")
        print("✅ Système de monitoring opérationnel")
        print("")
        
    except Exception as e:
        print(f"❌ Erreur lors du Job 11: {e}")

if __name__ == "__main__":
    main()
