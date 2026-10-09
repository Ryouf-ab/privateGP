# Diyara data (Sprint 1, Person 4)

This folder holds all the project datasets and the tables built from them.

| Path | What it is |
|---|---|
| `diyara_data.sql` | **Import this.** Creates and fills `neighborhoods` (193 districts) and `properties` (1,190 listings) in `diyara_db` |
| `clean/` | The same two tables as CSV (`districts.csv`, `properties.csv`) |
| `raw/` | The original datasets as collected |
| `scripts/` | Python scripts that rebuild `clean/` from `raw/` |

## How to load the data

1. Make sure `diyara_db` exists (see the main README).
2. Open phpMyAdmin, select `diyara_db`, go to **Import**, and choose `data/diyara_data.sql`.
3. Check: `SELECT COUNT(*) FROM neighborhoods;` should return 193.

## Main columns in `neighborhoods`

`neighborhood_id`, `name_ar`, `name_en`, `region`, `latitude`, `longitude`, `schools_count` (+ `schools_primary/middle/secondary`), `hospitals_count`, `parks_count`, `gyms_count`, `pharmacies_count`, `supermarkets_count`, `shopping_centers_count`, `banks_count`, `fuel_stations_count`, `metro_stations_count`, `median_price_m2`, `deals_count`, `median_property_price`, `median_apartment_price`, `median_villa_price`, `median_floor_price`, `listings_count`.

Person 3's filtering reads from this table, and `recommendations.php` shows its rows.

## Rebuilding the tables

```
python data/scripts/build_districts.py data/raw data/clean
python data/scripts/to_sql.py data/clean data/diyara_data.sql
```
(`to_sql.py` writes data only; the table definitions at the top of `diyara_data.sql` were added by hand.)

## Sources used

| File | Source | Rows | Used for |
|---|---|---|---|
| Aqar_Riyadh_cleaned.xlsx | Kaggle (Aqar listings) | 1,190 | properties table, median prices by type |
| MOJ_Riyadh_transactions_with_region.xlsx | Ministry of Justice | 1,675 deals (1,499 residential) | median price per m² |
| commercial_services_cleaned.xlsx | RCRC Open Data | 1,900 | supermarkets, shopping centers, banks, fuel stations |
| riyadh_schools_final.csv | Ministry of Education | 4,282 school-stage rows | schools per district and stage |
| riyadh_hospitals_final.csv | Hospitals list | 89 | hospitals per district |
| riyadh_parks_final.csv | Parks list | 86 | parks per district |
| RiyadhGyms.xlsx | Google Places | 769 | gyms per district |
| RiyadhPharmacy.xlsx | Google Places | 2,285 | pharmacies per district |
| Riyadh_Metro_Stations_Final.xlsx | Riyadh Metro | 94 stations | metro stations per district |
| riyadh_distances_*.csv | Google Maps | 1,045 pairs | not loaded yet (commute, Sprint 2) |

## How the data was merged

1. **One district key.** Arabic names were normalized (أ/إ/آ → ا, ة → ه, ى → ي, Persian ی → ي, "حي " prefix removed) plus a short alias list (e.g. العريجاء الغربية → العريجاء الغربي). Junk values (الرياض, أخرى, 3419) were dropped. Result: 193 districts.
2. **Arabic ↔ English names.** RCRC files use English names (AL-MALQA). Each Arabic-labelled point (pharmacy, gym, hospital, park, metro) voted for the English district of its nearest RCRC point within 1.5 km; matches were then checked against a transliteration similarity score, and 7 were fixed by hand. 159 of 163 RCRC districts were matched.
3. **Coordinates and region.** District centre = median of its points; region = most common region label across sources.
4. **Schools** have coordinates but no district, so each was assigned to the nearest district centre within 3 km. 1,348 rows were dropped because geocoding put many different schools on the same fallback point (1,165 rows at 24.713552, 46.675296).
5. **Prices.** 26 Aqar land listings were priced per m² and were converted to totals (price × area). MOJ price per m² outside 200–30,000 SAR was treated as an outlier.

## Known gaps

- 21 districts have no coordinates and 34 have no English name (they appear only in Aqar or MOJ).
- 87 districts have no Aqar listings, so `median_property_price` is NULL for them.
- 8 Aqar listings have a district that could not be matched (stored with `neighborhood_id` NULL).
