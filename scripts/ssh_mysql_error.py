#!/usr/bin/env python3
"""
Job 06: Script de récupération des erreurs d'accès MariaDB/MySQL - Version corrigée
Analyser les vrais logs MySQL trouvés dans /var/log/mysql/
"""

import paramiko
import sys
import os
import time
import re
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
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=20)
        
        time.sleep(1)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        erreur = stderr.read().decode('utf-8', errors='ignore').strip()
        
        client.close()
        return True, sortie, erreur
        
    except Exception as e:
        return False, "", str(e)

def generer_nouvelles_tentatives_echec(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Générer de nouvelles tentatives échouées avec plus de variété
    """
    print("=== Génération de nouvelles tentatives d'accès échouées ===")
    
    fausses_tentatives = [
        ("pirate", "motdepasse"),
        ("utilisateur", "123456789"),
        ("webmaster", "webmaster"),
        ("guest", "guest"),
        ("administrator", "password123"),
        ("user", "user"),
        ("mysql", "mysql")
    ]
    
    for user, passwd in fausses_tentatives:
        print(f"Tentative échouée: {user}@{passwd}")
        commande = f"mysql -u {user} -p{passwd} -h localhost -e 'SELECT 1;' 2>&1 || echo 'Échec généré'"
        succes, sortie, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande, mot_de_passe_sudo)
        time.sleep(0.5)
    
    # Attendre que les logs soient écrits
    time.sleep(3)
    print("Nouvelles tentatives d'échec générées")
    return True

def analyser_logs_mysql_corriges(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Analyser les logs MySQL dans les vrais emplacements trouvés
    """
    print("=== Analyse des logs MySQL (emplacements corrigés) ===")
    
    # Emplacements confirmés des logs
    chemins_logs = [
        "/var/log/mysql/error.log",
        "/var/log/mysql/mysql.log"
    ]
    
    erreurs_trouvees = []
    
    for chemin in chemins_logs:
        print(f"\nAnalyse de: {chemin}")
        
        # Lire le contenu récent du log
        commande_lecture = f"tail -100 {chemin}"
        succes, contenu_log, erreur = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_lecture, mot_de_passe_sudo)
        
        if succes and contenu_log:
            print(f"Log lu avec succès - {len(contenu_log)} caractères")
            
            # Montrer un échantillon du contenu
            lignes = contenu_log.split('\n')
            print(f"Nombre de lignes: {len(lignes)}")
            
            if len(lignes) > 0:
                print("Échantillon des dernières lignes:")
                for i, ligne in enumerate(lignes[-5:]):
                    if ligne.strip():
                        print(f"  {i+1}: {ligne[:100]}...")
            
            # Analyser les erreurs
            erreurs = extraire_erreurs_connexion_ameliore(contenu_log, chemin)
            erreurs_trouvees.extend(erreurs)
            print(f"Erreurs trouvées dans {chemin}: {len(erreurs)}")
            
        else:
            print(f"Impossible de lire {chemin}: {erreur}")
    
    return erreurs_trouvees

def extraire_erreurs_connexion_ameliore(contenu_log, nom_fichier):
    """
    Extraire les erreurs de connexion avec des patterns améliorés
    """
    erreurs = []
    lines = contenu_log.split('\n')
    
    print(f"Analyse de {len(lines)} lignes dans {nom_fichier}")
    
    for line_num, line in enumerate(lines):
        if not line.strip():
            continue
            
        # Patterns pour différents types d'erreurs MySQL/MariaDB
        patterns = [
            # Access denied classique
            r"Access denied for user '([^']+)'@'([^']+)' \(using password: (YES|NO)\)",
            # Connection refused
            r"Host '([^']+)' is not allowed to connect",
            # Authentication failure générique
            r"authentication.*user[=:\s]*([^\s,']+).*host[=:\s]*([^\s,']+)",
            # Failed connection
            r"Failed.*connection.*user[=:\s]*([^\s,']+).*from[=:\s]*([^\s,']+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    utilisateur = match.group(1)
                    ip_source = match.group(2)
                elif len(match.groups()) >= 1:
                    utilisateur = match.group(1)
                    ip_source = 'localhost'
                else:
                    utilisateur = 'unknown'
                    ip_source = 'unknown'
                
                # Extraire timestamp
                timestamp_patterns = [
                    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
                    r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})',
                    r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'
                ]
                
                date_erreur = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for ts_pattern in timestamp_patterns:
                    ts_match = re.search(ts_pattern, line)
                    if ts_match:
                        date_erreur = ts_match.group(1)
                        break
                
                erreur_info = {
                    'date_erreur': date_erreur,
                    'nom_compte': utilisateur,
                    'adresse_ip': ip_source,
                    'type_erreur': 'Access Denied',
                    'message_complet': line.strip(),
                    'fichier_source': nom_fichier
                }
                erreurs.append(erreur_info)
                print(f"  Erreur détectée ligne {line_num}: {utilisateur}@{ip_source}")
    
    return erreurs

def stocker_erreurs_ameliore(ip_serveur, nom_utilisateur, mot_de_passe_sudo, erreurs_trouvees):
    """
    Stocker les erreurs avec plus de détails
    """
    print(f"\n=== Stockage de {len(erreurs_trouvees)} erreurs en base ===")
    
    if not erreurs_trouvees:
        print("Aucune erreur trouvée à stocker")
        return True
    
    compteur_succes = 0
    for i, erreur in enumerate(erreurs_trouvees):
        date_erreur = erreur['date_erreur']
        nom_compte = erreur['nom_compte'].replace("'", "\\'")[:50]
        adresse_ip = erreur['adresse_ip'][:45]
        type_erreur = erreur['type_erreur'][:50]
        message_complet = erreur['message_complet'].replace("'", "\\'").replace('"', '\\"')[:500]
        
        commande_insertion = f'''mysql -u psmm -ppsmm123 -D psmm_logs -e "
        INSERT INTO mysql_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet) 
        VALUES ('{date_erreur}', '{nom_compte}', '{adresse_ip}', '{type_erreur}', '{message_complet}');"'''
        
        succes, sortie, erreur_sql = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_insertion, mot_de_passe_sudo)
        
        if succes:
            compteur_succes += 1
            print(f"  {i+1}. Stocké: {nom_compte}@{adresse_ip}")
        else:
            print(f"  {i+1}. Échec: {erreur_sql}")
    
    print(f"Résumé: {compteur_succes}/{len(erreurs_trouvees)} erreurs stockées avec succès")
    return True

def main():
    """
    Fonction principale corrigée
    """
    print("Analyse des erreurs MySQL/MariaDB - Version corrigée")
    
    ip_serveur_bd = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    try:
        # 1. Générer de nouvelles tentatives échouées
        generer_nouvelles_tentatives_echec(ip_serveur_bd, nom_utilisateur, mot_de_passe_sudo)
        
        # 2. Analyser les logs dans les bons emplacements
        erreurs_trouvees = analyser_logs_mysql_corriges(ip_serveur_bd, nom_utilisateur, mot_de_passe_sudo)
        
        # 3. Stocker les erreurs trouvées
        if erreurs_trouvees:
            stocker_erreurs_ameliore(ip_serveur_bd, nom_utilisateur, mot_de_passe_sudo, erreurs_trouvees)
        else:
            print("Aucune erreur détectée dans les logs")
        
        # 4. Afficher le résumé
        print("\n" + "="*60)
        print("RÉSUMÉ DE L'ANALYSE")
        print(f"Erreurs détectées: {len(erreurs_trouvees)}")
        
        # Afficher quelques détails
        if erreurs_trouvees:
            print("\nDétails des erreurs:")
            for i, erreur in enumerate(erreurs_trouvees[:3]):
                print(f"  {i+1}. {erreur['nom_compte']} depuis {erreur['adresse_ip']}")
        
        print("Analyse terminée!")
        
    except Exception as e:
        print(f"Erreur générale: {e}")

if __name__ == "__main__":
    main()

