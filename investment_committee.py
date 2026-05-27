import autogen
import json
import os

# ---------------------------------------------------------------------------
# LLM Configuration — LM Studio only (all agents)
# ---------------------------------------------------------------------------

lm_studio_config = [
    {
        "model": "meta-llama-3-8b-instruct",
        "api_key": "lm-studio",
        "base_url": "http://localhost:1234/v1",
        "temperature": 0.7,
    }
]

llm_cfg = {"config_list": lm_studio_config}

# ---------------------------------------------------------------------------
# Investment Committee Agents
# ---------------------------------------------------------------------------

portfolio_manager = autogen.AssistantAgent(
    name="portfolio_manager",
    llm_config=llm_cfg,
    system_message=(
        "You are the Head Portfolio Manager. You speak LAST. Review the JSON "
        "data and the arguments from Alpha, Risk, and Macro. You must make a "
        "final, authoritative decision. Output a 'FINAL APPROVED TRADES' list "
        "containing the exact stock tickers we will execute today, the direction "
        "(LONG or SHORT), and a 1-sentence justification. Do not ask the team "
        "for further thoughts."
    ),
)

alpha_synthesizer = autogen.AssistantAgent(
    name="alpha_synthesizer",
    llm_config=llm_cfg,
    system_message=(
        "You are the aggressive Alpha Synthesizer. Based STRICTLY on the "
        "provided JSON data, identify the best Long and Short opportunities. "
        "Pitch the top 3 most compelling trades based on their Conviction "
        "Scores and Algorithm Signals. Do not hallucinate or invent data."
    ),
)

chief_risk_officer = autogen.AssistantAgent(
    name="chief_risk_officer",
    llm_config=llm_cfg,
    system_message=(
        "You are the Chief Risk Officer. Review the Alpha Synthesizer's "
        "proposed trades and the JSON data. Argue against trades that show "
        "sector concentration (e.g., too many financials or tech stocks). "
        "Point out the risks of 144 Delay signals. Do not hallucinate or "
        "invent data. Keep it concise."
    ),
)

macro_strategist = autogen.AssistantAgent(
    name="macro_strategist",
    llm_config=llm_cfg,
    system_message=(
        "You are the Macro Strategist. Look strictly at the 'macro_regime' "
        "key in the JSON. If it says 'NORMAL', assume a healthy, balanced "
        "market and do NOT hallucinate an inverted yield curve or recession. "
        "Analyze how the given macro regime impacts the proposed trades. "
        "Keep it concise."
    ),
)

# ---------------------------------------------------------------------------
# User Proxy (pipeline trigger — no human input, no code execution)
# ---------------------------------------------------------------------------

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    code_execution_config=False,
    human_input_mode="NEVER",
)

# ---------------------------------------------------------------------------
# Group Chat Setup
# ---------------------------------------------------------------------------

groupchat = autogen.GroupChat(
    agents=[user_proxy, alpha_synthesizer, chief_risk_officer,
            macro_strategist, portfolio_manager],
    messages=[],
    max_round=6,
    speaker_selection_method="round_robin",
)

manager = autogen.GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_cfg,
)

# ---------------------------------------------------------------------------
# Execution Trigger — reads live signals from LangGraph engine output
# ---------------------------------------------------------------------------

file_path = "signals_output.json"

if os.path.exists(file_path):
    with open(file_path, "r") as f:
        live_signals = json.load(f)
    signal_payload = json.dumps(live_signals, indent=2)
else:
    signal_payload = "ERROR: signals_output.json not found. Run main.py first."
    print(signal_payload)
    exit()

user_proxy.initiate_chat(
    manager,
    message=(
        f"Team, the LangGraph extraction engine has finished its daily run. "
        f"Analyze the following live quantitative ledger outputs and debate the positions:\n\n"
        f"{signal_payload}"
    ),
)
