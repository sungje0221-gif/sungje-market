import secrets
import time
import streamlit as st

from engine.schwab import (
    SchwabError,
    authorization_url,
    clear_cache,
    connection_status,
    delete_token,
    exchange_code,
)


def render():
    st.title("Charles Schwab Connection")
    st.caption("OAuth 정보는 GitHub가 아니라 Streamlit Secrets에 보관합니다.")

    status = connection_status()
    c1, c2, c3 = st.columns(3)
    c1.metric("Credentials", "READY" if status["configured"] else "NOT SET")
    c2.metric("Connection", "CONNECTED" if status["connected"] else "DISCONNECTED")
    c3.metric("Refresh Token", "YES" if status["has_refresh_token"] else "NO")

    with st.expander("1. Streamlit Secrets 설정", expanded=not status["configured"]):
        st.code(
            "[schwab]\n"
            'client_id = "YOUR_APP_KEY"\n'
            'client_secret = "YOUR_APP_SECRET"\n'
            'redirect_uri = "YOUR_REGISTERED_CALLBACK_URL"',
            language="toml",
        )
        st.write("Streamlit Cloud의 App settings → Secrets에 입력합니다.")

    if not status["configured"]:
        st.warning("먼저 Schwab 개발자 앱 정보와 Redirect URI를 등록해야 합니다.")
        return

    if "schwab_oauth_state" not in st.session_state:
        st.session_state.schwab_oauth_state = secrets.token_urlsafe(24)

    try:
        url = authorization_url(st.session_state.schwab_oauth_state)
        st.link_button("Schwab 로그인 및 승인", url, type="primary", use_container_width=True)
    except SchwabError as exc:
        st.error(str(exc))
        return

    callback = st.text_area(
        "Callback URL 또는 authorization code",
        height=110,
        placeholder="https://your-callback-url/?code=...",
    )

    if st.button("연결 완료", type="primary", disabled=not callback.strip()):
        try:
            exchange_code(callback)
            clear_cache()
            st.success("Charles Schwab 계좌 연결이 완료되었습니다.")
            time.sleep(1)
            st.rerun()
        except SchwabError as exc:
            st.error(str(exc))

    if status["connected"]:
        st.divider()
        if st.button("Schwab 연결 해제"):
            delete_token()
            clear_cache()
            st.success("저장된 OAuth 토큰을 삭제했습니다.")
            st.rerun()
