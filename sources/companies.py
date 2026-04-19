from shared.utils import normalize_company_id


def derive_compat_group(difficulty, hiring_pattern, industry, tags):
    tags = set(tags)

    if "mssp" in tags:
        return "mssp"
    if hiring_pattern == "hire-heavy":
        return "hire-heavy"
    if industry == "security":
        return "security-focused"
    if difficulty == "realistic":
        return "realistic-tech"
    if difficulty == "stretch":
        return "stretch-tech"
    if difficulty == "lottery":
        return "lottery"
    return "standard"


def with_profile(companies, *, tags, difficulty, hiring_pattern, industry):
    enriched = []
    normalized_tags = sorted({str(tag).strip().lower() for tag in tags if str(tag).strip()})
    compat_group = derive_compat_group(difficulty, hiring_pattern, industry, normalized_tags)

    for company in companies:
        row = dict(company)
        row["id"] = normalize_company_id(row.get("id") or f"{row['type']}:{row['board']}")
        row["tags"] = list(normalized_tags)
        row["difficulty"] = difficulty
        row["hiring_pattern"] = hiring_pattern
        row["industry"] = industry
        row["group"] = compat_group
        enriched.append(row)

    return enriched


MSSP_COMPANIES = with_profile(
    [
        {"name": "GuidePoint Security", "type": "greenhouse", "board": "guidepointsecurity"},
        {"name": "Huntress", "type": "greenhouse", "board": "huntress"},
        {"name": "Blumira", "type": "greenhouse", "board": "blumira"},
        {"name": "Red Canary", "type": "greenhouse", "board": "zscalerredcanary"},
        {"name": "CyberSheath", "type": "greenhouse", "board": "cybersheath"},
        {"name": "Expel", "type": "greenhouse", "board": "expel"},
        {"name": "Bishop Fox", "type": "greenhouse", "board": "bishopfox"},
        {"name": "Legato Security", "type": "greenhouse", "board": "legatosecurity"},
        {"name": "Critical Start", "type": "greenhouse", "board": "criticalstart"},
        {"name": "ReliaQuest", "type": "greenhouse", "board": "reliaquest"},
        {"name": "Critical Insight", "type": "greenhouse", "board": "criticalinsight"},
    ],
    tags=["security", "mssp", "soc", "hire-heavy"],
    difficulty="realistic",
    hiring_pattern="hire-heavy",
    industry="security",
)

SECURITY_FOCUSED_COMPANIES = with_profile(
    [
        {"name": "SecurityScorecard", "type": "greenhouse", "board": "securityscorecard"},
        {"name": "Snyk", "type": "greenhouse", "board": "snyk"},
        {"name": "Okta", "type": "greenhouse", "board": "okta"},
        {"name": "Cloudflare", "type": "greenhouse", "board": "cloudflare"},
        {"name": "Abnormal Security", "type": "greenhouse", "board": "abnormalsecurity"},
        {"name": "At-Bay", "type": "greenhouse", "board": "atbayjobs"},
        {"name": "Recorded Future", "type": "greenhouse", "board": "recordedfuture"},
        {"name": "Tines", "type": "greenhouse", "board": "tines"},
        {"name": "Axonius", "type": "greenhouse", "board": "axonius"},
        {"name": "HiddenLayer", "type": "greenhouse", "board": "hiddenlayer"},
        {"name": "Vanta", "type": "ashby", "board": "vanta"},
        {"name": "Drata", "type": "ashby", "board": "drata"},
        {"name": "Material Security", "type": "ashby", "board": "materialsecurity"},
        {"name": "Semgrep", "type": "ashby", "board": "semgrep"},
        {"name": "Wiz", "type": "ashby", "board": "wiz"},
        {"name": "Teleport", "type": "greenhouse", "board": "teleport"},
        {"name": "Chainguard", "type": "greenhouse", "board": "chainguard"},
        {"name": "Armis", "type": "greenhouse", "board": "armissecurity"},
        {"name": "Vectra", "type": "greenhouse", "board": "vectranetworks"},
        {"name": "BeyondTrust", "type": "greenhouse", "board": "beyondtrust"},
        {"name": "NinjaOne", "type": "greenhouse", "board": "ninjaone"},
        {"name": "Orca Security", "type": "greenhouse", "board": "orcasecurity"},
        {"name": "Cymulate", "type": "greenhouse", "board": "cymulate"},
        {"name": "Island", "type": "greenhouse", "board": "island"},
        {"name": "Netskope", "type": "greenhouse", "board": "netskope"},
        {"name": "Tenable", "type": "greenhouse", "board": "tenableinc"},
        {"name": "Sift", "type": "greenhouse", "board": "sift"},
        {"name": "SentinelOne", "type": "greenhouse", "board": "sentinellabs"},
        {"name": "Rubrik", "type": "greenhouse", "board": "rubrik"},
        {"name": "Ping Identity", "type": "greenhouse", "board": "pingidentity"},
        {"name": "AppOmni", "type": "greenhouse", "board": "appomni"},
        {"name": "Keeper Security", "type": "greenhouse", "board": "keepersecurity"},
        {"name": "KnowBe4", "type": "greenhouse", "board": "knowbe4"},
        {"name": "ConnectWise", "type": "greenhouse", "board": "connectwise"},
        {"name": "Kaseya", "type": "greenhouse", "board": "kaseya"},
        {"name": "ThreatLocker", "type": "greenhouse", "board": "threatlocker"},
        {"name": "Deepwatch", "type": "greenhouse", "board": "deepwatchinc"},
        {"name": "Tanium", "type": "greenhouse", "board": "tanium"},
        {"name": "Jamf", "type": "greenhouse", "board": "jamf"},
        {"name": "CyberNut", "type": "ashby", "board": "cybernut"},
        {"name": "Rhymetec", "type": "greenhouse", "board": "rhymetec"},
        {"name": "LTS", "type": "greenhouse", "board": "lts"},
    ],
    tags=["security", "vendor", "cloud", "saas"],
    difficulty="stretch",
    hiring_pattern="steady",
    industry="security",
)

NYC_FRIENDLY_COMPANIES = with_profile(
    [
        {"name": "Major League Baseball", "type": "greenhouse", "board": "majorleaguebaseball"},
        {"name": "Roadie", "type": "greenhouse", "board": "roadie"},
        {"name": "Standard Bots", "type": "ashby", "board": "standardbots"},
    ],
    tags=["consumer", "nyc-friendly", "local-ny", "remote-friendly"],
    difficulty="realistic",
    hiring_pattern="steady",
    industry="consumer",
)

MID_TIER_COMPANIES = with_profile(
    [
        {"name": "Betterment", "type": "greenhouse", "board": "betterment"},
        {"name": "Plaid", "type": "lever", "board": "plaid"},
        {"name": "Braze", "type": "greenhouse", "board": "braze"},
        {"name": "Headway", "type": "greenhouse", "board": "headway"},
        {"name": "Spring Health", "type": "greenhouse", "board": "springhealth66"},
        {"name": "Maven Clinic", "type": "greenhouse", "board": "mavenclinic"},
        {"name": "Lumafield", "type": "lever", "board": "lumafield"},
        {"name": "Mercury", "type": "ashby", "board": "mercury"},
        {"name": "Retool", "type": "ashby", "board": "retool"},
        {"name": "Benchling", "type": "greenhouse", "board": "benchling"},
        {"name": "Samsara", "type": "greenhouse", "board": "samsara"},
        {"name": "Flock Safety", "type": "greenhouse", "board": "flocksafety"},
        {"name": "Verkada", "type": "greenhouse", "board": "verkada"},
        {"name": "Navan", "type": "greenhouse", "board": "navan"},
        {"name": "Sentry", "type": "greenhouse", "board": "sentry"},
        {"name": "ClickUp", "type": "greenhouse", "board": "clickup"},
        {"name": "Miro", "type": "greenhouse", "board": "miro"},
        {"name": "Zapier", "type": "greenhouse", "board": "zapier"},
        {"name": "Olo", "type": "greenhouse", "board": "olo"},
        {"name": "Hinge Health", "type": "greenhouse", "board": "hingehealth"},
        {"name": "Oscar Health", "type": "greenhouse", "board": "oscar"},
        {"name": "Warby Parker", "type": "greenhouse", "board": "warbyparker"},
        {"name": "Yext", "type": "greenhouse", "board": "yext"},
        {"name": "Yes Energy", "type": "greenhouse", "board": "yesenergy"},
        {"name": "Payabli", "type": "ashby", "board": "payabli"},
    ],
    tags=["tech", "mid-tier", "saas", "nyc-friendly", "remote-friendly"],
    difficulty="realistic",
    hiring_pattern="steady",
    industry="tech",
)

REALISTIC_TECH_COMPANIES = with_profile(
    [
        {"name": "Datadog", "type": "greenhouse", "board": "datadog"},
        {"name": "MongoDB", "type": "greenhouse", "board": "mongodb"},
        {"name": "Dropbox", "type": "greenhouse", "board": "dropbox"},
        {"name": "Webflow", "type": "greenhouse", "board": "webflow"},
        {"name": "Squarespace", "type": "greenhouse", "board": "squarespace"},
        {"name": "Gusto", "type": "greenhouse", "board": "gusto"},
        {"name": "Dataiku", "type": "greenhouse", "board": "dataiku"},
        {"name": "Chime", "type": "greenhouse", "board": "chime"},
        {"name": "Checkr", "type": "greenhouse", "board": "checkr"},
        {"name": "Robinhood", "type": "greenhouse", "board": "robinhood"},
        {"name": "Affirm", "type": "greenhouse", "board": "affirm"},
        {"name": "Brex", "type": "greenhouse", "board": "brex"},
        {"name": "Replit", "type": "ashby", "board": "replit"},
        {"name": "Ramp", "type": "ashby", "board": "ramp"},
        {"name": "Toast", "type": "greenhouse", "board": "toast"},
        {"name": "Postman", "type": "greenhouse", "board": "postman"},
        {"name": "Docker", "type": "greenhouse", "board": "docker"},
        {"name": "HashiCorp", "type": "greenhouse", "board": "hashicorp"},
        {"name": "PagerDuty", "type": "greenhouse", "board": "pagerduty"},
        {"name": "Airtable", "type": "greenhouse", "board": "airtable"},
        {"name": "Asana", "type": "greenhouse", "board": "asana"},
        {"name": "Discord", "type": "greenhouse", "board": "discord"},
        {"name": "HubSpot", "type": "greenhouse", "board": "hubspot"},
        {"name": "Elastic", "type": "greenhouse", "board": "elastic"},
        {"name": "Nextech", "type": "lever", "board": "nextech"},
        {"name": "IonQ", "type": "greenhouse", "board": "ionq"},
        {"name": "NinjaTrader", "type": "greenhouse", "board": "ninjatrader"},
        {"name": "Patreon", "type": "ashby", "board": "patreon"},
        {"name": "Temporal Technologies", "type": "greenhouse", "board": "temporaltechnologies"},
        {"name": "Attio", "type": "ashby", "board": "attio"},
        {"name": "Vultr", "type": "ashby", "board": "vultr"},
        {"name": "One Pass Solutions", "type": "ashby", "board": "one-pass-solutions"},
        {"name": "Knowtex", "type": "ashby", "board": "knowtex"},
        {"name": "Archy", "type": "ashby", "board": "Archy"},
        {"name": "Prompt", "type": "ashby", "board": "prompt"},
        {"name": "LangChain", "type": "ashby", "board": "langchain"},
        {"name": "Atlan", "type": "ashby", "board": "atlan"},
        {"name": "Default", "type": "ashby", "board": "withdefault"},
        {"name": "Flex", "type": "ashby", "board": "withflex"},
        {"name": "Hubstaff", "type": "ashby", "board": "hubstaff"},
        {"name": "Feathr", "type": "ashby", "board": "feathr"},
        {"name": "Roboflow", "type": "ashby", "board": "roboflow"},
        {"name": "Appspace", "type": "greenhouse", "board": "appspace"},
        {"name": "Glean", "type": "greenhouse", "board": "gleanwork"},
        {"name": "Algolia", "type": "greenhouse", "board": "algolia"},
        {"name": "Mattermost", "type": "greenhouse", "board": "mattermost"},
        {"name": "Cribl", "type": "greenhouse", "board": "cribl"},
        {"name": "Fleetio", "type": "greenhouse", "board": "fleetio"},
        {"name": "GitLab", "type": "greenhouse", "board": "gitlab"},
        {"name": "6sense", "type": "greenhouse", "board": "6sense"},
        {"name": "Locus Robotics", "type": "greenhouse", "board": "locusrobotics"},
        {"name": "Nexus Cognitive Technologies", "type": "ashby", "board": "nexus-cognitive"},
        {"name": "PerfectServe", "type": "greenhouse", "board": "perfectserve"},
        {"name": "Raptor Technologies", "type": "greenhouse", "board": "raptortechnologies"},
        {"name": "Submittable", "type": "greenhouse", "board": "submittable"},
        {"name": "Lirio", "type": "greenhouse", "board": "lirio"},
        {"name": "SpecterOps", "type": "greenhouse", "board": "specterops"},
        {"name": "ClickHouse", "type": "greenhouse", "board": "clickhouse"},
        {"name": "Accela", "type": "greenhouse", "board": "accela"},
        {"name": "Marqeta", "type": "greenhouse", "board": "marqeta"},
        {"name": "Fastly", "type": "greenhouse", "board": "fastly"},
    ],
    tags=["tech", "saas", "growth", "remote-friendly"],
    difficulty="realistic",
    hiring_pattern="steady",
    industry="tech",
)

STRETCH_TECH_COMPANIES = with_profile(
    [
        {"name": "Coinbase", "type": "greenhouse", "board": "coinbase"},
        {"name": "Airbnb", "type": "greenhouse", "board": "airbnb"},
        {"name": "Lyft", "type": "greenhouse", "board": "lyft"},
        {"name": "Instacart", "type": "greenhouse", "board": "instacart"},
        {"name": "Udemy", "type": "greenhouse", "board": "udemy"},
        {"name": "Coursera", "type": "greenhouse", "board": "coursera"},
        {"name": "Peloton", "type": "greenhouse", "board": "peloton"},
        {"name": "Reddit", "type": "greenhouse", "board": "reddit"},
        {"name": "Duolingo", "type": "greenhouse", "board": "duolingo"},
        {"name": "1Password", "type": "greenhouse", "board": "1password"},
        {"name": "Scale AI", "type": "greenhouse", "board": "scaleai"},
        {"name": "Rippling", "type": "greenhouse", "board": "rippling"},
        {"name": "Canva", "type": "greenhouse", "board": "canva"},
        {"name": "Anduril", "type": "greenhouse", "board": "andurilindustries"},
        {"name": "PlanetScale", "type": "greenhouse", "board": "planetscale"},
        {"name": "Tailscale", "type": "greenhouse", "board": "tailscale"},
    ],
    tags=["tech", "consumer", "growth"],
    difficulty="stretch",
    hiring_pattern="steady",
    industry="tech",
)

LOTTERY_COMPANIES = with_profile(
    [
        {"name": "OpenAI", "type": "ashby", "board": "openai"},
        {"name": "Anthropic", "type": "greenhouse", "board": "anthropic"},
        {"name": "Stripe", "type": "greenhouse", "board": "stripe"},
        {"name": "Figma", "type": "greenhouse", "board": "figma"},
        {"name": "Snowflake", "type": "ashby", "board": "snowflake"},
        {"name": "Notion", "type": "ashby", "board": "notion"},
    ],
    tags=["tech", "prestige", "brand-magnet"],
    difficulty="lottery",
    hiring_pattern="selective",
    industry="tech",
)

COMPANIES = (
    MSSP_COMPANIES
    + MID_TIER_COMPANIES
    + SECURITY_FOCUSED_COMPANIES
    + NYC_FRIENDLY_COMPANIES
    + REALISTIC_TECH_COMPANIES
    + STRETCH_TECH_COMPANIES
    + LOTTERY_COMPANIES
)

COMPANY_GROUP_BY_ID = {company["id"]: company["group"] for company in COMPANIES}
COMPANY_NAME_BY_ID = {company["id"]: company["name"] for company in COMPANIES}
COMPANY_TAGS_BY_ID = {company["id"]: tuple(company["tags"]) for company in COMPANIES}
COMPANY_DIFFICULTY_BY_ID = {company["id"]: company["difficulty"] for company in COMPANIES}
COMPANY_HIRING_PATTERN_BY_ID = {company["id"]: company["hiring_pattern"] for company in COMPANIES}
COMPANY_INDUSTRY_BY_ID = {company["id"]: company["industry"] for company in COMPANIES}
COMPANY_METADATA_BY_ID = {
    company["id"]: {
        "name": company["name"],
        "group": company["group"],
        "tags": tuple(company["tags"]),
        "difficulty": company["difficulty"],
        "hiring_pattern": company["hiring_pattern"],
        "industry": company["industry"],
        "source": company["type"],
        "board": company["board"],
    }
    for company in COMPANIES
}
