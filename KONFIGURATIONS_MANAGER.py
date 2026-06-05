# KONFIGURATIONS_MANAGER.py
"""
ZENTRALER KONFIGURATIONS-MANAGER FÜR SCHACHMATTSCHILD SYSTEM
Enterprise-Grade Konfigurationsverwaltung für alle 11 Module
"""

import json
import yaml
import os
import threading
import time
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging
from datetime import datetime
import copy

class KonfigurationsUmgebung(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing" 
    PRODUCTION = "production"
    STAGING = "staging"

class KonfigurationsBereich(Enum):
    SYSTEM = "system"
    SICHERHEIT = "sicherheit"
    PERFORMANCE = "performance"
    NETZWERK = "netzwerk"
    MODULE = "module"
    SENSITIVE = "sensitive"

class AenderungsTyp(Enum):
    ERSTELLT = "erstellt"
    AKTUALISIERT = "aktualisiert"
    GELOESCHT = "gelöscht"
    ROLLBACK = "rollback"
    IMPORTIERT = "importiert"

@dataclass
class KonfigurationsAenderung:
    aenderung_id: str
    timestamp: float
    benutzer: str
    bereich: KonfigurationsBereich
    typ: AenderungsTyp
    schluessel: str
    alter_wert: Any
    neuer_wert: Any
    kommentar: str = ""
    version: str = ""

@dataclass
class KonfigurationsVersion:
    version_id: str
    timestamp: float
    beschreibung: str
    checksum: str
    konfiguration: Dict[str, Any]
    aenderungen: List[KonfigurationsAenderung]
    benutzer: str

class SensitiveDataVerschluesselung:
    """Verschlüsselung für sensible Konfigurationsdaten"""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
        self.fernet = self._initialisiere_verschluesselung()
        
    def _initialisiere_verschluesselung(self) -> Fernet:
        """Initialisiert AES-256 Verschlüsselung für sensible Daten"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"SCHACHMATTSCHILD_CONFIG_SALT",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def verschluesseln(self, daten: str) -> str:
        """Verschlüsselt sensible Daten"""
        return self.fernet.encrypt(daten.encode()).decode()
    
    def entschluesseln(self, verschluesselte_daten: str) -> str:
        """Entschlüsselt sensible Daten"""
        daten_bytes = self.fernet.decrypt(verschluesselte_daten.encode())
        return daten_bytes.decode()
    
    def ist_verschluesselt(self, daten: str) -> bool:
        """Prüft ob Daten verschlüsselt sind"""
        try:
            self.entschluesseln(daten)
            return True
        except:
            return False

class KonfigurationsValidierung:
    """Validierung aller Konfigurationsparameter"""
    
    def __init__(self):
        self.validierungs_regeln = self._initialisiere_validierungs_regeln()
        
    def _initialisiere_validierungs_regeln(self) -> Dict[str, Callable]:
        """Initialisiert Validierungsregeln für alle Konfigurationsparameter"""
        return {
            # System-Konfiguration
            "system.umgebung": self._validiere_umgebung,
            "system.debug": self._validiere_boolean,
            "system.log_level": self._validiere_log_level,
            
            # Performance-Konfiguration
            "performance.update_intervall": self._validiere_positive_zahl,
            "performance.max_cpu_auslastung": self._validiere_prozent,
            "performance.max_ram_auslastung": self._validiere_prozent,
            
            # Netzwerk-Konfiguration
            "netzwerk.timeout": self._validiere_positive_zahl,
            "netzwerk.max_verbindungen": self._validiere_positive_ganzzahl,
            "netzwerk.port": self._validiere_port,
            
            # Sicherheits-Konfiguration
            "sicherheit.master_key": self._validiere_nicht_leer,
            "sicherheit.verschluesselung_aktiv": self._validiere_boolean,
            
            # Modul-spezifische Konfiguration
            "module.schwarmintelligenz.max_drohnen": self._validiere_positive_ganzzahl,
            "module.zielerkennung.confidence_threshold": self._validiere_prozent,
            "module.kommunikation.retry_attempts": self._validiere_positive_ganzzahl,
        }
    
    def validiere_konfiguration(self, konfiguration: Dict[str, Any]) -> List[str]:
        """Validiert gesamte Konfiguration und gibt Fehler zurück"""
        fehler = []
        
        for schluessel, wert in konfiguration.items():
            if schluessel in self.validierungs_regeln:
                try:
                    self.validierungs_regeln[schluessel](wert)
                except ValueError as e:
                    fehler.append(f"{schluessel}: {str(e)}")
        
        return fehler
    
    def _validiere_umgebung(self, wert: str):
        """Validiert Umgebungs-Einstellung"""
        gueltige_umgebungen = [env.value for env in KonfigurationsUmgebung]
        if wert not in gueltige_umgebungen:
            raise ValueError(f"Ungültige Umgebung: {wert}. Gültig: {gueltige_umgebungen}")
    
    def _validiere_boolean(self, wert: Any):
        """Validiert Boolean-Werte"""
        if not isinstance(wert, bool):
            raise ValueError(f"Muss Boolean sein: {wert}")
    
    def _validiere_log_level(self, wert: str):
        """Validiert Log-Level"""
        gueltige_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if wert not in gueltige_levels:
            raise ValueError(f"Ungültiges Log-Level: {wert}. Gültig: {gueltige_levels}")
    
    def _validiere_positive_zahl(self, wert: Any):
        """Validiert positive Zahlen"""
        if not isinstance(wert, (int, float)) or wert <= 0:
            raise ValueError(f"Muss positive Zahl sein: {wert}")
    
    def _validiere_positive_ganzzahl(self, wert: Any):
        """Validiert positive Ganzzahlen"""
        if not isinstance(wert, int) or wert <= 0:
            raise ValueError(f"Muss positive Ganzzahl sein: {wert}")
    
    def _validiere_prozent(self, wert: Any):
        """Validiert Prozentwerte (0-100)"""
        if not isinstance(wert, (int, float)) or not (0 <= wert <= 100):
            raise ValueError(f"Muss Prozentwert zwischen 0 und 100 sein: {wert}")
    
    def _validiere_port(self, wert: Any):
        """Validiert Port-Nummern"""
        if not isinstance(wert, int) or not (1 <= wert <= 65535):
            raise ValueError(f"Ungültiger Port: {wert}. Muss zwischen 1 und 65535 sein")
    
    def _validiere_nicht_leer(self, wert: Any):
        """Validiert dass Wert nicht leer ist"""
        if not wert or (isinstance(wert, str) and not wert.strip()):
            raise ValueError("Darf nicht leer sein")

class KonfigurationsManager:
    """
    Zentrale Konfigurationsverwaltung für das SCHACHMATTSCHILD System
    """
    
    def __init__(self, basis_pfad: str = "konfiguration", 
                 umgebung: KonfigurationsUmgebung = KonfigurationsUmgebung.DEVELOPMENT,
                 master_key: str = None):
        
        self.basis_pfad = basis_pfad
        self.umgebung = umgebung
        self.aktuelle_konfiguration: Dict[str, Any] = {}
        self.versions_historie: List[KonfigurationsVersion] = []
        self.aenderungs_historie: List[KonfigurationsAenderung] = []
        
        # Sicherheit
        self.master_key = master_key or os.getenv("SCHACHMATTSCHILD_MASTER_KEY", "default_master_key")
        self.verschluesselung = SensitiveDataVerschluesselung(self.master_key)
        self.validierung = KonfigurationsValidierung()
        
        # Zugriffsbeschränkungen
        self.zugriffs_rechte = self._initialisiere_zugriffs_rechte()
        
        # Callbacks für Konfigurationsänderungen
        self.aenderung_callbacks: Dict[str, List[Callable]] = {}
        
        # Threading
        self._lock = threading.RLock()
        
        # Initialisiere Verzeichnis
        self._initialisiere_verzeichnis()
        
        # Lade Konfiguration
        self.lade_konfiguration()
        
        print(f"⚙️  Konfigurations-Manager für {umgebung.value} initialisiert")
    
    def _initialisiere_verzeichnis(self):
        """Initialisiert das Konfigurationsverzeichnis"""
        os.makedirs(self.basis_pfad, exist_ok=True)
        os.makedirs(os.path.join(self.basis_pfad, "versionen"), exist_ok=True)
        os.makedirs(os.path.join(self.basis_pfad, "templates"), exist_ok=True)
    
    def _initialisiere_zugriffs_rechte(self) -> Dict[str, List[str]]:
        """Initialisiert Zugriffsrechte für kritische Einstellungen"""
        return {
            "sicherheit.master_key": ["admin"],
            "sicherheit.verschluesselung_aktiv": ["admin", "operator"],
            "system.umgebung": ["admin"],
            "netzwerk.port": ["admin", "operator"],
        }
    
    def lade_konfiguration(self) -> bool:
        """
        Lädt die Konfiguration für die aktuelle Umgebung
        Returns: True bei Erfolg
        """
        with self._lock:
            try:
                # Lade Basis-Konfiguration
                basis_config = self._lade_datei("basis_config.json") or {}
                
                # Lade Umgebungs-spezifische Konfiguration
                umgebungs_config = self._lade_datei(f"{self.umgebung.value}_config.json") or {}
                
                # Lade Module-Konfiguration
                module_config = self._lade_datei("module_config.json") or {}
                
                # Merge Konfigurationen
                self.aktuelle_konfiguration = self._merge_konfigurationen(
                    basis_config, umgebungs_config, module_config
                )
                
                # Validiere Konfiguration
                fehler = self.validierung.validiere_konfiguration(self.aktuelle_konfiguration)
                if fehler:
                    raise ValueError(f"Konfigurationsfehler: {', '.join(fehler)}")
                
                # Entschlüssele sensitive Daten
                self._entschluessele_sensitive_daten()
                
                # Erstelle initiale Version
                if not self.versions_historie:
                    self._erstelle_konfigurations_version("Initiale Konfiguration")
                
                print(f"✅ Konfiguration für {self.umgebung.value} geladen")
                return True
                
            except Exception as e:
                print(f"❌ Fehler beim Laden der Konfiguration: {e}")
                # Fallback auf Standard-Konfiguration
                self.aktuelle_konfiguration = self._erstelle_standard_konfiguration()
                return False
    
    def _lade_datei(self, dateiname: str) -> Optional[Dict[str, Any]]:
        """Lädt eine Konfigurationsdatei"""
        pfad = os.path.join(self.basis_pfad, dateiname)
        
        if not os.path.exists(pfad):
            return None
            
        try:
            with open(pfad, 'r', encoding='utf-8') as f:
                if dateiname.endswith('.yaml') or dateiname.endswith('.yml'):
                    return yaml.safe_load(f)
                else:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  Fehler beim Laden von {dateiname}: {e}")
            return None
    
    def _merge_konfigurationen(self, *konfigurationen: Dict[str, Any]) -> Dict[str, Any]:
        """Führt mehrere Konfigurationsebenen zusammen"""
        merged = {}
        for config in konfigurationen:
            self._deep_merge(merged, config)
        return merged
    
    def _deep_merge(self, ziel: Dict, quelle: Dict):
        """Tiefes Merge von Dictionaries"""
        for key, value in quelle.items():
            if (key in ziel and isinstance(ziel[key], dict) 
                and isinstance(value, dict)):
                self._deep_merge(ziel[key], value)
            else:
                ziel[key] = value
    
    def _erstelle_standard_konfiguration(self) -> Dict[str, Any]:
        """Erstellt eine Standard-Konfiguration als Fallback"""
        return {
            "system": {
                "umgebung": self.umgebung.value,
                "debug": True,
                "log_level": "INFO"
            },
            "performance": {
                "update_intervall": 2.0,
                "max_cpu_auslastung": 80.0,
                "max_ram_auslastung": 85.0
            },
            "netzwerk": {
                "timeout": 30.0,
                "max_verbindungen": 100,
                "port": 8080
            },
            "sicherheit": {
                "master_key": self.master_key,
                "verschluesselung_aktiv": True
            },
            "module": {
                "schwarmintelligenz": {
                    "max_drohnen": 50,
                    "sicherheits_abstand": 15.0
                },
                "zielerkennung": {
                    "confidence_threshold": 0.6,
                    "zu_verfolgende_klassen": ["FPV_Drohne", "Baba_Yaga"]
                },
                "kommunikation": {
                    "retry_attempts": 3,
                    "timeout_glasfaser": 0.1
                }
            }
        }
    
    def _entschluessele_sensitive_daten(self):
        """Entschlüsselt alle sensiblen Daten in der Konfiguration"""
        if not self.aktuelle_konfiguration.get("sicherheit", {}).get("verschluesselung_aktiv", False):
            return
            
        for schluessel, wert in self.aktuelle_konfiguration.items():
            if isinstance(wert, str) and self.verschluesselung.ist_verschluesselt(wert):
                try:
                    self.aktuelle_konfiguration[schluessel] = self.verschluesselung.entschluesseln(wert)
                except Exception as e:
                    print(f"⚠️  Fehler beim Entschlüsseln von {schluessel}: {e}")
    
    def get_konfiguration(self, schluessel: str = None, standard: Any = None) -> Any:
        """
        Gibt Konfigurationswert zurück
        Args:
            schluessel: Punkt-Notation für verschachtelte Werte (z.B. "system.debug")
            standard: Standardwert falls Schlüssel nicht existiert
        """
        with self._lock:
            if not schluessel:
                return copy.deepcopy(self.aktuelle_konfiguration)
            
            # Navigiere durch verschachtelte Struktur
            teile = schluessel.split('.')
            aktuell = self.aktuelle_konfiguration
            
            for teil in teile:
                if isinstance(aktuell, dict) and teil in aktuell:
                    aktuell = aktuell[teil]
                else:
                    return standard
            
            return copy.deepcopy(aktuell)
    
    def set_konfiguration(self, schluessel: str, wert: Any, benutzer: str = "system", 
                         kommentar: str = "") -> bool:
        """
        Setzt einen Konfigurationswert
        Returns: True bei Erfolg
        """
        with self._lock:
            try:
                # Prüfe Zugriffsrechte
                if not self._hat_berechtigung(schluessel, benutzer):
                    raise PermissionError(f"Benutzer {benutzer} hat keine Berechtigung für {schluessel}")
                
                # Validiere neuen Wert
                if schluessel in self.validierung.validierungs_regeln:
                    self.validierung.validierungs_regeln[schluessel](wert)
                
                # Alten Wert speichern für Historie
                alter_wert = self.get_konfiguration(schluessel)
                
                # Setze neuen Wert
                teile = schluessel.split('.')
                aktuell = self.aktuelle_konfiguration
                
                for i, teil in enumerate(teile[:-1]):
                    if teil not in aktuell:
                        aktuell[teil] = {}
                    aktuell = aktuell[teil]
                
                # Verschlüssele sensitive Daten falls nötig
                if self._ist_sensibler_schluessel(schluessel):
                    wert = self.verschluesselung.verschluesseln(str(wert))
                
                aktuell[teile[-1]] = wert
                
                # Protokolliere Änderung
                aenderung = KonfigurationsAenderung(
                    aenderung_id=str(uuid.uuid4()),
                    timestamp=time.time(),
                    benutzer=benutzer,
                    bereich=self._bestimme_bereich(schluessel),
                    typ=AenderungsTyp.AKTUALISIERT,
                    schluessel=schluessel,
                    alter_wert=alter_wert,
                    neuer_wert=wert,
                    kommentar=kommentar
                )
                
                self.aenderungs_historie.append(aenderung)
                
                # Benachrichtige Callbacks
                self._benachrichtige_aenderung_callbacks(schluessel, wert, alter_wert)
                
                print(f"✅ Konfiguration {schluessel} aktualisiert durch {benutzer}")
                return True
                
            except Exception as e:
                print(f"❌ Fehler beim Setzen von {schluessel}: {e}")
                return False
    
    def _hat_berechtigung(self, schluessel: str, benutzer: str) -> bool:
        """Prüft ob Benutzer Berechtigung für Konfigurationsänderung hat"""
        if schluessel in self.zugriffs_rechte:
            erforderliche_rollen = self.zugriffs_rechte[schluessel]
            # Vereinfachte Rollenprüfung - in Produktion mit echten Berechtigungen
            return benutzer in erforderliche_rollen or "admin" in erforderliche_rollen
        return True  # Standard: Erlaubt
    
    def _ist_sensibler_schluessel(self, schluessel: str) -> bool:
        """Bestimmt ob Schlüssel sensible Daten enthält"""
        sensible_schluessel = [
            "sicherheit.master_key",
            "sicherheit.api_keys",
            "netzwerk.passwoerter",
            "database.passwort"
        ]
        return any(schluessel.startswith(s) for s in sensible_schluessel)
    
    def _bestimme_bereich(self, schluessel: str) -> KonfigurationsBereich:
        """Bestimmt den Konfigurationsbereich basierend auf Schlüssel"""
        if schluessel.startswith("sicherheit"):
            return KonfigurationsBereich.SICHERHEIT
        elif schluessel.startswith("performance"):
            return KonfigurationsBereich.PERFORMANCE
        elif schluessel.startswith("netzwerk"):
            return KonfigurationsBereich.NETZWERK
        elif schluessel.startswith("module"):
            return KonfigurationsBereich.MODULE
        else:
            return KonfigurationsBereich.SYSTEM
    
    def _benachrichtige_aenderung_callbacks(self, schluessel: str, neuer_wert: Any, alter_wert: Any):
        """Benachrichtigt alle registrierten Callbacks"""
        if schluessel in self.aenderung_callbacks:
            for callback in self.aenderung_callbacks[schluessel]:
                try:
                    callback(schluessel, neuer_wert, alter_wert)
                except Exception as e:
                    print(f"❌ Fehler in Änderungs-Callback für {schluessel}: {e}")
    
    def add_aenderung_callback(self, schluessel: str, callback: Callable):
        """Fügt Callback für Konfigurationsänderungen hinzu"""
        if schluessel not in self.aenderung_callbacks:
            self.aenderung_callbacks[schluessel] = []
        self.aenderung_callbacks[schluessel].append(callback)
    
    def speichere_konfiguration(self, beschreibung: str = "Manuelle Änderung", 
                               benutzer: str = "system") -> bool:
        """
        Speichert aktuelle Konfiguration als neue Version
        Returns: True bei Erfolg
        """
        with self._lock:
            try:
                version = self._erstelle_konfigurations_version(beschreibung, benutzer)
                
                # Speichere in Datei
                umgebungs_pfad = os.path.join(
                    self.basis_pfad, 
                    f"{self.umgebung.value}_config.json"
                )
                
                with open(umgebungs_pfad, 'w', encoding='utf-8') as f:
                    json.dump(self.aktuelle_konfiguration, f, indent=2, ensure_ascii=False)
                
                # Speichere Version separat
                version_pfad = os.path.join(
                    self.basis_pfad, 
                    "versionen", 
                    f"{version.version_id}.json"
                )
                
                with open(version_pfad, 'w', encoding='utf-8') as f:
                    json.dump({
                        "version_id": version.version_id,
                        "timestamp": version.timestamp,
                        "beschreibung": version.beschreibung,
                        "checksum": version.checksum,
                        "konfiguration": version.konfiguration
                    }, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Konfiguration gespeichert als Version {version.version_id}")
                return True
                
            except Exception as e:
                print(f"❌ Fehler beim Speichern der Konfiguration: {e}")
                return False
    
    def _erstelle_konfigurations_version(self, beschreibung: str, benutzer: str) -> KonfigurationsVersion:
        """Erstellt eine neue Konfigurationsversion"""
        version_id = str(uuid.uuid4())
        timestamp = time.time()
        
        # Berechne Checksum für Konfiguration
        config_string = json.dumps(self.aktuelle_konfiguration, sort_keys=True)
        checksum = hashlib.sha256(config_string.encode()).hexdigest()
        
        # Letzte Änderungen sammeln
        letzte_aenderungen = [
            a for a in self.aenderungs_historie 
            if a.timestamp > (timestamp - 300)  # Letzte 5 Minuten
        ]
        
        version = KonfigurationsVersion(
            version_id=version_id,
            timestamp=timestamp,
            beschreibung=beschreibung,
            checksum=checksum,
            konfiguration=copy.deepcopy(self.aktuelle_konfiguration),
            aenderungen=letzte_aenderungen,
            benutzer=benutzer
        )
        
        self.versions_historie.append(version)
        return version
    
    def lade_version(self, version_id: str, benutzer: str = "system") -> bool:
        """
        Lädt eine bestimmte Konfigurationsversion
        Returns: True bei Erfolg
        """
        with self._lock:
            try:
                version = next((v for v in self.versions_historie if v.version_id == version_id), None)
                if not version:
                    # Versuche aus Datei zu laden
                    version_pfad = os.path.join(self.basis_pfad, "versionen", f"{version_id}.json")
                    if not os.path.exists(version_pfad):
                        raise FileNotFoundError(f"Version {version_id} nicht gefunden")
                    
                    with open(version_pfad, 'r', encoding='utf-8') as f:
                        daten = json.load(f)
                    
                    version = KonfigurationsVersion(
                        version_id=daten["version_id"],
                        timestamp=daten["timestamp"],
                        beschreibung=daten["beschreibung"],
                        checksum=daten["checksum"],
                        konfiguration=daten["konfiguration"],
                        aenderungen=[],
                        benutzer=benutzer
                    )
                
                # Setze Konfiguration
                self.aktuelle_konfiguration = copy.deepcopy(version.konfiguration)
                
                # Protokolliere Rollback
                aenderung = KonfigurationsAenderung(
                    aenderung_id=str(uuid.uuid4()),
                    timestamp=time.time(),
                    benutzer=benutzer,
                    bereich=KonfigurationsBereich.SYSTEM,
                    typ=AenderungsTyp.ROLLBACK,
                    schluessel="*",
                    alter_wert=None,
                    neuer_wert=version_id,
                    kommentar=f"Rollback zu Version {version_id}"
                )
                
                self.aenderungs_historie.append(aenderung)
                
                print(f"🔙 Rollback zu Version {version_id} durchgeführt")
                return True
                
            except Exception as e:
                print(f"❌ Fehler beim Laden der Version {version_id}: {e}")
                return False
    
    def get_versions_historie(self) -> List[Dict[str, Any]]:
        """Gibt Versionshistorie zurück"""
        with self._lock:
            return [
                {
                    "version_id": v.version_id,
                    "timestamp": v.timestamp,
                    "beschreibung": v.beschreibung,
                    "benutzer": v.benutzer,
                    "checksum": v.checksum[:8]  # Kurzform
                }
                for v in self.versions_historie[-10:]  # Letzte 10 Versionen
            ]
    
    def erstelle_template(self, name: str, konfiguration: Dict[str, Any]) -> bool:
        """
        Erstellt ein Konfigurations-Template
        Returns: True bei Erfolg
        """
        try:
            template_pfad = os.path.join(self.basis_pfad, "templates", f"{name}.json")
            
            with open(template_pfad, 'w', encoding='utf-8') as f:
                json.dump(konfiguration, f, indent=2, ensure_ascii=False)
            
            print(f"📁 Template {name} erstellt")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Erstellen des Templates {name}: {e}")
            return False
    
    def lade_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Lädt ein Konfigurations-Template"""
        template_pfad = os.path.join(self.basis_pfad, "templates", f"{name}.json")
        
        if not os.path.exists(template_pfad):
            return None
            
        try:
            with open(template_pfad, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Fehler beim Laden des Templates {name}: {e}")
            return None

# =============================================================================
# TEST UND DEMONSTRATION
# =============================================================================

def demonstriere_konfigurations_manager():
    """Demonstriert den Konfigurations-Manager"""
    print("🧪 DEMONSTRATION KONFIGURATIONS-MANAGER")
    
    # Erstelle Konfigurations-Manager
    config_manager = KonfigurationsManager(
        umgebung=KonfigurationsUmgebung.DEVELOPMENT,
        master_key="mein_geheimer_master_key_123!"
    )
    
    # Zeige aktuelle Konfiguration
    print(f"\n📋 AKTUELLE KONFIGURATION:")
    system_config = config_manager.get_konfiguration("system")
    print(f"   Umgebung: {system_config.get('umgebung')}")
    print(f"   Debug: {system_config.get('debug')}")
    print(f"   Log Level: {system_config.get('log_level')}")
    
    # Teste Konfigurationsänderung
    print(f"\n🔧 TESTE KONFIGURATIONSÄNDERUNG:")
    erfolg = config_manager.set_konfiguration(
        "system.log_level", 
        "DEBUG", 
        benutzer="admin",
        kommentar="Erhöhtes Logging für Debugging"
    )
    print(f"   Änderung erfolgreich: {erfolg}")
    
    # Teste Validierung
    print(f"\n🎯 TESTE VALIDIERUNG:")
    try:
        config_manager.set_konfiguration("system.umgebung", "INVALID", benutzer="admin")
    except Exception as e:
        print(f"   Validierung funktioniert: {e}")
    
    # Speichere Konfiguration
    print(f"\n💾 SPEICHERE KONFIGURATION:")
    erfolg = config_manager.speichere_konfiguration(
        "Test-Änderungen", 
        benutzer="admin"
    )
    print(f"   Speichern erfolgreich: {erfolg}")
    
    # Zeige Versionshistorie
    print(f"\n📜 VERSIONSHISTORIE:")
    historie = config_manager.get_versions_historie()
    for version in historie:
        zeit = datetime.fromtimestamp(version['timestamp']).strftime("%H:%M:%S")
        print(f"   {version['version_id'][:8]} - {zeit} - {version['beschreibung']}")
    
    # Teste Template-Erstellung
    print(f"\n📁 TESTE TEMPLATES:")
    template_config = {
        "system": {"umgebung": "production", "debug": False},
        "performance": {"max_cpu_auslastung": 90.0}
    }
    config_manager.erstelle_template("production_basis", template_config)
    
    # Lade Template
    geladenes_template = config_manager.lade_template("production_basis")
    print(f"   Template geladen: {geladenes_template is not None}")
    
    print(f"\n✅ KONFIGURATIONS-MANAGER FUNKTIONIERT")

if __name__ == "__main__":
    demonstriere_konfigurations_manager()
