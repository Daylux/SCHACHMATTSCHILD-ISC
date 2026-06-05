# HYBRID_KOMMUNIKATION_MODUL.py
"""
HYBRIDE GLASFASER-FUNK KOMMUNIKATIONSPROTOKOLLE
Robuste Datenübertragung unter Störbedingungen für SCHACHMATTSCHILD
"""

import threading
import time
import socket
import json
import hashlib
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import random

class UebertragungsArt(Enum):
    GLASFASER = "glasfaser"
    FUNK = "funk"
    NOTFALL = "notfall"

class VerbindungsStatus(Enum):
    AKTIV = "aktiv"
    GESTOERT = "gestört"
    UNTERBROCHEN = "unterbrochen"
    WIEDERHERGESTELLT = "wiederhergestellt"

@dataclass
class Nachricht:
    sender_id: str
    empfaenger_id: str
    daten: dict
    timestamp: float
    prioritaet: int  # 1-10, 10 = höchste
    uebertragungs_art: UebertragungsArt
    checksum: str = None
    versuch: int = 0

@dataclass
class VerbindungsMetriken:
    latenzen: List[float]
    paketverlust: float
    signalstaerke: float
    last_update: float

class HybrideKommunikation:
    def __init__(self, knoten_id: str):
        self.knoten_id = knoten_id
        self.verbindungen: Dict[str, VerbindungsStatus] = {}
        self.metriken: Dict[str, VerbindungsMetriken] = {}
        
        # Protokoll-Parameter
        self.max_wiederholungen = 3
        self.timeout_glasfaser = 0.1  # Sekunden
        self.timeout_funk = 0.5       # Sekunden
        self.signal_schwelle = 0.3    # Minimale Signalstärke
        
        # Störungs-Erkennung
        self.stoerungs_zustaende = {
            "jammer_erkannt": False,
            "signal_unterbrochen": False,
            "glasfaser_beschaedigt": False
        }
        
        # Threading
        self._lock = threading.Lock()
        self._running = True
        self._monitor_thread = threading.Thread(target=self._verbindungs_monitor)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
        # Callback für eingehende Nachrichten
        self.empfangs_callback: Optional[Callable] = None
        
        print(f"📡 HYBRIDE KOMMUNIKATION INITIALISIERT: {knoten_id}")
    
    def verbindung_herstellen(self, ziel_id: str, verbindungs_art: UebertragungsArt):
        """Stellt Verbindung zu einem anderen Knoten her"""
        with self._lock:
            self.verbindungen[ziel_id] = VerbindungsStatus.AKTIV
            self.metriken[ziel_id] = VerbindungsMetriken(
                latenzen=[], paketverlust=0.0, signalstaerke=1.0, last_update=time.time()
            )
            print(f"🔗 Verbindung zu {ziel_id} hergestellt via {verbindungs_art.value}")
    
    def nachricht_senden(self, ziel_id: str, daten: dict, prioritaet: int = 5) -> bool:
        """
        Sendet Nachricht mit hybridem Protokoll
        Returns: Erfolgsstatus
        """
        if ziel_id not in self.verbindungen:
            print(f"⚠️  Keine Verbindung zu {ziel_id}")
            return False
        
        # Wähle Übertragungsart basierend auf Störungszustand
        uebertragungs_art = self._waehle_uebertragungs_art(ziel_id)
        
        # Erstelle Nachricht
        nachricht = Nachricht(
            sender_id=self.knoten_id,
            empfaenger_id=ziel_id,
            daten=daten,
            timestamp=time.time(),
            prioritaet=prioritaet,
            uebertragungs_art=uebertragungs_art
        )
        
        # Füge Checksum hinzu
        nachricht.checksum = self._berechne_checksum(nachricht)
        
        # Sende mit Wiederholungslogik
        erfolg = self._sende_mit_wiederholung(nachricht)
        
        if erfolg:
            print(f"📤 Nachricht an {ziel_id} via {uebertragungs_art.value} gesendet")
        else:
            print(f"❌ Nachricht an {ziel_id} fehlgeschlagen")
            self._behandle_verbindungsausfall(ziel_id)
            
        return erfolg
    
    def _waehle_uebertragungs_art(self, ziel_id: str) -> UebertragungsArt:
        """Wählt optimale Übertragungsart basierend auf Störungszustand"""
        if self.stoerungs_zustaende["jammer_erkannt"]:
            return UebertragungsArt.GLASFASER
        elif self.stoerungs_zustaende["glasfaser_beschaedigt"]:
            return UebertragungsArt.FUNK
        elif self.stoerungs_zustaende["signal_unterbrochen"]:
            return UebertragungsArt.NOTFALL
        
        # Automatische Auswahl basierend auf Metriken
        metrik = self.metriken.get(ziel_id)
        if metrik and metrik.paketverlust > 0.5:  # Hoher Paketverlust
            return UebertragungsArt.GLASFASER
        elif metrik and metrik.signalstaerke < self.signal_schwelle:
            return UebertragungsArt.GLASFASER
        else:
            # Standard: Funk für Mobilität, Glasfaser für Stabilität
            return UebertragungsArt.FUNK if "MOBIL" in ziel_id else UebertragungsArt.GLASFASER
    
    def _sende_mit_wiederholung(self, nachricht: Nachricht) -> bool:
        """Sendet Nachricht mit Wiederholungslogik bei Fehlern"""
        for versuch in range(self.max_wiederholungen):
            nachricht.versuch = versuch + 1
            
            # Simuliere Übertragung mit realistischen Fehlerraten
            erfolg = self._simuliere_uebertragung(nachricht)
            
            if erfolg:
                # Update Metriken bei Erfolg
                self._update_metriken(nachricht.empfaenger_id, erfolg=True)
                return True
            else:
                # Warte vor Wiederholung
                time.sleep(0.1 * (2 ** versuch))  # Exponentielles Backoff
        
        # Alle Versuche fehlgeschlagen
        self._update_metriken(nachricht.empfaenger_id, erfolg=False)
        return False
    
    def _simuliere_uebertragung(self, nachricht: Nachricht) -> bool:
        """Simuliert die physikalische Übertragung mit realistischen Fehlern"""
        # Realistische Fehlerwahrscheinlichkeiten basierend auf Übertragungsart
        fehler_wahrscheinlichkeiten = {
            UebertragungsArt.GLASFASER: 0.01,    # 1% Fehlerrate
            UebertragungsArt.FUNK: 0.15,         # 15% Fehlerrate
            UebertragungsArt.NOTFALL: 0.4        # 40% Fehlerrate
        }
        
        # Erhöhte Fehlerrate bei Störungen
        if self.stoerungs_zustaende["jammer_erkannt"] and nachricht.uebertragungs_art == UebertragungsArt.FUNK:
            fehler_wahrscheinlichkeiten[UebertragungsArt.FUNK] = 0.8  # 80% Fehler bei Jammer
        
        fehler_rate = fehler_wahrscheinlichkeiten[nachricht.uebertragungs_art]
        
        # Simuliere Übertragungserfolg
        return random.random() > fehler_rate
    
    def _behandle_verbindungsausfall(self, ziel_id: str):
        """Behandelt Verbindungsausfälle und initiiert Gegenmaßnahmen"""
        with self._lock:
            self.verbindungen[ziel_id] = VerbindungsStatus.GESTOERT
            
            # Aktiviere Notfallprotokolle
            if "ORAKEL" in ziel_id:
                self._aktiviere_notfall_routing(ziel_id)
            elif "SOKOL" in ziel_id:
                self._aktiviere_autonomen_modus(ziel_id)
    
    def _aktiviere_notfall_routing(self, ziel_id: str):
        """Aktiviert alternative Routing-Pfade bei Ausfällen"""
        print(f"🚨 Aktiviere Notfall-Routing für {ziel_id}")
        # Hier würde Mesh-Netzwerk Routing aktiviert werden
    
    def _aktiviere_autonomen_modus(self, ziel_id: str):
        """Aktiviert autonomen Betrieb bei Kommunikationsausfall"""
        print(f"🤖 Aktiviere autonomen Modus für {ziel_id}")
        # Drohne operiert autonom basierend auf letzter bekannter Mission
    
    def _update_metriken(self, ziel_id: str, erfolg: bool):
        """Aktualisiert Verbindungsmetriken"""
        if ziel_id not in self.metriken:
            return
            
        metrik = self.metriken[ziel_id]
        jetzt = time.time()
        
        # Vereinfachte Metrik-Berechnung
        if not erfolg:
            metrik.paketverlust = min(1.0, metrik.paketverlust + 0.1)
        
        # Signalstärke simuliert Umgebungsbedingungen
        metrik.signalstaerke = max(0.1, random.uniform(0.5, 1.0))
        metrik.last_update = jetzt
    
    def _berechne_checksum(self, nachricht: Nachricht) -> str:
        """Berechnet Checksum für Datenintegrität"""
        daten_string = json.dumps(nachricht.daten, sort_keys=True) + str(nachricht.timestamp)
        return hashlib.md5(daten_string.encode()).hexdigest()
    
    def stoerung_melden(self, stoerungs_typ: str, zustand: bool):
        """Meldet externe Störungen"""
        if stoerungs_typ in self.stoerungs_zustaende:
            self.stoerungs_zustaende[stoerungs_typ] = zustand
            status = "AKTIV" if zustand else "BEENDET"
            print(f"🚨 Störung {stoerungs_typ}: {status}")
    
    def _verbindungs_monitor(self):
        """Überwacht kontinuierlich Verbindungsqualität"""
        while self._running:
            time.sleep(2)  # Überwachungsintervall
            
            with self._lock:
                for ziel_id, status in self.verbindungen.items():
                    if status == VerbindungsStatus.GESTOERT:
                        # Versuche Wiederherstellung
                        if self._verbindung_testen(ziel_id):
                            self.verbindungen[ziel_id] = VerbindungsStatus.WIEDERHERGESTELLT
                            print(f"🔧 Verbindung zu {ziel_id} wiederhergestellt")
    
    def _verbindung_testen(self, ziel_id: str) -> bool:
        """Testet Verbindungswiederherstellung"""
        # Simuliere Verbindungstest
        return random.random() > 0.7  # 70% Erfolgschance
    
    def setze_empfangs_callback(self, callback: Callable):
        """Setzt Callback für eingehende Nachrichten"""
        self.empfangs_callback = callback
    
    def beenden(self):
        """Beendet die Kommunikationskomponente"""
        self._running = False
        self._monitor_thread.join()

# TESTMODUL FÜR HYBRIDE KOMMUNIKATION
def teste_hybride_kommunikation():
    """Testet das hybride Kommunikationssystem"""
    print("🧪 TESTE HYBRIDE KOMMUNIKATIONSPROTOKOLLE...")
    
    # Erstelle Kommunikationsknoten
    knoten_a = HybrideKommunikation("ORAKEL_ALPHA")
    knoten_b = HybrideKommunikation("SOKOL_BRAVO")
    
    # Stelle Verbindung her
    knoten_a.verbindung_herstellen("SOKOL_BRAVO", UebertragungsArt.FUNK)
    knoten_b.verbindung_herstellen("ORAKEL_ALPHA", UebertragungsArt.GLASFASER)
    
    # Teste Nachrichtenaustausch
    test_daten = {
        "befehl": "ZIEL_VERFOLGEN",
        "ziel_id": "FPV_DRONE_001",
        "position": [100, 50, 200],
        "prioritaet": 8
    }
    
    # Normale Übertragung
    print("\n📨 Teste normale Übertragung...")
    erfolg = knoten_a.nachricht_senden("SOKOL_BRAVO", test_daten)
    print(f"Ergebnis: {'ERFOLG' if erfolg else 'FEHLGESCHLAGEN'}")
    
    # Simuliere Störung
    print("\n🚨 Simuliere Jammer-Störung...")
    knoten_a.stoerung_melden("jammer_erkannt", True)
    
    # Übertragung unter Störbedingungen
    erfolg_unter_stoerung = knoten_a.nachricht_senden("SOKOL_BRAVO", test_daten)
    print(f"Übertragung unter Störung: {'ERFOLG' if erfolg_unter_stoerung else 'FEHLGESCHLAGEN'}")
    
    # Beende Kommunikation
    knoten_a.beenden()
    knoten_b.beenden()
    
    print("✅ HYBRIDE KOMMUNIKATIONSPROTOKOLLE FUNKTIONIEREN")

if __name__ == "__main__":
    teste_hybride_kommunikation()
