import os
import json
import time
from typing import TypedDict, Annotated

from dotenv import load_dotenv

# ============================================================
# LOAD .ENV
# ============================================================

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# ============================================================
# LANGCHAIN / LANGGRAPH
# ============================================================

from langchain_core.messages import (
    BaseMessage,
    HumanMessage
)

from langchain_google_genai import (
    ChatGoogleGenerativeAI
)

from langgraph.graph import (
    StateGraph,
    START,
    END
)

from langgraph.graph.message import (
    add_messages
)

from langgraph.checkpoint.memory import (
    InMemorySaver
)


# ============================================================
# LOCAL TOOLS
# ============================================================

from tools import (
    search_knowledge_base,
    search_tickets,
    get_all_policies,
    get_all_tickets,
)


# ============================================================
# GEMINI MODEL ORDER
# ============================================================

MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
]


# ============================================================
# MODELS THAT HAVE ALREADY FAILED
# ============================================================

unavailable_models = set()


# ============================================================
# CHECK API KEY
# ============================================================

if not GOOGLE_API_KEY:

    print(
        "\nWARNING: GOOGLE_API_KEY was not found.\n"
        "Check your .env file.\n"
    )


# ============================================================
# NORMALIZE GEMINI RESPONSE
#
# Gemini responses can be:
#
# "text"
#
# OR:
#
# [
#     {"type": "text", "text": "..."}
# ]
#
# This function handles both.
# ============================================================

def get_response_text(response):

    content = response.content


    # --------------------------------------------------------
    # CASE 1: NORMAL STRING
    # --------------------------------------------------------

    if isinstance(content, str):

        return content.strip()


    # --------------------------------------------------------
    # CASE 2: LIST
    # --------------------------------------------------------

    if isinstance(content, list):

        parts = []


        for item in content:

            # -----------------------------------------------
            # Plain string
            # -----------------------------------------------

            if isinstance(item, str):

                parts.append(item)


            # -----------------------------------------------
            # Dictionary
            # -----------------------------------------------

            elif isinstance(item, dict):

                if "text" in item:

                    parts.append(
                        str(item["text"])
                    )


        return "\n".join(
            parts
        ).strip()


    # --------------------------------------------------------
    # CASE 3: OTHER
    # --------------------------------------------------------

    return str(
        content
    ).strip()


# ============================================================
# GEMINI INVOCATION WITH FALLBACK
# ============================================================

def invoke_with_fallback(
    prompt,
    preferred_model=None
):

    if not GOOGLE_API_KEY:

        raise RuntimeError(
            "GOOGLE_API_KEY is missing. "
            "Add your Gemini API key to .env."
        )


    # ========================================================
    # CREATE MODEL ORDER
    # ========================================================

    if preferred_model:

        model_order = [
            preferred_model
        ]

        for model in MODELS:

            if model != preferred_model:

                model_order.append(model)

    else:

        model_order = MODELS.copy()


    # ========================================================
    # REMOVE MODELS ALREADY MARKED UNAVAILABLE
    # ========================================================

    available_models = [

        model

        for model in model_order

        if model not in unavailable_models

    ]


    # If all models are unavailable,
    # make one fresh attempt.

    if not available_models:

        available_models = model_order


    # ========================================================
    # TRY MODELS
    # ========================================================

    last_error = None


    for model_name in available_models:

        try:

            print(
                f"\nTrying model: {model_name}"
            )


            llm = ChatGoogleGenerativeAI(

                model=model_name,

                temperature=0,

                api_key=GOOGLE_API_KEY,

            )


            response = llm.invoke(
                prompt
            )


            print(
                f"Model used: {model_name}"
            )


            return response, model_name


        except Exception as e:

            last_error = e

            error_message = str(e)

            error_lower = (
                error_message.lower()
            )


            print(
                f"Model failed: {model_name}"
            )

            print(
                f"Reason: {error_message}"
            )


            # =================================================
            # RATE LIMIT / QUOTA
            # =================================================

            quota_error = (

                "429" in error_message

                or

                "resource_exhausted"
                in error_lower

                or

                "quota"
                in error_lower

                or

                "rate limit"
                in error_lower

            )


            # =================================================
            # TEMPORARY SERVICE ERROR
            # =================================================

            temporary_error = (

                "503" in error_message

                or

                "unavailable"
                in error_lower

                or

                "timeout"
                in error_lower

                or

                "deadline"
                in error_lower

            )


            # =================================================
            # MODEL NOT FOUND
            # =================================================

            model_error = (

                "model_not_found"
                in error_lower

                or

                "not_found"
                in error_lower

            )


            # =================================================
            # FALLBACK
            # =================================================

            if (
                quota_error
                or temporary_error
                or model_error
            ):

                unavailable_models.add(
                    model_name
                )


                print(
                    f"Marking {model_name} "
                    f"as temporarily unavailable."
                )


                print(
                    "Switching to next Gemini model..."
                )


                time.sleep(0.5)

                continue


            # =================================================
            # OTHER ERROR
            # =================================================

            print(
                "Unexpected model error."
            )

            print(
                "Trying fallback model..."
            )


            time.sleep(0.5)


    # ========================================================
    # ALL MODELS FAILED
    # ========================================================

    raise RuntimeError(
        "All Gemini models failed. "
        f"Last error: {last_error}"
    )


# ============================================================
# AGENT STATE
# ============================================================

class AgentState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]

    knowledge: list

    tickets: list

    decision: str

    response: str

    model_used: str


# ============================================================
# GET LATEST USER MESSAGE
# ============================================================

def get_latest_user_message(state):

    messages = state.get(
        "messages",
        []
    )


    for message in reversed(
        messages
    ):

        if isinstance(
            message,
            HumanMessage
        ):

            return message.content


    return ""


# ============================================================
# NODE 1
# POLICY RETRIEVAL
# ============================================================

def retrieve_knowledge(state):

    user_request = (
        get_latest_user_message(
            state
        )
    )


    policies = get_all_policies()


    policy_text = "\n\n".join(

        [

            f"""
POLICY ID: {policy['id']}
TITLE: {policy['title']}
POLICY: {policy['policy']}
"""

            for policy in policies

        ]

    )


    prompt = f"""
You are the policy retrieval component of
Veridian Corp's Internal IT Support Agent.

Identify ONLY the policies relevant to the
employee's current request.

Use ONLY the supplied Veridian Corp policies.

Do not invent policies.
Do not modify policy rules.

EMPLOYEE REQUEST:

{user_request}


AVAILABLE POLICIES:

{policy_text}


Return ONLY valid JSON.

Use exactly:

{{
    "relevant_policy_ids": ["KB-XX"]
}}

If no policy is relevant:

{{
    "relevant_policy_ids": []
}}
"""


    try:

        result, model_used = (
            invoke_with_fallback(
                prompt,
                state.get("model_used")
            )
        )


        # IMPORTANT:
        # Do NOT use result.content.strip()
        # Gemini 3.x can return a list.

        content = get_response_text(
            result
        )


        # Remove markdown JSON fences

        content = content.replace(
            "```json",
            ""
        )

        content = content.replace(
            "```",
            ""
        )

        content = content.strip()


        parsed = json.loads(
            content
        )


        selected_ids = parsed.get(
            "relevant_policy_ids",
            []
        )


        selected_policies = [

            policy

            for policy in policies

            if policy["id"]
            in selected_ids

        ]


        print(
            "\nPOLICY RETRIEVAL"
        )

        print(
            f"Model: {model_used}"
        )


        for policy in selected_policies:

            print(
                f"{policy['id']}: "
                f"{policy['title']}"
            )


        # ----------------------------------------------------
        # KEYWORD FALLBACK
        # ----------------------------------------------------

        if not selected_policies:

            selected_policies = (
                search_knowledge_base(
                    user_request
                )
            )


        return {

            "knowledge":
                selected_policies,

            "model_used":
                model_used

        }


    except Exception as e:

        print(
            "\nSemantic policy retrieval failed."
        )

        print(e)


        fallback = (
            search_knowledge_base(
                user_request
            )
        )


        return {

            "knowledge":
                fallback

        }


# ============================================================
# NODE 2
# TICKET RETRIEVAL
# ============================================================

def retrieve_tickets(state):

    user_request = (
        get_latest_user_message(
            state
        )
    )


    tickets = get_all_tickets()


    ticket_text = "\n\n".join(

        [

            f"""
TICKET ID: {ticket['ticket_id']}
ISSUE: {ticket['issue']}
STATUS: {ticket['status']}
"""

            for ticket in tickets

        ]

    )


    prompt = f"""
You are the historical ticket retrieval
component of Veridian Corp's Internal IT
Support Agent.

Compare the employee request with every
historical ticket.

Score every ticket:

0 = unrelated
1 = weak similarity
2 = relevant
3 = highly relevant / strong precedent


EMPLOYEE REQUEST:

{user_request}


TICKETS:

{ticket_text}


Return ONLY valid JSON.

Use exactly:

{{
    "scores": [
        {{
            "ticket_id": "TK-XXXX",
            "score": 0
        }}
    ]
}}

You MUST return a score for EVERY ticket.
"""


    try:

        result, model_used = (
            invoke_with_fallback(
                prompt,
                state.get("model_used")
            )
        )


        # IMPORTANT:
        # Gemini 3.x can return list content.

        content = get_response_text(
            result
        )


        content = content.replace(
            "```json",
            ""
        )

        content = content.replace(
            "```",
            ""
        )

        content = content.strip()


        parsed = json.loads(
            content
        )


        scores = parsed.get(
            "scores",
            []
        )


        score_map = {}


        for item in scores:

            if "ticket_id" in item:

                score_map[
                    item["ticket_id"]
                ] = item.get(
                    "score",
                    0
                )


        print(
            "\nTICKET RETRIEVAL SCORES"
        )

        print(
            f"Model: {model_used}"
        )


        for ticket in tickets:

            ticket_id = (
                ticket["ticket_id"]
            )


            score = score_map.get(
                ticket_id,
                0
            )


            print(
                f"{ticket_id}: {score}"
            )


        selected_tickets = [

            ticket

            for ticket in tickets

            if score_map.get(
                ticket["ticket_id"],
                0
            ) >= 2

        ]


        print(
            "\nSELECTED TICKETS"
        )


        for ticket in selected_tickets:

            print(
                f"{ticket['ticket_id']}: "
                f"{ticket['issue']}"
            )


        # ----------------------------------------------------
        # KEYWORD FALLBACK
        # ----------------------------------------------------

        if not selected_tickets:

            selected_tickets = (
                search_tickets(
                    user_request
                )
            )


        return {

            "tickets":
                selected_tickets,

            "model_used":
                model_used

        }


    except Exception as e:

        print(
            "\nSemantic ticket retrieval failed."
        )

        print(e)


        fallback = (
            search_tickets(
                user_request
            )
        )


        return {

            "tickets":
                fallback

        }


# ============================================================
# NODE 3
# DECISION MAKER
# ============================================================

def make_decision(state):

    user_request = (
        get_latest_user_message(
            state
        )
    )


    knowledge = state.get(
        "knowledge",
        []
    )


    tickets = state.get(
        "tickets",
        []
    )


    messages = state.get(
        "messages",
        []
    )


    # ========================================================
    # CONVERSATION HISTORY
    # ========================================================

    conversation_history = "\n".join(

        [

            f"{message.type.upper()}: "
            f"{message.content}"

            for message in messages[-8:]

        ]

    )


    # ========================================================
    # POLICY CONTEXT
    # ========================================================

    if knowledge:

        policy_context = "\n\n".join(

            [

                f"""
POLICY ID: {item['id']}
TITLE: {item['title']}
POLICY: {item['policy']}
"""

                for item in knowledge

            ]

        )

    else:

        policy_context = (
            "No relevant policy was found."
        )


    # ========================================================
    # TICKET CONTEXT
    # ========================================================

    if tickets:

        ticket_context = "\n\n".join(

            [

                f"""
TICKET ID: {ticket['ticket_id']}
ISSUE: {ticket['issue']}
STATUS: {ticket['status']}
"""

                for ticket in tickets

            ]

        )

    else:

        ticket_context = (
            "No relevant historical ticket "
            "was found."
        )


    # ========================================================
    # DECISION PROMPT
    # ========================================================

    prompt = f"""
You are the decision-making component of
Veridian Corp's Internal IT Support Agent.

Determine the correct next action for the
employee's IT request.

You MUST follow the supplied company policies.

You MUST NOT invent:
- company policies
- approvals
- procedures
- technical facts
- employee information


==================================================
ALLOWED DECISIONS
==================================================

RESOLVE

CLARIFY

ROUTE_TO_IT

ROUTE_TO_FINANCE

ESCALATE_TO_SECURITY

WAIT_FOR_APPROVAL


==================================================
DECISION RULES
==================================================

RESOLVE:
The policy clearly explains what the employee
should do and no approval or missing information
is required.

CLARIFY:
Important information is missing.

ROUTE_TO_IT:
The issue requires IT intervention.

ROUTE_TO_FINANCE:
The request belongs to Finance or requires
Finance processing.

ESCALATE_TO_SECURITY:
The request involves phishing, malware,
unauthorized access, or a security incident.

WAIT_FOR_APPROVAL:
The action requires manager, Finance,
Security, or another approval.


==================================================
CONVERSATION HISTORY
==================================================

{conversation_history}


==================================================
CURRENT EMPLOYEE REQUEST
==================================================

{user_request}


==================================================
RELEVANT COMPANY POLICIES
==================================================

{policy_context}


==================================================
RELEVANT HISTORICAL TICKETS
==================================================

{ticket_context}


==================================================
OUTPUT FORMAT
==================================================

Return EXACTLY:

CATEGORY: <short category>

DECISION: <one allowed decision>

REASON: <brief explanation based only on supplied data>

NEXT ACTION: <specific next step>

RELEVANT POLICIES: <policy IDs or NONE>

RELEVANT TICKETS: <ticket IDs or NONE>

MISSING INFORMATION: <missing information or NONE>

RESPONSE: <employee-facing response>

Do not add markdown.
Do not add extra sections.
"""


    try:

        result, model_used = (
            invoke_with_fallback(
                prompt,
                state.get("model_used")
            )
        )


        # IMPORTANT:
        # Handles both string and list content.

        decision_text = (
            get_response_text(
                result
            )
        )


        # ====================================================
        # FORCE RETRIEVED TICKETS INTO OUTPUT
        # ====================================================

        if tickets:

            ticket_ids = ", ".join(

                [

                    ticket["ticket_id"]

                    for ticket in tickets

                ]

            )


            lines = (
                decision_text.splitlines()
            )


            new_lines = []

            ticket_line_found = False


            for line in lines:

                if line.upper().startswith(
                    "RELEVANT TICKETS:"
                ):

                    new_lines.append(
                        "RELEVANT TICKETS: "
                        + ticket_ids
                    )

                    ticket_line_found = True

                else:

                    new_lines.append(
                        line
                    )


            if not ticket_line_found:

                new_lines.append(
                    "RELEVANT TICKETS: "
                    + ticket_ids
                )


            decision_text = "\n".join(
                new_lines
            )


        # ====================================================
        # EXTRACT EMPLOYEE RESPONSE
        # ====================================================

        employee_response = ""


        for line in (
            decision_text.splitlines()
        ):

            if line.upper().startswith(
                "RESPONSE:"
            ):

                employee_response = (
                    line.split(
                        ":",
                        1
                    )[1].strip()
                )

                break


        if not employee_response:

            employee_response = (
                decision_text
            )


        print(
            "\nDECISION MODEL"
        )

        print(
            f"Model: {model_used}"
        )


        return {

            "decision":
                decision_text,

            "response":
                employee_response,

            "model_used":
                model_used

        }


    except Exception as e:

        print(
            "\nDecision generation failed."
        )

        print(e)


        error_response = (
            "The Veridian IT Agent could not "
            "complete this request because the "
            "AI service is currently unavailable. "
            "Please try again shortly."
        )


        return {

            "decision":
                "CATEGORY: SYSTEM\n"
                "DECISION: ROUTE_TO_IT\n"
                "REASON: AI model service unavailable.\n"
                "NEXT ACTION: Retry the request shortly.\n"
                "RELEVANT POLICIES: NONE\n"
                "RELEVANT TICKETS: NONE\n"
                "MISSING INFORMATION: NONE\n"
                f"RESPONSE: {error_response}",

            "response":
                error_response

        }


# ============================================================
# BUILD LANGGRAPH
# ============================================================

builder = StateGraph(
    AgentState
)


builder.add_node(
    "retrieve_knowledge",
    retrieve_knowledge
)


builder.add_node(
    "retrieve_tickets",
    retrieve_tickets
)


builder.add_node(
    "make_decision",
    make_decision
)


builder.add_edge(
    START,
    "retrieve_knowledge"
)


builder.add_edge(
    "retrieve_knowledge",
    "retrieve_tickets"
)


builder.add_edge(
    "retrieve_tickets",
    "make_decision"
)


builder.add_edge(
    "make_decision",
    END
)


# ============================================================
# MEMORY
# ============================================================

memory = InMemorySaver()


# ============================================================
# COMPILE
# ============================================================

agent = builder.compile(
    checkpointer=memory
)


# ============================================================
# RUN AGENT
# ============================================================

def run_agent(
    user_request: str,
    thread_id: str = "default"
):

    config = {

        "configurable": {

            "thread_id":
                thread_id

        }

    }


    result = agent.invoke(

        {
            "messages": [

                HumanMessage(
                    content=user_request
                )

            ],

            "knowledge": [],

            "tickets": [],

            "decision": "",

            "response": "",

            "model_used": ""

        },

        config=config

    )


    return {

        "response":
            result.get(
                "response",
                ""
            ),

        "decision":
            result.get(
                "decision",
                ""
            ),

        "knowledge":
            result.get(
                "knowledge",
                []
            ),

        "tickets":
            result.get(
                "tickets",
                []
            ),

        "model_used":
            result.get(
                "model_used",
                ""
            )

    }


# ============================================================
# CLI TEST
#
# This ONLY runs if you execute:
#
#     uv run python agent.py
#
# It will NOT run when Streamlit starts app.py.
# ============================================================

if __name__ == "__main__":

    print(
        "\n================================"
    )

    print(
        "       VERIDIAN IT AGENT"
    )

    print(
        "================================\n"
    )


    result = run_agent(

        "Requesting approval to install a "
        "browser extension for productivity tracking.",

        thread_id="test-user"

    )


    print(
        "\nFINAL RESULT\n"
    )


    print(
        result["decision"]
    )


    print(
        "\nMODEL USED:"
    )


    print(
        result["model_used"]
    )


    print(
        "\n\nMEMORY TEST\n"
    )


    result2 = run_agent(

        "What policy applies to this?",

        thread_id="test-user"

    )


    print(
        result2["decision"]
    )


    print(
        "\nMODEL USED:"
    )


    print(
        result2["model_used"]
    )