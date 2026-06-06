# Daylux Labs - ISC_AI - Proprietary and Confidential
# SCHWARMINTELLIGENZ_MODUL.py
"""
SCHWARMINTELLIGENZ FÜR DROHNEN-KOORDINATION
Modul für koordinierte Abfangmanöver im SCHACHMATTSCHILD-System
"""

import numpy as np
import math
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Drohne:
    id: str
    position: np.ndarray  # [x, y, z]
    velocity: np.ndarray  # [vx, vy, vz]
    ziel_position: np.ndarray
    max_geschwindigkeit: float = 30.0  # m/s
    sicherheits_abstand: float = 15.0  # Meter
    drohnen_typ: str = "ORAKEL"  # ORAKEL, SOKOL, SENSOR

class SchwarmIntelligenz:
    def __init__(self):
        self.drohnen = []
        self.regeln_gewichte = {
            'ziel_ausrichtung': 1.0,
            'schwarm_kohaesion': 0.3,
            'kollisions_vermeidung': 1.5,
            'geschwindigkeit_anpassung': 0.5
        }
        self.kommunikations_reichweite = 1000  # Meter
        
    def drohne_hinzufuegen(self, drohne: Drohne):
        """Füge Drohne zum Schwarm hinzu"""
        self.drohnen.append(drohne)
        
    def berechne_schwarm_verhalten(self) -> Dict[str, np.ndarray]:
        """
        Berechnet Schwarmverhalten basierend auf Boids-Algorithmus
        mit militärischen Anpassungen für Abfangmanöver
        """
        neue_geschwindigkeiten = {}
        
        for drohne in self.drohnen:
            # Regel 1: Zielausrichtung (Priorität für Abfangmanöver)
            ziel_vektor = self._ziel_ausrichtung(drohne)
            
            # Regel 2: Schwarm-Kohäsion
            kohaesion_vektor = self._schwarm_kohaesion(drohne)
            
            # Regel 3: Kollisionsvermeidung
            kollisions_vektor = self._kollisions_vermeidung(drohne)
            
            # Regel 4: Geschwindigkeitsanpassung
            geschwindigkeit_vektor = self._geschwindigkeit_anpassung(drohne)
            
            # Kombiniere alle Verhaltensregeln
            gesamt_vektor = (
                self.regeln_gewichte['ziel_ausrichtung'] * ziel_vektor +
                self.regeln_gewichte['schwarm_kohaesion'] * kohaesion_vektor +
                self.regeln_gewichte['kollisions_vermeidung'] * kollisions_vektor +
                self.regeln_gewichte['geschwindigkeit_anpassung'] * geschwindigkeit_vektor
            )
            
            # Begrenze Geschwindigkeit
            neue_geschwindigkeit = self._begrenze_geschwindigkeit(
                drohne.velocity + gesamt_vektor, 
                drohne.max_geschwindigkeit
            )
            
            neue_geschwindigkeiten[drohne.id] = neue_geschwindigkeit
            
        return neue_geschwindigkeiten
    
    def _ziel_ausrichtung(self, drohne: Drohne) -> np.ndarray:
        """Berechnet Vektor zur Zielverfolgung (militärische Präzision)"""
        if drohne.drohnen_typ == "SOKOL":
            # SOKOL-Drohnen: Aggressive Zielverfolgung
            ziel_richtung = drohne.ziel_position - drohne.position
            return self._normalisiere_vektor(ziel_richtung) * 2.0
        else:
            # ORAKEL/SENSOR: Standard Zielverfolgung
            ziel_richtung = drohne.ziel_position - drohne.position
            return self._normalisiere_vektor(ziel_richtung)
    
    def _schwarm_kohaesion(self, drohne: Drohne) -> np.ndarray:
        """Berechnet Kohäsionsvektor zum Schwarmzentrum"""
        nachbarn = self._finde_nachbarn(drohne)
        if not nachbarn:
            return np.zeros(3)
            
        # Berechne Schwarmzentrum
        positions_sum = sum(nachbar.position for nachbar in nachbarn)
        schwarm_zentrum = positions_sum / len(nachbarn)
        
        # Vektor zum Schwarmzentrum
        return self._normalisiere_vektor(schwarm_zentrum - drohne.position) * 0.5
    
    def _kollisions_vermeidung(self, drohne: Drohne) -> np.ndarray:
        """Vermeidet Kollisionen mit anderen Drohnen"""
        kollisions_vektor = np.zeros(3)
        nachbarn = self._finde_nachbarn(drohne)
        
        for nachbar in nachbarn:
            distanz = np.linalg.norm(nachbar.position - drohne.position)
            if distanz < drohne.sicherheits_abstand:
                # Berechne Ausweichvektor
                ausweich_richtung = drohne.position - nachbar.position
                staerke = (drohne.sicherheits_abstand - distanz) / drohne.sicherheits_abstand
                kollisions_vektor += self._normalisiere_vektor(ausweich_richtung) * staerke
                
        return kollisions_vektor
    
    def _geschwindigkeit_anpassung(self, drohne: Drohne) -> np.ndarray:
        """Passt Geschwindigkeit an Nachbarn an"""
        nachbarn = self._finde_nachbarn(drohne)
        if not nachbarn:
            return np.zeros(3)
            
        # Durchschnittsgeschwindigkeit der Nachbarn
        geschwindigkeiten_sum = sum(nachbar.velocity for nachbar in nachbarn)
        durchschnitt_geschwindigkeit = geschwindigkeiten_sum / len(nachbarn)
        
        return (durchschnitt_geschwindigkeit - drohne.velocity) * 0.1
    
    def _finde_nachbarn(self, drohne: Drohne) -> List[Drohne]:
        """Findet Nachbarn innerhalb der Kommunikationsreichweite"""
        nachbarn = []
        for andere_drohne in self.drohnen:
            if andere_drohne.id != drohne.id:
                distanz = np.linalg.norm(andere_drohne.position - drohne.position)
                if distanz <= self.kommunikations_reichweite:
                    nachbarn.append(andere_drohne)
        return nachbarn
    
    def _normalisiere_vektor(self, vektor: np.ndarray) -> np.ndarray:
        """Normalisiert einen Vektor"""
        norm = np.linalg.norm(vektor)
        if norm == 0:
            return np.zeros(3)
        return vektor / norm
    
    def _begrenze_geschwindigkeit(self, geschwindigkeit: np.ndarray, max_geschw: float) -> np.ndarray:
        """Begrenzt die Geschwindigkeit auf Maximum"""
        aktuelle_geschw = np.linalg.norm(geschwindigkeit)
        if aktuelle_geschw > max_geschw:
            return (geschwindigkeit / aktuelle_geschw) * max_geschw
        return geschwindigkeit

# TESTMODUL FÜR SCHWARMINTELLIGENZ
def teste_schwarm_intelligenz():
    """Testet das Schwarmintelligenz-Modul"""
    print("🧪 TESTE SCHWARMINTELLIGENZ-MODUL...")
    
    # Erstelle Schwarm-Controller
    schwarm = SchwarmIntelligenz()
    
    # Erstelle Test-Drohnen
    drohnen = [
        Drohne("SOKOL_1", np.array([0, 0, 100]), np.array([10, 0, 0]), np.array([1000, 0, 100])),
        Drohne("SOKOL_2", np.array([50, 0, 100]), np.array([10, 5, 0]), np.array([1000, 0, 100])),
        Drohne("ORAKEL_1", np.array([0, 50, 150]), np.array([0, 10, 0]), np.array([1000, 0, 100]))
    ]
    
    for drohne in drohnen:
        schwarm.drohne_hinzufuegen(drohne)
    
    # Simuliere Schwarmverhalten
    for step in range(5):
        geschwindigkeiten = schwarm.berechne_schwarm_verhalten()
        print(f"Schritt {step + 1}:")
        for drohne_id, geschw in geschwindigkeiten.items():
            print(f"  {drohne_id}: Geschw = {np.linalg.norm(geschw):.1f} m/s")
    
    print("✅ SCHWARMINTELLIGENZ-MODUL FUNKTIONIERT")

if __name__ == "__main__":
    teste_schwarm_intelligenz()
