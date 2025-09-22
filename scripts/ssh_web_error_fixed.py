#!/usr/bin/env python3
"""
Job 08: Script de récupération des erreurs Web - Version corrigée
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
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=15)
        
        time.sleep(1)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        client.close()
        
        return True, sortie
        
    except Exception as e:
        return False, str(e)

def analyser_logs_web_corrige(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Analyser les logs Web avec sudo pour Apache
    """
    print("=== Analyse des logs Web (avec sudo) ===")
    
    # Lire directement les logs Apache avec sudo
    commandes_logs = [
        ("sudo tail -50 /var/log/apache2/access.log | grep -E '40[13]'", "Access log 401/403"),
        ("sudo tail -50 /var/log/apache2/error.log | grep -i auth", "Error log auth"),
        ("sudo tail -50 /var/log/apache2/access.log", "Access log complet")
    ]
    
    erreurs_trouvees = []
    
    for commande, description in commandes_logs:
        print(f"\n--- {description} ---")
        succes, contenu_log = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes and contenu_log and len(contenu_log.strip()) > 0:
            print(f"Logs trouvés - {len(contenu_log)} caractères")
            
            # Afficher échantillon
            lignes = contenu_log.split('\n')[:5]
            for i, ligne in enumerate(lignes):
                if ligne.strip():
                    print(f"  {i+1}: {ligne[:80]}...")
            
            # Analyser les erreurs
            erreurs = extraire_erreurs_web(contenu_log, description)
            erreurs_trouvees.extend(erreurs)
            
            if erreurs:
                print(f"Erreurs détectées: {len(erreurs)}")
        else:
            print("Aucun contenu trouvé")
    
    return erreurs_trouvees

def extraire_erreurs_web(contenu_log, nom_source):
    """
    Extraire les erreurs Web des logs Apache
    """
    erreurs = []
    lines = contenu_log.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        # Pattern Apache access log: IP - user [date] "GET /path HTTP/1.1" code size
        pattern_access = r'(\d+\.\d+\.\d+\.\d+) - ([^\s]*) \[([^\]]+)\] "[^"]*" (40[13]) \d+'
        match = re.search(pattern_access, line)
        
        if match:
            ip_source = match.group(1)
            utilisateur = match.group(2) if match.group(2) != '-' else 'anonymous'
            date_erreur = match.group(3)
            code_statut = match.group(4)
            
            erreur_info = {
                'date_erreur': date_erreur,
                'nom_compte': utilisateur,
                'adresse_ip': ip_source,
                'type_erreur': 'Web Auth Failed',
                'message_complet': line.strip(),
                'serveur_source': 'WEB',
                'code_statut': code_statut
            }
            erreurs.append(erreur_info)
    
    return erreurs

def stocker_erreurs_web(erreurs_trouvees):
    """
    Stocker les erreurs Web en base
    """
    print(f"\n=== Stockage de {len(erreurs_trouvees)} erreurs Web ===")
    
    if not erreurs_trouvees:
        print("Aucune erreur Web à stocker")
        return True
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    for i, erreur in enumerate(erreurs_trouvees):
        date_erreur = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        nom_compte = erreur['nom_compte'].replace("'", "\\'")[:50]
        adresse_ip = erreur['adresse_ip'][:45]
        type_erreur = erreur['type_erreur'][:50]
        message_complet = erreur['message_complet'].replace("'", "\\'")[:500]
        serveur_source = erreur['serveur_source']
        code_statut = erreur['code_statut'][:10]
        
        commande_insertion = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO web_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source, code_statut) VALUES ('{date_erreur}', '{nom_compte}', '{adresse_ip}', '{type_erreur}', '{message_complet}', '{serveur_source}', '{code_statut}');\""
        
        succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_insertion, mot_de_passe_sudo)
        
        if succes:
            print(f"  ✅ {i+1}. Stocké: {nom_compte}@{adresse_ip} (Code: {code_statut})")
        else:
            print(f"  ❌ {i+1}. Échec: {sortie}")
    
    return True

def main():
    print("Analyse des erreurs Web - Version corrigée avec sudo")
    
    ip_serveur_web = "192.168.81.139"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    try:
        # Analyser les logs avec sudo
        erreurs_trouvees = analyser_logs_web_corrige(ip_serveur_web, nom_utilisateur, mot_de_passe_sudo)
        
        # Stocker en base
        stocker_erreurs_web(erreurs_trouvees)
        
        print("\n" + "="*60)
        print("JOB 08 TERMINÉ")
        print(f"Erreurs Web détectées: {len(erreurs_trouvees)}")
        
        if erreurs_trouvees:
            print("✅ Erreurs Web analysées et stockées")
        else:
            print("⚠️ Aucune erreur 401/403 trouvée dans les logs")
        
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    main()
