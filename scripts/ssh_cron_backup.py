#!/usr/bin/env python3
"""
Job 10: Script de sauvegarde automatique de la base de données
Sauvegarde locale horodatée avec conservation de 7 dernières sauvegardes
Planification toutes les 3 heures
"""

import paramiko
import os
import time
import glob
from datetime import datetime

def ssh_connect_and_run_sudo(nom_hote, nom_utilisateur, commande, mot_de_passe_sudo, chemin_cle=None):
    """
    Se connecter via SSH et exécuter une commande avec sudo
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
            timeout=15
        )
        
        commande_complete = f"echo '{mot_de_passe_sudo}' | sudo -S {commande} 2>/dev/null"
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=30)
        
        time.sleep(2)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        erreur = stderr.read().decode('utf-8', errors='ignore').strip()
        client.close()
        
        return True, sortie, erreur
        
    except Exception as e:
        return False, "", str(e)

def creer_repertoire_sauvegarde():
    """
    Créer le répertoire de sauvegarde local sur le serveur MariaDB
    """
    print("=== Création du répertoire de sauvegarde ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    commandes_preparation = [
        ("mkdir -p /var/backups/psmm", "Création du répertoire backup"),
        ("chown datateam-monitor:datateam-monitor /var/backups/psmm", "Attribution des permissions"),
        ("chmod 750 /var/backups/psmm", "Sécurisation du répertoire")
    ]
    
    for commande, description in commandes_preparation:
        print(f"{description}...")
        succes, sortie, erreur = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes:
            print(f"  ✅ {description} réussie")
        else:
            print(f"  ⚠️ {description}: {erreur}")
    
    return True

def effectuer_sauvegarde_database():
    """
    Effectuer la sauvegarde de la base de données psmm_logs
    """
    print("=== Sauvegarde de la base de données ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    # Horodatage pour le nom de fichier
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nom_fichier = f"psmm_logs_backup_{timestamp}.sql"
    chemin_backup = f"/var/backups/psmm/{nom_fichier}"
    
    print(f"Fichier de sauvegarde: {nom_fichier}")
    
    # Commande mysqldump pour sauvegarder la base
    commande_backup = f"mysqldump -u psmm -ppsmm123 --single-transaction --routines --triggers --add-drop-database --databases psmm_logs > {chemin_backup}"
    
    print("Exécution de mysqldump...")
    succes, sortie, erreur = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_backup, mot_de_passe_sudo)
    
    if succes:
        # Vérifier que le fichier a été créé
        commande_verification = f"ls -lh {chemin_backup}"
        succes_verif, sortie_verif, _ = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_verification, mot_de_passe_sudo)
        
        if succes_verif and sortie_verif:
            print(f"✅ Sauvegarde créée avec succès:")
            print(f"   {sortie_verif}")
            
            # Compresser la sauvegarde
            commande_compression = f"gzip {chemin_backup}"
            succes_zip, _, _ = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_compression, mot_de_passe_sudo)
            
            if succes_zip:
                print(f"✅ Sauvegarde compressée: {nom_fichier}.gz")
                return f"{nom_fichier}.gz"
            else:
                return nom_fichier
        else:
            print(f"❌ Erreur lors de la vérification du fichier de sauvegarde")
            return None
    else:
        print(f"❌ Erreur lors de la sauvegarde: {erreur}")
        return None

def nettoyer_anciennes_sauvegardes():
    """
    Conserver seulement les 7 dernières sauvegardes
    """
    print("=== Nettoyage des anciennes sauvegardes ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    # Lister tous les fichiers de sauvegarde triés par date
    commande_liste = "ls -1t /var/backups/psmm/psmm_logs_backup_*.sql.gz 2>/dev/null | head -20"
    succes, liste_fichiers, _ = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_liste, mot_de_passe_sudo)
    
    if succes and liste_fichiers:
        fichiers = liste_fichiers.strip().split('\n')
        print(f"Nombre de sauvegardes trouvées: {len(fichiers)}")
        
        if len(fichiers) > 7:
            # Supprimer les sauvegardes au-delà des 7 plus récentes
            fichiers_a_supprimer = fichiers[7:]
            print(f"Suppression de {len(fichiers_a_supprimer)} anciennes sauvegardes:")
            
            for fichier in fichiers_a_supprimer:
                if fichier.strip():
                    commande_suppression = f"rm -f {fichier.strip()}"
                    succes_sup, _, _ = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_suppression, mot_de_passe_sudo)
                    
                    if succes_sup:
                        nom_fichier = os.path.basename(fichier.strip())
                        print(f"  ✅ Supprimé: {nom_fichier}")
                    else:
                        print(f"  ❌ Erreur suppression: {fichier}")
        else:
            print("✅ Nombre de sauvegardes dans la limite (≤7)")
    else:
        print("ℹ️ Aucune sauvegarde existante trouvée")
    
    return True

def afficher_statistiques_sauvegardes():
    """
    Afficher les statistiques des sauvegardes
    """
    print("=== Statistiques des sauvegardes ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    commandes_stats = [
        ("ls -lht /var/backups/psmm/", "Liste des sauvegardes"),
        ("du -sh /var/backups/psmm/", "Espace disque utilisé"),
        ("find /var/backups/psmm/ -name '*.gz' | wc -l", "Nombre de sauvegardes")
    ]
    
    for commande, description in commandes_stats:
        print(f"\n--- {description} ---")
        succes, sortie, _ = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes and sortie:
            print(sortie)
        else:
            print("Aucun résultat")

def tester_restauration_sauvegarde():
    """
    Tester qu'une sauvegarde peut être restaurée (test rapide)
    """
    print("=== Test de validité de la sauvegarde ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    # Trouver la sauvegarde la plus récente
    commande_derniere = "ls -1t /var/backups/psmm/psmm_logs_backup_*.sql.gz 2>/dev/null | head -1"
    succes, derniere_sauvegarde, _ = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_derniere, mot_de_passe_sudo)
    
    if succes and derniere_sauvegarde:
        fichier_backup = derniere_sauvegarde.strip()
        print(f"Test de la sauvegarde: {os.path.basename(fichier_backup)}")
        
        # Tester l'intégrité du fichier compressé
        commande_test = f"zcat {fichier_backup} | head -20 | grep -i 'CREATE DATABASE'"
        succes_test, sortie_test, _ = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_test, mot_de_passe_sudo)
        
        if succes_test and 'CREATE DATABASE' in sortie_test:
            print("✅ Sauvegarde valide - Structure SQL détectée")
        else:
            print("⚠️ Avertissement - Structure SQL non détectée")
    else:
        print("❌ Aucune sauvegarde trouvée pour le test")

def configurer_cron_job():
    """
    Configurer la tâche cron pour exécuter la sauvegarde toutes les 3 heures
    """
    print("=== Configuration de la tâche cron ===")
    
    chemin_script = "/root/ssh_cron_backup.py"
    
    # Ligne cron pour exécution toutes les 3 heures
    ligne_cron = f"0 */3 * * * /usr/bin/python3 {chemin_script} >> /var/log/psmm_backup.log 2>&1"
    
    print("Tâche cron à ajouter:")
    print(f"  {ligne_cron}")
    print("\nPour activer la sauvegarde automatique:")
    print(f"  1. crontab -e")
    print(f"  2. Ajouter la ligne: {ligne_cron}")
    print(f"  3. Sauvegarder et quitter")
    
    # Créer un fichier d'aide pour la configuration cron
    aide_cron = f"""
# Configuration automatique de sauvegarde PSMM
# Ajoutez cette ligne à votre crontab (crontab -e):

{ligne_cron}

# Explication:
# 0 */3 * * * = Toutes les 3 heures à la minute 0
# /usr/bin/python3 {chemin_script} = Script de sauvegarde
# >> /var/log/psmm_backup.log 2>&1 = Log des exécutions

# Pour vérifier les tâches cron actives:
# crontab -l

# Pour voir les logs de sauvegarde:
# tail -f /var/log/psmm_backup.log
"""
    
    with open("/root/cron_backup_help.txt", "w") as f:
        f.write(aide_cron)
    
    print(f"\n✅ Aide sauvegardée dans: /root/cron_backup_help.txt")

def main():
    """
    Fonction principale - Sauvegarde automatique avec rotation
    """
    print("Sauvegarde automatique de la base de données PSMM")
    print("Système: Horodatage + Conservation de 7 sauvegardes")
    print("")
    
    try:
        # 1. Préparer l'environnement de sauvegarde
        creer_repertoire_sauvegarde()
        
        # 2. Effectuer la sauvegarde
        fichier_backup = effectuer_sauvegarde_database()
        
        if fichier_backup:
            # 3. Nettoyer les anciennes sauvegardes
            nettoyer_anciennes_sauvegardes()
            
            # 4. Afficher les statistiques
            afficher_statistiques_sauvegardes()
            
            # 5. Tester la validité de la sauvegarde
            tester_restauration_sauvegarde()
            
            # 6. Configurer cron (information)
            configurer_cron_job()
            
            # 7. Résumé final
            print("\n" + "="*60)
            print("JOB 10 TERMINÉ AVEC SUCCÈS")
            print("="*60)
            print(f"✅ Sauvegarde créée: {fichier_backup}")
            print("✅ Rotation des sauvegardes appliquée")
            print("✅ Système de sauvegarde opérationnel")
            print("✅ Configuration cron préparée")
            print("")
            print("📅 Planification recommandée: Toutes les 3 heures")
            
        else:
            print("❌ Échec de la sauvegarde")
            
    except Exception as e:
        print(f"❌ Erreur lors du Job 10: {e}")

if __name__ == "__main__":
    main()
