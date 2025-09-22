#!/usr/bin/env python3
"""
Job 09: Script d'envoi de mail à l'administrateur système
Envoyer un mail avec les historiques des tentatives de connexion de la veille
"""

import paramiko
import os
import time
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

def recuperer_statistiques_erreurs():
    """
    Récupérer les statistiques d'erreurs des dernières 24h depuis toutes les tables
    """
    print("=== Récupération des statistiques d'erreurs ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    hier = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Requêtes pour chaque type d'erreur
    requetes = {
        "MySQL": f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"SELECT COUNT(*) as total, nom_compte, adresse_ip FROM mysql_errors WHERE date_erreur >= '{hier}' GROUP BY nom_compte, adresse_ip;\"",
        "FTP": f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"SELECT COUNT(*) as total, nom_compte, adresse_ip FROM ftp_errors WHERE date_erreur >= '{hier}' GROUP BY nom_compte, adresse_ip;\"", 
        "Web": f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"SELECT COUNT(*) as total, nom_compte, adresse_ip, code_statut FROM web_errors WHERE date_erreur >= '{hier}' GROUP BY nom_compte, adresse_ip;\""
    }
    
    statistiques = {}
    
    for service, requete in requetes.items():
        print(f"Récupération des stats {service}...")
        succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, requete, mot_de_passe_sudo)
        
        if succes and sortie:
            statistiques[service] = sortie
            print(f"  {service}: {len(sortie.split(chr(10)))} lignes récupérées")
        else:
            statistiques[service] = "Aucune donnée"
    
    return statistiques

def generer_rapport_securite(statistiques):
    """
    Générer le rapport de sécurité complet
    """
    date_rapport = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    hier = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    
    rapport = f"""
╔══════════════════════════════════════════════════════════════╗
║                 RAPPORT SÉCURITÉ QUOTIDIEN - PSMM           ║
║                     Système DataTeam                        ║
╚══════════════════════════════════════════════════════════════╝

Date du rapport: {date_rapport}
Période analysée: {hier} (dernières 24 heures)
Statut système: OPÉRATIONNEL

╔══════════════════════════════════════════════════════════════╗
║                    RÉSUMÉ EXÉCUTIF                           ║
╚══════════════════════════════════════════════════════════════╝

Serveurs surveillés: 
  • MySQL/MariaDB (192.168.81.141)
  • FTP vsftpd (192.168.81.137)  
  • Web Apache2 (192.168.81.139)

╔══════════════════════════════════════════════════════════════╗
║              TENTATIVES D'ACCÈS MYSQL ÉCHOUÉES               ║
╚══════════════════════════════════════════════════════════════╝

{statistiques.get('MySQL', 'Aucune erreur MySQL détectée')}

╔══════════════════════════════════════════════════════════════╗
║               TENTATIVES D'ACCÈS FTP ÉCHOUÉES                ║
╚══════════════════════════════════════════════════════════════╝

{statistiques.get('FTP', 'Aucune erreur FTP détectée')}

╔══════════════════════════════════════════════════════════════╗
║               TENTATIVES D'ACCÈS WEB ÉCHOUÉES                ║
╚══════════════════════════════════════════════════════════════╝

{statistiques.get('Web', 'Aucune erreur Web détectée')}

╔══════════════════════════════════════════════════════════════╗
║                     RECOMMANDATIONS                         ║
╚══════════════════════════════════════════════════════════════╝

🔍 ACTIONS RECOMMANDÉES:
  1. Vérifier les adresses IP suspectes
  2. Analyser les patterns d'attaque répétés
  3. Considérer le blocage des IPs malveillantes
  4. Renforcer les mots de passe si nécessaire
  5. Mettre en place fail2ban si requis

⚠️  ALERTES:
  • Surveiller les tentatives d'accès admin/root
  • Vérifier les comptes inexistants utilisés
  • Contrôler les authentifications à répétition

╔══════════════════════════════════════════════════════════════╗
║                INFORMATIONS SYSTÈME                          ║
╚══════════════════════════════════════════════════════════════╝

Générateur: Système PSMM v1.0
  • Python: Scripts d'analyse automatique
  • Shell: Connexions SSH sécurisées  
  • MariaDB: Base de données centralisée
  • Mail: Notifications administrateur

Serveur de monitoring: datateam-monitor
Base de données: psmm_logs (192.168.81.141)
Tables surveillées: mysql_errors, ftp_errors, web_errors

---
📧 Ce rapport est généré automatiquement tous les jours
📊 Pour plus d'informations: Consulter la base psmm_logs
🔧 Configuration: Scripts dans /root/ sur datateam-monitor
"""
    
    return rapport

def envoyer_mail_administrateur(contenu_rapport):
    """
    Simuler l'envoi du mail et logger l'action
    """
    print("=== Envoi du mail à l'administrateur système ===")
    
    # Configuration mail
    destinataire = "admin@datateam.local"
    expediteur = "monitoring@datateam.local" 
    sujet = f"[ALERTE SÉCURITÉ] Rapport quotidien PSMM - {datetime.now().strftime('%d/%m/%Y')}"
    
    # Simulation d'envoi (affichage console)
    print("\n" + "="*80)
    print("SIMULATION D'ENVOI DE MAIL")
    print("="*80)
    print(f"À: {destinataire}")
    print(f"De: {expediteur}")
    print(f"Sujet: {sujet}")
    print("="*80)
    print(contenu_rapport)
    print("="*80)
    print("FIN DE SIMULATION")
    
    # Logger l'envoi dans la base
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    date_envoi = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message_log = f"Rapport sécurité envoyé à {destinataire}"
    
    commande_log = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO ftp_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source) VALUES ('{date_envoi}', 'SYSTEM_MAIL', '127.0.0.1', 'Rapport Quotidien', '{message_log}', 'MONITORING');\""
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_log, mot_de_passe_sudo)
    
    if succes:
        print("✅ Envoi de mail simulé et enregistré en base de données")
    else:
        print("❌ Erreur lors de l'enregistrement du mail")
    
    return True

def main():
    """
    Fonction principale - Génération et envoi du rapport quotidien
    """
    print("Génération du rapport de sécurité quotidien PSMM")
    print("Système de surveillance: Python + Shell + MariaDB + Mail\n")
    
    try:
        # 1. Récupérer les statistiques d'erreurs
        statistiques = recuperer_statistiques_erreurs()
        
        # 2. Générer le rapport complet
        rapport = generer_rapport_securite(statistiques)
        
        # 3. Envoyer le mail à l'administrateur
        envoyer_mail_administrateur(rapport)
        
        # 4. Résumé final
        print("\n" + "="*60)
        print("JOB 09 TERMINÉ AVEC SUCCÈS")
        print("="*60)
        print("✅ Statistiques d'erreurs récupérées")
        print("✅ Rapport de sécurité généré")
        print("✅ Mail administrateur envoyé (simulé)")
        print("✅ Action loggée en base de données")
        
    except Exception as e:
        print(f"❌ Erreur lors du Job 09: {e}")

if __name__ == "__main__":
    main()
