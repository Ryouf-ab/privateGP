import sys, re, glob, numpy as np, pandas as pd
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
d = sys.argv[1]; out = sys.argv[2]
def norm(s):
    if pd.isna(s): return None
    s = str(s).strip(); s = re.sub(r'^حي\s+', '', s); s = re.sub(r'\s+', ' ', s)
    s = s.replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ة','ه').replace('ى','ي').replace('ی','ي').replace('ک','ك')
    return ALIAS.get(s, s)
ALIAS = {'العريجاء الغربيه':'العريجاء الغربي', 'العريجاء الوسطي':'العريجاء الاوسط', 'غبيراء':'غبيرا', 'غبيره':'غبيرا',
         'المعيزله':'المعيزيله', 'المعيزليه':'المعيزيله', 'المنصوره':'المنصوره (خنشليله)', 'خنشليله':'المنصوره (خنشليله)',
         'سدره':'السدره', 'الصفاء':'الصفا', 'مخطط الخير':'الخير'}
JUNK = {'3419', 'اخري', 'الرياض', 'شرق الرياض'}
def clean_display(s): return re.sub(r'^حي\s+', '', str(s).strip())

aqar = pd.read_excel(f'{d}/Aqar_Riyadh_cleaned.xlsx')
moj = pd.read_excel(f'{d}/MOJ_Riyadh_transactions_with_region.xlsx')
hosp = pd.read_csv(f'{d}/riyadh_hospitals_final.csv')
parks = pd.read_csv(f'{d}/riyadh_parks_final.csv')
gyms = pd.read_excel(f'{d}/RiyadhGyms.xlsx')
pharm = pd.read_excel(f'{d}/RiyadhPharmacy.xlsx')
metro = pd.read_excel(f'{d}/Riyadh_Metro_Stations_Final.xlsx')
rcrc = pd.read_excel(f'{d}/commercial_services_cleaned.xlsx')
centers = pd.read_csv(f'{d}/riyadh_district_centers.csv')

# Arabic point data -> centroids and region
pts = pd.concat([
    pharm.rename(columns={'district':'d','latitude':'lat','longitude':'lon','region':'reg'})[['d','lat','lon','reg']],
    gyms.rename(columns={'district':'d','latitude':'lat','longitude':'lon','region':'reg'})[['d','lat','lon','reg']],
    hosp.rename(columns={'district_ar':'d','latitude':'lat','longitude':'lon','المنطقة':'reg'})[['d','lat','lon','reg']],
    parks.rename(columns={'district_ar':'d','latitude':'lat','longitude':'lon','المنطقة':'reg'})[['d','lat','lon','reg']],
    metro.rename(columns={'Neighborhood':'d','Latitude':'lat','Longitude':'lon','Region':'reg'})[['d','lat','lon','reg']],
])
pts['key'] = pts['d'].map(norm)

# display names: most common original spelling per key
names = pd.concat([aqar['District'], moj['الحي'], pts['d']]).dropna().map(clean_display)
disp = names.groupby(names.map(norm)).agg(lambda s: s.value_counts().index[0])

cent = pts.groupby('key').agg(lat=('lat','median'), lon=('lon','median'), n_pts=('lat','size'))
regmap = pd.concat([
    pharm.assign(key=pharm['district'].map(norm))[['key','region']].rename(columns={'region':'r'}),
    gyms.assign(key=gyms['district'].map(norm))[['key','region']].rename(columns={'region':'r'}),
    aqar.assign(key=aqar['District'].map(norm))[['key','المنطقة']].rename(columns={'المنطقة':'r'}),
    moj.assign(key=moj['الحي'].map(norm))[['key','المنطقة_الجغرافية']].rename(columns={'المنطقة_الجغرافية':'r'}),
]).dropna()
region = regmap.groupby('key')['r'].agg(lambda s: s.value_counts().index[0])

def hav(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return 6371*2*np.arcsin(np.sqrt(a))

# Arabic -> English via vote: each Arabic-labelled point votes for the English district of its nearest RCRC point (<=1.5 km)
r = rcrc.dropna(subset=['Latitude','Longitude'])
rl, rn, rd = r['Latitude'].values, r['Longitude'].values, r['District name'].values
votes = []
for k, la, lo in pts[['key','lat','lon']].itertuples(index=False):
    dist = hav(la, lo, rl, rn); i = dist.argmin()
    if dist[i] <= 1.5: votes.append((k, rd[i]))
v = pd.DataFrame(votes, columns=['key','en'])
vc = v.groupby(['key','en']).size().rename('n').reset_index().sort_values('n', ascending=False)
tot = v.groupby('key').size()
best = vc.drop_duplicates('key').set_index('key')
best['share'] = best['n'] / tot[best.index]
best = best[(best['share'] >= 0.5) & (best['n'] >= 2)]
from translit import sim, ar_skel, en_skel
best['sim'] = [sim(k, e) for k, e in zip(best.index, best['en'])]
# translated names (King Saud University, New Industrial City) have low letter similarity but strong votes
best = best[(best['sim'] >= 0.45) | ((best['share'] >= 0.8) & (best['n'] >= 5))]
# an English district may only map to one Arabic district: keep strongest
best = best.sort_values('n', ascending=False)
best = best[~best['en'].duplicated()]
en_map = best['en']
# second pass: unmapped English names matched to unmapped Arabic names by spelling
all_ar = set(names.map(norm)) - set(en_map.index)
for e in sorted(set(rcrc['District name'].dropna()) - set(en_map.values)):
    cands = sorted(((sim(a, e), a) for a in all_ar), reverse=True)
    if cands and cands[0][0] >= 0.8 and (len(cands) == 1 or cands[1][0] < cands[0][0]):
        en_map[cands[0][1]] = e; all_ar.discard(cands[0][1])
# manual fixes checked by hand: wrong vote (الدوبيه) and names the automatic pass could not pair
MANUAL = {'الديره': 'AD-DIRAH', 'الصفا': 'AS-SAFA', 'المرقب': 'AL-MARGAB', 'الزهراء': 'AZ-ZAHRAA',
          'جامعه الملك سعود': 'KING SAUD UNIVERSITY', 'مطار الملك خالد الدولي': 'KING KHALID INT.AIRPORT',
          'العريجاء الغربي': 'WEST AL-ORAIJA'}
en_map = en_map.drop(labels=['الدوبيه'], errors='ignore')
en_map = en_map[~en_map.isin(MANUAL.values())]
for a, e in MANUAL.items(): en_map[a] = e
print('rejected/unmapped english:', sorted(set(rcrc['District name'].dropna()) - set(en_map.values)))

keys = sorted(set(disp.index) - JUNK)
dist_df = pd.DataFrame({'key': keys})
dist_df['name_ar'] = dist_df['key'].map(disp)
dist_df['name_en'] = dist_df['key'].map(en_map)
dist_df = dist_df.join(cent, on='key')
# fill missing coords from English centre
cen = centers.set_index('District name')
miss = dist_df['lat'].isna() & dist_df['name_en'].notna()
dist_df.loc[miss, 'lat'] = dist_df.loc[miss, 'name_en'].map(cen['lat'])
dist_df.loc[miss, 'lon'] = dist_df.loc[miss, 'name_en'].map(cen['lon'])
dist_df['region'] = dist_df['key'].map(region)

# ---- indicators ----
def cnt(df, col):
    return df[col].map(norm).value_counts()
dist_df['hospitals'] = dist_df['key'].map(cnt(hosp,'district_ar')).fillna(0).astype(int)
dist_df['parks'] = dist_df['key'].map(cnt(parks,'district_ar')).fillna(0).astype(int)
dist_df['gyms'] = dist_df['key'].map(cnt(gyms,'district')).fillna(0).astype(int)
dist_df['pharmacies'] = dist_df['key'].map(cnt(pharm,'district')).fillna(0).astype(int)
# interchange stations appear once per line (94 rows, 83 stations); count each station once
dist_df['metro_stations'] = dist_df['key'].map(cnt(metro.drop_duplicates('Station_ID'),'Neighborhood')).fillna(0).astype(int)
en2key = {v:k for k,v in en_map.items()}
rc = rcrc.assign(key=rcrc['District name'].map(en2key))
cat = rc.pivot_table(index='key', columns='Category', values='Service name', aggfunc='size', fill_value=0)
dist_df['supermarkets'] = dist_df['key'].map(cat.get('Supermarket',0)+cat.get('Hypermarket',0)+cat.get('Grocery Store',0)).fillna(0).astype(int)
dist_df['shopping_centers'] = dist_df['key'].map(cat.get('Shopping Center',0)).fillna(0).astype(int)
dist_df['banks'] = dist_df['key'].map(cat.get('Bank',0)).fillna(0).astype(int)
dist_df['fuel_stations'] = dist_df['key'].map(cat.get('Fuel Station',0)).fillna(0).astype(int)

# schools: Ministry of Education list for 1448 AH (private, never uploaded). Each school's district comes from its
# address text; schools with no usable address fall back to the nearest district centre (within 3 km) of the school's
# coordinates in the older MOE file. Only the per-district counts (raw/schools_by_district.csv) are kept in the repo.
cc = dist_df.dropna(subset=['lat'])
ck, cla, clo = cc['key'].values, cc['lat'].values, cc['lon'].values
def nearest(la, lo):
    dd = hav(la, lo, cla, clo); i = dd.argmin(); return ck[i] if dd[i] <= 3 else None
priv = sys.argv[3] if len(sys.argv) > 3 else None
if priv:
    moe = pd.read_excel(f'{priv}/moe_schools_1448.xlsx', header=2).dropna(subset=['الرقم الوزاري'])
    key_set = set(dist_df['key'])
    cand = {k: k for k in key_set}; cand.update({a: k for a, k in ALIAS.items() if k in key_set})   # spelling variants too
    keys_by_len = sorted(cand, key=len, reverse=True)
    def addr_key(a):
        if pd.isna(a): return None
        t = str(a).replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ة','ه').replace('ى','ي')
        t = ' ' + re.sub(r'\s+', ' ', re.sub(r'[()\-،,_/]', ' ', t)) + ' '
        for k in keys_by_len:
            for v in {k, k[2:] if k.startswith('ال') and len(k) > 5 else k}:
                if re.search(r'(^|\s|حي)' + re.escape(v) + r'ه?(\s|$)', t): return cand[k]
        for w in t.split():
            w = re.sub(r'^حي', '', w); al = ALIAS.get(w) or ALIAS.get('ال' + w)
            if al in key_set: return al
        return None
    moe['key'] = moe['العنوان'].map(addr_key)
    old = pd.read_csv(f'{priv}/riyadh_schools_final.csv').dropna(subset=['lat','lon'])
    old = old[old.groupby(['lat','lon'])['الرقم الوزاري'].transform('nunique') <= 10]   # drop shared geocoding fallback points
    xy = old.drop_duplicates('الرقم الوزاري').set_index('الرقم الوزاري')[['lat','lon']]
    moe = moe.join(xy, on='الرقم الوزاري')
    fb = moe['key'].isna() & moe['lat'].notna()
    moe.loc[fb, 'key'] = [nearest(a, b) for a, b in zip(moe.loc[fb, 'lat'], moe.loc[fb, 'lon'])]
    print('MOE schools:', len(moe), 'by address:', (moe['key'].notna() & ~fb).sum(), 'by coords:', moe.loc[fb, 'key'].notna().sum(), 'unassigned:', moe['key'].isna().sum())
    sbd = pd.DataFrame({'schools': moe.groupby('key').size()})
    for stage, col in [('الإبتدائية','schools_primary'),('المتوسطة','schools_middle'),('الثانوية','schools_secondary')]:
        sbd[col] = moe[moe['المرحلة'].str.contains(stage, na=False)].groupby('key').size()
    sbd = sbd.fillna(0).astype(int).rename_axis('district_key').reset_index()
    sbd.to_csv(f'{d}/schools_by_district.csv', index=False, encoding='utf-8-sig')
sbd = pd.read_csv(f'{d}/schools_by_district.csv').set_index('district_key')
for col in ['schools','schools_primary','schools_middle','schools_secondary']:
    dist_df[col] = dist_df['key'].map(sbd[col]).fillna(0).astype(int)

# clinics (Kaggle "Riyadh Hospitals and Clinics", from Google Maps): non-hospital medical points, nearest centroid within 3 km
hc = pd.read_excel(f'{d}/riyadh_hospitals_clinics.xlsx')
hc = hc[~hc['Type_of_Utility'].isin({'beauty_salon','hair_care','spa','parking','veterinary_care','pharmacy'})]
hc = hc[~hc['Name'].str.contains(r'بوابة|مواقف|صيدلية|gate|parking|pharmacy|صالون|salon|بيطري|vet', case=False, regex=True)]
hc = hc[hc['Latitude'].between(24.3,25.2) & hc['Longitude'].between(46.3,47.2)]
hc = hc.drop_duplicates(['Name']).drop_duplicates(['Latitude','Longitude'])
is_hosp = hc['Name'].str.contains(r'مستشفى|مستشفي|hospital|المدينة الطبية|مدينة الملك.*الطبية|medical city', case=False, regex=True) \
          & ~hc['Name'].str.contains(r'عياد|clinic|مستوصف|polyclinic|مجمع|dental|اسنان|أسنان', case=False, regex=True)
cl = hc[~is_hosp].copy()
cl['key'] = [nearest(a,b) for a,b in zip(cl['Latitude'], cl['Longitude'])]
print('clinics kept:', len(cl), 'assigned:', cl['key'].notna().sum())
dist_df['clinics'] = dist_df['key'].map(cl.groupby('key').size()).fillna(0).astype(int)

# prices
mr = moj[moj['تصنيف العقار']=='سكني'].assign(key=moj['الحي'].map(norm))
mr = mr[(mr['سعر_المتر']>200) & (mr['سعر_المتر']<30000)]
dist_df['moj_median_price_m2'] = dist_df['key'].map(mr.groupby('key')['سعر_المتر'].median()).round(0)
dist_df['moj_deals'] = dist_df['key'].map(mr.groupby('key').size()).fillna(0).astype(int)
aqar = aqar.copy()
per_m2 = aqar['Price'] < 20000   # land listings priced per m2
aqar['Price'] = np.where(per_m2, aqar['Price'] * aqar['Area'], aqar['Price'])
print('aqar prices converted from per-m2:', per_m2.sum())
aq = aqar.assign(key=aqar['District'].map(norm), ptype=aqar['Property Type'].map(norm))
dist_df['aqar_listings'] = dist_df['key'].map(aq.groupby('key').size()).fillna(0).astype(int)
dist_df['aqar_median_price'] = dist_df['key'].map(aq.groupby('key')['Price'].median()).round(0)
for t, col in [('شقه','aqar_median_price_apartment'),('فيلا','aqar_median_price_villa'),('دور','aqar_median_price_floor')]:
    dist_df[col] = dist_df['key'].map(aq[aq['ptype']==t].groupby('key')['Price'].median()).round(0)

dist_df.insert(0, 'district_id', range(1, len(dist_df)+1))
dist_df.drop(columns=['n_pts']).to_csv(f'{out}/districts.csv', index=False, encoding='utf-8-sig')

# properties table
keymap = dict(zip(dist_df['key'], dist_df['district_id']))
props = pd.DataFrame({
  'property_id': aqar['Property_ID'], 'district_id': aqar['District'].map(norm).map(keymap),
  'property_type': aqar['Property Type'].map(lambda s: norm(s) if pd.notna(s) else s).replace({'شقه':'شقة','ارض سكنيه':'أرض سكنية','عماره سكنيه':'عمارة سكنية','ارض':'أرض','عماره':'عمارة','استراحه':'استراحة'}),
  'bedrooms': aqar['Bedrooms'], 'bathrooms': aqar['Bathrooms'], 'area_m2': aqar['Area'], 'price': aqar['Price'],
}).drop_duplicates('property_id')
props.to_csv(f'{out}/properties.csv', index=False, encoding='utf-8-sig')

# report
print('districts', len(dist_df), 'with coords', dist_df['lat'].notna().sum(), 'with english', dist_df['name_en'].notna().sum(), 'with region', dist_df['region'].notna().sum())
print('english districts in RCRC', rcrc['District name'].nunique(), 'mapped', len(en_map))
print('rcrc rows mapped', rc['key'].notna().mean().round(3))
print('props', len(props), 'no district', props['district_id'].isna().sum())
print(dist_df.sort_values('pharmacies', ascending=False).head(8)[['name_ar','name_en','region','schools','pharmacies','supermarkets','metro_stations','moj_median_price_m2','aqar_median_price']].to_string())
print(best.sort_values('sim').head(12)[['en','n','share','sim']].to_string())
