#!/usr/bin/env python3
"""
Lecteur de Messages Google Chat - PSMM
Lire les messages entrants depuis Google Chat et envoyer des réponses
Version française complète pour le système PSMM
"""

import os
import json
import subprocess
from datetime import datetime

# Fichier de stockage des messages
FICHIER_MESSAGES = "/tmp/google_chat_mesajlar.log"

# Configuration webhook pour réponses
WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQAwl_qRJ8/messages?key=AIzaSyDdI0hCZtE6vySjMlVl6e3zfBRPIGV__PU&token=9eqH2fEZNn3y24tXKLX6n9L-NafVnRjTD1Bg8CDMJ7k"

def lire_messages_recents(nombre=10):
    """
    Lire les derniers messages reçus de Google Chat
    """
    print("📱 Messages Google Chat Reçus:")
    print("=" * 60)
    
    if os.path.exists(FICHIER_MESSAGES):
        try:
            with open(FICHIER_MESSAGES, 'r', encoding='utf-8') as fichier:
                lignes_messages = fichier.readlines()
            
            if lignes_messages:
                # Afficher les derniers messages
                messages_recents = lignes_messages[-nombre:]
                for message in messages_recents:
                    print(message.strip())
                
                print(f"\nTotal: {len(lignes_messages)} message(s) reçu(s)")
            else:
                print("📭 Aucun message dans le fichier")
        except Exception as e:
            print(f"❌ Erreur lecture fichier: {e}")
    else:
        print("📂 Fichier de messages non trouvé")
        print(f"Chemin attendu: {FICHIER_MESSAGES}")
    
    print("=" * 60)

def envoyer_reponse_chat(texte_reponse):
    """
    Envoyer une réponse vers Google Chat
    """
    try:
        # Formatage du message de réponse
        horodatage = datetime.now().strftime('%H:%M:%S')
        message_formate = f"🤖 PSMM Réponse ({horodatage}): {texte_reponse}"
        
        # Préparation du payload JSON
        payload = {"text": message_formate}
        donnees_json = json.dumps(payload, ensure_ascii=False)
        
        # Commande curl pour envoi
        commande_curl = [
            'curl', '-X', 'POST',
            '-H', 'Content-Type: application/json; charset=utf-8',
            '-d', donnees_json,
            WEBHOOK_URL
        ]
        
        # Exécution de l'envoi
        resultat = subprocess.run(
            commande_curl, 
            capture_output=True, 
            text=True, 
            timeout=15
        )
        
        if resultat.returncode == 0:
            print(f"✅ Réponse envoyée: {texte_reponse}")
            
            # Logger l'envoi de la réponse
            logger_reponse_envoyee(texte_reponse)
            return True
        else:
            print(f"❌ Erreur envoi: {resultat.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de la réponse: {e}")
        return False

def logger_reponse_envoyee(texte_reponse):
    """
    Logger les réponses envoyées dans un fichier séparé
    """
    fichier_reponses = "/tmp/reponses_psmm_chat.log"
    horodatage = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    ligne_log = f"[{horodatage}] PSMM Réponse: {texte_reponse}\n"
    
    try:
        with open(fichier_reponses, 'a', encoding='utf-8') as fichier:
            fichier.write(ligne_log)
    except Exception as e:
        print(f"Erreur logging réponse: {e}")

def mode_surveillance_continue():
    """
    Mode surveillance continue des messages
    """
    print("👁️  Mode Surveillance Continue des Messages")
    print("Appuyez sur Ctrl+C pour arrêter")
    print("-" * 40)
    
    import time
    
    try:
        taille_precedente = 0
        
        while True:
            if os.path.exists(FICHIER_MESSAGES):
                taille_actuelle = os.path.getsize(FICHIER_MESSAGES)
                
                if taille_actuelle > taille_precedente:
                    print(f"\n🔔 Nouveau message détecté à {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Lire le nouveau message
                    with open(FICHIER_MESSAGES, 'r', encoding='utf-8') as fichier:
                        lignes = fichier.readlines()
                        if lignes:
                            print(f"Dernier message: {lignes[-1].strip()}")
                    
                    taille_precedente = taille_actuelle
                    
            time.sleep(5)  # Vérifier toutes les 5 secondes
            
    except KeyboardInterrupt:
        print("\n🛑 Surveillance arrêtée")

def mode_discussion_interactive():
    """
    Mode discussion interactive avec Google Chat
    """
    print("💬 Mode Discussion Interactive PSMM-Google Chat")
    print("Tapez 'quitter' pour sortir, 'messages' pour voir les messages")
    print("-" * 50)
    
    while True:
        try:
            # Afficher les messages récents d'abord
            lire_messages_recents(3)
            
            # Demander réponse à l'utilisateur
            reponse = input("\n💭 Votre réponse (ou commande): ").strip()
            
            if reponse.lower() in ['quitter', 'quit', 'exit', 'sortir']:
                print("👋 Au revoir!")
                break
            elif reponse.lower() == 'messages':
                lire_messages_recents(10)
                continue
            elif reponse.lower() == 'statut':
                envoyer_reponse_chat("Système PSMM opérationnel - Monitoring actif")
            elif reponse.lower() == 'aide':
                print("\nCommandes disponibles:")
                print("- 'messages': Afficher tous les messages")
                print("- 'statut': Envoyer statut système")
                print("- 'quitter': Sortir du mode interactif")
                print("- Tout autre texte: Envoyer comme réponse")
                continue
            elif reponse:
                envoyer_reponse_chat(reponse)
            
            print("\n" + "-" * 30)
            
        except KeyboardInterrupt:
            print("\n\n👋 Discussion interrompue")
            break
        except Exception as e:
            print(f"Erreur: {e}")

def generer_rapport_messages():
    """
    Générer un rapport des messages reçus
    """
    print("📋 Génération du Rapport de Messages")
    
    if not os.path.exists(FICHIER_MESSAGES):
        print("Aucun fichier de messages trouvé")
        return
    
    try:
        with open(FICHIER_MESSAGES, 'r', encoding='utf-8') as fichier:
            messages = fichier.readlines()
        
        total_messages = len(messages)
        print(f"Total messages reçus: {total_messages}")
        
        if total_messages > 0:
            # Analyser les expéditeurs
            expediteurs = {}
            for message in messages:
                if ': ' in message:
                    try:
                        partie_expediteur = message.split('] ')[1].split(':')[0]
                        expediteurs[partie_expediteur] = expediteurs.get(partie_expediteur, 0) + 1
                    except:
                        continue
            
            print("\nMessages par expéditeur:")
            for expediteur, count in expediteurs.items():
                print(f"  {expediteur}: {count} message(s)")
            
            # Messages récents
            print(f"\nDerniers 5 messages:")
            for message in messages[-5:]:
                print(f"  {message.strip()}")
        
        # Générer rapport pour Google Chat
        if total_messages > 0:
            rapport = f"📊 Rapport Messages PSMM: {total_messages} messages reçus. "
            rapport += f"Dernière activité: {messages[-1][:30] if messages else 'N/A'}"
            envoyer_reponse_chat(rapport)
            
    except Exception as e:
        print(f"Erreur génération rapport: {e}")

def nettoyer_anciens_messages(jours=7):
    """
    Nettoyer les messages plus anciens que X jours
    """
    print(f"🧹 Nettoyage messages plus anciens que {jours} jours")
    
    if not os.path.exists(FICHIER_MESSAGES):
        print("Aucun fichier à nettoyer")
        return
    
    try:
        from datetime import timedelta
        limite_date = datetime.now() - timedelta(days=jours)
        
        with open(FICHIER_MESSAGES, 'r', encoding='utf-8') as fichier:
            lignes = fichier.readlines()
        
        lignes_conservees = []
        for ligne in lignes:
            try:
                # Extraire la date de la ligne [YYYY-MM-DD HH:MM:SS]
                if ligne.startswith('['):
                    date_str = ligne[1:20]  # [2025-09-19 22:01:50]
                    date_message = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    
                    if date_message >= limite_date:
                        lignes_conservees.append(ligne)
                else:
                    lignes_conservees.append(ligne)  # Conserver si format non reconnu
            except:
                lignes_conservees.append(ligne)  # Conserver en cas d'erreur parsing
        
        # Réécrire le fichier avec les messages conservés
        with open(FICHIER_MESSAGES, 'w', encoding='utf-8') as fichier:
            fichier.writelines(lignes_conservees)
        
        messages_supprimes = len(lignes) - len(lignes_conservees)
        print(f"✅ {messages_supprimes} anciens messages supprimés")
        print(f"📁 {len(lignes_conservees)} messages conservés")
        
    except Exception as e:
        print(f"Erreur nettoyage: {e}")

def afficher_aide():
    """
    Afficher l'aide du script
    """
    aide_texte = """
📖 AIDE - Lecteur Messages Google Chat PSMM

UTILISATION:
  python3 lecteur_messages_chat.py [COMMANDE]

COMMANDES DISPONIBLES:
  lire               - Lire les derniers messages (par défaut)
  repondre [TEXTE]   - Envoyer une réponse
  discussion         - Mode discussion interactive
  surveillance       - Mode surveillance continue
  rapport            - Générer rapport des messages
  nettoyer           - Nettoyer anciens messages
  aide               - Afficher cette aide

EXEMPLES:
  python3 lecteur_messages_chat.py
  python3 lecteur_messages_chat.py lire
  python3 lecteur_messages_chat.py repondre "Système opérationnel"
  python3 lecteur_messages_chat.py discussion
  python3 lecteur_messages_chat.py surveillance

FICHIERS:
  Messages entrants: /tmp/google_chat_mesajlar.log
  Réponses envoyées: /tmp/reponses_psmm_chat.log

INTÉGRATION PSMM:
  Ce script fait partie du système de monitoring PSMM
  et permet la communication bidirectionnelle avec Google Chat.
"""
    print(aide_texte)

def main():
    """
    Fonction principale avec gestion des arguments
    """
    import sys
    
    if len(sys.argv) == 1:
        # Par défaut: lire les messages
        lire_messages_recents()
        
    elif len(sys.argv) >= 2:
        commande = sys.argv[1].lower()
        
        if commande in ['lire', 'read']:
            lire_messages_recents()
            
        elif commande in ['repondre', 'reply']:
            if len(sys.argv) >= 3:
                texte_reponse = ' '.join(sys.argv[2:])
                envoyer_reponse_chat(texte_reponse)
            else:
                print("Usage: python3 lecteur_messages_chat.py repondre [TEXTE]")
                
        elif commande in ['discussion', 'chat', 'interactif']:
            mode_discussion_interactive()
            
        elif commande in ['surveillance', 'watch', 'monitor']:
            mode_surveillance_continue()
            
        elif commande in ['rapport', 'report']:
            generer_rapport_messages()
            
        elif commande in ['nettoyer', 'clean']:
            nettoyer_anciens_messages()
            
        elif commande in ['aide', 'help', '--help', '-h']:
            afficher_aide()
            
        else:
            print(f"Commande inconnue: {commande}")
            print("Utilisez 'aide' pour voir les commandes disponibles")
    
    else:
        afficher_aide()

if __name__ == "__main__":
    main()
