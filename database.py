# database.py
import streamlit as st
import hashlib
import json
import psycopg2
from config import create_defaults

# Manejo robusto de la conexión para evitar crashes si falta libpq-dev
try:
    import psycopg2
except ImportError:
    psycopg2 = None

def get_db_connection():
    if not psycopg2:
        st.error("⚠️ Error: psycopg2 no instalado.")
        return None
    try:
        conn = psycopg2.connect(
            host=st.secrets["supabase"]["host"],
            user=st.secrets["supabase"]["user"],
            password=st.secrets["supabase"]["password"],
            dbname=st.secrets["supabase"]["dbname"],
            port=st.secrets["supabase"]["port"],
            connect_timeout=5
        )
        return conn
    except Exception as e:
        st.error(f"🚨 Error de conexión DB: {e}")
        return None

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password):
    conn = get_db_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute('INSERT INTO users(username, password, is_premium) VALUES (%s, %s, %s)',
                    (username, make_hashes(password), 0))
        defaults = json.dumps(create_defaults())
        cur.execute('INSERT INTO user_data(username, data) VALUES (%s, %s)', (username, defaults))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        return False
    except Exception as e:
        st.error(e)
        conn.close()
        return False

def login_user(username, password):
    conn = get_db_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s',
                    (username, make_hashes(password)))
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except:
        return None

def get_user_data(username):
    conn = get_db_connection()
    if not conn: return create_defaults()
    try:
        cur = conn.cursor()
        cur.execute('SELECT data FROM user_data WHERE username = %s', (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return json.loads(result[0])
    except:
        pass
    return create_defaults()

def save_user_data(username, data):
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()
        json_data = json.dumps(data)
        cur.execute('UPDATE user_data SET data = %s WHERE username = %s', (json_data, username))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Error al guardar: {e}")
