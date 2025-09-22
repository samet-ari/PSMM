#!/usr/bin/env python3
"""
Job 04: Script de connexion SSH avec sudo
En utilisant le script précédent, ajouter l'exécution de commandes shell avec sudo
"""

import paramiko
import sys
import os
import time

def ssh_connect_and_run_sudo(nom_hote, nom_utilisateur, commande, mot_de_passe_sudo, chemin_cle=None):
    """
    Se connecter via SSH et exécuter une commande avec privilèges sudo
    """
    try:
        print(f"🔌 Connexion au serveur {nom_hote}...")
        
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
        
        print(f"✅ Connexion réussie à {nom_hote}")
        
        # Utiliser echo avec pipe pour envoyer le mot de passe sudo
        commande_complete = f"echo '{mot_de_passe_sudo}' | sudo -S {commande} 2>/dev/null"
        print(f"🔧 Exécution: sudo {commande}")
        
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=15)
        
        # Attendre un peu pour l'exécution
        time.sleep(1)
        
        # Lire les résultats
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        erreur = stderr.read().decode('utf-8', errors='ignore').strip()
        
        # Nettoyer la sortie des messages sudo
        if sortie:
            lines = sortie.split('\n')
            sortie_propre = []
            for line in lines:
                line = line.strip()
                if line and not any(x in line.lower() for x in ['[sudo]', 'password for', 'sorry']):
                    sortie_propre.append(line)
            sortie = '\n'.join(sortie_propre)
        
        if sortie:
            print(f"📊 Résultat de la commande:\n{sortie}")
        
        if erreur and not any(x in erreur.lower() for x in ['password', 'sudo']):
            print(f"⚠️ Erreur: {erreur}")
            
        client.close()
        print(f"🔌 Connexion fermée à {nom_hote}\n")
        
        return True, sortie, erreur
        
    except Exception as e:
        print(f"❌ Erreur de connexion à {nom_hote}: {e}\n")
        return False, "", str(e)

def ssh_connect_and_run_normal(nom_hote, nom_utilisateur, commande, chemin_cle=None):
    """
    Se connecter via SSH et exécuter une commande normale (sans sudo)
    Réutilise le code du Job 03
    """
    try:
        print(f"🔌 Connexion au serveur {nom_hote}...")
        
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
        
        print(f"✅ Connexion réussie à {nom_hote}")
        print(f"🔧 Exécution de la commande: {commande}")
        
        stdin, stdout, stderr = client.exec_command(commande)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        erreur = stderr.read().decode('utf-8', errors='ignore').strip()
        
        if sortie:
            print(f"📊 Résultat de la commande:\n{sortie}")
        
        if erreur:
            print(f"⚠️ Erreur: {erreur}")
            
        client.close()
        print(f"🔌 Connexion fermée à {nom_hote}\n")
        
        return True, sortie, erreur
        
    except Exception as e:
        print(f"❌ Erreur de connexion à {nom_hote}: {e}\n")
        return False, "", str(e)

def main():
    """
    Fonction principale - Test des commandes normales et sudo
    """
    print("🚀 Début du test SSH avec commandes sudo...\n")
    
    # Configuration des serveurs
    serveurs = {
        "Serveur FTP": "192.168.81.137",
        "Serveur Web": "192.168.81.139",
        "Serveur BD": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"  # Mot de passe sudo défini
    
    # Commandes normales pour comparaison
    commandes_normales = [
        ("whoami", "Vérifier l'utilisateur actuel"),
        ("hostname", "Nom de la machine"),
        ("pwd", "Répertoire courant")
    ]
    
    # Commandes nécessitant sudo
    commandes_sudo = [
        ("whoami", "Vérifier les privilèges sudo"),
        ("systemctl status ssh --no-pager -l", "État du service SSH"),
        ("cat /var/log/auth.log | tail -3", "Dernières connexions"),
        ("ls -la /root", "Contenu du répertoire root"),
        ("cat /etc/shadow | head -2", "Fichier des mots de passe")
    ]
    
    # Vérifier la clé SSH
    chemin_cle = os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.exists(chemin_cle):
        print(f"❌ Clé SSH introuvable: {chemin_cle}")
        return
    
    print(f"🔑 Utilisation de la clé SSH: {chemin_cle}")
    print(f"👤 Nom d'utilisateur: {nom_utilisateur}")
    print(f"🔐 Mot de passe sudo: {mot_de_passe_sudo}\n")
    
    # Tester sur chaque serveur
    for nom_serveur, ip in serveurs.items():
        print(f"🎯 === Test sur {nom_serveur} ({ip}) ===")
        
        print("\n--- Commandes normales ---")
        for commande, description in commandes_normales:
            print(f"\n📋 Test: {description}")
            succes, sortie, erreur = ssh_connect_and_run_normal(ip, nom_utilisateur, commande)
            if not succes:
                print(f"❌ Échec de la commande normale sur {nom_serveur}")
                break
        
        print("\n--- Commandes sudo ---")
        for commande, description in commandes_sudo:
            print(f"\n🔐 Test: {description}")
            succes, sortie, erreur = ssh_connect_and_run_sudo(ip, nom_utilisateur, commande, mot_de_passe_sudo)
            if not succes:
                print(f"❌ Échec de la commande sudo sur {nom_serveur}")
                continue  # Continuer même en cas d'échec
                
        print("-" * 60)

    print("✅ Tests terminés!")

if __name__ == "__main__":
    main()
