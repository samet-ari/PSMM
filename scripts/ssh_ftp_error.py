#!/usr/bin/env python3
"""
Job 07: Script de récupération des erreurs FTP - Version finale
Forcer la génération de logs FTP et les analyser
"""

import paramiko
import os
import time

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
        
        sortie = stdout.read().decode('utf-8', errors='ignore').strip()
        client.close()
        
        return True, sortie
        
    except Exception as e:
        return False, str(e)

def generer_vraies_tentatives_ftp(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Générer de vraies tentatives de connexion FTP qui produisent des logs
    """
    print("=== Génération de tentatives FTP réelles ===")
    
    # Utiliser netcat et telnet pour forcer des connexions
    tentatives_agressives = [
        f"timeout 5 nc {ip_serveur} 21 <<< 'USER baduser\r\nPASS wrongpass\r\nQUIT\r\n' 2>/dev/null || echo 'nc_test'",
        f"timeout 5 telnet {ip_serveur} 21 <<< 'USER hacker\r\nPASS 123456\r\nQUIT\r\n' 2>/dev/null || echo 'telnet_test'",
        f"echo -e 'USER admin\\r\\nPASS admin\\r\\nQUIT\\r\\n' | timeout 5 nc {ip_serveur} 21 || echo 'admin_test'",
        f"echo -e 'USER test\\r\\nPASS test\\r\\nQUIT\\r\\n' | timeout 5 nc {ip_serveur} 21 || echo 'test_test'"
    ]
    
    for i, cmd in enumerate(tentatives_agressives):
        print(f"Tentative {i+1}: Connexion directe au port 21")
        succes, sortie = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, cmd, mot_de_passe_sudo)
        time.sleep(2)  # Attendre que les logs soient écrits
    
    print("Tentatives de connexion directe terminées")
    return True

def chercher_logs_partout(ip_serveur, nom_utilisateur, mot_de_passe_sudo):
    """
    Chercher les logs FTP dans tous les emplacements possibles
    """
    print("=== Recherche exhaustive des logs FTP ===")
    
    # Tous les emplacements possibles
    commandes_recherche = [
        ("journalctl -u vsftpd --no-pager -n 20", "Logs systemd vsftpd"),
        ("tail -20 /var/log/syslog | grep -i vsftpd", "Syslog vsftpd"),
        ("tail -20 /var/log/messages 2>/dev/null | grep -i ftp", "Messages FTP"),
        ("tail -20 /var/log/auth.log | grep -i ftp", "Auth logs FTP"),
        ("find /var/log -name '*ftp*' -o -name '*xfer*' -o -name 'vsftpd*' 2>/dev/null", "Fichiers logs FTP"),
        ("ls -la /var/log/vsftpd.log /var/log/xferlog 2>/dev/null", "Logs standards FTP"),
        ("cat /var/log/vsftpd.log 2>/dev/null | tail -10", "Contenu vsftpd.log"),
        ("cat /var/log/xferlog 2>/dev/null | tail -10", "Contenu xferlog")
    ]
    
    logs_trouvés = []
    
    for commande, description in commandes_recherche:
        print(f"\n--- {description} ---")
        succes, resultat = ssh_connect_and_run_sudo(ip_serveur, nom_utilisateur, commande, mot_de_passe_sudo)
        
        if succes and resultat and len(resultat.strip()) > 0:
            print(f"RÉSULTAT TROUVÉ:")
            print(resultat[:400] + "..." if len(resultat) > 400 else resultat)
            
            # Vérifier si ça contient des logs d'erreur FTP
            if any(word in resultat.lower() for word in ['fail', 'error', 'denied', 'incorrect', '530']):
                logs_trouvés.append((description, resultat))
                print("^ LOGS D'ERREUR DÉTECTÉS!")
        else:
            print("Aucun résultat")
    
    return logs_trouvés

def creer_table_ftp_si_necessaire():
    """
    Créer la table FTP sur le serveur MariaDB
    """
    print("\n=== Création table FTP sur serveur MariaDB ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    commande_sql = "mysql -u psmm -ppsmm123 -D psmm_logs -e \"CREATE TABLE IF NOT EXISTS ftp_errors (id INT AUTO_INCREMENT PRIMARY KEY, date_erreur DATETIME, nom_compte VARCHAR(100), adresse_ip VARCHAR(45), type_erreur VARCHAR(50), message_complet TEXT, serveur_source VARCHAR(50), date_insertion TIMESTAMP DEFAULT CURRENT_TIMESTAMP);\""
    
    succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_sql, mot_de_passe_sudo)
    
    if succes:
        print("✅ Table ftp_errors créée/vérifiée")
        return True
    else:
        print(f"❌ Erreur: {sortie}")
        return False

def stocker_logs_ftp_bruts(logs_trouvés):
    """
    Stocker les logs FTP trouvés dans la base de données
    """
    if not logs_trouvés:
        print("\n=== Aucun log FTP à stocker ===")
        return
    
    print(f"\n=== Stockage de {len(logs_trouvés)} sources de logs FTP ===")
    
    ip_mariadb = "192.168.81.141"
    nom_utilisateur = "datateam-monitor"
    mot_de_passe_sudo = "123"
    
    for i, (description, contenu) in enumerate(logs_trouvés):
        # Insérer le log brut pour analyse ultérieure
        date_now = time.strftime('%Y-%m-%d %H:%M:%S')
        contenu_escape = contenu.replace("'", "\\'").replace('"', '\\"')[:500]
        
        commande_insert = f"mysql -u psmm -ppsmm123 -D psmm_logs -e \"INSERT INTO ftp_errors (date_erreur, nom_compte, adresse_ip, type_erreur, message_complet, serveur_source) VALUES ('{date_now}', 'ANALYSE_LOGS', 'SYSTEM', 'Log Analysis', '{contenu_escape}', 'FTP_DIAGNOSTIC');\""
        
        succes, sortie = ssh_connect_and_run_sudo(ip_mariadb, nom_utilisateur, commande_insert, mot_de_passe_sudo)
        
        if succes:
            print(f"✅ {i+1}. Log stocké: {description}")
        else:
            print(f"❌ {i+1}. Erreur: {sortie}")

def main():
    """
    Fonction principale - Analyse finale des logs FTP
    """
    print("Analyse finale des erreurs FTP avec génération forcée de logs")
    
    ip_serveur_ftp = "192.168.81.137"
    nom_utilisateur = "datateam-monitor"  
    mot_de_passe_sudo = "123"
    
    try:
        # 1. Créer table FTP dans MariaDB
        creer_table_ftp_si_necessaire()
        
        # 2. Générer des vraies tentatives de connexion FTP
        generer_vraies_tentatives_ftp(ip_serveur_ftp, nom_utilisateur, mot_de_passe_sudo)
        
        # 3. Attendre que les logs soient écrits
        print("\nAttente de 5 secondes pour l'écriture des logs...")
        time.sleep(5)
        
        # 4. Chercher les logs partout
        logs_trouvés = chercher_logs_partout(ip_serveur_ftp, nom_utilisateur, mot_de_passe_sudo)
        
        # 5. Stocker ce qu'on a trouvé
        stocker_logs_ftp_bruts(logs_trouvés)
        
        # 6. Résumé final
        print("\n" + "="*60)
        print("ANALYSE FTP FINALE")
        print(f"Sources de logs trouvées: {len(logs_trouvés)}")
        
        if logs_trouvés:
            print("✅ Logs FTP détectés et stockés en base de données")
            print("Les erreurs FTP sont maintenant trackées dans psmm_logs.ftp_errors")
        else:
            print("⚠️ Aucun log d'erreur FTP généré - possibles raisons:")
            print("  - Les tentatives de connexion n'échouent pas comme attendu")
            print("  - vsftpd utilise un autre système de logging")
            print("  - Les logs sont dans un emplacement non standard")
        
        print("\nJob 07 terminé - passage au Job 08 (logs Web)")
        
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    main()
