import pandas as pd
import sqlite3
import os

excel_path = 'Quotazioni_Fantacalcio_Stagione_2026_27.xlsx'
stats_path = 'Statistiche_Fantacalcio_Stagione_2025_26.xlsx'

if not os.path.exists(excel_path):
    print(f"❌ Errore: Non trovo il file '{excel_path}' nella cartella!")
else:
    print(f"📂 Lettura del file {excel_path} in corso...")
    df = pd.read_excel(excel_path, sheet_name='Tutti', header=1)

    # Unione con le statistiche della stagione precedente (2025/26) se disponibili
    if os.path.exists(stats_path):
        print(f"📂 Lettura delle statistiche 2025/26 da {stats_path} in corso...")
        df_stats = pd.read_excel(stats_path, sheet_name='Tutti', header=1)
        df_stats = df_stats[['Id', 'Pv', 'Mv', 'Fm', 'Gf', 'Gs', 'Ass', 'Amm', 'Esp']].copy()
        df_stats.columns = ['Id', 'stat_pv', 'stat_mv', 'stat_fm', 'stat_gf', 'stat_gs', 'stat_ass', 'stat_amm', 'stat_esp']
        df = pd.merge(df, df_stats, on='Id', how='left')

    out_df = pd.DataFrame()
    out_df['Fantacalcio_Id'] = df['Id'].astype(str)
    out_df['Nome'] = df['Nome']
    out_df['Ruolo'] = df['R']
    out_df['Ruoli_Mantra'] = df['RM'].fillna('-')
    out_df['Squadra_Appartenenza'] = df['Squadra']
    out_df['Quotazione'] = df['Qt.A'].astype(str)
    out_df['Quotazione_Mantra'] = df['Qt.A M'].astype(str)
    out_df['FVM'] = df['FVM'].astype(str)

    # Statistiche 2025/26
    out_df['stat_pv'] = df['stat_pv'].fillna(0) if 'stat_pv' in df.columns else 0
    out_df['stat_mv'] = df['stat_mv'].fillna(0.0) if 'stat_mv' in df.columns else 0.0
    out_df['stat_fm'] = df['stat_fm'].fillna(0.0) if 'stat_fm' in df.columns else 0.0
    out_df['stat_gf'] = df['stat_gf'].fillna(0) if 'stat_gf' in df.columns else 0
    out_df['stat_gs'] = df['stat_gs'].fillna(0) if 'stat_gs' in df.columns else 0
    out_df['stat_ass'] = df['stat_ass'].fillna(0) if 'stat_ass' in df.columns else 0
    out_df['stat_amm'] = df['stat_amm'].fillna(0) if 'stat_amm' in df.columns else 0
    out_df['stat_esp'] = df['stat_esp'].fillna(0) if 'stat_esp' in df.columns else 0

    out_df.to_csv('giocatori.csv', sep=';', index=False, encoding='utf-8')
    print("✅ Generato 'giocatori.csv'. Aggiornamento database SQLite in corso...")

    conn = sqlite3.connect('fanta.db')
    cursor = conn.cursor()

    # Rimuoviamo eventuali tabelle vecchie per pulizia
    cursor.execute('DROP TABLE IF EXISTS info_squadre_serie_a')
    cursor.execute('DROP TABLE IF EXISTS giocatori')

    cursor.execute('''
        CREATE TABLE giocatori (
            id INTEGER PRIMARY KEY AUTOINCREMENT, fantacalcio_id TEXT, nome TEXT, ruolo TEXT, ruoli_mantra TEXT,
            squadra_serie_a TEXT, quotazione TEXT, quotazione_mantra TEXT, fvm TEXT, 
            stat_pv INTEGER DEFAULT 0, stat_mv REAL DEFAULT 0.0, stat_fm REAL DEFAULT 0.0, 
            stat_gf INTEGER DEFAULT 0, stat_gs INTEGER DEFAULT 0, stat_ass INTEGER DEFAULT 0, 
            stat_amm INTEGER DEFAULT 0, stat_esp INTEGER DEFAULT 0,
            squadra_id INTEGER, costo INTEGER, assegnato_il INTEGER
        )
    ''')

    for _, r in out_df.iterrows():
        cursor.execute('''
            INSERT INTO giocatori (fantacalcio_id, nome, ruolo, ruoli_mantra, squadra_serie_a, quotazione, quotazione_mantra, fvm, stat_pv, stat_mv, stat_fm, stat_gf, stat_gs, stat_ass, stat_amm, stat_esp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(r['Fantacalcio_Id']), str(r['Nome']), str(r['Ruolo']), str(r['Ruoli_Mantra']), 
            str(r['Squadra_Appartenenza']), str(r['Quotazione']), str(r['Quotazione_Mantra']), 
            str(r['FVM']), 
            int(r['stat_pv']), float(r['stat_mv']), float(r['stat_fm']),
            int(r['stat_gf']), int(r['stat_gs']), int(r['stat_ass']),
            int(r['stat_amm']), int(r['stat_esp'])
        ))

    conn.commit()
    conn.close()
    print("✅ Database aggiornato e pronto.")