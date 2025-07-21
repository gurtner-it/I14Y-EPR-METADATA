# EPD Metadata Publisher

Dieses Repository enthält ein Python-Skript zum automatisierten Publizieren und Aktualisieren von **FHIR ValueSets** auf der **I14Y-Plattform** des Bundes im Kontext des Elektronischen Patientendossiers (EPD).

## 🔍 Zweck

Die ValueSets sind zentrale semantische Bausteine für das EPD. Dieses Tool erlaubt es, neue oder aktualisierte `ValueSet`-Ressourcen im JSON-Format gemäss FHIR-Spezifikation via REST API auf die I14Y-Plattform zu übertragen.

---

## 📦 Voraussetzungen

- Python ≥ 3.8
- MacOS, Linux oder Windows
- Internetzugang zur I14Y-Produktionsumgebung
- API-Zugangsdaten (Client ID & Secret via eHealth Suisse / BIT)

---

## ⚙️ Installation (lokal auf macOS)

```bash
# 1. Repository klonen
git clone https://github.com/PeroGrgic/EPD_Metadata.git
cd EPD_Metadata

# 2. Virtuelle Umgebung erstellen
python3 -m venv .venv
source .venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt
