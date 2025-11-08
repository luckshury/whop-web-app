"""
Authentication helpers for Whop integration using the official whop-sdk.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Optional, Tuple

import streamlit as st
from whop_sdk import Whop
from whop_sdk.types import UserCheckAccessResponse


def _get_env(key: str, default: str = "") -> str:
    """Fetch environment variables, checking Streamlit secrets first."""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


def _is_dev_mode() -> bool:
    return _get_env("DEV_MODE", "false").lower() == "true"


def _is_iframe_context() -> bool:
    params = st.query_params
    return params.get("whop_iframe") == "true" or params.get("experience_id") is not None


@lru_cache(maxsize=1)
def _get_whop_client() -> Optional[Whop]:
    """Initialise Whop SDK client (cached)."""
    app_id = _get_env("WHOP_APP_ID") or _get_env("NEXT_PUBLIC_WHOP_APP_ID")
    api_key = _get_env("WHOP_API_KEY")
    if not app_id or not api_key:
        return None
    return Whop(app_id=app_id, api_key=api_key)


def _validate_access(
    user_id: str,
    experience_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Check if a user has access to an experience/company."""
    client = _get_whop_client()
    if client is None:
        return False, None, (
            "Whop credentials missing. Set WHOP_API_KEY and WHOP_APP_ID / "
            "NEXT_PUBLIC_WHOP_APP_ID."
        )

    resource_id = experience_id or company_id
    if not resource_id:
        return False, None, "No resource id provided for Whop access check."

    try:
        resp: UserCheckAccessResponse = client.users.check_access(
        resource_id, id=user_id
        )
        if resp.has_access and resp.access_level != "no_access":
            user_data = {
                "user_id": user_id,
                "resource_id": resource_id,
                "access_level": resp.access_level,
                "mode": "iframe" if _is_iframe_context() else "external",
            }
            return True, user_data, None

        return False, None, "You do not have an active membership for this experience."
    except Exception as exc:
        return False, None, f"Whop API error: {exc}"


def require_whop_auth() -> None:
    """
    Enforce Whop authentication. Should be called at the top of the Streamlit app.
    """
    if _is_dev_mode():
        st.session_state["authenticated_user"] = {
            "user_id": "dev_user",
            "resource_id": "dev_experience",
            "access_level": "admin",
            "mode": "development",
        }
        return

    client = _get_whop_client()
    if client is None:
        st.error(
            "Whop authentication is not configured. "
            "Set WHOP_API_KEY and WHOP_APP_ID (or NEXT_PUBLIC_WHOP_APP_ID)."
        )
        st.stop()

    params = st.query_params
    experience_id = params.get("experience_id")
    company_id = params.get("company_id")
    user_id = params.get("user_id") or params.get("userId")

    # Use cached session if present
    if st.session_state.get("whop_authenticated"):
        return

    if user_id and (experience_id or company_id):
        ok, user_data, error_msg = _validate_access(
            user_id, experience_id=experience_id, company_id=company_id
        )
        if ok and user_data:
            st.session_state["whop_authenticated"] = True
            st.session_state["authenticated_user"] = user_data
            return

        # Show access denied screen inside iframe
        st.error(error_msg or "Unable to verify Whop access.")
        _render_paywall(experience_id)
        st.stop()

    if _is_iframe_context():
        st.info("Waiting for Whop to provide user context...")
        st.stop()

    # External access - show paywall with manual verification option
    _render_paywall(experience_id)
    st.stop()


def _render_paywall(prefill_experience: Optional[str]) -> None:
    """Render subscription prompt with manual verification."""
    st.title("🔒 Subscription Required")
    st.markdown(
        "This analysis suite is available exclusively to Whop members. "
        "Install the Whop app and make sure you have an active membership."
    )

    checkout_url = _get_env("WHOP_CHECKOUT_URL", "https://whop.com")
    st.markdown(
        f"""
<div style="text-align:center;margin:1.5rem 0;">
  <a href="{checkout_url}" target="_blank">
    <button style="
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #fff;
      font-size: 1.1rem;
      padding: 0.9rem 2.8rem;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      box-shadow: 0 4px 15px rgba(118, 75, 162, 0.35);
    ">
      🚀 View Membership Options
    </button>
  </a>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("Already a member?")
    st.caption("Enter your Whop user ID and experience ID to validate access.")

    with st.form("manual_whop_validation"):
        user_id_input = st.text_input(
            "Whop User ID",
            value=st.session_state.get("manual_whop_user", ""),
            placeholder="user_xxxxxxxxxxxxx",
        )
        experience_input = st.text_input(
            "Experience ID",
            value=prefill_experience or st.session_state.get("manual_whop_exp", ""),
            placeholder="exp_xxxxxxxxxxxxx",
        )
        submitted = st.form_submit_button("Validate Access")

    if submitted:
        st.session_state["manual_whop_user"] = user_id_input
        st.session_state["manual_whop_exp"] = experience_input
        if user_id_input and experience_input:
            with st.spinner("Verifying membership…"):
                ok, user_data, error_msg = _validate_access(
                    user_id_input, experience_id=experience_input
                )
            if ok and user_data:
                st.session_state["whop_authenticated"] = True
                st.session_state["authenticated_user"] = user_data
                st.success("Access verified! Reloading…")
                st.rerun()
            else:
                st.error(error_msg or "Unable to verify membership.")
        else:
            st.warning("Please provide both your Whop user ID and experience ID.")

