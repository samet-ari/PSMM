#!/usr/bin/env python3
"""
Job 05: Script de connexion SSH pour vérifier l'accès MariaDB/MySQL
Se connecter au serveur MariaDB et vérifier l'accès à la base de données
"""

import paramiko
import sys
import os
import time

def ssh_connect_and_run_sudo(nom_hote, nom_utilisateur, commande, mot_de_passe_sudo, chemin_cle=None):
    """
    Se connecter via SSH et exécuter une commande avec sudo
    """
    try:
        print(f"Connexion au serveur {nom_hote}...")
        
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
        
        print(f"Connexion SSH réussie à {nom_hote}")
        
        # Exécuter la commande avec sudo
        commande_complete = f"echo '{mot_de_passe_sudo}' | sudo -S {commande} 2>/dev/null"
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=15)
        
        time.sleep(1)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        erreur = stderr.read().decode('utf-8', errors='ignore').strip()
        
        # Nettoyer la sortie
        if sortie:
            lines = sortie.split('\n')
            sortie_propre = []
            for line in lines:
                line = line.strip()
                if line and not any(x in line.lower() for x in ['[sudo]', 'password for']):
                    sortie_propre.append(line)
            sortie = '\n'.join(sortie_propre)
        
        client.close()
        
        return True, sortie, erreur
        
    except Exception as e:
        print(f"Erreur de connexion SSH: {e}")
        return False, "", str(e)

def verifier_mariadb_service(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Vérifier que le service MariaDB est installé et actif
    """
    print("\n=== Vérification du service MariaDB ===")
    
    commandes_verification = [
        ("systemctl status mariadb --no-pager", "État du service MariaDB"),
        ("systemctl status mysql --no-pager", "État du service MySQL (si MariaDB non trouvé)"),
        ("ps aux | grep mysql", "Processus MySQL/MariaDB en cours"),
        ("netstat -tlnp | grep 3306", "Port 3306 (MySQL) ouvert"),
        ("which mysql", "Client MySQL installé")
    ]
    
    for commande, description in commandes_verification:
        print(f"\n--- {description} ---")
        succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes and sortie:
            print(f"Résultat:\n{sortie}")
        elif erreur:
            print(f"Erreur: {erreur}")
        else:
            print("Aucun résultat")
    
    return True

def tester_connexion_mysql(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Tenter une connexion MySQL basique
    """
    print("\n=== Test de connexion MySQL ===")
    
    # Commandes de test MySQL
    commandes_mysql = [
        ("mysql --version", "Version du client MySQL"),
        ("mysql -u root -e 'SELECT VERSION();'", "Test connexion root sans mot de passe"),
        ("mysql -u root -p123 -e 'SHOW DATABASES;'", "Test avec mot de passe 123"),
        ("mysql -u root -e 'SHOW DATABASES;'", "Liste des bases de données"),
        ("mysql -u root -e 'SELECT User, Host FROM mysql.user;'", "Utilisateurs MySQL")
    ]
    
    for commande, description in commandes_mysql:
        print(f"\n--- {description} ---")
        succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes and sortie:
            print(f"Résultat:\n{sortie}")
        elif erreur:
            print(f"Information: {erreur}")
        
        # Pause entre les commandes
        time.sleep(1)
    
    return True

def creer_utilisateur_test(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Créer un utilisateur de test pour le projet PSMM
    """
    print("\n=== Création utilisateur de test ===")
    
    commandes_creation = [
        ("mysql -u root -e \"CREATE USER IF NOT EXISTS 'psmm'@'localhost' IDENTIFIED BY 'psmm123';\"", 
         "Créer utilisateur psmm"),
        ("mysql -u root -e \"GRANT ALL PRIVILEGES ON *.* TO 'psmm'@'localhost' WITH GRANT OPTION;\"", 
         "Donner privilèges à psmm"),
        ("mysql -u root -e \"CREATE DATABASE IF NOT EXISTS psmm_logs;\"", 
         "Créer base de données psmm_logs"),
        ("mysql -u root -e \"FLUSH PRIVILEGES;\"", 
         "Actualiser les privilèges"),
        ("mysql -u psmm -ppsmm123 -e 'SHOW DATABASES;'", 
         "Tester connexion utilisateur psmm")
    ]
    
    for commande, description in commandes_creation:
        print(f"\n--- {description} ---")
        succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes and sortie:
            print(f"Résultat:\n{sortie}")
        elif erreur and "error" not in erreur.lower():
            print(f"Information: {erreur}")
        
        time.sleep(1)
    
    return True

def main():
    """
    Fonction principale - Vérifier l'accès à MariaDB/MySQL
    """
    print("Début de la vérification d'accès MariaDB/MySQL")
    
    # Configuration
    ip_serveur_bd = "192.168.81.141"  # Serveur MariaDB
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    # Vérifier la clé SSH
    chemin_cle = os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.exists(chemin_cle):
        print(f"Erreur: Clé SSH introuvable: {chemin_cle}")
        return
    
    print(f"Serveur cible: {ip_serveur_bd}")
    print(f"Utilisateur SSH: {nom_utilisateur}")
    
    try:
        # 1. Vérifier le service MariaDB
        verifier_mariadb_service(ip_serveur_bd, nom_utilisateur, mot_de_passe_sudo)
        
        # 2. Tester les connexions MySQL
        tester_connexion_mysql(ip_serveur_bd, nom_utilisateur, mot_de_passe_sudo)
        
        # 3. Créer utilisateur et base de test
        creer_utilisateur_test(ip_serveur_bd, nom_utilisateur, mot_de_passe_sudo)
        
        print("\n" + "="*50)
        print("Vérification MariaDB terminée")
        print("Si aucune erreur critique, l'accès MySQL est fonctionnel")
        
    except Exception as e:
        print(f"Erreur générale: {e}")

if __name__ == "__main__":
    main()
