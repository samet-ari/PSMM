#!/usr/bin/env python3
"""
Job 08: Script de récupération des erreurs d'accès Web
Analyser les logs du serveur Web pour les erreurs d'authentification
Le serveur Web est protégé par un compte utilisateur et mot de passe
"""

import paramiko
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
        stdin, stdout, stderr = client.exec_command(commande_complete, timeout=15)
        
        time.sleep(1)
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        client.close()
        
        return True, sortie
        
    except Exception as e:
        return False, str(e)

def creer_table_erreurs_web():
    """
    Créer la table pour stocker les erreurs d'accès Web
    """
    print("=== Création de la table des erreurs Web ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    commande_sql = "mysql -u psmm -ppsmm123 -D psmm_logs -e \"CREATE TABLE IF NOT EXISTS web_errors (id INT AUTO_INCREMENT PRIMARY KEY, date_erreur DATETIME, nom_compte VARCHAR(100), adresse_ip VARCHAR(45), type_erreur VARCHAR(50), message_complet TEXT, serveur_source VARCHAR(50), code_statut VARCHAR(10), date_insertion TIMESTAMP DEFAULT CURRENT_TIMESTAMP);\""
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_sql, mot_de_passe_sudo)
    
    if succes:
        print("✅ Table web_errors créée/vérifiée avec succès")
        return True
    else:
        print(f"❌ Erreur création table: {sortie}")
        return False

def analyser_serveur_web(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Analyser la configuration du serveur Web
    """
    print("=== Analyse de la configuration du serveur Web ===")
    
    commandes_diagnostic = [
        ("systemctl status apache2 --no-pager", "État du service Apache2"),
        ("systemctl status nginx --no-pager", "État du service Nginx"),
        ("ps aux | grep -E '(apache|nginx|httpd)' | grep -v grep", "Processus Web en cours"),
        ("netstat -tlnp | grep :80", "Port HTTP (80) ouvert"),
        ("netstat -tlnp | grep :443", "Port HTTPS (443) ouvert"),
        ("find /var/log -name '*apache*' -o -name '*nginx*' -o -name '*access*' -o -name '*error*' 2>/dev/null", "Logs Web disponibles"),
        ("ls -la /var/log/apache2/ 2>/dev/null", "Logs Apache2"),
        ("ls -la /var/log/nginx/ 2>/dev/null", "Logs Nginx"),
        ("cat /etc/apache2/sites-enabled/* 2>/dev/null | grep -E '(Auth|Directory)' | head -10", "Configuration Auth Apache"),
        ("cat /etc/nginx/sites-enabled/* 2>/dev/null | grep -E '(auth|location)' | head -10", "Configuration Auth Nginx")
    ]
    
    config_info = {}
    
    for commande, description in commandes_diagnostic:
        print(f"\n--- {description} ---")
        succes, resultat = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes and resultat:
            print(resultat[:300] + "..." if len(resultat) > 300 else resultat)
            config_info[description] = resultat
        else:
            print("Aucun résultat")
    
    return config_info

def generer_tentatives_auth_web(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Générer des tentatives d'authentification échouées sur le serveur Web
    """
    print("=== Génération de tentatives d'authentification Web échouées ===")
    
    # Tentatives avec différents outils HTTP
    tentatives = [
        ("admin", "password"),
        ("webmaster", "123"),
        ("user", "user"),
        ("test", "123"),
        ("root", "toor"),
        ("guest", "guest"),
        ("administrator", "123")
    ]
    
    for user, passwd in tentatives:
        print(f"Tentative Web: {user}@{passwd}")
        
        # Utiliser curl avec authentification basique
        commandes_http = [
            f"curl -s -u {user}:{passwd} http://{ip_serveur}/ -w '%{{http_code}}' -o /dev/null --connect-timeout 5 || echo 'curl_fail'",
            f"wget --user={user} --password={passwd} --tries=1 --timeout=5 -qO- http://{ip_serveur}/ 2>/dev/null || echo 'wget_fail'",
            f"curl -s -u {user}:{passwd} http://{ip_serveur}/admin/ -w '%{{http_code}}' -o /dev/null --connect-timeout 5 || echo 'admin_fail'",
            f"curl -s -u {user}:{passwd} http://{ip_serveur}/login/ -w '%{{http_code}}' -o /dev/null --connect-timeout 5 || echo 'login_fail'"
        ]
        
        for cmd in commandes_http:
            succes, sortie = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, cmd, mot_de_passe_sudo)
            time.sleep(1)
    
    print("Tentatives d'authentification Web générées")
    return True

def analyser_logs_web(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Analyser les logs du serveur Web pour trouver les erreurs d'authentification
    """
    print("=== Analyse des logs Web ===")
    
    # Emplacements possibles des logs Web
    chemins_logs_web = [
        "/var/log/apache2/access.log",
        "/var/log/apache2/error.log",
        "/var/log/nginx/access.log", 
        "/var/log/nginx/error.log",
        "/var/log/httpd/access_log",
        "/var/log/httpd/error_log",
        "/var/log/auth.log",
        "/var/log/syslog"
    ]
    
    erreurs_trouvees = []
    
    for chemin in chemins_logs_web:
        print(f"\nAnalyse de: {chemin}")
        
        # Vérifier existence et lire les logs récents
        commande_lecture = f"test -f {chemin} && tail -50 {chemin} | grep -iE '(40[13]|auth|login|password|unauthorized)' || echo 'NOT_FOUND'"
        succes, contenu_log = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande_lecture, mot_de_passe_sudo)
        
        if succes and contenu_log and 'NOT_FOUND' not in contenu_log:
            print(f"Logs Web trouvés - {len(contenu_log)} caractères")
            
            # Afficher échantillon
            lignes = contenu_log.split('\n')[:5]
            for i, ligne in enumerate(lignes):
                if ligne.strip():
                    print(f"  Échantillon {i+1}: {ligne[:80]}...")
            
            # Analyser les erreurs Web
            erreurs = extraire_erreurs_web(contenu_log, chemin)
            erreurs_trouvees.extend(erreurs)
            
            if erreurs:
                print(f"Erreurs Web détectées: {len(erreurs)}")
        else:
            print(f"Log non trouvé ou vide: {chemin}")
    
    return erreurs_trouvees

def extraire_erreurs_web(contenu_log, nom_fichier):
    """
    Extraire les erreurs d'authentification Web avec regex
    """
    erreurs = []
    lines = contenu_log.split('\n')
    
    for line in lines:
        if not line.strip():
            continue
        
        # Patterns pour erreurs Web (Apache/Nginx)
        patterns_web = [
            # Apache access log avec codes 401/403
            r'(\d+\.\d+\.\d+\.\d+).*\[([^\]]+)\].*"[A-Z]+ [^"]*" (40[13]) \d+',
            # Nginx access log avec codes 401/403  
            r'(\d+\.\d+\.\d+\.\d+) - ([^\s]*) \[([^\]]+)\] "[^"]*" (40[13]) \d+',
            # Erreurs d'authentification génériques
            r'authentication.*failed.*user[=:\s]*([^\s,]+).*from[=:\s]*([^\s,\]]+)',
            r'Invalid user.*([^\s,]+).*from.*(\d+\.\d+\.\d+\.\d+)',
            # Apache error log
            r'client (\d+\.\d+\.\d+\.\d+).*user ([^:]+): authentication failure',
            # Nginx error log
            r'(\d+\.\d+\.\d+\.\d+).*user "([^"]+)".*password mismatch'
        ]
        
        for pattern in patterns_web:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Déterminer IP et utilisateur selon le pattern
                if len(groups) >= 2:
                    if '.' in groups[0]:  # Premier groupe est IP
                        ip_source = groups[0]
                        utilisateur = groups[1] if len(groups) > 1 else 'unknown'
                    else:  # Premier groupe est utilisateur
                        utilisateur = groups[0]
                        ip_source = groups[1] if len(groups) > 1 and '.' in groups[1] else 'unknown'
                else:
                    ip_source = 'unknown'
                    utilisateur = 'unknown'
                
                # Code de statut HTTP si disponible
                code_statut = 'unknown'
                for group in groups:
                    if group and group in ['401', '403', '404']:
                        code_statut = group
                        break
                
                # Extraire timestamp
                date_erreur = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                timestamp_patterns = [
                    r'\[([^\]]+)\]',
                    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})'
                ]
                
                for ts_pattern in timestamp_patterns:
                    timestamp_match = re.search(ts_pattern, line)
                    if timestamp_match:
                        date_erreur = timestamp_match.group(1)
                        break
                
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
                break
    
    return erreurs

def stocker_erreurs_web(erreurs_trouvees):
    """
    Stocker les erreurs Web dans la base de données
    """
    print(f"\n=== Stockage de {len(erreurs_trouvees)} erreurs Web ===")
    
    if not erreurs_trouvees:
        print("Aucune erreur Web trouvée à stocker")
        return True
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    compteur_succes = 0
    
    for i, erreur in enumerate(erreurs_trouvees):
        date_erreur = erreur['date_erreur']
        nom_compte = erreur['nom_compte'].replace("'", "\\'")[:50]
        adresse_ip = erreur['adresse_ip'][:45]
        type_erreur = erreur['type_erreur'][:50]
        message_complet = erreur['message_complet'].replace("'", "\\'")[:500]
        serveur_source = erreur['serveur_source']
        code_statut = erreur['code_statut'][:10]
        
        commande_insertion = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO web_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source, code_statut) VALUES ('{date_erreur}', '{nom_compte}', '{adresse_ip}', '{type_erreur}', '{message_complet}', '{serveur_source}', '{code_statut}');\""
        
        succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_insertion, mot_de_passe_sudo)
        
        if succes:
            compteur_succes += 1
            print(f"  ✅ {i+1}. Stocké: {nom_compte}@{adresse_ip} (Code: {code_statut})")
        else:
            print(f"  ❌ {i+1}. Échec: {sortie}")
    
    print(f"Résumé: {compteur_succes}/{len(erreurs_trouvees)} erreurs Web stockées")
    return True

def main():
    """
    Fonction principale - Analyser les erreurs d'authentification Web
    """
    print("Analyse des erreurs d'authentification du serveur Web")
    
    ip_serveur_web = "192.168.81.139"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    try:
        # 1. Créer table Web errors
        if not creer_table_erreurs_web():
            return
        
        # 2. Analyser la configuration du serveur Web
        config_info = analyser_serveur_web(ip_serveur_web, nom_utilisateur, mot_de_passe_sudo)
        
        # 3. Générer des tentatives d'authentification échouées
        generer_tentatives_auth_web(ip_serveur_web, nom_utilisateur, mot_de_passe_sudo)
        
        # 4. Attendre que les logs soient écrits
        print("\nAttente de 5 secondes pour l'écriture des logs...")
        time.sleep(5)
        
        # 5. Analyser les logs Web
        erreurs_trouvees = analyser_logs_web(ip_serveur_web, nom_utilisateur, mot_de_passe_sudo)
        
        # 6. Stocker les erreurs en base
        stocker_erreurs_web(erreurs_trouvees)
        
        # 7. Résumé final
        print("\n" + "="*60)
        print("ANALYSE WEB TERMINÉE")
        print(f"Erreurs Web détectées: {len(erreurs_trouvees)}")
        
        if erreurs_trouvees:
            print("✅ Logs Web analysés et stockés en base de données")
            print("Les erreurs Web sont trackées dans psmm_logs.web_errors")
        else:
            print("⚠️ Aucune erreur Web détectée - possibles raisons:")
            print("  - Serveur Web non protégé par authentification")
            print("  - Logs dans un emplacement non standard")
            print("  - Tentatives non loggées")
        
        print("\nJob 08 terminé - passage au Job 09 (envoi de mails)")
        
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    main()
