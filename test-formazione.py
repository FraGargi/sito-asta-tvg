from main import SessionLocal, Giocatore, calcola_formazione_tipo

db = SessionLocal()

# Prende il primo giocatore disponibile nel database per fare un test
test_giocatore = db.query(Giocatore).first()

if test_giocatore:
    print(f"🔍 Test in corso per la squadra: [{test_giocatore.squadra_serie_a}] (Giocatore test: {test_giocatore.nome})")
    formazione = calcola_formazione_tipo(db, test_giocatore.squadra_serie_a)
    
    print(f"📊 Giocatori trovati per la formazione: {len(formazione)}")
    for p in formazione:
        print(f" - [{p['ruolo']}] {p['nome']} (Status: {p['formazione']})")
else:
    print("❌ Errore: Il database è completamente vuoto! Hai dimenticato di fare il reset di fanta.db o di lanciare aggiorna.py?")

db.close()