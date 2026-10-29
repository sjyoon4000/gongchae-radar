#!/usr/bin/env python3
"""Cartok 시세 수집. 파싱 실패 시 기존 데이터 보존하고 오류로 종료."""
import datetime as dt, json, os, pathlib, re, sys
import requests
from bs4 import BeautifulSoup

URL='http://www.cartok.com/getSubMenuLoad.do?sub_menu_id=gongchae&sub_menu_val=1'
ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'data.json'

def parse(html):
    soup=BeautifulSoup(html,'html.parser')
    for tag in soup(['script','style','noscript']):tag.decompose()
    rows=[]
    # 테이블 행에 날짜 및 두 수치가 들어가는 경우 우선 사용
    for tr in soup.select('tr'):
        cells=[x.get_text(' ',strip=True) for x in tr.select('th,td')]
        text=' '.join(cells)
        m=re.search(r'(20\d{2}[-./]\d{1,2}[-./]\d{1,2})',text)
        nums=re.findall(r'(?<![\d.])(\d{1,2}\.\d{1,3})(?![\d.])',text[m.end():] if m else '')
        if m and len(nums)>=2:rows.append((m.group(1),float(nums[0]),float(nums[1])))
    if not rows:
        # 모바일 뷰처럼 날짜/수치가 개별 li 또는 div에 분리된 경우
        text=soup.get_text(' ',strip=True)
        pattern=r'(20\d{2}[-./]\d{1,2}[-./]\d{1,2})\s+(\d{1,2}\.\d{1,3})\s+(\d{1,2}\.\d{1,3})'
        rows=[(a,float(b),float(c)) for a,b,c in re.findall(pattern,text)]
    out={}
    for date,metro,regional in rows:
        try:date=dt.date.fromisoformat(date.replace('.','-').replace('/','-')).isoformat()
        except ValueError:continue
        if not (0<metro<40 and 0<regional<40):continue
        out[date]={'date':date,'metro':metro,'regional':regional}
    return sorted(out.values(),key=lambda x:x['date'],reverse=True)

def main():
    r=requests.get(URL,timeout=25,headers={'User-Agent':'Mozilla/5.0 (compatible; BondQuoteMonitor/1.0)','Referer':'http://www.cartok.com/'})
    r.raise_for_status();r.encoding=r.apparent_encoding
    rows=parse(r.text)
    if not rows:raise RuntimeError('날짜와 시세 2개를 추출하지 못함. HTML 구조 확인 필요')
    if len(rows)<2:raise RuntimeError('최소 2거래일 검증 불가')
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    latest=dt.date.fromisoformat(rows[0]['date'])
    if latest>today or (today-latest).days>7:raise RuntimeError(f'최신 자료 날짜가 비정상: {latest}')
    data=json.loads(DATA.read_text(encoding='utf-8'))
    prior={x['date']:x for x in data.get('history',[])}
    prior.update({x['date']:x for x in rows})
    history=sorted(prior.values(),key=lambda x:x['date'],reverse=True)[:30]
    if data['market']['date']>rows[0]['date']:
        print('기존 데이터가 더 최신이므로 유지');return
    data['history']=history
    data['market']={**rows[0],'source':'Cartok 공채정보 (자동 수집 · 지역별 실제 할인율 차이 유의)'}
    data['version']=rows[0]['date']+'-cartok'
    data['market']['verifiedAutomated']=True
    data['market']['collectedAt']=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds')
    DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('수집 완료:',rows[0])
if __name__=='__main__':
    try:main()
    except Exception as e:print('수집 실패:',e,file=sys.stderr);sys.exit(1)
