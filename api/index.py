import os, re, json, tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pypdf import PdfReader
from groq import Groq

app=FastAPI(title="AI PDF Assistant")
documents={}
history=[]

PAGE="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI PDF Assistant</title>
<style>body{margin:0;background:#09090d;color:#eee;font:14px Arial}.app{display:grid;grid-template-columns:240px 1fr;min-height:100vh}.side{padding:22px 16px;background:#111118;border-right:1px solid #292933}.brand{font-size:18px;font-weight:700;margin-bottom:25px}.sub{color:#777;font-size:11px;margin-top:4px}button,.upload{display:block;width:100%;padding:11px;margin:9px 0;border:1px solid #333;border-radius:9px;background:#17171f;color:#ddd;cursor:pointer}.docs{margin-top:20px}.doc{padding:9px;border-radius:7px;cursor:pointer;font-size:12px}.doc:hover{background:#25212d}.main{min-width:0}.top{height:58px;padding:0 25px;border-bottom:1px solid #222;display:flex;align-items:center;justify-content:space-between}.status{color:#888;font-size:12px}.chat{padding:35px 20px 130px;max-width:800px;margin:auto}.hero{text-align:center;padding:90px 10px}.hero h1{font-size:32px;font-weight:500}.hero p{color:#777;line-height:1.7}.msg{margin:0 0 22px}.label{color:#777;font-size:11px;margin-bottom:6px}.bubble{padding:14px;border:1px solid #292933;border-radius:12px;white-space:pre-wrap;line-height:1.65;background:#111119}.composer{position:fixed;bottom:0;left:240px;right:0;background:linear-gradient(transparent,#09090d 25%);padding:35px 20px 18px}.bar{max-width:780px;margin:auto;display:flex;gap:10px;background:#14141c;border:1px solid #333;border-radius:14px;padding:10px}.bar textarea{flex:1;background:transparent;border:0;outline:0;color:#eee;resize:none;min-height:38px}.send{width:45px}.on{background:#6d4aff}.ats{max-width:900px;margin:auto;padding:45px 20px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{padding:20px;border:1px solid #292933;border-radius:14px;background:#111119}.card input{width:100%;margin-top:12px}.result{margin-top:20px;padding:20px;border:1px solid #292933;border-radius:14px}.tag{display:inline-block;padding:6px 9px;margin:4px;background:#222;border-radius:7px;font-size:12px}@media(max-width:700px){.app{grid-template-columns:1fr}.side{display:none}.composer{left:0}.grid{grid-template-columns:1fr}}</style></head>
<body><div class="app"><aside class="side"><div class="brand">✦ PDF AI<div class="sub">Document Intelligence</div></div><button onclick="newChat()">＋ New Chat</button><label class="upload">＋ Upload PDF<input id="pdf" type="file" accept=".pdf" hidden></label><button onclick="location.href='/ats-analysis'">◈ ATS Analysis</button><div class="docs" id="docs"></div></aside><main class="main"><header class="top"><span>RAG Assistant</span><span class="status" id="status">No document</span></header><section class="chat" id="chat"><div class="hero" id="hero"><div style="font-size:35px">✦</div><h1>Chat with your documents</h1><p>Upload a PDF and ask questions about it, or use web search.</p></div></section><div class="composer"><div class="bar"><textarea id="q" placeholder="Upload a PDF to start..." disabled></textarea><button class="send" onclick="send()">↑</button></div><button id="web" onclick="web=!web;this.classList.toggle('on',web);q.disabled=false">🌐 Web Search</button></div></main></div>
<script>let selected='',web=false;const q=document.getElementById('q'),chat=document.getElementById('chat'),status=document.getElementById('status');function esc(s){return s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}async function load(){let d=await(await fetch('/documents')).json();document.getElementById('docs').innerHTML=d.documents.map(x=>'<div class="doc" onclick="selectDoc('+JSON.stringify(x)+')">📄 '+esc(x)+'</div>').join('')}function selectDoc(x){selected=x;q.disabled=false;q.placeholder='Ask anything about '+x+'...';status.textContent='● '+x}function add(w,t){let d=document.createElement('div');d.className='msg';d.innerHTML='<div class="label">'+w+'</div><div class="bubble"></div>';d.querySelector('.bubble').textContent=t;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d.querySelector('.bubble')}async function send(){let x=q.value.trim();if(!x)return;if(!web&&!selected){add('Assistant','Please upload and select a PDF first.');return}q.value='';document.getElementById('hero').style.display='none';add('You',x);let b=add('Assistant','Thinking...');try{let r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:x,selected_document:selected,use_web:web})});let d=await r.json();b.textContent=d.answer||d.error}catch(e){b.textContent='Request failed. Check your Vercel environment variables.'}}async function newChat(){await fetch('/new-chat',{method:'POST'});location.reload()}document.getElementById('pdf').addEventListener('change',async e=>{let f=e.target.files[0];if(!f)return;status.textContent='Processing...';let fd=new FormData();fd.append('file',f);try{let r=await fetch('/upload',{method:'POST',body:fd}),d=await r.json();if(!r.ok)throw Error(d.detail);selected=d.filename;await load();selectDoc(selected)}catch(e){status.textContent=e.message}});q.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});load();</script></body></html>"""

ATS="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ATS Analysis</title><style>body{margin:0;background:#0b0b0f;color:#eee;font:14px Arial;padding:40px}.box{max-width:900px;margin:auto}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card,.result{padding:20px;border:1px solid #292933;border-radius:14px;background:#111119}.card input{width:100%;margin-top:12px}button{padding:12px 18px;margin-top:20px;cursor:pointer}.tag{display:inline-block;padding:6px 9px;margin:4px;background:#222;border-radius:7px;font-size:12px}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style></head><body><div class="box"><a href="/" style="color:#aaa">← Back</a><h1>ATS Resume Analyzer</h1><p>Compare a resume with a job description.</p><div class="grid"><div class="card"><h3>Resume PDF</h3><input id="r" type="file" accept=".pdf"></div><div class="card"><h3>Job Description PDF</h3><input id="j" type="file" accept=".pdf"></div></div><button onclick="analyze()">Analyze Resume</button><div id="out"></div></div><script>async function analyze(){let r=document.getElementById('r').files[0],j=document.getElementById('j').files[0];if(!r||!j)return alert('Upload both PDFs');let f=new FormData();f.append('resume',r);f.append('job_description',j);document.getElementById('out').textContent='Analyzing...';try{let x=await fetch('/ats/analyze',{method:'POST',body:f}),d=await x.json();if(!x.ok)throw Error(d.detail);let a=d.analysis;document.getElementById('out').innerHTML='<div class="result"><h2>ATS Score: '+d.overall_score+'/100</h2><h3>'+d.match_level+'</h3><p><b>Experience:</b> '+a.experience_match+'</p><h3>Matching Skills</h3>'+tags(a.matching_skills)+'<h3>Missing Skills</h3>'+tags(a.missing_skills)+'<h3>Matching Keywords</h3>'+tags(a.matching_keywords)+'<h3>Missing Keywords</h3>'+tags(a.missing_keywords)+'<h3>Strengths</h3><ul>'+list(a.strengths)+'</ul><h3>Recommendations</h3><ul>'+list(a.recommendations)+'</ul></div>'}catch(e){document.getElementById('out').textContent=e.message}}function tags(a){return(a||[]).map(x=>'<span class="tag">'+x+'</span>').join('')}function list(a){return(a||[]).map(x=>'<li>'+x+'</li>').join('')}</script></body></html>"""

def client():
    key=os.getenv("GROQ_API_KEY")
    if not key: raise RuntimeError("GROQ_API_KEY is not configured in Vercel.")
    return Groq(api_key=key)

def text_from_pdf(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf",delete=False) as f:
        f.write(data); p=f.name
    try:return "\n\n".join((x.extract_text() or "") for x in PdfReader(p).pages).strip()
    finally:
        try:os.unlink(p)
        except OSError:pass

@app.get("/",response_class=HTMLResponse)
def home(): return PAGE

@app.get("/ats-analysis",response_class=HTMLResponse)
def ats_page(): return ATS

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/documents")
def docs(): return {"documents":list(documents)}

@app.post("/upload")
async def upload(file:UploadFile=File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"): raise HTTPException(400,"Please upload a PDF file.")
    t=text_from_pdf(await file.read())
    if not t: raise HTTPException(400,"Could not extract text from this PDF.")
    documents[os.path.basename(file.filename)]=t
    return {"filename":os.path.basename(file.filename),"documents":list(documents)}

@app.post("/new-chat")
def reset(): history.clear(); return {"message":"New chat started"}

@app.post("/chat")
def chat(body:dict):
    question=str(body.get("question","")).strip()
    if not question: raise HTTPException(400,"Question is required.")
    if body.get("use_web"):
        key=os.getenv("TAVILY_API_KEY")
        if not key: raise HTTPException(500,"TAVILY_API_KEY is not configured in Vercel.")
        import requests
        rr=requests.post("https://api.tavily.com/search",json={"api_key":key,"query":question,"max_results":5},timeout=20).json()
        context="\n\n".join(x.get("content","") for x in rr.get("results",[]))
        prompt=f"Answer using only these web results:\n{context}\n\nQuestion: {question}"
    else:
        name=body.get("selected_document")
        if name not in documents:return {"error":"Please select a valid PDF first or enable Web Search."}
        terms=set(re.findall(r"[a-zA-Z0-9]{3,}",question.lower()))
        parts=documents[name]; chunks=[parts[i:i+3500] for i in range(0,len(parts),3500)]
        context="\n\n---\n\n".join(sorted(chunks,key=lambda x:sum(x.lower().count(t) for t in terms),reverse=True)[:4])
        prompt=f"Answer only from the PDF context. If unsupported, say you could not find it.\nPDF CONTEXT:\n{context}\nQUESTION:\n{question}"
    ans=client().chat.completions.create(model="openai/gpt-oss-20b",messages=[{"role":"user","content":prompt}],temperature=0,max_tokens=1500).choices[0].message.content
    history.extend([question,ans]); return {"answer":ans,"route":"web" if body.get("use_web") else "pdf","sources":[]}

@app.post("/ats/analyze")
async def ats_analyze(resume:UploadFile=File(...),job_description:UploadFile=File(...)):
    rt=text_from_pdf(await resume.read()); jt=text_from_pdf(await job_description.read())
    if not rt or not jt: raise HTTPException(400,"Could not extract text from one of the PDFs.")
    prompt=f"""Compare this resume with this job description. Return ONLY JSON with exactly these fields: matching_skills, missing_skills, matching_keywords, missing_keywords, experience_match, strengths, recommendations. Treat alternative technologies as one broader requirement. Do not invent experience. Do not calculate a score.
JOB DESCRIPTION:
{jt}
RESUME:
{rt}"""
    raw=client().chat.completions.create(model="openai/gpt-oss-20b",messages=[{"role":"user","content":prompt}],temperature=0,max_tokens=2500).choices[0].message.content.strip()
    raw=raw.replace(chr(96)*3+"json","").replace(chr(96)*3,"").strip()
    try:a=json.loads(raw)
    except Exception:raise HTTPException(502,"The AI returned an invalid analysis. Please try again.")
    ms=a.get("matching_skills",[]); xs=a.get("missing_skills",[]); mk=a.get("matching_keywords",[]); xk=a.get("missing_keywords",[])
    s=(len(ms)/(len(ms)+len(xs))*100) if ms or xs else 0; k=(len(mk)/(len(mk)+len(xk))*100) if mk or xk else 0
    score=round(s*.65+k*.35)
    level="Excellent Match" if score>=90 else "Strong Match" if score>=75 else "Moderate Match" if score>=60 else "Weak Match" if score>=40 else "Poor Match"
    return {"overall_score":score,"match_level":level,"analysis":a}
