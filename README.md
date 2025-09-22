# 🔍 PSMM - Système de Monitoring et Surveillance Multi-serveurs

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Linux](https://img.shields.io/badge/OS-Linux-green.svg)](https://www.debian.org/)
[![Status](https://img.shields.io/badge/Status-Production--Ready-success.svg)]()

## 📋 À Propos

**PSMM (Plateforme de Surveillance et Monitoring Multi-serveurs)** est un système complet de monitoring automatisé développé pour surveiller et maintenir l'infrastructure de serveurs Linux en temps réel.

Développé avec Python et intégrant MariaDB, ce système surveille 3 serveurs (FTP, Web, Base de données) depuis un serveur central de monitoring avec des alertes automatiques et une intégration Google Chat.

## 🎯 Fonctionnalités Principales

- ✅ **Surveillance Multi-serveurs** - Monitoring de serveurs FTP, Web et Base de données
- ✅ **Alertes Automatiques** - Notifications par email et Google Chat en temps réel
- ✅ **Base de Données Centralisée** - Logging centralisé avec MariaDB (psmm_logs)
- ✅ **Sauvegardes Automatiques** - Rotation automatique des backups toutes les 3h
- ✅ **Monitoring Ressources** - CPU, RAM, Disque en temps réel avec seuils d'alerte
- ✅ **Interface Chat** - Communication bidirectionnelle via Google Chat API
- ✅ **15 Scripts Automatisés** - Jobs complets pour maintenance et surveillance

## 🖥️ Architecture Système
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  datateam-ftp   │    │  datateam-web   │    │ datateam-mariadb│
│ (192.168.81.137)│    │ (192.168.81.139)│    │ (192.168.81.141)│
│   - vsftpd      │    │   - Apache2     │    │   - MariaDB     │
│   - Monitoring  │    │   - PHP/Web     │    │   - psmm_logs   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
│                      │                      │
└──────────────────────┼──────────────────────┘
│
┌─────────────┴───────────┐
│   datateam-monitor      │
│   (Serveur Central)     │
│   + Python Scripts      │
│   + Google Chat API     │
└─────────────────────────┘

## 📦 Installation

### Prérequis Système
- **OS**: Debian/Ubuntu Linux
- **Python**: 3.9+ avec paramiko, mysql-connector
- **Base de données**: MariaDB/MySQL
- **Réseau**: SSH Key Authentication configuré
- **Accès**: sudo sur tous les serveurs

### Installation Rapide
```bash
# Cloner le repository
git clone https://github.com/[USERNAME]/PSMM.git
cd PSMM

# Rendre les scripts exécutables
chmod +x scripts/*.py

# Installer les dépendances Python
pip3 install paramiko mysql-connector-python flask psutil
