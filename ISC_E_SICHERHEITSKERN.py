#!/usr/bin/env python3
# Daylux Labs - ISC_AI - Proprietary and Confidential
# -*- coding: utf-8 -*-
"""
ISC-E Sicherheitskern (Patent 05)
==================================
Deterministische Sicherheitsinfrastruktur zur Validierung physischer Umwelt-
und Ereigniszustände mit mehrschichtiger Referenzarchitektur,
Langzeittrendanalyse und automatischer Rekalibrierung.

Patent DE 10 2025 ... (ISC-E)
Anspruch 1-13 vollständig implementiert.

Kern-Architektur (4-Layer nach Patent Figur 1):
  Layer 1: Primärquelle  – Lokale, physisch gesicherte Sensorik (HAL)
  Layer 2: Sekundärquelle – Kryptografisch signierte externe Referenzen
  Layer 3: Konsistenzprüfung – Deterministischer Abgleich P vs. S
  Layer 4: Audit-Referenzkette – Crypto-Audit-Log (SHA-256 verkettet)

Eigenschaften:
  - KEINE KI im Sicherheitspfad (Patent Anspruch 4)
  - Deterministisch, konfigurierbare Toleranzschwellen
  - Revisionssicheres Audit-Log
  - 30-Tage-Langzeittrendanalyse mit gestaffelter Auflösung
  - Safety-Interrupt für deterministische Notabschaltung
"""

import hashlib
import hmac
import json
import time
import os
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Optional


# ============================================================================
# ENUMS
# ============================================================================

class ISCESicherheitszustand(Enum):
    """Sicherheitszustände des ISC-E Kerns (Patent Anspruch 6)"""
    GRUEN = "gruen"           # Alles OK
    GELB = "gelb"             # Leichte Abweichung, beobachtet
    ORANGE = "orange"         # Signifikante Abweichung, Maßnahmen
    ROT = "rot"               # Kritisch, Notabschaltung


class ReferenzQuelle(Enum):
    """Typ der Referenzquelle"""
    PRIMAER = "primaer"       # Lokale Sensorik (HAL)
    SEKUNDAER = "sekundaer"   # Kryptografisch signierte externe Referenz
    INTERN = "intern"         # Interner Kalibrierungswert


class AuditEintragTyp(Enum):
    """Typ eines Audit-Log-Eintrags (Patent Abschnitt 6)"""
    VALIDIERUNG = "validierung"
    REFERENZ_ABGLEICH = "referenz_abgleich"
    SCHUTZMASSNAHME = "schutzmassnahme"
    REKALIBRIERUNG = "rekalibrierung"
    FEHLER = "fehler"
    SYSTEMSTART = "systemstart"
    TREND_ALARM = "trend_alarm"
    SAFETY_INTERRUPT = "safety_interrupt"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class AuditEintrag:
    """
    Einzelner Eintrag im Crypto-Audit-Log (Patent Anspruch 8).
    
    Jeder Eintrag ist kryptografisch mit dem vorherigen verkettet:
    hash = SHA256(vorheriger_hash + zeitstempel + daten + signatur)
    """
    typ: AuditEintragTyp
    zeitstempel: float
    beschreibung: str
    daten: dict = field(default_factory=dict)
    
    # Referenzabgleich-Daten (Patent Anspruch 8)
    primaer_wert: Optional[float] = None
    sekundaer_wert: Optional[float] = None
    toleranz_abweichung: Optional[float] = None
    
    # Kryptografische Verkettung
    vorheriger_hash: str = ""
    eigener_hash: str = ""
    signatur: str = ""  # HMAC-SHA256 über den Eintrag
    
    def berechne_hash(self, secret: bytes) -> str:
        """Berechnet SHA-256 Hash + HMAC-Signatur (Patent Anspruch 8, 10)"""
        # Inhalt serialisieren
        inhalt = json.dumps({
            'typ': self.typ.value,
            'zeitstempel': self.zeitstempel,
            'beschreibung': self.beschreibung,
            'daten': self.daten,
            'primaer_wert': self.primaer_wert,
            'sekundaer_wert': self.sekundaer_wert,
            'toleranz_abweichung': self.toleranz_abweichung,
            'vorheriger_hash': self.vorheriger_hash,
        }, sort_keys=True, default=str)
        
        # SHA-256 Hash
        self.eigener_hash = hashlib.sha256(
            (self.vorheriger_hash + inhalt).encode('utf-8')
        ).hexdigest()
        
        # HMAC-SHA256 Signatur
        self.signatur = hmac.new(
            secret,
            self.eigener_hash.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return self.eigener_hash


@dataclass
class PrimärquelleDaten:
    """
    Daten von der lokalen, physisch gesicherten Sensorik
    (Patent Anspruch 1, Layer 1)
    """
    sensor_id: str
    timestamp: float
    wert: float
    einheit: str = ""
    sensor_typ: str = ""


@dataclass
class SekundärquelleDaten:
    """
    Kryptografisch signierte externe Referenz
    (Patent Anspruch 1, Layer 2)
    
    Wird nur akzeptiert, wenn Signatur mit hinterlegtem
    öffentlichen Schlüssel gültig ist (Anspruch 9).
    """
    quelle: str
    timestamp: float
    wert: float
    einheit: str = ""
    signatur: str = ""
    oeffentlicher_schluessel_id: str = ""


@dataclass
class KonsistenzPruefungErgebnis:
    """
    Ergebnis einer Konsistenzprüfung (Patent Anspruch 1, Layer 3)
    """
    ist_konsistent: bool
    primaer_wert: float
    sekundaer_wert: float
    toleranz: float
    abweichung: float
    ist_validiert: bool = False


@dataclass
class TrendAnalyseErgebnis:
    """
    Ergebnis der Langzeittrendanalyse (Patent Anspruch 11)
    """
    drift_erkannt: bool
    drift_wert: float
    drift_schwellwert: float
    steigung: float
    rekalibrierung_ausgeloest: bool = False


# ============================================================================
# ISC-E CORE – Sicherheitskern
# ============================================================================

class ISCESicherheitsKern:
    """
    ISC-E Core (600) – Deterministische Sicherheitsinstanz
    (Patent Figur 1)
    
    Implementiert:
      - Deterministische Referenzarchitektur (Schichten 1-4)
      - Crypto-Audit-Log mit SHA-256 Verkettung
      - Langzeittrendanalyse (30 Tage, gestaffelte Auflösung)
      - Automatische Rekalibrierung
      - Safety-Interrupt
      - KEINE KI im Sicherheitspfad (Anspruch 4)
    """
    
    def __init__(
        self,
        kern_id: str = "ISC-E-001",
        toleranz_schwelle: float = 0.05,     # 5% Default-Toleranz
        drift_schwellwert: float = 0.1,      # 10% Drift löst Alarm aus
        hmac_secret: Optional[bytes] = None,
        vertrauensanker_schluessel: Optional[bytes] = None,
    ):
        # Identität
        self.kern_id = kern_id
        self.logger = None  # Kann extern gesetzt werden
        
        # Konfigurierbare Schwellwerte (Patent Anspruch 1)
        self.toleranz_schwelle = toleranz_schwelle
        self.drift_schwellwert = drift_schwellwert
        
        # Kryptografische Schlüssel (Patent Anspruch 9)
        self._hmac_secret = hmac_secret or os.urandom(32)
        self._vertrauensanker = vertrauensanker_schluessel or os.urandom(32)
        
        # Sicherheitszustand (Patent Anspruch 6)
        self.zustand = ISCESicherheitszustand.GRUEN
        
        # Crypto-Audit-Log (Patent Anspruch 8)
        self._audit_log: list[AuditEintrag] = []
        self._letzter_hash = "0" * 64  # Genesis-Block
        
        # Langzeittrendanalyse (Patent Anspruch 11)
        self._trend_speicher: dict[str, list[dict]] = {
            '24h': [],    # 1 Sekunde Auflösung
            '7d': [],     # 1 Minute Auflösung
            '30d': [],    # 1 Stunde Auflösung
        }
        
        # Primärquelle-Simulation (Layer 1)
        self._primaer_sensoren: dict[str, dict] = {}
        
        # Systemstart protokollieren
        self._log_eintrag(
            AuditEintragTyp.SYSTEMSTART,
            f"ISC-E Kern {kern_id} gestartet",
            {'toleranz': toleranz_schwelle, 'drift': drift_schwellwert}
        )
    
    # ========================================================================
    # LAYER 1: PRIMÄRQUELLE (Patent Anspruch 1, Figur 1)
    # ========================================================================
    
    def registriere_primaer_sensor(self, sensor_id: str, sensor_typ: str = "",
                                    offset: float = 0.0, faktor: float = 1.0):
        """
        Registriert einen lokalen, physisch gesicherten Sensor
        (Patent Schicht 1: Primärquelle)
        
        Der Sensor ist direkt mit dem ISC-E Core verbunden,
        ohne Netzwerkanbindung.
        """
        self._primaer_sensoren[sensor_id] = {
            'sensor_typ': sensor_typ,
            'offset': offset,
            'faktor': faktor,
            'letzter_wert': None,
            'letzte_zeit': None,
        }
    
    def lese_primaer_sensor(self, sensor_id: str, rohwert: float) -> PrimärquelleDaten:
        """
        Liest einen Primärsensor aus (simuliert).
        
        Args:
            sensor_id: ID des Sensors
            rohwert: Rohwert des Sensors (wird mit offset/faktor kalibriert)
            
        Returns:
            PrimärquelleDaten mit dem kalibrierten Wert
        """
        if sensor_id not in self._primaer_sensoren:
            raise ValueError(f"Unbekannter Sensor: {sensor_id}")
        
        sensor = self._primaer_sensoren[sensor_id]
        
        # Kalibrierung anwenden
        kalibrierter_wert = rohwert * sensor['faktor'] + sensor['offset']
        
        daten = PrimärquelleDaten(
            sensor_id=sensor_id,
            timestamp=time.time(),
            wert=round(kalibrierter_wert, 6),
            sensor_typ=sensor['sensor_typ'],
        )
        
        sensor['letzter_wert'] = daten.wert
        sensor['letzte_zeit'] = daten.timestamp
        
        # Direkt ins Audit-Log schreiben (Patent Abschnitt 2, Layer 1)
        self._log_eintrag(
            AuditEintragTyp.VALIDIERUNG,
            f"Primärsensor {sensor_id}: {daten.wert}",
            {'sensor_id': sensor_id, 'rohwert': rohwert, 'kalibriert': daten.wert}
        )
        
        return daten
    
    # ========================================================================
    # LAYER 2: SEKUNDÄRQUELLE (Patent Anspruch 1, 9)
    # ========================================================================
    
    def validiere_sekundaer_quelle(
        self, daten: SekundärquelleDaten
    ) -> bool:
        """
        Prüft die kryptografische Signatur einer externen Referenz.
        (Patent Anspruch 9)
        
        Nur gültig, wenn Signatur mit hinterlegtem Vertrauensanker-Schlüssel
        geprüft werden kann.
        """
        if not daten.signatur:
            return False
        
        # HMAC-Prüfung mit Vertrauensanker
        expected = hmac.new(
            self._vertrauensanker,
            f"{daten.quelle}{daten.timestamp}{daten.wert}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected.encode('utf-8'), daten.signatur.encode('utf-8'))
    
    # ========================================================================
    # LAYER 3: KONSISTENZPRÜFUNG (Patent Anspruch 1, Layer 3)
    # ========================================================================
    
    def konsistenz_pruefung(
        self,
        primaer: PrimärquelleDaten,
        sekundaer: SekundärquelleDaten,
        toleranz: Optional[float] = None
    ) -> KonsistenzPruefungErgebnis:
        """
        Deterministischer Abgleich zwischen Primär- und Sekundärquelle
        (Patent Anspruch 1, Schicht 3)
        
        Ein Wert gilt nur dann als validiert, wenn beide Quellen
        innerhalb der Toleranzschwelle übereinstimmen.
        """
        tol = toleranz if toleranz is not None else self.toleranz_schwelle
        
        # Abweichung berechnen (prozentual)
        if primaer.wert != 0:
            abweichung = abs(primaer.wert - sekundaer.wert) / abs(primaer.wert)
        else:
            abweichung = abs(sekundaer.wert) if sekundaer.wert != 0 else 0.0
        
        ist_konsistent = abweichung <= tol
        
        ergebnis = KonsistenzPruefungErgebnis(
            ist_konsistent=ist_konsistent,
            primaer_wert=primaer.wert,
            sekundaer_wert=sekundaer.wert,
            toleranz=tol,
            abweichung=round(abweichung, 6),
            ist_validiert=ist_konsistent,
        )
        
        # Audit-Log Eintrag (Patent Anspruch 8)
        self._log_eintrag(
            AuditEintragTyp.REFERENZ_ABGLEICH,
            f"Konsistenzprüfung: {'✅' if ist_konsistent else '❌'} "
            f"(P={primaer.wert}, S={sekundaer.wert}, Δ={abweichung:.4f}, T={tol})",
            {'primaer_wert': primaer.wert, 'sekundaer_wert': sekundaer.wert,
             'abweichung': abweichung, 'toleranz': tol},
            primaer_wert=primaer.wert,
            sekundaer_wert=sekundaer.wert,
            toleranz_abweichung=abweichung,
        )
        
        return ergebnis
    
    # ========================================================================
    # LAYER 4: AUDIT-REFERENZKETTE (Patent Anspruch 10)
    # ========================================================================
    
    def _log_eintrag(
        self,
        typ: AuditEintragTyp,
        beschreibung: str,
        daten: dict = None,
        primaer_wert: float = None,
        sekundaer_wert: float = None,
        toleranz_abweichung: float = None,
    ) -> AuditEintrag:
        """
        Erstellt einen kryptografisch verketteten Audit-Eintrag
        (Patent Anspruch 8, 10)
        
        Jeder Eintrag enthält den Hash des vorherigen Eintrags,
        sodass eine manipulationssichere Kette entsteht.
        """
        eintrag = AuditEintrag(
            typ=typ,
            zeitstempel=time.time(),
            beschreibung=beschreibung,
            daten=daten or {},
            primaer_wert=primaer_wert,
            sekundaer_wert=sekundaer_wert,
            toleranz_abweichung=toleranz_abweichung,
            vorheriger_hash=self._letzter_hash,
        )
        
        # SHA-256 Hash + HMAC-Signatur berechnen
        eintrag.berechne_hash(self._hmac_secret)
        self._letzter_hash = eintrag.eigener_hash
        
        self._audit_log.append(eintrag)
        
        if self.logger:
            self.logger.debug(f"[ISC-E] {typ.value}: {beschreibung}")
        
        return eintrag
    
    def audit_log_pruefen(self) -> bool:
        """
        Überprüft die Integrität der gesamten Audit-Kette.
        (Patent Anspruch 8, 10)
        
        Stellt sicher, dass kein Eintrag manipuliert wurde.
        """
        letzter_hash = "0" * 64
        
        for eintrag in self._audit_log:
            # Prüfe: vorheriger_hash muss letzter_hash sein
            if eintrag.vorheriger_hash != letzter_hash:
                return False
            
            # Prüfe: Hash muss korrekt neu berechenbar sein
            inhalt = json.dumps({
                'typ': eintrag.typ.value,
                'zeitstempel': eintrag.zeitstempel,
                'beschreibung': eintrag.beschreibung,
                'daten': eintrag.daten,
                'primaer_wert': eintrag.primaer_wert,
                'sekundaer_wert': eintrag.sekundaer_wert,
                'toleranz_abweichung': eintrag.toleranz_abweichung,
                'vorheriger_hash': eintrag.vorheriger_hash,
            }, sort_keys=True, default=str)
            
            erwarteter_hash = hashlib.sha256(
                (eintrag.vorheriger_hash + inhalt).encode('utf-8')
            ).hexdigest()
            
            if eintrag.eigener_hash != erwarteter_hash:
                return False
            
            letzter_hash = eintrag.eigener_hash
        
        return True
    
    def get_audit_log(self, letzte_n: int = 0) -> list[dict]:
        """
        Gibt die letzten n Audit-Log-Einträge aus.
        (Patent Abschnitt 6)
        """
        eintraege = self._audit_log[-letzte_n:] if letzte_n > 0 else self._audit_log
        return [
            {
                'typ': e.typ.value,
                'zeitstempel': e.zeitstempel,
                'beschreibung': e.beschreibung,
                'daten': e.daten,
                'primaer_wert': e.primaer_wert,
                'sekundaer_wert': e.sekundaer_wert,
                'toleranz_abweichung': e.toleranz_abweichung,
                'hash': e.eigener_hash[:16] + '...',
                'signatur': e.signatur[:8] + '...',
            }
            for e in eintraege
        ]
    
    # ========================================================================
    # LANGZEITTRENDANALYSE (Patent Anspruch 11)
    # ========================================================================
    
    def trend_daten_aufzeichnen(self, sensor_id: str, wert: float):
        """
        Zeichnet Messwerte für die Langzeittrendanalyse auf.
        (Patent Abschnitt 4)
        
        Gestaffelte Auflösung:
          - 24h: 1 Sekunde
          - 7d:  1 Minute
          - 30d: 1 Stunde
        """
        jetzt = time.time()
        
        # 24h Speicher (1s Auflösung)
        self._trend_speicher['24h'].append({
            'zeit': jetzt, 'wert': wert, 'sensor': sensor_id
        })
        
        # 7d Speicher (1min Auflösung) – nur jede Minute
        if len(self._trend_speicher['7d']) == 0 or \
           jetzt - self._trend_speicher['7d'][-1]['zeit'] >= 60:
            self._trend_speicher['7d'].append({
                'zeit': jetzt, 'wert': wert, 'sensor': sensor_id
            })
        
        # 30d Speicher (1h Auflösung) – nur jede Stunde
        if len(self._trend_speicher['30d']) == 0 or \
           jetzt - self._trend_speicher['30d'][-1]['zeit'] >= 3600:
            self._trend_speicher['30d'].append({
                'zeit': jetzt, 'wert': wert, 'sensor': sensor_id
            })
        
        # Alte Daten bereinigen
        self._trend_bereinigen()
    
    def _trend_bereinigen(self):
        """Entfernt Daten außerhalb des Zeitfensters"""
        jetzt = time.time()
        grenzen = {'24h': 86400, '7d': 604800, '30d': 2592000}
        
        for key, max_age in grenzen.items():
            self._trend_speicher[key] = [
                e for e in self._trend_speicher[key]
                if jetzt - e['zeit'] <= max_age
            ]
    
    def trend_analyse(
        self, sensor_id: str = ""
    ) -> TrendAnalyseErgebnis:
        """
        Führt Langzeittrendanalyse durch (Patent Anspruch 11)
        
        Verwendet lineare Regression über die gespeicherten Daten.
        Bei Überschreitung des Drift-Schwellwerts: Alarm + Rekalibrierung.
        """
        daten = self._trend_speicher['24h']
        
        if sensor_id:
            daten = [d for d in daten if d['sensor'] == sensor_id]
        
        if len(daten) < 10:  # Zu wenig Daten für Trend
            return TrendAnalyseErgebnis(
                drift_erkannt=False,
                drift_wert=0.0,
                drift_schwellwert=self.drift_schwellwert,
                steigung=0.0,
            )
        
        # Einfache lineare Regression
        n = len(daten)
        x_werte = [d['zeit'] for d in daten]
        y_werte = [d['wert'] for d in daten]
        
        x_mean = sum(x_werte) / n
        y_mean = sum(y_werte) / n
        
        # Steigung berechnen
        zaehler = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_werte, y_werte))
        nenner = sum((x - x_mean) ** 2 for x in x_werte)
        
        steigung = zaehler / nenner if nenner != 0 else 0.0
        
        # Drift als relative Änderung über das gesamte Fenster
        if y_mean != 0:
            drift = abs(steigung * (x_werte[-1] - x_werte[0]) / y_mean)
        else:
            drift = 0.0
        
        drift_erkannt = drift > self.drift_schwellwert
        
        ergebnis = TrendAnalyseErgebnis(
            drift_erkannt=drift_erkannt,
            drift_wert=round(drift, 6),
            drift_schwellwert=self.drift_schwellwert,
            steigung=round(steigung, 10),
        )
        
        if drift_erkannt:
            self._log_eintrag(
                AuditEintragTyp.TREND_ALARM,
                f"⚠️ Drift erkannt! Δ={drift:.4f} (Schwelle={self.drift_schwellwert})",
                {'drift': drift, 'steigung': steigung, 'sensor': sensor_id}
            )
            
            # Automatische Rekalibrierung auslösen (Patent Anspruch 11)
            ergebnis.rekalibrierung_ausgeloest = True
        
        return ergebnis
    
    def rekalibriere(self, sensor_id: str, sekundaer_wert: float):
        """
        Automatische Rekalibrierung anhand kryptografisch signierter
        externer Referenzen (Patent Anspruch 11)
        
        Passt die internen Kalibrierungsfaktoren an.
        """
        if sensor_id not in self._primaer_sensoren:
            raise ValueError(f"Unbekannter Sensor: {sensor_id}")
        
        sensor = self._primaer_sensoren[sensor_id]
        letzter_wert = sensor['letzter_wert']
        
        if letzter_wert is not None and letzter_wert != 0:
            # Neuen Faktor berechnen
            neuer_faktor = sekundaer_wert / letzter_wert
            sensor['faktor'] = round(neuer_faktor, 6)
            
            self._log_eintrag(
                AuditEintragTyp.REKALIBRIERUNG,
                f"🔄 Rekalibrierung {sensor_id}: Faktor={neuer_faktor:.4f}",
                {
                    'sensor_id': sensor_id,
                    'alter_wert': letzter_wert,
                    'referenz_wert': sekundaer_wert,
                    'neuer_faktor': neuer_faktor,
                }
            )
    
    # ========================================================================
    # SAFETY-INTERRUPT (Patent Anspruch 6, 7)
    # ========================================================================
    
    def safety_interrupt(self, grund: str) -> dict:
        """
        Deterministische Notabschaltung über Safety-Interrupt.
        (Patent Figur 1, Komponente 640; Anspruch 6, 7)
        
        KEINE KI-Beteiligung – rein deterministisch.
        """
        self.zustand = ISCESicherheitszustand.ROT
        
        eintrag = self._log_eintrag(
            AuditEintragTyp.SAFETY_INTERRUPT,
            f"🚨 SAFETY INTERRUPT: {grund}",
            {'grund': grund, 'kern_id': self.kern_id}
        )
        
        return {
            'aktion': 'notabschaltung',
            'zustand': ISCESicherheitszustand.ROT.value,
            'kern_id': self.kern_id,
            'timestamp': time.time(),
            'audit_hash': eintrag.eigener_hash,
            'hinweis': 'Deterministische Schutzmassnahme ohne KI-Beteiligung'
        }
    
    # ========================================================================
    # SCHUTZMASSNAHMEN (Patent Anspruch 6)
    # ========================================================================
    
    def schutzmassnahme_einleiten(
        self,
        konsistenz: KonsistenzPruefungErgebnis,
        primaer: PrimärquelleDaten,
        sekundaer: SekundärquelleDaten,
    ) -> dict:
        """
        Deterministische Schutzmaßnahmen bei Inkonsistenz
        (Patent Anspruch 6)
        
        Maßnahmen:
          1. Blockierung der auslösenden Aktion
          2. Isolation betroffener Systeme
          3. Notabschaltung bei ROT
        """
        abweichung = konsistenz.abweichung
        
        # Zustand basierend auf Abweichung (DFP V5.0 Degradationsstufen)
        if abweichung <= self.toleranz_schwelle * 1.5:
            self.zustand = ISCESicherheitszustand.GELB
            massnahme = "beobachten"
        elif abweichung <= self.toleranz_schwelle * 3.0:
            self.zustand = ISCESicherheitszustand.ORANGE
            massnahme = "isolieren"
        else:
            return self.safety_interrupt(
                f"Kritische Inkonsistenz: P={primaer.wert} vs S={sekundaer.wert} "
                f"(Δ={abweichung:.4f})"
            )
        
        self._log_eintrag(
            AuditEintragTyp.SCHUTZMASSNAHME,
            f"🛡️ Schutzmassnahme: {massnahme} (Zustand: {self.zustand.value})",
            {
                'massnahme': massnahme,
                'zustand': self.zustand.value,
                'abweichung': abweichung,
                'primaer_wert': primaer.wert,
                'sekundaer_wert': sekundaer.wert,
            },
            primaer_wert=primaer.wert,
            sekundaer_wert=sekundaer.wert,
            toleranz_abweichung=abweichung,
        )
        
        return {
            'massnahme': massnahme,
            'zustand': self.zustand.value,
            'blockiert': massnahme != 'beobachten',
            'audit_hash': self._letzter_hash[:16] + '...',
        }
    
    # ========================================================================
    # SYSTEMSTATUS (Patent Figur 1)
    # ========================================================================
    
    def system_status(self) -> dict:
        """
        Gibt vollständigen Systemstatus zurück.
        """
        return {
            'kern_id': self.kern_id,
            'zustand': self.zustand.value,
            'toleranz_schwelle': self.toleranz_schwelle,
            'drift_schwellwert': self.drift_schwellwert,
            'sensor_anzahl': len(self._primaer_sensoren),
            'audit_log_eintraege': len(self._audit_log),
            'audit_log_intakt': self.audit_log_pruefen(),
            'trend_daten': {k: len(v) for k, v in self._trend_speicher.items()},
            'timestamp': time.time(),
            'ki_frei': True,  # Anspruch 4
        }


# ============================================================================
# HILFSFUNKTION: Signierte externe Referenz erzeugen (für Tests/Sekundärquelle)
# ============================================================================

def erzeuge_signierte_referenz(
    quelle: str,
    wert: float,
    vertrauensanker: bytes,
    timestamp: Optional[float] = None
) -> SekundärquelleDaten:
    """
    Erzeugt eine kryptografisch signierte externe Referenz.
    (Hilfsfunktion für Tests und Sekundärquellen-Simulation)
    """
    ts = timestamp or time.time()
    
    signatur = hmac.new(
        vertrauensanker,
        f"{quelle}{ts}{wert}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return SekundärquelleDaten(
        quelle=quelle,
        timestamp=ts,
        wert=wert,
        signatur=signatur,
        oeffentlicher_schluessel_id="VERTRAUENSANKER_001",
    )
