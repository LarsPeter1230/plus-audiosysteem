import re, os
SRC="/tmp/demo_src2"; OUT="/tmp/demo"
os.makedirs(OUT, exist_ok=True)
PAGES=["login","volume","presets","tts","beheer","gebruikers","oidc","logs"]
NAVMAP={"/volume":"volume.html","/presets":"presets.html","/tts":"tts.html",
        "/beheer":"beheer.html","/gebruikers":"gebruikers.html","/admin/oidc":"oidc.html",
        "/logs":"logs.html","/logout":"login.html","/onboarding":"volume.html","/":"volume.html"}

def relink(s):
    for a,b in NAVMAP.items():
        s=s.replace('href="%s"'%a,'href="%s"'%b)
    s=re.sub(r'href="/[a-zA-Z0-9_/-]*"', lambda m: m.group(0) if m.group(0).endswith('.html"') else 'href="#"', s)
    s=s.replace('="/static/','="static/')
    s=re.sub(r'action="/[^"]*"', 'action="#"', s)
    return s

def inject(s):
    tag='<script src="mock.js"></script>'
    if "<head>" in s: return s.replace("<head>","<head>\n"+tag,1)
    m=re.search(r"<head[^>]*>", s)
    if m: return s[:m.end()]+"\n"+tag+s[m.end():]
    return tag+"\n"+s

for p in PAGES:
    fp=os.path.join(SRC,p+".html")
    if not os.path.exists(fp): print("mist",p); continue
    s=open(fp).read()
    s=re.sub(r"[Kk]oelhuis","Demo",s)   # veiligheidsnet
    s=inject(relink(s))
    open(os.path.join(OUT,p+".html"),"w").write(s)
    print("built",p,len(s))

open(os.path.join(OUT,"index.html"),"w").write(
    '<!doctype html><meta charset="utf-8"><title>PLUS Audiosysteem — demo</title>'
    '<meta http-equiv="refresh" content="0; url=login.html">'
    '<body style="font:16px sans-serif;padding:40px">Demo laden… <a href="login.html">Openen</a></body>')
print("built index (→ login)")
