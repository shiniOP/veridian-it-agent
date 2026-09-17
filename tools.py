import json


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def search_knowledge_base(query: str):
    """
    Basic fallback keyword search over the supplied
    Veridian Corp knowledge base.
    """

    knowledge_base = load_json("data/knowledge_base.json")

    query_words = query.lower().split()

    results = []

    for item in knowledge_base:

        text = (
            item["title"] + " " +
            item["policy"]
        ).lower()

        score = sum(
            1
            for word in query_words
            if word in text
        )

        if score > 0:
            results.append((score, item))

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        item
        for score, item in results[:5]
    ]


def search_tickets(query: str):
    """
    Search the supplied Veridian Corp ticket history.
    """

    tickets = load_json("data/tickets.json")

    query_words = query.lower().split()

    results = []

    for ticket in tickets:

        text = (
            ticket["issue"] + " " +
            ticket["status"]
        ).lower()

        score = sum(
            1
            for word in query_words
            if word in text
        )

        if score > 0:
            results.append((score, ticket))

    results.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return [
        ticket
        for score, ticket in results[:5]
    ]


def get_employee_request(request_id: str):
    """
    Retrieve one of the assignment's employee requests.
    """

    requests = load_json("data/requests.json")

    for request in requests:

        if request["request_id"].upper() == request_id.upper():
            return request

    return None


def get_all_policies():
    """
    Return all policies from the supplied data pack.

    Used by the semantic policy selector.
    """

    return load_json("data/knowledge_base.json")


def get_all_tickets():
    """
    Return all tickets from the supplied data pack.
    """

    return load_json("data/tickets.json")