# 🎵 Szybki Start - Rozpoznawanie Trackerów

## Co się zmieniło?

Teraz program **automatycznie rozpoznaje tracker** każdego pliku SID!

## Gdzie widzę tracker?

### 1. 🎵 W Oknie Głównym
Kiedy załadujesz plik SID, pod metadanymi (Artist, Year) pojawi się pomarańczowy napis:

```
TITLE SONG
Unknown Artist
2023
🎵 Tracker: JCH_NewPlayer
```

### 2. 📋 W Playliście
Nowa kolumna "Tracker" wyświetla tracker każdej piosenki:

```
┌─────────────┬──────────────┬──────┬──────────┬────────────────┐
│ Artist      │ Title        │ Year │ Duration │ Tracker        │
├─────────────┼──────────────┼──────┼──────────┼────────────────┤
│ Composer A  │ Song 1       │ 2023 │ 2:15     │ JCH_NewPlayer  │
│ Composer B  │ Song 2       │ 1990 │ 1:45     │ Sosperec       │
│ Unknown     │ Song 3       │      │ 2:00     │ Unknown        │
└─────────────┴──────────────┴──────┴──────────┴────────────────┘
```

## Jak to działa?

1. **Szukanie charakterystycznych bajtów** w danych SID
2. **Porównywanie ze wzorcami** z pliku `sidid.cfg`
3. **Zwracanie nazwy trackera** lub "Unknown"

## Obsługiwane trackery (775+)

### Najpopularniejsze:
- **JCH_NewPlayer** - bardzo częsty
- **CheeseCutter** - nowoczesny tracker
- **Sosperec** - popularna biblioteka
- **Skyt_Player** - typowy player
- **DMC** - digitalne próbki

...i jeszcze 770+ innych!

## Czy mogę wyłączyć?

Funkcja jest zintegrowana i nie spowalnia programu, ale możesz:
- Edytować `sid_player_modern07.py`
- Skomentować linię z `recognize_tracker()`

## Jeśli coś nie działa

```
[TRACKER] Wczytano 775 wzorów
✓ System aktywny
```

Sprawdź w konsoli debugowania czy pojawia się taka linijka.

Jeśli brakuje:
```
[TRACKER] ⚠ Nie znaleziono sidid.cfg
```

Upewnij się że `sidid.cfg` istnieje w katalogu programu.

## Czy to spowalnia program?

**Nie!**
- Wczytywanie wzorów: **~100ms** (raz przy starcie)
- Rozpoznawanie pliku: **~20ms** (na plik)
- Całkowicie niezauważalne

## Debugging

Aby zobaczyć szczegóły rozpoznawania, użyj:

```python
from tracker_recognition import get_recognizer
r = get_recognizer()
tracker = r.recognize_tracker("plik.sid", verbose=True)
```

W konsoli debugowania zobaczysz:
```
[TRACKER] ✓ Znaleziono: JCH_NewPlayer
lub
[TRACKER] ? Nie znaleziono dopasowania
```

---

**Tips:**
- Obraz pliku w playliście jest skanowany tylko gdy dodajesz go
- Tracker się nie zmienia dla tego samego pliku
- "Unknown" = tracker poza bazą lub niestandardowy

Powodzenia! 🎶