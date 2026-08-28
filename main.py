from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Optional
import time
import io
import csv
import os
import random

SQLALCHEMY_DATABASE_URL = "sqlite:///./fanta.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Squadra(Base):
    __tablename__ = "squadre"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    budget_iniziale = Column(Integer, default=500)

class InfoSquadraSerieA(Base):
    __tablename__ = "info_squadre_serie_a"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    modulo = Column(String, default="-")
    formazione_tipo = Column(String, default="-")
    rigoristi = Column(String, default="-")
    piazzati = Column(String, default="-")
    ballottaggi = Column(String, default="-")

class Giocatore(Base):
    __tablename__ = "giocatori"
    id = Column(Integer, primary_key=True, index=True)
    fantacalcio_id = Column(String, default="")
    nome = Column(String, index=True)
    ruolo = Column(String, index=True) 
    ruoli_mantra = Column(String, default="-")
    squadra_serie_a = Column(String, default="Sconosciuta", index=True)
    quotazione = Column(String, default="1")
    quotazione_mantra = Column(String, default="1")
    fvm = Column(String, default="0")
    media = Column(String, default="-")
    fantamedia = Column(String, default="-")
    titolarita = Column(String, default="-")
    affidabilita = Column(String, default="-")
    integrita = Column(String, default="-")
    rigori = Column(String, default="-")
    piazzati = Column(String, default="-")
    formazione = Column(String, default="-")
    dettaglio_ruolo = Column(String, default="-")
    descrizione = Column(String, default="-")

    squadra_id = Column(Integer, ForeignKey("squadre.id"), nullable=True, index=True)
    costo = Column(Integer, nullable=True)
    assegnato_il = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Asta Fantacalcio")
templates = Jinja2Templates(directory="templates")

REGOLE_ROSA = {"P": 3, "D": 8, "C": 8, "A": 6}
SLOT_TOTALI = sum(REGOLE_ROSA.values())

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

stato_asta = {
    "nome_asta": "ASTA FANTACALCIO",
    "attiva": False, "giocatore_id": None, "nome": "", "ruolo": "", "squadra_serie_a": "", "prezzo": 1, "fine_timer": 0,
    "fvm": "0", "titolarita": "-", "affidabilita": "-", "integrita": "-",
    "rigori": "-", "piazzati": "-", "formazione": "-", "dettaglio_ruolo": "-", "descrizione": "-",
    "ultimi_rilanci": [],
    "squadra_in_vantaggio": "Nessuna",
    "version": 0
}

class Assegnazione(BaseModel): giocatore_id: int; squadra_id: int; costo: int
class UpdateLive(BaseModel): giocatore_id: Optional[int] = None; prezzo: Optional[int] = None; azione: str
class Svincolo(BaseModel): giocatore_id: int
class NomeAsta(BaseModel): nome: str
class Rilancio(BaseModel): squadra_id: int; incremento: int = 1
class ModificaBudget(BaseModel): squadra_id: int; budget_iniziale: int

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if db.query(Squadra).count() == 0:
        db.add_all([Squadra(nome=f"Team {i}") for i in range(1, 9)])
        db.commit()
    db.close()

@app.get("/")
def read_admin(request: Request, db: Session = Depends(get_db)):
    squadre = db.query(Squadra).all()
    giocatori_liberi = db.query(Giocatore).filter(Giocatore.squadra_id == None).order_by(Giocatore.nome).all()
    return templates.TemplateResponse(request=request, name="admin.html", context={"squadre": squadre, "giocatori": giocatori_liberi})

@app.get("/tv")
def read_tv(request: Request):
    return templates.TemplateResponse(request=request, name="tv.html")

@app.get("/user")
def read_user(request: Request, db: Session = Depends(get_db)):
    squadre = db.query(Squadra).all()
    return templates.TemplateResponse(request=request, name="user.html", context={"squadre": squadre})

@app.post("/api/imposta_nome_asta")
def imposta_nome_asta(dati: NomeAsta):
    global stato_asta
    stato_asta["nome_asta"] = dati.nome.upper()
    stato_asta["version"] += 1
    return {"status": "success"}

@app.get("/api/esporta_csv")
def esporta_csv(db: Session = Depends(get_db)):
    squadre = db.query(Squadra).all()
    output = io.StringIO()
    
    for sq in squadre:
        # Delimitatore iniziale di blocco squadra richiesto da Leghe FC
        output.write("$,$,$\n")
        
        giocatori = db.query(Giocatore).filter(Giocatore.squadra_id == sq.id).all()
        for g in giocatori:
            # Rimuove eventuali virgole dal nome squadra per non corrompere la formattazione CSV
            nome_sq = str(sq.nome).replace(",", "")
            
            # Leghe FC richiede rigorosamente l'ID ufficiale del giocatore
            fanta_id = g.fantacalcio_id if g.fantacalcio_id else str(g.id)
            costo = g.costo if g.costo is not None else 1
            
            output.write(f"{nome_sq},{fanta_id},{costo}\n")
            
    # Delimitatore finale di chiusura file
    output.write("$,$,$\n")
    output.seek(0)
    
    return StreamingResponse(
        output, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=rose_leghe_fantacalcio.csv"}
    )
    
@app.get("/api/lista_giocatori")
def lista_giocatori(db: Session = Depends(get_db)):
    giocatori = db.query(Giocatore).all()
    squadre = {s.id: s.nome for s in db.query(Squadra).all()}
    return [{
        "id": g.id, "nome": g.nome, "ruolo": g.ruolo, "squadra_serie_a": g.squadra_serie_a,
        "quotazione": g.quotazione, "fvm": g.fvm, 
        "titolarita": g.titolarita, "affidabilita": g.affidabilita, "integrita": g.integrita,
        "rigori": g.rigori, "piazzati": g.piazzati, "formazione": g.formazione,
        "dettaglio_ruolo": g.dettaglio_ruolo, "descrizione": g.descrizione,
        "squadra_proprietaria": squadre.get(g.squadra_id) if g.squadra_id else None,
        "costo": g.costo
    } for g in giocatori]

@app.get("/api/info_squadre_serie_a")
def info_squadre_serie_a(db: Session = Depends(get_db)):
    info = db.query(InfoSquadraSerieA).all()
    return {i.nome: {"modulo": i.modulo, "formazione_tipo": i.formazione_tipo, "rigoristi": i.rigoristi, "piazzati": i.piazzati, "ballottaggi": i.ballottaggi} for i in info}

@app.post("/api/live")
def gestisci_live(dati: UpdateLive, db: Session = Depends(get_db)):
    global stato_asta
    if dati.azione == "start" and dati.giocatore_id:
        g = db.query(Giocatore).filter(Giocatore.id == dati.giocatore_id).first()
        if g:
            stato_asta.update({
                "attiva": True, "giocatore_id": g.id, "nome": g.nome, "ruolo": g.ruolo, "squadra_serie_a": g.squadra_serie_a, 
                "prezzo": 1, "fine_timer": int(time.time()) + 10, "fvm": g.fvm, 
                "titolarita": g.titolarita, "affidabilita": g.affidabilita, "integrita": g.integrita,
                "rigori": g.rigori, "piazzati": g.piazzati, "formazione": g.formazione, 
                "dettaglio_ruolo": g.dettaglio_ruolo, "descrizione": g.descrizione,
                "ultimi_rilanci": [{"squadra": "Base d'asta", "prezzo": 1}],
                "squadra_in_vantaggio": "Nessuna (Base d'asta)"
            })
    elif dati.azione == "aggiorna" and dati.prezzo is not None:
        stato_asta["prezzo"] = dati.prezzo
        stato_asta["fine_timer"] = int(time.time()) + 10
    elif dati.azione == "timer": 
        stato_asta["fine_timer"] = int(time.time()) + 10 
    elif dati.azione == "stop": 
        stato_asta["attiva"] = False
    
    stato_asta["version"] += 1
    return stato_asta

@app.post("/api/rilancia")
def rilancia_asta(dati: Rilancio, db: Session = Depends(get_db)):
    global stato_asta
    if not stato_asta["attiva"]:
        raise HTTPException(status_code=400, detail="Nessuna asta attiva al momento!")
        
    if int(time.time()) >= stato_asta["fine_timer"]:
        raise HTTPException(status_code=400, detail="Tempo scaduto! Non puoi più rilanciare.")
        
    if dati.incremento not in [1, 5, 10]:
        raise HTTPException(status_code=400, detail="Incremento non valido!")
    
    squadra = db.query(Squadra).filter(Squadra.id == dati.squadra_id).first()
    if not squadra:
        raise HTTPException(status_code=404, detail="Squadra non trovata")
        
    giocatori_squadra = db.query(Giocatore).filter(Giocatore.squadra_id == squadra.id).all()
    
    ruolo_asta = stato_asta["ruolo"]
    count_ruolo = sum(1 for g in giocatori_squadra if g.ruolo == ruolo_asta)
    limite_ruolo = REGOLE_ROSA.get(ruolo_asta, 99)
    if count_ruolo >= limite_ruolo:
        raise HTTPException(status_code=400, detail=f"Hai già raggiunto il limite massimo di {limite_ruolo} per il ruolo {ruolo_asta}!")
    
    spesa = sum(g.costo for g in giocatori_squadra if g.costo)
    slot_v = SLOT_TOTALI - len(giocatori_squadra)
    crediti_da_conservare = slot_v - 1 if slot_v > 0 else 0
    offerta_max = squadra.budget_iniziale - spesa - crediti_da_conservare
    
    nuovo_prezzo = stato_asta["prezzo"] + dati.incremento
    if nuovo_prezzo > offerta_max:
        raise HTTPException(status_code=400, detail=f"Crediti insufficienti! (Devi conservare 1 cr. per i tuoi altri {crediti_da_conservare} slot vuoti)")
        
    stato_asta["prezzo"] = nuovo_prezzo
    stato_asta["fine_timer"] = int(time.time()) + 10
    stato_asta["squadra_in_vantaggio"] = squadra.nome
    stato_asta["version"] += 1
    
    if "ultimi_rilanci" not in stato_asta:
        stato_asta["ultimi_rilanci"] = []
    stato_asta["ultimi_rilanci"].insert(0, {"squadra": squadra.nome, "prezzo": nuovo_prezzo})
    stato_asta["ultimi_rilanci"] = stato_asta["ultimi_rilanci"][:5]
    
    return {"status": "success", "nuovo_prezzo": nuovo_prezzo}

@app.get("/api/live")
def ottieni_live(): return stato_asta

@app.post("/api/assegna")
def assegna_giocatore(dati: Assegnazione, db: Session = Depends(get_db)):
    giocatore = db.query(Giocatore).filter(Giocatore.id == dati.giocatore_id).first()
    squadra = db.query(Squadra).filter(Squadra.id == dati.squadra_id).first()
    if not giocatore or not squadra or giocatore.squadra_id is not None: 
        raise HTTPException(status_code=400, detail="Giocatore o Squadra non validi o già assegnato")
    
    giocatori_squadra = db.query(Giocatore).filter(Giocatore.squadra_id == squadra.id).all()
    
    count_ruolo = sum(1 for g in giocatori_squadra if g.ruolo == giocatore.ruolo)
    limite_ruolo = REGOLE_ROSA.get(giocatore.ruolo, 99)
    if count_ruolo >= limite_ruolo:
        raise HTTPException(status_code=400, detail=f"Errore: La squadra ha già {limite_ruolo} giocatori per il ruolo {giocatore.ruolo}!")
    
    spesa = sum(g.costo for g in giocatori_squadra if g.costo)
    slot_v = SLOT_TOTALI - len(giocatori_squadra)
    crediti_da_conservare = slot_v - 1 if slot_v > 0 else 0
    offerta_max = squadra.budget_iniziale - spesa - crediti_da_conservare
    
    if dati.costo > offerta_max: 
        raise HTTPException(status_code=400, detail=f"Errore: Crediti insufficienti. Max offerta per questa squadra: {offerta_max}")
        
    giocatore.squadra_id = squadra.id; giocatore.costo = dati.costo; giocatore.assegnato_il = int(time.time()); db.commit()
    global stato_asta; stato_asta["attiva"] = False; stato_asta["version"] += 1
    return {"status": "success"}

@app.post("/api/svincola")
def svincola_giocatore(dati: Svincolo, db: Session = Depends(get_db)):
    giocatore = db.query(Giocatore).filter(Giocatore.id == dati.giocatore_id).first()
    if giocatore:
        giocatore.squadra_id = None; giocatore.costo = None; giocatore.assegnato_il = 0; db.commit()
        global stato_asta; stato_asta["version"] += 1
    return {"status": "success"}

@app.post("/api/modifica_budget")
def modifica_budget(dati: ModificaBudget, db: Session = Depends(get_db)):
    squadra = db.query(Squadra).filter(Squadra.id == dati.squadra_id).first()
    if not squadra:
        raise HTTPException(status_code=404, detail="Squadra non trovata")
    squadra.budget_iniziale = dati.budget_iniziale
    db.commit()
    global stato_asta; stato_asta["version"] += 1
    return {"status": "success"}

@app.post("/api/pesca_casuale")
def pesca_casuale(ruolo: Optional[str] = None, db: Session = Depends(get_db)):
    global stato_asta
    query = db.query(Giocatore).filter(Giocatore.squadra_id == None)
    if ruolo and ruolo in ["P", "D", "C", "A"]:
        query = query.filter(Giocatore.ruolo == ruolo)
    liberi = query.all()
    if not liberi:
        raise HTTPException(status_code=400, detail=f"Nessun giocatore disponibile per il ruolo {ruolo}!" if ruolo else "Nessun giocatore disponibile!")
    g = random.choice(liberi)
    stato_asta.update({
        "attiva": True, "giocatore_id": g.id, "nome": g.nome, "ruolo": g.ruolo, "squadra_serie_a": g.squadra_serie_a, 
        "prezzo": 1, "fine_timer": int(time.time()) + 10, "fvm": g.fvm, 
        "titolarita": g.titolarita, "affidabilita": g.affidabilita, "integrita": g.integrita,
        "rigori": g.rigori, "piazzati": g.piazzati, "formazione": g.formazione, 
        "dettaglio_ruolo": g.dettaglio_ruolo, "descrizione": g.descrizione,
        "ultimi_rilanci": [{"squadra": "Base d'asta", "prezzo": 1}],
        "squadra_in_vantaggio": "Nessuna (Base d'asta)"
    })
    stato_asta["version"] += 1
    return {"status": "success", "nome": g.nome}

@app.get("/api/ultimi_acquisti")
def ultimi_acquisti(db: Session = Depends(get_db)):
    giocatori = db.query(Giocatore).filter(Giocatore.squadra_id != None).order_by(Giocatore.assegnato_il.desc()).limit(12).all()
    squadre = {s.id: s.nome for s in db.query(Squadra).all()}
    return [{"id": g.id, "nome": g.nome, "ruolo": g.ruolo, "costo": g.costo, "squadra": squadre.get(g.squadra_id, "Sconosciuta")} for g in giocatori]

@app.get("/api/top_svincolati")
def top_svincolati(db: Session = Depends(get_db)):
    liberi = db.query(Giocatore).filter(Giocatore.squadra_id == None).all()
    def get_fvm(g):
        try: return float(str(g.fvm).replace(",", "."))
        except: return 0.0
    top = sorted(liberi, key=get_fvm, reverse=True)[:5]
    return [{"nome": g.nome, "ruolo": g.ruolo, "fvm": g.fvm} for g in top]

@app.get("/api/stato_squadre")
def stato_squadre(db: Session = Depends(get_db)):
    squadre = db.query(Squadra).all()
    risultato = []
    for s in squadre:
        giocatori = db.query(Giocatore).filter(Giocatore.squadra_id == s.id).all()
        spesa_totale = sum(g.costo for g in giocatori if g.costo)
        stats_ruoli = {"P": {"count": 0, "spesa": 0}, "D": {"count": 0, "spesa": 0}, "C": {"count": 0, "spesa": 0}, "A": {"count": 0, "spesa": 0}}
        for g in giocatori:
            r = (g.ruolo or "").strip().upper()
            if r in stats_ruoli:
                stats_ruoli[r]["count"] += 1 
                stats_ruoli[r]["spesa"] += (g.costo or 0)
        perc_tot = int((spesa_totale / s.budget_iniziale) * 100) if s.budget_iniziale > 0 else 0
        for r in stats_ruoli:
            stats_ruoli[r]["perc"] = int((stats_ruoli[r]["spesa"] / s.budget_iniziale) * 100) if s.budget_iniziale > 0 else 0
            stats_ruoli[r]["max"] = REGOLE_ROSA[r]
        slot_v = SLOT_TOTALI - len(giocatori)
        risultato.append({
            "id": s.id,
            "nome": s.nome, 
            "budget_iniziale": s.budget_iniziale,
            "spesi": spesa_totale,
            "crediti_residui": s.budget_iniziale - spesa_totale, 
            "offerta_max": (s.budget_iniziale - spesa_totale - (slot_v - 1)) if slot_v > 0 else 0, 
            "perc_totale": perc_tot, 
            "stats_ruoli": stats_ruoli, 
            "rosa": [{"id": g.id, "nome": g.nome, "ruolo": g.ruolo, "costo": g.costo} for g in giocatori]
        })
    return risultato