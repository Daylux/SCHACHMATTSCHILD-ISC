# LEISTUNGS_MONITOR.py
"""
ECHIZEIT-LEISTUNGSMONITOR FÜR SCHACHMATTSCHILD SYSTEM
Überwacht Performance, Ressourcen und Latenzen aller 8 Kernmodule
"""

import time
import threading
import psutil
import numpy as np
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import statistics
import queue

class LeistungsStatus(Enum):
    OPTIMAL = "optimal"
    NORMAL = "normal"
    WARNUNG = "warnung"
    KRITISCH = "kritisch"
    AUSFALL = "ausfall"

class MetrikTyp(Enum):
    LATENZ = "latenz"
    CPU = "cpu"
    RAM = "ram"
    NETZWERK = "netzwerk"
    ENERGIE = "energie"
    FEHLER = "fehler"

@dataclass
class LeistungsMetrik:
    typ: MetrikTyp
    wert: float
    einheit: str
    timestamp: float
    modul: str = "system"
    schwellwert: Optional[float] = None

@dataclass
class PerformanceSnapshot:
    timestamp: float
    module_metriken: Dict[str, List[LeistungsMetrik]]
    system_metriken: Dict[str, float]
    warnungen: List[str]

@dataclass
class TrendAnalyse:
    modul: str
    metrik_typ: MetrikTyp
    trend: str  # "steigend", "fallend", "stabil"
    aenderungs_rate: float  # Prozent pro Stunde
    vorhersage: Optional[float] = None
    empfehlung: Optional[str] = None

class EchtzeitLeistungsMonitor:
    """
    Echtzeit-Leistungsmonitor für das SCHACHMATTSCHILD System
    """
    
    def __init__(self, update_intervall: float = 2.0, historie_stunden: int = 24):
        self.update_intervall = update_intervall
        self.historie_stunden = historie_stunden
        
        # Datenstrukturen
        self.leistungs_daten: List[PerformanceSnapshot] = []
        self.metrik_historie: Dict[str, List[LeistungsMetrik]] = {}
        self.aktive_warnungen: List[str] = []
        
        # Schwellwerte für Warnungen
        self.schwellwerte = {
            "cpu_auslastung": 80.0,  # %
            "ram_auslastung": 85.0,  # %
            "latenz_kritisch": 0.1,  # Sekunden (100ms)
            "latenz_warnung": 0.05,  # Sekunden (50ms)
            "netzwerk_verlust": 10.0,  # % Paketverlust
            "energie_verbrauch": 120.0  # Watt
        }
        
        # Modul-spezifische Performance-Ziele
        self.modul_ziele = {
            "schwarmintelligenz": {"latenz": 0.05, "cpu": 15.0},
            "zielerkennung": {"latenz": 0.1, "cpu": 25.0},
            "kommunikation": {"latenz": 0.02, "cpu": 10.0},
            "orakel_architektur": {"latenz": 0.01, "cpu": 5.0},
            "dynamische_konfig": {"latenz": 0.03, "cpu": 8.0},
            "predictive_maintenance": {"latenz": 0.2, "cpu": 12.0},
            "remote_hotswap": {"latenz": 0.15, "cpu": 18.0},
            "simulator": {"latenz": 0.08, "cpu": 20.0}
        }
        
        # Threading und Steuerung
        self._lock = threading.RLock()
        self._is_running = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop)
        self._monitor_thread.daemon = True
        
        # Callbacks für Warnungen und Dashboards
        self.warnung_callbacks: List[Callable] = []
        self.dashboard_callbacks: List[Callable] = []
        
        # Statistik
        self.startzeit = time.time()
        self.gesamt_metriken = 0
        
        # Initialisiere Logging
        self._setup_logging()
        
        print(f"📊 Echtzeit-Leistungsmonitor initialisiert (Update: {update_intervall}s)")
    
    def _setup_logging(self):
        """Konfiguriert Performance-Logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('leistungs_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('LeistungsMonitor')
    
    def start_monitoring(self):
        """Startet das kontinuierliche Monitoring"""
        self._monitor_thread.start()
        self.logger.info("🚀 Leistungsmonitoring gestartet")
    
    def _monitoring_loop(self):
        """Haupt-Monitoring-Schleife"""
        while self._is_running:
            try:
                with self._lock:
                    snapshot = self._erfasse_performance_snapshot()
                    self.leistungs_daten.append(snapshot)
                    
                    # Analysiere und generiere Warnungen
                    self._analysiere_performance(snapshot)
                    
                    # Datenbereinigung (alte Einträge entfernen)
                    self._bereinige_alte_daten()
                    
                    # Callbacks aufrufen
                    self._aktualisiere_dashboards(snapshot)
                
                time.sleep(self.update_intervall)
                
            except Exception as e:
                self.logger.error(f"Fehler in Monitoring-Schleife: {e}")
                time.sleep(5)  # Wiederherstellungsverzögerung
    
    def _erfasse_performance_snapshot(self) -> PerformanceSnapshot:
        """Erfasst einen kompletten Performance-Snapshot"""
        timestamp = time.time()
        module_metriken = {}
        system_metriken = self._erfasse_system_metriken()
        
        # Modul-spezifische Metriken (simuliert - in Produktion echte Messungen)
        for modul_name in self.modul_ziele.keys():
            module_metriken[modul_name] = self._erfasse_modul_metriken(modul_name)
        
        return PerformanceSnapshot(
            timestamp=timestamp,
            module_metriken=module_metriken,
            system_metriken=system_metriken,
            warnungen=[]
        )
    
    def _erfasse_system_metriken(self) -> Dict[str, float]:
        """Erfasst System-weite Metriken"""
        try:
            # CPU Auslastung
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # RAM Auslastung
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            ram_used_gb = ram.used / (1024**3)
            
            # Netzwerk (vereinfacht)
            netzwerk = psutil.net_io_counters()
            netzwerk_sent_mb = netzwerk.bytes_sent / (1024**2)
            netzwerk_recv_mb = netzwerk.bytes_recv / (1024**2)
            
            # Energie (simuliert - in Produktion Hardware-Messung)
            energie_verbrauch = 45.0 + (cpu_percent * 0.5)  # Simulation
            
            return {
                "cpu_percent": cpu_percent,
                "ram_percent": ram_percent,
                "ram_used_gb": ram_used_gb,
                "netzwerk_sent_mb": netzwerk_sent_mb,
                "netzwerk_recv_mb": netzwerk_recv_mb,
                "energie_verbrauch_w": energie_verbrauch,
                "prozesse_aktiv": len(psutil.pids())
            }
            
        except Exception as e:
            self.logger.error(f"Fehler beim Erfassen System-Metriken: {e}")
            return {}
    
    def _erfasse_modul_metriken(self, modul_name: str) -> List[LeistungsMetrik]:
        """Erfasst Modul-spezifische Performance-Metriken"""
        metrik_liste = []
        timestamp = time.time()
        
        try:
            # Simulierte Modul-Metriken (in Produktion: echte Messungen)
            if modul_name == "schwarmintelligenz":
                # Latenz für Schwarmberechnungen
                latenz = max(0.01, np.random.normal(0.03, 0.01))
                cpu_usage = np.random.normal(12.0, 3.0)
                
                metrik_liste.extend([
                    LeistungsMetrik(MetrikTyp.LATENZ, latenz, "s", timestamp, modul_name, 0.05),
                    LeistungsMetrik(MetrikTyp.CPU, cpu_usage, "%", timestamp, modul_name, 15.0)
                ])
                
            elif modul_name == "zielerkennung":
                # Latenz für Bildanalyse
                latenz = max(0.05, np.random.normal(0.08, 0.02))
                cpu_usage = np.random.normal(20.0, 5.0)
                
                metrik_liste.extend([
                    LeistungsMetrik(MetrikTyp.LATENZ, latenz, "s", timestamp, modul_name, 0.1),
                    LeistungsMetrik(MetrikTyp.CPU, cpu_usage, "%", timestamp, modul_name, 25.0)
                ])
                
            elif modul_name == "kommunikation":
                # Latenz für Nachrichtenübertragung
                latenz = max(0.005, np.random.normal(0.015, 0.005))
                netzwerk_usage = np.random.normal(5.0, 2.0)
                
                metrik_liste.extend([
                    LeistungsMetrik(MetrikTyp.LATENZ, latenz, "s", timestamp, modul_name, 0.02),
                    LeistungsMetrik(MetrikTyp.NETZWERK, netzwerk_usage, "MB/s", timestamp, modul_name, 10.0)
                ])
                
            # Weitere Module ähnlich...
            else:
                # Generische Metriken für andere Module
                latenz = max(0.01, np.random.normal(0.05, 0.02))
                cpu_usage = np.random.normal(10.0, 3.0)
                
                metrik_liste.extend([
                    LeistungsMetrik(MetrikTyp.LATENZ, latenz, "s", timestamp, modul_name),
                    LeistungsMetrik(MetrikTyp.CPU, cpu_usage, "%", timestamp, modul_name)
                ])
            
            # Speichere in Historie
            for metrik in metrik_liste:
                key = f"{modul_name}_{metrik.typ.value}"
                if key not in self.metrik_historie:
                    self.metrik_historie[key] = []
                self.metrik_historie[key].append(metrik)
                self.gesamt_metriken += 1
                
        except Exception as e:
            self.logger.error(f"Fehler beim Erfassen von {modul_name}: {e}")
            
        return metrik_liste
    
    def _analysiere_performance(self, snapshot: PerformanceSnapshot):
        """Analysiert Performance und generiert Warnungen"""
        warnungen = []
        
        # System-weite Warnungen
        system_metriken = snapshot.system_metriken
        
        if system_metriken.get("cpu_percent", 0) > self.schwellwerte["cpu_auslastung"]:
            warnungen.append(f"🚨 CPU-Auslastung kritisch: {system_metriken['cpu_percent']:.1f}%")
            
        if system_metriken.get("ram_percent", 0) > self.schwellwerte["ram_auslastung"]:
            warnungen.append(f"🚨 RAM-Auslastung kritisch: {system_metriken['ram_percent']:.1f}%")
        
        # Modul-spezifische Warnungen
        for modul_name, metriken in snapshot.module_metriken.items():
            for metrik in metriken:
                if metrik.schwellwert and metrik.wert > metrik.schwellwert:
                    warnungen.append(
                        f"⚠️ {modul_name} {metrik.typ.value}: {metrik.wert:.3f}{metrik.einheit} "
                        f"(Schwellwert: {metrik.schwellwert}{metrik.einheit})"
                    )
        
        # Füge neue Warnungen hinzu
        for warnung in warnungen:
            if warnung not in self.aktive_warnungen:
                self.aktive_warnungen.append(warnung)
                self._loese_warnung_aus(warnung)
        
        # Entferne veraltete Warnungen
        self.aktive_warnungen = [w for w in self.aktive_warnungen if w in warnungen]
        snapshot.warnungen = warnungen
    
    def _loese_warnung_aus(self, warnung: str):
        """Löst Warnungen über Callbacks aus"""
        self.logger.warning(warnung)
        
        for callback in self.warnung_callbacks:
            try:
                callback(warnung)
            except Exception as e:
                self.logger.error(f"Fehler in Warnungs-Callback: {e}")
    
    def _aktualisiere_dashboards(self, snapshot: PerformanceSnapshot):
        """Aktualisiert Dashboards über Callbacks"""
        dashboard_daten = self._generiere_dashboard_daten(snapshot)
        
        for callback in self.dashboard_callbacks:
            try:
                callback(dashboard_daten)
            except Exception as e:
                self.logger.error(f"Fehler in Dashboard-Callback: {e}")
    
    def _generiere_dashboard_daten(self, snapshot: PerformanceSnapshot) -> Dict[str, Any]:
        """Generiert Daten für Echtzeit-Dashboards"""
        return {
            "timestamp": snapshot.timestamp,
            "system_metriken": snapshot.system_metriken,
            "aktive_warnungen": snapshot.warnungen,
            "modul_status": {
                modul: {
                    "latenz": next((m.wert for m in metriken if m.typ == MetrikTyp.LATENZ), 0),
                    "cpu": next((m.wert for m in metriken if m.typ == MetrikTyp.CPU), 0)
                }
                for modul, metriken in snapshot.module_metriken.items()
            },
            "gesamt_statistik": {
                "laufzeit_stunden": (time.time() - self.startzeit) / 3600,
                "gesamt_metriken": self.gesamt_metriken,
                "aktive_warnungen_count": len(snapshot.warnungen)
            }
        }
    
    def _bereinige_alte_daten(self):
        """Entfernt alte Performance-Daten"""
        cutoff_time = time.time() - (self.historie_stunden * 3600)
        
        # Bereinige Leistungsdaten
        self.leistungs_daten = [
            snapshot for snapshot in self.leistungs_daten 
            if snapshot.timestamp > cutoff_time
        ]
        
        # Bereinige Metrik-Historie
        for key in list(self.metrik_historie.keys()):
            self.metrik_historie[key] = [
                metrik for metrik in self.metrik_historie[key]
                if metrik.timestamp > cutoff_time
            ]
    
    def get_aktuelle_performance(self) -> Dict[str, Any]:
        """Gibt aktuelle Performance-Daten zurück"""
        with self._lock:
            if not self.leistungs_daten:
                return {}
            
            aktuell = self.leistungs_daten[-1]
            return self._generiere_dashboard_daten(aktuell)
    
    def get_trend_analyse(self, modul: str, metrik_typ: MetrikTyp, stunden: int = 1) -> Optional[TrendAnalyse]:
        """Analysiert Performance-Trends für ein Modul"""
        with self._lock:
            key = f"{modul}_{metrik_typ.value}"
            if key not in self.metrik_historie or len(self.metrik_historie[key]) < 2:
                return None
            
            metriken = self.metrik_historie[key]
            cutoff_time = time.time() - (stunden * 3600)
            relevante_metriken = [m for m in metriken if m.timestamp > cutoff_time]
            
            if len(relevante_metriken) < 2:
                return None
            
            werte = [m.wert for m in relevante_metriken]
            timestamps = [m.timestamp for m in relevante_metriken]
            
            # Einfache lineare Regression für Trend
            if len(werte) > 1:
                trend, aenderungs_rate = self._berechne_trend(werte, timestamps)
                vorhersage = self._mache_vorhersage(werte, trend, aenderungs_rate)
                empfehlung = self._generiere_empfehlung(modul, metrik_typ, trend, werte[-1])
                
                return TrendAnalyse(
                    modul=modul,
                    metrik_typ=metrik_typ,
                    trend=trend,
                    aenderungs_rate=aenderungs_rate,
                    vorhersage=vorhersage,
                    empfehlung=empfehlung
                )
            
            return None
    
    def _berechne_trend(self, werte: List[float], timestamps: List[float]) -> tuple:
        """Berechnet Trend und Änderungsrate"""
        if len(werte) < 2:
            return "stabil", 0.0
        
        # Einfache Trendberechnung
        erste_haelfte = statistics.mean(werte[:len(werte)//2])
        zweite_haelfte = statistics.mean(werte[len(werte)//2:])
        
        if zweite_haelfte > erste_haelfte * 1.1:
            trend = "steigend"
        elif zweite_haelfte < erste_haelfte * 0.9:
            trend = "fallend"
        else:
            trend = "stabil"
        
        aenderungs_rate = ((zweite_haelfte - erste_haelfte) / erste_haelfte) * 100
        
        return trend, aenderungs_rate
    
    def _mache_vorhersage(self, werte: List[float], trend: str, aenderungs_rate: float) -> float:
        """Macht einfache Performance-Vorhersage"""
        letzter_wert = werte[-1]
        
        if trend == "steigend":
            return letzter_wert * (1 + aenderungs_rate / 100)
        elif trend == "fallend":
            return letzter_wert * (1 - aenderungs_rate / 100)
        else:
            return letzter_wert
    
    def _generiere_empfehlung(self, modul: str, metrik_typ: MetrikTyp, trend: str, aktueller_wert: float) -> str:
        """Generiert Optimierungs-Empfehlungen"""
        ziel = self.modul_ziele.get(modul, {}).get(metrik_typ.value, 0)
        
        if metrik_typ == MetrikTyp.LATENZ and aktueller_wert > ziel:
            return f"Latenz optimieren - aktuell {aktueller_wert:.3f}s, Ziel {ziel}s"
        elif metrik_typ == MetrikTyp.CPU and aktueller_wert > ziel:
            return f"CPU-Auslastung reduzieren - aktuell {aktueller_wert:.1f}%, Ziel {ziel}%"
        elif trend == "steigend" and aenderungs_rate > 10:
            return f"Performance-Degradation erkannt - {aenderungs_rate:.1f}% Anstieg"
        else:
            return "Performance innerhalb der Ziele"
    
    def generiere_performance_report(self, stunden: int = 24) -> Dict[str, Any]:
        """Generiert einen detaillierten Performance-Report"""
        with self._lock:
            cutoff_time = time.time() - (stunden * 3600)
            relevante_snapshots = [
                s for s in self.leistungs_daten 
                if s.timestamp > cutoff_time
            ]
            
            if not relevante_snapshots:
                return {}
            
            # Aggregierte Statistiken
            system_cpu_values = [s.system_metriken.get("cpu_percent", 0) for s in relevante_snapshots]
            system_ram_values = [s.system_metriken.get("ram_percent", 0) for s in relevante_snapshots]
            
            report = {
                "zeitraum": {
                    "start": datetime.fromtimestamp(relevante_snapshots[0].timestamp).isoformat(),
                    "ende": datetime.fromtimestamp(relevante_snapshots[-1].timestamp).isoformat(),
                    "dauer_stunden": stunden
                },
                "system_performance": {
                    "cpu_avg": statistics.mean(system_cpu_values),
                    "cpu_max": max(system_cpu_values),
                    "ram_avg": statistics.mean(system_ram_values),
                    "ram_max": max(system_ram_values)
                },
                "modul_performance": {},
                "warnungen_analyse": {
                    "gesamt_warnungen": sum(len(s.warnungen) for s in relevante_snapshots),
                    "kritische_phasen": len([s for s in relevante_snapshots if len(s.warnungen) > 0])
                },
                "empfehlungen": []
            }
            
            # Modul-spezifische Analysen
            for modul in self.modul_ziele.keys():
                trend_analyse = self.get_trend_analyse(modul, MetrikTyp.LATENZ, stunden)
                if trend_analyse:
                    report["modul_performance"][modul] = {
                        "trend": trend_analyse.trend,
                        "aenderungs_rate": trend_analyse.aenderungs_rate,
                        "empfehlung": trend_analyse.empfehlung
                    }
            
            return report
    
    def add_warnung_callback(self, callback: Callable):
        """Fügt Callback für Warnungen hinzu"""
        self.warnung_callbacks.append(callback)
    
    def add_dashboard_callback(self, callback: Callable):
        """Fügt Callback für Dashboard-Updates hinzu"""
        self.dashboard_callbacks.append(callback)
    
    def beenden(self):
        """Beendet den Leistungsmonitor"""
        self._is_running = False
        self.logger.info("🛑 Leistungsmonitor beendet")

# =============================================================================
# DASHBOARD UND VISUALISIERUNG
# =============================================================================

class EchtzeitDashboard:
    """Einfaches Echtzeit-Dashboard für Performance-Daten"""
    
    def __init__(self, monitor: EchtzeitLeistungsMonitor):
        self.monitor = monitor
        self.aktuelle_daten = {}
        
        # Registriere Callback
        self.monitor.add_dashboard_callback(self.aktualisiere_dashboard)
    
    def aktualisiere_dashboard(self, daten: Dict[str, Any]):
        """Aktualisiert das Dashboard mit neuen Daten"""
        self.aktuelle_daten = daten
        self._zeige_dashboard()
    
    def _zeige_dashboard(self):
        """Zeigt das Echtzeit-Dashboard an"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print("🎯 SCHACHMATTSCHILD LEISTUNGS-DASHBOARD")
        print("=" * 80)
        
        if not self.aktuelle_daten:
            print("⏳ Warte auf Daten...")
            return
        
        # System-Übersicht
        system = self.aktuelle_daten.get("system_metriken", {})
        print(f"\n💻 SYSTEMÜBERSICHT:")
        print(f"   CPU: {system.get('cpu_percent', 0):.1f}% | "
              f"RAM: {system.get('ram_percent', 0):.1f}% | "
              f"Energie: {system.get('energie_verbrauch_w', 0):.1f}W")
        
        # Modul-Performance
        print(f"\n🔧 MODUL-PERFORMANCE:")
        modul_status = self.aktuelle_daten.get("modul_status", {})
        for modul, metriken in modul_status.items():
            latenz = metriken.get('latenz', 0) * 1000  # in ms
            cpu = metriken.get('cpu', 0)
            status = "✅" if latenz < 50 and cpu < 80 else "⚠️" if latenz < 100 else "❌"
            print(f"   {status} {modul:<20} Latenz: {latenz:5.1f}ms | CPU: {cpu:4.1f}%")
        
        # Warnungen
        warnungen = self.aktuelle_daten.get("aktive_warnungen", [])
        if warnungen:
            print(f"\n🚨 AKTIVE WARNUNGEN ({len(warnungen)}):")
            for warnung in warnungen[:5]:  # Zeige max 5 Warnungen
                print(f"   • {warnung}")
            if len(warnungen) > 5:
                print(f"   ... und {len(warnungen) - 5} weitere")
        else:
            print(f"\n✅ KEINE AKTIVEN WARNUNGEN")
        
        # Statistik
        statistik = self.aktuelle_daten.get("gesamt_statistik", {})
        print(f"\n📊 STATISTIK:")
        print(f"   Laufzeit: {statistik.get('laufzeit_stunden', 0):.1f}h | "
              f"Metriken: {statistik.get('gesamt_metriken', 0):,}")

# =============================================================================
# TEST UND DEMONSTRATION
# =============================================================================

def demonstriere_leistungsmonitor():
    """Demonstriert den Leistungsmonitor in Aktion"""
    print("🧪 DEMONSTRATION LEISTUNGSMONITOR")
    
    # Erstelle und starte Monitor
    monitor = EchtzeitLeistungsMonitor(update_intervall=3.0)
    dashboard = EchtzeitDashboard(monitor)
    
    # Füge Warnungs-Callback hinzu
    def warnungs_handler(nachricht: str):
        print(f"🔔 WARNHANDLER: {nachricht}")
    
    monitor.add_warnung_callback(warnungs_handler)
    
    # Starte Monitoring
    monitor.start_monitoring()
    
    print("📊 Monitoring läuft... Drücke Ctrl+C zum Beenden")
    
    try:
        # Lauf für 30 Sekunden und zeige Reports
        time.sleep(30)
        
        # Generiere Performance-Report
        print("\n📈 GENERIERE PERFORMANCE-REPORT...")
        report = monitor.generiere_performance_report(stunden=0.1)  # Letzte 6 Minuten
        
        if report:
            print(f"\n📋 PERFORMANCE-REPORT:")
            print(f"   Zeitraum: {report['zeitraum']['start']} bis {report['zeitraum']['ende']}")
            print(f"   CPU-Durchschnitt: {report['system_performance']['cpu_avg']:.1f}%")
            print(f"   RAM-Durchschnitt: {report['system_performance']['ram_avg']:.1f}%")
            print(f"   Warnungen gesamt: {report['warnungen_analyse']['gesamt_warnungen']}")
            
            # Zeige Trend-Analysen
            print(f"\n📈 TREND-ANALYSEN:")
            for modul in ["schwarmintelligenz", "zielerkennung", "kommunikation"]:
                trend = monitor.get_trend_analyse(modul, MetrikTyp.LATENZ, 0.1)
                if trend:
                    print(f"   {modul}: {trend.trend} ({trend.aenderungs_rate:+.1f}%) - {trend.empfehlung}")
        
        # Speichere Report
        with open("performance_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report gespeichert: performance_report.json")
        
    except KeyboardInterrupt:
        print("\n⏹️  Beende Demonstration...")
    
    finally:
        monitor.beenden()

if __name__ == "__main__":
    demonstriere_leistungsmonitor()
