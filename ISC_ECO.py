"""
ISC_ECO.py
ISC-Patentfamilie – Modul 15
Deterministischer Energie-Gatekeeper fuer KI-generierten Code
"""

import ast
import hashlib
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import deque

class EcoStatus(Enum):
    BELLARD_OPTIMAL    = "bellard_optimal"
    STANDARD_EFFIZIENT = "standard_effizient"
    AKZEPTABEL         = "akzeptabel"
    BLOCKIERT          = "blockiert"


@dataclass
class EcoAnalyseBericht:
    code_hash: str
    final_score: float
    schwellwert: float
    status: EcoStatus
    ist_blockiert: bool
    optimierungshinweis: str


class ISCEcoNodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.penalty_score = 0.0
        self.bonus_score = 0.0
        self.erkannte_penalties = []
        self.erkannte_boni = []

    def visit_For(self, node):
        self.penalty_score += 25.0
        self.erkannte_penalties.append("Iteration (For)")
        self.generic_visit(node)

    def visit_While(self, node):
        self.penalty_score += 30.0
        self.erkannte_penalties.append("Iteration (While)")
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, (ast.LShift, ast.RShift)):
            self.bonus_score += 15.0
            self.erkannte_boni.append("Bitshift-Operation")
        elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
            self.bonus_score += 10.0
            self.erkannte_boni.append("Bitweise Logik")
        self.generic_visit(node)


class ISCEco:
    def __init__(self, schwellwert: float = 75.0):
        self.basis_schwellwert = schwellwert
        self.aktueller_schwellwert = schwellwert
        self._audit_log = deque(maxlen=1000)

    def setze_hardware_limit(self, batterie_prozent: float, temperatur_c: float):
        """Dynamische Anpassung des Schwellwerts an physische Hardware-Grenzwerte"""
        faktor = 1.0
        if batterie_prozent < 20.0:
            faktor *= 0.5
        if temperatur_c > 75.0:
            faktor *= 0.4
        self.aktueller_schwellwert = self.basis_schwellwert * faktor

    def analysiere(self, quellcode: str) -> EcoAnalyseBericht:
        code_hash = hashlib.sha256(quellcode.encode()).hexdigest()[:16]
        try:
            tree = ast.parse(quellcode)
            visitor = ISCEcoNodeVisitor()
            visitor.visit(tree)
            
            score = max(0.0, visitor.penalty_score - visitor.bonus_score)
            sw = self.aktueller_schwellwert

            if score <= sw * 0.5:
                status = EcoStatus.BELLARD_OPTIMAL
                blockiert = False
            elif score <= sw:
                status = EcoStatus.STANDARD_EFFIZIENT
                blockiert = False
            elif score <= sw * 1.5:
                status = EcoStatus.AKZEPTABEL
                blockiert = False
            else:
                status = EcoStatus.BLOCKIERT
                blockiert = True

            hinweis = "Code energetisch freigegeben." if not blockiert else "Ausfuehrung verweigert: Ineffiziente Strukturmuster detektiert."
            
            bericht = EcoAnalyseBericht(code_hash, score, sw, status, blockiert, hinweis)
            self._audit_log.append(bericht)
            return bericht

        except Exception as e:
            return EcoAnalyseBericht(code_hash, 999.0, self.aktueller_schwellwert, EcoStatus.BLOCKIERT, True, f"Syntax-Fehler: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("ISC-ECO: PHYSISCH-GEKOPPELTE HARDWARE-VALIDIERUNG")
    print("=" * 60)

    eco_system = ISCEco(schwellwert=50.0)
    
    schwerer_code = """
def rechen_intensiv():
    for i in range(100):
        for j in range(100):
            print(i, j)
"""

    print("[Status: Normalbetrieb] Batterie: 100%, Temperatur: 35°C")
    eco_system.setze_hardware_limit(batterie_prozent=100.0, temperatur_c=35.0)
    bericht_normal = eco_system.analysiere(schwerer_code)
    print(f" -> Score: {bericht_normal.final_score}, Schwellwert: {bericht_normal.schwellwert}")
    print(f" -> Status: {bericht_normal.status.value.upper()} | Blockiert: {bericht_normal.ist_blockiert}\n")

    print("[Status: KRITISCHER ENERGIEEINBRUCH] Batterie: 15%, Temperatur: 80°C")
    eco_system.setze_hardware_limit(batterie_prozent=15.0, temperatur_c=80.0)
    bericht_krise = eco_system.analysiere(schwerer_code)
    print(f" -> Score: {bericht_krise.final_score}, Schwellwert: {bericht_krise.schwellwert}")
    print(f" -> Status: {bericht_krise.status.value.upper()} | Blockiert: {bericht_krise.ist_blockiert}")
    print(f" -> Hinweis: {bericht_krise.optimierungshinweis}")
    print("=" * 60)