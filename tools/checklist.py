from __future__ import annotations

from config import AppConfig
from schemas import SourceAttribution, ToolResult
from tools.base import ActionTool, ToolParameter


BASE_CHECKLISTS = {
    "undergraduate": [
        "**Academic setup:** Check your Join U of T, ACORN, and faculty onboarding steps so you know your registration tasks, tuition deadlines, and any pre-arrival forms still pending.",
        "**Immigration documents:** Keep your passport, visa or eTA, PAL if required, letter of acceptance, and study permit support documents ready in both printed and digital form.",
        "**Housing confirmation:** Finalize your residence, temporary accommodation, or off-campus housing details, including move-in date, address, payment instructions, and key pickup plan.",
        "**Health coverage planning:** Review UHIP start timing, clinic access, and any prescription or vaccination records you should carry in case you need care soon after arrival.",
        "**Money and payment access:** Prepare enough funds for your first weeks, make sure your bank cards will work in Canada, and set a rough budget for rent, food, transit, phone, and emergency costs.",
        "**Technology and account access:** Test your UTORid, email, Duo or multi-factor login, and any student portals you may need for course enrolment, housing, or orientation.",
        "**Packing priorities:** Put travel documents, medications, chargers, weather-appropriate clothes, and one change of essentials in your carry-on rather than your checked luggage.",
    ],
    "graduate": [
        "**Graduate program coordination:** Confirm registration, department orientation, supervisor or graduate unit instructions, and any onboarding tasks tied to your program, lab, or funding.",
        "**Immigration documents:** Prepare your passport, visa or eTA, letter of acceptance, study permit paperwork, and printed backups so your border documents are easy to present.",
        "**Funding and cash-flow plan:** Check when scholarships, TA or RA funding, payroll, or reimbursements begin so you can cover the gap between arrival and first payment.",
        "**Housing confirmation:** Lock in your move-in plan, building access details, temporary backup stay if needed, and the exact route from the airport to your accommodation.",
        "**Health coverage planning:** Review UHIP timing, required personal records, and what you should do if you need medical help before you are fully settled.",
        "**Academic and identity records:** Keep your student number, offer details, department contacts, key emails, and any academic records you may need in one place.",
        "**Research or work onboarding:** If your program involves lab access, TA work, or early department paperwork, note what documents or account access you may need in the first week.",
    ],
    "phd": [
        "**Doctoral program coordination:** Confirm your department onboarding, SGS requirements, supervisor expectations, and any doctoral orientation, milestone, or registration steps due before arrival.",
        "**Supervisor and research start plan:** Check whether your supervisor, lab, or research group expects any meetings, paperwork, ethics training, or onboarding tasks in your first weeks.",
        "**Funding and stipend timing:** Confirm when your funding package, stipend, TA or RA payments, or reimbursements begin so you can plan for any gap before the first deposit arrives.",
        "**Immigration documents:** Keep your passport, visa or eTA, admission letter, study permit support documents, and printed backups organized for travel and border inspection.",
        "**Housing confirmation:** Finalize your move-in plan, building access, check-in instructions, and backup stay in case your travel timing shifts.",
        "**Health coverage planning:** Review UHIP timing, any prescription or medical documents you should carry, and what to do if you need care before you are fully settled.",
        "**Research and identity records:** Keep your student number, supervisor contact details, funding letters, department emails, and key academic records easy to access.",
        "**Work eligibility planning:** If TA, RA, or campus employment starts early, read ahead on SIN and payroll-related next steps so you are ready once you arrive.",
    ],
    "exchange": [
        "**Exchange administration:** Review your exchange acceptance, course enrolment, learning agreement or approvals, and any campus-specific onboarding requirements before departure.",
        "**Immigration documents:** Prepare your passport, visa or eTA, exchange admission documents, and study permit or visitor paperwork as required for your exchange length.",
        "**Housing confirmation:** Verify where you will stay when you arrive, how long that booking covers, and what to do if check-in timing changes.",
        "**Insurance and health planning:** Review UHIP or other required coverage for visiting students and carry any important medical or prescription documents with you.",
        "**Money and payment access:** Prepare a practical budget for the first few weeks and make sure you can pay for food, transit, phone service, and housing-related costs right away.",
        "**Academic readiness:** Save key dates for orientation, timetable changes, and the first week of classes so you do not miss exchange-specific deadlines.",
        "**Arrival contact plan:** Keep your host department, housing office, and emergency contact details accessible offline in case your internet connection is limited on arrival.",
    ],
    "other": [
        "**Program onboarding:** Review the registration steps, orientation messages, and deadlines for your program so you know what must be done before classes begin.",
        "**Immigration documents:** Keep your passport, visa or eTA, admission documents, and travel records ready in printed and digital form for easy access during travel.",
        "**Housing confirmation:** Confirm where you will stay, how you will enter the building, and what your backup plan is if travel timing changes.",
        "**Health coverage planning:** Review your health insurance setup, emergency care information, and any prescription or medical records you should carry.",
        "**Money and first-month budget:** Estimate your first-month costs and make sure you have payment access for rent, transit, groceries, and emergencies.",
        "**Technology and communications:** Test your university logins, save important contact details, and plan how you will get internet or phone access when you land.",
        "**Packing priorities:** Put your most important documents, medications, chargers, and immediate-use clothing in your carry-on rather than checked baggage.",
    ],
}

ARRIVAL_STATUS_STEPS = {
    "not_arrived": [
        "**Travel booking timing:** Finalize flights only after your entry documents, housing dates, and arrival plan line up so you do not create last-minute travel problems.",
        "**Pre-arrival roadmap check:** Review the Pre-Arrival and Roadmap resources to make sure you have not missed any university, travel, or settlement task.",
        "**Offline backup folder:** Download or print the key documents, addresses, and contact information you would still need if your phone battery dies or internet is unavailable.",
    ],
    "arriving_soon": [
        "**Carry-on document folder:** Put your passport, visa or eTA, admission documents, housing details, and study permit paperwork in your carry-on so they are immediately available.",
        "**Airport-to-housing route:** Decide exactly how you will get from the airport to your accommodation, including late-night, weekend, or delayed-flight backup options.",
        "**First 72 hours plan:** Prepare medications, weather-appropriate clothes, toiletries, payment access, and the essentials you need before you can fully unpack or shop.",
        "**Arrival communications:** Make sure you can contact your housing provider, friend, family member, or campus office quickly if you are delayed or need help finding the location.",
    ],
}

FIRST_TIME_CANADA_STEPS = [
    "**Border readiness:** Know which documents you may need to show at the airport or port of entry, and keep all supporting paperwork together rather than packed away in checked luggage.",
    "**First-time settlement planning:** Save your university address, housing address, emergency contacts, and key support links somewhere you can access offline if needed.",
    "**Phone and connectivity:** Make a plan for mobile data, Wi-Fi access, and how you will contact housing or support services as soon as you land.",
    "**Canadian essentials planning:** Read ahead about banking, transit, and SIN-related next steps so the first week in Canada feels less overwhelming.",
]

WEEKEND_ARRIVAL_STEPS = [
    "**Weekend or after-hours check-in:** Confirm exactly how you will enter your building, collect keys, or reach staff if your housing office is closed when you arrive.",
    "**Food and essentials backup:** Identify a nearby grocery store, pharmacy, or convenience option in case you arrive outside regular business hours.",
    "**Weekend transit backup:** Check airport transit, taxi, or rideshare options for your expected arrival time so you are not stranded if regular service is limited.",
]

STATUS_LABELS = {
    "not_arrived": "planning ahead",
    "arriving_soon": "arriving soon",
}

DISPLAY_LABELS = {
    "undergraduate": "undergraduate",
    "graduate": "graduate",
    "phd": "PhD",
    "exchange": "exchange",
    "other": "student",
}

DISPLAY_ARTICLES = {
    "undergraduate": "an",
    "graduate": "a",
    "phd": "a",
    "exchange": "an",
    "other": "a",
}

CHECKLIST_SOURCES = [
    SourceAttribution(
        title="Pre-Arrival",
        url="https://internationalexperience.utoronto.ca/international-student-services/resource-and-information-hub/pre-arrival",
        section="Pre-Arrival",
    ),
    SourceAttribution(
        title="University Health Insurance Plan (UHIP)",
        url="https://internationalexperience.utoronto.ca/international-student-services/healthcare-coverage-and-u-of-t/university-health-insurance-plan-uhip",
        section="University Health Insurance Plan (UHIP)",
    ),
    SourceAttribution(
        title="Finances",
        url="https://internationalexperience.utoronto.ca/international-student-services/resource-and-information-hub/finances",
        section="Finances",
    ),
]


class PreArrivalChecklistTool(ActionTool):
    name = "pre_arrival_checklist"
    description = "Generate a personalized pre-arrival checklist."
    parameters = [
        ToolParameter(
            name="student_type",
            description="The student's academic profile.",
            follow_up_question="Which student type best fits you: undergraduate, graduate, PhD, exchange, or other?",
            allowed_values=["undergraduate", "graduate", "phd", "exchange", "other"],
        ),
        ToolParameter(
            name="arrival_status",
            description="The student's current arrival stage.",
            follow_up_question=(
                "Which stage best fits you right now: **planning ahead** or **arriving soon**?\n\n"
                "**Planning ahead** means you are still preparing and your trip is not imminent.\n"
                "**Arriving soon** means you expect to arrive within the next 2 to 3 weeks.\n\n"
                "If you are already in Canada, say that and I will switch to arrival-focused guidance instead."
            ),
            allowed_values=["not_arrived", "arriving_soon", "already_in_canada"],
        ),
    ]

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config

    def _request_specific_steps(self, request_text: str) -> list[str]:
        lowered = request_text.lower()
        extra_steps: list[str] = []

        if any(
            phrase in lowered
            for phrase in [
                "first time in canada",
                "first time come to canada",
                "first time coming to canada",
                "new to canada",
                "never been to canada",
            ]
        ):
            extra_steps.extend(FIRST_TIME_CANADA_STEPS)
        if any(token in lowered for token in ["this weekend", "next weekend", "weekend", "saturday", "sunday"]):
            extra_steps.extend(WEEKEND_ARRIVAL_STEPS)
        return extra_steps

    def _already_in_canada_steps(self) -> list[str]:
        return [
            "**UHIP and health setup:** Confirm your UHIP coverage status, keep your insurance details handy, and learn where to get care if you need help soon.",
            "**Immediate local essentials:** Set up your phone access, transit plan, groceries, and any basic items you need for your first week in Canada.",
            "**Money and identity setup:** Plan for banking, payment access, and any next steps related to SIN or employment paperwork if they apply to you.",
            "**Housing and orientation follow-up:** Confirm move-in details, building access, and any orientation or faculty events you still need to attend.",
            "**Support contacts:** Save CIE, your department or faculty, and housing contacts in case an urgent issue comes up after arrival.",
        ]

    def _ensure_minimum_depth(self, items: list[str], minimum: int = 8) -> list[str]:
        if len(items) >= minimum:
            return items

        filler_items = [
            "**Important contacts:** Save key university, housing, and emergency contact information before you travel.",
            "**Arrival calendar:** Put orientation, registration, payment, and first-week deadlines in one place you can quickly check.",
            "**Packing cross-check:** Recheck your carry-on against your document list, medications, chargers, and weather essentials before departure.",
        ]
        seen = {item.lower() for item in items}
        completed = list(items)
        for item in filler_items:
            if item.lower() in seen:
                continue
            completed.append(item)
            seen.add(item.lower())
            if len(completed) >= minimum:
                break
        return completed

    def run(
        self,
        params: dict[str, str],
        request_text: str = "",
        history=None,
    ) -> ToolResult:
        student_type = params.get("student_type", "other")
        arrival_status = params.get("arrival_status", "not_arrived")
        student_label = DISPLAY_LABELS.get(student_type, student_type.replace("_", " "))
        article = DISPLAY_ARTICLES.get(student_type, "a")

        if arrival_status == "already_in_canada":
            body = "\n".join(f"- {item}" for item in self._already_in_canada_steps())
            output = (
                "A **pre-arrival checklist** is mainly for students who have **not reached Canada yet**.\n\n"
                "Since you are **already in Canada**, focus on these **arrival and settlement tasks** instead:\n\n"
                f"{body}\n\n"
                "If you want, I can help you turn this into an arrival-week checklist next."
            )
            return ToolResult(tool_name=self.name, output=output, sources=CHECKLIST_SOURCES, metadata={"redirected": True})

        checklist_items = list(BASE_CHECKLISTS.get(student_type, BASE_CHECKLISTS["other"]))
        checklist_items.extend(ARRIVAL_STATUS_STEPS.get(arrival_status, ARRIVAL_STATUS_STEPS["not_arrived"]))
        checklist_items.extend(self._request_specific_steps(request_text))

        # Keep order stable while removing duplicates.
        unique_items: list[str] = []
        seen: set[str] = set()
        for item in checklist_items:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            unique_items.append(item)

        unique_items = self._ensure_minimum_depth(unique_items, minimum=8)

        body = "\n".join(f"- {item}" for item in unique_items)
        output = (
            f"Here is your **pre-arrival checklist** for **{article} {student_label} student** who is **{STATUS_LABELS.get(arrival_status, 'planning ahead')}**:\n\n"
            "Use this as a practical preparation list before you travel:\n\n"
            f"{body}"
        )
        return ToolResult(
            tool_name=self.name,
            output=output,
            sources=CHECKLIST_SOURCES,
            metadata={"bullet_count": len(unique_items), "tool_mode": "structured_checklist"},
        )
