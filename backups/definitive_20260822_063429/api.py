from fastapi import FastAPI
import sqlite3

app = FastAPI(title="BIRTH_EDGE Validator API")

@app.get("/v1/tokens/pass")
def get_pass():
    con = sqlite3.connect("data/learning.db")
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT addr, chain, symbol, overall_score, holder_score, 
               initial_liquidity_usd, discovered_at
        FROM learning_results 
        WHERE overall_score > 75 
        ORDER BY overall_score DESC
    """).fetchall()
    con.close()
    return [dict(r) for r in rows]

@app.get("/v1/stats")
def get_stats():
    con = sqlite3.connect("data/learning.db")
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT COUNT(*) as total, AVG(overall_score) as avg_score, MAX(overall_score) as max_score FROM learning_results").fetchone()
    con.close()
    return dict(row)

@app.get("/")
def root():
    return {"alive": True, "service": "BIRTH_EDGE validator"}
