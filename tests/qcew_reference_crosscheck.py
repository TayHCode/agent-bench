"""Offline independent SQL cross-check of both complete BLS answer tables.

Run with uv run --no-project --with duckdb python tests/qcew_reference_crosscheck.py
--archives-dir <cache> --prepared-task <prepared-task> --scratch-dir <scratch>.
Archives must already exist; this script makes no network or model calls.
"""
import csv,io,zipfile,json
from pathlib import Path
import duckdb
import argparse
parser=argparse.ArgumentParser(description='Independently cross-check the prepared BLS known answers using DuckDB SQL.')
parser.add_argument('--archives-dir',required=True)
parser.add_argument('--prepared-task',required=True)
parser.add_argument('--scratch-dir',required=True)
args=parser.parse_args()
root=Path(args.archives_dir)
scratch=Path(args.scratch_dir)
scratch.mkdir(parents=True,exist_ok=True)
con=duckdb.connect()
con.execute("SET memory_limit='2GB'")
con.execute("SET threads=2")
con.execute('SET temp_directory=?',[str(scratch/'duckdb-temp')])
con.execute('CREATE TABLE cells(year INTEGER, area VARCHAR, industry VARCHAR, emp DOUBLE, wages DOUBLE)')
for year in [2025,2026]:
 p=scratch/f'qcew-sql-{year}.csv'
 if not p.exists():
  with zipfile.ZipFile(root/f'qcew-{year}.zip') as z, z.open(z.namelist()[0]) as f, p.open('wb') as out:
   import shutil
   shutil.copyfileobj(f,out)
 print('SQL reading',year,flush=True)
 con.execute('''INSERT INTO cells SELECT CAST(year AS INTEGER), area_fips,industry_code,
 CASE WHEN coalesce(trim(disclosure_code),'')='' THEN (CAST(month1_emplvl AS DOUBLE)+CAST(month2_emplvl AS DOUBLE)+CAST(month3_emplvl AS DOUBLE))/3 ELSE NULL END,
 CASE WHEN coalesce(trim(disclosure_code),'')='' THEN CAST(total_qtrly_wages AS DOUBLE) ELSE NULL END
 FROM read_csv(?,all_varchar=true) WHERE year=? AND qtr='1' AND own_code='5' AND size_code='0'
 AND ((regexp_full_match(area_fips,'[0-9]{5}') AND substr(area_fips,1,2) IN ('01','02','04','05','06','08','09','10','11','12','13','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30','31','32','33','34','35','36','37','38','39','40','41','42','44','45','46','47','48','49','50','51','53','54','55','56') AND substr(area_fips,3) NOT IN ('000','999') AND agglvl_code IN ('71','74')) OR (area_fips='US000' AND agglvl_code IN ('11','14')))''',[str(p),str(year)])
con.execute('''CREATE TABLE sector_values AS
WITH keys AS (SELECT DISTINCT area,industry FROM cells WHERE area!='US000' AND industry!='10'
 AND area IN (SELECT area FROM cells WHERE industry='10')),
 joined AS (SELECT k.area,k.industry,
 CASE WHEN a.area IS NULL OR b.area IS NULL THEN 'missing'
 WHEN a.emp IS NULL OR b.emp IS NULL THEN 'suppressed'
 WHEN n0.emp IS NULL OR n1.emp IS NULL OR n0.emp=0 THEN 'no_national' ELSE 'ok' END AS status,
 a.emp AS e0,b.emp AS e1,b.emp-a.emp AS delta,
 a.emp*(u1.emp/u0.emp-1) AS ng,
 a.emp*(n1.emp/n0.emp-u1.emp/u0.emp) AS mix,
 b.emp-a.emp*n1.emp/n0.emp AS rs,
 (b.emp/nullif(t1.emp,0))/(n1.emp/u1.emp) AS lq,
 a.wages/(13*nullif(a.emp,0)) AS w0,b.wages/(13*nullif(b.emp,0)) AS w1
 FROM keys k LEFT JOIN cells a ON a.year=2025 AND a.area=k.area AND a.industry=k.industry
 LEFT JOIN cells b ON b.year=2026 AND b.area=k.area AND b.industry=k.industry
 LEFT JOIN cells n0 ON n0.year=2025 AND n0.area='US000' AND n0.industry=k.industry
 LEFT JOIN cells n1 ON n1.year=2026 AND n1.area='US000' AND n1.industry=k.industry
 LEFT JOIN cells t1 ON t1.year=2026 AND t1.area=k.area AND t1.industry='10'
 CROSS JOIN (SELECT * FROM cells WHERE year=2025 AND area='US000' AND industry='10') u0
 CROSS JOIN (SELECT * FROM cells WHERE year=2026 AND area='US000' AND industry='10') u1)
 SELECT area,industry,status,e0,e1,delta,
 CASE WHEN status='ok' THEN ng END AS ng,CASE WHEN status='ok' THEN mix END AS mix,
 CASE WHEN status='ok' THEN rs END AS rs,CASE WHEN status='ok' THEN lq END AS lq,
 CASE WHEN status='ok' THEN w0 END AS w0,CASE WHEN status='ok' THEN w1 END AS w1,
 CASE WHEN status='ok' THEN (w1/nullif(w0,0)-1)*100 END AS wg FROM joined''')
sectors=con.execute('SELECT * FROM sector_values ORDER BY area,industry').fetchall()
counties=con.execute('''WITH agg AS (SELECT area,
 sum(CASE WHEN status='ok' THEN e0 ELSE 0 END) AS cov0,
 sum(CASE WHEN status='ok' THEN e1 ELSE 0 END) AS cov1,
 sum(CASE WHEN status='ok' THEN delta ELSE 0 END) AS dc,
 sum(coalesce(ng,0)) AS ng,sum(coalesce(mix,0)) AS mix,sum(coalesce(rs,0)) AS rs,
 sum(CASE WHEN status='ok' THEN 1 ELSE 0 END) AS ok,
 sum(CASE WHEN status!='ok' THEN 1 ELSE 0 END) AS unavailable FROM sector_values GROUP BY area)
 SELECT x.area,a.emp,b.emp,b.emp-a.emp,cov0,cov1,dc,ng,mix,rs,b.emp-a.emp-dc,ok,unavailable
 FROM agg x LEFT JOIN cells a ON a.area=x.area AND a.year=2025 AND a.industry='10'
 LEFT JOIN cells b ON b.area=x.area AND b.year=2026 AND b.industry='10' ORDER BY x.area''').fetchall()
for name,rows in [('sector_shift_share.csv',sectors),('county_summary.csv',counties)]:
 p=Path(args.prepared_task)/'gold'/name
 with p.open(newline='') as f:reader=csv.reader(f);next(reader);expected=list(reader)
 assert len(rows)==len(expected),(name,len(rows),len(expected))
 mismatches=[]
 for actual,want in zip(rows,expected):
  for i,(a,b) in enumerate(zip(actual,want)):
   if a is None:ok=b==''
   elif isinstance(a,str):ok=a==b
   else:ok=abs(float(a)-float(b))<0.00002
   if not ok:mismatches.append((actual[:2],i,a,b))
 assert not mismatches,(name,mismatches[:5])
 print(name,'independent SQL agrees on all',len(rows),'rows',flush=True)
(scratch/'qcew-independent-validation.json').write_text(json.dumps({'sector_rows':len(sectors),'county_rows':len(counties),'independent_sql_matches_all_cells':True},indent=2))
