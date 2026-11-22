<div align="center">

<img src="custom_components/aster_meteo/brand/logo@2x.png" alt="A-Ster.pl Meteo" width="360" />

# A-Ster.pl Meteo Integration

**An unofficial integration: live data from the A-Ster agro-meteo network, in Home Assistant, for as many stations as you like.**

Temperature, humidity, wind, rain, soil moisture and more from the public ASTERGate feed of IUNG-PIB
Puławy. Configured from the UI, installed with HACS, one device per station.

[![Validate](https://github.com/RikoDEV/aster-meteo-ha-integration/actions/workflows/validate.yaml/badge.svg)](https://github.com/RikoDEV/aster-meteo-ha-integration/actions/workflows/validate.yaml)
[![HACS: Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant: 2025.3+](https://img.shields.io/badge/Home%20Assistant-2025.3%2B-blue.svg)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=RikoDEV&repository=aster-meteo-ha-integration&category=integration)

[Quick start](#quick-start) · [Features](#features) · [Entities](#entities) · [Finding your station ID](#finding-your-station-id) · [Polski](README_pl.md)

</div>

---

## Features

**Stations**
- Add any number of stations from the UI. Each station is a *subentry* of the integration, so
  **Add meteo station** is a button on the integration page
- One device per station, named by you (for example `Maków Weather`)
- Per-station update interval and a "stale after" time: a station that stops reporting turns
  unavailable instead of showing old numbers forever

**Readings**
- Air and ground temperature, humidity, pressure, wind speed and direction
- Rain today and yesterday, precipitation type, sunshine duration, leaf wetness
- Soil temperature and soil moisture at 10, 20, 30, 40, 60 and 100 cm, PM2.5 and PM10
- Only the sensors a station really has are created. Many stations have no barometer or soil
  probes; those entities appear on their own if the station starts reporting them

**Weather and diagnostics**
- A `weather` entity per station with current conditions, wind and dew point
- A *Last measurement* diagnostic sensor that stays available while the station is silent
- English and Polish translations

## Quick start

1. Click the button at the top of this page, then **Download** in HACS. If HACS answers
   "Repository not found", add the repository once by hand: **HACS** → menu (⋮) →
   **Custom repositories**, paste `https://github.com/RikoDEV/aster-meteo-ha-integration` and choose
   the category **Integration**.
2. Restart Home Assistant after the download. To install by hand instead,
   copy `custom_components/aster_meteo` to `config/custom_components/` and restart.
3. Press the button below, or go to **Settings** → **Devices & services** → **Add integration** →
   **A-Ster.pl Meteo**, and enter the [station ID](#finding-your-station-id) (for example `428`), an optional name and the
   intervals.
4. To add more stations, open the integration and press **Add meteo station**. The pencil beside a
   station changes its ID, name or intervals. To remove a station, use **⋮** → **Delete** beside it,
   or **Delete** on its device page. A device can also be renamed and moved to an area there.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=aster_meteo)

| Setting | Default | Meaning |
| --- | --- | --- |
| Station ID | | Number of the station in the A-Ster network |
| Name | `A-Ster <ID>` | Device name, which also forms the entity IDs |
| Update interval | 10 min | How often the station is polled; stations report every 10 minutes |
| Mark as unavailable after | 6 h | Age of the last measurement after which entities become unavailable |

Home Assistant **2025.3** or newer is required, for config subentries.

## Finding your station ID

Every station has its own page on the A-Ster portal, addressed by the place name, for example
`http://meteor.iung.pulawy.pl/view2.php?u=R%C4%99czno` (Ręczno). The station ID is the number the
page requests its data from:

1. Open your station's page in the browser.
2. Press **F12** → **Network** and reload the page (or use *View page source*, **Ctrl+U**, and
   search for `data2.php`).
3. Find the request `data2.php?s=422`. The number after `s=` (here **422**) is the station ID to
   enter in Home Assistant.

You can check an ID directly by opening `http://meteor.iung.pulawy.pl/data2.php?s=<ID>`. A station
with data returns a block of readings starting with `{ data: "2026-…"`.

Don't know the name of a nearby station? `scripts/find_stations.py` probes a range of IDs and lists
the ones that currently report data. Keep the range small, it is a public server:

```sh
python scripts/find_stations.py 400 440    # a narrow range
python scripts/find_stations.py --all      # also stations with stale data
```

## Entities

Created per station when the station reports the value:

| Entity | API field | Unit |
| --- | --- | --- |
| Air temperature | `temperatureInt` | °C |
| Humidity | `humidityInt` | % |
| Pressure | `pressInt` | hPa |
| Wind speed | `windSpeed` | m/s |
| Wind direction | `windDir` | ° |
| Rain today | `rainT` | mm |
| Rain yesterday | `rainY` | mm |
| Precipitation type | `Op_Typ` | none / rain / hail / other |
| Ground temperature | `t5Int` | °C |
| Soil temperature 10 cm | `tg10Int` | °C |
| Leaf wetness | `leafInt` | |
| Sunshine duration | `irr_durInt` | h |
| PM2.5 and PM10 | `pm2Int`, `pm10Int` | µg/m³ |
| Soil moisture 10, 20, 30, 40, 60 and 100 cm | `soil10` … `soil100` | % |
| Last measurement (diagnostic) | `data` | timestamp |
| Weather | derived | |

The weather *condition* is an **estimate**: rain or hail from the precipitation sensor, fog from
high humidity and calm wind, sunny from the sunshine reading, otherwise cloudy or clear from the
humidity and the position of the sun. The stations measure, they do not forecast, so there is no
forecast.

Entity IDs follow the device name and your Home Assistant language: a station called
`Maków Weather` becomes `sensor.makow_weather_air_temperature` in English or
`sensor.makow_weather_temperatura_powietrza` in Polish.

## How it works

The server answers `GET /data2.php?s=<id>` with a JavaScript object literal (not JSON): scalar
current readings plus a few nested chart series. The parser blanks the nested series and reads the
top-level values, treating empty strings as "no reading". Timestamps are Polish local time.

## Repository layout

| Part | Technology | Location |
| --- | --- | --- |
| Integration | Python, Home Assistant config subentries | [`custom_components/aster_meteo/`](custom_components/aster_meteo) |
| Payload parser | Standard library only | [`parser.py`](custom_components/aster_meteo/parser.py) |
| Logo and icon | Pillow script | [`brand/`](custom_components/aster_meteo/brand), [`scripts/make_brand.py`](scripts/make_brand.py) |
| Station finder | Standard library only | [`scripts/find_stations.py`](scripts/find_stations.py) |
| Tests | `unittest` with real responses | [`tests/`](tests) |
| CI | hassfest, HACS validation, tests | [`.github/workflows/`](.github/workflows) |

Home Assistant 2026.3 and newer shows the images in the `brand` folder in the UI; older versions
show the default icon. The parser has no Home Assistant dependency, so the tests run without it:

```sh
pip install tzdata
python -m unittest discover -s tests -v
```

## Contributing

Bug reports and pull requests are welcome. Please keep polling polite: the default is one request
per station every 10 minutes.

## Disclaimer

This is an unofficial, community project. It is not affiliated with, endorsed by or sponsored by
IUNG-PIB or the A-Ster network, and "A-Ster" is used only to say which data source it reads. The
measurement data belongs to its owners. The logo in `brand/` is original artwork, not the A-Ster
logo.

## License

The code of this integration is licensed under the [MIT License](LICENSE). That license covers
only this code, not the data it retrieves.
