<div align="center">

<img src="custom_components/aster_meteo/brand/logo@2x.png" alt="A-Ster.pl Meteo" width="360" />

# A-Ster.pl Meteo Integration

**Nieoficjalna integracja: bieżące dane z sieci agrometeo A-Ster w Home Assistant, dla dowolnej liczby stacji.**

Temperatura, wilgotność, wiatr, opady, wilgotność gleby i więcej z publicznego kanału ASTERGate
IUNG-PIB w Puławach. Konfiguracja z poziomu interfejsu, instalacja przez HACS, jedno urządzenie na
stację.

[![Validate](https://github.com/RikoDEV/aster-meteo-ha-integration/actions/workflows/validate.yaml/badge.svg)](https://github.com/RikoDEV/aster-meteo-ha-integration/actions/workflows/validate.yaml)
[![HACS: Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant: 2025.3+](https://img.shields.io/badge/Home%20Assistant-2025.3%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=RikoDEV&repository=aster-meteo-ha-integration&category=integration)

[Szybki start](#szybki-start) · [Funkcje](#funkcje) · [Encje](#encje) · [Jak znaleźć numer stacji](#jak-znaleźć-numer-stacji) · [Migracja](#migracja-ze-starej-platformy-makow_weather) · [English](README.md)

</div>

---

## Funkcje

**Stacje**
- Dodawaj dowolną liczbę stacji z interfejsu. Każda stacja to *podwpis* integracji, więc **Dodaj
  stację meteo** jest przyciskiem na stronie integracji
- Jedno urządzenie na stację, z nazwą wybraną przez Ciebie (na przykład `Maków Weather`)
- Własna częstotliwość odświeżania i czas "nieaktualności" dla każdej stacji: stacja, która
  przestaje raportować, staje się niedostępna zamiast pokazywać stare liczby w nieskończoność

**Odczyty**
- Temperatura powietrza i przy gruncie, wilgotność, ciśnienie, prędkość i kierunek wiatru
- Opady dziś i wczoraj, rodzaj opadu, czas nasłonecznienia, zwilżenie liści
- Temperatura i wilgotność gleby na 10, 20, 30, 40, 60 i 100 cm, PM2.5 i PM10
- Tworzone są tylko czujniki, które stacja naprawdę ma. Wiele stacji nie ma barometru ani sond
  glebowych; takie encje pojawią się same, gdy stacja zacznie je raportować

**Pogoda i diagnostyka**
- Encja `weather` dla każdej stacji z aktualnymi warunkami, wiatrem i punktem rosy
- Diagnostyczny czujnik *Ostatni pomiar*, który pozostaje dostępny, gdy stacja milczy
- Tłumaczenia: angielski i polski

## Szybki start

1. Kliknij przycisk na górze tej strony, a następnie **Pobierz** w HACS. Jeśli HACS odpowie
   "Repository not found", dodaj repozytorium ręcznie: **HACS** → menu (⋮) →
   **Własne repozytoria**, wklej `https://github.com/RikoDEV/aster-meteo-ha-integration` i wybierz
   kategorię **Integracja**.
2. Po pobraniu zrestartuj Home Assistant. Aby zainstalować ręcznie,
   skopiuj `custom_components/aster_meteo` do `config/custom_components/` i zrestartuj.
3. Naciśnij przycisk poniżej albo przejdź do **Ustawienia** → **Urządzenia i usługi** →
   **Dodaj integrację** → **A-Ster.pl Meteo** i podaj [numer stacji](#jak-znaleźć-numer-stacji) (na przykład `428`), opcjonalną nazwę oraz
   interwały.
4. Aby dodać kolejne stacje, otwórz integrację i naciśnij **Dodaj stację meteo**. Ołówek obok stacji
   pozwala zmienić jej nazwę lub interwały.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=aster_meteo)

| Ustawienie | Domyślnie | Znaczenie |
| --- | --- | --- |
| Identyfikator stacji | | Numer stacji w sieci A-Ster |
| Nazwa | `A-Ster <ID>` | Nazwa urządzenia, z której powstają też identyfikatory encji |
| Częstotliwość odświeżania | 10 min | Jak często pobierane są dane; stacje raportują co 10 minut |
| Oznacz jako niedostępną po | 6 h | Wiek ostatniego pomiaru, po którym encje stają się niedostępne |

Wymagany jest Home Assistant **2025.3** lub nowszy (podwpisy konfiguracji).

## Jak znaleźć numer stacji

Każda stacja ma własną stronę w portalu A-Ster, adresowaną nazwą miejscowości, na przykład
`http://meteor.iung.pulawy.pl/view2.php?u=R%C4%99czno` (Ręczno). Numer stacji to liczba, z której
strona pobiera dane:

1. Otwórz stronę swojej stacji w przeglądarce.
2. Naciśnij **F12** → **Network** i odśwież stronę (albo użyj *Pokaż źródło strony*, **Ctrl+U**, i
   wyszukaj `data2.php`).
3. Znajdź zapytanie `data2.php?s=422`. Liczba po `s=` (tutaj **422**) to numer stacji, który
   wpisujesz w Home Assistant.

Numer możesz sprawdzić bezpośrednio, otwierając `http://meteor.iung.pulawy.pl/data2.php?s=<ID>`.
Stacja z danymi zwraca blok odczytów zaczynający się od `{ data: "2026-…"`.

Nie znasz nazwy pobliskiej stacji? `scripts/find_stations.py` sprawdza zakres numerów i wypisuje te,
które aktualnie raportują dane. Zakres trzymaj niewielki, to publiczny serwer:

```sh
python scripts/find_stations.py 400 440    # wąski zakres
python scripts/find_stations.py --all      # także stacje z nieaktualnymi danymi
```

## Encje

Tworzone dla każdej stacji, gdy stacja raportuje daną wartość:

| Encja | Pole API | Jednostka |
| --- | --- | --- |
| Temperatura powietrza | `temperatureInt` | °C |
| Wilgotność | `humidityInt` | % |
| Ciśnienie | `pressInt` | hPa |
| Prędkość wiatru | `windSpeed` | m/s |
| Kierunek wiatru | `windDir` | ° |
| Opady dziś | `rainT` | mm |
| Opady wczoraj | `rainY` | mm |
| Rodzaj opadu | `Op_Typ` | brak / deszcz / grad / inny |
| Temperatura przy gruncie | `t5Int` | °C |
| Temperatura gleby 10 cm | `tg10Int` | °C |
| Zwilżenie liści | `leafInt` | |
| Czas nasłonecznienia | `irr_durInt` | h |
| PM2.5 i PM10 | `pm2Int`, `pm10Int` | µg/m³ |
| Wilgotność gleby 10, 20, 30, 40, 60 i 100 cm | `soil10` … `soil100` | % |
| Ostatni pomiar (diagnostyka) | `data` | znacznik czasu |
| Pogoda | wyliczana | |

*Warunki* pogodowe są **szacowane**: deszcz lub grad z czujnika opadów, mgła z wysokiej wilgotności
i bezwietrznej pogody, słonecznie z odczytu nasłonecznienia, w pozostałych przypadkach pochmurno lub
bezchmurnie na podstawie wilgotności i położenia słońca. Stacje mierzą, a nie prognozują, więc
prognozy nie ma.

Identyfikatory encji wynikają z nazwy urządzenia i języka Home Assistant: stacja o nazwie
`Maków Weather` daje `sensor.makow_weather_air_temperature` po angielsku albo
`sensor.makow_weather_temperatura_powietrza` po polsku.

## Migracja ze starej platformy `makow_weather`

1. Zainstaluj tę integrację i dodaj stację `428` o nazwie **Maków Weather**.
2. Usuń stary blok `sensor: - platform: makow_weather` oraz folder `custom_components/makow_weather`,
   a następnie zrestartuj.
3. Zaktualizuj pulpity i automatyzacje używające `sensor.makow_weather_*` do nowych identyfikatorów
   encji; zobacz **Ustawienia** → **Encje**.

## Jak to działa

Serwer odpowiada na `GET /data2.php?s=<id>` obiektem JavaScript (nie JSON): skalarne bieżące odczyty
oraz kilka zagnieżdżonych serii wykresów. Parser wycina zagnieżdżone serie i czyta wartości
najwyższego poziomu, traktując puste ciągi jako brak odczytu. Znaczniki czasu są w polskim czasie
lokalnym.

## Struktura repozytorium

| Część | Technologia | Lokalizacja |
| --- | --- | --- |
| Integracja | Python, podwpisy konfiguracji Home Assistant | [`custom_components/aster_meteo/`](custom_components/aster_meteo) |
| Parser danych | Tylko biblioteka standardowa | [`parser.py`](custom_components/aster_meteo/parser.py) |
| Logo i ikona | Skrypt Pillow | [`brand/`](custom_components/aster_meteo/brand), [`scripts/make_brand.py`](scripts/make_brand.py) |
| Wyszukiwarka stacji | Tylko biblioteka standardowa | [`scripts/find_stations.py`](scripts/find_stations.py) |
| Testy | `unittest` na prawdziwych odpowiedziach | [`tests/`](tests) |
| CI | hassfest, walidacja HACS, testy | [`.github/workflows/`](.github/workflows) |

Home Assistant 2026.3 i nowszy pokazuje obrazy z folderu `brand` w interfejsie; starsze wersje
pokazują domyślną ikonę. Parser nie zależy od Home Assistant, więc testy działają bez niego:

```sh
pip install tzdata
python -m unittest discover -s tests -v
```

## Współtworzenie

Zgłoszenia błędów i pull requesty są mile widziane. Prosimy o rozsądne odpytywanie serwera:
domyślnie jedno zapytanie na stację co 10 minut.

## Zastrzeżenie

To nieoficjalny projekt społecznościowy. Nie jest powiązany z IUNG-PIB ani siecią A-Ster, nie jest
przez nie wspierany ani sponsorowany, a nazwa "A-Ster" służy wyłącznie do wskazania źródła danych.
Dane pomiarowe należą do ich właścicieli. Logo w `brand/` to autorska grafika, a nie logo A-Ster.

## Licencja

Kod tej integracji jest udostępniany na [licencji MIT](LICENSE). Licencja obejmuje wyłącznie ten
kod, a nie pobierane dane.
