import pandas as pd
import sqlite3
import os

excel_path = 'Quotazioni_Fantacalcio_Stagione_2026_27.xlsx'

if not os.path.exists(excel_path):
    print(f"❌ Errore: Non trovo il file '{excel_path}' nella cartella!")
else:
    print(f"📂 Lettura del file {excel_path} in corso...")
    df = pd.read_excel(excel_path, sheet_name='Tutti', header=1)

    out_df = pd.DataFrame()
    out_df['Fantacalcio_Id'] = df['Id'].astype(str)
    out_df['Nome'] = df['Nome']
    out_df['Ruolo'] = df['R']
    out_df['Ruoli_Mantra'] = df['RM'].fillna('-')
    out_df['Squadra_Appartenenza'] = df['Squadra']
    out_df['Quotazione'] = df['Qt.A'].astype(str)
    out_df['Quotazione_Mantra'] = df['Qt.A M'].astype(str)
    out_df['FVM'] = df['FVM'].astype(str)
    
    out_df['Media'] = df['Media'].astype(str) if 'Media' in df.columns else '-'
    out_df['Fantamedia'] = df['Fantamedia'].astype(str) if 'Fantamedia' in df.columns else '-'
    out_df['Titolarita'] = df['Titolarità'].astype(str) if 'Titolarità' in df.columns else '-'
    out_df['Affidabilita'] = df['Affidabilità'].astype(str) if 'Affidabilità' in df.columns else '-'
    out_df['Integrita'] = df['Integrità'].astype(str) if 'Integrità' in df.columns else '-'
    out_df['Rigori'] = df['Rigori'].astype(str) if 'Rigori' in df.columns else '-'
    out_df['Piazzati'] = df['Piazzati'].astype(str) if 'Piazzati' in df.columns else '-'
    out_df['Formazione'] = df['Formazione'].astype(str) if 'Formazione' in df.columns else 'Riserva'
    out_df['Dettaglio_Ruolo'] = df['Dettaglio_Ruolo'].astype(str) if 'Dettaglio_Ruolo' in df.columns else '-'
    out_df['Descrizione'] = df['Descrizione'].astype(str) if 'Descrizione' in df.columns else '-'

    out_df.to_csv('giocatori.csv', sep=';', index=False, encoding='utf-8')
    print("✅ Generato 'giocatori.csv'. Aggiornamento database SQLite in corso...")

    conn = sqlite3.connect('fanta.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giocatori (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fantacalcio_id TEXT, nome TEXT, ruolo TEXT, ruoli_mantra TEXT,
            squadra_serie_a TEXT, quotazione TEXT, quotazione_mantra TEXT, fvm TEXT, media TEXT, fantamedia TEXT,
            titolarita TEXT, affidabilita TEXT, integrita TEXT, rigori TEXT, piazzati TEXT, formazione TEXT,
            dettaglio_ruolo TEXT, descrizione TEXT, squadra_id INTEGER, costo INTEGER, assegnato_il INTEGER
        )
    ''')

    cursor.execute('DELETE FROM giocatori WHERE squadra_id IS NULL')

    giocatori_inseriti = 0
    for _, r in out_df.iterrows():
        cursor.execute('''
            INSERT INTO giocatori (fantacalcio_id, nome, ruolo, ruoli_mantra, squadra_serie_a, quotazione, quotazione_mantra, fvm, media, fantamedia, titolarita, affidabilita, integrita, rigori, piazzati, formazione, dettaglio_ruolo, descrizione)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(r['Fantacalcio_Id']), str(r['Nome']), str(r['Ruolo']), str(r['Ruoli_Mantra']), 
            str(r['Squadra_Appartenenza']), str(r['Quotazione']), str(r['Quotazione_Mantra']), 
            str(r['FVM']), str(r['Media']), str(r['Fantamedia']), str(r['Titolarita']), 
            str(r['Affidabilita']), str(r['Integrita']), str(r['Rigori']), str(r['Piazzati']), 
            str(r['Formazione']), str(r['Dettaglio_Ruolo']), str(r['Descrizione'])
        ))
        giocatori_inseriti += 1

    # ==========================================
    # 1. INIEZIONE DATI TATTICI SQUADRE SERIE A
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS info_squadre_serie_a (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, modulo TEXT,
            formazione_tipo TEXT, rigoristi TEXT, piazzati TEXT, ballottaggi TEXT
        )
    ''')

    dettagli_squadre = {
        "Lazio": {
            "modulo": "4-2-3-1",
            "formazione_tipo": "Mandas; Marusic, Sutalo, Provstgaard, Pedraza; Rovella, Frattesi; Cancellieri, Taylor, Zaccagni; Pinamonti",
            "rigoristi": "1° Zaccagni, 2° Cataldi, 3° Taylor",
            "piazzati": "Punizioni: Rovella, Zaccagni, Cataldi, Noslin. Angoli: Zaccagni, Pedraza, Isaksen, Noslin.",
            "ballottaggi": "Marusic 40% - Floriani 35% - Lazzari 25% | Sutalo 55% - Doekhi 45% | Frattesi 40% - Dele Bashiru 20% - Cataldi 20% - Taylor 20% | Cancellieri 51% - Isaksen 49% | Taylor 60% - Dia 40% | Pinamonti 75% - Dia 25%"
        }
    }

    for sq_nome, info in dettagli_squadre.items():
        cursor.execute('''
            INSERT INTO info_squadre_serie_a (nome, modulo, formazione_tipo, rigoristi, piazzati, ballottaggi)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(nome) DO UPDATE SET
            modulo=excluded.modulo, formazione_tipo=excluded.formazione_tipo, rigoristi=excluded.rigoristi, piazzati=excluded.piazzati, ballottaggi=excluded.ballottaggi
        ''', (sq_nome, info["modulo"], info["formazione_tipo"], info["rigoristi"], info["piazzati"], info["ballottaggi"]))

   # ==========================================
    # 2. INIEZIONE APPUNTI DI SCOUTING GIOCATORI
    # ==========================================
    scouting_giocatori = {
        "MANDAS": {
            "titolarita": "8/10", "affidabilita": "7/10", "integrita": "9/10",
            "formazione": "TITOLARE | Gerarchia definita su Motta",
            "descrizione": "Rientrato dal prestito in Inghilterra, trova i galloni da titolare. Dotato di buona presenza e ottima reattività tra i pali, deve migliorare nelle uscite e nel gioco coi piedi. Potrebbe essere maggiormente sotto pressione in avvio di stagione."
        },
        "MOTTA": {
            "titolarita": "3/10", "affidabilita": "7/10", "integrita": "9/10",
            "formazione": "RISERVA | Secondo portiere",
            "descrizione": "Ha messo in mostra buoni fondamentali e potenzialità fisiche, ma anche lacune dovute all’inesperienza. In partenza il suo ruolo sarà quello di riserva."
        },
        "RENZETTI": {
            "titolarita": "1/10", "affidabilita": "5/10", "integrita": "8/10",
            "formazione": "RISERVA | Terzo portiere",
            "descrizione": "Terzo portiere, non vedrà mai il campo se non in situazioni di emergenza."
        },
        "FURLANETTO": {
            "titolarita": "1/10", "affidabilita": "5/10", "integrita": "7/10",
            "formazione": "RISERVA",
            "descrizione": "Operato alla fine della scorsa stagione per la lesione del crociato, potrebbe rientrare in tempo per giocarsi il ruolo di terzo portiere."
        },
        "PROVSTGAARD": {
            "titolarita": "9/10", "affidabilita": "7/10", "integrita": "9/10",
            "formazione": "TITOLARE | Difensore centrale",
            "descrizione": "I cambiamenti nel reparto lo portano a conquistare il posto. Molto prestante fisicamente, ma anche un po' lento nei movimenti e recuperi. Titolare regolarista per la sufficienza, ma attenzione alla scarsa propensione ai bonus."
        },
        "PEDRAZA": {
            "titolarita": "7/10", "affidabilita": "6/10", "integrita": "8/10",
            "formazione": "TITOLARE | Terzino Sinistro",
            "descrizione": "Esterno difensivo classico, discreta spinta e attenzione difensiva. Garantisce maggiore equilibrio rispetto a Tavares. Buona scelta per una regolarista da modificatore con qualche assist."
        },
        "SUTALO": {
            "titolarita": "8/10", "affidabilita": "6/10", "integrita": "8/10",
            "formazione": "BALLOTTAGGIO | 55% di titolarità",
            "descrizione": "Aggiunge qualità di recupero in velocità. Ben dotato dal punto di vista del palleggio in uscita. Attenzione alla fragilità fisica, ha saltato più di una gara nelle ultime stagioni."
        },
        "DOEKHI": {
            "titolarita": "6/10", "affidabilita": "5/10", "integrita": "9/10",
            "formazione": "BALLOTTAGGIO | 45% con Sutalo",
            "descrizione": "Roccioso difensore arrivato a zero. Prestante fisicamente in area avversaria. Lento e imballato nei movimenti, potrebbe andare in difficoltà se la difesa dovrà accompagnare la pressione alta."
        },
        "MARUSIC": {
            "titolarita": "6/10", "affidabilita": "6/10", "integrita": "8/10",
            "formazione": "BALLOTTAGGIO | 40% Terzino Destro",
            "descrizione": "Difensore poliedrico di equilibrio tattico. In ballottaggio con Floriani e Lazzari, teoricamente favorito. Soffre i palloni alti dal lato opposto, diminuita la sua pericolosità offensiva."
        },
        "TAVARES": {
            "titolarita": "6/10", "affidabilita": "6/10", "integrita": "7/10",
            "formazione": "RISERVA | Terzino Sinistro",
            "descrizione": "Con Gattuso si dovrebbe tornare a maggiore spinta sugli esterni, ma dovrà vedersela con Pedraza. Non è un giocatore dalla titolarità garantita, attenzione a non pagarlo troppo."
        },
        "FLORIANI MUSSOLINI": {
            "titolarita": "6/10", "affidabilita": "6/10", "integrita": "9/10",
            "formazione": "RISERVA | Terzino Destro (35%)",
            "descrizione": "Buona capacità di corsa e sovrapposizione. Manca di esperienza in A, partirà dalla panchina ma troverà spazio. Scommessa a basso costo o per riconferme."
        },
        "PELLEGRINI": {
            "titolarita": "5/10", "affidabilita": "5/10", "integrita": "8/10",
            "formazione": "RISERVA | Terzino Sinistro",
            "descrizione": "L'arrivo di Pedraza lo relega a riserva. Discreta spinta ma tendenza a distrarsi in copertura e a rimediare cartellini."
        },
        "LAZZARI": {
            "titolarita": "5/10", "affidabilita": "5/10", "integrita": "6/10",
            "formazione": "RISERVA | Terzino Destro (25%)",
            "descrizione": "In fase calante. Scarsa titolarità, impiego a partita in corso. Storica fragilità muscolare ai polpacci."
        },
        "ROMAGNOLI": {
            "titolarita": "3/10", "affidabilita": "7/10", "integrita": "7/10",
            "formazione": "ESUBERO / RISERVA",
            "descrizione": "Pessimi rapporti societari, contratto in scadenza e possibile cessione in Arabia. Sconsigliato, altissimo rischio buco in rosa."
        },
        "PATRIC": {
            "titolarita": "3/10", "affidabilita": "5/10", "integrita": "4/10",
            "formazione": "RISERVA",
            "descrizione": "Infortuni cronici e dubbi sulle capacità di recupero. Considerato uomo spogliatoio, sconsigliato l'acquisto."
        },
        "GIGOT": {
            "titolarita": "3/10", "affidabilita": "5/10", "integrita": "4/10",
            "formazione": "RISERVA",
            "descrizione": "Fermo da un anno per problemi a schiena e anca. Condizione avvolta dal mistero, acquisto sconsigliato."
        },
        "TAYLOR": {
            "titolarita": "9/10", "affidabilita": "7/10", "integrita": "8/10",
            "formazione": "TITOLARE | Trequartista o Mezzala (60%)",
            "descrizione": "Il centrocampista di maggiore qualità. Tempi di inserimento e propensione al tiro dal limite. Se gioca trequartista l'appetibilità schizza alle stelle, ottima regolarità di voti."
        },
        "ZACCAGNI": {
            "titolarita": "9/10", "affidabilita": "6/10", "integrita": "7/10",
            "formazione": "TITOLARE | Esterno Sinistro",
            "descrizione": "Da lui ci si aspetta che torni decisivo. Da valutare il pieno recupero fisico post-pubalgia. Il 4-2-3-1 di Gattuso potrebbe abbassarlo leggermente in costruzione. Da prendere se listato CC."
        },
        "FRATTESI": {
            "titolarita": "8/10", "affidabilita": "7/10", "integrita": "7/10",
            "formazione": "TITOLARE | Mediano o Mezzala (40%)",
            "descrizione": "Acquisto importante, poliedrico e flessibile. Ottima capacità di leggere l'azione e proporsi in area avversaria. Titolare indiscusso alla lunga."
        },
        "ISAKSEN": {
            "titolarita": "7/10", "affidabilita": "7/10", "integrita": "8/10",
            "formazione": "BALLOTTAGGIO | 49% Ala Destra",
            "descrizione": "Alternanza con Cancellieri. Sconta un'operazione per pubalgia. Soffre di limiti di personalità e poca lucidità sotto porta. Pochi bonus pesanti in canna (3-4 gol)."
        },
        "CANCELLIERI": {
            "titolarita": "7/10", "affidabilita": "6/10", "integrita": "8/10",
            "formazione": "BALLOTTAGGIO | 51% Ala Destra",
            "descrizione": "Esterno di corsa, manca di confidenza col gol (max 4-5 a campionato). Fatica a difesa schierata. In vantaggio su Isaksen solo per la condizione fisica del danese."
        },
        "CATALDI": {
            "titolarita": "6/10", "affidabilita": "6/10", "integrita": "8/10",
            "formazione": "BALLOTTAGGIO | 20% Mediano",
            "descrizione": "Campione di continuità per il modificatore, ma nel nuovo ruolo da mediano farà più legna e fatica, arrivando spesso in debito d'ossigeno. Riempitivo."
        },
        "ROVELLA": {
            "titolarita": "8/10", "affidabilita": "7/10", "integrita": "6/10",
            "formazione": "TITOLARE | Mediano difensivo",
            "descrizione": "Se recupera fisicamente il posto è suo. Porta voti regolari ma è allergico ai bonus (1 gol in carriera) e incline all'ammonizione."
        },
        "DELE BASHIRU": {
            "titolarita": "6/10", "affidabilita": "5/10", "integrita": "9/10",
            "formazione": "BALLOTTAGGIO | 20% Mediano",
            "descrizione": "Calcio con l'elmetto. Tanta fisicità ma limiti tecnici e tattici evidenti. Non porterà bonus pesanti, acquisto rischioso."
        },
        "PRZYBOREK": {
            "titolarita": "4/10", "affidabilita": "5/10", "integrita": "9/10",
            "formazione": "RISERVA",
            "descrizione": "Impiegato fuori ruolo in preparazione, precludendo il potenziale offensivo. Rischia di vedere poco il campo."
        },
        "BELAHYANE": {
            "titolarita": "4/10", "affidabilita": "5/10", "integrita": "8/10",
            "formazione": "RISERVA",
            "descrizione": "Limiti fisici evidenti da mediano, andrà in difficoltà nei contrasti. Sconsigliato."
        },
        "GALASSI": {
            "titolarita": "2/10", "affidabilita": "5/10", "integrita": "9/10",
            "formazione": "PRIMAVERA",
            "descrizione": "Giovanissimo, probabile dirottamento in Primavera."
        },
        "FARCOMENI": {
            "titolarita": "2/10", "affidabilita": "5/10", "integrita": "9/10",
            "formazione": "PRIMAVERA",
            "descrizione": "Aggregato dalla Primavera, nessun minutaggio previsto."
        },
        "PINAMONTI": {
            "titolarita": "8/10", "affidabilita": "6/10", "integrita": "8/10",
            "formazione": "TITOLARE | Punta (75%)",
            "descrizione": "Costante sui 10 gol a stagione. In vantaggio su Dia. Perfetto attaccante di provincia, beneficerà del gioco sulle fasce."
        },
        "DIA": {
            "titolarita": "7/10", "affidabilita": "5/10", "integrita": "7/10",
            "formazione": "BALLOTTAGGIO | Punta o Treq. (25%)",
            "descrizione": "In discesa costante da due anni. Limiti di freddezza sotto porta, corsa a vuoto e problemi fisici. Acquistarlo è un grande rischio."
        },
        "NOSLIN": {
            "titolarita": "6/10", "affidabilita": "5/10", "integrita": "8/10",
            "formazione": "RISERVA | Esterno / Punta",
            "descrizione": "Vice Zaccagni a sinistra, fatica terribilmente a destra. Utilizzato prevalentemente a gara in corso, da acquistare solo in coppia."
        },
        "RATKOV": {
            "titolarita": "5/10", "affidabilita": "5/10", "integrita": "9/10",
            "formazione": "RISERVA | Punta",
            "descrizione": "Ancora acerbo tecnicamente e muscolarmente. Sfruttabile sui cross, ma il livello della Serie A per ora sembra troppo alto per lui."
        },
        "SERRA": {
            "titolarita": "2/10", "affidabilita": "5/10", "integrita": "9/10",
            "formazione": "PRIMAVERA / SCOMMESSA",
            "descrizione": "Tra i giovani è quello con maggiori potenzialità. Possibile jolly per le riconferme, ma chiuso da Zaccagni e Noslin."
        }
    }

    # Esegue l'aggiornamento (override) per i giocatori presenti nel dizionario
    for nome_giocatore, note in scouting_giocatori.items():
        cursor.execute('''
            UPDATE giocatori
            SET titolarita = ?, affidabilita = ?, integrita = ?, formazione = ?, descrizione = ?
            WHERE nome LIKE ?
        ''', (note['titolarita'], note['affidabilita'], note['integrita'], note['formazione'], note['descrizione'], f"%{nome_giocatore}%"))

    conn.commit()
    conn.close()
    print("✅ Scouting e Tattica caricati! Database pronto.")