"""
ISC_CHAMAELEON.py
ISC-Patentfamilie – Modul 17
Deterministisches Tarnungs- und Anpassungssystem fuer autonome Schwaerme
"""

import hashlib
import hmac
import time
import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TarnModus(Enum):
    NORMAL          = "normal"
    FREQUENZ_WECHSEL = "frequenz_wechsel"
    TIMING_VARIATION = "timing_variation"
    PROTOKOLL_WECHSEL = "protokoll_wechsel"
    STILLES_SENDEN   = "stilles_senden"
    NOTFALL_MINIMUM  = "notfall_minimum"


class BedrohungsStufe(Enum):
    KEINE    = 0
    NIEDRIG  = 1
    MITTEL   = 2
    HOCH     = 3
    KRITISCH = 4


@dataclass
class KommunikationsProfil:
    frequenz_hz: float = 2400.0
    sendeleistung_dbm: float = 20.0
    timing_intervall_ms: float = 100.0
    protokoll: str = "ISC_STANDARD"
    tarn_modus: TarnModus = TarnModus.NORMAL
    letzter_wechsel: float = 0.0


class ISCChamaeleon:
    PROFILE = {
        TarnModus.NORMAL: {'frequenz_hz': 2400.0, 'sendeleistung_dbm': 20.0, 'timing_intervall_ms': 100.0, 'protokoll': 'ISC_STANDARD'},
        TarnModus.FREQUENZ_WECHSEL: {'frequenz_hz': 5800.0, 'sendeleistung_dbm': 15.0, 'timing_intervall_ms': 80.0, 'protokoll': 'ISC_STANDARD'},
        TarnModus.TIMING_VARIATION: {'frequenz_hz': 2400.0, 'sendeleistung_dbm': 20.0, 'timing_intervall_ms': 73.0, 'protokoll': 'ISC_TIMING_V2'},
        TarnModus.PROTOKOLL_WECHSEL: {'frequenz_hz': 915.0, 'sendeleistung_dbm': 25.0, 'timing_intervall_ms': 150.0, 'protokoll': 'ISC_BACKUP'},
        TarnModus.STILLES_SENDEN: {'frequenz_hz': 433.0, 'sendeleistung_dbm': 5.0, 'timing_intervall_ms': 500.0, 'protokoll': 'ISC_SILENT'},
        TarnModus.NOTFALL_MINIMUM: {'frequenz_hz': 121.5, 'sendeleistung_dbm': 30.0, 'timing_intervall_ms': 1000.0, 'protokoll': 'ISC_EMERGENCY'},
    }

    def __init__(self, einheit_id: str, hardware_seed: str = "", wechsel_cooldown_s: float = 5.0):
        self.einheit_id = einheit_id
        self._hardware_key = (hardware_seed or einheit_id).encode()
        self._cooldown = wechsel_cooldown_s
        self._aktuelles_profil = KommunikationsProfil()
        self._sequenz_index = 0
        self._wechsel_sequenz = self._generiere_wechsel_sequenz()
        self._bedrohungs_log: List = []  # wird bei Bedarf gefüllt

    def _generiere_wechsel_sequenz(self) -> List[TarnModus]:
        hmac_gen = hmac.new(self._hardware_key, b"PROFIL_WECHSEL_SEQUENCE", hashlib.sha256)
        seed_hash = hmac_gen.hexdigest()
        
        sequenz = []
        modi = [m for m in TarnModus if m != TarnModus.NOTFALL_MINIMUM]
        for i in range(0, len(seed_hash) - 1, 2):
            index = int(seed_hash[i:i+2], 16) % len(modi)
            sequenz.append(modi[index])
        return sequenz

    def erkenne_bedrohung(self, signal_staerke_dbm: float, paket_fehlerrate: float,
                           unbekannte_sender: int, frequenz_stoerung: bool) -> BedrohungsStufe:
        score = 0
        if signal_staerke_dbm < -90: score += 1
        if signal_staerke_dbm < -100: score += 1
        if paket_fehlerrate > 0.1: score += 1
        if paket_fehlerrate > 0.3: score += 1
        if unbekannte_sender > 0: score += 1
        if unbekannte_sender > 3: score += 1
        if frequenz_stoerung: score += 2

        if score == 0: return BedrohungsStufe.KEINE
        elif score <= 1: return BedrohungsStufe.NIEDRIG
        elif score <= 3: return BedrohungsStufe.MITTEL
        elif score <= 5: return BedrohungsStufe.HOCH
        else: return BedrohungsStufe.KRITISCH

    def reagiere_auf_bedrohung(self, stufe: BedrohungsStufe, bedrohungs_typ: str = "unbekannt") -> KommunikationsProfil:
        jetzt = time.time()
        cooldown_ok = (jetzt - self._aktuelles_profil.letzter_wechsel >= self._cooldown)

        if stufe == BedrohungsStufe.KEINE:
            neuer_modus = TarnModus.NORMAL
        elif stufe == BedrohungsStufe.KRITISCH:
            neuer_modus = TarnModus.NOTFALL_MINIMUM
        elif cooldown_ok:
            neuer_modus = self._wechsel_sequenz[self._sequenz_index % len(self._wechsel_sequenz)]
            self._sequenz_index += 1
        else:
            return self._aktuelles_profil

        profil_daten = self.PROFILE.get(neuer_modus, self.PROFILE[TarnModus.NORMAL])
        self._aktuelles_profil = KommunikationsProfil(
            frequenz_hz=profil_daten['frequenz_hz'],
            sendeleistung_dbm=profil_daten['sendeleistung_dbm'],
            timing_intervall_ms=profil_daten['timing_intervall_ms'],
            protokoll=profil_daten['protokoll'],
            tarn_modus=neuer_modus,
            letzter_wechsel=jetzt
        )
        return self._aktuelles_profil

    def berechne_naechste_sendezeit(self) -> float:
        basis = self._aktuelles_profil.timing_intervall_ms
        hmac_step = hmac.new(self._hardware_key, f"STEP_{self._sequenz_index}".encode(), hashlib.sha256)
        hash_val = hmac_step.hexdigest()
        
        variation = (int(hash_val[:4], 16) % 40) - 20  # -20 bis +20 ms Jitter
        self._sequenz_index += 1
        return (basis + variation) / 1000.0

    def status(self) -> Dict:
        return {
            'einheit_id': self.einheit_id,
            'modus': self._aktuelles_profil.tarn_modus.value,
            'frequenz_hz': self._aktuelles_profil.frequenz_hz,
            'protokoll': self._aktuelles_profil.protokoll,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 55)
    print("ISC-Chamaeleon v1.0 – Anpassungssystem Demo")
    print("=" * 55)

    chamaeleon = ISCChamaeleon("Drohne_Alpha", hardware_seed="ISC_SEED_2026")

    # Normalbetrieb
    stufe = chamaeleon.erkenne_bedrohung(-70, 0.01, 0, False)
    profil = chamaeleon.reagiere_auf_bedrohung(stufe)
    print(f"Normal: {chamaeleon.status()}")

    # Mittlere Bedrohung
    stufe = chamaeleon.erkenne_bedrohung(-95, 0.2, 2, False)
    profil = chamaeleon.reagiere_auf_bedrohung(stufe, "Stoersignal")
    print(f"Mittel: {chamaeleon.status()}")

    # Kritische Bedrohung
    stufe = chamaeleon.erkenne_bedrohung(-105, 0.5, 5, True)
    profil = chamaeleon.reagiere_auf_bedrohung(stufe, "Jammer erkannt")
    print(f"Kritisch: {chamaeleon.status()}")

    print("=" * 55)