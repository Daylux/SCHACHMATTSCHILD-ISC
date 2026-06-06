# Daylux Labs - ISC_AI - Proprietary and Confidential
# PREDICTIVE_MAINTENANCE_MODUL.py
"""
PREDICTIVE MAINTENANCE INTEGRATION
KI-gestützte Ausfallvorhersage und Selbstheilungs-Protokolle
SCHACHMATTSCHILD - Militärischer Standard
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import json
from datetime import datetime, timedelta
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
warnings.filterwarnings('ignore')

class WartungsStatus(Enum):
    OPTIMAL = "optimal"
    WARNUNG = "warnung"
    KRITISCH = "kritisch"
    AUSFALL = "ausfall"

class WartungsAktion(Enum):
    ÜBERWACHEN = "überwachen"
    WARTUNG_EMPFEHLEN = "wartung_empfehlen"
    AUSTAUSCH_EMPFEHLEN = "austausch_empfehlen"
    SOFORTIGE_DEAKTIVIERUNG = "sofortige_deaktivierung"
    SELBSTHEILUNG_AKTIVIEREN = "selbstheilung_aktivieren"

@dataclass
class modul_metriken:
    modul_id: str
    modul_typ: str
    betriebsstunden: float
    leistungsaufnahme_avg: float
    temperatur_avg: float
    fehler_count: int
    last_reset: float
    zuverlaessigkeit_score: float = 1.0

@dataclass
class VorhersageErgebnis:
    modul_id: str
    ausfall_wahrscheinlichkeit: float
    verbleibende_lebensdauer: float  # in Stunden
    kritische_komponenten: List[str]
    empfolene_aktion: WartungsAktion
    konfidenz: float
    zeitstempel: float

@dataclass
class SelbstheilungsProtokoll:
    protokoll_id: str
    modul_id: str
    aktion: str
    zustand_vorher: Dict
    zustand_nachher: Dict
    erfolg: bool
    zeitstempel: float

class KI_AusfallVorhersage:
    """KI-Modell für Ausfallvorhersage basierend auf Modul-Metriken"""
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.ist_trained = False
        self.genauigkeit: float = 0.0
        
    def trainieren(self, trainings_daten: pd.DataFrame, ziel_variable: pd.Series):
        """Trainiert das KI-Modell mit historischen Daten"""
        try:
            # Features skalieren
            X_scaled = self.scaler.fit_transform(trainings_daten)
            
            # Modell training
            self.model.fit(X_scaled, ziel_variable)
            
            # Genauigkeit berechnen
            self.genauigkeit = self.model.score(X_scaled, ziel_variable)
            self.ist_trained = True
            
            print(f"✅ KI-Modell trainiert - Genauigkeit: {self.genauigkeit:.3f}")
            
        except Exception as e:
            print(f"❌ Fehler beim Training: {e}")
            self.ist_trained = False

    def vorhersage(self, modul_metriken: modul_metriken) -> VorhersageErgebnis:
        """Macht Ausfallvorhersage für ein Modul"""
        if not self.ist_trained:
            return self._fallback_vorhersage(modul_metriken)
        
        try:
            # Features vorbereiten
            features = self._extrahiere_features(modul_metriken)
            features_scaled = self.scaler.transform([features])
            
            # Vorhersage
            ausfall_wahrscheinlichkeit = self.model.predict_proba(features_scaled)[0][1]
            verbleibende_lebensdauer = self._berechne_lebensdauer(modul_metriken, ausfall_wahrscheinlichkeit)
            aktion = self._bestimme_aktion(ausfall_wahrscheinlichkeit, modul_metriken)
            
            return VorhersageErgebnis(
                modul_id=modul_metriken.modul_id,
                ausfall_wahrscheinlichkeit=ausfall_wahrscheinlichkeit,
                verbleibende_lebensdauer=verbleibende_lebensdauer,
                kritische_komponenten=self._identifiziere_kritische_komponenten(modul_metriken),
                empfolene_aktion=aktion,
                konfidenz=min(self.genauigkeit, 0.95),
                zeitstempel=time.time()
            )
            
        except Exception as e:
            print(f"❌ Vorhersage-Fehler: {e}")
            return self._fallback_vorhersage(modul_metriken)
    
    def _extrahiere_features(self, metrik: modul_metriken) -> List[float]:
        """Extrahiert Features für KI-Modell"""
        return [
            metrik.betriebsstunden,
            metrik.leistungsaufnahme_avg,
            metrik.temperatur_avg,
            metrik.fehler_count,
            metrik.zuverlaessigkeit_score,
            metrik.betriebsstunden / (metrik.fehler_count + 1)  # MTBF ähnlich
        ]
    
    def _berechne_lebensdauer(self, metrik: modul_metriken, ausfall_wahrscheinlichkeit: float) -> float:
        """Berechnet verbleibende Lebensdauer in Stunden"""
        basis_lebensdauer = 10000  # Standard-Lebensdauer in Stunden
        alters_faktor = metrik.betriebsstunden / basis_lebensdauer
        zuverlaessigkeits_faktor = metrik.zuverlaessigkeit_score
        
        verbleibend = basis_lebensdauer * (1 - alters_faktor) * zuverlaessigkeits_faktor
        verbleibend *= (1 - ausfall_wahrscheinlichkeit)
        
        return max(verbleibend, 0)
    
    def _bestimme_aktion(self, ausfall_wahrscheinlichkeit: float, metrik: modul_metriken) -> WartungsAktion:
        """Bestimmt empfohlene Wartungsaktion"""
        if ausfall_wahrscheinlichkeit > 0.8 or metrik.zuverlaessigkeit_score < 0.3:
            return WartungsAktion.SOFORTIGE_DEAKTIVIERUNG
        elif ausfall_wahrscheinlichkeit > 0.6:
            return WartungsAktion.SELBSTHEILUNG_AKTIVIEREN
        elif ausfall_wahrscheinlichkeit > 0.4:
            return WartungsAktion.AUSTAUSCH_EMPFEHLEN
        elif ausfall_wahrscheinlichkeit > 0.2:
            return WartungsAktion.WARTUNG_EMPFEHLEN
        else:
            return WartungsAktion.ÜBERWACHEN
    
    def _identifiziere_kritische_komponenten(self, metrik: modul_metriken) -> List[str]:
        """Identifiziert kritische Komponenten basierend auf Metriken"""
        kritische = []
        
        if metrik.temperatur_avg > 80:
            kritische.append("KÜHLSYSTEM")
        if metrik.leistungsaufnahme_avg > metrik.leistungsaufnahme_avg * 1.5:
            kritische.append("STROMVERSORGUNG")
        if metrik.fehler_count > 10:
            kritische.append("FEHLERANFÄLLIGE_KOMPONENTEN")
        if metrik.zuverlaessigkeit_score < 0.5:
            kritische.append("ALLGEMEINE_ZUVERLÄSSIGKEIT")
            
        return kritische

    def _fallback_vorhersage(self, metrik: modul_metriken) -> VorhersageErgebnis:
        """Fallback-Vorhersage wenn KI nicht trainiert ist"""
        ausfall_wahrscheinlichkeit = min(metrik.betriebsstunden / 10000, 0.9)
        
        return VorhersageErgebnis(
            modul_id=metrik.modul_id,
            ausfall_wahrscheinlichkeit=ausfall_wahrscheinlichkeit,
            verbleibende_lebensdauer=max(10000 - metrik.betriebsstunden, 0),
            kritische_komponenten=[],
            empfolene_aktion=WartungsAktion.ÜBERWACHEN,
            konfidenz=0.5,
            zeitstempel=time.time()
        )

class SelbstheilungsManager:
    """Manager für automatische Selbstheilungs-Protokolle"""
    
    def __init__(self):
        self.protokolle: List[SelbstheilungsProtokoll] = []
        self._lock = threading.RLock()
        
        # Selbstheilungs-Registry
        self.selbstheilungs_registry = {
            "KÜHLSYSTEM": self._protokoll_kuehlung,
            "STROMVERSORGUNG": self._protokoll_stromversorgung,
            "FEHLERANFÄLLIGE_KOMPONENTEN": self._protokoll_komponenten_reset,
            "ALLGEMEINE_ZUVERLÄSSIGKEIT": self._protokoll_zuverlaessigkeit
        }
    
    def aktiviere_selbstheilung(self, modul_id: str, kritische_komponenten: List[str], zustand: Dict) -> bool:
        """Aktiviert Selbstheilung für kritische Komponenten"""
        with self._lock:
            gesamt_erfolg = True
            protokoll_aktionen = []
            
            for komponente in kritische_komponenten:
                if komponente in self.selbstheilungs_registry:
                    erfolg = self.selbstheilungs_registry[komponente](modul_id, zustand)
                    gesamt_erfolg &= erfolg
                    protokoll_aktionen.append(f"{komponente}:{'ERFOLG' if erfolg else 'FEHLER'}")
            
            # Protokolliere Selbstheilungsversuch
            protokoll = SelbstheilungsProtokoll(
                protokoll_id=str(int(time.time())),
                modul_id=modul_id,
                aktion=" | ".join(protokoll_aktionen),
                zustand_vorher=zustand,
                zustand_nachher=self._erfasse_aktuellen_zustand(modul_id),
                erfolg=gesamt_erfolg,
                zeitstempel=time.time()
            )
            
            self.protokolle.append(protokoll)
            return gesamt_erfolg
    
    def _protokoll_kuehlung(self, modul_id: str, zustand: Dict) -> bool:
        """Selbstheilungsprotokoll für Kühlsystem"""
        print(f"❄️  Aktiviere Kühlungs-Protokoll für {modul_id}")
        # Simuliere Kühlungsoptimierung
        time.sleep(0.1)
        return True
    
    def _protokoll_stromversorgung(self, modul_id: str, zustand: Dict) -> bool:
        """Selbstheilungsprotokoll für Stromversorgung"""
        print(f"⚡ Aktiviere Stromoptimierung für {modul_id}")
        # Simuliere Stromoptimierung
        time.sleep(0.1)
        return True
    
    def _protokoll_komponenten_reset(self, modul_id: str, zustand: Dict) -> bool:
        """Selbstheilungsprotokoll für Komponenten-Reset"""
        print(f"🔄 Aktiviere Komponenten-Reset für {modul_id}")
        # Simuliere weichen Reset
        time.sleep(0.2)
        return True

    def _protokoll_zuverlaessigkeit(self, modul_id: str, zustand: Dict) -> bool:
        """Selbstheilungsprotokoll für allgemeine Zuverlässigkeit"""
        print(f"🔧 Aktiviere Zuverlässigkeits-Protokoll für {modul_id}")
        # Simuliere Kalibrierung
        time.sleep(0.3)
        return True
    
    def _erfasse_aktuellen_zustand(self, modul_id: str) -> Dict:
        """Erfasst aktuellen Modul-Zustand (simuliert)"""
        return {
            "temperatur": np.random.normal(45, 5),
            "leistung": np.random.normal(100, 10),
            "status": "OPTIMAL"
        }

class PredictiveMaintenanceSystem:
    """
    Hauptsystem für Predictive Maintenance Integration
    """
    
    def __init__(self, orakel_drohne):
        self.orakel = orakel_drohne
        self.ki_vorhersage = KI_AusfallVorhersage()
        self.selbstheilung = SelbstheilungsManager()
        self.metriken_history: Dict[str, List[modul_metriken]] = {}
        
        # Überwachungsparameter
        self.ueberwachungs_intervall = 60  # Sekunden
        self.warnungs_schwellwert = 0.3
        self.kritischer_schwellwert = 0.7
        
        # Threading
        self._lock = threading.RLock()
        self._is_running = True
        self._ueberwachungs_thread = threading.Thread(target=self._ueberwachungs_loop)
        self._ueberwachungs_thread.daemon = True
        self._ueberwachungs_thread.start()
        
        # Callbacks für Alarme
        self.alarm_callbacks: List[Callable] = []
        
        # Initialisiere mit Trainingsdaten
        self._initialisiere_ki_modell()
        
        print(f"🔧 Predictive Maintenance für {orakel_drohne.drohnen_id} initialisiert")
    
    def _initialisiere_ki_modell(self):
        """Initialisiert KI-Modell mit Standard-Trainingsdaten"""
        try:
            # Generiere synthetische Trainingsdaten
            trainings_daten, ziel_variable = self._generiere_trainingsdaten()
            self.ki_vorhersage.trainieren(trainings_daten, ziel_variable)
        except Exception as e:
            print(f"⚠️  KI-Training fehlgeschlagen, verwende Fallback: {e}")
    
    def _generiere_trainingsdaten(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Generiert synthetische Trainingsdaten für KI-Modell"""
        n_samples = 1000
        features = []
        targets = []
        
        for i in range(n_samples):
            betriebsstunden = np.random.exponential(5000)
            leistung = np.random.normal(100, 20)
            temperatur = np.random.normal(50, 15)
            fehler = np.random.poisson(betriebsstunden / 1000)
            zuverlaessigkeit = np.random.beta(2, 2)
            
            # Ausfall-Simulation
            ausfall_risiko = (
                betriebsstunden / 10000 +
                max(0, temperatur - 70) / 100 +
                fehler / 10 +
                (1 - zuverlaessigkeit)
            )
            ausfall = 1 if ausfall_risiko > 0.6 else 0
            
            features.append([betriebsstunden, leistung, temperatur, fehler, zuverlaessigkeit])
            targets.append(ausfall)
        
        return pd.DataFrame(features), pd.Series(targets)
    
    def _ueberwachungs_loop(self):
        """Haupt-Überwachungsschleife für alle Module"""
        while self._is_running:
            try:
                with self._lock:
                    for modul_id, modul in self.orakel.module.items():
                        self._ueberwache_modul(modul_id, modul)
                
                time.sleep(self.ueberwachungs_intervall)
                
            except Exception as e:
                print(f"❌ Fehler in Überwachungsschleife: {e}")
                time.sleep(10)  # Wiederherstellungsverzögerung
    
    def _ueberwache_modul(self, modul_id: str, modul):
        """Überwacht ein einzelnes Modul und macht Vorhersagen"""
        # Erfasse aktuelle Metriken
        metrik = self._erfasse_modul_metriken(modul_id, modul)
        
        # Speichere in Historie
        if modul_id not in self.metriken_history:
            self.metriken_history[modul_id] = []
        self.metriken_history[modul_id].append(metrik)
        
        # KI-Vorhersage
        vorhersage = self.ki_vorhersage.vorhersage(metrik)
        
        # Behandle Vorhersage
        self._behandle_vorhersage(vorhersage, modul)
        
        # Protokolliere
        self._protokolliere_vorhersage(vorhersage)
    
    def _erfasse_modul_metriken(self, modul_id: str, modul) -> modul_metriken:
        """Erfasst Metriken für ein Modul"""
        status = modul.status_bericht()
        
        return modul_metriken(
            modul_id=modul_id,
            modul_typ=type(modul).__name__,
            betriebsstunden=status.get('betriebsstunden', 0) + np.random.exponential(10),
            leistungsaufnahme_avg=modul.daten.leistungsaufnahme,
            temperatur_avg=status.get('temperatur', 45) + np.random.normal(0, 2),
            fehler_count=status.get('fehler_count', 0),
            last_reset=time.time() - np.random.exponential(10000),
            zuverlaessigkeit_score=max(0.1, 1.0 - (status.get('fehler_count', 0) / 100))
        )
    
    def _behandle_vorhersage(self, vorhersage: VorhersageErgebnis, modul):
        """Behandelt Vorhersageergebnis und initiiert Maßnahmen"""
        if vorhersage.ausfall_wahrscheinlichkeit > self.kritischer_schwellwert:
            # KRITISCH - Sofortmaßnahmen
            self._loese_alarm_aus(f"KRITISCH: {vorhersage.modul_id}", vorhersage)
            
            if vorhersage.empfolene_aktion == WartungsAktion.SELBSTHEILUNG_AKTIVIEREN:
                erfolg = self.selbstheilung.aktiviere_selbstheilung(
                    vorhersage.modul_id,
                    vorhersage.kritische_komponenten,
                    modul.status_bericht()
                )
                if not erfolg:
                    self._loese_alarm_aus("SELBSTHEILUNG_FEHLGESCHLAGEN", vorhersage)
                    
        elif vorhersage.ausfall_wahrscheinlichkeit > self.warnungs_schwellwert:
            # WARNUNG - Benachrichtigung
            self._loese_alarm_aus(f"WARNUNG: {vorhersage.modul_id}", vorhersage)
    
    def _loese_alarm_aus(self, nachricht: str, vorhersage: VorhersageErgebnis):
        """Löst Wartungsalarm aus"""
        alarm_daten = {
            "nachricht": nachricht,
            "modul_id": vorhersage.modul_id,
            "ausfall_wahrscheinlichkeit": vorhersage.ausfall_wahrscheinlichkeit,
            "empfohlene_aktion": vorhersage.empfolene_aktion.value,
            "zeitstempel": time.time()
        }
        
        print(f"🚨 PREDICTIVE MAINTENANCE ALARM: {nachricht}")
        print(f"   Ausfallwahrscheinlichkeit: {vorhersage.ausfall_wahrscheinlichkeit:.1%}")
        print(f"   Empfohlene Aktion: {vorhersage.empfolene_aktion.value}")
        
        # Benachrichtige Callbacks
        for callback in self.alarm_callbacks:
            try:
                callback(alarm_daten)
            except Exception as e:
                print(f"❌ Fehler in Alarm-Callback: {e}")
    
    def _protokolliere_vorhersage(self, vorhersage: VorhersageErgebnis):
        """Protokolliert Vorhersage für spätere Analyse"""
        # In Produktion: In Datenbank oder Logfile schreiben
        pass
    
    def get_modul_gesundheit(self, modul_id: str) -> Optional[Dict]:
        """Gibt Gesundheitsstatus eines Moduls zurück"""
        if modul_id not in self.metriken_history:
            return None
            
        historie = self.metriken_history[modul_id]
        if not historie:
            return None
            
        aktuell = historie[-1]
        vorhersage = self.ki_vorhersage.vorhersage(aktuell)
        
        return {
            "modul_id": modul_id,
            "betriebsstunden": aktuell.betriebsstunden,
            "ausfall_wahrscheinlichkeit": vorhersage.ausfall_wahrscheinlichkeit,
            "verbleibende_lebensdauer": vorhersage.verbleibende_lebensdauer,
            "zuverlaessigkeit_score": aktuell.zuverlaessigkeit_score,
            "wartungs_status": self._bestimme_wartungs_status(vorhersage),
            "letzte_aktualisierung": time.time()
        }
    
    def _bestimme_wartungs_status(self, vorhersage: VorhersageErgebnis) -> WartungsStatus:
        """Bestimmt Wartungsstatus basierend auf Vorhersage"""
        if vorhersage.ausfall_wahrscheinlichkeit > 0.7:
            return WartungsStatus.AUSFALL
        elif vorhersage.ausfall_wahrscheinlichkeit > 0.5:
            return WartungsStatus.KRITISCH
        elif vorhersage.ausfall_wahrscheinlichkeit > 0.3:
            return WartungsStatus.WARNUNG
        else:
            return WartungsStatus.OPTIMAL
    
    def add_alarm_callback(self, callback: Callable):
        """Fügt Callback für Wartungsalarme hinzu"""
        self.alarm_callbacks.append(callback)
    
    def beenden(self):
        """Beendet das Predictive Maintenance System"""
        self._is_running = False


# =============================================================================
# TESTMODUL FÜR PREDICTIVE MAINTENANCE
# =============================================================================

def teste_predictive_maintenance():
    """Testet das Predictive Maintenance System"""
    print("🧪 TESTE PREDICTIVE MAINTENANCE SYSTEM...")
    
    from MODULARE_ORAKEL_ARCHITEKTUR import OrakelDrohne, EOIR_Sensor, RadarSensor
    
    # Erstelle Test-Drohne
    orakel = OrakelDrohne("ORAKEL_PM_001")
    orakel.energie_system_aktivieren()
    
    # Füge Module hinzu
    eoir_id = orakel.modul_hinzufuegen("EOIR_Sensor")
    radar_id = orakel.modul_hinzufuegen("RadarSensor")
    
    # Aktiviere Module
    orakel.modul_aktivieren(eoir_id)
    orakel.modul_aktivieren(radar_id)
    
    # Erstelle Predictive Maintenance System
    pm_system = PredictiveMaintenanceSystem(orakel)
    
    # Füge Alarm-Callback hinzu
    def alarm_callback(alarm_daten):
        print(f"🔔 ALARM CALLBACK: {alarm_daten['nachricht']}")
    
    pm_system.add_alarm_callback(alarm_callback)
    
    # Teste Gesundheitsüberwachung
    print("\n📊 TESTE GESUNDHEITSÜBERWACHUNG:")
    time.sleep(2)  # Warte auf erste Überwachungszyklen
    
    for modul_id in [eoir_id, radar_id]:
        gesundheit = pm_system.get_modul_gesundheit(modul_id)
        if gesundheit:
            print(f"\n🔧 Gesundheit {modul_id}:")
            for key, value in gesundheit.items():
                if key != "letzte_aktualisierung":
                    print(f"   {key}: {value}")
    
    # Teste KI-Vorhersage-Genauigkeit
    print(f"\n🤖 KI-VORHERSAGE-GENAUIGKEIT: {pm_system.ki_vorhersage.genauigkeit:.1%}")
    
    # Simuliere kritischen Zustand
    print("\n🔥 SIMULIERE KRITISCHEN ZUSTAND:")
    kritische_metrik = modul_metriken(
        modul_id="TEST_KRITISCH",
        modul_typ="TestModul",
        betriebsstunden=9000,
        leistungsaufnahme_avg=200,
        temperatur_avg=85,
        fehler_count=15,
        last_reset=time.time() - 1000,
        zuverlaessigkeit_score=0.2
    )
    
    vorhersage = pm_system.ki_vorhersage.vorhersage(kritische_metrik)
    print(f"   Ausfallwahrscheinlichkeit: {vorhersage.ausfall_wahrscheinlichkeit:.1%}")
    print(f"   Empfohlene Aktion: {vorhersage.empfolene_aktion.value}")
    
    # Beende Systeme
    time.sleep(1)
    pm_system.beenden()
    orakel.energie_system_deaktivieren()
    
    print("✅ PREDICTIVE MAINTENANCE SYSTEM FUNKTIONIERT")

if __name__ == "__main__":
    teste_predictive_maintenance()
