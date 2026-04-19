"""Static config data for the job tool.

This file keeps the long constant lists and score-tuning dictionaries out of
`main.py` so the entrypoint stays easier to read.
"""

MAX_RESULTS_PER_TRACK = {
    "soc_analyst": 15,
    "cyber_analyst": 15,
    "it_bridge": 15,
}

OVERFLOW_RESULTS_PER_TRACK = {
    "soc_analyst": 8,
    "cyber_analyst": 8,
    "it_bridge": 8,
}

STRETCH_RESULTS_PER_TRACK = {
    "soc_analyst": 6,
    "cyber_analyst": 6,
    "it_bridge": 0,
}

VOLUME_RESULTS_PER_TRACK = {
    "soc_analyst": 20,
    "cyber_analyst": 20,
    "it_bridge": 20,
}

INTERNSHIP_RESULTS_PER_TRACK = {
    "soc_analyst": 8,
    "cyber_analyst": 8,
    "it_bridge": 8,
}

REQUEST_DELAY = 0.25
MIN_FINAL_SCORE = 55
APPLY_THRESHOLD = 75

LOCATION_MODE_LABELS = {
    "nyc_strict": "New York strict",
    "east_coast": "East Coast",
    "us_remote": "US remote",
}

RESULT_FILE_EXTENSIONS = (".csv", ".txt", ".html", ".md")

NY_LOCATION_TERMS = [
    "new york",
    "nyc",
    "manhattan",
    "brooklyn",
    "queens",
    "bronx",
    "long island city",
    "long island",
    "nassau",
    "suffolk",
    "westchester",
    "white plains",
    "yonkers",
    "melville",
    "hicksville",
    "farmingdale",
    "hauppauge",
]

REMOTE_LOCATION_TERMS = [
    "remote",
    "work from home",
]

EAST_COAST_LOCATION_TERMS = [
    "boston",
    "massachusetts",
    "washington, dc",
    "district of columbia",
    "maryland",
    "virginia",
    "new jersey",
    "connecticut",
    "pennsylvania",
    "philadelphia",
]

US_WIDE_LOCATION_TERMS = [
    "united states",
    "usa",
    "united states of america",
    "usa - update location",
]

NON_TARGET_REMOTE_TERMS = [
    "australia",
    "brazil",
    "canada",
    "emea",
    "europe",
    "india",
    "korea",
    "london",
    "serbia",
    "singapore",
    "tokyo",
    "united kingdom",
]

UGLY_ENTRY_TAGS = {
    "msp",
    "mssp",
    "it-services",
    "service-desk",
    "staffing",
    "enterprise",
    "insurance",
    "gov-adjacent",
    "healthcare",
    "local-ny",
}

PRESTIGE_HEAVY_TAGS = {
    "prestige",
    "brand-magnet",
    "consumer",
}

TRACKS = {
    "soc_analyst": {
        "label": "TIER A | SOC / DETECTION / RESPONSE",
        "resume_key": "cyber",
        "skill_profile": "cyber",
        "certs": ["cissp", "cism", "cisa", "security+", "gcih", "oscp"],
        "min_final_score": 62,
    },
    "cyber_analyst": {
        "label": "TIER C | CYBER / IAM / RISK BRIDGE",
        "resume_key": "cyber",
        "skill_profile": "cyber",
        "certs": ["cissp", "cism", "cisa", "security+", "gcih", "oscp"],
        "min_final_score": 60,
    },
    "it_bridge": {
        "label": "TIER B | IT SUPPORT / APPLICATION SUPPORT / IT OPS",
        "resume_key": "it_support",
        "skill_profile": "it_support",
        "certs": ["a+", "network+", "itil", "ccna", "md-102", "jamf 200"],
        "min_final_score": 54,
    },
}

HIDDEN_REQUIREMENT_SIGNALS = [
    (
        "ownership expectations",
        [
            r"\bownership\b",
            r"\bend[- ]to[- ]end\b",
            r"\bautonom(?:ous|ously)\b",
            r"\bindependently\b",
        ],
        6,
    ),
    (
        "ambiguity tolerance",
        [
            r"\bambigu(?:ity|ous)\b",
            r"\bundefined\b",
            r"\bunstructured\b",
        ],
        5,
    ),
    (
        "cross-functional influence",
        [
            r"\bcross-functional\b",
            r"\binfluence(?:\s+\w+){0,3}\s+stakeholders?\b",
            r"\bexecutive stakeholders?\b",
            r"\bsenior stakeholders?\b",
            r"\bpartner with\b",
            r"\balign(?:ment)?\b",
        ],
        5,
    ),
    (
        "initiative-driving",
        [
            r"\bdrive initiatives?\b",
            r"\blead initiatives?\b",
            r"\bown roadmap\b",
            r"\bset strategy\b",
            r"\bdefine strategy\b",
        ],
        6,
    ),
    (
        "scaling depth",
        [
            r"\bscale\b",
            r"\bscaling\b",
            r"\blarge[- ]scale\b",
            r"\bdistributed systems?\b",
            r"\bproduction systems?\b",
            r"\bhigh[- ]throughput\b",
        ],
        6,
    ),
    (
        "mentorship expectations",
        [
            r"\bmentor(?:ing)?\b",
            r"\bcoach(?:ing)?\b",
            r"\bguide others\b",
        ],
        5,
    ),
]

PROJECT_BACKED_TERMS = {
    "cyber": [
        "soc",
        "siem",
        "sentinel",
        "microsoft sentinel",
        "alert triage",
        "incident response",
        "investigation",
        "log analysis",
        "kql",
        "defender",
        "microsoft defender",
        "wireshark",
        "packet analysis",
        "vulnerability",
        "network",
        "powershell",
    ],
    "it_support": [
        "it support",
        "technical support",
        "troubleshooting",
        "windows",
        "network",
    ],
}

EXECUTION_DEPTH_TERMS = {
    "cyber": [
        "design",
        "architect",
        "architecture",
        "build systems",
        "from scratch",
        "production systems",
        "distributed systems",
        "scalable",
        "large-scale",
        "ownership",
        "leadership",
    ],
    "it_support": [
        "escalation management",
        "lead initiatives",
    ],
}

NARRATIVE_SIGNALS = {
    "cyber": {
        "positive": [
            ("soc story", [r"\bsoc\b", r"\bsecurity operations?\b"], 12),
            ("analyst story", [r"\banalyst\b", r"\binvestigat(?:e|or)\b"], 14),
            ("detection and response story", [r"\bdetection\b", r"\bresponse\b", r"\bincident response\b"], 10),
            ("monitoring story", [r"\bsiem\b", r"\bsplunk\b", r"\bsentinel\b", r"\bmonitoring\b"], 8),
            ("triage and logs story", [r"\balert triage\b", r"\blog analysis\b", r"\binvestigation\b"], 8),
            ("entry bridge story", [r"\bassociate\b", r"\bspecialist\b", r"\btechnician\b", r"\bentry(?:[- ]level)?\b"], 8),
        ],
        "negative": [
            ("appsec story mismatch", [r"\bapplication security\b", r"\bproduct security\b"], 22),
            ("cloud or infra security mismatch", [r"\bcloud security\b", r"\binfrastructure security\b", r"\bplatform security\b"], 16),
            ("offensive security mismatch", [r"\boffensive security\b", r"\bred team\b", r"\bpenetration(?: |-)?testing\b"], 14),
            ("devsecops mismatch", [r"\bdevsecops\b", r"\bsecurity architecture\b"], 12),
            ("software engineering mismatch", [r"\bsoftware engineering\b", r"\bbackend\b", r"\bdistributed systems?\b"], 16),
        ],
    },
    "it_support": {
        "positive": [
            ("help desk story", [r"\bhelp ?desk\b", r"\bservice ?desk\b"], 18),
            ("it support story", [r"\bit support\b", r"\btechnical support\b", r"\bend user support\b"], 16),
            ("desktop support story", [r"\bdesktop support\b", r"\bdesktop technician\b"], 16),
            ("troubleshooting story", [r"\btroubleshooting\b", r"\bwindows\b", r"\bticketing\b"], 10),
            ("bridge it ops story", [r"\bit operations?\b", r"\bsystems?(?: administrator| admin)?\b", r"\bsaas administrator\b"], 8),
        ],
        "negative": [
            ("customer support mismatch", [r"\bcustomer support\b", r"\bproduct support\b"], 18),
            ("software or product mismatch", [r"\bsoftware engineer\b", r"\bdeveloper\b", r"\bproduct manager\b"], 18),
            ("sales or solutions mismatch", [r"\bsales\b", r"\bsolutions engineer\b", r"\baccount executive\b"], 14),
        ],
    },
}

EFFORT_SIGNALS = [
    (
        "assessment-heavy process",
        [
            r"\bassessment\b",
            r"\bchallenge\b",
            r"\btake[- ]home\b",
            r"\bcase study\b",
            r"\bpresentation\b",
        ],
        8,
    ),
    (
        "after-hours or on-call load",
        [
            r"\bon[- ]call\b",
            r"\bafter hours\b",
            r"\bweekends?\b",
            r"\b24/?7\b",
        ],
        6,
    ),
]
