"""
ISC_IMMUN.py
ISC-Patentfamilie – Modul 16
Dezentrales, biologisch inspiriertes Immun-System fuer Schwarm-Netzknoten

!!! ARCHITEKTUR-HINWEIS UND DISCLAIMER FÜR GITHUB-NUTZER !!!
Diese Implementierung simuliert das dezentrale Myzel-Protokoll funktional innerhalb 
eines geschlossenen Python-Prozesses über direkte Objektreferenzen. 
Für den produktiven Einsatz auf realer Drohnen- oder Embedded-Hardware müssen die 
Methoden 'emitiere_botenstoff()' und 'empfange_botenstoff()' an die physische 
Netzwerkschicht (z. B. Linux-Sockets via UDP/IP, LoRaWAN-Schnittstellen oder 
proprietäre Krypto-Mesh-Protokolle) gekoppelt werden.
"""

import time
import hashlib
from enum import Enum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from collections import deque

class KnotenStatus(Enum):
    GESUND      = "gesund"
    VERDAECHTIG = "verdaechtig"
    ISOLIERT    = "isoliert"
    GEHEILT     = "geheilt"


@dataclass
class MyzelBotenstoff:
    """Der algorithmische Botenstoff zur präventiven Immunisierung des Schwarms"""
    ursprung_knoten: str
    schad_signatur: str
    ttl: int  # Time-to-Live zur Begrenzung der exponentiellen Kaskade


class ISCImmunNode:
    def __init__(self, knoten_id: str, anomalie_schwelle: int = 3, quarantaene_s: float = 5.0):
        self.knoten_id = knoten_id
        self.status = KnotenStatus.GESUND
        self.anomalie_schwelle = anomalie_schwelle
        self.quarantaene_dauer = quarantaene_s
        
        # Lokale Datenbank des Knotens (Keine zentrale Instanz!)
        self.lokaler_anomalie_zaehler: Dict[str, int] = {}
        self.blockierte_ast_signaturen: Set[str] = set()
        self.nachbarn: List['ISCImmunNode'] = []
        self.isoliert_seit: Optional[float] = None
        
        # RAM-Schutz gegen Speicherlecks
        self._ereignis_log = deque(maxlen=1000)

    def registriere_nachbar(self, nachbar_knoten: 'ISCImmunNode'):
        if nachbar_knoten not in self.nachbarn:
            self.nachbarn.append(nachbar_knoten)

    def verarbeite_lokale_beobachtung(self, fremd_knoten_id: str, ist_anomal: bool, schad_signatur: Optional[str] = None):
        """Autonome Bewertung von Nachbarknoten durch lokale Sensorik/Heartbeats"""
        if self.status == KnotenStatus.ISOLIERT:
            return

        if ist_anomal:
            self.lokaler_anomalie_zaehler[fremd_knoten_id] = self.lokaler_anomalie_zaehler.get(fremd_knoten_id, 0) + 1
            
            # Botenstoff bereits bei der ersten Anomalie senden (für Proof of Concept)
            if schad_signatur:
                self.emitiere_botenstoff(schad_signatur)
            
            if self.lokaler_anomalie_zaehler[fremd_knoten_id] >= self.anomalie_schwelle:
                self._logge_ereignis(f"Knoten {fremd_knoten_id} lokal als ISOLIERT klassifiziert.")
        else:
            self.lokaler_anomalie_zaehler[fremd_knoten_id] = max(0, self.lokaler_anomalie_zaehler.get(fremd_knoten_id, 0) - 1)

    def emitiere_botenstoff(self, signatur: str):
        """Kaskadierende Emission des Botenstoffes an alle erreichbaren Nachbarn (Myzel-Prinzip)"""
        self.blockierte_ast_signaturen.add(signatur)
        botenstoff = MyzelBotenstoff(ursprung_knoten=self.knoten_id, schad_signatur=signatur, ttl=3)
        
        for nachbar in self.nachbarn:
            nachbar.empfange_botenstoff(botenstoff)

    def empfange_botenstoff(self, botenstoff: MyzelBotenstoff):
        """Autonome, praeventive Mutation der Filterregeln bei Botenstoff-Empfang"""
        if botenstoff.schad_signatur in self.blockierte_ast_signaturen:
            return  # Bereits immunisiert

        # Praeventive Mutation der lokalen Blockade-Schwellen
        self.blockierte_ast_signaturen.add(botenstoff.schad_signatur)
        self._logge_ereignis(f"Praeventive Immunisierung aktiv. Signatur {botenstoff.schad_signatur} blockiert.")

        # Exponentielle Weiterleitung falls TTL noch aktiv
        if botenstoff.ttl > 1:
            weitergeleiteter_botenstoff = MyzelBotenstoff(
                ursprung_knoten=botenstoff.ursprung_knoten,
                schad_signatur=botenstoff.schad_signatur,
                ttl=botenstoff.ttl - 1
            )
            for nachbar in self.nachbarn:
                nachbar.empfange_botenstoff(weitergeleiteter_botenstoff)

    def pruefe_quellcode_ausfuehrung(self, ast_signatur: str) -> bool:
        """Prüft, ob eine empfangene Code-Struktur lokal blockiert ist"""
        if ast_signatur in self.blockierte_ast_signaturen:
            self._logge_ereignis(f"BLOCKADE: Code mit Signatur {ast_signatur} praeventiv abgewiesen!")
            return False
        return True

    def _logge_ereignis(self, eintrag: str):
        self._ereignis_log.append(f"[{time.time():.2f}] {eintrag}")


if __name__ == "__main__":
    print("=" * 55)
    print("ISC-Immun v1.0 – Schwarm-Abwehrsystem Demo")
    print("=" * 55)
    
    knoten_a = ISCImmunNode("Drohne_Alpha")
    knoten_b = ISCImmunNode("Drohne_Beta")
    knoten_c = ISCImmunNode("Drohne_Gamma")
    
    knoten_a.registriere_nachbar(knoten_b)
    knoten_b.registriere_nachbar(knoten_a)
    knoten_b.registriere_nachbar(knoten_c)
    knoten_c.registriere_nachbar(knoten_b)
    
    schad_signatur = "AST_MALICIOUS_TEST"
    
    print("Test: Drohne_Alpha entdeckt Schadcode und sendet Botenstoff...")
    knoten_a.verarbeite_lokale_beobachtung("Sensor_XYZ", ist_anomal=True, schad_signatur=schad_signatur)
    
    print(f"Drohne_Alpha blockiert: {schad_signatur in knoten_a.blockierte_ast_signaturen}")
    print(f"Drohne_Beta blockiert: {schad_signatur in knoten_b.blockierte_ast_signaturen}")
    print(f"Drohne_Gamma blockiert: {schad_signatur in knoten_c.blockierte_ast_signaturen}")
    
    print("=" * 55)