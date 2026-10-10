"""Known answers from published QCEW cells, with exact rational arithmetic."""
import csv
from fractions import Fraction as F
import io
from pathlib import Path
import zipfile

SECTOR_COLUMNS = ['area_fips', 'industry_code', 'status', 'employment_2025', 'employment_2026', 'change', 'national_share', 'industry_mix', 'regional_shift', 'lq_2026', 'weekly_wage_2025', 'weekly_wage_2026', 'wage_growth_pct']
COUNTY_COLUMNS = ['area_fips', 'employment_2025', 'employment_2026', 'change', 'covered_employment_2025', 'covered_employment_2026', 'covered_change', 'national_share', 'industry_mix', 'regional_shift', 'unallocated_change', 'ok_sectors', 'unavailable_sectors']
STATES = {'01','02','04','05','06','08','09','10','11','12','13','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30','31','32','33','34','35','36','37','38','39','40','41','42','44','45','46','47','48','49','50','51','53','54','55','56'}


def county(fips):
    return len(fips) == 5 and fips.isdigit() and fips[:2] in STATES and fips[2:] not in {'000','999'}


def read_cells(path, year):
    cells = {}
    with zipfile.ZipFile(path) as archive:
        members = [n for n in archive.namelist() if n.endswith('.csv')]
        if len(members) != 1:
            raise ValueError('unexpected upstream archive layout')
        with archive.open(members[0]) as stream:
            for row in csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig', newline='')):
                if (row['year'], row['qtr'], row['own_code'], row['size_code']) != (str(year), '1', '5', '0'):
                    continue
                area, level = row['area_fips'], row['agglvl_code']
                if not ((county(area) and level in {'71','74'}) or (area == 'US000' and level in {'11','14'})):
                    continue
                key = area, row['industry_code']
                if key in cells:
                    raise ValueError('duplicate published cell')
                cells[key] = None if row['disclosure_code'].strip() else (F(sum(int(row[f'month{i}_emplvl']) for i in [1,2,3]), 3), int(row['total_qtrly_wages']))
    return cells


def published(cells, key):
    value = cells.get(key)
    return value[0] if value is not None else None


def ratio(a, b):
    return a / b if a is not None and b is not None and b != 0 else None


def format_value(value):
    if value is None:
        return ''
    if isinstance(value, (F, float)):
        return f'{float(value):.6f}'
    return str(value)


def write(path, columns, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows([[format_value(v) for v in row] for row in rows])


def answers(old, new):
    national_growth = new['US000','10'][0] / old['US000','10'][0] - 1
    areas = sorted({a for a, i in old.keys() | new.keys() if county(a) and i == '10'})
    sector_rows, county_rows = [], []
    by_area = {}
    for a,i in old.keys() | new.keys():
        if county(a) and i != '10':
            by_area.setdefault(a,set()).add(i)
    for area in areas:
        total0, total1 = published(old,(area,'10')), published(new,(area,'10'))
        sums = [F(0)] * 6
        ok = unavailable = 0
        industries = sorted(by_area.get(area,set()))
        for industry in industries:
            key = area, industry
            nkey = ('US000', industry)
            e0, e1 = published(old,key), published(new,key)
            if key not in old or key not in new:
                status = 'missing'
            elif old[key] is None or new[key] is None:
                status = 'suppressed'
            elif nkey not in old or nkey not in new or old[nkey] is None or new[nkey] is None or old[nkey][0] == 0:
                status = 'no_national'
            else:
                status = 'ok'
            change = e1-e0 if e0 is not None and e1 is not None else None
            ng = mix = regional = lq = w0 = w1 = wg = None
            if status == 'ok':
                sector_growth = new[nkey][0] / old[nkey][0] - 1
                ng = e0 * national_growth
                mix = e0 * (sector_growth - national_growth)
                regional = change - ng - mix
                lq = ratio(ratio(e1,total1), ratio(new[nkey][0],new['US000','10'][0]))
                w0 = ratio(old[key][1],13*e0)
                w1 = ratio(new[key][1],13*e1)
                wg = (w1/w0-1)*100 if w0 not in (None,0) and w1 is not None else None
                for j,v in enumerate([e0,e1,change,ng,mix,regional]):sums[j]+=v
                ok += 1
            else:
                unavailable += 1
            sector_rows.append([area,industry,status,e0,e1,change,ng,mix,regional,lq,w0,w1,wg])
        delta = total1-total0 if total1 is not None and total0 is not None else None
        county_rows.append([area,total0,total1,delta,*sums,delta-sums[2] if delta is not None else None,ok,unavailable])
    return sector_rows,county_rows


def build(data, destination):
    data, destination = Path(data), Path(destination)
    old = read_cells(data/'qcew-2025.zip',2025)
    new = read_cells(data/'qcew-2026.zip',2026)
    sectors,counties = answers(old,new)
    destination.mkdir(parents=True,exist_ok=True)
    write(destination/'sector_shift_share.csv',SECTOR_COLUMNS,sectors)
    write(destination/'county_summary.csv',COUNTY_COLUMNS,counties)
    print(f'known answer: {len(sectors)} county-sector rows, {len(counties)} counties',flush=True)
