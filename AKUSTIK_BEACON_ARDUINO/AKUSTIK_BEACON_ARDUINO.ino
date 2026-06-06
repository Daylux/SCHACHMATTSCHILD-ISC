/**
 * AKUSTIK_BEACON_ARDUINO.ino
 * ===========================
 * SCHACHMATTSCHILD – ISC-A Bridge V3
 * Akustischer Frequenzsprung-Sender (18 kHz – 22 kHz)
 *
 * Implementiert den JAR-Algorithmus (Jamming Acoustic Resilience):
 * - Deterministische Frequenzsprünge im Ultraschallband
 * - 500 Hz Raster, 9 Stufen (18.0 / 18.5 / 19.0 / ... / 22.0 kHz)
 * - Anti-Jamming durch Frequenz-Hopping
 * - Synchronisation über Schwarm-Taktgeber
 *
 * Hardware: Arduino Nano/Uno (ATmega328P, 16 MHz)
 * Ausgang:  OC1A (Pin 9) – PWM über Timer1
 * Optional: HC-12/Serial für Debug
 *
 * Autor: Dmitrij Medkov / Exi
 * Datum: Juni 2026
 * Lizenz: ISC (Industrial Security Cloud)
 */

// ============================================================================
// KONFIGURATION
// ============================================================================

// Frequenzbereich (JAR-Algorithmus)
const float FREQ_MIN = 18000.0;   // 18 kHz – Ultraschall-Untergrenze
const float FREQ_MAX = 22000.0;   // 22 kHz – Ultraschall-Obergrenze
const float FREQ_SCHRITT = 500.0; // 500 Hz Raster

// Timing
const unsigned long HOP_INTERVAL_MS = 50;   // Frequenzwechsel alle 50 ms
const unsigned long BEACON_INTERVAL_MS = 2000; // Beacon-Impuls alle 2 s
const unsigned long SERIAL_BAUD = 115200;

// PWM-Pin (Timer1 OC1A = Pin 9 auf Uno/Nano)
const int PWM_PIN = 9;

// ============================================================================
// GLOBALE VARIABLEN
// ============================================================================

// JAR-Zustand
float aktuelle_frequenz = FREQ_MIN;
unsigned long letzter_hop = 0;
unsigned long letzter_beacon = 0;
bool jar_aktiv = true;
int hop_zaehler = 0;

// Schwarm-Synchronisation (wird über Serial gesetzt)
unsigned long schwarm_takt = 0;
uint8_t schwarm_id = 0;

// ============================================================================
// TIMER1 INITIALISIERUNG (18-22 kHz PWM)
// ============================================================================

/**
 * Initialisiert Timer1 im CTC-Modus für präzise Frequenzerzeugung.
 * 
 * Timer1 = 16-Bit Timer auf ATmega328P (16 MHz)
 * Modus: CTC (Clear Timer on Compare Match), nicht-invertierend
 * Ausgang: OC1A (Pin 9)
 * 
 * Frequenz = F_CPU / (2 * prescaler * (OCR1A + 1))
 * OCR1A = F_CPU / (2 * prescaler * Frequenz) - 1
 * 
 * Für 18 kHz: OCR1A = 16000000 / (2*1*18000) - 1 = 443
 * Für 22 kHz: OCR1A = 16000000 / (2*1*22000) - 1 = 362
 */
void timer1_init(float frequenz_hz) {
  // Timer1 stoppen
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  
  // OCR1A berechnen (auf nächsten Integer runden)
  uint16_t ocr = (uint16_t)(F_CPU / (2.0 * 1.0 * frequenz_hz) + 0.5) - 1;
  
  // Begrenzung für 16-Bit Timer
  if (ocr > 65535) ocr = 65535;
  if (ocr < 2) ocr = 2;
  
  OCR1A = ocr;
  
  // CTC-Modus (WGM1 = 4): Zähler bis OCR1A, dann Reset
  // Nicht-invertierend: COM1A = 2 (Toggle auf OC1A bei Match)
  TCCR1A |= (1 << COM1A0);  // Toggle OC1A on Compare Match
  TCCR1B |= (1 << WGM12);   // CTC Mode
  
  // Prescaler = 1 (CS10 = 1): Keine Vorteilung
  TCCR1B |= (1 << CS10);
  
  // Pin 9 als Ausgang (OC1A)
  pinMode(PWM_PIN, OUTPUT);
}

/**
 * Setzt eine neue Frequenz durch Neuberechnung von OCR1A.
 */
void setze_frequenz(float frequenz_hz) {
  // Begrenzung auf Ultraschallband
  if (frequenz_hz < FREQ_MIN) frequenz_hz = FREQ_MIN;
  if (frequenz_hz > FREQ_MAX) frequenz_hz = FREQ_MAX;
  
  aktuelle_frequenz = frequenz_hz;
  
  // Timer mit neuer Frequenz neu initialisieren
  timer1_init(frequenz_hz);
}

// ============================================================================
// JAR-ALGORITHMUS (Jamming Acoustic Resilience)
// ============================================================================

/**
 * Führt einen deterministischen Frequenzsprung durch.
 * 
 * Algorithmus:
 * 1. Erhöhe Frequenz um FREQ_SCHRITT (500 Hz)
 * 2. Bei Überschreitung von FREQ_MAX → Zurücksetzen auf FREQ_MIN
 * 3. Synchronisation über Schwarm-Takt
 * 
 * Dies entspricht dem JAR-Algorithmus aus ISC_A_BRIDGE_CONTROLLER.py
 */
void jar_frequenzwechsel() {
  if (!jar_aktiv) return;
  
  float neue_frequenz = aktuelle_frequenz + FREQ_SCHRITT;
  
  // Wrap-Around bei Erreichen der Obergrenze
  if (neue_frequenz > FREQ_MAX) {
    neue_frequenz = FREQ_MIN;
  }
  
  setze_frequenz(neue_frequenz);
  hop_zaehler++;
}

// ============================================================================
// BEACON-SIGNAL
// ============================================================================

/**
 * Sendet einen akustischen Beacon-Impuls zur Schwarm-Identifikation.
 * 
 * Der Beacon ist ein kurzer Frequenz-Durchlauf (18→20→22 kHz)
 * als "Freund/Feind"-Kennung.
 */
void sende_beacon() {
  // Kurzer Sweep 18→22 kHz als Identifikation
  for (float f = FREQ_MIN; f <= FREQ_MAX; f += FREQ_SCHRITT * 2) {
    setze_frequenz(f);
    delay(2);  // 2 ms pro Stufe = ~10 ms Gesamtdauer
  }
  
  // Zurück zur Betriebsfrequenz
  setze_frequenz(aktuelle_frequenz);
}

// ============================================================================
// SERIAL-KOMMANDO INTERPRETER
// ============================================================================

/**
 * Verarbeitet eingehende Serial-Kommandos:
 * 
 * "JAR=1"    → JAR aktivieren
 * "JAR=0"    → JAR deaktivieren
 * "FREQ=20000" → Manuelle Frequenz setzen (20 kHz)
 * "BEACON"   → Beacon manuell auslösen
 * "STATUS"   → Status ausgeben
 * "ID=5"     → Schwarm-ID setzen
 */
void verarbeite_kommando(String cmd) {
  cmd.trim();
  
  if (cmd.startsWith("JAR=")) {
    jar_aktiv = cmd.substring(4).toInt() == 1;
    Serial.print("JAR: ");
    Serial.println(jar_aktiv ? "AKTIV" : "AUS");
    
  } else if (cmd.startsWith("FREQ=")) {
    float f = cmd.substring(5).toFloat();
    if (f >= FREQ_MIN && f <= FREQ_MAX) {
      setze_frequenz(f);
      Serial.print("FREQ: ");
      Serial.print(f);
      Serial.println(" Hz");
    }
    
  } else if (cmd == "BEACON") {
    sende_beacon();
    Serial.println("BEACON: GESENDET");
    
  } else if (cmd == "STATUS") {
    Serial.println("=== STATUS ===");
    Serial.print("Frequenz: "); Serial.print(aktuelle_frequenz); Serial.println(" Hz");
    Serial.print("JAR: "); Serial.println(jar_aktiv ? "AN" : "AUS");
    Serial.print("Hop #: "); Serial.println(hop_zaehler);
    Serial.print("Schwarm-ID: "); Serial.println(schwarm_id);
    Serial.print("Takt: "); Serial.println(schwarm_takt);
    
  } else if (cmd.startsWith("ID=")) {
    schwarm_id = (uint8_t)cmd.substring(3).toInt();
    Serial.print("SCHWARM-ID: ");
    Serial.println(schwarm_id);
  }
}

// ============================================================================
// ARDUINO SETUP
// ============================================================================

void setup() {
  // Serial für Debug und Steuerung
  Serial.begin(SERIAL_BAUD);
  while (!Serial) { delay(10); }
  
  Serial.println();
  Serial.println("========================================");
  Serial.println("SCHACHMATTSCHILD – Akustik Beacon V3.0");
  Serial.println("JAR-Algorithmus (18-22 kHz)");
  Serial.println("========================================");
  
  // Timer1 initialisieren bei Startfrequenz (18 kHz)
  setze_frequenz(FREQ_MIN);
  
  Serial.print("Startfrequenz: ");
  Serial.print(aktuelle_frequenz);
  Serial.println(" Hz");
}

// ============================================================================
// ARDUINO LOOP
// ============================================================================

void loop() {
  unsigned long jetzt = millis();
  
  // 1. Serial-Kommandos verarbeiten
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    verarbeite_kommando(cmd);
  }
  
  // 2. JAR-Frequenzsprung (alle HOP_INTERVAL_MS)
  if (jar_aktiv && (jetzt - letzter_hop >= HOP_INTERVAL_MS)) {
    jar_frequenzwechsel();
    letzter_hop = jetzt;
  }
  
  // 3. Beacon-Impuls (alle BEACON_INTERVAL_MS)
  if (jetzt - letzter_beacon >= BEACON_INTERVAL_MS) {
    // Nur wenn JAR aktiv und nicht im Debug-Modus
    if (jar_aktiv) {
      // Kurz pausieren für Beacon, dann weiter
      bool jar_merker = jar_aktiv;
      jar_aktiv = false;
      sende_beacon();
      jar_aktiv = jar_merker;
    }
    letzter_beacon = jetzt;
  }
}
