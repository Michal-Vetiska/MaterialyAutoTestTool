# Material Auto Test Tool

Moderní univerzální desktopová aplikace pro testování chatbot materiálů a scénářů.

## Požadavky
- Python 3.8+
- Knihovny: PyQt5, requests, pyyaml

Nainstaluj je příkazem:
```bash
pip3 install PyQt5 requests pyyaml
```

## Spuštění aplikace
1. Zkopíruj všechny soubory do libovolné složky.
2. Spusť aplikaci:
   ```bash
   python3 MaterialAutoTestToolApp_qt.py
   ```

## Použití
1. **Zadej endpoint chatbota** (např. `http://127.0.0.1:1234`) a ulož.
2. **Vlož obsah materiálu** (context1.txt) a YAML scénáře do příslušných polí (nebo použij tlačítko „Vložit ze schránky“).
3. Klikni na **Spustit test**.
4. Výsledky a souhrn se zobrazí v aplikaci.

- Všechny potřebné soubory (`context1.txt`, `test_core_messenger_and_inbox.yaml`, `endpoint.txt`) se ukládají automaticky do aktuální složky.
- Aplikace je přenositelná a nevyžaduje žádné úpravy kódu.

## Formát YAML souboru

YAML soubor s testovacími scénáři musí mít následující strukturu:

```yaml
tests:
  default:
    - id: 1
      question: "Tvoje testovací otázka?"
      expected_keywords:
        - "klíčové slovo 1"
        - "klíčové slovo 2"
        - "klíčové slovo 3"

    - id: 2
      question: "Další testovací otázka?"
      expected_keywords:
        - "další klíčové slovo"
        - "ještě jedno"
```

### Struktura testu:
- **`tests:`** - Hlavní klíč pro všechny testy
- **`default:`** - Sekce obsahující seznam testů
- **`id:`** - Jedinečné číslo testu (číslo)
- **`question:`** - Otázka, která se pošle chatbotu (text v uvozovkách)
- **`expected_keywords:`** - Seznam očekávaných klíčových slov, která by měla být v odpovědi (seznam řetězců)

### Příklad:
```yaml
tests:
  default:
    - id: 1
      question: "Jaké aplikace jsou součástí ekosystému Core.Admin?"
      expected_keywords:
        - "Core.Admin"
        - "Core.Admin.Api"
        - "Core.ARR"
        - "Core.Persona"
        - "Core.Identity"
```

**Důležité:**
- Každý test musí mít unikátní `id`
- `question` musí být v uvozovkách
- `expected_keywords` je seznam, každé klíčové slovo na samostatném řádku s pomlčkou
- Odsazení musí být konzistentní (doporučeno 2 mezery)

## Poznámky
- Pokud používáš Windows, změň příkaz `python3` na `python` podle své instalace.
- Pro balení do .app nebo .exe lze použít PyInstaller nebo Platypus (návod na vyžádání).

---

**Autor:**
Michal Vetiška
