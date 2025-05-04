from supabase import create_client, Client
import streamlit as st

def supabase_client():
    try:
        return create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"]
        )
    except Exception as e:
        st.error(f"Erro na conexão com Supabase: {str(e)}")
        return None
