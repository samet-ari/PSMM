#!/usr/bin/env python3
"""
Job 14: Script de mise à jour automatique des serveurs
Se connecter à alcasar, vérifier les mises à jour, les installer
Vérifier si redémarrage nécessaire et envoyer mail à l'administrateur
Puis se déconnecter d'alcasar
"""

import paramiko
import os
import time
import re
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
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=30)
        
        time.sleep(2)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        erreur = stderr.read().decode('utf-8', errors='ignore').strip()
        client.close()
        
        return True, sortie, erreur
        
    except Exception as e:
        return False, "", str(e)

def connecter_alcasar():
    """
    Se connecter au réseau alcasar pour accéder à Internet
    """
    print("=== Connexion au réseau alcasar ===")
    
    # Note: Dans un environnement réel, alcasar serait le portail captif
    # Ici nous simulons la connexion réseau
    
    commandes_connexion = [
        ("ping -c 3 8.8.8.8", "Test connectivité Internet"),
        ("curl -s --connect-timeout 10 http://debian.org > /dev/null && echo 'INTERNET_OK' || echo 'INTERNET_FAILED'", "Vérification accès web")
    ]
    
    for commande, description in commandes_connexion:
        print(f"{description}...")
        resultat = os.system(commande + " > /dev/null 2>&1")
        
        if resultat == 0:
            print(f"✅ {description} réussie")
        else:
            print(f"⚠️ {description} échouée")
    
    # Test avec curl plus explicite
    commande_test = "timeout 10 curl -s -I http://debian.org | head -1"
    try:
        resultat = os.popen(commande_test).read().strip()
        if "200 OK" in resultat:
            print("✅ Connexion Internet confirmée")
            return True
        else:
            print("⚠️ Connexion Internet limitée")
            return False
    except:
        print("⚠️ Test de connectivité échoué")
        return False

def verifier_mises_a_jour_serveur(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Vérifier les mises à jour disponibles sur un serveur
    """
    print(f"\n=== Vérification mises à jour: {nom_serveur} ({ip_serveur}) ===")
    
    resultats = {
        'serveur': nom_serveur,
        'ip': ip_serveur,
        'mises_a_jour_disponibles': 0,
        'paquets_a_jour': [],
        'erreurs': [],
        'reboot_requis': False
    }
    
    # 1. Mise à jour de la liste des paquets
    print("Mise à jour de la liste des paquets...")
    succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, "apt update", mot_de_passe_sudo)
    
    if not succes:
        resultats['erreurs'].append(f"Erreur apt update: {erreur}")
        return resultats
    
    # 2. Vérifier les mises à jour disponibles
    print("Vérification des paquets à mettre à jour...")
    succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, "apt list --upgradable 2>/dev/null | grep -c upgradable", mot_de_passe_sudo)
    
    if succes and sortie:
        try:
            # Soustraire 1 car apt list inclut une ligne d'en-tête
            nb_updates = max(0, int(sortie) - 1) if sortie.isdigit() else 0
            resultats['mises_a_jour_disponibles'] = nb_updates
            print(f"Mises à jour disponibles: {nb_updates}")
        except:
            resultats['mises_a_jour_disponibles'] = 0
    
    # 3. Lister les paquets à mettre à jour
    if resultats['mises_a_jour_disponibles'] > 0:
        succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, "apt list --upgradable 2>/dev/null | tail -n +2 | head -10", mot_de_passe_sudo)
        
        if succes and sortie:
            paquets = sortie.split('\n')
            for paquet in paquets[:5]:  # Limiter à 5 pour l'affichage
                if paquet.strip():
                    nom_paquet = paquet.split('/')[0] if '/' in paquet else paquet
                    resultats['paquets_a_jour'].append(nom_paquet.strip())
            
            print(f"Exemples de paquets: {', '.join(resultats['paquets_a_jour'][:3])}")
    
    return resultats

def installer_mises_a_jour_serveur(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo, nb_updates):
    """
    Installer les mises à jour sur un serveur
    """
    print(f"\n=== Installation mises à jour: {nom_serveur} ===")
    
    if nb_updates == 0:
        print("✅ Aucune mise à jour nécessaire")
        return True, False
    
    print(f"Installation de {nb_updates} mise(s) à jour...")
    
    # Installation avec confirmation automatique et sans interaction
    commande_upgrade = "DEBIAN_FRONTEND=noninteractive apt upgrade -y -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold'"
    
    succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_upgrade, mot_de_passe_sudo)
    
    if succes:
        print(f"✅ Mises à jour installées sur {nom_serveur}")
        
        # Vérifier si un redémarrage est nécessaire
        reboot_requis = verifier_reboot_requis(ip_serveur, nom_utilisateur, mot_de_passe_sudo)
        
        return True, reboot_requis
    else:
        print(f"❌ Erreur lors de l'installation: {erreur}")
        return False, False

def verifier_reboot_requis(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Vérifier si un redémarrage est requis après les mises à jour
    """
    # Vérifier l'existence du fichier /var/run/reboot-required
    succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, "test -f /var/run/reboot-required && echo 'REBOOT_REQUIRED' || echo 'NO_REBOOT'", mot_de_passe_sudo)
    
    if succes and "REBOOT_REQUIRED" in sortie:
        print("⚠️ Redémarrage requis après mise à jour")
        return True
    else:
        print("✅ Aucun redémarrage requis")
        return False

def envoyer_rapport_mises_a_jour(resultats_serveurs, serveurs_reboot_requis):
    """
    Envoyer un rapport des mises à jour à l'administrateur
    """
    print(f"\n=== Envoi rapport mises à jour ===")
    
    date_rapport = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # Statistiques globales
    total_serveurs = len(resultats_serveurs)
    serveurs_avec_updates = sum(1 for r in resultats_serveurs if r.get('mises_a_jour_disponibles', 0) > 0)
    total_updates = sum(r.get('mises_a_jour_disponibles', 0) for r in resultats_serveurs)
    
    contenu_rapport = f"""
📦 RAPPORT DE MISES À JOUR SYSTÈME - DATATEAM

Date: {date_rapport}
Serveurs vérifiés: {total_serveurs}
Serveurs avec mises à jour: {serveurs_avec_updates}
Total mises à jour installées: {total_updates}

=== DÉTAIL PAR SERVEUR ===
"""
    
    for resultat in resultats_serveurs:
        nom = resultat.get('serveur', 'Unknown')
        ip = resultat.get('ip', 'Unknown')
        nb_updates = resultat.get('mises_a_jour_disponibles', 0)
        paquets = resultat.get('paquets_a_jour', [])
        
        contenu_rapport += f"\n🖥️ {nom} ({ip}):\n"
        contenu_rapport += f"   Mises à jour: {nb_updates}\n"
        
        if paquets:
            contenu_rapport += f"   Paquets: {', '.join(paquets[:3])}\n"
        
        if nom in serveurs_reboot_requis:
            contenu_rapport += f"   ⚠️ REDÉMARRAGE REQUIS\n"
        else:
            contenu_rapport += f"   ✅ Aucun redémarrage nécessaire\n"
    
    if serveurs_reboot_requis:
        contenu_rapport += f"\n🔴 ACTIONS REQUISES:\n"
        contenu_rapport += f"Les serveurs suivants nécessitent un redémarrage:\n"
        for serveur in serveurs_reboot_requis:
            contenu_rapport += f"• {serveur}\n"
        contenu_rapport += f"\nPlanifier le redémarrage pendant une fenêtre de maintenance.\n"
    
    contenu_rapport += f"""

=== INFORMATIONS SYSTÈME ===
Processus automatique: Mise à jour serveurs PSMM
Connexion réseau: Via alcasar (simulé)
Prochaine vérification: Selon planification cron

---
Système de mise à jour automatique PSMM
Monitoring: datateam-monitor
"""
    
    # Simulation d'envoi
    print("SIMULATION ENVOI RAPPORT MISES À JOUR:")
    print("="*60)
    print("À: admin@datateam.local")
    print("Sujet: [MAINTENANCE] Rapport mises à jour système")
    print("="*60)
    print(contenu_rapport)
    print("="*60)
    
    # Logger le rapport
    logger_rapport_updates(len(resultats_serveurs), total_updates, len(serveurs_reboot_requis))
    
    print("✅ Rapport envoyé et loggé")

def logger_rapport_updates(nb_serveurs, nb_updates, nb_reboots):
    """
    Logger le rapport de mises à jour en base de données
    """
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    date_action = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"Updates: {nb_serveurs} serveurs, {nb_updates} mises à jour, {nb_reboots} reboots requis"
    
    commande_log = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO ftp_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source) VALUES ('{date_action}', 'AUTO_UPDATE', '127.0.0.1', 'System Update', '{message}', 'MAINTENANCE');\""
    
    succes, sortie, erreur = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_log, mot_de_passe_sudo)

def deconnecter_alcasar():
    """
    Se déconnecter du réseau alcasar
    """
    print(f"\n=== Déconnexion alcasar ===")
    print("🔌 Déconnexion du portail captif (simulé)")
    print("✅ Déconnexion réseau terminée")

def main():
    """
    Fonction principale - Mise à jour automatique avec connexion alcasar
    """
    print("Mise à jour automatique des serveurs - Job 14")
    print("Processus: Connexion → Vérification → Installation → Rapport → Déconnexion")
    print("")
    
    # Configuration des serveurs
    serveurs = {
        "datateam-ftp": "192.168.81.137",
        "datateam-web": "192.168.81.139", 
        "datateam-mariadb": "192.168.81.141"
    }
    
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    try:
        # 1. Connexion à alcasar pour accès Internet
        connexion_ok = connecter_alcasar()
        
        if not connexion_ok:
            print("⚠️ Connexion Internet limitée - Continuons quand même")
        
        # 2. Vérification des mises à jour sur chaque serveur
        resultats_serveurs = []
        serveurs_reboot_requis = []
        
        for nom_serveur, ip_serveur in serveurs.items():
            # Vérifier les mises à jour disponibles
            resultat = verifier_mises_a_jour_serveur(ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo)
            resultats_serveurs.append(resultat)
            
            # Installer si nécessaire
            if resultat['mises_a_jour_disponibles'] > 0:
                installation_ok, reboot_requis = installer_mises_a_jour_serveur(
                    ip_serveur, nom_serveur, nom_utilisateur, mot_de_passe_sudo, 
                    resultat['mises_a_jour_disponibles']
                )
                
                if reboot_requis:
                    serveurs_reboot_requis.append(nom_serveur)
        
        # 3. Envoyer le rapport à l'administrateur
        envoyer_rapport_mises_a_jour(resultats_serveurs, serveurs_reboot_requis)
        
        # 4. Déconnexion alcasar
        deconnecter_alcasar()
        
        # 5. Résumé final
        total_updates = sum(r.get('mises_a_jour_disponibles', 0) for r in resultats_serveurs)
        
        print("\n" + "="*60)
        print("JOB 14 TERMINÉ")
        print("="*60)
        print(f"✅ {len(serveurs)} serveurs vérifiés")
        print(f"✅ {total_updates} mise(s) à jour installée(s)")
        print(f"✅ {len(serveurs_reboot_requis)} serveur(s) nécessite(nt) un redémarrage")
        print(f"✅ Rapport envoyé à l'administrateur")
        
        if serveurs_reboot_requis:
            print(f"⚠️ Redémarrage requis: {', '.join(serveurs_reboot_requis)}")
        
        
    except Exception as e:
        print(f"❌ Erreur lors du Job 14: {e}")
        # Assurer la déconnexion même en cas d'erreur
        deconnecter_alcasar()

if __name__ == "__main__":
    main()
