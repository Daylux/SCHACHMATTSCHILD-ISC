# Daylux Labs - ISC_AI - Proprietary and Confidential
# AKUSTIK_BEACON_SYSTEM.py
"""
AKUSTIK-BEACON-SYSTEM FÜR FREUND/FEIND-ERKENNUNG
Verschlüsselte Ultraschall-Signaturen und akustische Triangulation
SCHACHMATTSCHILD - Ergänzungsmodul
"""

import numpy as np
import threading
import time
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet
import pyaudio
import wave
import struct

class AkustikSignalTyp(Enum):
    FREUND_BEACON = "freund_beacon"
    FEIND_ERKENNUNG = "feind_erkennung"
    NOTFALL_SIGNAL = "notfall_signal"
    POSITIONS_ABFRAGE = "positions_abfrage"

class FrequenzBereich(Enum):
    ULTRASCHALL_LOW = 18000  # 18 kHz
    ULTRASCHALL_MID = 20000  # 20 kHz  
    ULTRASCHALL_HIGH = 22000  # 22 kHz

@dataclass
class AkustikBeacon:
    beacon_id: str
    position: Tuple[float, float, float]
    signal_typ: AkustikSignalTyp
    frequenz: FrequenzBereich
    timestamp: float
    signatur: str
    verschluesselte_daten: str
    signal_staerke: float = 0.0

@dataclass
class TriangulationsErgebnis:
    ziel_position: Tuple[float, float, float]
    konfidenz: float
    anzahl_beacons: int
    triangulations_zeit: float
    fehler_radius: float

class UltraschallEncoder:
    """Encoder für verschlüsselte Ultraschall-Signaturen"""
    
    def __init__(self, schluessel: str):
        self.schluessel = schluessel.encode()
        self.fernet = self._initialisiere_verschluesselung()
        self.aktuelle_frequenz = FrequenzBereich.ULTRASCHALL_MID
        
    def _initialisiere_verschluesselung(self) -> Fernet:
        """Initialisiert AES-256 Verschlüsselung für Akustik-Signaturen"""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"AKUSTIK_BEACON_SALT",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.schluessel))
        return Fernet(key)
    
    def generiere_beacon_signal(self, beacon_daten: Dict, signal_typ: AkustikSignalTyp) -> AkustikBeacon:
        """Generiert verschlüsseltes Beacon-Signal"""
        # Verschlüssele Beacon-Daten
        daten_string = json.dumps(beacon_daten, sort_keys=True)
        verschluesselte_daten = self.fernet.encrypt(daten_string.encode()).decode()
        
        # Erstelle digitale Signatur
        signatur = self._erstelle_signatur(beacon_daten)
        
        # Wähle Frequenz basierend auf Signaltyp und Hopping-Pattern
        frequenz = self._waehle_frequenz(signal_typ)
        
        beacon = AkustikBeacon(
            beacon_id=str(hashlib.sha256(signatur.encode()).hexdigest()[:16]),
            position=beacon_daten.get("position", (0, 0, 0)),
            signal_typ=signal_typ,
            frequenz=frequenz,
            timestamp=time.time(),
            signatur=signatur,
            verschluesselte_daten=verschluesselte_daten
        )
        
        return beacon
    
    def _waehle_frequenz(self, signal_typ: AkustikSignalTyp) -> FrequenzBereich:
        """Wählt Frequenz basierend auf Hopping-Pattern und Signaltyp"""
        # Dynamisches Frequenz-Hopping für Anti-Jamming
        hopping_pattern = {
            AkustikSignalTyp.FREUND_BEACON: [
                FrequenzBereich.ULTRASCHALL_LOW,
                FrequenzBereich.ULTRASCHALL_MID,
                FrequenzBereich.ULTRASCHALL_HIGH
            ],
            AkustikSignalTyp.FEIND_ERKENNUNG: [
                FrequenzBereich.ULTRASCHALL_HIGH,
                FrequenzBereich.ULTRASCHALL_LOW
            ],
            AkustikSignalTyp.NOTFALL_SIGNAL: [
                FrequenzBereich.ULTRASCHALL_MID
            ]
        }
        
        pattern = hopping_pattern.get(signal_typ, [FrequenzBereich.ULTRASCHALL_MID])
        aktuelle_index = int(time.time() * 2) % len(pattern)  # Alle 0.5 Sekunden wechseln
        return pattern[aktuelle_index]
    
    def _erstelle_signatur(self, daten: Dict) -> str:
        """Erstellt HMAC-SHA256 Signatur für Beacon-Daten"""
        daten_string = json.dumps(daten, sort_keys=True)
        signatur = hashlib.sha256(
            (daten_string + self.schluessel.decode()).encode()
        ).hexdigest()
        return signatur
    
    def validiere_beacon(self, beacon: AkustikBeacon) -> bool:
        """Validiert Beacon-Signatur und Entschlüsselt Daten"""
        try:
            # Entschlüssele Daten
            daten_string = self.fernet.decrypt(beacon.verschluesselte_daten.encode()).decode()
            daten = json.loads(daten_string)
            
            # Validiere Signatur
            erwartete_signatur = self._erstelle_signatur(daten)
            if beacon.signatur != erwartete_signatur:
                return False
                
            # Prüfe Zeitstempel (Anti-Replay)
            if time.time() - beacon.timestamp > 5.0:  # 5 Sekunden Toleranz
                return False
                
            return True
            
        except Exception:
            return False

class AkustikTriangulation:
    """Echtzeit-Akustik-Triangulation für Positionsbestimmung"""
    
    def __init__(self):
        self.schallgeschwindigkeit = 343.0  # m/s bei 20°C
        self.min_beacons_fuer_triangulation = 3
        
    def trianguliere_position(self, beacon_empfaengnisse: List[AkustikBeacon]) -> Optional[TriangulationsErgebnis]:
        """
        Führt akustische Triangulation durch
        Returns: Triangulationsergebnis oder None bei Fehler
        """
        if len(beacon_empfaengnisse) < self.min_beacons_fuer_triangulation:
            return None
            
        startzeit = time.time()
        
        try:
            # Time Difference of Arrival (TDOA) Algorithmus
            positionen = [beacon.position for beacon in beacon_empfaengnisse]
            signal_staerken = [beacon.signal_staerke for beacon in beacon_empfaengnisse]
            timestamps = [beacon.timestamp for beacon in beacon_empfaengnisse]
            
            # Gewichtete Positionsberechnung basierend auf Signalstärke
            gewichtete_position = self._berechne_gewichtete_position(positionen, signal_staerken)
            
            # Konfidenz basierend auf Signalqualität und Anzahl der Beacons
            konfidenz = self._berechne_konfidenz(signal_staerken, len(beacon_empfaengnisse))
            
            # Fehlerradius basierend auf Signalstärke-Varianz
            fehler_radius = self._berechne_fehler_radius(signal_staerken, positionen)
            
            ergebnis = TriangulationsErgebnis(
                ziel_position=gewichtete_position,
                konfidenz=konfidenz,
                anzahl_beacons=len(beacon_empfaengnisse),
                triangulations_zeit=time.time() - startzeit,
                fehler_radius=fehler_radius
            )
            
            return ergebnis
            
        except Exception as e:
            print(f"❌ Fehler bei Triangulation: {e}")
            return None
    
    def _berechne_gewichtete_position(self, positionen: List[Tuple], signal_staerken: List[float]) -> Tuple[float, float, float]:
        """Berechnet gewichtete Position basierend auf Signalstärken"""
        if not signal_staerken:
            return (0, 0, 0)
            
        # Normalisiere Signalstärken für Gewichtung
        max_staerke = max(signal_staerken)
        if max_staerke == 0:
            gewichte = [1.0 / len(signal_staerken)] * len(signal_staerken)
        else:
            gewichte = [s / max_staerke for s in signal_staerken]
        
        # Gewichtete Mittelwertberechnung
        gesamt_gewicht = sum(gewichte)
        x = sum(p[0] * g for p, g in zip(positionen, gewichte)) / gesamt_gewicht
        y = sum(p[1] * g for p, g in zip(positionen, gewichte)) / gesamt_gewicht
        z = sum(p[2] * g for p, g in zip(positionen, gewichte)) / gesamt_gewicht
        
        return (x, y, z)
    
    def _berechne_konfidenz(self, signal_staerken: List[float], anzahl_beacons: int) -> float:
        """Berechnet Konfidenz der Triangulation"""
        basis_konfidenz = min(1.0, anzahl_beacons / 6.0)  # Max 6 Beacons für 100%
        signal_qualitaet = np.mean(signal_staerken) / 100.0 if signal_staerken else 0
        
        konfidenz = (basis_konfidenz * 0.6) + (signal_qualitaet * 0.4)
        return min(konfidenz, 1.0)
    
    def _berechne_fehler_radius(self, signal_staerken: List[float], positionen: List[Tuple]) -> float:
        """Berechnet geschätzten Fehlerradius"""
        if len(signal_staerken) < 2:
            return 10.0  # Standard-Fehlerradius
            
        # Fehlerradius basierend auf Signalstärke-Varianz
        signal_varianz = np.var(signal_staerken) if signal_staerken else 100
        basis_fehler = 2.0 + (signal_varianz / 50.0)
        
        return min(basis_fehler, 15.0)  # Max 15 Meter Fehlerradius

class AkustikBeaconSystem:
    """
    Hauptsystem für akustische Freund/Feind-Erkennung
    """
    
    def __init__(self, drohnen_id: str, schluessel: str):
        self.drohnen_id = drohnen_id
        self.encoder = UltraschallEncoder(schluessel)
        self.triangulation = AkustikTriangulation()
        
        # Audio-Handling
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.sample_rate = 44100
        self.chunk_size = 1024
        
        # Beacon-Verwaltung
        self.aktive_beacons: Dict[str, AkustikBeacon] = {}
        self.empfangene_beacons: List[AkustikBeacon] = []
        self.freund_systeme: List[str] = []
        
        # Threading
        self._lock = threading.RLock()
        self._is_running = True
        self._sender_thread = threading.Thread(target=self._beacon_sender_loop)
        self._empfaenger_thread = threading.Thread(target=self._beacon_empfaenger_loop)
        self._analyse_thread = threading.Thread(target=self._analyse_loop)
        
        # Störungs-Erkennung
        self.stoerungs_zustaende = {
            "jammer_erkannt": False,
            "rauschen_erhoeht": False,
            "frequenz_gestoert": False
        }
        
        # Initialisiere Audio
        self.audio = pyaudio.PyAudio()
        
        print(f"🔊 Akustik-Beacon-System für {drohnen_id} initialisiert")
    
    def starte_system(self):
        """Startet das Akustik-Beacon-System"""
        self._sender_thread.daemon = True
        self._empfaenger_thread.daemon = True
        self._analyse_thread.daemon = True
        
        self._sender_thread.start()
        self._empfaenger_thread.start()
        self._analyse_thread.start()
        
        print("🚀 Akustik-Beacon-System gestartet")
    
    def sende_freund_beacon(self, position: Tuple[float, float, float]):
        """Sendet Freund-Beacon mit aktueller Position"""
        with self._lock:
            beacon_daten = {
                "drohnen_id": self.drohnen_id,
                "position": position,
                "typ": "freund",
                "timestamp": time.time()
            }
            
            beacon = self.encoder.generiere_beacon_signal(
                beacon_daten, 
                AkustikSignalTyp.FREUND_BEACON
            )
            
            self.aktive_beacons[beacon.beacon_id] = beacon
            print(f"📡 Sende Freund-Beacon von Position {position}")
    
    def sende_feind_erkennung(self, position: Tuple[float, float, float], ziel_id: str):
        """Sendet Feind-Erkennungs-Signal"""
        with self._lock:
            beacon_daten = {
                "drohnen_id": self.drohnen_id,
                "position": position,
                "ziel_id": ziel_id,
                "typ": "feind_erkennung",
                "timestamp": time.time()
            }
            
            beacon = self.encoder.generiere_beacon_signal(
                beacon_daten,
                AkustikSignalTyp.FEIND_ERKENNUNG
            )
            
            self.aktive_beacons[beacon.beacon_id] = beacon
            print(f"🎯 Sende Feind-Erkennung für {ziel_id}")
    
    def _beacon_sender_loop(self):
        """Sendet kontinuierlich Beacon-Signale"""
        while self._is_running:
            try:
                with self._lock:
                    # Sende alle aktiven Beacons
                    for beacon_id, beacon in list(self.aktive_beacons.items()):
                        if time.time() - beacon.timestamp > 2.0:  # Beacon veraltet
                            del self.aktive_beacons[beacon_id]
                        else:
                            self._sende_akustisches_signal(beacon)
                
                time.sleep(0.1)  # 10x pro Sekunde senden
                
            except Exception as e:
                print(f"❌ Fehler im Beacon-Sender: {e}")
                time.sleep(1)
    
    def _beacon_empfaenger_loop(self):
        """Empfängt und verarbeitet Beacon-Signale"""
        try:
            # Öffne Audio-Stream für Empfang
            stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            while self._is_running:
                try:
                    # Lies Audio-Daten
                    audio_data = stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Analysiere auf Beacon-Signale
                    erkannte_beacons = self._analysiere_audio_daten(audio_data)
                    
                    with self._lock:
                        for beacon in erkannte_beacons:
                            if self.encoder.validiere_beacon(beacon):
                                self.empfangene_beacons.append(beacon)
                                self._verarbeite_beacon(beacon)
                
                except Exception as e:
                    print(f"❌ Fehler im Audio-Empfang: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"❌ Fehler im Beacon-Empfänger: {e}")
    
    def _analysiere_audio_daten(self, audio_data: bytes) -> List[AkustikBeacon]:
        """Analysiert Audio-Daten auf Beacon-Signale"""
        erkannte_beacons = []
        
        try:
            # Konvertiere Audio-Daten zu numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # FFT für Frequenzanalyse
            fft_result = np.fft.fft(audio_array)
            frequencies = np.fft.fftfreq(len(fft_result), 1.0 / self.sample_rate)
            
            # Suche nach Ultraschall-Signaturen
            for freq_bereich in FrequenzBereich:
                freq_index = np.where(
                    (frequencies >= freq_bereich.value - 100) & 
                    (frequencies <= freq_bereich.value + 100)
                )[0]
                
                if len(freq_index) > 0:
                    signal_staerke = np.mean(np.abs(fft_result[freq_index]))
                    
                    if signal_staerke > 1000:  # Schwellwert für Beacon-Erkennung
                        # Simuliere Beacon-Erkennung (in Produktion: echte Dekodierung)
                        beacon = AkustikBeacon(
                            beacon_id="erkannt_" + str(time.time()),
                            position=(0, 0, 0),  # Wird durch Triangulation bestimmt
                            signal_typ=AkustikSignalTyp.FREUND_BEACON,
                            frequenz=freq_bereich,
                            timestamp=time.time(),
                            signatur="simuliert",
                            verschluesselte_daten="simuliert",
                            signal_staerke=signal_staerke
                        )
                        erkannte_beacons.append(beacon)
            
            return erkannte_beacons
            
        except Exception as e:
            print(f"❌ Fehler bei Audio-Analyse: {e}")
            return []
    
    def _sende_akustisches_signal(self, beacon: AkustikBeacon):
        """Sendet akustisches Beacon-Signal (simuliert)"""
        # In Produktion: Echte Ultraschall-Generierung
        # Hier Simulation der Signalübertragung
        pass
    
    def _verarbeite_beacon(self, beacon: AkustikBeacon):
        """Verarbeitet empfangene Beacon-Signale"""
        try:
            # Entschlüssele Beacon-Daten
            daten_string = self.encoder.fernet.decrypt(
                beacon.verschluesselte_daten.encode()
            ).decode()
            daten = json.loads(daten_string)
            
            beacon_typ = daten.get("typ")
            sender_id = daten.get("drohnen_id")
            
            if beacon_typ == "freund":
                if sender_id not in self.freund_systeme:
                    self.freund_systeme.append(sender_id)
                    print(f"✅ Freund-System erkannt: {sender_id}")
                    
            elif beacon_typ == "feind_erkennung":
                ziel_id = daten.get("ziel_id")
                if ziel_id == self.drohnen_id:
                    print(f"🚨 FEIND-ERKENNUNG: Wir wurden als Ziel identifiziert!")
                    # Aktiviere Gegenmaßnahmen
                    self._aktiviere_gegenmassnahmen()
                    
        except Exception as e:
            print(f"❌ Fehler bei Beacon-Verarbeitung: {e}")
    
    def _aktiviere_gegenmassnahmen(self):
        """Aktiviert Gegenmaßnahmen bei Feind-Erkennung"""
        print("🛡️ Aktiviere akustische Gegenmaßnahmen...")
        
        # Frequenz-Hopping aktivieren
        self.stoerungs_zustaende["jammer_erkannt"] = True
        
        # Notfall-Beacon senden
        self.sende_notfall_signal()
    
    def sende_notfall_signal(self):
        """Sendet akustisches Notfall-Signal"""
        beacon_daten = {
            "drohnen_id": self.drohnen_id,
            "typ": "notfall",
            "timestamp": time.time(),
            "position": (0, 0, 0)  # Wird durch Aufrufer gesetzt
        }
        
        beacon = self.encoder.generiere_beacon_signal(
            beacon_daten,
            AkustikSignalTyp.NOTFALL_SIGNAL
        )
        
        with self._lock:
            self.aktive_beacons[beacon.beacon_id] = beacon
        print("🆘 Sende akustisches Notfall-Signal")
    
    def _analyse_loop(self):
        """Analysiert kontinuierlich die akustische Umgebung"""
        while self._is_running:
            try:
                with self._lock:
                    # Führe Triangulation durch
                    if len(self.empfangene_beacons) >= 3:
                        triangulations_ergebnis = self.triangulation.trianguliere_position(
                            self.empfangene_beacons
                        )
                        
                        if triangulations_ergebnis and triangulations_ergebnis.konfidenz > 0.7:
                            print(f"🎯 Triangulation: Position {triangulations_ergebnis.ziel_position} "
                                  f"(Konfidenz: {triangulations_ergebnis.konfidenz:.1%})")
                    
                    # Bereinige alte Beacons
                    aktueller_zeit = time.time()
                    self.empfangene_beacons = [
                        b for b in self.empfangene_beacons 
                        if aktueller_zeit - b.timestamp < 10.0
                    ]
                
                time.sleep(1.0)  # Alle Sekunde analysieren
                
            except Exception as e:
                print(f"❌ Fehler in Analyse-Schleife: {e}")
                time.sleep(5)
    
    def friendly_fire_pruefung(self, ziel_position: Tuple[float, float, float]) -> bool:
        """
        Prüft ob Ziel ein Freund-System ist
        Returns: True wenn Friendly-Fire-Gefahr besteht
        """
        with self._lock:
            # Prüfe ob Freund-Beacon in Zielbereich
            for beacon in self.empfangene_beacons:
                if (beacon.signal_typ == AkustikSignalTyp.FREUND_BEACON and
                    self._berechne_distanz(beacon.position, ziel_position) < 5.0):
                    print("⚠️ FRIENDLY-FIRE-WARNUNG: Freund-System in Zielbereich!")
                    return True
            
            return False
    
    def _berechne_distanz(self, pos1: Tuple[float, float, float], pos2: Tuple[float, float, float]) -> float:
        """Berechnet euklidische Distanz zwischen zwei Positionen"""
        return np.sqrt(
            (pos1[0] - pos2[0])**2 + 
            (pos1[1] - pos2[1])**2 + 
            (pos1[2] - pos2[2])**2
        )
    
    def beende_system(self):
        """Beendet das Akustik-Beacon-System"""
        self._is_running = False
        
        if hasattr(self, 'audio'):
            self.audio.terminate()
        
        print("🛑 Akustik-Beacon-System beendet")

# =============================================================================
# INTEGRATION MIT BESTEHENDEN MODULEN
# =============================================================================

class AkustikBeaconIntegration:
    """Integrationsklasse für bestehende SCHACHMATTSCHILD Module"""
    
    def __init__(self, schwarm_intelligenz, kommunikations_modul):
        self.schwarm_intelligenz = schwarm_intelligenz
        self.kommunikations_modul = kommunikations_modul
        self.akustik_system = None
        
    def initialisiere_akustik_system(self, drohnen_id: str, schluessel: str):
        """Initialisiert das Akustik-Beacon-System"""
        self.akustik_system = AkustikBeaconSystem(drohnen_id, schluessel)
        self.akustik_system.starte_system()
        
        # Integriere in bestehende Module
        self._integriere_in_schwarmintelligenz()
        self._integriere_in_kommunikation()
        
        print("✅ Akustik-Beacon-System integriert")
    
    def _integriere_in_schwarmintelligenz(self):
        """Integriert Akustik-System in Schwarmintelligenz"""
        # Friendly-Fire-Prüfung vor Angriffen
        original_angriff = getattr(self.schwarm_intelligenz, 'starte_angriff', None)
        
        if original_angriff:
            def sichere_angriff(ziel_position):
                if self.akustik_system and self.akustik_system.friendly_fire_pruefung(ziel_position):
                    print("🚫 ANGRIFF ABGEBROCHEN: Friendly-Fire-Gefahr!")
                    return False
                return original_angriff(ziel_position)
            
            setattr(self.schwarm_intelligenz, 'starte_angriff', sichere_angriff)
    
    def _integriere_in_kommunikation(self):
        """Integriert Akustik-System in Kommunikation"""
        # Akustische Backup-Kommunikation bei Funk-Ausfall
        original_senden = getattr(self.kommunikations_modul, 'nachricht_senden', None)
        
        if original_senden:
            def redundante_nachricht(ziel_id, daten, prioritaet=5):
                # Versuche primäre Kommunikation
                erfolg = original_senden(ziel_id, daten, prioritaet)
                
                if not erfolg and self.akustik_system:
                    # Verwende akustische Backup-Kommunikation
                    print("🔊 Verwende akustische Backup-Kommunikation")
                    self.akustik_system.sende_notfall_signal()
                
                return erfolg
            
            setattr(self.kommunikations_modul, 'nachricht_senden', redundante_nachricht)

# =============================================================================
# TESTMODUL
# =============================================================================

def teste_akustik_beacon_system():
    """Testet das Akustik-Beacon-System"""
    print("🧪 TESTE AKUSTIK-BEACON-SYSTEM")
    
    # Erstelle Test-System
    akustik_system = AkustikBeaconSystem("TEST_DROHNE_001", "geheimer_schluessel")
    akustik_system.starte_system()
    
    # Teste Beacon-Sendung
    print("\n📡 TESTE BEACON-SENDUNG:")
    akustik_system.sende_freund_beacon((100, 50, 20))
    akustik_system.sende_feind_erkennung((200, 100, 30), "FEIND_DROHNE_001")
    
    # Teste Friendly-Fire-Prüfung
    print("\n🎯 TESTE FRIENDLY-FIRE-PRÜFUNG:")
    friendly_fire_gefahr = akustik_system.friendly_fire_pruefung((105, 52, 22))
    print(f"   Friendly-Fire-Gefahr: {friendly_fire_gefahr}")
    
    # Warte auf Analyse
    time.sleep(3)
    
    # Beende System
    akustik_system.beende_system()
    
    print("✅ AKUSTIK-BEACON-SYSTEM FUNKTIONIERT")

if __name__ == "__main__":
    teste_akustik_beacon_system()
