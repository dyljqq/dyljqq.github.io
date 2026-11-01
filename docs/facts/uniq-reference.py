import re,sys,os,html,collections,json
root=sys.argv[1]
pages={}
for dp,dn,fn in os.walk(root):
    if any(x in dp for x in ('/.git','/node_modules','/tools/store','/assets')): continue
    if 'index.html' in fn:
        p=os.path.join(dp,'index.html'); u='/'+os.path.relpath(dp,root).replace('.','')+'/'
        u=u.replace('//','/')
        s=open(p,encoding='utf-8',errors='ignore').read()
        if 'noindex' in s[:6000] and 'name="robots"' in s[:6000]: continue
        lang=(re.search(r'<html[^>]*lang="([^"]+)"',s) or [None,'?'])[1]
        s=re.sub(r'<!-- sitefooter:start -->.*?<!-- sitefooter:end -->','',s,flags=re.S)
        s=re.sub(r'<(script|style|svg|head|nav|header|footer)\b.*?</\1>','',s,flags=re.S|re.I)
        t=html.unescape(re.sub(r'<[^>]+>',' ',s))
        cjk=lang.split('-')[0] in ('ja','zh','ko','th')
        if cjk: toks=[c for c in re.sub(r'\s+','',t)]
        else: toks=re.findall(r'\w+',t.lower())
        pages[u]=(lang,toks,cjk)
K=5
sh={u:set(tuple(t[i:i+K]) for i in range(max(0,len(t)-K+1))) for u,(l,t,c) in pages.items()}
cnt=collections.Counter(x for s in sh.values() for x in s)
out=[]
for u,(l,t,c) in pages.items():
    s=sh[u]
    if not s: continue
    uniq=sum(1 for x in s if cnt[x]==1)/len(s)
    out.append((u,l,len(t),round(uniq*100)))
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False)
def grp(u):
    if u.startswith('/tools/'): return 'tools'
    if u.startswith('/blog/'): return 'blog'
    if any(k in u for k in ('privacy','terms','support','legal')): return 'legal'
    return 'product/home'
G=collections.defaultdict(list)
for u,l,n,q in out: G[grp(u)].append(q)
for g,v in G.items():
    v=sorted(v); print(g,len(v),'median uniq%',v[len(v)//2],'<40%:',sum(1 for x in v if x<40),'<30%:',sum(1 for x in v if x<30))
print('total pages',len(out))
print('--- tools pages lowest uniqueness')
for u,l,n,q in sorted([o for o in out if grp(o[0])=='tools'],key=lambda o:o[3])[:30]: print(q,'%',n,l,u)
