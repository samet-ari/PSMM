#!/usr/bin/env python3
"""
Job 03: Script de connexion SSH
Connexion depuis la VM Monitor vers d'autres serveurs et exécution de commandes
"""

import paramiko
import sys
import os

def ssh_connect_and_run(nom_hote, nom_utilisateur, commande, chemin_cle=None):
    """
    Se connecter via SSH et exécuter une commande
    """
    try:
        print(f"🔌 Connexion au serveur {nom_hote}...")
        
        # Déterminer le chemin de la clé SSH
        if chemin_cle is None:
            chemin_cle = os.path.expanduser("~/.ssh/id_rsa")
        
        # Créer le client SSH
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Se connecter avec la clé SSH
        client.connect(
            hostname=nom_hote,
            username=nom_utilisateur,
            key_filename=chemin_cle
        )
        
        print(f"✅ Connexion à {nom_hote} réussie!")
        
        # Exécuter la commande
        print(f"🔧 Exécution de la commande: {commande}")
        stdin, stdout, stderr = client.exec_command(commande)
        
        # Récupérer les résultats
        sortie = stdout.read().decode().strip()
        erreur = stderr.read().decode().strip()
        
        if sortie:
            print(f"📊 Résultat de la commande:\n{sortie}")
        
        if erreur:
            print(f"⚠️ Message d'erreur:\n{erreur}")
            
        # Fermer la connexion
        client.close()
        print(f"🔌 Connexion à {nom_hote} fermée\n")
        
        return True, sortie, erreur
        
    except Exception as e:
        print(f"❌ Erreur de connexion à {nom_hote}: {e}\n")
        return False, "", str(e)

def main():
    """
    Fonction principale - Se connecter aux VMs et exécuter les commandes de test
    """
    print("🚀 Début du test de connexion SSH...\n")
    
    # Adresses IP des VMs - MODIFIER AVEC VOS VRAIES IPs!
    serveurs = {
        "Serveur FTP": "192.168.81.137",
        "Serveur Web": "192.168.81.139",
        "Serveur BD": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"  # Nom d'utilisateur corrigé
    commandes_test = [
        "df -h",           # Utilisation du disque
        "free -h",         # État de la RAM
        "uptime",          # Durée de fonctionnement
        "whoami"           # Contrôle utilisateur
    ]
    
    # Vérifier l'existence de la clé SSH
    chemin_cle = os.path.expanduser("~/.ssh/id_rsa")
    if not os.path.exists(chemin_cle):
        print(f"❌ Clé SSH non trouvée: {chemin_cle}")
        print("💡 Exécutez d'abord: ssh-keygen -t rsa -b 4096")
        return
    
    print(f"🔑 Utilisation de la clé SSH: {chemin_cle}")
    print(f"👤 Nom d'utilisateur: {nom_utilisateur}\n")
    
    # Se connecter à chaque serveur et tester les commandes
    for nom_serveur, ip in serveurs.items():
        print(f"🎯 === {nom_serveur} ({ip}) ===")
        
        for commande in commandes_test:
            succes, sortie, erreur = ssh_connect_and_run(ip, nom_utilisateur, commande)
            
            if not succes:
                print(f"❌ Problème d'accès au {nom_serveur}!")
                break
                
        print("-" * 50)

if __name__ == "__main__":
    main()
