import sqlite3
import pandas as pd
import json
import os

db_path = os.environ.get('DB_PATH', 'python/hopilot/data/normalized_poker.sqlite3')
if not os.path.exists(db_path):
    # Try alternate path if first one fails
    db_path = 'hopilot/data/normalized_poker.sqlite3'
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        exit(1)

conn = sqlite3.connect(db_path)

print('--- Global Table Counts ---')
tables = ['simulations', 'hand_matrices', 'matrix_cells', 'aggregated_metrics', 'game_states', 'players']
for t in tables:
    try:
        count = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f'{t:25}: {count}')
    except Exception as e:
        print(f'{t:25}: Error - {e}')

print('\n--- Latest Simulation Details ---')
res = conn.execute('SELECT id, name, parameters FROM simulations ORDER BY id DESC LIMIT 1').fetchone()
if res:
    sim_id, name, params_json = res
    print(f'ID: {sim_id}')
    print(f'Name: {name}')
    params = json.loads(params_json)
    print(f'Status: {params.get("status")}')
    
    raw_start = params.get("raw_game_state_id_start")
    raw_end = params.get("raw_game_state_id_end")
    
    if raw_start is not None and raw_end is not None:
        gs_count = conn.execute('SELECT COUNT(*) FROM game_states WHERE id BETWEEN ? AND ?', (raw_start, raw_end)).fetchone()[0]
        print(f'GameStates in range [{raw_start}, {raw_end}]: {gs_count}')
        
        matrix_res = conn.execute('SELECT id FROM hand_matrices WHERE simulation_id = ?', (sim_id,)).fetchone()
        if matrix_res:
            m_id = matrix_res[0]
            cell_count = conn.execute('SELECT COUNT(*) FROM matrix_cells WHERE matrix_id = ?', (m_id,)).fetchone()[0]
            print(f'Aggregated Matrix ID: {m_id}')
            print(f'Matrix Cells: {cell_count}')
            
            if cell_count > 0:
                print('\n--- Sample Aggregated Metrics ---')
                metrics_df = pd.read_sql_query('''
                    SELECT mc.hand_combination, am.equity, am.win_probability, am.sample_count 
                    FROM aggregated_metrics am
                    JOIN matrix_cells mc ON am.cell_id = mc.id
                    WHERE mc.matrix_id = ?
                    LIMIT 5
                ''', conn, params=(int(m_id),))
                print(metrics_df.to_string(index=False))
else:
    print("No simulations found in database.")

conn.close()
