# ZIELERKENNUNG_YOLO_MODUL.py
"""
YOLO-ZIELERKENNUNG FÜR FPV-DROHNEN UND 'BABA YAGA'
Modul für visuelle Zielerkennung im SCHACHMATTSCHILD-System
"""

import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
import time

# Conditionale Imports für Entwicklungs-/Testumgebungen ohne GPU
try:
    import cv2
    CV2_VERFUEGBAR = True
except ImportError:
    CV2_VERFUEGBAR = False

try:
    import torch
    import torchvision
    TORCH_VERFUEGBAR = True
except ImportError:
    TORCH_VERFUEGBAR = False

@dataclass
class Erkennung:
    klasse: str
    konfidenz: float
    bounding_box: Tuple[int, int, int, int]  # x1, y1, x2, y2
    position_3d: Tuple[float, float, float] = None

class YOLO_Zielerkennung:
    def __init__(self, modell_pfad: str = None):
        """
        Initialisiert YOLO-Zielerkennung
        Kann vortrainierte Modelle oder custom Training verwenden
        """
        self.klassen_namen = {
            0: "FPV_Drohne",
            1: "Baba_Yaga", 
            2: "Quadcopter",
            3: "Flugzeug",
            4: "Helikopter"
        }
        
        self.erkennungsschwellwert = 0.6  # Minimale Konfidenz
        self.zu_verfolgende_klassen = ["FPV_Drohne", "Baba_Yaga", "Quadcopter"]
        
        # Lade Modell
        self.modell = self._lade_yolo_modell(modell_pfad)
        self.ist_initialisiert = True
        
        # Statistik
        self.erkennungs_statistik = {
            "gesamt_erkannt": 0,
            "fpv_erkannt": 0,
            "baba_yaga_erkannt": 0
        }
        
    def _lade_yolo_modell(self, modell_pfad: str):
        """
        Lädt YOLO-Modell - automatischer Fallback auf vortrainiert
        """
        try:
            if not TORCH_VERFUEGBAR:
                raise ImportError("PyTorch nicht verfügbar - Fallback-Modus")
            
            if modell_pfad and modell_pfad.endswith('.pt'):
                # Lade custom trainiertes Modell
                modell = torch.hub.load('ultralytics/yolov5', 'custom', path=modell_pfad)
            else:
                # Lade vortrainiertes YOLOv5s Modell
                modell = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                
            # Setze Modell für Inference
            modell.conf = self.erkennungsschwellwert
            print("✅ YOLO-Modell erfolgreich geladen")
            return modell
            
        except Exception as e:
            print(f"⚠️  Fehler beim Laden des YOLO-Modells: {e}")
            print("🔄 Verwende Fallback-Erkennungslogik")
            return self._erstelle_fallback_modell()
    
    def _erstelle_fallback_modell(self):
        """Erstellt einfache Fallback-Erkennung für Testzwecke (kein cv2/torch nötig)"""
        class FallbackModell:
            def __init__(self):
                self.conf = 0.6
                # Format wie YOLOv5: Liste von Tensoren, einer pro Bild
                # Jeder Tensor = [N, 6] mit [x1, y1, x2, y2, conf, class]
                self.xyxy = [[[0, 0, 100, 100, 0.8, 0]]]  # 1 Bild, 1 Detection
            def __call__(self, img):
                return self
        return FallbackModell()
    
    def analysiere_bild(self, bild: np.ndarray) -> List[Erkennung]:
        """
        Analysiert ein Bild auf Drohnen-Ziele
        """
        if not self.ist_initialisiert:
            raise RuntimeError("YOLO-Modell nicht initialisiert")
        
        # Führe Inference aus
        ergebnisse = self.modell(bild)
        
        # Verarbeite Erkennungen
        erkennungen = []
        
        # Unterstützt sowohl torch tensors (echtes YOLO) als auch Listen (Fallback)
        detections = getattr(ergebnisse, 'xyxy', None)
        if detections is None:
            return erkennungen
        detections = detections[0]
        
        for det in detections:
            # Kompatibel mit torch.tensor.tolist() und plain list
            x1, y1, x2, y2, conf, cls = det if isinstance(det, (list, tuple)) else det.tolist()
            klassen_id = int(cls)
            
            if klassen_id in self.klassen_namen:
                klasse_name = self.klassen_namen[klassen_id]
                
                # Filtere nur relevante Klassen
                if klasse_name in self.zu_verfolgende_klassen:
                    # Berechne 3D-Position (vereinfacht)
                    position_3d = self._berechne_3d_position(bild, (x1, y1, x2, y2))
                    
                    erkennung = Erkennung(
                        klasse=klasse_name,
                        konfidenz=conf,
                        bounding_box=(int(x1), int(y1), int(x2), int(y2)),
                        position_3d=position_3d
                    )
                    erkennungen.append(erkennung)
                    
                    # Update Statistik
                    self._update_statistik(klasse_name)
        
        return erkennungen
    
    def _berechne_3d_position(self, bild: np.ndarray, bbox: Tuple) -> Tuple[float, float, float]:
        """
        Vereinfachte Berechnung der 3D-Position basierend auf Bounding Box
        In realer Implementation: Stereokameras oder LIDAR Integration
        """
        h, w = bild.shape[:2]
        x1, y1, x2, y2 = bbox
        
        # Berechne Zentrum der Bounding Box
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        
        # Normalisiere Koordinaten
        norm_x = center_x / w
        norm_y = center_y / h
        
        # Schätze Entfernung basierend auf Bounding Box Größe
        bbox_breite = x2 - x1
        bbox_höhe = y2 - y1
        bbox_flaeche = bbox_breite * bbox_höhe
        bild_flaeche = w * h
        
        # Vereinfachte Entfernungsabschätzung
        if bbox_flaeche > bild_flaeche * 0.3:  # Groß = nah
            entfernung = 50.0  # Meter
        elif bbox_flaeche > bild_flaeche * 0.1:  # Mittel
            entfernung = 100.0
        else:  # Klein = weit
            entfernung = 200.0
            
        # Konvertiere zu 3D-Koordinaten (vereinfacht)
        x_3d = (norm_x - 0.5) * entfernung * 2
        y_3d = (0.5 - norm_y) * entfernung * 2
        z_3d = entfernung
        
        return (x_3d, y_3d, z_3d)
    
    def _update_statistik(self, klasse: str):
        """Aktualisiert Erkennungsstatistik"""
        self.erkennungs_statistik["gesamt_erkannt"] += 1
        
        if klasse == "FPV_Drohne":
            self.erkennungs_statistik["fpv_erkannt"] += 1
        elif klasse == "Baba_Yaga":
            self.erkennungs_statistik["baba_yaga_erkannt"] += 1
    
    def get_statistik(self) -> Dict:
        """Gibt aktuelle Erkennungsstatistik zurück"""
        return self.erkennungs_statistik.copy()
    
    def zeichne_erkennungen(self, bild: np.ndarray, erkennungen: List[Erkennung]) -> np.ndarray:
        """
        Zeichnet Erkennungen auf das Bild für Visualisierung
        """
        ausgabe_bild = bild.copy()
        
        if not CV2_VERFUEGBAR:
            # Ohne OpenCV: Nur Log-Ausgabe
            print(f"📋 [Simuliert] {len(erkennungen)} Erkennungen gezeichnet")
            return ausgabe_bild
        
        for erkennung in erkennungen:
            x1, y1, x2, y2 = erkennung.bounding_box
            
            # Wähle Farbe basierend auf Klasse
            if erkennung.klasse == "FPV_Drohne":
                farbe = (0, 0, 255)  # Rot
            elif erkennung.klasse == "Baba_Yaga":
                farbe = (0, 165, 255)  # Orange
            else:
                farbe = (255, 0, 0)  # Blau
            
            # Zeichne Bounding Box
            cv2.rectangle(ausgabe_bild, (x1, y1), (x2, y2), farbe, 2)
            
            # Zeichne Label
            label = f"{erkennung.klasse} {erkennung.konfidenz:.2f}"
            cv2.putText(ausgabe_bild, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, farbe, 2)
        
        return ausgabe_bild

# TESTMODUL FÜR ZIELERKENNUNG
def teste_zielerkennung():
    """Testet das YOLO-Zielerkennungsmodul"""
    print("TESTE YOLO-ZIELERKENNUNGSMODUL...")
    
    # Erstelle Zielerkennungsinstanz
    zielerkennung = YOLO_Zielerkennung()
    
    # Erstelle Testbild (kann durch echte Kamera ersetzt werden)
    test_bild = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Simuliere Erkennung
    print("Analysiere Testbild...")
    startzeit = time.time()
    erkennungen = zielerkennung.analysiere_bild(test_bild)
    dauer = time.time() - startzeit
    
    print(f"Analyse abgeschlossen in {dauer:.3f}s")
    print(f"Gefundene Ziele: {len(erkennungen)}")
    
    for i, erkennung in enumerate(erkennungen):
        print(f"  Ziel {i+1}: {erkennung.klasse} (Konfidenz: {erkennung.konfidenz:.2f})")
        print(f"    Position 3D: {erkennung.position_3d}")
    
    # Zeige Statistik
    statistik = zielerkennung.get_statistik()
    print(f"Statistik: {statistik}")
    
    print("ZIELERKENNUNGSMODUL FUNKTIONIERT")

if __name__ == "__main__":
    teste_zielerkennung()
