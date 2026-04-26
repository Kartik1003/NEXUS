"""Deterministic Department Classifier — Rule-based logic (No LLM)."""

FINANCE_OVERRIDES = [
    "cash flow", "cashflow", "bank balance", "invoice", "invoices",
    "accounts receivable", "accounts payable", "burn rate",
    "balance sheet", "p&l", "revenue forecast", "budget", "financial",
    "saas subscription", "subscription cost", "liquidity", "runway"
]

KEYWORD_MAP = {
    "Finance": [
        "cash flow", "cashflow", "revenue", "invoice", "invoices",
        "bank balance", "budget", "forecast", "financial", "profit",
        "loss", "expense", "expenses", "roi", "balance sheet",
        "accounting", "tax", "payroll cost", "payroll analysis",
        "saas subscription", "subscription cost", "payment", "payments",
        "accounts receivable", "accounts payable", "p&l", "burn rate",
        "runway", "liquidity", "working capital"
    ],
    "HR": [
        "hire", "hiring", "recruit", "recruitment", "resume", "interview",
        "onboarding", "employee handbook", "policy", "policies", "compliance",
        "performance review", "employee satisfaction", "headcount",
        # Policy procedure & toolkit signals
        "toolkit", "toolkits", "procedure", "procedures", "disciplinary",
        "grievance", "step-by-step", "managers to follow", "leave request",
        "formal process", "sop", "standard operating procedure",
        "hr workflow", "people process", "hr process",
    ],
    "IT": [
        "code", "bug", "deploy", "api", "server", "database",
        "frontend", "backend", "security", "infrastructure", "debug",
        "software", "hardware", "network", "system",
        "website", "web app", "web application", "build", "develop",
        "responsive", "ui", "ux", "landing page", "portal",
        "dashboard", "mobile app", "platform", "application", "feature",
        "endpoint", "microservice", "devops", "cloud", "saas product",
        # Login/auth pages — must NOT fall to HR even if "employee" is in the task
        "login page", "login form", "sign in page", "registration page",
        "employee portal", "staff portal", "employee details form",
        "employee management system",
    ],
    "Marketing": [
        "campaign", "brand", "seo", "content", "social media",
        "email marketing", "ad", "advertisement", "conversion",
        "lead generation", "marketing", "promotion"
    ],
    "Customer Service": [
        "customer", "support", "ticket", "complaint", "refund",
        "escalation", "satisfaction", "helpdesk", "churn"
    ],
    "Operations": [
        "process", "workflow", "logistics", "supply chain",
        "operations", "efficiency", "project plan", "vendor",
        "roadmap", "milestone", "timeline", "sprint", "backlog"
    ]

}


def classify_department(task: str) -> str:
    task_lower = task.lower()

    # Hard overrides — unambiguous Finance signals take absolute priority
    for signal in FINANCE_OVERRIDES:
        if signal in task_lower:
            return "Finance"

    # Weighted keyword scoring
    scores = {dept: 0 for dept in KEYWORD_MAP}
    for dept, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in task_lower:
                scores[dept] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Operations"